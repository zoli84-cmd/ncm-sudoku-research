import numpy as np
import pytest
import torch

from conftest import ROOT, needs_model

LOCK = ROOT / "runs" / "e5" / "lock"
HEADS = ROOT / "runs" / "e5" / "causal" / "heads"
needs_components = pytest.mark.skipif(
    not all((LOCK / f"{k}.npy").exists() for k in ("W", "Q", "H", "R", "Pi"))
    or not all((HEADS / f"{k}.pt").exists() for k in ("P4", "P8")),
    reason="frozen E5 components or P4/P8 heads not on disk",
)


def test_conditions_constant():
    from ncm_sudoku.e5batch import CONDITIONS

    assert CONDITIONS == ["Q"] + [f"rand{j}" for j in range(20)] + ["hv", "shuf", "full_be", "full_input"]
    assert len(CONDITIONS) == 25


def test_codes_must_cover_exactly_levels_1_to_6():
    from ncm_sudoku.e5batch import evaluate_batch

    good = np.zeros((2, 35), np.int64)
    for cr, cd in ((np.zeros((2, 34), np.int64), good), (good, np.zeros((2, 36), np.int64))):
        with pytest.raises(ValueError, match="35"):
            evaluate_batch(None, {}, {}, None, None, cr, cd, None, None, None, None)


def _batch_inputs(model, released):
    from ncm_sudoku.labels import candidate_mask
    from ncm_sudoku.runner import generate_codes, puzzle_tensor

    pz_r = released[0][:4]
    pz_d = pz_r[::-1].copy()  # donors: the same four puzzles in reversed order
    codes = generate_codes(model, pz_r, batch_size=4).numpy().astype(np.int64)[:, :35]
    comps = {k: np.load(LOCK / f"{k}.npy", allow_pickle=False) for k in ("W", "Q", "H", "R", "Pi")}
    heads = {k: torch.load(HEADS / f"{k}.pt", weights_only=True) for k in ("P4", "P8")}
    mask = lambda p: np.stack([candidate_mask(g) for g in p])  # noqa: E731
    return (comps, heads, puzzle_tensor(pz_r), puzzle_tensor(pz_d), codes, codes[::-1].copy(),
            pz_r == 0, pz_d == 0, mask(pz_r), mask(pz_d))


@pytest.mark.slow
@needs_model
@needs_components
def test_evaluate_batch_passes_all_checks_on_real_pairs(model, released):
    from ncm_sudoku.e5batch import CONDITIONS, evaluate_batch

    args = _batch_inputs(model, released)
    out = evaluate_batch(model, *args)
    assert out["invalid_reasons"] == []
    for key in ("directed", "undirected", "argmax_changes", "shift4", "shift8", "flip4", "flip8"):
        assert out[key].shape == (4, len(CONDITIONS)) and out[key].dtype == np.float64
        assert np.isfinite(out[key]).all()
    ci = {c: i for i, c in enumerate(CONDITIONS)}
    d = out["directed"]
    # the full swap is its own reference: directed = TV(clean, full) - 0
    assert np.array_equal(d[:, ci["full_be"]], out["diagnostics"]["tv_clean_full"])
    assert (d[:, ci["full_be"]] > 0).all()
    diag = out["diagnostics"]
    assert diag["target_norm"].shape == (4,)
    for k in ("actual_norm", "scale", "cos_delta"):
        assert diag[k].shape == (4, len(CONDITIONS))
    # Q steps are not rescaled; the full swap's actual change is the full difference
    assert np.allclose(diag["scale"][:, ci["Q"]], 1.0)
    assert np.allclose(diag["actual_norm"][:, ci["Q"]], diag["target_norm"], rtol=1e-5)


@pytest.mark.slow
@needs_model
@needs_components
def test_evaluate_batch_reports_injected_failures(model, released, monkeypatch):
    from ncm_sudoku import e5batch

    args = _batch_inputs(model, released)
    comps = args[0]
    orig_project, orig_norm, orig_values = e5batch.project_step, e5batch.norm_matched, e5batch._patch_values

    def leaky_project(delta, basis):  # the high-variance step picks up a W-row component
        step = orig_project(delta, basis)
        if basis is comps["H"]:
            step = step + np.linalg.norm(step, axis=1, keepdims=True) * comps["W"][0] / np.linalg.norm(comps["W"][0])
        return step

    monkeypatch.setattr(e5batch, "project_step", leaky_project)
    reasons = e5batch.evaluate_batch(model, *args)["invalid_reasons"]
    assert "hv_invariance" in reasons
    monkeypatch.setattr(e5batch, "project_step", orig_project)

    def failing_norm(raw, target):
        raise ValueError("control projection numerically zero for a positive target norm")

    monkeypatch.setattr(e5batch, "norm_matched", failing_norm)
    out = e5batch.evaluate_batch(model, *args)
    assert "zero_rule" in out["invalid_reasons"]
    assert out["invalid_reasons"].count("zero_rule") == 1  # deduplicated per batch
    assert out["directed"].shape == (4, len(e5batch.CONDITIONS))  # the pairs are not dropped
    monkeypatch.setattr(e5batch, "norm_matched", orig_norm)

    def tampered_values(xr, both, step=None, donor=None):  # one written element off by 1 ulp
        v = orig_values(xr, both, step=step, donor=donor)
        r, c = np.argwhere(both)[0]
        v[r, c, 0] = np.nextafter(v[r, c, 0], np.float32(np.inf))
        return v

    monkeypatch.setattr(e5batch, "_patch_values", tampered_values)
    reasons = e5batch.evaluate_batch(model, *args)["invalid_reasons"]
    assert "written_rows" in reasons


@pytest.mark.slow
@needs_model
@needs_components
def test_evaluate_batch_reports_untouched_rows_and_hook_level(model, released, monkeypatch):
    from ncm_sudoku import e5batch, e5causal

    args = _batch_inputs(model, released)

    def leaky_patch(self, _m, _a, out):  # `Level7Hooks._patch`, but the BOS row 0 is changed too
        self.applied += 1
        self.captured["L2_before"] = out.detach().clone()
        if self.patch is None:
            return out
        rows, values = self.patch
        new = out.clone()
        new[:, 0] += 1.0
        mask = torch.as_tensor(rows)[..., None]
        new[:, self.cells] = torch.where(mask, torch.as_tensor(values, dtype=new.dtype), new[:, self.cells])
        self.written_ok, self.untouched_ok = e5causal.isolation_check(out, new, self.cells, rows, values)
        self.captured["L2_after"] = new.detach().clone()
        return new

    with monkeypatch.context() as mp:
        mp.setattr(e5causal.Level7Hooks, "_patch", leaky_patch)
        assert "untouched_rows" in e5batch.evaluate_batch(model, *args)["invalid_reasons"]

    orig_level_logits = e5batch.level_logits

    def wrong_level(m, prefix, codes, level):  # every call runs level 6 instead of 7
        return orig_level_logits(m, prefix, codes, level - 1)

    monkeypatch.setattr(e5batch, "level_logits", wrong_level)
    assert "hook_level" in e5batch.evaluate_batch(model, *args)["invalid_reasons"]


@pytest.mark.slow
@needs_model
@needs_components
def test_evaluate_batch_flags_a_foreign_hook(model, released):
    from ncm_sudoku.e5batch import evaluate_batch

    args = _batch_inputs(model, released)
    handle = model.net.transformer.blocks[5].register_forward_pre_hook(lambda _m, _a: None)
    try:
        assert evaluate_batch(model, *args)["invalid_reasons"] == ["hook_count"]
    finally:
        handle.remove()

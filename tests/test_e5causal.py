import numpy as np
import pytest
import torch

from conftest import needs_model
from ncm_sudoku.e5causal import (
    DERANGEMENT,
    Level7Hooks,
    compare_predictions,
    isolation_check,
    high_variance_basis,
    norm_matched,
    orthonormal_rows,
    project_step,
    random_basis,
    shuffled_raw,
    tv,
)


def test_bases_are_orthonormal_and_rank_checked():
    R = random_basis(3)
    assert np.allclose(R.T @ R, np.eye(9))
    W = np.random.default_rng(0).standard_normal((9, 512))
    Q, s = orthonormal_rows(W)
    assert np.allclose(Q.T @ Q, np.eye(9)) and np.allclose(W @ (Q @ Q.T), W)
    with pytest.raises(ValueError):
        orthonormal_rows(np.vstack([W[:8], W[:1]]))


def test_norm_matching_and_zero_rule():
    raw = np.array([[3.0, 4.0], [1.0, 0.0], [0.0, 0.0]])
    step, scale = norm_matched(raw, np.array([10.0, 2.0, 0.0]))
    assert np.allclose(np.linalg.norm(step, axis=1), [10, 2, 0]) and scale[2] == 0
    with pytest.raises(ValueError):
        norm_matched(np.zeros((1, 2)), np.array([1.0]))


def test_shuffled_step_permutes_the_head_logit_change():
    rng = np.random.default_rng(1)
    W = rng.standard_normal((9, 512))
    delta = rng.standard_normal((5, 512))
    step = shuffled_raw(delta, W)
    assert np.allclose(step @ W.T, (delta @ W.T)[:, DERANGEMENT])
    assert not np.any(DERANGEMENT == np.arange(9))


def test_high_variance_basis_is_orthogonal_to_q_and_keeps_head_logits():
    rng = np.random.default_rng(2)
    W = rng.standard_normal((9, 512))
    Q, _ = orthonormal_rows(W)
    B = high_variance_basis(rng.standard_normal((400, 512)), Q)
    assert np.allclose(Q.T @ B, 0, atol=1e-10) and np.allclose(B.T @ B, np.eye(9), atol=1e-10)
    delta = rng.standard_normal((3, 512))
    assert np.allclose(project_step(delta, B) @ W.T, 0, atol=1e-9)


def test_compare_predictions_checks_shape_nan_pattern_finiteness_and_equality():
    saved = np.full((2, 81, 9), np.nan)
    saved[:, :40] = 0.25
    assert compare_predictions(saved.copy(), saved)["passed"]
    off = saved.copy()
    off[0, 0, 0] = np.nextafter(0.25, 1)
    r = compare_predictions(off, saved)
    assert not r["passed"] and r["max_abs_diff"] > 0 and r["n_unequal"] == 1
    hole = saved.copy()
    hole[0, 50, 0] = 0.25  # evaluable on one side only
    assert not compare_predictions(hole, saved)["nan_pattern_equal"]
    inf = saved.copy()
    inf[1, 3, 3] = np.inf
    assert not compare_predictions(inf, saved)["finite"]
    assert not compare_predictions(saved[:1], saved)["shape_equal"]


def _iso_case():
    rng = np.random.default_rng(5)
    B, T, d = 2, 100, 4
    cells = np.arange(1, 82)
    out = torch.as_tensor(rng.standard_normal((B, T, d)), dtype=torch.float32)
    rows = np.zeros((B, 81), bool)
    rows[0, [3, 7]] = rows[1, 10] = True
    values = rng.standard_normal((B, 81, d)).astype(np.float32)
    new = out.clone()
    new[:, 1:82][torch.as_tensor(rows)] = torch.as_tensor(values[rows])
    return out, new, cells, rows, values


def test_isolation_check_covers_every_non_targeted_row():
    out, new, cells, rows, values = _iso_case()
    assert isolation_check(out, new, cells, rows, values) == (True, True)
    bad = new.clone()
    bad[0, 1 + 5, 0] += 1  # a cell row that is not targeted (the old check skipped all cell rows)
    assert isolation_check(out, bad, cells, rows, values) == (True, False)
    bad = new.clone()
    bad[1, 0, 0] += 1  # BOS row
    assert isolation_check(out, bad, cells, rows, values)[1] is False
    bad = new.clone()
    bad[0, 1 + 3, 2] = float(np.nextafter(np.float32(bad[0, 1 + 3, 2].item()), np.float32(10)))
    assert isolation_check(out, bad, cells, rows, values)[0] is False


class _FakeNet(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.transformer = torch.nn.Module()
        self.transformer.blocks = torch.nn.ModuleList([torch.nn.Identity() for _ in range(8)])
        self.prefix_len = 91


def test_level7_hooks_patch_and_flags():
    out, _, cells, rows, values = _iso_case()
    net = _FakeNet()
    with Level7Hooks(net, cells) as h:
        h.patch = (rows, values)
        new = net.transformer.blocks[1](out)
    assert h.applied == 1 and h.written_ok and h.untouched_ok
    assert torch.equal(new[:, 1:82][torch.as_tensor(rows)], torch.as_tensor(values[rows]))
    assert torch.equal(new[:, 1:82][torch.as_tensor(~rows)], out[:, 1:82][torch.as_tensor(~rows)])


def test_tv_averages_over_queries():
    p = np.zeros((1, 2, 16))
    q = np.zeros((1, 2, 16))
    p[0, :, 0] = 1
    q[0, 0, 0] = 1
    q[0, 1, 1] = 1
    assert np.allclose(tv(p, q), [0.5])


@pytest.mark.slow
@needs_model
def test_hook_identity_self_donor_and_full_swap(model, released):
    from ncm_sudoku.e5causal import Level7Hooks
    from ncm_sudoku.e5extract import PREFIX_CELLS
    from ncm_sudoku.intervene import level_logits
    from ncm_sudoku.runner import generate_codes, puzzle_tensor

    pz = released[0][:4]
    x = puzzle_tensor(pz)
    codes = generate_codes(model, pz, batch_size=4)
    plain = level_logits(model, x, codes, 7)
    with Level7Hooks(model.net, PREFIX_CELLS) as h:
        clean = level_logits(model, x, codes, 7)
        assert h.applied == 1
        own = h.captured["L2_before"][:, torch.as_tensor(PREFIX_CELLS)].numpy()
    assert torch.equal(plain, clean)
    rows = (pz == 0)
    with Level7Hooks(model.net, PREFIX_CELLS) as h:  # self-donor: own values written back
        h.patch = (rows, own)
        same = level_logits(model, x, codes, 7)
        assert h.applied == 1 and h.untouched_ok and h.written_ok
    assert torch.equal(same, clean)
    donor = own[::-1].copy()  # a real, different donor (rows reversed)
    with Level7Hooks(model.net, PREFIX_CELLS) as h:
        h.patch = (rows, donor)
        level_logits(model, x, codes, 7)
        after = h.captured["L2_after"][:, torch.as_tensor(PREFIX_CELLS)].numpy()
        assert h.untouched_ok and h.written_ok
    assert np.array_equal(after[rows], donor[rows]) and np.array_equal(after[~rows], own[~rows])

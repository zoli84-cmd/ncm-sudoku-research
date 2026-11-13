import functools
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from ncm_sudoku import e2p2, subsets, wp2

ROOT = Path(__file__).resolve().parents[1]
TAG = "a" * 40
CODE = {"commit": TAG, "dirty": False, "diff_sha256": None}
ENV = {"python": "3.12.0", "torch": "2.x", "deterministic": True}
FROZEN = {"tag": "wp2-code", "tag_commit": TAG, "head": TAG, "code_clean": True,
          "upstream_commit": wp2.UPSTREAM_COMMIT, "upstream_ok": True, "upstream_clean": True, "frozen": True}
KEYS = ["base", "level1/v00", "L06/B"]
N_CAL = 5
N = 3  # dry-role size in these tests


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _restore_determinism():
    prev = torch.are_deterministic_algorithms_enabled()
    yield
    torch.use_deterministic_algorithms(prev)


def _fake_cal():
    rng = np.random.default_rng(1)
    return [SimpleNamespace(puzzle_id=f"cal-{i}", puzzle=rng.integers(0, 10, 81).astype(np.int8),
                            solution=rng.integers(1, 10, 81).astype(np.int8)) for i in range(N_CAL)]


def _values(key, ids, sham_b=None):
    if key == "base":
        return [{"puzzle_id": p, "solve_A": 1, "solve_B1": 1} for p in ids]
    if key.startswith("level1/"):
        return [{"puzzle_id": p, "value": 0, "noop": False, "solve_D": 0} for p in ids]
    solve_B = [1] * len(ids)
    if sham_b is not None:
        solve_B[sham_b] = 0
    return solve_B


class Pilot:
    """Fake `e2p2.run_pilot2` with the stage contract (done, on_stage, technical)."""

    def __init__(self, fail_after=None, mismatch=None, sham_b=None, check=None):
        self.fail_after, self.mismatch, self.sham_b, self.check = fail_after, mismatch or {}, sham_b, check
        self.calls = []

    def __call__(self, m, puzzles, solutions, ids, chunk=50, frozen_freqs=None, A=None, done=None,
                 on_stage=None, decode_chunk=None, diagnostics=False):
        assert {1, 2, 6, 11} <= set(frozen_freqs)
        self.calls.append({"A": A.clone(), "done": dict(done), "decode_chunk": decode_chunk,
                           "diagnostics": diagnostics, "chunk": chunk, "ids": list(ids)})
        vals, n_new = {}, 0
        for i, key in enumerate(KEYS):
            if key in done:
                vals[key] = done[key]
                continue
            if self.fail_after is not None and n_new == self.fail_after:
                raise RuntimeError("simulated crash")
            if self.check is not None:
                self.check(key)
            vals[key] = _values(key, ids, self.sham_b)
            diag = {"changed_C": np.zeros((len(ids), 81), dtype=bool)} if key.startswith("level1/") else None
            on_stage(key, vals[key], diag, {"seconds": 1.0 + i, "diag_seconds": 0.25 * i,
                                            "code_mismatch": self.mismatch.get(key, 0)})
            n_new += 1
        base = vals["base"]
        records = [{"puzzle_id": b["puzzle_id"], "level": 6, "solve_A": b["solve_A"], "solve_B": sb}
                   for b, sb in zip(base, vals["L06/B"])]
        return {"freqs_level1": [1 / 16] * 16, "freq_source": "frozen", "base": base,
                "level1": vals["level1/v00"], "level1_noop_mismatch": 0,
                "level1_noop_max_tv": {"tv": None, "tv_empty": None}, "records": records}


@pytest.fixture
def env(tmp_path, monkeypatch):
    mod = _load("wp2_e2")
    monkeypatch.setattr(wp2, "ROOT", tmp_path)
    monkeypatch.setattr(wp2, "DRY_CHECK", tmp_path / "experiments" / "wp2" / "dry" / "check.json")
    monkeypatch.setattr(wp2, "freeze_state", lambda root=None: dict(FROZEN))
    monkeypatch.setattr(wp2, "code_state", lambda: dict(CODE))
    monkeypatch.setattr(wp2, "environment_record", lambda: dict(ENV))
    cal = _fake_cal()
    monkeypatch.setattr(wp2.subsets, "generate_subset", lambda name, n: cal[:n] if name == "cal" else pytest.fail())
    real_load_role = wp2.load_role
    monkeypatch.setattr(wp2, "load_role", lambda role: real_load_role(role, n_dry=N))
    levels = {str(lv): {"counts": [1] * 16, "frequencies": (np.ones(16) / 16).astype(np.float32).tolist()}
              for lv in range(1, 13)}
    freqs = tmp_path / "cal_freqs.json"
    freqs.write_text(json.dumps({"levels": levels}), encoding="utf-8")
    monkeypatch.setattr(mod, "FREQS", freqs)
    monkeypatch.setattr(mod, "FREQS_SHA256", wp2.file_sha256(freqs))
    order = []
    monkeypatch.setattr(wp2, "verify_checkpoints", lambda d: order.append("ckpt"))
    monkeypatch.setattr(mod, "load_model", lambda d: order.append("model") or SimpleNamespace(levels=(1, 2)))
    clean = []

    def clean_codes(m, puzzles, chunk=50):
        clean.append(len(puzzles))
        return torch.arange(len(puzzles) * 3, dtype=torch.int64).reshape(len(puzzles), 3)
    monkeypatch.setattr(e2p2, "clean_codes", clean_codes)
    monkeypatch.setattr(e2p2, "stage_keys", lambda levels: list(KEYS))
    pilot = Pilot()
    monkeypatch.setattr(e2p2, "run_pilot2", pilot)
    exp, raw = tmp_path / "experiments" / "wp2" / "dry", tmp_path / "runs" / "wp2" / "dry"
    return SimpleNamespace(mod=mod, cal=cal, order=order, clean=clean, pilot=pilot, mp=monkeypatch,
                           record=exp / "runs" / "e2.json", raw=raw, e2=raw / "e2")


def _use(env, pilot):
    env.mp.setattr(e2p2, "run_pilot2", pilot)
    env.pilot = pilot
    return pilot


def _rec(env):
    return json.loads(env.record.read_text(encoding="utf-8"))


def _crash(env, fail_after=2, **kw):
    _use(env, Pilot(fail_after=fail_after, **kw))
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.mod.main(["--role", "dry"])


def test_wp2_e2_constants():
    mod = _load("wp2_e2")
    assert mod.FREQS == ROOT / "experiments" / "lock" / "cal_freqs.json"
    assert mod.FREQS_SHA256 == "0cc7292718750754baf27b813a4095e2a7479cf4e480fbed50e43c665c7983fb"
    assert mod.CHUNK == 50 and mod.DECODE_CHUNK == 50
    assert wp2.file_sha256(mod.FREQS) == mod.FREQS_SHA256


def test_wp2_e2_dry_end_to_end(env):
    env.mod.main(["--role", "dry"])
    raw = json.loads((env.raw / "e2.json").read_text(encoding="utf-8"))
    assert raw["role"] == "dry" and raw["freq_source"] == "frozen" and raw["note"] == wp2.DRY_NOTE
    assert raw["ids"] == [g.puzzle_id for g in env.cal[:N]]
    assert raw["chunk"] == 50 and raw["decode_chunk"] == 50 and raw["freqs_sha256"] == env.mod.FREQS_SHA256
    assert raw["environment"] == ENV and raw["code"] == CODE and raw["freeze"]["frozen"] is True
    rec = _rec(env)
    assert rec["complete"] is True and rec["valid"] is True and rec["status"] == "valid"
    assert rec["inputs"] == {"n": N, "ids_sha256": subsets.sha256_ids(raw["ids"]),
                             "puzzles_sha256": subsets.sha256_array(np.stack([g.puzzle for g in env.cal[:N]])),
                             "solutions_sha256": subsets.sha256_array(np.stack([g.solution for g in env.cal[:N]])),
                             "freqs_sha256": env.mod.FREQS_SHA256, "chunk": 50, "decode_chunk": 50}
    assert rec["n_records"] == N and rec["n_level1_records"] == N and rec["level1_noop_mismatch"] == 0
    assert rec["sham_mismatch"] == {"level1_B1": 0, "levels_B": {"6": 0}}
    assert rec["code_mismatch"] == {"level1_B1": 0, "levels_B": {"6": 0}, "level1_noop_D": 0}
    assert rec["outputs"] == {"e2.json": wp2.file_sha256(env.raw / "e2.json"),
                              "A.npy": wp2.file_sha256(env.e2 / "A.npy"),
                              "parts.json": wp2.file_sha256(env.e2 / "parts.json")}
    A = np.load(env.e2 / "A.npy")
    assert A.dtype == np.int64 and A.shape == (N, 3)
    assert env.order == ["ckpt", "model"]
    assert env.pilot.calls[0]["chunk"] == 50 and env.pilot.calls[0]["ids"] == raw["ids"]
    assert {"pilot_seconds", "context_seconds"} <= set(rec["timing"]) and rec["timing"] == raw["timing"]


def test_wp2_e2_passes_decode_chunk_and_diagnostics(env):
    env.mod.main(["--role", "dry"])
    call = env.pilot.calls[0]
    assert call["decode_chunk"] == 50 and call["diagnostics"] is True
    raw = json.loads((env.raw / "e2.json").read_text(encoding="utf-8"))
    diag = env.e2 / "diag" / "level1__v00.npz"
    assert raw["diag_files"] == {"level1/v00": {"file": "level1__v00.npz", "sha256": wp2.file_sha256(diag)}}
    with np.load(diag) as z:
        assert z["changed_C"].shape == (N, 81)
    manifest = json.loads((env.e2 / "parts.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"parts/base.json", "parts/level1__v00.json", "parts/L06__B.json",
                             "diag/level1__v00.npz"}


def test_wp2_e2_A_hash_recorded_before_first_stage(env):
    seen = []

    def check(key):
        if not seen:
            rec = _rec(env)
            seen.append(rec.get("A_sha256") == wp2.file_sha256(env.e2 / "A.npy"))
    _use(env, Pilot(check=check))
    env.mod.main(["--role", "dry"])
    assert seen == [True]


def test_wp2_e2_resume_after_crash(env):
    _crash(env)
    rec = _rec(env)
    assert rec["complete"] is False and "A_sha256" in rec
    assert sorted(p.name for p in (env.e2 / "parts").iterdir()) == ["base.json", "level1__v00.json"]
    assert (env.e2 / "A.npy").is_file()
    A_first = env.pilot.calls[0]["A"]
    pilot = _use(env, Pilot())
    with pytest.raises(SystemExit):
        env.mod.main(["--role", "dry"])
    env.mp.setattr(e2p2, "clean_codes", lambda *a, **k: pytest.fail("A must be loaded from A.npy"))
    env.mod.main(["--role", "dry", "--resume"])
    assert set(pilot.calls[0]["done"]) == {"base", "level1/v00"}
    assert torch.equal(pilot.calls[0]["A"], A_first)
    rec = _rec(env)
    assert rec["complete"] is True and rec["valid"] is True and len(rec["resumes"]) == 1


def test_wp2_e2_crash_before_A(env):
    def boom(*a, **k):
        raise RuntimeError("simulated crash")
    real = e2p2.clean_codes
    env.mp.setattr(e2p2, "clean_codes", boom)
    with pytest.raises(RuntimeError):
        env.mod.main(["--role", "dry"])
    assert not (env.e2 / "A.npy").exists() and "A_sha256" not in _rec(env)
    env.mp.setattr(e2p2, "clean_codes", real)
    env.mod.main(["--role", "dry", "--resume"])
    assert env.clean == [N] and env.pilot.calls[0]["done"] == {}
    assert _rec(env)["A_sha256"] == wp2.file_sha256(env.e2 / "A.npy")
    assert _rec(env)["A_regenerated_matches"] is None


def test_wp2_e2_crash_between_A_and_record(env):
    real = wp2.update_run
    env.mp.setattr(wp2, "update_run", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("simulated crash")))
    with pytest.raises(RuntimeError):
        env.mod.main(["--role", "dry"])
    assert (env.e2 / "A.npy").is_file() and "A_sha256" not in _rec(env) and not (env.e2 / "parts").exists()
    stale_part, stale_diag = env.e2 / "parts" / "stale.json", env.e2 / "diag" / "stale.npz"
    for p in (stale_part, stale_diag):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
    env.mp.setattr(wp2, "update_run", real)
    env.mod.main(["--role", "dry", "--resume"])
    assert env.clean == [N, N] and env.pilot.calls[0]["done"] == {}
    assert not stale_part.exists() and not stale_diag.exists()
    assert _rec(env)["A_sha256"] == wp2.file_sha256(env.e2 / "A.npy")
    assert _rec(env)["A_regenerated_matches"] is True


def test_wp2_e2_resume_rejects_altered_A_or_part(env):
    _crash(env)
    _use(env, Pilot())
    A_path, part = env.e2 / "A.npy", env.e2 / "parts" / "level1__v00.json"
    original = A_path.read_bytes()
    A_path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(SystemExit, match="A.npy"):
        env.mod.main(["--role", "dry", "--resume"])
    A_path.write_bytes(original)
    part_text = part.read_text(encoding="utf-8")
    obj = json.loads(part_text)
    obj["value"][0]["solve_D"] = 1
    part.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(SystemExit, match="level1__v00"):
        env.mod.main(["--role", "dry", "--resume"])
    obj = json.loads(part_text)
    obj["A_sha256"] = "0" * 64
    wp2.atomic_json(part, obj, indent=None)
    manifest_path = env.e2 / "parts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["parts/level1__v00.json"] = wp2.file_sha256(part)
    wp2.atomic_json(manifest_path, manifest)
    with pytest.raises(SystemExit, match="A_sha256"):
        env.mod.main(["--role", "dry", "--resume"])
    assert env.pilot.calls == []


def test_wp2_e2_resume_drops_unlisted_part(env):
    _crash(env)
    unlisted = env.e2 / "parts" / "L06__B.json"
    wp2.atomic_json(unlisted, {"key": "L06/B", "A_sha256": _rec(env)["A_sha256"], "value": [0] * N,
                               "technical": {"seconds": 9.0, "diag_seconds": 0.0, "code_mismatch": 0}})
    pilot = _use(env, Pilot())
    env.mod.main(["--role", "dry", "--resume"])
    assert set(pilot.calls[0]["done"]) == {"base", "level1/v00"}
    assert json.loads(unlisted.read_text(encoding="utf-8"))["value"] == [1] * N
    assert _rec(env)["valid"] is True


def test_wp2_e2_dry_force_clears_stale_artifacts(env):
    env.mod.main(["--role", "dry"])
    old = env.e2 / "parts" / "old.json"
    old.write_text("{}", encoding="utf-8")
    old_diag = env.e2 / "diag" / "old.npz"
    old_diag.write_text("x", encoding="utf-8")
    pilot = _use(env, Pilot())
    env.mod.main(["--role", "dry", "--force"])
    assert pilot.calls[0]["done"] == {} and env.clean == [N, N]
    assert not old.exists() and not old_diag.exists()
    assert _rec(env)["complete"] is True


def test_wp2_e2_identity_failure_invalidates_record(env, capsys):
    _use(env, Pilot(sham_b=1))
    with pytest.raises(SystemExit) as e:
        env.mod.main(["--role", "dry"])
    assert e.value.code == 3
    rec = _rec(env)
    assert rec["complete"] is True and rec["valid"] is False and rec["status"] == "identity-failure"
    assert rec["sham_mismatch"]["levels_B"]["6"] == 1
    for p in (env.raw / "e2.json", env.e2 / "A.npy", env.e2 / "parts", env.e2 / "diag"):
        assert p.exists()
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["status"] == "identity-failure" and line["valid"] is False


def test_wp2_e2_code_mismatch_with_equal_solve_is_identity_failure(env):
    _use(env, Pilot(mismatch={"L06/B": 1}))
    with pytest.raises(SystemExit) as e:
        env.mod.main(["--role", "dry"])
    assert e.value.code == 3
    rec = _rec(env)
    assert rec["sham_mismatch"] == {"level1_B1": 0, "levels_B": {"6": 0}}
    assert rec["code_mismatch"]["levels_B"]["6"] == 1
    assert rec["valid"] is False and rec["status"] == "identity-failure"


def test_wp2_e2_parts_carry_timings_and_counts(env):
    _crash(env, mismatch={"level1/v00": 2})
    for i, name in enumerate(["base", "level1__v00"]):
        part = json.loads((env.e2 / "parts" / f"{name}.json").read_text(encoding="utf-8"))
        assert part["technical"] == {"seconds": 1.0 + i, "diag_seconds": 0.25 * i,
                                     "code_mismatch": 2 if i == 1 else 0}
        assert part["A_sha256"] == _rec(env)["A_sha256"]
    _use(env, Pilot())
    with pytest.raises(SystemExit) as e:
        env.mod.main(["--role", "dry", "--resume"])
    assert e.value.code == 3
    raw = json.loads((env.raw / "e2.json").read_text(encoding="utf-8"))
    assert raw["stage_seconds"] == {k: {"seconds": 1.0 + i, "diag_seconds": 0.25 * i} for i, k in enumerate(KEYS)}
    assert raw["code_mismatch"] == {"level1_B1": 0, "levels_B": {"6": 0}, "level1_noop_D": 2}
    assert _rec(env)["code_mismatch"] == raw["code_mismatch"]


def test_wp2_e2_test_role_hash_mismatch_exits_before_model(env, tmp_path):
    d = tmp_path / "test"
    d.mkdir()
    ids = ["t0", "t1", "t2"]
    p = np.zeros((3, 81), np.uint8)
    (d / "ids.json").write_text(json.dumps(ids), encoding="utf-8")
    np.save(d / "puzzles.npy", p)
    np.save(d / "solutions.npy", p + 1)
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"count": 3, "ids": ids, "sha256": {
        "ids": subsets.sha256_ids(ids), "puzzles": subsets.sha256_array(p),
        "solutions": subsets.sha256_array(p + 1)}}), encoding="utf-8")
    p[0, 0] = 5
    np.save(d / "puzzles.npy", p)
    env.mp.setattr(wp2, "verify_test_data", functools.partial(wp2.verify_test_data, d, lock))
    env.mp.setattr(env.mod, "load_model", lambda d: pytest.fail("model loaded before TEST verification"))
    with pytest.raises(SystemExit, match="puzzles"):
        env.mod.main(["--role", "test"])
    assert env.order == []


def test_wp2_e2_freqs_file_hash_checked(env):
    env.mod.FREQS.write_text(env.mod.FREQS.read_text(encoding="utf-8") + " ", encoding="utf-8")
    env.mp.setattr(env.mod, "load_model", lambda d: pytest.fail("model loaded before the freqs check"))
    with pytest.raises(SystemExit, match="cal_freqs"):
        env.mod.main(["--role", "dry"])
    assert env.order == [] and not env.record.exists()


def test_wp2_e2_stdout_is_technical_only(env, capsys):
    env.mod.main(["--role", "dry"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines
    for line in lines:
        assert set(json.loads(line)) <= set(wp2.TECHNICAL_KEYS)


# --- TEST role ------------------------------------------------------------------------------

def _freeze_for_test(env, tmp_path):
    """Valid dry record of the runner plus a passing dry check, so the TEST guard passes; toy TEST data."""
    env.mod.main(["--role", "dry"])
    compared = tmp_path / "experiments" / "wp2" / "dry" / "compare.json"
    compared.write_text("{}\n", encoding="utf-8")
    probe = tmp_path / "runs" / "e3prep" / "probe_val" / "ids.json"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("[]\n", encoding="utf-8")
    rel = lambda p: p.relative_to(tmp_path).as_posix()  # noqa: E731
    snap = {"dry_records": {rel(env.record): wp2.file_sha256(env.record)},
            "compared": {rel(compared): wp2.file_sha256(compared)},
            "probe_inputs": {rel(probe): wp2.file_sha256(probe)}}
    wp2.atomic_json(wp2.DRY_CHECK, {"technical_success": True, "code": {"commit": TAG}, "snapshot": snap})
    d = tmp_path / "test"
    d.mkdir()
    ids = [f"t{i}" for i in range(N)]
    rng = np.random.default_rng(2)
    p, s = rng.integers(0, 10, (N, 81)).astype(np.uint8), rng.integers(1, 10, (N, 81)).astype(np.uint8)
    (d / "ids.json").write_text(json.dumps(ids), encoding="utf-8")
    np.save(d / "puzzles.npy", p)
    np.save(d / "solutions.npy", s)
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"count": N, "ids": ids, "sha256": {
        "ids": subsets.sha256_ids(ids), "puzzles": subsets.sha256_array(p),
        "solutions": subsets.sha256_array(s)}}), encoding="utf-8")
    env.mp.setattr(wp2, "verify_test_data", functools.partial(wp2.verify_test_data, d, lock))
    exp, raw = tmp_path / "experiments" / "wp2" / "test", tmp_path / "runs" / "wp2" / "test"
    env.record, env.raw, env.e2 = exp / "runs" / "e2.json", raw, raw / "e2"
    env.clean.clear()
    return ids, p, s


def _files(root):
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def test_wp2_e2_test_role_resume_ignores_unlisted_part(env, tmp_path):
    ids, p, s = _freeze_for_test(env, tmp_path)
    _use(env, Pilot(fail_after=2))
    with pytest.raises(RuntimeError, match="simulated crash"):
        env.mod.main(["--role", "test"])
    stale = env.e2 / "parts" / "L06__B.json"
    stale_obj = {"key": "L06/B", "A_sha256": _rec(env)["A_sha256"], "value": [0] * N,
                 "technical": {"seconds": 9.0, "diag_seconds": 0.0, "code_mismatch": 7}}
    wp2.atomic_json(stale, stale_obj, indent=None)
    before = _files(env.raw)
    pilot = _use(env, Pilot())
    env.mod.main(["--role", "test", "--resume"])
    assert set(pilot.calls[0]["done"]) == {"base", "level1/v00"}
    assert before <= _files(env.raw)  # nothing deleted
    part = json.loads(stale.read_text(encoding="utf-8"))
    assert part["value"] == [1] * N and part["technical"]["code_mismatch"] == 0  # overwritten, not read
    expected = Pilot()(SimpleNamespace(levels=(1, 2)), p, s, ids, frozen_freqs={1: 0, 2: 0, 6: 0, 11: 0},
                       A=torch.zeros(1), done={}, on_stage=lambda *a: None)
    raw = json.loads((env.raw / "e2.json").read_text(encoding="utf-8"))
    assert {k: raw[k] for k in expected} == expected
    assert raw["code_mismatch"] == {"level1_B1": 0, "levels_B": {"6": 0}, "level1_noop_D": 0}
    assert raw["note"] is None and raw["role"] == "test" and raw["ids"] == ids
    rec = _rec(env)
    assert rec["complete"] is True and rec["valid"] is True and rec["status"] == "valid"
    assert env.clean == [N]


def test_wp2_e2_test_role_fresh_start_over_existing_outputs_refused(env, tmp_path):
    _freeze_for_test(env, tmp_path)
    leftover = env.e2 / "A.npy"
    leftover.parent.mkdir(parents=True, exist_ok=True)
    np.save(leftover, np.zeros((N, 3), np.int64))
    content, n_calls = leftover.read_bytes(), len(env.pilot.calls)
    env.mp.setattr(env.mod, "load_model", lambda d: pytest.fail("model loaded over existing TEST outputs"))
    with pytest.raises(SystemExit, match="single-look"):
        env.mod.main(["--role", "test"])
    assert leftover.read_bytes() == content and len(env.pilot.calls) == n_calls
    rec = _rec(env)
    assert rec["complete"] is False
    assert "outputs_started" not in rec  # the refused attempt never earned the resume marker

    # A later --resume must not treat that leftover (possibly a complete, valid prior run whose
    # record was separately lost, e.g. to `git clean`) as this run's own partial state: it must
    # not regenerate A, rerun any stage, or overwrite A.npy/parts/diag.
    with pytest.raises(SystemExit, match="outputs_started"):
        env.mod.main(["--role", "test", "--resume"])
    assert leftover.read_bytes() == content and len(env.pilot.calls) == n_calls
    assert _rec(env)["complete"] is False

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rec(pid, level, dose, seed, D, eligible=True, policy="frequency"):
    return {"puzzle_id": pid, "level": level, "policy": policy, "dose": dose, "seed": seed,
            "eligible": eligible, "solve_A": 1, "solve_B": 1, "solve_C": 1, "solve_D": D,
            "well_formed_C": True, "well_formed_D": True, "tv": 0.1 * level, "tv_empty": 0.1,
            "hamming_CA": 0, "hamming_CA_empty": 0, "latent": 0.5, "codebook_rms": 1.0, "requant_ratio": 0.2,
            "downstream_changes_D": 0}


def _l1(pid, v, w, C, D):
    return {"puzzle_id": pid, "value": v, "w_frequency": w, "w_uniform": w, "solve_C": C, "solve_D": D,
            "well_formed_C": True, "well_formed_D": True, "tv": 0.01, "tv_empty": 0.01, "hamming_CA": 0,
            "hamming_CA_empty": 0, "latent": 0.1, "codebook_rms": 1.0, "requant_ratio": 0.1, "downstream_changes_D": 0}


def _toy_pilot2_out():
    records = []
    for s, d in enumerate([0, 1, 1]):
        records.append(_rec("p1", 11, 1, s, d))
        records.append(_rec("p2", 11, 1, s, 1))
    for s in range(3):
        records += [_rec("p1", 2, 1, s, 1), _rec("p2", 2, 1, s, 1)]
    return {
        "freqs_level1": [1 / 16] * 16,
        "base": [{"puzzle_id": "p1", "solve_A": 1, "solve_B1": 1}, {"puzzle_id": "p2", "solve_A": 1, "solve_B1": 1}],
        "level1": [_l1("p1", 1, 0.75, 0, 0), _l1("p1", 2, 0.25, 0, 1), _l1("p2", 1, 1.0, 1, 1)],
        "records": records,
    }


def _ci(estimate=0.0, lo=-0.1, hi=0.1, method="bootstrap", n=25, n_nonzero=25):
    return {"estimate": estimate, "method": method, "ci": [lo, hi], "n": n, "n_nonzero": n_nonzero}


def _family(**kwargs):
    return {"level": 1 - 0.05 / 3, **_ci(**kwargs)}


def _minimal_summary():
    return {
        "n_cal": 300,
        "seconds": 3600.0,
        "contrasts": {
            "theta2": {"frequency": {"estimate": 0.0, "ci95": _ci(), "family": _family(method="bound")},
                       "uniform": {"estimate": 0.0, "ci95": _ci(), "family": None}},
            "theta_comp": {"frequency": {"estimate": 0.0, "ci95": _ci(), "family": _family()},
                           "uniform": {"estimate": 0.0, "ci95": _ci(), "family": None}},
            "theta2_prime": {"frequency": {"estimate": 0.0, "ci95": _ci(), "family": None,
                                            "tost90": _ci(lo=-0.02, hi=0.02, method="bootstrap")},
                              "uniform": {"estimate": 0.0, "ci95": _ci(), "family": None,
                                          "tost90": _ci(lo=-0.02, hi=0.02)}},
        },
        "equivalence_tost": True,
        "sham_mismatch": {"level1_B1": 1, "levels_B": {"2": 0, "6": 0, "11": 2}},
        "auc": {
            "6-11": {"auc_a": 0.1, "auc_b": 0.2, "range": (0.0, 1.0), "reason": None},
            "2-11": {"auc_a": None, "auc_b": None, "range": None, "reason": "fewer than two distinct damage values"},
        },
        "configurations": [
            {"level": 11, "policy": "frequency", "dose": 1, "n_records": 10, "excluded_share": 0.1,
             "solve_mean": {"A": 0.9, "B": 0.9, "C": 0.5, "D": 0.4},
             "format_error_share": {"C": 0.0, "D": 0.0},
             "quantiles": {"tv": [0.0, 0.1, 0.2, 0.3, 0.4]}},
        ],
    }


def test_guard_refuses_when_summary_exists(tmp_path, monkeypatch):
    mod = _load("e2_pilot2")
    monkeypatch.setattr(mod, "OUT", tmp_path)
    (tmp_path / "summary.json").write_text("{}")
    with pytest.raises(SystemExit):
        mod.guard(force=False)
    mod.guard(force=True)


def test_write_report_utf8(tmp_path):
    mod = _load("e2_pilot2")
    mod.write_report(_minimal_summary(), tmp_path / "r.md")
    text = (tmp_path / "r.md").read_bytes().decode("utf-8")
    assert "θ₂" in text and "Non-confirmatory" in text
    assert "Sham mismatch" in text and "B1≠A 1" in text and "L11 2" in text


def test_from_raw_rebuilds_summary_and_respects_guard(tmp_path, monkeypatch):
    mod = _load("e2_pilot2")
    raw = dict(_toy_pilot2_out(), date="2026-11-10", n_cal=2, seconds=7200.0, environment={"git": "x"})
    (tmp_path / "pilot2.json").write_text(json.dumps(raw))
    monkeypatch.setattr(mod, "RAW", tmp_path / "pilot2.json")
    monkeypatch.setattr(mod, "OUT", tmp_path / "out")
    for name in ("environment_record", "assert_generator_frozen", "generate_subset", "load_model", "run_pilot2"):
        monkeypatch.setattr(mod, name, lambda *a, _n=name, **k: pytest.fail(f"--from-raw must not call {_n}"))
    monkeypatch.setattr(mod.sys, "argv", ["e2_pilot2.py", "--from-raw"])
    mod.main()
    s = json.loads((tmp_path / "out" / "summary.json").read_text(encoding="utf-8"))
    assert s["seconds"] == 7200.0 and s["n_cal"] == 2 and s["environment"] == {"git": "x"}
    assert s["date"] == "2026-11-10" and "contrasts" in s
    assert "Non-confirmatory" in (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
    with pytest.raises(SystemExit):
        mod.main()
    monkeypatch.setattr(mod.sys, "argv", ["e2_pilot2.py", "--from-raw", "--force"])
    mod.main()


def test_e2_sample_size_reads_pilot2_and_writes_output(tmp_path, monkeypatch):
    mod = _load("e2_sample_size")
    raw = tmp_path / "pilot2.json"
    out_path = tmp_path / "sample_size_e2.json"
    raw.write_text(json.dumps(_toy_pilot2_out()))
    monkeypatch.setattr(mod, "RAW", raw)
    monkeypatch.setattr(mod, "OUT", out_path)

    calls = {}

    def fake_e2_sample_size(values, **kwargs):
        calls["values"] = values
        return {"max_rounded": 100, "notes": {}}

    monkeypatch.setattr(mod, "e2_sample_size", fake_e2_sample_size)
    mod.main()

    assert set(calls["values"]) == {"theta2", "theta_comp", "theta2_prime"}
    assert json.loads(out_path.read_text(encoding="utf-8")) == {"max_rounded": 100, "notes": {}}

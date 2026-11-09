import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _script():
    spec = importlib.util.spec_from_file_location("wp1_pilot", ROOT / "scripts" / "wp1_pilot.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_write_report_is_utf8(tmp_path):
    summary = {
        "seconds": 3600.0,
        "theta2": {"estimate": 0.0, "ci95": [0.0, 0.0], "n_puzzles": 1},
        "theta_comp_level2": {"estimate": 0.0, "ci95": [0.0, 0.0], "n_puzzles": 1},
        "dose_overlap": {"levels_2_11_overlap": True},
        "by_config": {},
    }
    path = tmp_path / "pilot_report.md"
    _script().write_report(summary, path)
    assert "θ₂" in path.read_bytes().decode("utf-8")

import copy
import re
import json
from pathlib import Path

import pytest

from ncm_sudoku import wp4tables as t

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def results():
    return json.loads((ROOT / "experiments/wp2/test/results.json").read_text(encoding="utf-8"))


def body_rows(tex):
    body = tex.split("\\midrule", 1)[1].split("\\bottomrule", 1)[0]
    return body.count("\\\\")


def check_shape(tex, rows):
    assert tex.startswith("\\begin{tabular}") and tex.endswith("\\end{tabular}\n")
    assert "\\toprule" in tex
    assert re.search(r"\b(None|nan|inf)\b", tex) is None
    assert body_rows(tex) == rows


def test_primary_table(results):
    tex = t.primary_table(results)
    check_shape(tex, 3)
    h2 = next(r for r in results["readings"] if r["hypothesis"] == "H2")
    assert t.escape(h2["does_not_follow"]) in tex
    assert "\\ensuremath{-}11.1" in tex


def test_e3_matrix_table(results):
    check_shape(t.e3_matrix_table(results), 22)


def test_e2_dose_table(results):
    tex = t.e2_dose_table(results)
    check_shape(tex, 28)
    assert "enumerated" in tex


def test_e1_table(results):
    tex = t.e1_table(results)
    assert tex.startswith("\\begin{tabular}") and "None" not in tex and body_rows(tex) >= 8


def test_equivariance_table(results):
    check_shape(t.equivariance_table(results), 3)


def test_deviations_table_reads_ids_from_decisions():
    tex = t.deviations_table(ROOT / "DECISIONS.md")
    check_shape(tex, len(t.DEVIATIONS))
    for did in ("D78", "D79", "D81", "D82", "D84"):
        assert did in tex


def test_deviations_table_missing_id_raises(tmp_path):
    f = tmp_path / "DECISIONS.md"
    f.write_text("| D78 | x |\n")
    with pytest.raises(KeyError, match="D79"):
        t.deviations_table(f)


def test_escape_special_characters():
    s = t.escape("50% & a_b {x} #1 ~ ^ \\ ± θ₂′ − ≈")
    assert s == (
        "50\\% \\& a\\_b \\{x\\} \\#1 \\textasciitilde{} \\textasciicircum{} \\textbackslash{} "
        "$\\pm$ $\\theta_2'$ $-$ $\\approx$"
    )


def test_missing_reading_raises(results):
    broken = copy.deepcopy(results)
    broken["readings"] = [r for r in broken["readings"] if r["hypothesis"] != "H3"]
    with pytest.raises(KeyError, match="H3"):
        t.primary_table(broken)


def test_missing_interval_names_the_path(results):
    broken = copy.deepcopy(results)
    broken["primary"]["H3"]["family"] = None
    with pytest.raises(KeyError, match="primary.H3.family"):
        t.primary_table(broken)


def test_missing_brier_is_an_error_not_a_dash(results):
    broken = copy.deepcopy(results)
    broken["tables"]["e3_main"][0]["brier"] = None
    with pytest.raises((KeyError, ValueError), match="brier"):
        t.e3_matrix_table(broken)

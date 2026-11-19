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


def test_summary_table(results):
    tex = t.summary_table(results)
    check_shape(tex, 5)
    assert r"\ensuremath{-}11.1" in tex and "[0.0025, 0.0033]" in tex
    assert "5.0 pp" in tex and "3.0 pp" in tex


def test_readings_table_has_every_triggered_row(results):
    tex = t.readings_table(results)
    triggered = [r for r in results["readings"] if r["row"]]
    check_shape(tex, len(triggered))
    assert len(triggered) == 7
    for r in triggered:
        assert t.escape(r["claim"]) in tex and t.escape(r["does_not_follow"]) in tex


def test_secondary_table(results):
    tex = t.secondary_table(results)
    check_shape(tex, len(t.SECONDARY_ROWS))
    assert "0.0636" in tex  # macro F1 of the primary probe


def test_depth_table(results):
    tex = t.depth_table(results)
    check_shape(tex, 5)
    assert "2842" in tex and "0.0014" in tex  # stuck cells; projected raw input


def test_levels_table(results):
    check_shape(t.levels_table(results), 3)


def test_e2_diagnostics_table(results):
    check_shape(t.e2_diagnostics_table(results), 28)


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
    tex = t.equivariance_table(results)
    check_shape(tex, 3)
    assert "full group" in tex


def test_deviations_table_reads_ids_from_decisions():
    tex = t.deviations_table(ROOT / "DECISIONS.md")
    check_shape(tex, len(t.DEVIATIONS))
    for did in ("D77", "D78", "D79", "D81, D82", "D84"):
        assert did in tex
    assert "not evaluated" in tex


def test_deviations_table_missing_id_raises(tmp_path):
    f = tmp_path / "DECISIONS.md"
    f.write_text("| D77 | x |\n| D78 | x |\n")
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
        t.readings_table(broken)


def test_missing_interval_names_the_path(results):
    broken = copy.deepcopy(results)
    broken["primary"]["H3"]["family"] = None
    with pytest.raises(KeyError, match="primary.H3.family"):
        t.summary_table(broken)


def test_missing_brier_is_an_error_not_a_dash(results):
    broken = copy.deepcopy(results)
    broken["tables"]["e3_main"][0]["brier"] = None
    with pytest.raises((KeyError, ValueError), match="brier"):
        t.e3_matrix_table(broken)


def test_e2_replacement_table(results):
    tex = t.e2_replacement_table(results)
    check_shape(tex, 28)
    assert "0.0089" in tex and "0.0000098" in tex  # level-1 and level-11 median replacement probability
    row = next(line for line in tex.splitlines() if line.startswith("2 & frequency & 2 &"))
    assert "0.52" in row and "0.74" not in row  # registered per-position RMS, not the summed norm


def test_secondary_table_reports_hidden_only(results):
    tex = t.secondary_table(results)
    assert "0.0074" in tex and "0.0382" in tex


def test_per_digit_f1_table(results):
    tex = t.per_digit_f1_table(results)
    check_shape(tex, 2)
    assert "0.0700" in tex  # digit 1 of the primary probe


def test_deviations_mention_hidden_single_items():
    tex = t.deviations_table(ROOT / "DECISIONS.md")
    assert "(puzzle, unit, digit, cell)" in tex


def test_readings_table_uses_the_tmlr_text_width(results):
    # TMLR text width 6.5 in (16.5 cm); 8 tabcolsep of 6 pt take about 1.7 cm, so the p-columns may use up to 14.8 cm.
    import re

    widths = [float(w) for w in re.findall(r"p\{([0-9.]+)cm\}", t.readings_table(results).split("\n", 1)[0])]
    assert len(widths) == 4
    assert 14.0 <= sum(widths) <= 14.8

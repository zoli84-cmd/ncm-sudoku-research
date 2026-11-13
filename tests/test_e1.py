import pytest

from conftest import needs_model
from ncm_sudoku.e1 import e1_records, e1_summary, e1_table


@needs_model
@pytest.mark.slow
def test_e1_summary_small(model, released):
    puzzles, sols = released
    r = e1_summary(model, puzzles[:4], sols[:4], batch_size=4)
    assert r["n"] == 4
    assert set(r) >= {"teacher", "generated", "per_level", "hamming", "n"}
    assert len(r["per_level"]) == 12 and r["per_level"][0]["level"] == 1
    assert r["per_level"][-1]["solve"] == pytest.approx(r["generated"]["solve"])
    assert r["teacher"]["exact_share"] == 1.0
    for row in r["per_level"]:
        assert 0.0 <= row["code_agreement"] <= 1.0


@needs_model
@pytest.mark.slow
def test_e1_table_agrees_with_e1_summary(model, released):
    p, s = released[0][:4], released[1][:4]
    t = e1_table(e1_records(model, p, s, [str(i) for i in range(4)], batch_size=4))
    ref = e1_summary(model, p, s, batch_size=4)
    assert t["generated"]["format_error"] == 0  # precondition for comparing Hamming with e1_summary
    assert t["generated"]["solve"] == pytest.approx(ref["generated"]["solve"])
    assert len(t["per_level"]) == len(ref["per_level"])
    for a, b in zip(t["per_level"], ref["per_level"]):  # pytest.approx does not accept a list of dicts
        assert a == pytest.approx(b)
    assert t["hamming"]["token_mean"] == pytest.approx(ref["hamming"]["token_mean"])
    assert t["hamming"]["cell_mean"] == pytest.approx(ref["hamming"]["cell_mean"])
    assert t["teacher"]["exact_share"] == ref["teacher"]["exact_share"]
    assert 0 <= t["official_exact_share"] <= 1


def _record(**over):
    base = {
        "puzzle_id": "p0", "official_exact": True, "well_formed": True, "solve": True, "valid_grid": True,
        "all_clues_preserved": True, "clue_preservation": 1.0, "cell_acc_all": 1.0, "cell_acc_empty": 1.0,
        "constraint_violations": 2, "reference_match": True, "format_error": False,
        "token_hamming": 0.0, "cell_hamming": 0.1, "cell_hamming_empty": 0.2,
        "teacher_exact": True, "teacher_cell_acc_all": 1.0, "teacher_solve": True,
        "per_level": [{"level": lv, "code_agreement": 1.0, "solve": True, "cell_acc_all": 1.0,
                       "cell_acc_empty": 1.0, "format_error": False} for lv in range(1, 13)],
    }
    base.update(over)
    return base


def test_e1_table_counts_format_errors_and_violations():
    good = _record(constraint_violations=2)
    bad = _record(puzzle_id="p1", well_formed=False, solve=False, valid_grid=False, all_clues_preserved=False,
                  constraint_violations=None, reference_match=False, format_error=True)
    t = e1_table([good, bad])
    assert t["generated"]["format_error"] == 0.5 and t["generated"]["mean_constraint_violations_well_formed"] == 2.0


def test_e1_table_hamming_skips_format_errors_and_uses_empty_cells():
    good = _record(cell_hamming=0.2, cell_hamming_empty=0.4)
    bad = _record(puzzle_id="p1", well_formed=False, solve=False, valid_grid=False, all_clues_preserved=False,
                  constraint_violations=None, reference_match=False, format_error=True,
                  cell_hamming=None, cell_hamming_empty=None)
    t = e1_table([good, bad])
    assert t["hamming"]["n_cell_hamming"] == 1
    assert t["hamming"]["cell_mean"] == pytest.approx(0.2)
    assert t["hamming"]["cell_empty_mean"] == pytest.approx(0.4)

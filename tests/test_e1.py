import pytest

from conftest import needs_model
from ncm_sudoku.e1 import e1_summary

pytestmark = [needs_model, pytest.mark.slow]


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

import pytest

from ncm_sudoku.grid import encode_solution_tokens
from ncm_sudoku.official import decode_string, official_exact
from sudoku_cases import S

REF = decode_string(encode_solution_tokens(S))


def _one_wrong():
    t = encode_solution_tokens(S)
    t[0] = t[0] % 9 + 1
    return decode_string(t)


def test_decode_string():
    assert REF.count("|") == 8 and "<BOS>" not in REF
    assert len(REF) == 89
    assert decode_string([11, 0, 5, 11]) == "_5"


def test_identical():
    r = official_exact([REF], [REF])
    assert r["solved_pct"] == 100.0 and r["solved_n"] == 1 and r["n"] == 1
    assert r["cell_pct"] == 100.0 and r["valid_pct"] == 100.0


def test_one_wrong_digit():
    r = official_exact([_one_wrong()], [REF])
    assert r["solved_pct"] == 0.0
    assert r["cell_pct"] == pytest.approx(100.0 * 80 / 81)
    assert r["valid_pct"] == 0.0


def test_truncated_uses_shorter_zip():
    hyp = REF[:49]  # first five rows incl. separators -> 45 cells
    r = official_exact([hyp], [REF])
    assert r["cell_pct"] == pytest.approx(100.0)  # upstream behaviour: denominator shrinks to 45
    assert r["solved_pct"] == 0.0 and r["valid_pct"] == 0.0


def test_blank_not_valid():
    hyp = "_" + REF[1:]
    assert official_exact([hyp], [REF])["valid_pct"] == 0.0


def test_empty_hyp_cell_zero():
    r = official_exact(["", REF], [REF, REF])
    assert r["cell_pct"] == pytest.approx(50.0)

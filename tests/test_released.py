import hashlib
import json
import pickle
from pathlib import Path

import numpy as np
import pytest

from ncm_sudoku.dlx import dlx_count_solutions
from ncm_sudoku.released import UnsafePickleError, load_released, safe_load_pickle
from ncm_sudoku.solve import check_puzzle, count_solutions
from ncm_sudoku.validate import count_violations

ROOT = Path(__file__).resolve().parents[1]
HARD = ROOT / "data" / "released" / "sudoku" / "hard"
PROVENANCE = ROOT / "experiments" / "provenance" / "released_data.json"
needs_data = pytest.mark.skipif(not HARD.exists(), reason="released data not downloaded")


def test_safe_unpickler_rejects_global(tmp_path):
    p = tmp_path / "evil.pickle"
    p.write_bytes(b"cos\nsystem\n(S'echo pwned'\ntR.")
    with pytest.raises(UnsafePickleError):
        safe_load_pickle(p)


def test_safe_unpickler_accepts_plain(tmp_path):
    p = tmp_path / "plain.pickle"
    p.write_bytes(pickle.dumps([[1, 2], [3]], protocol=4))
    assert safe_load_pickle(p) == [[1, 2], [3]]


def test_load_rejects_malformed_tokens(tmp_path):
    (tmp_path / "puzzles.pickle").write_bytes(pickle.dumps([[11] + [0] * 88 + [11]]))
    (tmp_path / "solutions.pickle").write_bytes(pickle.dumps([[1] * 89]))
    with pytest.raises(ValueError):
        load_released(tmp_path)


@needs_data
def test_released_hard():
    puzzles, solutions = load_released(HARD)
    assert puzzles.shape == (2000, 81) and solutions.shape == (2000, 81)
    assert puzzles.dtype == np.int8
    assert ((puzzles != 0).sum(axis=1) == 30).all()
    for p, s in zip(puzzles, solutions):
        assert check_puzzle(p).consistent
        clues = p != 0
        assert np.array_equal(p[clues], s[clues])
        assert count_violations(s) == 0
    record = json.loads(PROVENANCE.read_text())["hard"]["files"]
    for name in ("puzzles.pickle", "solutions.pickle"):
        digest = hashlib.sha256((HARD / name).read_bytes()).hexdigest()
        assert digest == record[f"sudoku/hard/{name}"]["sha256"]


@needs_data
@pytest.mark.slow
def test_released_unique_sample():
    puzzles, _ = load_released(HARD)
    for p in puzzles[:200]:
        assert count_solutions(p) == 1
        assert dlx_count_solutions(p) == 1

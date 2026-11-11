import numpy as np

from ncm_sudoku.generate import generate_many
from ncm_sudoku.grid import UNITS
from ncm_sudoku.symmetry import (
    Symmetry,
    apply_symmetry,
    canonical_form,
    inverse,
    random_symmetry,
    screen_canonical,
    transform_predictions,
)
from sudoku_cases import P, S


def is_valid_solution(g):
    return all(sorted(int(g[c]) for c in unit) == list(range(1, 10)) for unit in UNITS)


def _relabel_first_row(g):
    """Relabel digits so the first row reads 1..9 (an upper bound on the minlex string)."""
    m = np.zeros(10, dtype=np.int64)
    m[g[:9]] = np.arange(1, 10)
    return (ord("0") + m[g]).astype(np.uint8).tobytes()


def test_apply_symmetry_keeps_valid_solution():
    rng = np.random.default_rng(0)
    for _ in range(50):
        g = apply_symmetry(np.asarray(S), random_symmetry(rng))
        assert is_valid_solution(g)


def test_apply_symmetry_keeps_blanks():
    rng = np.random.default_rng(5)
    s = random_symmetry(rng)
    assert (apply_symmetry(np.asarray(P), s) == 0).sum() == (np.asarray(P) == 0).sum()


def test_inverse_roundtrip_grid_and_predictions():
    rng = np.random.default_rng(1)
    for _ in range(10):
        s = random_symmetry(rng)
        g = np.asarray(S)
        assert np.array_equal(apply_symmetry(apply_symmetry(g, s), inverse(s)), g)
        p = rng.random((81, 9))
        assert np.allclose(transform_predictions(transform_predictions(p, s), inverse(s)), p)


def test_transform_predictions_matches_grid_transform():
    rng = np.random.default_rng(2)
    g = np.asarray(S)
    onehot = np.eye(10)[g][:, 1:]
    for _ in range(10):
        s = random_symmetry(rng)
        assert np.array_equal(transform_predictions(onehot, s), np.eye(10)[apply_symmetry(g, s)][:, 1:])


def test_random_symmetry_kinds():
    rng = np.random.default_rng(3)
    d = random_symmetry(rng, "digit")
    assert not d.transpose and d.row_perm == tuple(range(9)) and d.col_perm == tuple(range(9))
    gm = random_symmetry(rng, "geometric")
    assert gm.digit_perm == tuple(range(10))
    assert isinstance(gm, Symmetry)


def test_canonical_invariant_under_random_symmetries():
    rng = np.random.default_rng(4)
    g = np.asarray(S)
    c = canonical_form(g)
    for _ in range(20):
        assert canonical_form(apply_symmetry(g, random_symmetry(rng))) == c


def test_canonical_is_minimal_equivalent_grid():
    rng = np.random.default_rng(6)
    g = np.asarray(S)
    c = canonical_form(g)
    assert len(c) == 81 and c[:9] == b"123456789"
    cg = np.frombuffer(c, dtype=np.uint8).astype(np.int64) - ord("0")
    assert is_valid_solution(cg) and canonical_form(cg) == c
    for _ in range(200):
        assert c <= _relabel_first_row(apply_symmetry(g, random_symmetry(rng)))


def test_canonical_distinguishes_random_grids():
    sols = [p.solution for p in generate_many(20261109, 30)]  # dev seed, never reused for analysis
    assert len({canonical_form(s) for s in sols}) == 30


def test_screen_canonical_finds_classes_and_exact_duplicates():
    pz = generate_many(20261109, 3)
    rng = np.random.default_rng(7)
    released = np.stack([apply_symmetry(pz[0].solution, random_symmetry(rng)), pz[1].solution])
    out = screen_canonical({"dev": pz}, released)
    assert out["n_entries"] == 5
    assert sorted(map(sorted, out["classes"])) == sorted(
        [sorted(["released-0", pz[0].puzzle_id]), sorted(["released-1", pz[1].puzzle_id])]
    )
    assert out["exact_duplicates"] == [["released-1", pz[1].puzzle_id]]

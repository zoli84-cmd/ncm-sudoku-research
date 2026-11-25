import numpy as np

from ncm_sudoku.e5pairs import generate_pair
from ncm_sudoku.e5pilot import scatter, w_auc
from ncm_sudoku.e5probes import candidate_targets


def _d(n=3):
    pairs = [generate_pair(9, i) for i in range(n)]
    puzzles = np.concatenate([np.stack([p.a for p in pairs]), np.stack([p.b for p in pairs])])
    mask, empty = candidate_targets(puzzles)
    return {"n_pairs": n, "mask": mask, "empty": empty, "codes_same_1_6": np.array([True] + [False] * (n - 1))}


def test_w_auc_extremes():
    d = _d()
    assert w_auc(d["mask"].astype(np.float64), d)["overall"] == 1.0
    assert w_auc(1.0 - d["mask"], d)["overall"] == 0.0
    n = d["n_pairs"]
    same = np.concatenate([d["mask"][:n], d["mask"][:n]]).astype(np.float64)  # both members get a's prediction
    res = w_auc(same, d)
    assert res["overall"] == 0.5 and res["n_bits"] > 0
    assert len(res["per_pair"]) == n and res["codes_same"] == 0.5


def test_scatter_places_rows_on_empty_cells():
    empty = np.zeros((2, 81), bool)
    empty[0, 3] = empty[1, 5] = True
    out = scatter(np.arange(18, dtype=float).reshape(2, 9), empty)
    assert out[0, 3, 0] == 0 and out[1, 5, 8] == 17 and np.isnan(out[0, 0, 0])

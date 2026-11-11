"""Whole-layer E3 diagnostic features (plan v3.6 §8.1; D65).

Non-confirmatory planning code on PROBE-TRAIN/PROBE-VAL. §8.1 allows a whole-layer
probe under a separate specification: every probe input gets a representation
projected to the same pre-specified dimension (PCA, k = 256, fitted on PROBE-TRAIN
only), and the raw-input control is reported both projected and unprojected.

Per-cell probe input (the 81-way position one-hot is appended by
`probes.build_inputs`):
- `whole_layer_features`: PCA-k projection of the flattened 81 x F grid state (same
  vector for every cell of the puzzle) || the cell's own state.
- `raw_whole_features`: the 810-d puzzle one-hot, PCA-k projected or unprojected
  (same vector for every cell) || the cell's own one-hot (10).

PCA: centred SVD in float64; components are sign-normalized (largest-|value| entry
positive, first such entry on ties), so a refit on the same data is identical. When
fewer than k components exist (n <= k, toy data only), the remainder is zero-padded so
the projected width is always k.
"""

import numpy as np


def fit_pca(x_tr: np.ndarray, k: int = 256) -> dict:
    """Mean, top-k components [k, D] and the explained-variance share of the top k
    (sum of their squared singular values over the total centred sum of squares)."""
    x = np.array(x_tr, dtype=np.float64).reshape(len(x_tr), -1)  # own copy, centred in place
    mean = x.mean(axis=0)
    x -= mean
    d = x.shape[1]
    _, s, vt = np.linalg.svd(x, full_matrices=False)
    del x
    m = min(k, len(s))
    comp = np.zeros((k, d), dtype=np.float64)
    comp[:m] = vt[:m]
    idx = np.abs(comp[:m]).argmax(axis=1)
    signs = np.sign(comp[np.arange(m), idx])
    signs[signs == 0] = 1.0
    comp[:m] *= signs[:, None]
    total = float((s**2).sum())
    return {
        "mean": mean,
        "components": comp,
        "n_components_fitted": int(m),
        "explained_variance_share": float((s[:m] ** 2).sum() / total) if total > 0 else 1.0,
    }


def project(x: np.ndarray, pca: dict) -> np.ndarray:
    """[n, D] -> [n, k] float32 projection onto the fitted components."""
    x = np.asarray(x, dtype=np.float64).reshape(len(x), -1)
    return ((x - pca["mean"]) @ pca["components"].T).astype(np.float32)


def _with_global(glob: np.ndarray, own: np.ndarray) -> np.ndarray:
    """[n, G] global part broadcast to every cell || [n, 81, F] own part."""
    n = len(own)
    g = np.broadcast_to(np.asarray(glob, np.float32)[:, None, :], (n, 81, glob.shape[1]))
    return np.concatenate([g, np.asarray(own, np.float32)], axis=2)


def whole_layer_features(cell_states: np.ndarray, pca: dict) -> np.ndarray:
    """[n, 81, F] -> [n, 81, k + F]: grid PCA projection || own cell state."""
    states = np.asarray(cell_states, dtype=np.float32)
    return _with_global(project(states.reshape(len(states), -1), pca), states)


def raw_whole(puzzles: np.ndarray) -> np.ndarray:
    """[n, 81] -> [n, 810] float32 puzzle one-hot (10 values per cell, cell-major)."""
    p = np.asarray(puzzles)
    return np.eye(10, dtype=np.float32)[p].reshape(len(p), 810)


def raw_whole_features(puzzles: np.ndarray, pca: dict | None) -> np.ndarray:
    """[n, 81] -> [n, 81, k + 10] (projected by `pca`) or [n, 81, 820] (pca None):
    puzzle one-hot || own one-hot."""
    p = np.asarray(puzzles)
    r = raw_whole(p)
    glob = r if pca is None else project(r, pca)
    return _with_global(glob, np.eye(10, dtype=np.float32)[p])

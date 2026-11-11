"""Cell-relative whole-layer E3 diagnostic features (plan v3.6 §8.1; D65, D66).

Non-confirmatory planning code on PROBE-TRAIN/PROBE-VAL. §8.1 allows a whole-layer
probe under a separate specification: every probe input gets a representation
projected to the same pre-specified dimension, and the raw-input control is reported
both projected and unprojected.

D66 design (replaces the D65(1) whole-grid vector, which a shared linear probe can
only use as a per-puzzle offset): for each cell c, the states of c and its 20 peers
in `e3data` `PEERS[c]` order (`PEER_IDX[c]`, 21 x F) are projected by a PCA fitted on
the empty-cell rows of PROBE-TRAIN only, and the scores are whitened to unit
PROBE-TRAIN standard deviation. Probe input per cell (`whole_layer_features`):
whitened scores || the cell's own state || position one-hot (added by
`probes.build_inputs`). The projected raw control (`raw_projected_features`) is the
whitened PCA of `e3data.raw_features` (own || 20 peer one-hots, 210-d) || position.

PCA (`fit_pca_chunks`): two passes over row chunks (mean, then the centred covariance
accumulated in float64), so the full row matrix is never materialized; `eigh`;
components sorted by decreasing eigenvalue and sign-normalized (largest-|value| entry
positive, first such entry on ties). `scale` = sqrt(eigenvalue), i.e. the population
std of the scores on the fitting rows; zero-variance (relative eigenvalue <= 1e-10)
and zero-padded components (k > D) get scale 1.
"""

from collections.abc import Callable, Iterable

import numpy as np

from ncm_sudoku.e3data import _PEERS_IDX, raw_features

PEER_IDX = np.concatenate([np.arange(81, dtype=np.int64)[:, None], _PEERS_IDX], axis=1)  # (81, 21)
_REL_EPS = 1e-10


def fit_pca_chunks(make_chunks: Callable[[], Iterable[np.ndarray]], k: int = 256) -> dict:
    """PCA from row chunks; `make_chunks()` is called twice and must yield the same
    [m, D] chunks both times. Returns `mean`, `components` [k, D], `scale` [k],
    `n_components_fitted`, `explained_variance_share` (top-k eigenvalues over the
    trace), `n_rows`."""
    n, total = 0, None
    for x in make_chunks():
        x = np.asarray(x, np.float64)
        total = x.sum(axis=0) if total is None else total + x.sum(axis=0)
        n += len(x)
    mean = total / n
    d = len(mean)
    cov = np.zeros((d, d), np.float64)
    for x in make_chunks():
        xc = np.asarray(x, np.float64) - mean
        cov += xc.T @ xc
    cov /= n
    evals, evecs = np.linalg.eigh(cov)
    trace = float(np.trace(cov))
    del cov
    order = np.argsort(evals)[::-1]
    evals = np.clip(evals[order], 0.0, None)
    m = min(k, d)
    top = evecs[:, order[:m]].T  # (m, D)
    signs = np.sign(top[np.arange(m), np.abs(top).argmax(axis=1)])
    signs[signs == 0] = 1.0
    comp = np.zeros((k, d), np.float64)
    comp[:m] = top * signs[:, None]
    scale = np.ones(k, np.float64)
    lam = evals[:m]
    ok = lam > _REL_EPS * max(float(evals[0]), 0.0)
    scale[:m][ok] = np.sqrt(lam[ok])
    return {
        "mean": mean,
        "components": comp,
        "scale": scale,
        "n_components_fitted": int(m),
        "explained_variance_share": float(lam.sum() / trace) if trace > 0 else 1.0,
        "n_rows": int(n),
    }


def _row_chunks(x: np.ndarray, chunk: int):
    x = np.asarray(x).reshape(len(x), -1)
    return lambda: (x[i : i + chunk] for i in range(0, len(x), chunk))


def fit_pca(x: np.ndarray, k: int = 256, chunk: int = 4096) -> dict:
    """`fit_pca_chunks` over the rows of an in-memory [n, D] array."""
    return fit_pca_chunks(_row_chunks(x, chunk), k)


def project(x: np.ndarray, pca: dict, whiten: bool = True) -> np.ndarray:
    """[n, D] -> [n, k] float32 scores (divided by `scale` when `whiten`)."""
    x = np.asarray(x, np.float64).reshape(len(x), -1)
    z = (x - pca["mean"]) @ pca["components"].T
    return (z / pca["scale"] if whiten else z).astype(np.float32)


def variance_share_chunks(make_chunks: Callable[[], Iterable[np.ndarray]], pca: dict) -> float:
    """Variance of the rows captured by the fitted components, centred with the
    fitting mean: sum ||P(x - mean)||^2 / sum ||x - mean||^2."""
    num = den = 0.0
    for x in make_chunks():
        xc = np.asarray(x, np.float64) - pca["mean"]
        num += float(((xc @ pca["components"].T) ** 2).sum())
        den += float((xc**2).sum())
    return num / den if den > 0 else 1.0


def variance_share(x: np.ndarray, pca: dict, chunk: int = 4096) -> float:
    return variance_share_chunks(_row_chunks(x, chunk), pca)


def peer_states(states: np.ndarray) -> np.ndarray:
    """[n, 81, F] -> [n, 81, 21 F]: per cell, its own state then its 20 peers' states."""
    s = np.asarray(states, np.float32)
    return s[:, PEER_IDX, :].reshape(len(s), 81, -1)


def _empty_peer_chunks(states, empty, batch: int):
    empty = np.asarray(empty, bool)
    return lambda: (peer_states(states[i : i + batch])[empty[i : i + batch]] for i in range(0, len(empty), batch))


def fit_cell_pca(states: np.ndarray, empty: np.ndarray, k: int = 256, batch: int = 50) -> dict:
    """PCA of the 21-cell peer states over the empty-cell rows (PROBE-TRAIN), `batch`
    puzzles per chunk (works on read-only memmaps)."""
    return fit_pca_chunks(_empty_peer_chunks(states, empty, batch), k)


def cell_variance_share(states: np.ndarray, empty: np.ndarray, pca: dict, batch: int = 50) -> float:
    """`variance_share` of the empty-cell peer-state rows (e.g. PROBE-VAL)."""
    return variance_share_chunks(_empty_peer_chunks(states, empty, batch), pca)


def whole_layer_features(states: np.ndarray, pca: dict, batch: int = 50) -> np.ndarray:
    """[n, 81, F] -> [n, 81, k + F]: whitened peer-state PCA scores || own state."""
    n, _, f = states.shape
    k = pca["components"].shape[0]
    out = np.empty((n, 81, k + f), np.float32)
    for i in range(0, n, batch):
        s = np.asarray(states[i : i + batch], np.float32)
        b = len(s)
        out[i : i + b, :, :k] = project(peer_states(s).reshape(b * 81, -1), pca).reshape(b, 81, k)
        out[i : i + b, :, k:] = s
    return out


def raw_projected_features(puzzles: np.ndarray, pca: dict) -> np.ndarray:
    """[n, 81] -> [n, 81, k]: whitened PCA scores of `e3data.raw_features` (210-d)."""
    r = raw_features(puzzles)
    return project(r.reshape(-1, r.shape[2]), pca).reshape(len(r), 81, -1)

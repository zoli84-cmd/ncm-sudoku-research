"""Frozen peer order (v3.7 review CARBON-2): the D67-D71 whole-layer results depend on it."""

import hashlib

import numpy as np

from ncm_sudoku import e3data, wholelayer
from ncm_sudoku.grid import PEER_ORDER, PEERS

# SHA-256 of np.asarray(wholelayer.PEER_IDX, dtype=np.int64) C-order bytes (cell, then its 20 peers)
PEER_IDX_SHA256 = "57cc1251a39285a9dc5201f2b0b11d825f3f8850db5b356ab7b8187b4f582e1d"


def test_peer_order_shape_and_sets():
    assert len(PEER_ORDER) == 81
    for c in range(81):
        assert len(PEER_ORDER[c]) == 20 and set(PEER_ORDER[c]) == PEERS[c]
        assert all(isinstance(p, int) for p in PEER_ORDER[c])


def test_peer_idx_hash_is_frozen():
    data = np.asarray(wholelayer.PEER_IDX, dtype=np.int64).tobytes(order="C")
    assert hashlib.sha256(data).hexdigest() == PEER_IDX_SHA256


def test_indices_use_peer_order():
    assert np.array_equal(e3data._PEERS_IDX, np.asarray(PEER_ORDER, dtype=np.int64))
    assert np.array_equal(wholelayer.PEER_IDX[:, 0], np.arange(81)) and np.array_equal(wholelayer.PEER_IDX[:, 1:],
                                                                                         e3data._PEERS_IDX)


def test_raw_features_unchanged_against_frozenset_construction():
    old_idx = np.array([list(PEERS[c]) for c in range(81)], dtype=np.int64)  # pre-change construction

    def old_raw_features(puzzles):
        n = len(puzzles)
        oh = np.eye(10, dtype=np.float32)[puzzles]
        return np.concatenate([oh, oh[:, old_idx, :].reshape(n, 81, 200)], axis=2)

    pz = np.random.default_rng(0).integers(0, 10, (7, 81))
    assert np.array_equal(e3data.raw_features(pz), old_raw_features(pz))

import numpy as np
import pytest

from conftest import needs_model
from ncm_sudoku.e3data import (
    extract,
    extract_streamed,
    labels,
    load_level,
    peer_counts,
    raw_features,
    save_subset,
    surface_features,
)
from ncm_sudoku.grid import PEERS
from ncm_sudoku.labels import candidate_mask
from sudoku_cases import P, S


def test_labels_known_puzzle():
    lab = labels(np.asarray([P]))  # P from tests/sudoku_cases.py
    assert lab["empty"].sum() == int((np.asarray(P) == 0).sum())
    assert (lab["mask"][0][~lab["empty"][0]] == 0).all()
    assert np.array_equal(lab["mask"][0][lab["empty"][0]], candidate_mask(np.asarray(P))[lab["empty"][0]])


def test_raw_features_peer_order():
    f = raw_features(np.asarray([P]))
    c = 0
    peers = list(PEERS[c])
    assert f.shape == (1, 81, 210)
    assert f[0, c, :10].argmax() == P[c]
    assert [f[0, c, 10 + 10 * k : 20 + 10 * k].argmax() for k in range(20)] == [P[q] for q in peers]


def test_peer_counts_match_mask():
    pc = peer_counts(np.asarray([P]))
    lab = labels(np.asarray([P]))
    e = lab["empty"][0]
    assert np.array_equal((pc[0][e] == 0).astype(np.uint8), lab["mask"][0][e])


def test_surface_features_constant_over_cells():
    f = surface_features(np.asarray([P]))
    assert f.shape == (1, 81, 10)
    assert (f[0] == f[0, 0]).all()
    n_clues = int((np.asarray(P) != 0).sum())
    assert f[0, 0, 0] == pytest.approx(n_clues / 81.0)
    assert f[0, 0, 1:].sum() == pytest.approx(n_clues / 81.0)


def test_save_subset_skips_state_files_without_states_key(tmp_path):
    """The path scripts/e3_extract.py relies on: ext has only "solve" (states/teacher
    already written by extract_streamed), so save_subset must not touch L*/T*.npy."""
    puzzles, sols = np.asarray([P, P]), np.asarray([S, S])
    lab = labels(puzzles)
    save_subset(tmp_path, "probe_tiny", ["a", "b"], puzzles, sols, {"solve": np.array([True, False])}, lab)
    out = tmp_path / "probe_tiny"
    assert (out / "ids.json").exists() and (out / "puzzles.npy").exists()
    assert (out / "solve.npy").exists() and (out / "mask.npy").exists()
    assert (out / "empty.npy").exists() and (out / "depth.npy").exists()
    assert not any((out / f"L{lv:02d}.npy").exists() for lv in range(1, 13))
    assert not any((out / f"T{lv:02d}.npy").exists() for lv in (2, 6, 12))


@needs_model
@pytest.mark.slow
def test_extract_shapes(model, released):
    puzzles, sols = released
    ext = extract(model, puzzles[:3], sols[:3], batch=3)
    assert len(ext["states"]) == 12 and ext["states"][5].shape == (3, 81, 256)
    assert set(ext["teacher"]) == {2, 6, 12} and ext["solve"].shape == (3,)


@needs_model
@pytest.mark.slow
def test_extract_streamed_matches_extract(model, released, tmp_path):
    puzzles, sols = released
    ext = extract(model, puzzles[:3], sols[:3], batch=2)
    solve = extract_streamed(model, tmp_path / "probe_stream", puzzles[:3], sols[:3], batch=2)
    # Reopen every file fresh, after extract_streamed has returned: both via load_level's
    # mmap and via a plain (non-mmap) np.load, so the test fails if the write-mode memmap
    # handles were not actually released (closed) on return.
    assert np.array_equal(solve, ext["solve"])
    for lv in range(1, 13):
        assert np.array_equal(load_level(tmp_path, "probe_stream", lv), ext["states"][lv - 1])
        reloaded = np.load(tmp_path / "probe_stream" / f"L{lv:02d}.npy")
        assert np.array_equal(reloaded, ext["states"][lv - 1])
    for lv in (2, 6, 12):
        assert np.array_equal(load_level(tmp_path, "probe_stream", lv, teacher=True), ext["teacher"][lv])
        reloaded_t = np.load(tmp_path / "probe_stream" / f"T{lv:02d}.npy")
        assert np.array_equal(reloaded_t, ext["teacher"][lv])


@needs_model
@pytest.mark.slow
def test_save_and_load_level_roundtrip(model, released, tmp_path):
    puzzles, sols = released
    ext = extract(model, puzzles[:2], sols[:2], batch=2)
    lab = labels(puzzles[:2])
    save_subset(tmp_path, "probe_mini", ["a", "b"], puzzles[:2], sols[:2], ext, lab)
    loaded = load_level(tmp_path, "probe_mini", 6)
    assert np.array_equal(np.asarray(loaded), ext["states"][5])
    loaded_t = load_level(tmp_path, "probe_mini", 2, teacher=True)
    assert np.array_equal(np.asarray(loaded_t), ext["teacher"][2])


@needs_model
@pytest.mark.slow
def test_extract_streamed_releases_mappings_on_return(model, released, tmp_path):
    """On Windows a live memmap locks its file, so the WP2 directory publish
    (`score.tmp` -> `score`) fails while any mapping survives the return. No
    `gc.collect()` here: `extract_streamed` itself must release every mapping."""
    import os

    puzzles, sols = released
    extract_streamed(model, tmp_path / "score.tmp", puzzles[:4], sols[:4], batch=4)
    os.replace(tmp_path / "score.tmp", tmp_path / "score")
    assert (tmp_path / "score" / "T12.npy").exists()

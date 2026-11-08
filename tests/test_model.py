import hashlib
import json
import os
import pickle

import pytest
import torch

from conftest import CKPT_DIR, ROOT, needs_model
from ncm_sudoku.model import _safe_load, level_slices

LEVELS = (1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89)


def test_level_slices():
    sl = level_slices(LEVELS)
    assert [s.stop - s.start for s in sl] == list(LEVELS)
    assert sl[0].start == 0 and sl[-1].stop == 322
    assert all(a.stop == b.start for a, b in zip(sl, sl[1:]))


def test_unsafe_checkpoint_refused(tmp_path):
    p = tmp_path / "evil.pt"
    torch.save({"model": os.system}, p)
    with pytest.raises(pickle.UnpicklingError):
        _safe_load(p)


@needs_model
@pytest.mark.slow
def test_load_model(model):
    assert model.levels == LEVELS
    n_gen = sum(p.numel() for p in model.net.parameters())
    n_tok = sum(p.numel() for p in model.vqvae.parameters())
    assert abs(n_gen - 25.46e6) < 0.01e6
    assert abs(n_tok - 14.90e6) < 0.01e6
    assert not model.net.training and not model.vqvae.training
    assert torch.are_deterministic_algorithms_enabled()


@needs_model
@pytest.mark.slow
def test_checkpoint_hashes():
    record = json.loads((ROOT / "experiments" / "provenance" / "checkpoints.json").read_text())
    for name in ("generator.pt", "tokenizer.pt", "config.yaml"):
        digest = hashlib.sha256((CKPT_DIR / name).read_bytes()).hexdigest()
        assert digest == record["files"][f"sudoku/hard/{name}"]["sha256"]
    assert record["checkpoints_license"] == "MIT" and record["code_license"] == "MIT"

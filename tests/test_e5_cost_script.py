import importlib.util

import pytest
import torch

from conftest import ROOT, needs_model


def _load_script():
    spec = importlib.util.spec_from_file_location("e5_cost", ROOT / "scripts" / "e5_cost.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.slow
@needs_model
def test_capture_is_read_only_and_covers_every_pass(model, released):
    from ncm_sudoku.runner import puzzle_tensor

    mod = _load_script()
    x = puzzle_tensor(released[0][:2])
    plain = mod._generate(model.net, x)
    codes, passes = mod.generate_with_capture(model.net, x)
    assert torch.equal(plain, codes)
    P = model.net.prefix_len
    assert [p[0].shape[1] for p in passes] == [P + n for n in model.levels]
    assert all(len(p) == len(model.net.transformer.blocks) + 1 for p in passes)
    # The prefix attends only to itself, so layer 0 (the embedding) is identical in every pass.
    assert all(torch.equal(p[0][:, :P], passes[0][0][:, :P]) for p in passes)

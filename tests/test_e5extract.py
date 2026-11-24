import numpy as np
import pytest
import torch

from conftest import needs_model


@pytest.mark.slow
@needs_model
def test_capture_pass_keeps_codes_and_extracts_consistent_arrays(model, released):
    from ncm_sudoku.e5extract import LEVEL7_PASS, extract_batch, generate_capture_pass
    from ncm_sudoku.runner import generate_codes, puzzle_tensor

    puzzles, solutions = released[0][:2], released[1][:2]
    plain = generate_codes(model, puzzles, batch_size=2)
    codes, layers = generate_capture_pass(model.net, puzzle_tensor(puzzles))
    assert torch.equal(plain, codes)
    P = model.net.prefix_len
    assert len(layers) == len(model.net.transformer.blocks) + 1
    assert layers[0].shape[1] == P + model.levels[LEVEL7_PASS]

    out = extract_batch(model, puzzles, solutions)
    assert out["prefix_cells"].shape == (2, 9, 81, model.net.config.n_embd)
    assert out["prefix_bos"].shape == (2, 9, model.net.config.n_embd)
    assert out["level7_queries"].shape[2] == model.levels[LEVEL7_PASS]
    assert out["z6"].shape == (2, 81, 256) and out["z6_teacher"].shape == (2, 81, 256)
    assert out["solved"].dtype == bool
    assert np.array_equal(out["codes"], plain.numpy().astype(np.int8))

import numpy as np
import pytest
import torch

from conftest import needs_model
from ncm_sudoku.grid import encode_solution_tokens
from ncm_sudoku.runner import decode_codes, generate_codes, teacher_codes

pytestmark = [needs_model, pytest.mark.slow]


def test_generate_codes_shape(model, released):
    codes = generate_codes(model, released[0][:4])
    assert codes.shape == (4, 322) and codes.dtype == torch.long
    assert int(codes.min()) >= 0 and int(codes.max()) <= 15


def test_generate_deterministic(model, released):
    a = generate_codes(model, released[0][:4])
    b = generate_codes(model, released[0][:4])
    assert torch.equal(a, b)


def test_decode_codes_shape(model, released):
    out = decode_codes(model, generate_codes(model, released[0][:2]))
    assert out.shape == (2, 89)


def test_teacher_reconstruction(model, released):
    sols = released[1][:16]
    out = decode_codes(model, teacher_codes(model, sols))
    expected = torch.tensor(np.array([encode_solution_tokens(s) for s in sols]))
    assert torch.equal(out, expected)

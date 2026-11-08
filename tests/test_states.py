import pytest
import torch

from conftest import needs_model
from ncm_sudoku.model import level_slices
from ncm_sudoku.runner import decode_codes, generate_codes
from ncm_sudoku.states import cell_states, cumulative_states, decode_state, decode_state_logits

pytestmark = [needs_model, pytest.mark.slow]


@pytest.fixture(scope="module")
def codes(model, released):
    return generate_codes(model, released[0][:4])


def test_final_state_matches_upstream(model, codes):
    states = cumulative_states(model, codes)
    assert len(states) == 12 and states[0].shape == (4, 89, 256)
    upstream = model.vqvae.vq.idx_to_zhats(codes, return_zlevels=False)[0][-1]
    assert torch.equal(states[-1], upstream)


def test_state_storage_isolated(model, codes):
    states = cumulative_states(model, codes)
    assert len({s.data_ptr() for s in states}) == 12
    before = states[5].clone()
    states[11].add_(1.0)
    assert torch.equal(states[5], before)


def test_prefix_recomputation(model, codes):
    states = cumulative_states(model, codes)
    end6 = level_slices(model.levels)[5].stop
    assert torch.equal(cumulative_states(model, codes[:, :end6], upto=6)[-1], states[5])


def test_level12_contribution_nonzero_then_unequal(model, codes):
    states = cumulative_states(model, codes)
    if torch.linalg.norm(states[11] - states[10]) > 0:
        assert not torch.equal(states[11], states[10])


def test_decode_state_matches_runner(model, codes):
    states = cumulative_states(model, codes)
    assert torch.equal(decode_state(model, states[-1]), decode_codes(model, codes))


def test_decode_state_logits_shape(model, codes):
    z = cumulative_states(model, codes)[-1]
    logits = decode_state_logits(model, z)
    assert logits.shape == (4, 89, 12)
    assert torch.equal(logits.argmax(-1), decode_state(model, z))


def test_cell_states_shape(model, codes):
    z = cumulative_states(model, codes)[5]
    assert cell_states(z).shape == (4, 81, 256)

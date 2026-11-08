import pytest
import torch

from conftest import needs_model
from ncm_sudoku.intervene import continue_generation, forward_with_intervention, run_branches
from ncm_sudoku.model import level_slices
from ncm_sudoku.runner import generate_codes, puzzle_tensor
from ncm_sudoku.states import cumulative_states

pytestmark = [needs_model, pytest.mark.slow]


@pytest.fixture(scope="module")
def batch(model, released):
    puzzles = released[0][:4]
    prefix = puzzle_tensor(puzzles)
    clean = generate_codes(model, puzzles, batch_size=4)
    return prefix, clean


def _end(model, level):
    return level_slices(model.levels)[level - 1].stop


def test_public_name():
    assert forward_with_intervention is continue_generation


def test_noop_matches_upstream(model, batch):
    prefix, clean = batch
    assert torch.equal(continue_generation(model, prefix, None, 0), clean)


def test_writeback_all_levels(model, batch):
    prefix, clean = batch
    assert torch.equal(continue_generation(model, prefix, clean, 12), clean)


@pytest.mark.parametrize("level", [1, 2, 6, 11])
def test_sham_b_equals_a(model, batch, level):
    prefix, clean = batch
    b = continue_generation(model, prefix, clean[:, : _end(model, level)], level)
    assert torch.equal(b, clean)


@pytest.mark.parametrize("level", [2, 6])
def test_zhat_override_identity(model, batch, level):
    prefix, clean = batch
    z = cumulative_states(model, clean)[level - 1]
    out = continue_generation(model, prefix, clean[:, : _end(model, level)], level, z_hat_override=z)
    assert torch.equal(out, clean)


def test_zhat_override_changes_output(model, batch):
    prefix, clean = batch
    z = cumulative_states(model, clean)[1] + 5.0
    out = continue_generation(model, prefix, clean[:, : _end(model, 2)], 2, z_hat_override=z)
    assert torch.equal(out[:, : _end(model, 2)], clean[:, : _end(model, 2)])
    assert not torch.equal(out[:, _end(model, 2) :], clean[:, _end(model, 2) :])


def _perturb(clean, model, level):
    sl = level_slices(model.levels)[level - 1]
    p = clean[:, sl].clone()
    p[:, 0] = (p[:, 0] + 1) % 16
    return p


def test_branch_c_only_level_slice(model, batch):
    prefix, clean = batch
    level = 6
    br = run_branches(model, prefix, clean, level, _perturb(clean, model, level))
    sl = level_slices(model.levels)[level - 1]
    diff = (br.C != br.A).any(dim=0).nonzero().flatten().tolist()
    assert diff and all(sl.start <= i < sl.stop for i in diff)
    assert torch.equal(br.A, clean) and torch.equal(br.B, clean)


def test_branch_d_prefix_fixed(model, batch):
    prefix, clean = batch
    level = 2
    pert = _perturb(clean, model, level)
    br = run_branches(model, prefix, clean, level, pert)
    sl = level_slices(model.levels)[level - 1]
    assert torch.equal(br.D[:, : sl.start], clean[:, : sl.start])
    assert torch.equal(br.D[:, sl], pert)


def test_run_branches_computes_a(model, batch):
    prefix, clean = batch
    br = run_branches(model, prefix, None, 2, _perturb(clean, model, 2))
    assert torch.equal(br.A, clean)


def test_level_12_rejected(model, batch):
    prefix, clean = batch
    with pytest.raises(ValueError):
        run_branches(model, prefix, clean, 12, clean[:, level_slices(model.levels)[11]])


def test_batch_size_effect_recorded(model, batch, released):
    _, clean = batch
    alone = generate_codes(model, released[0][:1], batch_size=1)
    assert torch.equal(alone[0], clean[0])

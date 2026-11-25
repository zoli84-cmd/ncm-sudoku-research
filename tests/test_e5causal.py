import numpy as np
import pytest
import torch

from conftest import needs_model
from ncm_sudoku.e5causal import (
    DERANGEMENT,
    high_variance_basis,
    norm_matched,
    orthonormal_rows,
    project_step,
    random_basis,
    shuffled_raw,
    tv,
)


def test_bases_are_orthonormal_and_rank_checked():
    R = random_basis(3)
    assert np.allclose(R.T @ R, np.eye(9))
    W = np.random.default_rng(0).standard_normal((9, 512))
    Q, s = orthonormal_rows(W)
    assert np.allclose(Q.T @ Q, np.eye(9)) and np.allclose(W @ (Q @ Q.T), W)
    with pytest.raises(ValueError):
        orthonormal_rows(np.vstack([W[:8], W[:1]]))


def test_norm_matching_and_zero_rule():
    raw = np.array([[3.0, 4.0], [1.0, 0.0], [0.0, 0.0]])
    step, scale = norm_matched(raw, np.array([10.0, 2.0, 0.0]))
    assert np.allclose(np.linalg.norm(step, axis=1), [10, 2, 0]) and scale[2] == 0
    with pytest.raises(ValueError):
        norm_matched(np.zeros((1, 2)), np.array([1.0]))


def test_shuffled_step_permutes_the_head_logit_change():
    rng = np.random.default_rng(1)
    W = rng.standard_normal((9, 512))
    delta = rng.standard_normal((5, 512))
    step = shuffled_raw(delta, W)
    assert np.allclose(step @ W.T, (delta @ W.T)[:, DERANGEMENT])
    assert not np.any(DERANGEMENT == np.arange(9))


def test_high_variance_basis_is_orthogonal_to_q_and_keeps_head_logits():
    rng = np.random.default_rng(2)
    W = rng.standard_normal((9, 512))
    Q, _ = orthonormal_rows(W)
    B = high_variance_basis(rng.standard_normal((400, 512)), Q)
    assert np.allclose(Q.T @ B, 0, atol=1e-10) and np.allclose(B.T @ B, np.eye(9), atol=1e-10)
    delta = rng.standard_normal((3, 512))
    assert np.allclose(project_step(delta, B) @ W.T, 0, atol=1e-9)


def test_tv_averages_over_queries():
    p = np.zeros((1, 2, 16))
    q = np.zeros((1, 2, 16))
    p[0, :, 0] = 1
    q[0, 0, 0] = 1
    q[0, 1, 1] = 1
    assert np.allclose(tv(p, q), [0.5])


@pytest.mark.slow
@needs_model
def test_hook_identity_self_donor_and_full_swap(model, released):
    from ncm_sudoku.e5causal import Level7Hooks
    from ncm_sudoku.e5extract import PREFIX_CELLS
    from ncm_sudoku.intervene import level_logits
    from ncm_sudoku.runner import generate_codes, puzzle_tensor

    pz = released[0][:4]
    x = puzzle_tensor(pz)
    codes = generate_codes(model, pz, batch_size=4)
    plain = level_logits(model, x, codes, 7)
    with Level7Hooks(model.net, PREFIX_CELLS) as h:
        clean = level_logits(model, x, codes, 7)
        assert h.applied == 1
        own = h.captured["L2_before"][:, torch.as_tensor(PREFIX_CELLS)].numpy()
    assert torch.equal(plain, clean)
    rows = (pz == 0)
    with Level7Hooks(model.net, PREFIX_CELLS) as h:  # self-donor: own values written back
        h.patch = (rows, own)
        same = level_logits(model, x, codes, 7)
        assert h.applied == 1 and h.query_unchanged
    assert torch.equal(same, clean)
    donor = own[::-1].copy()  # a real, different donor (rows reversed)
    with Level7Hooks(model.net, PREFIX_CELLS) as h:
        h.patch = (rows, donor)
        level_logits(model, x, codes, 7)
        after = h.captured["L2_after"][:, torch.as_tensor(PREFIX_CELLS)].numpy()
        assert h.query_unchanged
    assert np.array_equal(after[rows], donor[rows]) and np.array_equal(after[~rows], own[~rows])

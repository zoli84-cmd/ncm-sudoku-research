import pytest
import torch

from conftest import needs_model
from ncm_sudoku.damage import codebook_rms, latent_distance, requantize, tv_damage
from ncm_sudoku.grid import CELL_TOKEN_INDICES
from ncm_sudoku.states import cumulative_states


def test_tv_known_values():
    a = torch.zeros(1, 89, 12)
    c = a.clone()
    c[0, CELL_TOKEN_INDICES[0], :] = torch.tensor([0.0] * 11 + [100.0])  # one cell nearly one-hot
    d = tv_damage(c, a)
    assert d.item() == pytest.approx((1 - 1 / 12) / 81, rel=1e-4)
    assert tv_damage(a, a).item() == 0.0


def test_tv_mask_and_range():
    a, c = torch.randn(2, 89, 12), torch.randn(2, 89, 12)
    mask = torch.zeros(2, 81, dtype=torch.bool)
    mask[:, :10] = True
    full, part = tv_damage(c, a), tv_damage(c, a, mask)
    assert ((full >= 0) & (full <= 1)).all() and ((part >= 0) & (part <= 1)).all()


def test_tv_defined_for_any_logits():
    a = torch.zeros(1, 89, 12)
    c = torch.full((1, 89, 12), -1e4)
    c[..., 10] = 1e4  # all separators
    assert torch.isfinite(tv_damage(c, a)).all()


def test_latent_distance():
    za = torch.ones(2, 3, 4)
    assert torch.equal(latent_distance(za, za), torch.zeros(2))
    assert latent_distance(2 * za, za)[0].item() == pytest.approx(1.0)


@needs_model
@pytest.mark.slow
def test_requantize_matches_upstream_from_level_1(model):
    z = torch.randn(3, model.levels[-1], model.vqvae.embed_dim, generator=torch.Generator().manual_seed(0))
    codes, _ = requantize(model, z, 1)
    # z_to_idx returns a bare Tensor[B, n] (not a tuple) when neither return_zhats
    # nor return_zlevels is set, unlike idx_to_zhats which always returns a tuple;
    # compare directly rather than indexing [0] (that would select batch row 0).
    assert torch.equal(codes, model.vqvae.vq.z_to_idx(z))


@needs_model
@pytest.mark.slow
def test_requantize_from_level_3_on_nonzero_residual(model):
    z = torch.randn(3, model.levels[-1], model.vqvae.embed_dim, generator=torch.Generator().manual_seed(1))
    codes_full = model.vqvae.vq.z_to_idx(z)
    z_le2 = cumulative_states(model, codes_full)[1]
    codes, ratio = requantize(model, z - z_le2, 3)
    assert torch.equal(codes, codes_full[:, sum(model.levels[:2]):])
    assert (ratio > 0).all()


@needs_model
@pytest.mark.slow
def test_requant_zero_residual(model):
    z = torch.zeros(2, model.levels[-1], model.vqvae.embed_dim)
    _, ratio = requantize(model, z, 3)
    assert torch.equal(ratio, torch.zeros(2))


@needs_model
@pytest.mark.slow
def test_codebook_rms(model):
    old = torch.tensor([[0, 1], [0, 1]])
    new = torch.tensor([[0, 1], [2, 1]])
    r = codebook_rms(model, 2, old, new)
    E = model.vqvae.vq.embeddings[1].weight
    assert r[0].item() == 0.0 and r[1].item() == pytest.approx((E[2] - E[0]).norm().item(), rel=1e-5)

"""forward_with_intervention and the four E2 branches (plan §2.2 item 4, §7.1, §9.2).

`continue_generation` mirrors NextConceptTransformer.generate for the Sudoku
configuration (query_level0, no l0_autoregressive, cfg_scale 0, no KV cache,
argmax sampling, no prefix padding). Each level sees only the puzzle prefix and the
downsampled cumulative state z_hat, so fixing levels 1..k and continuing reproduces
upstream exactly; identity tests check this bit for bit.
"""

from dataclasses import dataclass

import torch
import torch.nn.functional as F

from ncm_sudoku.model import NcmModel, level_slices


def _check_supported(net) -> None:
    if not net.query_level0 or net.l0_ar or net.use_ctx_encoder or net.prefix_pad_id is not None:
        raise NotImplementedError("continue_generation mirrors only the Sudoku generation path")


def _argmax(net, logits):
    net._cfg = None
    return net._sample_level(logits, 0.0, 0, 1.0)


@torch.no_grad()
def _prefix_embedding(net, prefix_tokens):
    P = net.prefix_len
    enc = net.vqvae_local[0].encoder
    if bool(getattr(net.config, "raw_token_prefix", False)):
        if bool(getattr(net.config, "contextual_prefix", False)) and len(getattr(enc, "blocks", [])) > 0:
            z_prefix = enc.forward_nopos(prefix_tokens)[:, :P, :]
        else:
            z_prefix = enc.wte(prefix_tokens)[:, :P, :]
    else:
        z_prefix = net.vqvae_local[0].encode_z(prefix_tokens)[:, :P, :]
    prefix_emb = net.transformer.wte(z_prefix)
    if not net.use_rope:
        prefix_emb = prefix_emb + net.wpe(net.wp_prefix)
    return prefix_emb


@torch.no_grad()
def _level0_logits(net, prefix_emb, B):
    P, l0, dev = net.prefix_len, net.levels[0], prefix_emb.device
    q0 = net.build_l0_query_input(B, prefix_emb.dtype)
    if net.use_post_upsample_conv:
        q0 = net._apply_post_upsample_conv_single(q0, 0)
    q = net.transformer.wte(q0)
    if not net.use_rope:
        q = q + net.wpe(net.wp_1L[:, :l0])
    if net.config.use_level_encoding:
        q = q + net.transformer.wle(net.lvl_1L[:, :l0])
    h = torch.cat([prefix_emb, q], dim=1)
    m0 = torch.zeros(1, 1, P + l0, P + l0, device=dev)
    m0[:, :, :P, P:] = float("-inf")
    rope_0 = (net.rope_cos_gen_0, net.rope_sin_gen_0) if net.use_rope else None
    for block in net.transformer.blocks:
        h = block(h, attn_mask=m0, rope_cos_sin=rope_0)
    h = net.transformer.ln_f(h)
    return net.lm_heads[0](h[:, P:, :])


@torch.no_grad()
def _level0_from_queries(net, prefix_emb, B):
    return _argmax(net, _level0_logits(net, prefix_emb, B))


@torch.no_grad()
def continue_generation(
    m: NcmModel,
    prefix_tokens: torch.Tensor,
    given_codes: torch.Tensor | None,
    n_given_levels: int,
    z_hat_override: torch.Tensor | None = None,
) -> torch.Tensor:
    """Generate all 12 levels, taking levels 1..n_given_levels from `given_codes`.

    `z_hat_override` (B, 89, 256) replaces the cumulative state right after level
    n_given_levels (1 <= n_given_levels <= 11); later levels accumulate on it.
    """
    net, levels = m.net, m.levels
    _check_supported(net)
    if not 0 <= n_given_levels <= len(levels):
        raise ValueError(f"n_given_levels must be in 0..{len(levels)}")
    slices = level_slices(levels)
    if n_given_levels:
        if given_codes is None or given_codes.shape[1] != slices[n_given_levels - 1].stop:
            raise ValueError("given_codes must cover exactly levels 1..n_given_levels")
    if z_hat_override is not None and not 1 <= n_given_levels <= len(levels) - 1:
        raise ValueError("z_hat_override needs 1 <= n_given_levels <= 11")

    B = prefix_tokens.shape[0]
    vq = net.vqvae_local[0].vq
    z_hat = torch.zeros(B, levels[-1], net.vqvae_local[0].embed_dim, device=prefix_tokens.device)
    prefix_emb = _prefix_embedding(net, prefix_tokens)
    if net.config.use_level_encoding:
        level_pos_embed = net.transformer.wle(net.lvl_1L)
    else:
        level_pos_embed = torch.zeros(1, net.L - levels[0], net.config.n_embd, device=prefix_tokens.device)
    if not net.use_rope:
        level_pos_embed = level_pos_embed + net.wpe(net.wp_1L)

    idx_next = given_codes[:, slices[0]] if n_given_levels else _level0_from_queries(net, prefix_emb, B)
    generated = [idx_next]
    level_acum = levels[0]
    for level_idx in range(len(levels) - 1):
        z_q_level = vq.embeddings[level_idx](idx_next)
        z_hat, x = vq.get_next_autoregressive_input(level_idx, z_hat, z_q_level)
        if z_hat_override is not None and level_idx == n_given_levels - 1:
            z_hat = z_hat_override.clone()
            x = F.interpolate(
                z_hat.transpose(-1, -2), size=(levels[level_idx + 1],), mode="area"
            ).transpose(-1, -2)
        if level_idx + 1 < n_given_levels:
            idx_next = given_codes[:, slices[level_idx + 1]]
        else:
            hi = level_idx + (1 - net._lvl_first)
            if net.use_post_upsample_conv:
                x = net._apply_post_upsample_conv_single(x, hi)
            x = net.transformer.wte(x) + level_pos_embed[:, level_acum : level_acum + levels[level_idx + 1], :]
            logits = net._decode_level_logits(x, prefix_emb, level_idx, None, hidx=hi)
            idx_next = _argmax(net, logits)
        generated.append(idx_next)
        level_acum += levels[level_idx + 1]
    return torch.cat(generated, dim=1)


forward_with_intervention = continue_generation


@torch.no_grad()
def level_logits(m: NcmModel, prefix_tokens: torch.Tensor, given_codes: torch.Tensor, level: int) -> torch.Tensor:
    """Generator logits [B, n_level, 16] for plan level `level` (1..12) given the puzzle prefix
    and `given_codes` levels 1..level-1 (extra columns are ignored), computed exactly as
    `continue_generation` computes them before its argmax: level 1 from the level-0 queries,
    later levels from the downsampled cumulative state of the given levels. Their argmax is
    the greedy code of that level."""
    net, levels = m.net, m.levels
    _check_supported(net)
    if not 1 <= level <= len(levels):
        raise ValueError(f"level must be in 1..{len(levels)}")
    slices = level_slices(levels)
    if level > 1 and given_codes.shape[1] < slices[level - 2].stop:
        raise ValueError("given_codes must cover levels 1..level-1")
    B = prefix_tokens.shape[0]
    prefix_emb = _prefix_embedding(net, prefix_tokens)
    if level == 1:
        return _level0_logits(net, prefix_emb, B)
    vq = net.vqvae_local[0].vq
    z_hat = torch.zeros(B, levels[-1], net.vqvae_local[0].embed_dim, device=prefix_tokens.device)
    if net.config.use_level_encoding:
        level_pos_embed = net.transformer.wle(net.lvl_1L)
    else:
        level_pos_embed = torch.zeros(1, net.L - levels[0], net.config.n_embd, device=prefix_tokens.device)
    if not net.use_rope:
        level_pos_embed = level_pos_embed + net.wpe(net.wp_1L)
    level_acum = levels[0]
    for level_idx in range(level - 1):
        z_q_level = vq.embeddings[level_idx](given_codes[:, slices[level_idx]])
        z_hat, x = vq.get_next_autoregressive_input(level_idx, z_hat, z_q_level)
        if level_idx == level - 2:
            hi = level_idx + (1 - net._lvl_first)
            if net.use_post_upsample_conv:
                x = net._apply_post_upsample_conv_single(x, hi)
            x = net.transformer.wte(x) + level_pos_embed[:, level_acum : level_acum + levels[level_idx + 1], :]
            return net._decode_level_logits(x, prefix_emb, level_idx, None, hidx=hi)
        level_acum += levels[level_idx + 1]


@dataclass(frozen=True)
class Branches:
    A: torch.Tensor
    B: torch.Tensor
    C: torch.Tensor
    D: torch.Tensor


def run_branches(
    m: NcmModel,
    prefix_tokens: torch.Tensor,
    clean_codes: torch.Tensor | None,
    level: int,
    perturbed_level_codes: torch.Tensor,
) -> Branches:
    """Four branches at plan level `level` (1..11), all on the same batch tensor (D20).

    Callers passing `clean_codes` must have generated them from this exact
    `prefix_tokens` batch; with None, A is generated here.
    """
    if not 1 <= level <= len(m.levels) - 1:
        raise ValueError("level must be in 1..11 (level 12 has no suffix)")
    sl = level_slices(m.levels)[level - 1]
    if perturbed_level_codes.shape[1] != sl.stop - sl.start:
        raise ValueError("perturbed_level_codes must have the level's length")
    a = clean_codes if clean_codes is not None else continue_generation(m, prefix_tokens, None, 0)
    b = continue_generation(m, prefix_tokens, a[:, : sl.stop], level)
    c = a.clone()
    c[:, sl] = perturbed_level_codes
    d = continue_generation(m, prefix_tokens, c[:, : sl.stop], level)
    return Branches(A=a, B=b, C=c, D=d)

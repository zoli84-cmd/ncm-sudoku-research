"""Safe CPU loading of the NCM Sudoku checkpoints (WP0-B, plan §2.2 items 1 and 4).

The upstream package `third_party/ncm` (pinned submodule) is imported unmodified.
Its own loaders use torch.load(weights_only=False); this module never calls them
and loads every checkpoint with weights_only=True (the released files contain only
tensors and an OrderedDict, verified with pickletools).
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_DIR = ROOT / "third_party" / "ncm"


def import_upstream() -> None:
    path = str(UPSTREAM_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


@dataclass(frozen=True)
class NcmModel:
    net: torch.nn.Module
    vqvae: torch.nn.Module
    cfg: object  # omegaconf DictConfig of the checkpoint's config.yaml
    levels: tuple[int, ...]


def _safe_load(path: Path) -> dict:
    return torch.load(path, weights_only=True, map_location="cpu")


def level_slices(levels) -> list[slice]:
    """Code-index slice per level; index 0 is plan level 1."""
    out, start = [], 0
    for n in levels:
        out.append(slice(start, start + n))
        start += n
    return out


def load_model(ckpt_dir: Path) -> NcmModel:
    import_upstream()
    from omegaconf import OmegaConf
    from models.next_concept import NextConceptTransformer
    from models.vqvae import VQVAE

    ckpt_dir = Path(ckpt_dir)
    torch.use_deterministic_algorithms(True)
    cfg = OmegaConf.load(ckpt_dir / "config.yaml")
    vq_kwargs = {k: v for k, v in OmegaConf.to_container(cfg.tokenizer.vqvae).items() if k != "checkpoint_path"}
    vq_kwargs["vector_quantizer_config"] = cfg.tokenizer.vqvae.vector_quantizer_config
    vqvae = VQVAE(**vq_kwargs)
    vqvae.load_state_dict(_safe_load(ckpt_dir / "tokenizer.pt")["model"], strict=True)
    vqvae.eval()
    net = NextConceptTransformer(vqvae_local=vqvae, config=cfg.model)
    net.load_state_dict(_safe_load(ckpt_dir / "generator.pt")["model"], strict=True)
    net.eval()
    levels = tuple(int(n) for n in vqvae.vq.levels)
    return NcmModel(net=net, vqvae=vqvae, cfg=cfg, levels=levels)

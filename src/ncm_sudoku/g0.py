"""G0 reproduction, identity checks and the D20 acceptance rule (plan §2.2 items 1, 2, 5);
shared run records `environment_record` and `code_state` (plan §12.2)."""

import hashlib
import json
import platform
import subprocess
import sys

import numpy as np
import torch

from ncm_sudoku.grid import encode_solution_tokens
from ncm_sudoku.intervene import continue_generation
from ncm_sudoku.model import ROOT, NcmModel, level_slices
from ncm_sudoku.official import decode_string, official_exact
from ncm_sudoku.runner import decode_codes, generate_codes, puzzle_tensor
from ncm_sudoku.states import cumulative_states
from ncm_sudoku.validate import evaluate, parse_output_tokens

PUBLISHED_SOLVED_PCT = 86.1
TOLERANCE_PP = 1.0
SHAM_LEVELS = tuple(range(1, 12))
OVERRIDE_LEVELS = (2, 6)
IDENTITY_KEYS = (
    "noop",
    *(f"sham_{lv}" for lv in SHAM_LEVELS),
    *(f"zhat_override_{lv}" for lv in OVERRIDE_LEVELS),
    "zhat_override_effective",
    "final_state_parity",
    "state_storage_isolated",
)


def environment_record() -> dict:
    prov = ROOT / "experiments" / "provenance" / "checkpoints.json"
    return {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "torch_threads": torch.get_num_threads(),
        "deterministic": torch.are_deterministic_algorithms_enabled(),
        "precision": "fp32, eager, cpu",
        "upstream_commit": subprocess.check_output(
            ["git", "-C", str(ROOT / "third_party" / "ncm"), "rev-parse", "HEAD"], text=True
        ).strip(),
        "checkpoints": json.loads(prov.read_text()) if prov.exists() else None,
    }


CODE_PATHS = ("src", "scripts", "pyproject.toml", "uv.lock")


def code_state() -> dict:
    """Repository commit, whether the code paths differ from it, and a hash of that diff."""
    git = lambda *a: subprocess.check_output(["git", "-C", str(ROOT), *a], text=True, encoding="utf-8")  # noqa: E731
    dirty = bool(git("status", "--porcelain", "--", *CODE_PATHS).strip())
    diff = git("diff", "HEAD", "--", *CODE_PATHS)
    return {"commit": git("rev-parse", "HEAD").strip(), "dirty": dirty,
            "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest() if dirty else None}


@torch.no_grad()
def identity_checks(m: NcmModel, puzzles: np.ndarray) -> dict[str, bool]:
    prefix = puzzle_tensor(puzzles)
    clean = generate_codes(m, puzzles, batch_size=len(puzzles))
    end = [s.stop for s in level_slices(m.levels)]
    states = cumulative_states(m, clean)
    result = {
        "noop": torch.equal(continue_generation(m, prefix, None, 0), clean),
    }
    for lv in SHAM_LEVELS:
        result[f"sham_{lv}"] = torch.equal(continue_generation(m, prefix, clean[:, : end[lv - 1]], lv), clean)
    for lv in OVERRIDE_LEVELS:
        out = continue_generation(m, prefix, clean[:, : end[lv - 1]], lv, z_hat_override=states[lv - 1])
        result[f"zhat_override_{lv}"] = torch.equal(out, clean)
    shifted = continue_generation(m, prefix, clean[:, : end[1]], 2, z_hat_override=states[1] + 5.0)
    result["zhat_override_effective"] = not torch.equal(shifted[:, end[1] :], clean[:, end[1] :])
    upstream_final = m.vqvae.vq.idx_to_zhats(clean, return_zlevels=False)[0][-1]
    result["final_state_parity"] = torch.equal(states[-1], upstream_final)
    before = states[5].clone()
    states[11].add_(1.0)
    result["state_storage_isolated"] = len({s.data_ptr() for s in states}) == 12 and torch.equal(states[5], before)
    return result


def g0_rule(official_solved_pct: float, identity: dict[str, bool]) -> dict:
    part_a = abs(official_solved_pct - PUBLISHED_SOLVED_PCT) <= TOLERANCE_PP
    part_b = set(identity) == set(IDENTITY_KEYS) and all(identity.values())
    return {
        "published_solved_pct": PUBLISHED_SOLVED_PCT,
        "tolerance_pp": TOLERANCE_PP,
        "official_solved_pct": official_solved_pct,
        "part_a_reproduction": part_a,
        "part_b_identity": part_b,
        "passed": part_a and part_b,
        "changed_output_count": "unavailable",  # no paired reference predictions (D29)
    }


@torch.no_grad()
def reproduce(m: NcmModel, puzzles: np.ndarray, solutions: np.ndarray, batch_size: int = 128) -> dict:
    tokens = torch.cat(
        [
            decode_codes(m, generate_codes(m, puzzles[i : i + batch_size], batch_size=batch_size))
            for i in range(0, len(puzzles), batch_size)
        ]
    )
    hyps = [decode_string(t.tolist()) for t in tokens]
    refs = [decode_string(encode_solution_tokens(s)) for s in solutions]
    metrics = [evaluate(p, parse_output_tokens(t.tolist()), s) for p, t, s in zip(puzzles, tokens, solutions)]
    own = {}
    for field in ("well_formed", "solve", "valid_grid", "all_clues_preserved", "clue_preservation",
                  "cell_acc_all", "cell_acc_empty", "reference_match"):
        own[field] = float(np.mean([float(getattr(x, field)) for x in metrics]))
    violations = [x.constraint_violations for x in metrics if x.constraint_violations is not None]
    own["mean_constraint_violations_well_formed"] = float(np.mean(violations)) if violations else None
    return {
        "n": len(puzzles),
        "batch_size": batch_size,
        "official": official_exact(hyps, refs),
        "own": own,
        "per_puzzle": [bool(x.solve) for x in metrics],
    }

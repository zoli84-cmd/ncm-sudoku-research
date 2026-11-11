"""E3 training-budget sensitivity (D68, non-confirmatory).

Reruns the level-6 whole-layer stage of `scripts/e3_wholelayer.py` (D66 design:
generated linear probe, permuted control, θ1 preview) with `min_steps` = 6,000
(3× the D63 budget) and writes everything to `experiments/e3prep/budget_sensitivity/`
(`wholelayer.json`, `wholelayer_report.md`, `wholelayer_h1_diffs_L06.json`).
The committed 2,000-step results in `experiments/e3prep/` are not touched.
Usage: uv run python scripts/e3_budget_sensitivity.py [--force | --resume]
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

MIN_STEPS = 6000
_SCRIPT = Path(__file__).resolve().parent / "e3_wholelayer.py"


def load_wholelayer():
    spec = importlib.util.spec_from_file_location("e3_wholelayer", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def configure(mod) -> None:
    """Points the whole-layer script at the sensitivity output and budget, L06 only."""
    mod.OUT = mod.ROOT / "experiments" / "e3prep" / "budget_sensitivity"
    mod.KW = {**mod.KW, "min_steps": MIN_STEPS}
    mod.STAGES = [s for s in mod.STAGES if s[0] == "L06"]
    mod.NOTE = mod.NOTE + f"; D68 budget sensitivity, min_steps = {MIN_STEPS}"


if __name__ == "__main__":
    m = load_wholelayer()
    configure(m)
    m.main()

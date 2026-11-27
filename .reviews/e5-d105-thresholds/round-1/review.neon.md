I'll read the review brief and examine the referenced materials to perform the review.

Elolvastam a review briefet; most párhuzamosan átnézem a fő D105 specifikációt, a kapcsolódó D101/D102 dokumentumokat, valamint a `power.py` és `wp2eval.py` fájlokat.

I have reviewed the D105 draft, D101/D102 design docs, and `power.py`/`wp2eval.py`. Next, I will inspect `DECISIONS.md`, `research_plan_v3.7.md`, `e2p2.py`, and the causal pilot JSON files.

I've read the D105 draft, prior E5 design specs (D101–D104), and earlier lock/power code (`power.py`, `wp2eval.py`, `research_plan_v3.7.md`). Next, I'll recompute the pilot readout and causal statistics safely without pickle, and inspect `e2p2.py`'s interval implementation and E5 codebase modules.

VERDICT: BLOCKED

Completing this objective strictly requires running a read-only shell/Python statistical recomputation that was denied by runtime permission recovery:

- **Required work blocked by permission recovery:** The review brief (`.reviews/e5-d105-thresholds/round-1/brief.neon.md`, *Specific focus for this artifact*, item 1) explicitly requires recomputing the pilot per-pair statistics quoted in the D105 draft Context:
  1. `W(Z<=6)` mean and SD from `experiments/e5/pilot/z6__shared__none.json` (`w_auc.per_pair`), and `Delta` from `experiments/e5/pilot/P2__shared__none.json` minus `z6`;
  2. Causal `Q` directed mean/SD and `Q − high-variance` mean/SD per pair (averaging both orders) from the binary archive `runs/e5/causal/primary.npz`;
  3. Rough TOST sample sizes.
- **Why this cannot be completed without shell execution:** `experiments/e5/causal/primary.json` only stores means and 95% bootstrap CIs—not the per-pair arrays or per-pair SDs (`0.061` and `0.041`) quoted in `docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md`. Those per-pair SDs exist only inside the binary `runs/e5/causal/primary.npz` file, which cannot be inspected with read-only file-viewing tools.
- **Blocked actions preventing autonomous completion:**
  - `powershell` (`actionId: 89dbe96e-7e68-41c8-9d16-05263ebd31af`): initially denied due to `allow_pickle=True` in the NumPy load call.
  - `powershell` (`actionId: 3faec7c0-eb54-4fda-87ea-8714eb3d499e`): subsequent pickle-free recomputation script was denied because the prior permission-recovery denial bound the same statistical recomputation.

**Next step for human:** Approve a read-only Python (`powershell`) execution (without `allow_pickle=True`) to load `experiments/e5/pilot/z6__shared__none.json`, `experiments/e5/pilot/P2__shared__none.json`, and `runs/e5/causal/primary.npz` and verify the quoted per-pair statistics and TOST sizes, or confirm that the review should be accepted with those `primary.npz` recomputation claims left unverified.


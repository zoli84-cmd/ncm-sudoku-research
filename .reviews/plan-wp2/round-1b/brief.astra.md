# Review brief: WP2 implementation plan — confirmatory TEST runs of a locked preregistration

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

**Read repository files only.** Do not open any file outside `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research`. Do not try to open `C:\Users\ako2bp\AGENTS.md` (the project `AGENTS.md` mentions it; it is out of scope and not needed). Do not run Python, `uv run`, PowerShell or other execution commands; verify by reading files only. If any read is denied, note it in one line under "Claims checked" and CONTINUE the full review with the repository files; a denied read never ends the review. Start by reading the artifact plan file.

**Keep the final answer short: at most about 1,200 words in total.** Report blocker and major findings in full; list minor findings as one line each (at most six) and no nits. Keep "Claims checked" to at most eight one-line items. A longer answer is truncated and the whole review is lost.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state. Return your review as your final answer; do not write it to disk.

## Artifact

- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\docs\superpowers\plans\2026-11-13-wp2.md` (the artifact: implementation plan)
- Spec it implements: `research_plan_v3.7.md` (locked protocol, tag `prereg-v3.7`; read §2.2, §6, §7, §8, §10, §11, §12.2, §13) and `DECISIONS.md` rows D74–D77 (D76 = WP2 process, D77 = accepted readings of ambiguous points)
- Code the plan reuses: `src/ncm_sudoku/e2p2.py`, `probes.py`, `e3controls.py`, `e3data.py`, `wholelayer.py`, `e3equiv.py`, `power.py`, `subsets.py`, `g0.py`; scripts `e2_pilot2.py`, `e3_extract.py`, `e3_probes.py`, `e3_wholelayer.py`, `wp1_e1.py`, `lock_test_set.py`, `lock_equiv_l12.py`
- Frozen inputs: `experiments/lock/test_set.json`, `experiments/lock/cal_freqs.json`, `experiments/e2p2/summary.json`, `experiments/e3prep/probes.json`, `experiments/e3prep/wholelayer.json`

## Context

Personal interpretability research project on Next-Concept Modeling (NCM) Sudoku generation. The protocol `research_plan_v3.7.md` is preregistered (git tag plus embargoed OSF registration). WP2 runs every confirmatory analysis once on 600 TEST puzzles (E1 descriptive; E2: H2 levels 1 vs. 11 solve contrast, H3 level-1 compensation; E3: H1 level-6 candidate-mask readability with a cell-relative whole-layer probe, two-sided with a family-level ±0.01 equivalence reading) plus the pre-specified secondary and exploratory analyses. No model has been run on TEST. Process (D76): all code written and reviewed, frozen by a git tag `wp2-code`, then a dry run on non-TEST data (E2 on the first 50 CAL puzzles must reproduce the pilot-2 records exactly; E3 with PROBE-VAL in the TEST role must reproduce the D64/D67 values), then the TEST runs, then a pre-written evaluation script. Risk tier: medium — the plan is revertable, but the runs it produces are single-look, so a plan error that survives code review becomes a post-lock deviation. The decision supported: whether this plan can be executed as written.

## Decision log from previous rounds

none

## What to check

1. **Fidelity to the locked protocol**: does every primary, secondary and exploratory analysis in v3.7 (§6–§8, §11, §13) have a task that implements it exactly — estimators, interval levels (98.33% family, 96.67% H1 TOST, 90% TOST for θ₂′ and θ_T, 95% otherwise), the rare-event rule and its levels, the frozen inputs (CAL frequencies, AUC common range, equivariance tolerance), seeds, probe grid and budget? Name anything missing, added, or implemented differently, with the plan line and the v3.7 section.
2. **Statistical code correctness**: the evaluation library task (`wp2eval.py`) and its tests — TOST logic, bootstrap-or-bound switch, the H1 two-reading logic and the §13 mechanical selection rules (consistent with §8.3 and §13, and with D77).
3. **Single-look safety**: can any step compute or display a TEST outcome before the code freeze, or let TEST results influence code? Is the freeze guard sound (tag commit, clean code paths, no `--force` in the TEST role, resume semantics)? Can a crash or resume silently change results?
4. **Dry-run validity**: does the dry run exercise every code path the TEST run uses, and are its pass criteria (exact equality with pilot 2 and the full-batch level-1 records; D64/D67 reproduction) achievable and checked?
5. **Reuse and refactors**: are the proposed changes to existing functions (`run_pilot2` stages, three-set `fit_cells`, `fit_selected` returning models/predictions) safe, i.e. do they keep pre-lock results reproducible, and are there tests that pin that?
6. **The 21 "Spec ambiguities"**: is any chosen reading inconsistent with v3.7's text, or does any hide a substantive analysis choice that should be logged differently?

## Output format

Respond in English. Use exactly this structure.

### Verdict
One or two sentences: can the plan be executed as written, and what is the single most important change?

### Findings
One block per blocker or major finding, most severe first. ID prefix: `ASTRA`.

```
ASTRA-<n> | <blocker|major> | <plan line or section>
Claim: <one or two sentences>
Evidence: <what you checked, with file:line>
Recommendation: <concrete change>
Confidence: <high|medium|low>
```

Then minor findings as one line each: `ASTRA-<n> | minor | <location> | <claim and recommendation>`.

Severity: blocker = executing as written produces wrong confirmatory results or breaks the single-look guarantee; major = significant risk or a clear mismatch with the locked protocol; minor = real but contained.

### Claims checked
At most eight one-line items, each marked holds / does not hold / could not verify.

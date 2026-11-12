# Review brief (round 2): Research plan v3.7 — preregistration lock version, round-1 fixes

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

**Read repository files only.** Do not open any file outside `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research`. Do not try to open `C:\Users\ako2bp\AGENTS.md` (the project `AGENTS.md` mentions it; it is out of scope and not needed). Do not run Python, `uv run`, PowerShell or other execution commands; verify by reading files only.

**Keep the final answer short: at most about 1,000 words in total.** Report blocker and major findings in full; list minor findings as one line each (at most five) and no nits. Keep "Claims checked" to at most eight one-line items. A longer answer is truncated and the whole review is lost.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state. Return your review as your final answer; do not write it to disk.

## Artifact

- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\research_plan_v3.7.md` (the artifact)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\plan-v3-7\round-2\r1-fixes.diff` (exactly what changed in the plan since round 1)
- Code changed since round 1 (`git diff 3ab0792 HEAD -- src scripts tests`): `src/ncm_sudoku/e2p2.py` (`frozen_freqs`, `pilot_freqs`, `load_frozen_freqs`, `clean_codes`), `src/ncm_sudoku/grid.py` (`PEER_ORDER`), `src/ncm_sudoku/e3data.py`, `src/ncm_sudoku/wholelayer.py`, `src/ncm_sudoku/e3equiv.py` (`acceptable`), `scripts/lock_cal_freqs.py`, `tests/test_peer_order.py`, `tests/test_lock_cal_freqs.py`
- New result file: `experiments/lock/cal_freqs.json`
- `DECISIONS.md` rows D72 and D73

## Context

Personal interpretability research project on Next-Concept Modeling (NCM) Sudoku generation. `research_plan_v3.7.md` is the preregistration lock version: it will be frozen by a git tag and an embargoed OSF registration; TEST puzzles are generated but no model has been run on them. Round 1 had two reviewers (carbon; astra replacing sol, which failed three times). All ten findings were accepted and applied: frozen CAL code frequencies for levels 2/6/11 passed to the E2 runner, a frozen peer order with PCA rules and control seeds, per-seed Brier averaging, a justification of the H1 switch, full-precision AUC range, a fixed equivariance tolerance, hash formats, a §13 rule requiring the 98.33% lower limit > 0 for the positive-but-small H1 reading, per-category equivariance numbers, and corrected provenance. Risk tier: high (published contract, hard to roll back). The decision supported: whether the round-1 fixes are correct and complete, so that v3.7 can go to the final review and the lock.

## Decision log from previous rounds

`C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\plan-v3-7\decisions.md`

Do not re-raise a resolved or rejected point unless you have new evidence, and then say what is new.

## What to check

1. Is each round-1 finding in the decision log actually resolved by the plan text in `r1-fixes.diff` and the code changes, and is each fix correct? In particular: the frozen-frequency path in `e2p2.run_pilot2` and `scripts/lock_cal_freqs.py`; the `PEER_ORDER` freeze and its hash; the §13 H1 rows against §8.3 and `power.h1_tost`.
2. Did the fixes introduce new inconsistencies across §3, §7, §8, §11, §12.1, §12.2, §13 and §16, or with D72/D73?
3. Fact-check the new numbers and hashes in §12.2 against `experiments/lock/cal_freqs.json`, `tests/test_peer_order.py` and `experiments/e2p2/summary.json`.

Scope: review only the round-1 fixes and their direct consequences; do not re-review unchanged sections.

## Output format

Respond in English. Use exactly this structure.

### Verdict
One or two sentences: are the fixes sound enough to proceed to the final review, and what is the single most important change?

### Findings
One block per finding, most severe first. ID prefix: `{{ID_PREFIX}}`.

```
{{ID_PREFIX}}-<n> | <blocker|major|minor|nit> | <file:line or artifact section>
Claim: <one or two sentences>
Evidence: <what you checked, with file:line>
Recommendation: <concrete change>
Confidence: <high|medium|low>
```

Severity: blocker = proceeding causes incorrect behaviour or a design that must be redone; major = significant risk or a wrong claim that drives a decision; minor = real but contained.

### Claims checked
At most eight one-line items, each marked holds / does not hold / could not verify.

# Review brief: E5 D105 draft: confirmatory thresholds, error rates and TEST size

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md (the artifact)
- Builds on: C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/docs/superpowers/specs/2026-11-25-e5-d102-causal-design.md, decisions D91–D104 in C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/DECISIONS.md
- Pilot data: C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/experiments/e5/pilot/*.json (per_pair W-AUC lists), C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/experiments/e5/causal/primary.json, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/runs/e5/causal/primary.npz, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/experiments/e5/causal/cosines.json
- Earlier lock practice: C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/research_plan_v3.7.md (§11, §12.2, §13), C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/power.py, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/wp2eval.py (ALPHA_FAMILY, tost)

## Context

The project studies a released NCM Sudoku generator; its submitted manuscript (under review, unchanged) found the candidate mask only weakly readable from the cumulative latent state Z<=6. E5, a separately preregistered follow-up, asks whether that weakness is a property of the state or of the generator. Pilots on counterfactual pairs (one solution, two clue masks) found the candidate mask perfectly readable within pairs from the generator's prefix encoding but at control level in Z<=6 (D100, D101), and a causal activation-exchange pilot found the level-7 code distribution sensitive to the candidate subspace beyond norm-matched, high-variance and shuffled-digit controls (D102–D104). The artifact fixes the numbers the E5 protocol will preregister: the Z<=6 equivalence band, the minimum prefix-minus-Z difference, the causal decision rule, the family-wise error control and the TEST size. Risk tier: high, because these numbers become a published preregistration that cannot be changed after the lock.

## Decision log from previous rounds

C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/.reviews/e5-d105-thresholds/decisions.md

If a decision log is given: do not re-raise a rejected point unless you have new evidence, and then say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify every concrete claim about the code (files, lines, behaviour) directly in the repository. Say for each checked claim whether it holds.
2. **Hidden risks in the proposed solution**: failure modes, edge cases, concurrency, serialization, migration and rollback, performance under real load, security.
3. **Missing issues or simpler alternatives**: anything important the artifact misses, and any simpler approach that would achieve the same goal.
4. **Prioritization and scope**: is the proposed order and scope right? What should be cut?

Specific focus for this artifact:
- Recompute the pilot per-pair statistics quoted in the Context (W(Z<=6) mean/SD from experiments/e5/pilot/z6__shared__none.json per_pair; Delta from P2__shared__none.json minus z6; causal Q and Q minus high-variance per pair from experiments/e5/causal/primary_per_pair.json (exported per-pair values, both orders averaged)) and the rough TOST sizes.
- Whether epsilon = 0.03 and the Delta minimum 0.25 are defensible and not tuned to guarantee success on the pilot; what an independent justification would be; whether the band should be centred on 0.5 or on an empirical null (D101 states the E3 controls are diagnostics, not a calibrated null).
- Error control: Bonferroni over three tests when the state reading needs two tests jointly (an intersection-union structure, where each test can be run at the full alpha) and the causal test answers a separate question; compare with plan v3.7 practice (wp2eval.ALPHA_FAMILY, TOST at 1 − 2 alpha).
- The causal rule (lower bound of Q directed effect > 0.01 TV; Q − high-variance > 0; Q − shuffled > 0): is 0.01 meaningful given the full-swap reference 0.061 and 14.2% of recipients with TV(clean, full) < 0.01? Are the three conjunctive conditions at alpha/3 each coherent?
- TEST size 500 pairs: justified by secondary strata, but a large TEST makes small probe-induced biases in W(Z<=6) more likely to exceed a narrow band; is there a better rule (e.g. size by the secondary strata with a precision target, or a smaller TEST)?
- Whether the final simulation as described (resampling PROBE-VAL per-pair values under shifted scenarios) can estimate false-positive rates validly, given that the probes are fitted on PROBE-TRAIN and frozen, and TEST pairs are fresh.



Note for this Final round: review the full artifact as it now stands after rounds R1 and R2. The per-pair data you need are in experiments/e5/pilot/*.json (w_auc.per_pair) and experiments/e5/causal/primary_per_pair.json; you do not need the .npz file. Focus on whether the decision procedure (unhedged one-sided betting tests, intersection-union over two claims at 0.025, sampling rule without replacement after internal collisions, N rule and scenario formulas) is valid, unambiguous and implementable, and whether any accepted finding in the decision log is not reflected in the text.

## Output format

Respond in Hungarian. Use exactly this structure so the findings can be processed automatically.

### Verdict
One or two sentences: is the artifact sound enough to proceed, and what is the single most important change?

### Findings
One block per finding, most severe first. ID prefix: `ASTRA`.

```
ASTRA-<n> | <blocker|major|minor|nit> | <file:line or artifact section>
Claim: <what is wrong or missing, one or two sentences>
Evidence: <what you checked in the code, with file:line>
Recommendation: <concrete change>
Confidence: <high|medium|low>
```

Severity definitions:
- **blocker**: proceeding as written causes incorrect behaviour, data loss, a security issue, or a design that must be redone.
- **major**: a significant risk, a wrong claim that drives a decision, or a clearly better alternative that changes the plan.
- **minor**: a real but contained issue; fix if cheap.
- **nit**: wording, style or preference. Report at most three nits.

Rules: only report what you checked or can argue concretely. If you could not verify a claim, say so with Confidence: low. Do not pad: zero findings in a category is a valid result.

### Claims checked
A short list of the artifact's code claims you verified, each marked holds / does not hold / could not verify.

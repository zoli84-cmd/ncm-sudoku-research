# Review brief: E5 D101 draft: primary readout and W-AUC inference after the pilot

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md (the artifact)
- Supporting code and data: C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/e5pilot.py, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/e5probes.py, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/e5pairs.py, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/e5extract.py, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/scripts/e5_pilot.py, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/experiments/e5/pilot/*.json, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/experiments/e5/pairs.json, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/experiments/e5/extract.json, decisions D91–D100 in C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/DECISIONS.md

## Context

The project studies a released Next-Concept Modeling (NCM) Sudoku generator; its submitted manuscript (under review, unchanged) found the candidate mask only weakly linearly readable from the cumulative latent state Z<=6. E5 is a separately preregistered follow-up asking whether that weakness is a property of the cumulative state or of the generator. A positive control on another published Sudoku transformer passed (D94–D98), counterfactual pairs (one solution, two clue masks) were generated (D97, D99), and a non-confirmatory pilot of probes was run on these pairs (D100, results in experiments/e5/pilot/). The artifact is a draft decision (D101) fixing the primary readout, the inference unit and null for the within-pair AUC, the prefix-layer selection rule and the Z stratum, before the E5 protocol and any TEST data exist. Risk tier: medium (planning decision, revertable; no high trigger), but it shapes a later preregistration, so statistical validity matters most.

## Decision log from previous rounds

none

If a decision log is given: do not re-raise a rejected point unless you have new evidence, and then say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify every concrete claim about the code (files, lines, behaviour) directly in the repository. Say for each checked claim whether it holds.
2. **Hidden risks in the proposed solution**: failure modes, edge cases, concurrency, serialization, migration and rollback, performance under real load, security.
3. **Missing issues or simpler alternatives**: anything important the artifact misses, and any simpler approach that would achieve the same goal.
4. **Prioritization and scope**: is the proposed order and scope right? What should be cut?

Specific focus for this artifact:
- Verify the pilot table in the artifact against experiments/e5/pilot/*.json (w_auc.overall, w_auc.codes_differ, summary.val_brier_mean, metrics.exact_match).
- Check `w_auc` in src/ncm_sudoku/e5pilot.py: bit selection (cell empty in both members, digit candidate in exactly one), tie handling, per-pair aggregation, and whether the claimed exact 0.5 for P0/shared and the teacher state follows from the code.
- Statistical validity of D101 point 2: is a pair-level sign-flip permutation test valid for the mean per-pair W-AUC (exchangeability of the two members under the null; pairs with no discordant bits; NaN handling), and is the pair-level bootstrap appropriate? Observation 3 claims bit-level clustering explains control W-AUCs of 0.43–0.58: is that the right explanation, or could the probe/control construction itself (e3controls.permuted_control tunes on permuted val; permute_labels) bias W-AUC away from 0.5?
- D101 point 1: is the shared own-position readout (state plus cell one-hot, src/ncm_sudoku/probes.py build_inputs) a fair common readout for Z<=6 (256-d, sum of codebook vectors) and prefix residual states (512-d)? Is the argument that the whole-layer readout measures the input at P0 correct (src/ncm_sudoku/wholelayer.py whole_layer_features), and does the same concern affect higher prefix layers or Z?
- D101 points 3 and 4: selection bias from picking the prefix layer on PROBE-VAL (also used for early stopping), and bias from restricting Z<=6 to pairs with different level 1–6 codes while the prefix uses all pairs.
- Whether the pilot result (prefix near-perfect, Z<=6 at control level) already makes the confirmatory question trivially decided, and if so what the protocol should test instead or in addition.



## Output format

Respond in Hungarian. Use exactly this structure so the findings can be processed automatically.

### Verdict
One or two sentences: is the artifact sound enough to proceed, and what is the single most important change?

### Findings
One block per finding, most severe first. ID prefix: `CARBON`.

```
CARBON-<n> | <blocker|major|minor|nit> | <file:line or artifact section>
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

# Review brief: E5 protocol v1 (draft preregistration)

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/e5_protocol_v1.md (the artifact)
- Decisions it compiles: D91–D106 in C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/DECISIONS.md; design specs C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md, 2026-11-25-e5-d102-causal-design.md, 2026-11-26-e5-d105-thresholds-design.md (same folder); their review logs under C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/.reviews/e5-d101-readout/, e5-d102-causal/, e5-d105-thresholds/
- Code the protocol relies on: C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/e5pairs.py, e5extract.py, e5pilot.py, e5probes.py, e5causal.py, e5stats.py; C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/scripts/e5_pairs.py, e5_extract.py, e5_causal.py, e5_causal_heads.py, e5_power.py; C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/intervene.py, states.py, labels.py
- Results it cites: C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/experiments/e5/ (pairs.json, extract.json, pilot/*.json, causal/heads.json, causal/primary.json, causal/primary_per_pair.json, causal/cosines.json, power.json); checkpoint provenance C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/experiments/provenance/checkpoints.json
- Format precedent: C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/research_plan_v3.7.md (§11–§13) and C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/osf/registration.md

## Context

The project studies the released NCM Sudoku-hard generator; its submitted manuscript (under review, unchanged) found the candidate mask only weakly linearly readable from the cumulative latent state Z<=6. E5 is a separately preregistered follow-up asking whether that weakness is a property of the state or of the generator, using counterfactual pairs (one solution, two clue masks). The artifact is the draft preregistration that compiles the reviewed design decisions D91–D106 into one protocol: data and screening, frozen probes and bases, two confirmatory claims tested with one-sided betting tests at alpha 0.025 each, invalid-run rules, secondary analyses, interpretation rules and pre-lock tasks. Risk tier: high, because after the lock (git tag plus OSF registration) the text is a published contract that cannot be changed.

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
- Faithfulness: does the protocol state every decision of D91–D106 correctly and completely, and does it contradict any of them (especially D101(1)–(5), D102(2)–(7), D105(1)–(7), D106)? Flag anything compiled wrongly or omitted.
- Executability and freezing: can every step be carried out as written with the existing code, and is every degree of freedom fixed before TEST (probe and basis identity, pair order, eligibility, tie handling, scoring, the decision function `ncm_sudoku.e5stats`, seeds)? Note that the Z<=6 head is not yet saved (§4, §9).
- The interpretation table (§8): are the justified claims and 'does not follow' entries correct and complete for every combination of A1/A2 and B1–B4 outcomes, and do they stay within what the tests support (frozen probe, this intervention)?
- Invalid-run and stopping rules (§6) and the internal-collision rule (§3): do they preserve the error guarantee and leave no room for outcome-dependent choices?
- Pre-lock tasks (§9): is the dry-run requirement (reproduce the pilot exactly on PROBE-VAL) achievable and sufficient, and is anything missing before the tag (e.g. registration content, versioning, deviations policy)?
- Numbers: check the cited figures (checkpoint hashes, N = 400 and the D106 power table, pilot values) against the files.



## Output format

Respond in Hungarian. Use exactly this structure so the findings can be processed automatically.

### Verdict
One or two sentences: is the artifact sound enough to proceed, and what is the single most important change?

### Findings
One block per finding, most severe first. ID prefix: `{{ID_PREFIX}}`.

```
{{ID_PREFIX}}-<n> | <blocker|major|minor|nit> | <file:line or artifact section>
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

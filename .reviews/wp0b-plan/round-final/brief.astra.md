# Review brief: WP0-B implementation plan: final check of R1 fixes

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- Primary: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/docs/superpowers/plans/2026-11-09-wp0b-model-instrumentation.md`
- Upstream code (read directly): `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/third_party/ncm/` (models/next_concept.py generate; models/quant.py get_next_autoregressive_input, idx_to_zhats)
- Spec: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/research_plan_v3.4.md` Sections 2.2, 8.1, 9.2

## Context

The plan implements safe CPU loading of the NCM Sudoku-hard checkpoint, an exact mirror of the official evaluation (G0), cumulative latent states, and a four-branch intervention wrapper used by all later experiments. Round R1 (one reviewer; the second failed) found two majors and five minor/nit items; all were accepted and applied. This final round checks only that those fixes are correct, consistent with the upstream code, and complete. Risk tier: medium (set by the user).

## Decision log from previous rounds

`C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/.reviews/wp0b-plan/decisions.md`

If a decision log is given: do not re-raise a rejected point unless you have new evidence, and then say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify every concrete claim about the code (files, lines, behaviour) directly in the repository. Say for each checked claim whether it holds.
2. **Hidden risks in the proposed solution**: failure modes, edge cases, concurrency, serialization, migration and rollback, performance under real load, security.
3. **Missing issues or simpler alternatives**: anything important the artifact misses, and any simpler approach that would achieve the same goal.
4. **Prioritization and scope**: is the proposed order and scope right? What should be cut?

Specific focus for this artifact:
1. Task 4 `z_hat_override`: is the handoff semantics correct against upstream `generate` and `get_next_autoregressive_input` (which level index is downsampled to which length; does setting z_hat after the given levels and interpolating to levels[n_given_levels] match what upstream would feed into the next level)? Are the two new tests sufficient?
2. Task 4 sham levels now include level 1: does n_given_levels=1 correctly skip the level-0 query block while still running loop iteration level_idx=0 (learned_up_l1) for level 2?
3. Task 5 `identity_checks` and `g0_rule` with IDENTITY_KEYS (10 checks): consistent with Task 4/3 tests and D20 part (b)? Is `reproduce` with batch_size=128 and the psutil/storage measurements in g0_cost adequate for plan Section 2.2 item 9?
4. Task 3 `CELL_TOKEN_INDICES = c + c // 9` and the puzzle-prefix offset `1 + c + c // 9`: correct for the 89-token output and 91-token prefix?
5. Task 2 percentage scale and empty-hyp handling: consistent with eval_merge.exact?

Scope: review only the parts changed after R1 and their direct consequences: Task 1 provenance licenses; Task 2 Produces and Step 1; Task 3 Files, Produces (cumulative_states input shape, decode_state_logits, CELL_TOKEN_INDICES, cell_states) and Step 1; Task 4 Produces (continue_generation signature with z_hat_override, run_branches with optional clean_codes) and Step 1 test list; Task 5 Produces (reproduce batch_size, identity_checks, g0_rule, g0_cost) and Step 1; Review Focus items 5 and 6. Do not re-review unchanged parts.

## Output format

Respond in English. Use exactly this structure so the findings can be processed automatically.

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

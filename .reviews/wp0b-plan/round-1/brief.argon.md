# Review brief: WP0-B implementation plan: NCM model instrumentation and G0 reproduction

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- Primary: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/docs/superpowers/plans/2026-11-09-wp0b-model-instrumentation.md`
- Spec it implements: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/research_plan_v3.4.md` (Sections 2.2, 6, 7, 9.2) and `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/DECISIONS.md` (D05, D08, D20, D22, D26, D29, D30)
- Upstream code (unmodified submodule at the pinned commit, read it directly): `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/third_party/ncm/` — especially `models/next_concept.py` (generate, _decode_level_logits), `models/quant.py` (idx_to_zhats, get_next_autoregressive_input, _up_to_full, _apply_quant_resi), `models/vqvae.py`, `scripts/eval_shard.py`, `scripts/eval_merge.py`, `config/eval/sudoku-hard.yaml`
- Existing own code the plan builds on: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/` (grid, validate, solve, dlx, labels, generate, released)

## Context

This plan implements WP0-B of an interpretability study of Next-Concept Modeling (NCM) on Sudoku: safe CPU loading of the released Sudoku-hard checkpoint, an exact mirror of the official evaluation (G0 reproduction against the published 86.1% solve rate), teacher codes, full-length cumulative latent states, and a forward_with_intervention wrapper that produces four branches A/B/C/D (clean, sham restart, perturbed code with replayed suffix, perturbed code with regenerated suffix). Every later experiment (E1 tokenizer/generator split, E2 level sensitivity and compensation, E3 probes on cumulative states, E4 patching) depends on these interfaces being correct and sufficient. The plan was written after reading the upstream code; its section "Upstream facts" lists what it relies on, and a CPU probe already loaded the checkpoints with weights_only=True and solved 109/128 released puzzles in about 1.1 s per puzzle. Execution will be test-driven with bit-for-bit identity tests against upstream generate. Risk tier: medium (set by the user); a design gap here would force rewriting the wrapper before E2/E4.

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
1. Verify every item of the plan section "Upstream facts this plan relies on" against `third_party/ncm` (generate control flow for query_level0 without l0_autoregressive and cfg_scale=0; the level_idx/hidx mapping; get_next_autoregressive_input in-place behaviour; eval_shard decoding path; eval_merge.exact semantics including the cell denominator; prefix_pad_id being None for Sudoku).
2. Task 4 `continue_generation(m, prefix_tokens, given_codes, n_given_levels)`: does mirroring the loop with given codes for levels 1..k reproduce exactly the state upstream would reach (level_pos_embed offsets, level_acum, rope buffers per level, use_post_upsample_conv, transformer.wte), and is this interface sufficient for later E2 dose perturbations (several positions, several levels) and E4 continuous patches on Z_{<=l} or on generator activations H_l (plan v3.4 Section 9.2 route x geometry)? Suggest the smallest interface change that avoids a rewrite later, if any.
3. Task 3 cumulative states: is an own loop mirroring idx_to_zhats with clone() per level correct, and is `decode_state` on partial Z_{<=l} the right decoding path for plan Section 2.2 item 7?
4. Task 5 G0: is the two-part rule (official solved within +/-1.0 pp of 86.1% on the same 2,000 boards; identity tests pass) implementable as specified (identity part via a pytest subprocess), and is the CPU vs CUDA difference the only expected deviation? Are memory measurements via psutil/tracemalloc adequate for plan Section 2.2 item 9?
5. Determinism: torch.use_deterministic_algorithms on CPU, thread count, and batch-size effects (Task 4 test_batch_size_effect_recorded). Is anything missing for the sham B=A test to be meaningful?
6. Security: weights_only=True loading and the test `test_unsafe_checkpoint_refused`; any other upstream path that would unpickle untrusted data.



## Output format

Respond in English. Use exactly this structure so the findings can be processed automatically.

### Verdict
One or two sentences: is the artifact sound enough to proceed, and what is the single most important change?

### Findings
One block per finding, most severe first. ID prefix: `ARGON`.

```
ARGON-<n> | <blocker|major|minor|nit> | <file:line or artifact section>
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

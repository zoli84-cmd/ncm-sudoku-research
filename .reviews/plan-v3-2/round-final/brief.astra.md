# Review brief: NCM-Sudoku research plan v3.3 (final check of R1 fixes)

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- Primary: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/research_plan_v3.3.md`
- Diff against the reviewed version: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/.reviews/plan-v3-2/round-final/changes.diff`
- Decisions: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/DECISIONS.md` (D20-D26)

## Context

The artifact is the authoritative pre-registration-style protocol for an interpretability study of Next-Concept Modeling (NCM, arXiv:2610.14162) on Sudoku. Round R1 (two reviewers) found no blockers but several majors; the accepted fixes were applied to create v3.3. This final round checks that those fixes are correct, complete and internally consistent, and that they introduce no new problems. Code claims refer to HazyResearch/ncm at commit c70274273f489abc73832b2b98584a8483b6b203 (not checked out locally); verify online if you can, otherwise mark could not verify. Risk tier: medium (set by the user).

## Decision log from previous rounds

`C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/.reviews/plan-v3-2/decisions.md`

If a decision log is given: do not re-raise a rejected point unless you have new evidence, and then say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify every concrete claim about the code (files, lines, behaviour) directly in the repository. Say for each checked claim whether it holds.
2. **Hidden risks in the proposed solution**: failure modes, edge cases, concurrency, serialization, migration and rollback, performance under real load, security.
3. **Missing issues or simpler alternatives**: anything important the artifact misses, and any simpler approach that would achieve the same goal.
4. **Prioritization and scope**: is the proposed order and scope right? What should be cut?

Specific focus for this artifact:
1. Section 4.1 distribution gate (D21): is the redesigned procedure (frozen generator, model-free depth gate, TOST at +/-5 pp with 90% interval against the finite released benchmark, simulated batch size, inconclusive vs mismatch, subsets generated after the gate) coherent and free of new leakage or forking paths?
2. Section 2.2 items 1, 2, 5, 6 (D20, D22): is the two-part G0 acceptance rule (+/-1.0 pp of 86.1% on the same 2,000 boards; 100% identity-test agreement) sensible, and is the own per-level cumulative-state loop correctly specified relative to upstream idx_to_zhats?
3. Section 9.2 and 12.2 (D23): are the two E4 patch classes and the per-class primary comparators well defined and consistent with Section 11.1 (E4 has its own primary contrast)?
4. Section 8.3 (D25): does adding level 12 as a secondary comparison and rewording level 2 keep the primary family and multiplicity statements consistent?
5. Sections 15 and 16 ordering and the Section 16 change list: complete and accurate relative to the diff?

Scope: review only the sections changed in `changes.diff` (Sections 2.2, 4, 4.1, 7.1, 8.2, 8.3, 9.2, 12.2, 16) and their direct consequences elsewhere in the plan. Do not re-review unchanged sections.

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

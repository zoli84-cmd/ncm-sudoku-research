# Review brief: NCM–Sudoku research plan v3.2 (methodology protocol)

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- Primary: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/research_plan_v3.2.md`
- Supporting (read as needed): `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/DECISIONS.md` (decisions D01–D19 with rationale), `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/literature/related_work_novelty_check.md` (related-work review), `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/research_plan_v3.md` (predecessor v3.0, for diffing)

## Context

The artifact is the authoritative pre-registration-style protocol for a personal interpretability study of Next-Concept Modeling (NCM, arXiv:2610.14162) on Sudoku: level-wise sensitivity of 12 hierarchical discrete-code levels (E1–E2, with a four-branch A/B/C/D compensation design), linear probes of the generated cumulative latent state for candidate masks and inference depth (E3), and optional targeted patching (E4). It supports the decision to start WP0 (reproduction and instrumentation) and, later, to lock the confirmatory analysis via an embargoed OSF registration. v3.0 already passed two expert reviews; v3.1 and v3.2 added project-setup decisions and a related-work review that were NOT reviewed externally (listed in Section 16). Code claims in the plan refer to the external repository HazyResearch/ncm at commit c70274273f489abc73832b2b98584a8483b6b203 and to the Hugging Face repos hazyresearch/ncm-checkpoints and hazyresearch/ncm-datasets; this local repository contains no upstream code yet. If you can read those sources online, verify against them; otherwise mark code claims as could not verify. Risk tier: medium (set by the user); an error here would invalidate the confirmatory study but is fixable before the lock.

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
1. Section 8.3 'Level choice' and D06: is moving the H1 primary level from 2 to 6 sound? Check the capacity argument (Z_{<=2} = 3 codes x 4 bits = 12 bits; level 6 = 35 codes, at most 140 bits; level code lengths 1,2,4,6,9,13,...) and whether the H1/H2/H3 primary family and the Bonferroni plan in Section 11.1 stay coherent when H1 uses level 6 while H2/H3 use levels 2 and 11.
2. Section 4.1 data sources and D10/D11: own generator (random full grid, greedy clue removal to exactly 30 clues with uniqueness check) versus the released 2,000-board hard set (same 2,000 solutions as easy/medium). Is the ±5 pp solve-rate gate on ~500 puzzles adequately powered and meaningful, and does greedy removal plausibly differ in difficulty from the S-FLM generator? Is tuning on CAL a leakage risk?
3. Section 2.2 item 1 and D08: FP32 eager CPU instead of the paper's BF16 + torch.compile. Does this threaten the G0 reproduction criterion or the interpretation of E2 results relative to the published model behaviour?
4. Section 7.1 'Trained robustness' and the new Section 13 row: is the interpretation of theta_comp against NCM corruption training and non-canonical codes correct and sufficient? Is the four-branch contrast still identifiable given that the generator conditions on the puzzle prefix at every level?
5. Sections 8.3 and 9.2 additions (secondary unit–digit probe target, random-direction control, clean–patched distance): are they well specified and not creating hidden multiplicity or garden-of-forking-paths risks?
6. Statistical plan (Section 11): unit of analysis, cluster bootstrap with 10,000 resamples, exact McNemar usage, and the variance formula Var(delta_hat) = (q - delta^2)/n — check correctness.



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

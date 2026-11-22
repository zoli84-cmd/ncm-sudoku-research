# Review brief: Prompt audit of the Claude Code instruction files, version 2 (Final round)

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- Primary: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/.reviews/prompt-audit/round-final/artifact.md` (version 2)
- Previous version, for comparison: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/.reviews/prompt-audit/round-1/artifact.md` (its appendix quotes the user-level files)
- Project files the hunks edit: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/AGENTS.md`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/paper/AGENTS.md`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/scripts/AGENTS.md`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/AGENTS.md`
- Supporting repository files: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/DECISIONS.md` (D81-D90), `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/scripts/wp4_build.py`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/wholelayer.py`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/wp2e3.py`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/pyproject.toml`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/literature/`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/docs/superpowers/`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/experiments/e3prep/`
- User-level files outside the repository are quoted in the version 1 appendix. Do not try to read them: access outside the repository is denied.

## Context

The artifact audits the instruction text that Claude Code loads in this research repository (a DOX hierarchy of AGENTS.md files plus user-level skills) for stale facts, history narratives, missing live rules and over-broad skill triggers, and proposes hunks to fix them. Round 1 (two reviewers) produced the decisions in the decision log below; version 2 applies them: seven new hunks (H10-H16, including a missing under-review rule from D90), five revised hunks (H2, H4, H5, H7, H8), a corrected finding 6 and a removed code-state argument. The decision it supports is which hunks to apply to the four project AGENTS.md files and two user-level files. Risk tier: medium (no high trigger; user-level files are outside git, hence the backup step). The repository is a preregistered study whose confirmatory run is complete and whose manuscript is under TMLR review; its rules forbid inventing facts.

## Decision log from previous rounds

`C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/.reviews/prompt-audit/decisions.md`

If a decision log is given: do not re-raise a rejected point unless you have new evidence, and then say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify every concrete claim about the code (files, lines, behaviour) directly in the repository. Say for each checked claim whether it holds.
2. **Hidden risks in the proposed solution**: failure modes, edge cases, concurrency, serialization, migration and rollback, performance under real load, security.
3. **Missing issues or simpler alternatives**: anything important the artifact misses, and any simpler approach that would achieve the same goal.
4. **Prioritization and scope**: is the proposed order and scope right? What should be cut?

Specific focus for this artifact:
1. Exactness of the hunks: for each of H1-H5 and H10-H16, does the `-` text match the current file exactly (so the hunk applies), and is every fact in the `+` text true in the repository (file lists against `git ls-files`, D-numbers, commit `fc61836`, forum id, submission number)?
2. H10 and H11 restate D90 (`DECISIONS.md:128`). Do they say exactly what D90 says, no more and no less? In particular, is including `refs.bib` and `generated/` in "the manuscript" justified, and are the two replacement clauses in H11 (lines 82 and 83) reasonable adaptations or invented rules?
3. H14 and H15: are the new wordings accurate (every package module except `dlx.py` has its own test module; plans per work package or stage; the two specs and who cites them)?
4. H16: does the banner keep every step number and every rule of the runbook intact, as D81-D83 require?
5. H5: are the named callers right (`scripts/e3_wholelayer.py` and `wp2e3`)? Is anything in the revised recommendation inconsistent with the decision log?

Scope: review only the sections listed under "Changes since version 1" (H2, H4, H5, H7, H8, H10-H16, finding 6, the removed code-state argument and the recommendation table) plus their direct consequences. Everything else was reviewed in round 1 and is settled in the decision log.

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

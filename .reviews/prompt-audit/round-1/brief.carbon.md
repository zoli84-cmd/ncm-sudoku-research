# Review brief: Prompt audit of the Claude Code instruction files (AGENTS.md hierarchy and user-level skills)

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- Primary: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/.reviews/prompt-audit/round-1/artifact.md`
- Project instruction files it audits: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/AGENTS.md`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/paper/AGENTS.md`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/scripts/AGENTS.md`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/AGENTS.md`
- Supporting repository files: `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/DECISIONS.md` (D81-D89), `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/.gitmodules`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/scripts/wp4_build.py`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/scripts/wp2_e3_extract.py`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/wp2.py`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/g0.py`, `C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/tests/test_wp2.py`
- User-level files outside the repository (`~/.claude/...`, `C:/Users/ako2bp/AGENTS.md`) are quoted in the artifact's appendix. Do not try to read them: access outside the repository is denied. Treat the quoted text as given.

## Context

The artifact is an audit of the instruction text that Claude Code loads in this research repository (a hierarchy of AGENTS.md files under the DOX convention, plus user-level skills and a user-level CLAUDE.md). It looks for text that no longer fits: stale facts the repository contradicts, history narratives in instruction files, migration-relative phrasing, over-broad skill triggers and pressure language that makes the current model (Claude Opus 5.5) over-trigger. It proposes nine edits (H1-H9) and then a second-pass recommendation: adopt H1-H4, H7/H8 and F2 optional, do not adopt H5, H6, H9. The decision it supports is which of these edits to apply. Risk tier: medium (no high trigger; the edits span several instruction files, and three of them sit outside git, so `git revert` cannot undo them). The repository is a preregistered study whose confirmatory TEST run is complete; its rules forbid inventing facts and require that edits under `src/` and `scripts/` do not disturb the recorded code state.

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
1. Stale-fact claims: check H1 (`AGENTS.md:21` vs `AGENTS.md:72`, `.gitmodules`) and H2 (`AGENTS.md:69-70`: do `experiments/e3prep/` and `experiments/lock/` exist and are they tracked?). Does any other line in the four AGENTS.md files state something the repository now contradicts and that the audit missed (for example the claim at `AGENTS.md:64` and `src/ncm_sudoku/AGENTS.md:11` of "one test module per package module": `dlx.py` has no `tests/test_dlx.py`)?
2. Information loss: H3 and H4 remove history from `paper/AGENTS.md:19` and `:31`. Is every removed fact still recorded in `DECISIONS.md` (D85, D88, D89) or elsewhere, and is `--check` really an exact equivalent of `--arxiv` in `scripts/wp4_build.py`?
3. Code-state argument: the artifact claims that editing `src/ncm_sudoku/AGENTS.md` or `scripts/AGENTS.md` makes the recorded code state dirty (`g0.code_state`, `wp2.freeze_state`, `tests/test_wp2.py:226`). Is that accurate, and does it matter after the WP2 TEST completion (D83) and the TMLR submission (D89 onward)? Does it argue against H5 as strongly as the artifact says?
4. The withdrawn H6 draft: the artifact says "the TEST role never deletes outputs" would be false because `wp2_e3_extract.py --resume` and `wp2_e3.py --resume` discard partial outputs even in the TEST role. Verify against `scripts/wp2_e3_extract.py`, `scripts/wp2_e3.py` and `src/ncm_sudoku/wp2.py`. Is "do not adopt now" the right call for H6 and finding 7, or is there a safe, smaller cut (for example removing only review IDs such as "v3.7 review CARBON-1")?
5. F1: the runbook at `scripts/AGENTS.md:22-45` describes a completed procedure. Does keeping it unchanged follow from the DOX rules quoted in the appendix and from the `DECISIONS.md` references (D81-D83), or should it be marked as completed in some minimal way?
6. User-level hunks H7, H8, H9 and the flags F2-F4: judge them only from the quoted text in the appendix. Are the reasons sound, and is the recommendation (H7/H8 optional, H9 rejected) consistent?



## Output format

Respond in English. Use exactly this structure so the findings can be processed automatically.

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

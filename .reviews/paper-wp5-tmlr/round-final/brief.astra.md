# Review brief: TMLR submission build of the preregistered NCM-Sudoku manuscript (anonymous, shortened to 12 pages)

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\main_anon.tex` (anonymous TMLR submission: `\usepackage{tmlr}`, `\anonymoustrue`) and `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\main.tex` (named build, `[preprint]` option)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\body.tex` (title, abstract, section inputs, `\label{main-end}` before the bibliography) and `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\preamble.tex` (`\anon{named}{anonymous}` macro)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\sections\` (all section files; appendix subsections A.3 to A.6 hold the material moved out of the main text)
- Built PDFs: `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\build\main_anon.pdf` (the file to be submitted) and `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\build\main.pdf`; read their text if useful (PyMuPDF is a dev dependency: `uv run --locked python -c "import pymupdf; ..."`)
- Numbers: every `\R{key}` is defined in `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\generated\numbers.json`; sources of truth `experiments\wp2\test\results.json`, the locked protocol `research_plan_v3.7.md` (§13 interpretation table), `osf\registration.md`, `DECISIONS.md` (D83 to D89)
- Design and venue rules: `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\docs\superpowers\specs\2026-11-18-wp5-tmlr-design.md`, `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\docs\venue\tmlr_submission_rules_2026-11-17.md`
- The pre-restructuring manuscript for comparison: `git show bee3d6a~6:paper/sections/<file>.tex` (or `git diff 2ad6498 -- paper/`)

## Context

A personal, preregistered interpretability study of the released NCM Sudoku-hard checkpoint (E1 tokenizer vs. generator; E2 level sensitivity H2 and compensation H3; E3 candidate-mask readability H1) was reviewed in five earlier rounds, then rejected by arXiv moderation without detail (D88). It is now being submitted to Transactions on Machine Learning Research (TMLR), double-blind, as a Regular submission (at most 12 pages of main text). For this, the manuscript was turned into one source with two builds and shortened from about 15.5 to 12 pages by moving descriptive and secondary material verbatim to the appendix and by replacing two paragraphs that repeated the abstract (D89). No number or analysis changed. Risk tier: high, because a journal submission is public and cannot be withdrawn cleanly, and a broken anonymization leads to desk rejection. The decision supported: is the anonymous PDF ready to submit, or what must change first?

## Decision log from previous rounds

`C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\paper-wp4\decisions.md` (five earlier rounds on the content; do not re-raise resolved content points unless the restructuring broke them) and `DECISIONS.md` D86 to D89.

If a decision log is given: do not re-raise a rejected point unless you have new evidence, and then say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify every concrete claim about the code (files, lines, behaviour) directly in the repository. Say for each checked claim whether it holds.
2. **Hidden risks in the proposed solution**: failure modes, edge cases, concurrency, serialization, migration and rollback, performance under real load, security.
3. **Missing issues or simpler alternatives**: anything important the artifact misses, and any simpler approach that would achieve the same goal.
4. **Prioritization and scope**: is the proposed order and scope right? What should be cut?

Specific focus for this artifact:
1. **Main text after shortening.** Read the anonymous PDF as a TMLR reviewer would: does the 12-page main text stand on its own? Check that every confirmatory result, registered reading and "does not follow" boundary, the pre-lock changes, the unrun registered analyses, the E4 paragraph and the AI-use section are still in the main text, and that the new short summaries (introduction Findings, discussion summary, E2 doses summary, E3 unit-level and equivariance summaries, short limitation paragraphs) say nothing the appendix detail does not support.
2. **Anonymity.** Search the anonymous PDF (text and metadata) and the `\anon` passages in `setup.tex`, `appendix.tex`, `statements.tex` for anything that identifies the author: name, ORCID, GitHub user or repository, OSF identifiers or DOI, own commit hashes or tag names, employer or university, single-author wording. The third-party Quantix-eng repository in the references is fine.
3. **TMLR compliance.** Unmodified `tmlr.sty` usage, first-page footnote on LLM use (TMLR FAQ), length (main text ends on page 12, `\label{main-end}`), author-year citations reading naturally, no acknowledgements, CC BY 4.0 statement.
4. **Appendix organization and cross-references.** Do references from the main text to floats now in the appendix (`tab:e1`, `fig:e1-levels`, `fig:dose-curves`, `fig:propagation`, `fig:damage-curves`, `fig:e3-supporting`) read well? Is the appendix order (A.1 to A.7) sensible?
5. **One open placement question.** The sentence that the registration stated the observed equivariance pattern as the expected outcome moved to the appendix with the equivariance details. Should it be in the main-text summary?

Review the full anonymous manuscript, with emphasis on what the restructuring changed (`git diff 2ad6498 -- paper/sections paper/body.tex paper/main.tex paper/main_anon.tex paper/preamble.tex`).

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

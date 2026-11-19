# Review brief: TMLR submission, delta check of the final-round fixes (anonymous build)

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- The change under review: `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\paper-wp5-tmlr\round-tmlr-delta\changes.diff` (equivalently `git show 2c2d652 -- paper/body.tex paper/sections`)
- Changed files in their current state: `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\sections\discussion.tex`, `e1.tex`, `e2.tex`, `e3.tex`, `appendix.tex` (same folder) and `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\body.tex`; the anonymous top file is `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\main_anon.tex`, and `\anon{named}{anonymous}` is defined in `paper\preamble.tex`
- Built anonymous PDF (the file to be submitted): `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\build\main_anon.pdf`; read its text if useful (`uv run --locked python -c "import pymupdf; ..."`, read-only)
- Numbers: every `\R{key}` is defined in `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\generated\numbers.json`; sources of truth `experiments\wp2\test\results.json`, the locked protocol `research_plan_v3.7.md`, `osf\registration.md`

## Context

A personal, preregistered interpretability study of the released NCM Sudoku-hard checkpoint (E1, E2 with H2/H3, E3 with H1) is about to be submitted to Transactions on Machine Learning Research as a double-blind Regular submission (main text at most 12 pages). The anonymous build was reviewed in a final round by two reviewers (ASTRA and CARBON); the accepted findings were applied in commit 2c2d652, and that change has not been reviewed by anyone. It restores two disclosures lost during shortening (a solution-digit reference value; E2 format-error rates), states both reasons the registered area comparisons could not be computed plus one propagation value, lists the untested readouts precisely, puts the registered equivariance expectation in the main text, adds appendix pointers and A.x numbering for appendix floats, and changes the anonymous code-release wording. Risk tier: high, because the submission is public and a deanonymizing detail or a misstated number cannot be withdrawn and may cause desk rejection. The decision supported: can the anonymous PDF be submitted as is?

## Decision log from previous rounds

`C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\paper-wp5-tmlr\decisions.md` (the triage of the ASTRA and CARBON final rounds, including which findings were accepted and why ASTRA-5, adding the registration date, was rejected for anonymity) and `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\paper-wp4\decisions.md` (earlier content rounds).

If a decision log is given: do not re-raise a rejected point unless you have new evidence, and then say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify every concrete claim about the code (files, lines, behaviour) directly in the repository. Say for each checked claim whether it holds.
2. **Hidden risks in the proposed solution**: failure modes, edge cases, concurrency, serialization, migration and rollback, performance under real load, security.
3. **Missing issues or simpler alternatives**: anything important the artifact misses, and any simpler approach that would achieve the same goal.
4. **Prioritization and scope**: is the proposed order and scope right? What should be cut?

Specific focus for this artifact:
1. **Each new sentence against its source.** For every sentence added in the diff, check that it is true and correctly scoped against the cited `\R{}` values and their sources: the solution-digit Brier reference (`soldigit.brier`; computed after TEST, level 12, exploratory) in `discussion.tex`; the E2 format-error rates (`e2.l1.uniform.fmtC`, `e2.l1.frequency.fmtC`) and the claim that such outputs stay in the solve denominator as unsolved; the two reasons in `e2.tex` (which levels lacked TEST coverage of the frozen calibration range, which had no frozen range) and the propagation value `e2.prop.level1-frequency.L11`; the list of untested readouts and the "a per-cell MLP improved only marginally" clause; the sentence in `e3.tex` that the registration stated the PROBE-VAL pattern as the expected outcome (check against `research_plan_v3.7.md` / `osf\registration.md`).
2. **Anonymity of the new wording.** The anonymous branch of the code-release passage in `appendix.tex` ("will be released"; anonymized archive available to reviewers on request) and anything else added: does it identify the author, or promise something inconsistent with a double-blind submission?
3. **Claim boundaries.** The added sentences must keep the hedging of the locked protocol: nothing should read as a confirmatory result where the source is exploratory or descriptive.
4. **Appendix numbering and pointers.** Figures and tables after `\appendix` are numbered A.1, A.2, ... and each appendix subsection from E2 on starts with `\clearpage`. Do the main-text pointers ("in Appendix ...") point to the right subsections, and does the A.x numbering read unambiguously next to appendix section letters in the PDF?
5. **Side effects on the main text.** Confirm in the PDF that the main text still ends on page 12 and that the additions did not push a float or a sentence into an awkward place.

Scope: review only the changes in `changes.diff` and their direct consequences in the anonymous PDF. Everything else was reviewed in the final rounds; do not re-review it.

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

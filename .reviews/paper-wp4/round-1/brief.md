# Review brief: WP4 manuscript draft (preregistered NCM-Sudoku study), round 1

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

**Read repository files only.** Do not open any file outside `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research`. Do not run Python, `uv run`, PowerShell or other execution commands; verify by reading files only. If any read is denied, note it in one line under "Claims checked" and finish the review.

**Keep the final answer short: at most about 1,500 words in total.** Report blocker and major findings in full; list minor findings as one line each (at most eight) and at most three nits. Keep "Claims checked" to at most ten one-line items. A longer answer is truncated and the whole review is lost.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\main.tex` (title, abstract, section order)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\sections\` (`introduction.tex`, `background.tex`, `setup.tex`, `e1.tex`, `e2.tex`, `e3.tex`, `discussion.tex`, `appendix.tex`)
- Every result number in the text is a macro `\R{key}`; the values are in `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\generated\numbers.json` (key -> formatted value; `\ensuremath{-}` is a minus sign). Generated tables are in `paper\generated\tables\*.tex`; figures are PDFs in `paper\generated\figures\` (you cannot view them; their content is defined in `src\ncm_sudoku\wp4figures.py`).
- Sources of truth: the confirmatory results `experiments\wp2\test\results.json` and their rendered report `experiments\wp2\test\report.md`; the locked protocol `research_plan_v3.7.md` (especially §1, §5, §7, §8, §11, §13 and §15); the decision log `DECISIONS.md` (D41, D42, D43, D64–D68, D78–D84); the mapping from macro keys to result fields in `src\ncm_sudoku\wp4numbers.py` (`KEYS`).

## Context

Personal interpretability research project on Next-Concept Modeling (NCM), a coarse-to-fine generator of discrete code hierarchies, applied to Sudoku. The protocol was preregistered (OSF, tag `prereg-v3.7`) and the confirmatory study (E1 tokenizer vs. generator; E2 level sensitivity H2 and compensation H3; E3 candidate-mask readability H1, plus secondary and exploratory analyses) was run once on 600 TEST puzzles and evaluated by a pre-written script (D83). The optional causal study E4 was dropped after the TEST results (D84). This artifact is the first complete draft of the arXiv preprint reporting these results; its central message, chosen by the author, is an integrated picture of where the Sudoku logic shows up in the hierarchy, including null and below-threshold results. Risk tier: high, because a public preprint with confirmatory claims cannot be withdrawn cleanly. The decision supported: what must change before the manuscript goes to further review rounds and, eventually, to arXiv.

## Decision log from previous rounds

None (round 1).

## What to check

Generic checks, always:
1. **Fact-check**: verify concrete claims against the sources of truth listed above. Say for each checked claim whether it holds.
2. **Hidden risks**: overclaiming, claims that contradict the registered interpretation table (plan §13), numbers attached to the wrong quantity, wrong interval type or level, statements about prior work that the cited source (as summarised in plan §2.1, §8.3, §15 and `literature/related_work_novelty_check.md`) does not support.
3. **Missing issues**: pre-specified results or limitations the manuscript omits, or disclosures a reader of a preregistered study would expect.
4. **Prioritization and scope**: what to cut, what to move, what a reader needs first.

Specific focus for this artifact:
1. **Numbers and their meaning.** For each `\R{key}` used in the prose, check in `wp4numbers.py` which result field it reads and whether the sentence describes that field correctly (sign, unit: Brier vs. percentage points vs. percent, interval type: 98.33% family vs. 95% individual vs. 96.67% TOST vs. 90% TOST vs. rare-event bound). Pay particular attention to `e2.tex` (H2, H3, θ₂′, dose and propagation statements) and `e3.tex` (H1, controls, level 12, equivariance).
2. **Claim boundaries (plan §13).** Every confirmatory statement must stay within its §13 "justified claim" and must not assert anything in its "does not follow" column. Check especially the abstract (`main.tex`), the "Findings" paragraph of `introduction.tex` and §"Where the Sudoku logic shows up" in `discussion.tex`, which interpret across experiments.
3. **Descriptive vs. inferential.** The E2 dose curves, the propagation diagnostics, the E1 per-level curves, the E3 depth breakdown and the equivariance result carry no inference. Flag any sentence that reads them as tested effects.
4. **Disclosure of post-registration decisions.** Is the handling of D78, D79, D81, D82 and D84 (appendix, setup, discussion) accurate and sufficient, in particular that E4 was dropped after seeing the TEST results, and that the primary H2 level was moved to level 1 before the lock on calibration data (D43)?
5. **Related work and novelty.** Are the statements about prior work in `background.tex` and `discussion.tex` supported by the plan's source summaries, and is the novelty claim appropriately narrow?
6. **Structure for a reader.** Is the order (Introduction, Background, Setup, E1, E2, E3, Discussion) and the placement of the primary-results tables (currently in `e3.tex`) right for an arXiv preprint?

## Output format

Respond in English. Use exactly this structure so the findings can be processed automatically.

### Verdict
One or two sentences: is the draft sound enough to proceed, and what is the single most important change?

### Findings
One block per blocker or major finding, most severe first. ID prefix: `{{ID_PREFIX}}`.

```
{{ID_PREFIX}}-<n> | <blocker|major> | <file:line or section>
Claim: <what is wrong or missing, one or two sentences>
Evidence: <what you checked, with file:line>
Recommendation: <concrete change>
Confidence: <high|medium|low>
```

Then minor findings as one line each: `{{ID_PREFIX}}-<n> | minor | <location> | <claim and recommendation>`, and at most three nits in the same form.

Severity definitions:
- **blocker**: publishing as written would state a wrong result, a claim the registered interpretation forbids, or misreport the preregistration.
- **major**: a significant risk of misreading, a missing disclosure or result a reader would need, or a clearly better structure.
- **minor**: a real but contained issue; fix if cheap.
- **nit**: wording, style or preference.

Rules: only report what you checked or can argue concretely. If you could not verify a claim, say so with Confidence: low. Do not pad: zero findings in a category is a valid result.

### Claims checked
At most ten one-line items, each marked holds / does not hold / could not verify.

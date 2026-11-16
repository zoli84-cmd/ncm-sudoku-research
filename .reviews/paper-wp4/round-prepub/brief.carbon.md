# Review brief: WP4 manuscript (preregistered NCM-Sudoku study), pre-publication round

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

**Read repository files only.** Do not open any file outside `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research`. Do not run Python, `uv run`, PowerShell or other execution commands; verify by reading files only. If any read is denied, note it in one line under "Claims checked" and finish the review.

**Keep the final answer short: at most about 1,500 words in total.** Report blocker and major findings in full; list minor findings as one line each (at most eight) and at most three nits. Keep "Claims checked" to at most ten one-line items. A longer answer is truncated and the whole review is lost.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\main.tex` (title, author line, abstract, section order) and `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\preamble.tex`
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\sections\` (`introduction.tex`, `background.tex`, `setup.tex`, `summary.tex`, `e1.tex`, `e2.tex`, `e3.tex`, `discussion.tex`, `statements.tex`, `appendix.tex`)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\refs.bib` (bibliography, plainnat style)
- Every result number in the text is a macro `\R{key}`; the values are in `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\generated\numbers.json` (key -> formatted value; `\ensuremath{-}` is a minus sign). Generated tables are in `paper\generated\tables\*.tex`; figures are PDFs in `paper\generated\figures\` (you cannot view them; their content is defined in `src\ncm_sudoku\wp4figures.py`, and the figure captions are in the section files).
- Sources of truth: the confirmatory results `experiments\wp2\test\results.json` and their rendered report `experiments\wp2\test\report.md`; the locked protocol `research_plan_v3.7.md` (especially §1, §5, §7, §8, §11, §13 and §15); the decision log `DECISIONS.md` (D41, D42, D43, D64–D68, D78–D84); the mapping from macro keys to result fields in `src\ncm_sudoku\wp4numbers.py` (`KEYS`); the pre-submission literature check `literature\presubmission_update_2026-11-16.md` (verified quotes from every cited source) and `literature\related_work_novelty_check.md`.

## Context

Personal interpretability research project on Next-Concept Modeling (NCM), a coarse-to-fine generator of discrete code hierarchies, applied to Sudoku. The protocol was preregistered (OSF, tag `prereg-v3.7`) and the confirmatory study (E1 tokenizer vs. generator; E2 level sensitivity H2 and compensation H3; E3 candidate-mask readability H1, plus secondary and exploratory analyses) was run once on 600 TEST puzzles and evaluated by a pre-written script (D83); the optional causal study E4 was dropped after the TEST results (D84). The manuscript has passed three review rounds (R1, R2, Final; decision log below). Since then it changed in these places: figures are now drawn at the final text width (page geometry in `preamble.tex`) in Computer Modern, and the E2 forest plot draws each threshold only on its rows; the related-work paragraph in `discussion.tex` (new citations of the Quantix-eng exploratory notes and Oh et al. 2026, narrowed Khoury sentence), the "Trained robustness" paragraph in `discussion.tex` and the matching sentence in `e2.tex` (training corruption attributed to the method), `background.tex` (Garg 2026); `refs.bib` (full author lists, venues, DOIs); the author line in `main.tex`; the licence sentence in `appendix.tex`; and the new AI-use statement `statements.tex`. This is the last review before the preprint goes public on arXiv and the repository is published. Risk tier: high, because a public preprint with confirmatory claims cannot be withdrawn cleanly. The decision supported: whether anything must still change before publication; look for every error that would be embarrassing or misleading once public.

## Decision log from previous rounds

`C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\paper-wp4\decisions.md` (rounds 1, 2 and Final, every item applied). Do not re-raise resolved points unless the fix is wrong or incomplete; say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify concrete claims against the sources of truth listed above. Say for each checked claim whether it holds.
2. **Hidden risks**: overclaiming, claims that contradict the registered interpretation table (plan §13), numbers attached to the wrong quantity, wrong interval type or level, statements about prior work that the cited source does not support.
3. **Missing issues**: pre-specified results or limitations the manuscript omits, or disclosures a reader of a preregistered study would expect.
4. **Prioritization and scope**: what to cut, what to move, what a reader needs first.

Specific focus for this artifact:
1. **Whole-document consistency.** Read the full manuscript once end to end as a first-time reader: do abstract, introduction findings, summary table, experiment sections and discussion state the same results with the same numbers, signs, interval types and hedges? Flag any contradiction between sections, and any cross-reference (`\ref`, table or figure number, section name) that points to the wrong place.
2. **Numbers and their meaning.** For each `\R{key}` in the prose, check in `wp4numbers.py` which result field it reads and whether the sentence describes that field correctly (sign, unit: Brier vs. percentage points vs. percent, interval type: 98.33% family vs. 95% individual vs. 96.67% TOST vs. rare-event bound).
3. **Figures against captions.** For each figure function in `src\ncm_sudoku\wp4figures.py` (`dose_curves`, `contrasts_forest`, `propagation`, `e3_readability`, `e3_supporting`, `e1_levels`), check that the caption in the section file describes what the code draws (series, line styles, intervals, thresholds, axes) and that legends and axis labels are correct.
4. **Prior work and bibliography.** Check every sentence that cites a source against the verified quotes in `literature\presubmission_update_2026-11-16.md`, especially the new Quantix-eng, Khoury, Oh et al. and Garg sentences; check `refs.bib` for wrong or incomplete metadata and for any claim of novelty that the Quantix-eng notes contradict.
5. **Publication-facing text.** Author line, AI-use statement (`statements.tex`), licence sentence and reproducibility paragraph (`appendix.tex`, the repository URL is a known placeholder until publication): are they accurate, complete and consistent with what the repository shows (tags `prereg-v3.7` and `wp2-code`, root `LICENSE`, OSF link), and is anything a reader of a preregistered study would expect missing (e.g. data and checkpoint provenance, compute)?
6. **Claim boundaries (plan §13).** Every confirmatory statement must stay within its §13 "justified claim" and must not assert anything in its "does not follow" column; descriptive results (dose curves, propagation, E1 per-level curves, depth breakdown, equivariance) must not be read as tested effects.

## Output format

Respond in English. Use exactly this structure so the findings can be processed automatically.

### Verdict
One or two sentences: is the draft sound enough to proceed, and what is the single most important change?

### Findings
One block per blocker or major finding, most severe first. ID prefix: `CARBON`.

```
CARBON-<n> | <blocker|major> | <file:line or section>
Claim: <what is wrong or missing, one or two sentences>
Evidence: <what you checked, with file:line>
Recommendation: <concrete change>
Confidence: <high|medium|low>
```

Then minor findings as one line each: `CARBON-<n> | minor | <location> | <claim and recommendation>`, and at most three nits in the same form.

Severity definitions:
- **blocker**: publishing as written would state a wrong result, a claim the registered interpretation forbids, or misreport the preregistration.
- **major**: a significant risk of misreading, a missing disclosure or result a reader would need, or a clearly better structure.
- **minor**: a real but contained issue; fix if cheap.
- **nit**: wording, style or preference.

Rules: only report what you checked or can argue concretely. If you could not verify a claim, say so with Confidence: low. Do not pad: zero findings in a category is a valid result.

### Claims checked
At most ten one-line items, each marked holds / does not hold / could not verify.

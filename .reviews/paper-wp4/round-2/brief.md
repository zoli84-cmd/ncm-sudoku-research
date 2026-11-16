# Review brief: WP4 manuscript draft (preregistered NCM-Sudoku study), round 2 on the round-1 changes

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

**Read repository files only.** Do not open any file outside `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research`. Do not run Python, `uv run`, PowerShell or other execution commands; verify by reading files only. If any read is denied, note it in one line under "Claims checked" and finish the review.

**Keep the final answer short: at most about 1,200 words in total.** Report blocker and major findings in full; list minor findings as one line each (at most six) and at most three nits. Keep "Claims checked" to at most eight one-line items. A longer answer is truncated and the whole review is lost.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state. Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\paper\main.tex` and `paper\sections\*.tex` (new: `summary.tex`)
- `C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\paper-wp4\round-2\r1.diff`: exactly what changed in round 1 (manuscript sources and the generator modules `src\ncm_sudoku\wp4tables.py`, `wp4numbers.py`, `wp4figures.py`)
- Every result number in the text is a macro `\R{key}`; values in `paper\generated\numbers.json`; key-to-field mapping in `src\ncm_sudoku\wp4numbers.py` (`KEYS`); generated tables in `paper\generated\tables\*.tex`.
- Sources of truth: `experiments\wp2\test\results.json`, `experiments\wp2\test\report.md`, `research_plan_v3.7.md` (§7, §8, §11, §13), `DECISIONS.md` (D43, D45, D64–D68, D77–D84), `literature\kniazev_fijalkow_2026_unit_probe.md`.

## Context

Personal interpretability research project on Next-Concept Modeling (NCM), a coarse-to-fine generator of discrete code hierarchies, applied to Sudoku. The confirmatory study (E1; E2 with H2 and H3; E3 with H1) was preregistered and run once on 600 TEST puzzles. This artifact is the draft arXiv preprint. Round 1 (two reviewers) found 3 blockers and 9 majors, all accepted and applied: preregistration chronology, cross-experiment claims within the registered interpretation table (§13), the relative cumulative-state distance in E2, the description of prior work, the surface-feature control, registered secondary metrics and E2 diagnostics as new generated tables, disclosure of pilot-driven pre-lock design changes, magnitude versus signed intervals, probe methods and seed stability, the E4 drop wording, and a new summary section with every triggered §13 row. Risk tier: high (a public preprint with confirmatory claims). The decision supported: whether the revised draft can go to the final review round.

## Decision log from previous rounds

`C:\Users\ako2bp\Documents\VS Code Projects\NCM-research\.reviews\paper-wp4\decisions.md`. Do not re-raise resolved points unless the fix is wrong or incomplete; say what is new.

## Scope

Review only the sections changed in round 1 (see the diff) and their direct consequences. For each accepted round-1 item, check that the fix is correct against the sources of truth and complete, and that it introduces no new defect (a new number bound to the wrong field, a new claim beyond §13, an inconsistency between sections, a broken cross-reference).

## What to check

1. **New numbers.** Every new `\R{key}` in the diff: does its `KEYS` entry read the field the sentence describes (unit, sign, interval type, quantile index; for example `h2.fam.abs.lo/hi`, `e2.l1.frequency.pnew.med`, `depth.*`, `sec.*`, `unit.*`)?
2. **Claim boundaries.** The revised abstract, introduction ("Findings"), `summary.tex`, the discussion summary, and the new sentences on the surface control, the unit-level target and equivariance: within §13 and the exploratory status where applicable?
3. **Disclosures.** The new "Changes before the lock" paragraph in `setup.tex`, the deviations table (`DEVIATIONS` in `wp4tables.py`) and the appendix text: accurate against `DECISIONS.md`, complete, not contradictory between sections?
4. **New tables.** `summary_table`, `readings_table`, `secondary_table`, `depth_table`, `levels_table`, `e2_diagnostics_table` in `wp4tables.py`: right fields, right labels and captions, right interval types (for example the equivalence column and the rare-event bound of the level 2 versus 11 contrast)?
5. **E2 propagation text.** Is the new explanation of the relative cumulative-state distance (constant absolute difference in branch C) correct against `src\ncm_sudoku\states.py` and `e2p2.py`?

## Output format

Respond in English. Use exactly this structure.

### Verdict
One or two sentences: can the revised draft go to the final round, and what is the single most important remaining change?

### Findings
One block per blocker or major finding, most severe first. ID prefix: `{{ID_PREFIX}}`.

```
{{ID_PREFIX}}-<n> | <blocker|major> | <file:line or section>
Claim: <one or two sentences>
Evidence: <what you checked, with file:line>
Recommendation: <concrete change>
Confidence: <high|medium|low>
```

Then minor findings as one line each: `{{ID_PREFIX}}-<n> | minor | <location> | <claim and recommendation>`, and at most three nits in the same form.

Severity: blocker = publishing as written would state a wrong result, a claim the registered interpretation forbids, or misreport the preregistration; major = a significant risk of misreading or a missing disclosure; minor = real but contained; nit = wording.

### Claims checked
At most eight one-line items, each marked holds / does not hold / could not verify.

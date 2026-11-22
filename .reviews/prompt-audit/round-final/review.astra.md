Verdict

Proceed with the D90 manuscript rule, but not with the recommendation table unchanged. The most
important change is to separate the recorded under-review rule from H11’s two proposed obligations:
neither was approved by D90.

Findings

ASTRA-1 | major | H11 and recommendation table, artifact.md:98–103,156
Claim: “Adopt first” includes two instructions the artifact itself says need confirmation.
Rechecking venue rules before an upload is sensible advice; requiring a new search whenever a
revision touches related work is a different trigger from the original submission-delay rule.
Evidence: DECISIONS.md:128 restricts manuscript changes to the OpenReview revision process.
research_plan_v3.7.md:40 requires a search before submission;
literature\presubmission_update_2026-11-16.md:3–6 records that search. Neither establishes a
post-submission search or venue-check schedule.
Recommendation: Adopt the status update at AGENTS.md:62 and the literature inventory addition now.
Remove the expired clauses at lines 82–83; list their proposed replacements separately as user
decisions, not D90 requirements.
Confidence: high

ASTRA-2 | major | H5, H14, H16 and H8, artifact.md:80,121,137,147
Claim: These deletion lines contain editorial ellipses, not the literal target text. H16 is the
consequential case: pasting its replacement as a whole line would preserve steps 1–8 but remove the
runbook’s --locked instruction and its explanation of why resume can fail.
Evidence: The real text continues at src\ncm_sudoku\AGENTS.md:27, AGENTS.md:64 and
scripts\AGENTS.md:22. H8 likewise omits both ends of the description quoted in
.reviews\prompt-audit\round-1\artifact.md:119.
Recommendation: Make H16 a banner inserted above the unchanged line. For H5 and root H14, specify
exact substring replacements rather than reproducing long index entries. For H8, replace only the
trigger sentence. Before H7 deletes a whole file, check that its live contents still match the
backed-up, graphify-only text.
Confidence: high

ASTRA-3 | minor | H10, artifact.md:89
Claim: The bibliography and rendered generated content are part of the manuscript, but D90 does not
define a freeze on every file under generated/. The distinction matters because not every generated
file enters the paper.
Evidence: paper\body.tex:26 uses refs.bib; paper\preamble.tex:14 and
paper\sections\summary.tex:11,19 load generated content. By contrast, generated/numbers.json is
produced alongside the TeX and read by lint, not by the manuscript (scripts\wp4_figures.py:47,
tests\test_texlint.py:99). paper\AGENTS.md:9–10 already defines ownership and forbids hand-editing
generated files.
Recommendation: Use D90’s sentence verbatim: “No change to the manuscript while under review except
through the OpenReview revision process.” Leave file ownership to the existing bullets; use the root
entry to point to the paper contract.
Confidence: high

ASTRA-4 | minor | H12, artifact.md:108
Claim: The public date is correct, but “citing the tag hash” identifies the wrong Git object if read
literally.
Evidence: osf\registration.md:5 cites the tag name and commit 3e39bc8…, consistent with D75 at
DECISIONS.md:113. git rev-parse refs/tags/prereg-v3.7 returns the annotated tag object fe4e66c…;
peeling the tag returns the registered commit 3e39bc8….
Recommendation: Say “an OSF registration citing the tag name and tagged commit.” Keep the D85 public
date; do not change the frozen plan or registration.
Confidence: high

ASTRA-5 | minor | H4, artifact.md:75
Claim: The file scope is now right, but the guarantee is still too broad for valid multiline TeX.
Evidence: scripts\wp4_build.py:18–19,32–44,119–124 strips comments and matches each physical line
separately. The matcher finds \placeholder{draft} but not an argument spanning two lines, or
\placeholder {draft} with a space.
Recommendation: Say the check rejects “uncommented, single-line literal \placeholder{...}
occurrences” in the listed files. No build-script change is needed.
Confidence: high

ASTRA-6 | minor | H14 and H15, artifact.md:122–132
Claim: Both inventories still imply a one-to-one correspondence. H14 holds for implementation
modules other than dlx.py, not for every tracked Python file; H15 describes how plans are organized,
not a guarantee that every stage has one.
Evidence: Of 36 tracked package .py files, 34 have a same-named test. src\ncm_sudoku\__init__.py:1
is docstring-only; tests\test_solve.py:4–13 exercises both solvers. The WP4 design explicitly puts
phase 2 outside the implementation plan
(docs\superpowers\specs\2026-11-15-wp4-manuscript-design.md:96–98).
Recommendation: Use “module tests live in tests/; the two solvers share test_solve.py” and
“implementation plans for work packages and selected stages.” Keep the specs entry as written.
Confidence: high

ASTRA-7 | minor | Finding 6, artifact.md:30
Claim: The corrected docstring attribution holds, but its example of information “found nowhere
else” does not. This is new evidence about the example, not a reason to reopen the deferred
condensation.
Evidence: src\ncm_sudoku\AGENTS.md:27 explicitly documents the same three e3metrics re-exports as
scripts\AGENTS.md:53. scripts\e3_probes.py:39 imports them and tests\test_e3metrics.py:168–174
asserts their identities. The compare_dirs function docstring itself is at
scripts\wp2_e3_extract.py:122–124.
Recommendation: Say the index contains cross-module relationships not captured by individual script
docstrings. Drop the uniqueness claim and keep H6 deferred.
Confidence: high

ASTRA-8 | minor | H10 and post-edit verification, artifact.md:89,166
Claim: The recommended pytest run can replace the local PDF at the very path H10 names as submission
provenance. A later file at that path is not proof of the bytes uploaded.
Evidence: With Tectonic installed, tests\test_wp4_build_script.py:177–180 performs a real anonymous
build in place. scripts\wp4_build.py:87–91 writes to paper/build/, which .gitignore:26 excludes. D90
records the source commit and submission, not a PDF digest.
Recommendation: Treat the path as the historical build path, not an archive. If the exact local
submission copy must be retained, run post-edit verification in a disposable checkout. Rebuilding
does not change the OpenReview submission.
Confidence: high

Claims checked

 - Holds — literal deletion text: H1–H4, H10’s purpose line, all three H11 lines, H12, both H13
lines, H14’s package-doc line and H15 match their targets exactly. H10’s new bullet has no deletion.
Does not hold: H5, root H14 and H16 as full lines; H8 also fails against the quoted appendix line.
These are text comparisons, not a claim that the report is a unified patch.
 - Holds — H1–H4 facts: The clean upstream checkout and tracked gitlink both resolve to
c70274273f489abc73832b2b98584a8483b6b203. H2 matches all 16 tracked E3-prep files and all six lock
files; scripts\e3_budget_sensitivity.py:1–7,27–33 accounts for the three nested outputs. H3 leaves
the ASCII and \pdfoutput instructions intact; D88–D89 record the retirement. H4’s named sources,
comment handling, flag alias and absence of current placeholder uses hold, subject to ASTRA-5.
 - Holds — H5 and code state: Both callers use the cell and raw PCA helpers
(scripts\e3_wholelayer.py:42–43,97,131; src\ncm_sudoku\wp2e3.py:59,116,200). The golden checks cover
the pre-lock scripts and matching WP2 stages (tests\test_e3_scripts.py:266–271;
tests\test_wp2e3.py:146–158). Adopting H5 on clarity grounds is consistent with R1. Credit the
caller facts to code, not the table’s generic DECISIONS.md rationale. g0.py:53–62 uses path-scoped
dirtiness and repo-wide HEAD; main is not the wp2-code commit required by wp2.py:231.
 - Holds — submission and publication records: D89–D90 (DECISIONS.md:127–128) support the
shared-source builds, Regular 12-page limit, submission date 2026-11-19, number 14707, forum
rDTv8xpA9g and anonymous PDF built from fc61836. The commit resolves locally. D85 confirms the
registration, not the private OSF project, became public on 2026-11-16. H11 names all four tracked
literature files; the Kniazev note identifies arXiv:2605.18847 and its code at
literature\kniazev_fijalkow_2026_unit_probe.md:1–5.
 - Holds — H13–H16 and finding 6: No R script is tracked; D87 records that the GLMM was not run, and
neither SciPy nor statsmodels is declared or imported in tracked Python. Eight plans and two specs
are tracked; paper\AGENTS.md:5 cites both specs. D81 and D82 cite step 4; D83 records completion and
cites steps 5–8 (DECISIONS.md:119–121). An insertion-only H16 preserves every step and rule.
scripts\AGENTS.md:53 is 18,798 bytes, consistent with “about 18 KB.”
 - Holds — H7/H8 recommendation: H8 retains explicit build, update and query requests without
requiring an existing graph; H7 remains optional with backup, fresh-session check and rollback, as
R1 decided. Could not verify (low confidence): current user-level file contents, live /graphify
dispatch or installer behavior. The appendix is snapshot evidence, not a live check.


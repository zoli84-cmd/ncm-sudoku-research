Verdict

Adopt H1–H3 and a narrower H4, but revise the second-pass recommendations before applying the rest.
The most important change is to mark the WP2 runbook as completed and historical while preserving
the numbered steps cited by the decision log.

Findings

SOL-1 | major | artifact F1; scripts/AGENTS.md:22–45,53
Claim: Keeping the numbered runbook is justified; keeping it framed as an active procedure is not.
The instructions also overstate what happens if evaluation fails and describe the dry check as
read-only even though it replaces approval files.
Evidence: DECISIONS.md:119–121 cites steps 4 and 5–8 and records that TEST and evaluation completed.
scripts/wp2_evaluate.py:180–187,817–819 renders the report before writing, but the two writes are
separate: failure on the second can leave results.json and block another single-look evaluation.
scripts/wp2_dry_check.py:497–503 deletes the previous approval before checking the freeze.
Recommendation: Add a one-line historical banner citing D83 and directing readers to the committed
TEST report rather than to reruns or retagging. Preserve the step numbers. Clarify that only failure
before publication leaves both outputs absent, and describe the dry checker as model-free, not
read-only.
Confidence: high

SOL-2 | major | artifact H7–H8; appendix graphify excerpts
Claim: The appendix does not establish that deleting the global block preserves /graphify. H8 is a
reasonable optional narrowing, but the existence of graphify-out/ should gate automatic use, not
explicit setup or refresh requests.
Evidence: The quoted CLAUDE.md:2–5 explicitly invokes graphify; the quoted SKILL.md:1–5 shows a
graphify directory, name: graphify-windows, and trigger: /graphify. Those excerpts do not establish
which name the harness registers or whether dispatch works without the block. The repository has no
graphify-out/, consistent with AGENTS.md:34.
Recommendation: Leave H7 pending a Claude Code dispatch check without the block. If opting into H8,
retain explicit requests for graph creation and refresh, and limit incidental triggering to relevant
questions in projects with a usable graph. Preserve the original user-level text and validate
changes separately; repository pytest cannot verify global skill dispatch.
Confidence: low

SOL-3 | minor | artifact Second-pass recommendation §1; H5
Claim: The dirty-state mechanism is real, but committing clears the dirty flag, not the recorded
identity mismatch. The artifact gives too much weight to this mechanism when deciding whether to
edit current-branch documentation after TEST.
Evidence: src/ncm_sudoku/g0.py:53–62 includes HEAD and checks src, scripts, pyproject.toml and
uv.lock. src/ncm_sudoku/wp2.py:215–234,336–359 requires the tag for TEST and compares stored code on
resume. tests/test_wp2.py:224–228 covers an untracked AGENTS.md; :249–256 shows that even an
out-of-scope docs commit breaks the freeze by moving HEAD. Here HEAD is already 98146e5, not the
wp2-code commit 1047668; the committed TEST report still records the latter
(experiments/wp2/test/report.md:6). D83 records completion and D90 records the subsequent TMLR
submission (DECISIONS.md:121,128).
Recommendation: Defer H5 as a standalone cosmetic edit, not as a threat to recorded results. If
already correcting the package instructions, say the PCA helpers are shared by e3_wholelayer.py and
wp2e3.py, rather than calling them helpers “of” the script. Keep the tag and artifacts unchanged,
and avoid such edits during an active resumable run.
Confidence: high

SOL-4 | minor | artifact H4; paper/AGENTS.md:19,32
Claim: The alias replacement is exact, but H4 retains an overbroad placeholder guarantee. The
neighboring verification bullet also overstates identifier detection and omits the LaTeX log check.
Evidence: scripts/wp4_build.py:18,32–44,113–139 registers both flags on one argparse action and
scans literal, uncommented placeholders only in the top-level sources, body and section files; it
does not scan preamble.tex or generated includes. Checked builds of either variant inspect the log;
the anonymous check searches a defined identifier list plus the generated code commit in extracted
text, metadata and links (:23–29,53–71,94–102).
Recommendation: Adopt --check and drop the dated note, but describe the placeholder check as
applying to the scanned sources. Use the existing Verification bullet for the exact checks and avoid
promising detection of every identifying string.
Confidence: high

SOL-5 | minor | artifact H6 and finding 7; scripts/AGENTS.md:53
Claim: Withdrawing the broad rewrite was right, but a narrow cut need not wait for a complete
rewrite. Having module docstrings is not proof that they contain every operational detail; for
example, the cited compare_dirs explanation is in a function docstring.
Evidence: All 30 top-level scripts have module docstrings. The index line is 18,798 UTF-8 bytes;
compare_dirs and its float64 cast are documented at scripts/wp2_e3_extract.py:121–133. CARBON-1 is
retained at scripts/lock_cal_freqs.py:1,33 and tests/test_e2p2.py:170; ambiguity 21 is recorded in
DECISIONS.md:115. The destructive resume branches are real: scripts/wp2_e3_extract.py:150–160
discards both score directories after the ownership check; scripts/wp2_e3.py:185–219,254–270
discards the first recomputable stage and its successors, while a digest mismatch in a stage being
verified aborts. src/ncm_sudoku/wp2.py:423–449,471–496 distinguishes fresh TEST refusal from
permitted cleanup of an owned partial run.
Recommendation: Keep H6 and the broad finding-7 relocation deferred. If touching the scripts index
for F1, trim only verified duplicate review labels, retaining the flags, ownership marker,
single-look rules and runner-specific resume behavior.
Confidence: high

SOL-6 | minor | AGENTS.md:64,69; src/ncm_sudoku/AGENTS.md:11
Claim: The one-test-module-per-package-module description is false, and H2 leaves a partial E3
preparation inventory looking exhaustive.
Evidence: There is no tests/test_dlx.py; tests/test_solve.py:4–12,53–68 covers dlx_count_solutions
alongside the other solver. The committed experiments/e3prep tree also contains h1_diffs_L02.json
and budget_sensitivity/, neither listed at AGENTS.md:69.
Recommendation: Describe tests/ as containing dedicated and shared package tests. Make the E3
preparation list explicitly representative or add the omitted entries. Fold the root fixes into
H1/H2 and the child correction into the next package-doc edit.
Confidence: high

SOL-7 | minor | src/ncm_sudoku/AGENTS.md:17
Claim: The contract that the WP4 modules compute no statistic is too broad; the number generator
computes a documented exploratory reference from committed results.
Evidence: src/ncm_sudoku/wp4numbers.py:336–348 derives the solution-digit Brier reference from the
committed TEST positive rate and also totals recorded runner durations. DECISIONS.md:124 (D86)
explicitly labels the reference exploratory.
Recommendation: Distinguish formatting and documented derivations from new confirmatory inference or
model runs. Keep the restriction on the latter and leave the generator unchanged.
Confidence: high

Claims checked

 - H1 — holds: AGENTS.md:21 is stale. AGENTS.md:72, .gitmodules:1–3, the HEAD gitlink and the clean
submodule checkout agree on the upstream pin.
 - H2 — holds: Both preparation directories exist and their files are tracked and committed. All
named entries exist; the E3 list is not exhaustive.
 - H3/H4 history and alias — holds: D88 records the rejection and no-resubmission restriction; D89
and commit 48ee537 record retirement of the package script. D85 records the repository going public
on 2026-11-16; commit 0beab3c records the URL replacing the placeholder that day. No placeholder
invocations remain in the manuscript TeX. --arxiv and --check are exact aliases for the same
variant; the alias is not the retired packaging script.
 - H4 universal placeholder guarantee — does not hold: The scan is limited to the sources and
literal syntax described in SOL-4.
 - H5 and freeze mechanics — holds: The helpers now live in wholelayer.py:152–186 and are used by
scripts/e3_wholelayer.py:42–43,97,131 and src/ncm_sudoku/wp2e3.py:59,113–117,200. Edits to either
tracked child AGENTS.md affect live code state; they do not rewrite the frozen run. The resume
identity check is covered by tests/test_wp2.py:436–449.
 - H6/F1 — holds: The cited runbook steps and TEST completion are recorded. The withdrawn blanket
statement that TEST never deletes outputs does not hold: a fresh start refuses existing targets, but
an owned incomplete run may discard partial outputs on resume.
 - Scope — holds for the repository: The four project AGENTS.md files are tracked, none imports
another, and no project CLAUDE.md, CLAUDE.local.md or prompt file under .claude/ was found. Exact
harness loading, global skill dispatch and installer rewrites could not verify from the appendix
alone (low confidence).
 - H9 — holds as a no-change decision: The quoted frontmatter disables model invocation and line 158
asks for fewer, high-conviction comments. Actual invocation frequency and the effect of the emphatic
wording could not verify (low confidence).
 - F2–F4 — holds as triage: The quoted inventory lacks proveit and verify, but availability through
other command routes could not verify (low confidence); generic examples are safer than substituting
another installation-dependent name. F3 needs no global edit: AGENTS.md:20 and :57 document the
narrower project prose rule and default-off setting. F4 is non-operative wording and not worth a
standalone edit.


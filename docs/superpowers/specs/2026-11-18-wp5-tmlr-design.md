# WP5 design: TMLR submission of the NCM-Sudoku manuscript

Date: 2026-11-18. Status: approved by the user on 2026-11-18 (including the calls after the builder check). Work package: WP5 (ROADMAP), decision log D88.

## Intent

The manuscript in `paper/` (preregistered study of the NCM Sudoku-hard checkpoint; E1 to E3, H1 to H3) is final in content but was rejected by arXiv moderation (D88). The author wants a peer-reviewed journal publication; the target is Transactions on Machine Learning Research (TMLR), chosen because it judges correctness and support of claims rather than novelty, accepts confirmatory and null or equivalence results, and allows public preprints. An acceptance would also open the arXiv appeal (D88). The rules are in `docs/venue/tmlr_submission_rules_2026-11-17.md` (primary sources, access 2026-11-17).

## Goals

1. One manuscript source, two builds from the same section files:
   - an anonymous TMLR submission PDF (`tmlr.sty` without options), for OpenReview;
   - a named PDF (`tmlr.sty` with the `[preprint]` option), with author line, ORCID, repository and OSF links, for the public repository and any later preprint or appeal.
2. Main text of at most 12 pages in the TMLR layout (a "Regular" submission), counted from page 1 to the end of the last main section before the references, as the TMLR form defines it (user decision B, 2026-11-18). The spike build of the current content gave about 15.5 pages.
3. TMLR rules met: unmodified style file, double-blind anonymization of the PDF, first-page footnote on LLM use (TMLR FAQ), CC BY 4.0 statement kept.
4. Everything stays generated and checked as today: `\R{key}` numbers, generated tables and figures, `texlint`, `wp4_figures.py --check`, the tests.

## Non-goals

- No new analysis, no new model run, no new number. Every result stays as reported (D83 to D87). Shortening moves text and floats to the appendix; it does not delete a result, a disclosure or a claim boundary.
- No arXiv resubmission (forbidden by the rejection e-mail, D88). The arXiv package script `scripts/wp4_arxiv.py` stays but is not part of WP5.
- No other preprint server for now (user decision 2026-11-18).
- No anonymized code supplement at submission (see "Open for the user").

## Anti-goals (failure even if it builds)

- Any identifying string in the anonymous PDF or its metadata: the author name (with or without accents), ORCID, the GitHub user or repository name, the OSF identifiers (`hb8vq`, `m28fx`, the DOI), the Bosch or university affiliation.
- A confirmatory result, a registered "does not follow" boundary, a preregistration disclosure (D84, D86, D87 items, the unrun exploratory analyses, the E4 wording) or the AI-use statement moving out of the main text.
- The two builds drifting apart in content: they must differ only in the author block, the identifying links and the TMLR option.
- Modifying `tmlr.sty`, `tmlr.bst` or `fancyhdr.sty` (TMLR may reject without review).

## Constraints

- TMLR style file from https://github.com/JmlrOrg/tmlr-style-file at commit `7bf90efe3a0debbba703c05c43f3ff7e4d4a2992` (spike, 2026-11-18): `tmlr.sty`, `tmlr.bst`, `fancyhdr.sty` vendored unmodified into `paper/`, with their SHA-256 pinned by a test. `tmlr.sty` sets 10 pt, a 6.5 x 9 in text block, loads `natbib` (author-year), `fontenc` T1, `lmodern`, `fancyhdr`, `eso-pic`.
- The current preamble's `geometry` (margin 1.1 in) and `natbib[numbers]` must go: they clash with `tmlr.sty`. The bibliography style becomes `tmlr`; `refs.bib` stays.
- Figures are drawn at `wp4figures.WIDTH` = 6.3 in, which fits the 6.5 in text width; the figure test that pins WIDTH to the old geometry must be re-pinned to the TMLR text width (figures at most 6.5 in). Whether to redraw at 6.5 in is left to the builder.
- The spike (`.superpowers/preview/tmlrspike/`, throwaway) compiled the current content in TMLR style with Tectonic without warnings: anonymous author block, TMLR header, author-year citations, floats fit.
- Language and style rules of `paper/AGENTS.md` hold (US spelling, no Oxford comma, registered terms unchanged).

## Approaches considered

1. Length: A) Long submission with the current content (no edits, slower review: 4-week reviews instead of 2, the ~9-week decision target only applies up to 12 pages); B) shorten to 12 pages by moving material to the appendix. Chosen: B (user, 2026-11-18), because of the faster review and because all three AI reviews found the text dense and repetitive.
2. Source layout: 1) one source, two builds selected by a switch; 2) a separate `paper_tmlr/` copy. Chosen: 1 (user, 2026-11-18): one text to maintain through several review rounds; the old 11 pt layout was never published (arXiv rejected it) and stays in git history.

## The design as decided

### Builds

- A switch selects anonymous or named output (for example `\ifanonymous`, set by two thin top-level files or a build flag; the mechanism is the builder's call). The named build uses `\usepackage[preprint]{tmlr}`, the anonymous build `\usepackage{tmlr}`.
- A small macro decides identifying text, for example `\anon{named text}{anonymous text}`. Anonymous replacements: the repository link becomes a neutral statement that code and results will be released (or are available to reviewers on request), and the preregistration citation keeps the fact and date of registration but withholds the OSF link and DOI ("registration link withheld for double-blind review"). The reproducibility paragraph keeps everything that does not identify the author.
- First-page footnote, in both builds, stating that AI assistants were used and pointing to the "Use of AI tools" section; the section itself stays as is.
- `scripts/wp4_build.py` gains a way to build each variant; the anonymous build has a check mode that fails if a forbidden identifying string appears in any manuscript source after the anonymous switch is applied, or in the PDF metadata (hyperref `pdfauthor` must stay empty). The existing `--arxiv` placeholder check is kept for both.
- A page check reports the page on which the main text ends (for example from a `\label` placed before the bibliography, read from the `.aux` file) and fails above 12 for the anonymous build.

### Shortening plan (target: about 4 pages moved)

Main text keeps: introduction (questions, findings, contributions), background, setup (model, data, labels, preregistration and pre-lock changes, execution), the results-at-a-glance tables (Tables 1 and 2), E1 core result, E2 design and H2 and H3 with their registered readings and the D87 damage comparison sentence, E3 design and H1 with its controls and registered readings, a short paragraph each for levels 2 and 12, the unit-level target and equivariance (with the key numbers and their exploratory status), and the discussion with every limitation stated at least in one sentence, the unrun registered analyses, the E4 paragraph, related work and the AI-use statement.

Moves to the appendix (as new appendix subsections with their full current text):
- E2 descriptive dose curves, propagation and damage-axis curves (Figures 3, 4, 5) with their explanatory paragraphs; the main text keeps one sentence each and a pointer.
- E3 supporting analyses (Figure 7: training-size curve, depth breakdown) with their paragraph; the main text keeps the "still falling" training-size sentence.
- The detailed paragraphs on levels 2 and 12, the unit-level target and equivariance, beyond the short main-text summaries.
- Detailed limitation paragraphs that exceed one or two sentences (for example distribution shift after replacement, readout capacity details), with a one-sentence version in the main text.
- If still above 12 pages: Table 3 (E1) to the appendix with its key numbers in the text, then tightening of repeated statements between the introduction findings, the summary section and the discussion summary.

The builder measures after each move and stops once the anonymous build reports at most 12 pages; the order above is the priority order.

### Verification

- All existing tests and checks pass (`uv run --locked pytest -q`, `wp4_figures.py --check`, `texlint`), plus new tests for: unmodified style files (SHA-256), the anonymity check, the page check, the re-pinned figure width.
- Both PDFs compile without LaTeX warnings, overfull boxes, undefined or multiply defined labels.
- A diff of the text of the two PDFs shows only the author block, the identifying links and the TMLR header or footer.
- A content-preservation check: every `\R{key}` used before the restructuring is still used somewhere in the manuscript, and every paragraph that moved is present verbatim in the appendix.
- One external review round before submission (copilot-review, Final type: astra on the full anonymous PDF and sources), because the restructuring touches every section.

### Submission (user steps, after the build is approved)

OpenReview TMLR form: title, abstract (plain text from the macros), submission length "Regular", the anonymous PDF, competing interests, human subjects "N/A", then the e-mail asking for recommended action editors. TMLR paused new submissions from about 2 December to early January in 2024 and 2025; no 2026 notice was found on 2026-11-17, so the aim is to submit before 2 December 2026 if the build and review allow it.

## Calls made after the builder check (designer's calls, for the user to check)

- Commit hashes and tag names of the author's own repository count as identifying: a reviewer could search GitHub for the short commit (`\R{code.commit}`, from the generated `numbers.tex`) or for the tags `prereg-v3.7` and `wp2-code` and find the repository. The anonymous build withholds them (for example "frozen under a git tag before any model ran on TEST", without the tag name or commit). Upstream, checkpoint and dataset revisions (`prov.*`, HazyResearch) stay. Because these values come from generated files, the anonymity check must scan the text extracted from the anonymous PDF (or the fully expanded sources including `generated/`), not only the hand-written section files; the forbidden list includes the commit `1047668`, the tag names and the strings named under Anti-goals.
- `scripts/wp4_arxiv.py` and `tests/test_wp4_arxiv_script.py` are retired in WP5 (removed, with the DOX entries updated): arXiv resubmission is forbidden (D88), and an appeal after acceptance would use the accepted version, which needs a new package anyway. The history keeps the script.
- The named PDF is a build target only (git-ignored `paper/build/`, as every PDF today); it is not committed.

## Left to the builder

The switch mechanism, file names of the top-level files, the macro names, the exact wording of the anonymous replacements and the footnote, how the page check reads the page number, whether figures are redrawn at 6.5 in, and the exact cut of each moved paragraph, within the rules above.

## Settled with the user (2026-11-18)

- No anonymized code supplement at the first submission; the anonymous paper states that code and results will be released, and a supplement can be provided during review if reviewers ask.
- Competing interests field: "The author is employed by Bosch; this work was done independently and is unrelated to that employment."

# Prompt audit of the Claude Code configuration loaded in NCM-research (2026-11-22), version 2

Version 2 applies the R1 decisions in `.reviews/prompt-audit/decisions.md`. Version 1 (reviewed in R1) is `.reviews/prompt-audit/round-1/artifact.md`.

## Changes since version 1

1. New findings and hunks from R1: H10 (D90 under-review rule in `paper/AGENTS.md`, CARBON-1), H11 (post-submission wording in `AGENTS.md:62,82-83`, CARBON-1, CARBON-5), H12 (OSF registration public, CARBON-5), H13 (GLMM R script and statsmodels/scipy, CARBON-5), H14 (test-module claim, CARBON-5 + SOL-6), H15 (`docs/superpowers/` entries, CARBON-5), H16 (completed banner on the WP2 runbook, SOL-1 + CARBON-6).
2. Revised hunks: H2 (complete `experiments/e3prep/` list, CARBON-5 + SOL-6), H4 (scope of the placeholder check, SOL-4), H5 (helpers shared by two callers, CARBON-2), H7 (backup, delete the file, live check, CARBON-3 + SOL-2), H8 (wording keeps explicit build/update requests, CARBON-3 + SOL-2).
3. Finding 6 evidence corrected: the cited `compare_dirs` text is a function docstring, and `scripts/AGENTS.md:53` also holds cross-module notes found nowhere else (CARBON-4 + SOL-5).
4. The code-state argument against editing `src/` and `scripts/` AGENTS.md files is removed (CARBON-2 + SOL-3): `g0.code_state` is dirty only while uncommitted, and its `commit` field is repo-wide HEAD, so a committed edit there changes it no differently from H1-H4.
5. Recommendation table rewritten; backup step added for user-level edits.

## Purpose and status

This report audits the instruction text that Claude Code loads in this project for text that no longer fits: stale facts the repository contradicts, history narratives, migration-relative phrasing, over-broad skill triggers and pressure language that makes the current model (Claude Opus 5.5) over-trigger. Nothing has been applied yet. The decision this report supports: which hunks to apply.

## Scope

Unchanged from version 1: the four project AGENTS.md files; the user-level files `C:\Users\ako2bp\AGENTS.md`, `~/.claude/CLAUDE.md` and six skills under `~/.claude/skills/` (quoted in the appendix); plugins and symlinked skills report only; settings, `.mcp.json`, memory files and credentials not read.

## Findings

| # | Location | Evidence | Pattern | Why it no longer fits | Confidence | Action |
|---|---|---|---|---|---|---|
| 1 | `AGENTS.md:21` | "planned as an unmodified submodule" | Stale fact | `.gitmodules`, `git submodule status` and `AGENTS.md:72` show the submodule at the pinned commit | High | H1 |
| 2 | `AGENTS.md:69-70` | "(created when the E3 scripts run)", "(created when the lock scripts run)"; the e3prep list omits tracked files | Stale fact; incomplete inventory | Both directories are tracked; `experiments/e3prep/` also holds `h1_diffs_L02.json`, `h1_diffs_L12.json` and `budget_sensitivity/` (3 files) | High | H2 |
| 3 | `paper/AGENTS.md:31` | "The arXiv package script was retired in WP5 (arXiv rejected the preprint, D88)" | History narrative | Recorded in D88 and D89 | Medium | H3 |
| 4 | `paper/AGENTS.md:19` | "(repository URL set 2026-11-16 after the repository went public); `--arxiv` fails if a `\placeholder{...}` is added again" | History; overstated guarantee | Recorded in D85; `--arxiv` is an alias of `--check`; `find_placeholders` scans only `main.tex`, `main_anon.tex`, `body.tex` and `sections/*.tex`, comments stripped (`scripts/wp4_build.py:31-43`) | Medium | H4 |
| 5 | `src/ncm_sudoku/AGENTS.md:27` | "shared stage helpers moved from `scripts/e3_wholelayer.py`" | Migration-relative phrasing | The helpers in `wholelayer.py` are used by `scripts/e3_wholelayer.py` and `src/ncm_sudoku/wp2e3.py:59` | Medium | H5 |
| 6 | `scripts/AGENTS.md:53` | One Child DOX Index line of about 18 KB | Verbose instruction file; history | Much of it repeats module and function docstrings (for example the `compare_dirs` function docstring at `scripts/wp2_e3_extract.py:121-133`), but it also holds cross-module notes found nowhere else (for example the `e3metrics` re-exports in `e3_probes.py`); a safe condensation needs a line-by-line comparison | Medium | deferred |
| 7 | `src/ncm_sudoku/AGENTS.md:27` (whole line) | Same pattern at module level | Verbose instruction file | As finding 6 | Medium | deferred |
| 8 | `~/.claude/CLAUDE.md:2-5` (all projects) | "invoke the Skill tool with `skill: "graphify"` before doing anything else" | Restates a harness default | The harness invokes `/<skill-name>` itself; the block loads in every session | Medium | H7 |
| 9 | `~/.claude/skills/graphify/SKILL.md:3` (all projects) | "Use when user asks any question about a codebase ..." | Over-broad trigger | Fires on any codebase question; this description loads in every session next to the superpowers "1% chance" hook | Medium | H8 |
| 10 | `~/.claude/skills/thermo-nuclear-code-quality-review/SKILL.md:17,19,85` | "Be extremely thorough and rigorous." and similar | Pressure language | User-invoked only; line 158 already limits nits | Medium | no change |
| 11 | `paper/AGENTS.md:5-22`; `AGENTS.md:62,82-83` | Purpose stops at D89; no under-review rule; "WP4 manuscript"; "re-check before submitting"; "repeat the search if submission is delayed" | Stale fact; missing live contract | D90 (`DECISIONS.md:128`): TMLR submission 14707 on 2026-11-19, "no change to the manuscript while under review except through the OpenReview revision process" | High | H10, H11 |
| 12 | `AGENTS.md:18` | "an embargoed OSF registration" | Stale fact | D85 and `AGENTS.md:47`: public since 2026-11-16 | High | H12 |
| 13 | `AGENTS.md:31-32` | "supplementary GLMM as an R script with lme4"; "statsmodels, scipy" | Stale fact | No `.R` file is tracked; D87 records that the GLMM was not run; neither statsmodels nor scipy is a dependency or imported | High | H13 |
| 14 | `AGENTS.md:64`; `src/ncm_sudoku/AGENTS.md:11` | "one test module per package module" | Stale fact | `dlx.py` has no `tests/test_dlx.py`; it is tested in `tests/test_solve.py` | High | H14 |
| 15 | `AGENTS.md:81,83` | plans "one per work package"; `docs/superpowers/specs/` and `literature/kniazev_fijalkow_2026_unit_probe.md` unlisted | Incomplete inventory | Eight plans cover work packages and their stages; two specs are tracked and cited by `paper/AGENTS.md`; the Kniazev note is tracked | High | H11, H15 |
| 16 | `scripts/AGENTS.md:22-45` | WP2 runbook framed as active guidance | Completed procedure | TEST complete (D83); D81-D83 cite steps 4 and 5-8, so the steps stay | High | H16 |
| F2 | `~/.claude/skills/fable-mode/SKILL.md:93` | "(/proveit, /verify, /code-review)" | Volatile specifics | Weak evidence; skill body loads only on invocation | Low | no change |
| F3 | `AGENTS.md:20` vs the user-level `caveman` skill | | Conflict | Covered by `AGENTS.md:20` | - | no change |
| F4 | `~/AGENTS.md:3` | "DOX is highly performant ..." | Padding | No behavioral effect | Low | no change |
| SOL-7 | `src/ncm_sudoku/AGENTS.md:17` | "they compute no statistic" | Contract vs code | `wp4numbers.py:336-347` derives an exploratory reference (`soldigit_brier`, D86); rewording would loosen a prohibition | - | deferred to the user |

Plugins and symlinked skills: unchanged from version 1 (report only).

## Proposed hunks

Project files (H1-H5, H10-H16):

H1 - `AGENTS.md:21`
```diff
-- Upstream code: `HazyResearch/ncm` at commit `c70274273f489abc73832b2b98584a8483b6b203`, planned as an unmodified submodule under `third_party/ncm`; own code goes to `src/ncm_sudoku/`
+- Upstream code: `HazyResearch/ncm` at commit `c70274273f489abc73832b2b98584a8483b6b203`, an unmodified git submodule under `third_party/ncm`; own code goes to `src/ncm_sudoku/`
```

H2 - `AGENTS.md:69-70`
```diff
-- `experiments/e3prep/` (created when the E3 scripts run): committed E3 preparation results, all non-confirmatory (`screen.json`, `extract.json`, `probes.json`, `probes_report.md`, `h1_diffs.json`, `equivariance.json`, `sample_size_h1.json`, `wholelayer.json`, `wholelayer_report.md`, `wholelayer_h1_diffs_L06.json`, `wholelayer_h1_diffs_L12.json`)
-- `experiments/lock/` (created when the lock scripts run): committed lock preparation results, all non-confirmatory (`power.json`, `power.md`, `test_set.json`, `equivariance_l12.json`, `cal_freqs.json`, `level1_check.json`)
+- [experiments/e3prep/](experiments/e3prep/): committed E3 preparation results, all non-confirmatory (`screen.json`, `extract.json`, `probes.json`, `probes_report.md`, `h1_diffs.json`, `h1_diffs_L02.json`, `h1_diffs_L12.json`, `equivariance.json`, `sample_size_h1.json`, `wholelayer.json`, `wholelayer_report.md`, `wholelayer_h1_diffs_L06.json`, `wholelayer_h1_diffs_L12.json`; `budget_sensitivity/` from `scripts/e3_budget_sensitivity.py`: `wholelayer.json`, `wholelayer_h1_diffs_L06.json`, `wholelayer_report.md`)
+- [experiments/lock/](experiments/lock/): committed lock preparation results, all non-confirmatory (`power.json`, `power.md`, `test_set.json`, `equivariance_l12.json`, `cal_freqs.json`, `level1_check.json`)
```

H3 - `paper/AGENTS.md:31`
```diff
-- Sources stay ASCII (TeX accents such as `\'a`); do not set `\pdfoutput` (it switches hyperref to the pdfTeX driver under Tectonic). The arXiv package script was retired in WP5 (arXiv rejected the preprint, D88)
+- Sources stay ASCII (TeX accents such as `\'a`); do not set `\pdfoutput` (it switches hyperref to the pdfTeX driver under Tectonic)
```

H4 - `paper/AGENTS.md:19`
```diff
-- Placeholders: none remain (repository URL set 2026-11-16 after the repository went public); `scripts/wp4_build.py --arxiv` fails if a `\placeholder{...}` is added again.
+- Placeholders: none remain; `scripts/wp4_build.py --check` fails if an uncommented `\placeholder{...}` appears in `main.tex`, `main_anon.tex`, `body.tex` or `sections/*.tex`.
```

H5 - `src/ncm_sudoku/AGENTS.md:27`
```diff
-... shared stage helpers moved from `scripts/e3_wholelayer.py` (outputs pinned by `tests/golden/e3_scripts_toy.json`): ...
+... stage helpers shared by `scripts/e3_wholelayer.py` and `wp2e3` (outputs pinned by `tests/golden/e3_scripts_toy.json`): ...
```

H10 - `paper/AGENTS.md:5` and Local Contracts (new first bullet)
```diff
-Manuscript of the preregistered E1–E3 study (WP4 content, design `docs/superpowers/specs/2026-11-15-wp4-manuscript-design.md`), restructured in WP5 for the TMLR submission: anonymous and named TMLR builds from one source, main text at most 12 pages (design `docs/superpowers/specs/2026-11-18-wp5-tmlr-design.md`, D89).
+Manuscript of the preregistered E1–E3 study (WP4 content, design `docs/superpowers/specs/2026-11-15-wp4-manuscript-design.md`), restructured in WP5 for the TMLR submission: anonymous and named TMLR builds from one source, main text at most 12 pages (design `docs/superpowers/specs/2026-11-18-wp5-tmlr-design.md`, D89). Submitted to TMLR on 2026-11-19 (submission 14707, D90).
@@ Local Contracts
+- Under review (D90): TMLR submission 14707 (OpenReview forum `rDTv8xpA9g`; submitted PDF `paper/build/main_anon.pdf` built at commit `fc61836`); while the review runs, the manuscript (sources, `refs.bib`, `generated/`) changes only through the OpenReview revision process; update this bullet when the review ends
```

H11 - `AGENTS.md:62,82,83`
```diff
-- [paper/AGENTS.md](paper/AGENTS.md): WP4 manuscript (LaTeX, Tectonic build, generated numbers, tables and figures; number and claim rules)
+- [paper/AGENTS.md](paper/AGENTS.md): manuscript, under TMLR review (D90; changes only through the OpenReview revision process); LaTeX, Tectonic build, generated numbers, tables and figures; number and claim rules
@@
-- [docs/venue/](docs/venue/): target-venue rules from primary sources (`tmlr_submission_rules_2026-11-17.md`: TMLR anonymization, length, style file, LLM policy, OpenReview profile, timeline); re-check before submitting
+- [docs/venue/](docs/venue/): target-venue rules from primary sources (`tmlr_submission_rules_2026-11-17.md`: TMLR anonymization, length, style file, LLM policy, OpenReview profile, timeline); re-check before the next OpenReview upload (revision or camera-ready)
@@
-- [literature/](literature/): `related_work_novelty_check.md` (related work and novelty verdicts per experiment, 2026-11-08) and `presubmission_update_2026-11-16.md` (pre-submission repeat of the search and verification of every `paper/refs.bib` entry) and `query_log.md` (every search query, tool, and result count); repeat the search if submission is delayed by more than a few weeks
+- [literature/](literature/): `related_work_novelty_check.md` (related work and novelty verdicts per experiment, 2026-11-08), `presubmission_update_2026-11-16.md` (pre-submission repeat of the search and verification of every `paper/refs.bib` entry), `kniazev_fijalkow_2026_unit_probe.md` (unit-level probe protocol of arXiv:2605.18847 and its code) and `query_log.md` (every search query, tool, and result count); repeat the search before an OpenReview revision that touches related work
```
The two replacement clauses at lines 82 and 83 are the author's adaptation of pre-submission rules to the post-submission state; they are assumptions for the user to confirm.

H12 - `AGENTS.md:18`
```diff
-- Lock: the preregistration lock is a git tag plus an embargoed OSF registration citing the tag hash (plan §12.2, §16)
+- Lock: the preregistration lock is a git tag plus an OSF registration citing the tag hash (plan §12.2, §16); the registration was embargoed at the lock and is public since 2026-11-16 (D85)
```

H13 - `AGENTS.md:31-32`
```diff
-- Environment: `uv`-managed Python 3.12 on native Windows, pytest; supplementary GLMM as an R script with lme4
-- Library docs: Context7 for PyTorch, huggingface_hub, statsmodels, scipy APIs
+- Environment: `uv`-managed Python 3.12 on native Windows, pytest
+- Library docs: Context7 for PyTorch and huggingface_hub APIs
```

H14 - `AGENTS.md:64` and `src/ncm_sudoku/AGENTS.md:11`
```diff
-- [tests/](tests/): pytest suite, one test module per package module; `sudoku_cases.py` holds ...
+- [tests/](tests/): pytest suite, one test module per package module (except `dlx.py`, tested in `test_solve.py`) plus script and style tests; `sudoku_cases.py` holds ...
@@ src/ncm_sudoku/AGENTS.md
-- Owns every module in this folder; one test module per package module lives in `tests/`
+- Owns every module in this folder; each has its test module in `tests/` (`dlx.py` is tested in `tests/test_solve.py`)
```

H15 - `AGENTS.md:81`
```diff
-- [docs/superpowers/plans/](docs/superpowers/plans/): implementation plans, one per work package (`YYYY-MM-DD-<topic>.md`)
+- [docs/superpowers/plans/](docs/superpowers/plans/): implementation plans, one per work package or stage (`YYYY-MM-DD-<topic>.md`)
+- [docs/superpowers/specs/](docs/superpowers/specs/): design specs (`YYYY-MM-DD-<topic>-design.md`) for WP4 and WP5, cited by `paper/AGENTS.md`
```

H16 - `scripts/AGENTS.md:22`
```diff
-WP2 freeze/dry/TEST runbook (run every command from the project root as ...):
+Completed (D83); kept unchanged because D81-D83 cite its step numbers and it records the single-look and dry-snapshot rules. WP2 freeze/dry/TEST runbook (run every command from the project root as ...):
```

User-level files (all projects; before any edit, copy each file to `~/.claude/backups/prompt-audit-2026-11-22/`; `uv run pytest -q` does not cover these files):

H7 - `~/.claude/CLAUDE.md`: delete the file (its only content is the graphify block), then start a new session and check that `/graphify` still runs the skill. Restore from the backup if it does not. The graphify installer may write the block again.

H8 - `~/.claude/skills/graphify/SKILL.md:3`
```diff
-description: "... Use when user asks any question about a codebase, project content, architecture, or file relationships — especially if graphify-out/ exists. ..."
+description: "... Use when the user invokes /graphify or asks to build, update or query a knowledge graph, or asks about architecture or file relationships in a project where graphify-out/ exists. ..."
```
A graphify upgrade may overwrite this file; re-apply then.

## Recommendation

| Hunk | Recommendation | Reason |
|---|---|---|
| H10, H11 | Adopt first | A live rule (D90) is missing from the nearest owning doc |
| H1, H2, H12, H13, H14, H15 | Adopt | Facts the repository contradicts or inventories it outgrew |
| H3, H4, H5 | Adopt | History and migration phrasing; the facts stay in `DECISIONS.md` |
| H16 | Adopt | Marks the completed runbook without breaking the D81-D83 step references |
| H8 | Adopt (user-level, back up first) | Removes a session-wide over-broad trigger |
| H7 | Optional (back up first, live check) | Small benefit; may be rewritten by the installer |
| H6, finding 7 | Deferred | Needs a line-by-line comparison; partly unique content |
| H9, F2, F3, F4 | No change | Low value or covered elsewhere |
| SOL-7 | User decision | Would loosen a prohibition |

After the edits: a DOX pass (the root Child DOX Index changes through H2, H11, H14, H15) and `uv run pytest -q`.

## Appendix: quoted text of the user-level files

Unchanged from version 1; see `.reviews/prompt-audit/round-1/artifact.md`, section "Appendix".

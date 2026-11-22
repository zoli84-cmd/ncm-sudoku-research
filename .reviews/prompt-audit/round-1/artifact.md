# Prompt audit of the Claude Code configuration loaded in NCM-research (2026-11-22)

## Purpose and status

This report audits the instruction text that Claude Code loads in this project for dated prompting patterns ("cruft"): text written for older models, facts the repository has outgrown, and instruction files that contradict each other. The audit follows the `prompt-audit` procedure of the Claude API skill (findings tied to a named pattern, a confidence level, an action; keep-list for load-bearing content). It produced proposed edits (hunks H1-H9) and a second-pass recommendation on which of them to adopt. Nothing has been applied yet. The decision this report supports: which hunks to apply.

Target model: Claude Opus 5.5 (the model running the session that will read these files). Relevant documented behavior: it follows instructions closely and literally, it is proactive by default, and emphatic or pushy wording makes it over-trigger.

## Scope

- Project instruction files (in this repository): `AGENTS.md`, `paper/AGENTS.md`, `scripts/AGENTS.md`, `src/ncm_sudoku/AGENTS.md`. No `CLAUDE.md`, `CLAUDE.local.md` or prompt files under `.claude/` exist in the project; no file imports another (`@path`).
- User-level files (outside this repository; their relevant text is quoted in the appendix, because reviewers cannot read them): `C:\Users\ako2bp\AGENTS.md` (DOX framework, loaded as an ancestor file), `~/.claude/CLAUDE.md`, six skills under `~/.claude/skills/` (be-ambitious, copilot-review, fable-mode, graphify, skillevaluator, thermo-nuclear-code-quality-review). Edits to these affect every project.
- Report only (no edits proposed, because updates would overwrite them): 21 installed plugins and 11 skills symlinked into `~/.claude/skills` from `~/.agents/skills`.
- Not read: settings files, `.mcp.json`, memory files, credentials.

## Findings

| # | Location | Evidence | Pattern | Why it no longer fits | Confidence | Action |
|---|---|---|---|---|---|---|
| 1 | `AGENTS.md:21` | "planned as an unmodified submodule under `third_party/ncm`" | Volatile specifics (stale fact) | `.gitmodules` and `git submodule status` show the submodule at `c70274273f489abc73832b2b98584a8483b6b203`; `AGENTS.md:72` already says so | High | rewrite (H1) |
| 2 | `AGENTS.md:69-70` | "`experiments/e3prep/` (created when the E3 scripts run)", "`experiments/lock/` (created when the lock scripts run)" | Volatile specifics | Both directories exist and are committed | High | rewrite (H2) |
| 3 | `paper/AGENTS.md:31` | "The arXiv package script was retired in WP5 (arXiv rejected the preprint, D88)" | History narrative | Archaeology inside the Verification section; D88 and D89 in `DECISIONS.md` record it; the DOX root rule says "Delete stale notes instead of explaining history" | Medium | remove (H3) |
| 4 | `paper/AGENTS.md:19` | "Placeholders: none remain (repository URL set 2026-11-16 after the repository went public); `scripts/wp4_build.py --arxiv` fails if ..." | History narrative; relative phrasing | Dated history; `--arxiv` is only an alias of `--check` (`scripts/wp4_build.py:116`) | Medium | rewrite (H4) |
| 5 | `src/ncm_sudoku/AGENTS.md:27` | "shared stage helpers moved from `scripts/e3_wholelayer.py`" | Migration-relative phrasing | Describes a diff against a past state | Medium | rewrite (H5) |
| 6 | `scripts/AGENTS.md:53` | One Child DOX Index line of about 15 KB with function-level detail (for example `compare_dirs` casting to float64, "v3.7 review CARBON-1", "spec ambiguity 21") | Verbose instruction file; volatile specifics; history | The same detail is in the script module docstrings (all 30 scripts have one; for example `scripts/wp2_e3_extract.py:123`); duplicated detail rots | Medium | rewrite (H6) |
| 7 | `src/ncm_sudoku/AGENTS.md:27` (whole line) | Same pattern at module level | Verbose instruction file | As finding 6 | Medium | move to docstrings (no hunk drafted) |
| 8 | `~/.claude/CLAUDE.md:2-5` (all projects) | "When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else." | Restates a harness default; pressure wording | The Claude Code harness already invokes a skill when the user types `/<skill-name>`; this block loads in every session of every project; the graphify installer may have written it and may write it again | Medium | remove (H7) |
| 9 | `~/.claude/skills/graphify/SKILL.md:3` (all projects) | "Use when user asks any question about a codebase, project content, architecture, or file relationships" | Over-broad trigger text | Taken literally, it fires on any codebase question; in this project graphify is not set up (`AGENTS.md:34`; no `graphify-out/` directory) | Medium | rewrite (H8) |
| 10 | `~/.claude/skills/thermo-nuclear-code-quality-review/SKILL.md:17, 19, 85` (all projects) | "Be extremely thorough and rigorous.", "Non-Negotiable Additional Standards", "What to Flag Aggressively" | Pressure language | Current models are thorough by default; emphasis pushes reviews toward over-flagging | Medium | rewrite (H9) |
| F1 | `scripts/AGENTS.md:22-45` | WP2 freeze/dry/TEST runbook | Volatile (completed procedure) | WP2 TEST is complete (D83), but the runbook holds prohibitions and `DECISIONS.md` D81-D83 cite "Runbook step 4" and "Runbook steps 5-8" | - | flag only (keep) |
| F2 | `~/.claude/skills/fable-mode/SKILL.md:93` | "It stacks with task-specific skills (/proveit, /verify, /code-review)." | Volatile specifics | `/proveit` and `/verify` are not among the installed skills; absence of an installed tool's command is weak evidence | Low | flag |
| F3 | `AGENTS.md:20` vs the user-level `caveman` skill | "no compressed or caveman-style prose in project files" vs a skill that triggers on "be brief" or "less tokens" | Conflict between instruction files | The project disables only the caveman plugin, not the symlinked user skill; a project file is no reason to edit a user-level file | - | flag |
| F4 | `~/AGENTS.md:3` | "DOX is highly performant AGENTS.md hierarchy installed here" | Padding | Self-description with no behavioral content | Low | flag |

Plugin and symlinked skills (report only): the superpowers SessionStart hook injects `using-superpowers` into every session ("even a 1% chance ... ABSOLUTELY MUST invoke ... before ANY response"), which pushes the model to invoke skills, including mattpocock skills the project does not use (`AGENTS.md:29`); last30days carries heavy caps and "LAW" rules; skill-creator advises making descriptions "pushy" because of under-triggering in older models; code-simplifier and codex-rescue push proactive action. Skill bodies load only on invocation, so in practice only the superpowers hook affects every session.

## Proposed hunks

H1 - `AGENTS.md:21`
```diff
-- Upstream code: `HazyResearch/ncm` at commit `c70274273f489abc73832b2b98584a8483b6b203`, planned as an unmodified submodule under `third_party/ncm`; own code goes to `src/ncm_sudoku/`
+- Upstream code: `HazyResearch/ncm` at commit `c70274273f489abc73832b2b98584a8483b6b203`, an unmodified git submodule under `third_party/ncm`; own code goes to `src/ncm_sudoku/`
```

H2 - `AGENTS.md:69-70` (file lists unchanged)
```diff
-- `experiments/e3prep/` (created when the E3 scripts run): committed E3 preparation results, ...
-- `experiments/lock/` (created when the lock scripts run): committed lock preparation results, ...
+- [experiments/e3prep/](experiments/e3prep/): committed E3 preparation results, ...
+- [experiments/lock/](experiments/lock/): committed lock preparation results, ...
```

H3 - `paper/AGENTS.md:31`
```diff
-- Sources stay ASCII (TeX accents such as `\'a`); do not set `\pdfoutput` (it switches hyperref to the pdfTeX driver under Tectonic). The arXiv package script was retired in WP5 (arXiv rejected the preprint, D88)
+- Sources stay ASCII (TeX accents such as `\'a`); do not set `\pdfoutput` (it switches hyperref to the pdfTeX driver under Tectonic)
```

H4 - `paper/AGENTS.md:19`
```diff
-- Placeholders: none remain (repository URL set 2026-11-16 after the repository went public); `scripts/wp4_build.py --arxiv` fails if a `\placeholder{...}` is added again.
+- Placeholders: none remain; `scripts/wp4_build.py --check` fails if a `\placeholder{...}` is added again.
```

H5 - `src/ncm_sudoku/AGENTS.md:27`
```diff
-... shared stage helpers moved from `scripts/e3_wholelayer.py` (outputs pinned by `tests/golden/e3_scripts_toy.json`): ...
+... shared stage helpers of `scripts/e3_wholelayer.py` (outputs pinned by `tests/golden/e3_scripts_toy.json`): ...
```

H6 - `scripts/AGENTS.md:53`: replace the 15 KB line with a compact per-group index (purpose, flags, outputs, rerun guards) plus a pointer to the module docstrings. The first draft contained the sentence "the TEST role never deletes outputs" for all WP2 runners; this is wrong (`wp2_e3_extract.py --resume` discards `score.tmp/` and `score/` even in the TEST role, and `wp2_e3.py --resume` discards unverified stages), so the draft is withdrawn (see below).

H7 - `~/.claude/CLAUDE.md` (all projects): delete lines 2-5 (the whole graphify block; the file is then empty).

H8 - `~/.claude/skills/graphify/SKILL.md:3` (all projects)
```diff
-description: "... Use when user asks any question about a codebase, project content, architecture, or file relationships — especially if graphify-out/ exists. ..."
+description: "... Use when the user invokes /graphify, or asks about architecture or file relationships in a project where graphify-out/ exists. ..."
```

H9 - `~/.claude/skills/thermo-nuclear-code-quality-review/SKILL.md` (all projects): delete "Be extremely thorough and rigorous." from the baseline quote (line 17); rename "Non-Negotiable Additional Standards" to "Additional Standards" (line 19) and "What to Flag Aggressively" to "What to Flag" (line 85).

## Second-pass recommendation

Three facts found after the first pass changed the recommendation:

1. `g0.code_state` hashes diffs over `src/` and `scripts/`, and `wp2.freeze_state` counts any file there, including `AGENTS.md` (`tests/test_wp2.py:226`). Editing `src/ncm_sudoku/AGENTS.md` or `scripts/AGENTS.md` makes the code state dirty until committed, and rerun-guarded scripts refuse `--resume` on a changed code state. WP2 TEST is complete (D83), so the practical risk is small, but edits there need a real benefit.
2. The H6 draft contained a false claim (see H6).
3. `DECISIONS.md` D81-D83 cite the runbook by step number (F1).

| Hunk | Recommendation | Reason |
|---|---|---|
| H1, H2, H3, H4 | Adopt | Fact or history fixes outside `src/` and `scripts/`; the information stays in `DECISIONS.md` |
| H8 | Optional | Removes over-triggering; the graphify package may overwrite the file on upgrade |
| H7 | Optional | Safe (the harness handles `/graphify`), small benefit, may be rewritten by the installer |
| F2 | Optional | Replace the missing skill names with existing ones (for example `superpowers:verification-before-completion`) |
| H5 | Do not adopt | One phrase; not worth making the code state dirty |
| H6, finding 7 | Do not adopt now | Needs a line-by-line comparison against the code; WP2 is complete and the scripts are effectively final; touches the code state |
| H9 | Do not adopt | User-invoked only, rarely used; the skill already asks for "a smaller number of high-conviction comments" |
| F1, F3, F4 | No change | F1 is cited by DECISIONS; F3 is covered by `AGENTS.md:20`; F4 has no behavioral effect |
| Plugins | No change | Plugin files are overwritten on update; the project workflow is built on superpowers, so its hook stays unless over-triggering is observed |

After any adopted hunk: a DOX pass (refresh affected Child DOX Index entries) and `uv run pytest -q`.

## Appendix: quoted text of the user-level files (outside the repository)

`~/.claude/CLAUDE.md` (complete; line 1 is empty):
```
2  # graphify
3
4  - **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
5  When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.
```

`~/.claude/skills/graphify/SKILL.md:1-5` (the file is 1,434 lines; frontmatter `name: graphify-windows`, directory `graphify`; lines 1399-1407 describe an optional command that writes a `## graphify` section into a project's local `CLAUDE.md`):
```
---
name: graphify-windows
description: "any input (code, docs, papers, images) → knowledge graph → clustered communities → HTML + JSON + audit report. Use when user asks any question about a codebase, project content, architecture, or file relationships — especially if graphify-out/ exists. Provides persistent graph with god nodes, community detection, and BFS/DFS query tools."
trigger: /graphify
---
```

`~/.claude/skills/thermo-nuclear-code-quality-review/SKILL.md` (frontmatter has `disable-model-invocation: true`):
```
17 > Perform a deep code quality audit of the current branch's changes. ... Be ambitious, if there is a clear path to improving the implementation that involves restructuring some of the codebase, go for it. Be extremely thorough and rigorous. Measure twice, cut once.
19 ## Non-Negotiable Additional Standards
85 ## What to Flag Aggressively
158 Do not flood the review with low-value nits if there are larger structural issues. Prefer a smaller number of high-conviction comments over a long list of cosmetic notes.
```

`~/.claude/skills/fable-mode/SKILL.md:93`:
```
- It stacks with task-specific skills (/proveit, /verify, /code-review). Those are the "how to check" tools; this is the discipline of when to reach for them.
```

`C:\Users\ako2bp\AGENTS.md:1-4` (DOX root, an ancestor of this repository):
```
# DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits
```
The same file's Style section says: "Document stable contracts, not diary entries", "Delete stale notes instead of explaining history", "Do not duplicate rules across many files unless each scope needs a local version".

Installed user skills at audit time (from the session's skill listing): be-ambitious, build-with-exa, caveman, company-research, copilot-review, diagram-design, dox, drawio-skill, exa-contents, exa-search, fable-mode, find-skills, graft, graphify, lead-generation, skillevaluator, thermo-nuclear-code-quality-review, plus plugin skills (superpowers, mattpocock-skills, codex, code-review, claude-md-management and others). No skill named `proveit` or `verify` is installed.

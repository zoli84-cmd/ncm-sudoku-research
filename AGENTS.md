# NCM-research

DOX rules are inherited from `C:\Users\ako2bp\AGENTS.md`; this file is the project root contract.

## Purpose

Personal research project on hierarchical sensitivity, error propagation, and logical representations in Next-Concept Modeling (NCM) Sudoku generation. The governing protocol is [research_plan_v3.5.md](research_plan_v3.5.md); work-package status and backlog are in [ROADMAP.md](ROADMAP.md); every decision and, after the lock, every deviation is logged in [DECISIONS.md](DECISIONS.md).

## Ownership

- Root owns the research plan, the decision log, project-wide rules, and the Child DOX Index
- `resources/` holds read-only source materials (papers, external references)

## Local Contracts

- Language: every project file (code, docs, notes, protocols, AGENTS.md) is written in English; communication with the user is in Hungarian
- Plan versions: `research_plan_v3.5.md` is authoritative; `research_plan_v3.4.md`, `research_plan_v3.3.md`, `research_plan_v3.2.md`, `research_plan_v3.1.md`, `NCM_Sudoku_kutatasi_terv_v3.md` (Hungarian original) and `research_plan_v3.md` (its translation) are frozen predecessors; never edit a released plan version in place, create a new version and log it in `DECISIONS.md`
- Lock: the preregistration lock is a git tag plus an embargoed OSF registration citing the tag hash (plan §12.2, §16)
- Never invent hashes, sample sizes, power estimates, or results; open items stay explicitly open
- Claim boundaries follow plan §13: written artifacts keep the hedging and "does not follow" qualifiers; no compressed or caveman-style prose in project files
- Upstream code: `HazyResearch/ncm` at commit `c70274273f489abc73832b2b98584a8483b6b203`, planned as an unmodified submodule under `third_party/ncm`; own code goes to `src/ncm_sudoku/`
- Numerical policy: FP32, eager mode, deterministic algorithms, CPU on native Windows (plan §2.2, DECISIONS D30)
- Not committed (see `.gitignore`): checkpoints, datasets, run outputs, paper PDFs, `.env`
- Secrets: `CONSENSUS_API_KEY` is read from the environment only; never write keys to files, logs, or commits

## Work Guidance

- Workflow: Superpowers process skills (brainstorming → writing-plans → executing-plans / test-driven-development → verification-before-completion)
- From Mattpocock skills use only `grilling` (plan stress tests), `research` (primary-source notes), `domain-modeling` (glossary for plan §3 notation)
- Coding style: Karpathy guidelines (surface assumptions, verifiable success criteria, surgical changes); Ponytail and Caveman are disabled for this project in `.claude/settings.json`
- Environment: `uv`-managed Python 3.12 on native Windows, pytest; supplementary GLMM as an R script with lme4
- Library docs: Context7 for PyTorch, huggingface_hub, statsmodels, scipy APIs
- Literature: Consensus API for peer-reviewed methodology search; supplement with arXiv / Semantic Scholar / Exa for recent ML preprints; save results and the query log under `literature/`
- Code-graph tooling (Graft or graphify, pick one) only after the upstream `ncm` submodule exists

## Verification

- From the project root on Windows (Git Bash or PowerShell): `uv run pytest -q`
- Slow checks (need `data/released/` and `checkpoints/`, about 2 minutes): `uv run pytest -q -m slow`
- G0 reproduction (about 45 minutes): `uv run python scripts/g0_reproduce.py`

## Child DOX Index

- [research_plan_v3.5.md](research_plan_v3.5.md): authoritative research plan
- [ROADMAP.md](ROADMAP.md): work-package status, effort and compute estimates, backlog, open items
- [research_plan_v3.4.md](research_plan_v3.4.md): frozen plan v3.4 (before WP0 implementation facts)
- [research_plan_v3.3.md](research_plan_v3.3.md): frozen plan v3.3 (after external review R1, before the final round)
- [research_plan_v3.2.md](research_plan_v3.2.md): frozen plan v3.2 (related-work review, before external review R1)
- [research_plan_v3.1.md](research_plan_v3.1.md): frozen plan v3.1 (setup decisions, before related-work review)
- [DECISIONS.md](DECISIONS.md): decision log and post-lock deviation log
- [research_plan_v3.md](research_plan_v3.md): frozen English translation of plan v3.0
- [NCM_Sudoku_kutatasi_terv_v3.md](NCM_Sudoku_kutatasi_terv_v3.md): frozen Hungarian original of plan v3.0
- [.claude/settings.json](.claude/settings.json): project Claude Code settings; disables `caveman@caveman` and `ponytail@ponytail` plugins and sets `CAVEMAN_DEFAULT_MODE=off` (the user-level caveman hooks read this)
- [.gitignore](.gitignore): excludes checkpoints, data, run outputs, paper PDFs, secrets
- [.gitattributes](.gitattributes): LF line endings everywhere, so lock hashes match across Windows and WSL
- [pyproject.toml](pyproject.toml), `uv.lock`, `.python-version`: uv project (Python 3.12, numpy; pytest as dev dependency)
- [src/ncm_sudoku/](src/ncm_sudoku/): own package; `grid.py` (grid conventions, NCM tokens), `validate.py` (parser, metrics), `solve.py` and `dlx.py` (independent solvers), `labels.py` (candidate mask, single waves), `generate.py` (fresh puzzles), `released.py` (safe loader for the released set), `model.py` (safe checkpoint loading), `official.py` (upstream metric mirror), `runner.py` (generation, decoding, teacher codes), `states.py` (cumulative states, cell mapping), `intervene.py` (`forward_with_intervention`, branches A–D), `g0.py` (G0 rule, identity checks, reproduction)
- [tests/](tests/): pytest suite, one test module per package module; `sudoku_cases.py` holds shared fixtures; `-m slow` runs real-data checks
- [scripts/](scripts/): `fetch_released_data.py`, `fetch_checkpoints.py` (downloads), `g0_reproduce.py`, `g0_cost.py` (G0)
- [experiments/g0/](experiments/g0/): committed G0 results (`reproduction.json`, `cost.json`)
- [experiments/provenance/](experiments/provenance/): `released_data.json` (dataset) and `checkpoints.json` (checkpoint revision, sizes, SHA-256, licenses, upstream commit)
- [third_party/ncm/](third_party/ncm/): upstream HazyResearch/ncm as a git submodule at the pinned commit; never modified; imported via `ncm_sudoku.model.import_upstream`
- `checkpoints/` (git-ignored): downloaded by `scripts/fetch_checkpoints.py`; load only through `ncm_sudoku.model.load_model` (weights_only=True)
- `runs/` (git-ignored): per-puzzle raw run outputs
- [.reviews/](.reviews/): external Copilot reviews per artifact (`review-plan.md`, `decisions.md`, briefs, reviewer outputs); transcripts are not committed
- [docs/superpowers/plans/](docs/superpowers/plans/): implementation plans (WP0-A Sudoku core)
- [literature/](literature/): `related_work_novelty_check.md` (related work and novelty verdicts per experiment, 2026-11-08) and `query_log.md` (every search query, tool, and result count); repeat the search before submission
- [resources/](resources/): source materials; `2610.14162v1.pdf` is the NCM paper (arXiv:2610.14162), local only

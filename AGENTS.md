# NCM-research

DOX rules are inherited from `C:\Users\ako2bp\AGENTS.md`; this file is the project root contract.

## Purpose

Personal research project on hierarchical sensitivity, error propagation, and logical representations in Next-Concept Modeling (NCM) Sudoku generation. The governing protocol is [research_plan_v3.7.md](research_plan_v3.7.md); work-package status and backlog are in [ROADMAP.md](ROADMAP.md); every decision and, after the lock, every deviation is logged in [DECISIONS.md](DECISIONS.md).

## Ownership

- Root owns the research plan, the decision log, project-wide rules, and the Child DOX Index
- `resources/` holds read-only source materials (papers, external references)

## Local Contracts

- Language: every project file (code, docs, notes, protocols, AGENTS.md) is written in English; communication with the user is in Hungarian
- Plan versions: `research_plan_v3.7.md` (preregistration lock version) is authoritative; `research_plan_v3.6.md`, `research_plan_v3.5.md`, `research_plan_v3.4.md`, `research_plan_v3.3.md`, `research_plan_v3.2.md`, `research_plan_v3.1.md`, `NCM_Sudoku_kutatasi_terv_v3.md` (Hungarian original) and `research_plan_v3.md` (its translation) are frozen predecessors; never edit a released plan version in place, create a new version and log it in `DECISIONS.md`
- Lock: the preregistration lock is a git tag plus an embargoed OSF registration citing the tag hash (plan §12.2, §16)
- Never invent hashes, sample sizes, power estimates, or results; open items stay explicitly open
- Claim boundaries follow plan §13: written artifacts keep the hedging and "does not follow" qualifiers; no compressed or caveman-style prose in project files
- Upstream code: `HazyResearch/ncm` at commit `c70274273f489abc73832b2b98584a8483b6b203`, planned as an unmodified submodule under `third_party/ncm`; own code goes to `src/ncm_sudoku/`
- Numerical policy: FP32, eager mode, deterministic algorithms, CPU on native Windows (plan §2.2, DECISIONS D30)
- Not committed (see `.gitignore`): checkpoints, datasets, root `runs/` raw outputs, paper PDFs, `.env`
- Secrets: `CONSENSUS_API_KEY` is read from the environment only; never write keys to files, logs, or commits

## Work Guidance

- Workflow: Superpowers process skills (brainstorming → writing-plans → executing-plans / test-driven-development → verification-before-completion)
- From Mattpocock skills use only `grilling` (plan stress tests), `research` (primary-source notes), `domain-modeling` (glossary for plan §3 notation)
- Coding style: Karpathy guidelines (surface assumptions, verifiable success criteria, surgical changes); Ponytail and Caveman are disabled for this project in `.claude/settings.json`
- Environment: `uv`-managed Python 3.12 on native Windows, pytest; supplementary GLMM as an R script with lme4
- Library docs: Context7 for PyTorch, huggingface_hub, statsmodels, scipy APIs
- Literature: Consensus API for peer-reviewed methodology search; supplement with arXiv / Semantic Scholar / Exa for recent ML preprints; save results and the query log under `literature/`
- Code-graph tooling: use at most one of Graft or graphify; neither is set up for this project yet

## Verification

- From the project root on Windows (Git Bash or PowerShell): `uv run pytest -q`
- Slow checks (need `data/released/` and `checkpoints/`, about 2 minutes): `uv run pytest -q -m slow`
- G0 reproduction (about 45 minutes): `uv run python scripts/g0_reproduce.py`

## Child DOX Index

- [research_plan_v3.7.md](research_plan_v3.7.md): authoritative research plan, preregistration lock version
- [research_plan_v3.6.md](research_plan_v3.6.md): frozen plan v3.6 (E2 redesign, before the E3 preparation and the lock)
- [research_plan_v3.5.md](research_plan_v3.5.md): frozen plan v3.5 (before the E2 redesign after the WP1 pilot)
- [osf/registration.md](osf/registration.md): OSF preregistration text for the v3.7 lock (tag `prereg-v3.7`), submitted by the user
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
- [pyproject.toml](pyproject.toml), `uv.lock`, `.python-version`: uv project (Python 3.12, numpy, torch, matplotlib for the WP4 figures; pytest as dev dependency)
- [paper/AGENTS.md](paper/AGENTS.md): WP4 manuscript (LaTeX, Tectonic build, generated numbers, tables and figures; number and claim rules)
- [src/ncm_sudoku/AGENTS.md](src/ncm_sudoku/AGENTS.md): own package; per-module contracts (frozen `grid.PEER_ORDER`, pinned by `tests/test_peer_order.py`; never reorder; `wp2.py` is the WP2 freeze guard and run-record layer every WP2 runner uses)
- [tests/](tests/): pytest suite, one test module per package module; `sudoku_cases.py` holds shared fixtures, `e2p2_fakes.py` deterministic fakes of the model pieces `e2p2` uses (`toy_model` with embedding tables, `exact_restart` for code-identity tests), `wp2_fakes.py` a complete synthetic set of WP2 raw outputs and valid run records for one role (`write_role`; the TEST role scores E3 on the E2 ids, as the real TEST does; tests of `scripts/wp2_evaluate.py` and `scripts/wp2_dry_check.py`); `golden/` holds outputs generated from earlier code that pin refactors (`summarize2_toy.json`; `e3_scripts_toy.json`: `stages` of `scripts/e3_wholelayer.py` (K 8) and `scripts/e3_probes.py` (SIZES (4, 8)) on the toy runs with the FAST budget, written before the WP2 helper move); `-m slow` runs real-data checks
- [scripts/AGENTS.md](scripts/AGENTS.md): run scripts; most result writers are rerun-guarded (`--force` / `--resume`); read the per-script contract there before forcing a rerun
- [experiments/g0/](experiments/g0/): committed G0 results (`reproduction.json`, `cost.json`)
- [experiments/wp1/](experiments/wp1/): committed WP1 results (`gate.json`, `e1_released.json`, `e1_cal.json`, `pilot_summary.json`, `pilot_report.md`, `screen.json`); `gate.json` must never be regenerated
- [experiments/e2p2/](experiments/e2p2/): committed E2 pilot-2 results (`summary.json`, `report.md`, `sample_size_e2.json`); raw per-record output is in `runs/e2p2/pilot2.json` (git-ignored)
- `experiments/e3prep/` (created when the E3 scripts run): committed E3 preparation results, all non-confirmatory (`screen.json`, `extract.json`, `probes.json`, `probes_report.md`, `h1_diffs.json`, `equivariance.json`, `sample_size_h1.json`, `wholelayer.json`, `wholelayer_report.md`, `wholelayer_h1_diffs_L06.json`, `wholelayer_h1_diffs_L12.json`)
- `experiments/lock/` (created when the lock scripts run): committed lock preparation results, all non-confirmatory (`power.json`, `power.md`, `test_set.json`, `equivariance_l12.json`, `cal_freqs.json`, `level1_check.json`)
- [experiments/provenance/](experiments/provenance/): `released_data.json` (dataset) and `checkpoints.json` (checkpoint revision, sizes, SHA-256, licenses, upstream commit)
- [third_party/ncm/](third_party/ncm/): upstream HazyResearch/ncm as a git submodule at the pinned commit; never modified; imported via `ncm_sudoku.model.import_upstream`
- `checkpoints/` (git-ignored): downloaded by `scripts/fetch_checkpoints.py`; load only through `ncm_sudoku.model.load_model` (weights_only=True)
- `runs/` (git-ignored): per-puzzle raw run outputs
- `runs/e3prep/<probe_train|probe_val>/` (git-ignored): PROBE subset arrays from `scripts/e3_extract.py` (`ids.json`, `puzzles.npy`, `solutions.npy`, `solve.npy`, `mask.npy`, `empty.npy`, `depth.npy`, `L01.npy`..`L12.npy`, `T02.npy`, `T06.npy`, `T12.npy`); about 3 GB total across both subsets
- [experiments/wp2/](experiments/wp2/) and `runs/wp2/<role>/` (`role` = `test` or `dry`): committed WP2 outputs (the TEST report is `experiments/wp2/test/report.md`, D83) and git-ignored raw outputs; run records in `experiments/wp2/<role>/runs/<runner>.json`; the dry approval is `experiments/wp2/dry/check.json` (and `check.md`), written by `scripts/wp2_dry_check.py`; `scripts/wp2_evaluate.py` writes `experiments/wp2/<role>/results.json` and `report.md`; see `ncm_sudoku.wp2`
- `runs/lock/test/` (git-ignored): TEST subset from `scripts/lock_test_set.py` (`ids.json`, `puzzles.npy`, `solutions.npy`, uint8); its hashes are in `experiments/lock/test_set.json`
- `runs/lock/equiv_l12/` (git-ignored): level-12 whole-layer seed probes from `scripts/lock_equiv_l12.py` (`L12_wholelayer_seed{0,1,2}.pt` state dicts, `pca.pt` tensors, `L12_wholelayer.json` config); reload with `load_saved` (`torch.load(weights_only=True)`)
- `runs/e3prep/models/` (git-ignored): selected level-6 linear seed probes from `scripts/e3_probes.py` (`L06_linear_seed{0,1,2}.pt` state dicts, `L06_linear.json` config); loaded with `torch.load(weights_only=True)`
- [.reviews/](.reviews/): external Copilot reviews per artifact (`review-plan.md`, `decisions.md`, briefs, reviewer outputs); transcripts are not committed
- [docs/superpowers/plans/](docs/superpowers/plans/): implementation plans, one per work package (`YYYY-MM-DD-<topic>.md`)
- [literature/](literature/): `related_work_novelty_check.md` (related work and novelty verdicts per experiment, 2026-11-08) and `query_log.md` (every search query, tool, and result count); repeat the search before submission
- [resources/](resources/): source materials; `2610.14162v1.pdf` is the NCM paper (arXiv:2610.14162), local only

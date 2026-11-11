# NCM-research

DOX rules are inherited from `C:\Users\ako2bp\AGENTS.md`; this file is the project root contract.

## Purpose

Personal research project on hierarchical sensitivity, error propagation, and logical representations in Next-Concept Modeling (NCM) Sudoku generation. The governing protocol is [research_plan_v3.6.md](research_plan_v3.6.md); work-package status and backlog are in [ROADMAP.md](ROADMAP.md); every decision and, after the lock, every deviation is logged in [DECISIONS.md](DECISIONS.md).

## Ownership

- Root owns the research plan, the decision log, project-wide rules, and the Child DOX Index
- `resources/` holds read-only source materials (papers, external references)

## Local Contracts

- Language: every project file (code, docs, notes, protocols, AGENTS.md) is written in English; communication with the user is in Hungarian
- Plan versions: `research_plan_v3.6.md` is authoritative; `research_plan_v3.5.md`, `research_plan_v3.4.md`, `research_plan_v3.3.md`, `research_plan_v3.2.md`, `research_plan_v3.1.md`, `NCM_Sudoku_kutatasi_terv_v3.md` (Hungarian original) and `research_plan_v3.md` (its translation) are frozen predecessors; never edit a released plan version in place, create a new version and log it in `DECISIONS.md`
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

- [research_plan_v3.6.md](research_plan_v3.6.md): authoritative research plan
- [research_plan_v3.5.md](research_plan_v3.5.md): frozen plan v3.5 (before the E2 redesign after the WP1 pilot)
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
- [src/ncm_sudoku/](src/ncm_sudoku/): own package; `grid.py` (grid conventions, NCM tokens), `validate.py` (parser, metrics), `solve.py` and `dlx.py` (independent solvers), `labels.py` (candidate mask, single waves), `generate.py` (fresh puzzles), `released.py` (safe loader for the released set), `model.py` (safe checkpoint loading), `official.py` (upstream metric mirror), `runner.py` (generation, decoding, teacher codes), `states.py` (cumulative states, cell mapping), `intervene.py` (`forward_with_intervention`, branches A–D), `g0.py` (G0 rule, identity checks, reproduction), `e2p2.py` (E2 pilot-2 runner `run_pilot2`, puzzle-level contrasts, bootstrap or rare-event bound, pairwise AUC, `summarize2`), `subsets.py` (seed namespaces, generator freeze check, duplicate/signature screen), `gate.py` (distribution gate), `e1.py` (E1 summary), `perturb.py` (dose grid, code replacement), `e2.py` (E2 pilot runner, θ estimators, cluster bootstrap), `damage.py` (TV damage, latent distance, codebook RMS, re-quantization), `power.py` (E2 sample-size simulation: thinning, sign-mixing and sign-flip scenarios, `required_n`, `e2_sample_size`; E3 H1 sample size: `shift_to`, `h1_sample_size`), `symmetry.py` (E3 prep: `Symmetry` group elements, `apply_symmetry`, `inverse`, `transform_predictions`, exact minlex `canonical_form`, orbit screen `screen_canonical`), `e3data.py` (E3 PROBE data extraction: `extract` and streaming `extract_streamed`, `labels`, `raw_features`/`peer_counts`/`surface_features` controls, `save_subset`/`load_level`), `probes.py` (E3 shared-cell probe training: `build_inputs` with an `n_positions` parameter for cell and unit readouts, `train_probe`, `GRID`/`SEEDS`, `brier_per_puzzle`, `select`, `fit_selected`), `e3controls.py` (E3 §8.2 controls and D62 unit–digit target: `permute_puzzles`, `random_features`, `permute_labels`, `marginal_brier`, `fit_cells`, `summarize_fit`, `permuted_control`, `run_controls`; `unit_digit_labels`, `unit_readout`, numpy `roc_auc`, `unit_metrics`, `run_unit_digit`), `e3equiv.py` (E3 D59 equivariance pilot `equivariance_pilot` with injectable predictors; default predictor `model_predict_fn` = generate, level-6 cell states, probe)
- [tests/](tests/): pytest suite, one test module per package module; `sudoku_cases.py` holds shared fixtures; `-m slow` runs real-data checks
- [scripts/](scripts/): `fetch_released_data.py`, `fetch_checkpoints.py` (downloads), `g0_reproduce.py`, `g0_cost.py` (G0); `wp1_gate.py` (single-look gate; refuses to rerun), `wp1_e1.py --subset released|cal`, `wp1_pilot.py [--report-only]`, `wp1_screen.py` (duplicate/signature screen over all generated subsets) (WP1); `e2_pilot2.py [--force] [--report-only | --from-raw]` (E2 pilot-2 on CAL; refuses to rerun unless summary.json is missing or `--force` is given; `--from-raw` rebuilds summary and report from `runs/e2p2/pilot2.json`), `e2_sample_size.py` (deterministic E2 sample-size simulation from the pilot-2 output; safe to rerun); `e3_screen.py` (exact canonical-form orbit screen over gate, CAL, PROBE-TRAIN, PROBE-VAL and the released set; writes `experiments/e3prep/screen.json`; safe to rerun); `e3_extract.py [--force]` (generates PROBE-TRAIN 2,000 and PROBE-VAL 500, extracts generated/teacher cell states and labels, streams them to `runs/e3prep/`, writes `experiments/e3prep/extract.json`; refuses to rerun if `runs/e3prep/probe_val/L12.npy` exists unless `--force`); `e3_probes.py [--force | --resume]` (E3 probe suite: 12-level linear curve, MLP and permuted control at levels 2/6/12, level-6 controls, unit–digit target, training-size curve, depth breakdown; saves the selected level-6 seed models; writes `experiments/e3prep/probes.json` after every stage, `probes_report.md`, `h1_diffs.json`; refuses to rerun if probes.json exists unless `--force` or `--resume`), `e3_equiv_power.py [--force | --power-only]` (D59 equivariance pilot through the model, rerun-guarded on `equivariance.json`; deterministic D60 H1 sample size to `sample_size_h1.json`)
- [experiments/g0/](experiments/g0/): committed G0 results (`reproduction.json`, `cost.json`)
- [experiments/wp1/](experiments/wp1/): committed WP1 results (`gate.json`, `e1_released.json`, `e1_cal.json`, `pilot_summary.json`, `pilot_report.md`, `screen.json`); `gate.json` must never be regenerated
- [experiments/e2p2/](experiments/e2p2/): committed E2 pilot-2 results (`summary.json`, `report.md`, `sample_size_e2.json`); raw per-record output is in `runs/e2p2/pilot2.json` (git-ignored)
- `experiments/e3prep/` (created when the E3 scripts run): committed E3 preparation results, all non-confirmatory (`screen.json`, `extract.json`, `probes.json`, `probes_report.md`, `h1_diffs.json`, `equivariance.json`, `sample_size_h1.json`)
- [experiments/provenance/](experiments/provenance/): `released_data.json` (dataset) and `checkpoints.json` (checkpoint revision, sizes, SHA-256, licenses, upstream commit)
- [third_party/ncm/](third_party/ncm/): upstream HazyResearch/ncm as a git submodule at the pinned commit; never modified; imported via `ncm_sudoku.model.import_upstream`
- `checkpoints/` (git-ignored): downloaded by `scripts/fetch_checkpoints.py`; load only through `ncm_sudoku.model.load_model` (weights_only=True)
- `runs/` (git-ignored): per-puzzle raw run outputs
- `runs/e3prep/<probe_train|probe_val>/` (git-ignored): PROBE subset arrays from `scripts/e3_extract.py` (`ids.json`, `puzzles.npy`, `solutions.npy`, `solve.npy`, `mask.npy`, `empty.npy`, `depth.npy`, `L01.npy`..`L12.npy`, `T02.npy`, `T06.npy`, `T12.npy`); about 3 GB total across both subsets
- `runs/e3prep/models/` (git-ignored): selected level-6 linear seed probes from `scripts/e3_probes.py` (`L06_linear_seed{0,1,2}.pt` state dicts, `L06_linear.json` config); loaded with `torch.load(weights_only=True)`
- [.reviews/](.reviews/): external Copilot reviews per artifact (`review-plan.md`, `decisions.md`, briefs, reviewer outputs); transcripts are not committed
- [docs/superpowers/plans/](docs/superpowers/plans/): implementation plans (WP0-A, WP0-B, WP1)
- [literature/](literature/): `related_work_novelty_check.md` (related work and novelty verdicts per experiment, 2026-11-08) and `query_log.md` (every search query, tool, and result count); repeat the search before submission
- [resources/](resources/): source materials; `2610.14162v1.pdf` is the NCM paper (arXiv:2610.14162), local only

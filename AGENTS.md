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
- Lock: the preregistration lock is a git tag plus an OSF registration citing the tag name and the tagged commit (plan §12.2, §16); the registration was embargoed at the lock and is public since 2026-11-16 (D85)
- Never invent hashes, sample sizes, power estimates, or results; open items stay explicitly open
- Claim boundaries follow plan §13: written artifacts keep the hedging and "does not follow" qualifiers; no compressed or caveman-style prose in project files
- Upstream code: `HazyResearch/ncm` at commit `c70274273f489abc73832b2b98584a8483b6b203`, an unmodified git submodule under `third_party/ncm`; `kameronton/sudoku-residual` (Kniazev & Fijalkow) at `a9b206955bfd1089a7253511fa9371066ecca570`, an unmodified submodule under `third_party/sudoku-residual`, used only for the E5 positive control and only from its own environment `.venv-kf/` (JAX, Python 3.13, built from its `uv.lock`; the exception to the FP32 policy for that model is D94); own code goes to `src/ncm_sudoku/`
- Numerical policy: FP32, eager mode, deterministic algorithms, CPU on native Windows (plan §2.2, DECISIONS D30)
- Not committed (see `.gitignore`): checkpoints, datasets, root `runs/` raw outputs, paper PDFs, `.env`
- Secrets: `CONSENSUS_API_KEY` is read from the environment only; never write keys to files, logs, or commits

## Work Guidance

- Workflow: Superpowers process skills (brainstorming → writing-plans → executing-plans / test-driven-development → verification-before-completion)
- From Mattpocock skills use only `grilling` (plan stress tests), `research` (primary-source notes), `domain-modeling` (glossary for plan §3 notation)
- Coding style: Karpathy guidelines (surface assumptions, verifiable success criteria, surgical changes); Ponytail and Caveman are disabled for this project in `.claude/settings.json`
- Environment: `uv`-managed Python 3.12 on native Windows, pytest
- Library docs: Context7 for PyTorch and huggingface_hub APIs
- Literature: Consensus API for peer-reviewed methodology search; Lacuna (Tiptree Systems) MCP server `lacuna-research` for ML/AI papers, authors and research directions (read-only, no key; no citation graph; no Zenodo coverage and some key prior work missing, so use it only as a supplement for watching recent arXiv papers, see `literature/query_log.md` 2026-11-22; cite its canonical Lacuna URLs and verify claims against the primary paper); supplement with arXiv / Semantic Scholar / Exa for recent ML preprints; save results and the query log under `literature/`
- Code-graph tooling: use at most one of Graft or graphify; neither is set up for this project yet

## Verification

- From the project root on Windows (Git Bash or PowerShell): `uv run pytest -q`
- Slow checks (need `data/released/` and `checkpoints/`, about 2 minutes): `uv run pytest -q -m slow`
- G0 reproduction (about 45 minutes): `uv run python scripts/g0_reproduce.py`

## Child DOX Index

- [research_plan_v3.7.md](research_plan_v3.7.md): authoritative research plan, preregistration lock version
- [e5_protocol_v1.md](e5_protocol_v1.md): E5 follow-up protocol (draft after high-tier review, not locked; D91–D107): state-versus-generator question, counterfactual TEST pairs, claims A and B with betting decisions, interpretation rules, pre-lock tasks
- [research_plan_v3.6.md](research_plan_v3.6.md): frozen plan v3.6 (E2 redesign, before the E3 preparation and the lock)
- [research_plan_v3.5.md](research_plan_v3.5.md): frozen plan v3.5 (before the E2 redesign after the WP1 pilot)
- [osf/registration.md](osf/registration.md): OSF preregistration text for the v3.7 lock (tag `prereg-v3.7`) as submitted by the user (frozen record); the registration is https://osf.io/hb8vq (DOI 10.17605/OSF.IO/HB8VQ, project https://osf.io/m28fx), public since 2026-11-16 (D85)
- [ROADMAP.md](ROADMAP.md): work-package status, effort and compute estimates, backlog, open items
- [research_plan_v3.4.md](research_plan_v3.4.md): frozen plan v3.4 (before WP0 implementation facts)
- [research_plan_v3.3.md](research_plan_v3.3.md): frozen plan v3.3 (after external review R1, before the final round)
- [research_plan_v3.2.md](research_plan_v3.2.md): frozen plan v3.2 (related-work review, before external review R1)
- [research_plan_v3.1.md](research_plan_v3.1.md): frozen plan v3.1 (setup decisions, before related-work review)
- [DECISIONS.md](DECISIONS.md): decision log and post-lock deviation log
- [research_plan_v3.md](research_plan_v3.md): frozen English translation of plan v3.0
- [NCM_Sudoku_kutatasi_terv_v3.md](NCM_Sudoku_kutatasi_terv_v3.md): frozen Hungarian original of plan v3.0
- [.mcp.json](.mcp.json): project MCP servers; `lacuna-research` (https://lacuna.tiptreesystems.com/api/mcp, Streamable HTTP, read-only, no credentials)
- [.claude/settings.json](.claude/settings.json): project Claude Code settings; disables `caveman@caveman` and `ponytail@ponytail` plugins and sets `CAVEMAN_DEFAULT_MODE=off` (the user-level caveman hooks read this)
- [LICENSE](LICENSE): MIT licence for the own code (`third_party/ncm` keeps its upstream MIT licence; the paper is CC BY 4.0)
- [.gitignore](.gitignore): excludes checkpoints, data, run outputs, paper PDFs, secrets
- [.gitattributes](.gitattributes): LF line endings everywhere, so lock hashes match across Windows and WSL
- [pyproject.toml](pyproject.toml), `uv.lock`, `.python-version`: uv project (Python 3.12, numpy, torch, matplotlib for the WP4 figures; pytest and pymupdf as dev dependencies, pymupdf for the anonymous-build check)
- [paper/AGENTS.md](paper/AGENTS.md): manuscript, submitted to TMLR and under review (D90; changes only through the OpenReview revision process); LaTeX, Tectonic build, generated numbers, tables and figures; number and claim rules
- [src/ncm_sudoku/AGENTS.md](src/ncm_sudoku/AGENTS.md): own package; per-module contracts (frozen `grid.PEER_ORDER`, pinned by `tests/test_peer_order.py`; never reorder; `wp2.py` is the WP2 freeze guard and run-record layer every WP2 runner uses)
- [tests/](tests/): pytest suite: package-module tests (the two solvers `solve.py` and `dlx.py` share `test_solve.py`) plus script and style tests; `sudoku_cases.py` holds shared fixtures, `e2p2_fakes.py` deterministic fakes of the model pieces `e2p2` uses (`toy_model` with embedding tables, `exact_restart` for code-identity tests), `wp2_fakes.py` a complete synthetic set of WP2 raw outputs and valid run records for one role (`write_role`; the TEST role scores E3 on the E2 ids, as the real TEST does; tests of `scripts/wp2_evaluate.py` and `scripts/wp2_dry_check.py`); `golden/` holds outputs generated from earlier code that pin refactors (`summarize2_toy.json`; `e3_scripts_toy.json`: `stages` of `scripts/e3_wholelayer.py` (K 8) and `scripts/e3_probes.py` (SIZES (4, 8)) on the toy runs with the FAST budget, written before the WP2 helper move); `-m slow` runs real-data checks
- [scripts/AGENTS.md](scripts/AGENTS.md): run scripts; most result writers are rerun-guarded (`--force` / `--resume`); read the per-script contract there before forcing a rerun
- [experiments/g0/](experiments/g0/): committed G0 results (`reproduction.json`, `cost.json`)
- [experiments/wp1/](experiments/wp1/): committed WP1 results (`gate.json`, `e1_released.json`, `e1_cal.json`, `pilot_summary.json`, `pilot_report.md`, `screen.json`); `gate.json` must never be regenerated
- [experiments/e2p2/](experiments/e2p2/): committed E2 pilot-2 results (`summary.json`, `report.md`, `sample_size_e2.json`); raw per-record output is in `runs/e2p2/pilot2.json` (git-ignored)
- [experiments/e3prep/](experiments/e3prep/): committed E3 preparation results, all non-confirmatory (`screen.json`, `extract.json`, `probes.json`, `probes_report.md`, `h1_diffs.json`, `h1_diffs_L02.json`, `h1_diffs_L12.json`, `equivariance.json`, `sample_size_h1.json`, `wholelayer.json`, `wholelayer_report.md`, `wholelayer_h1_diffs_L06.json`, `wholelayer_h1_diffs_L12.json`; `budget_sensitivity/` from `scripts/e3_budget_sensitivity.py`: `wholelayer.json`, `wholelayer_h1_diffs_L06.json`, `wholelayer_report.md`)
- [experiments/lock/](experiments/lock/): committed lock preparation results, all non-confirmatory (`power.json`, `power.md`, `test_set.json`, `equivariance_l12.json`, `cal_freqs.json`, `level1_check.json`)
- [experiments/e5/](experiments/e5/): E5 follow-up (D91), non-confirmatory: `cost.json` (generator activation extraction and storage cost; raw arrays in git-ignored `runs/e5/cost/`); counterfactual PROBE pairs (D97, D99): `pairs.json`, arrays in git-ignored `runs/e5/pairs/<subset>/`; their NCM activations: `extract.json`, arrays in git-ignored `runs/e5/acts/<subset>/<a|b>/` (about 2.6 GB); pilot probes (D100): `pilot/<rep>__<readout>__<control>.json`, predictions in git-ignored `runs/e5/pilot/`; causal pilot (D102–D104): `causal/heads.json`, `causal/primary*.json`, `causal/primary_per_pair.json`, `causal/cosines.json`, heads and raw arrays in git-ignored `runs/e5/causal/`; TEST-size simulation (D105, D106): `power.json`; positive control (D94, D95): `kf_extract_<dtype>.json`, `kf_control_<dtype>.json`, `kf_reference_<dtype>.json`; `runs/e5/kf/` (git-ignored) holds the `[clues_end]` activations `acts_<dtype>.npy` (6400, 8, 576), the upstream per-cell split `split.npy` and labels `upstream_targets.npy`
- [experiments/provenance/](experiments/provenance/): `released_data.json` (dataset), `checkpoints.json` (checkpoint revision, sizes, SHA-256, licenses, upstream commit) and `kf_artifacts.json` (Kniazev & Fijalkow Hugging Face artifacts for the E5 positive control: revision, SHA-256, contents, code commit)
- `data/kf/` (git-ignored): Kniazev & Fijalkow artifacts (`download/` the verified zip, `artifacts/` extracted: Orbax checkpoint, configs, `bt_traces_3m.npz`); untrusted input, load npz files with `allow_pickle=False`
- [third_party/ncm/](third_party/ncm/): upstream HazyResearch/ncm as a git submodule at the pinned commit; never modified; imported via `ncm_sudoku.model.import_upstream`
- [third_party/sudoku-residual/](third_party/sudoku-residual/): Kniazev & Fijalkow code as a git submodule at a9b2069; never modified; imported only by the E5 KF scripts running in `.venv-kf/` (create it with `UV_PROJECT_ENVIRONMENT=.venv-kf uv sync --frozen --extra probes --no-install-project --project third_party/sudoku-residual`; git-ignored)
- `checkpoints/` (git-ignored): downloaded by `scripts/fetch_checkpoints.py`; load only through `ncm_sudoku.model.load_model` (weights_only=True)
- `runs/` (git-ignored): per-puzzle raw run outputs
- `runs/submission/tmlr-14707/` (git-ignored): copies of `paper/build/main_anon.pdf` and `paper/build/main.pdf` taken on 2026-11-22 before any rebuild (local builds dated 2026-11-19 14:10, two minutes before commit `fc61836`); the authoritative submitted PDF is the one on OpenReview (D90)
- `runs/e3prep/<probe_train|probe_val>/` (git-ignored): PROBE subset arrays from `scripts/e3_extract.py` (`ids.json`, `puzzles.npy`, `solutions.npy`, `solve.npy`, `mask.npy`, `empty.npy`, `depth.npy`, `L01.npy`..`L12.npy`, `T02.npy`, `T06.npy`, `T12.npy`); about 3 GB total across both subsets
- [experiments/wp2/](experiments/wp2/) and `runs/wp2/<role>/` (`role` = `test` or `dry`): committed WP2 outputs (the TEST report is `experiments/wp2/test/report.md`, D83) and git-ignored raw outputs; run records in `experiments/wp2/<role>/runs/<runner>.json`; the dry approval is `experiments/wp2/dry/check.json` (and `check.md`), written by `scripts/wp2_dry_check.py`; `scripts/wp2_evaluate.py` writes `experiments/wp2/<role>/results.json` and `report.md`; see `ncm_sudoku.wp2`
- `runs/lock/test/` (git-ignored): TEST subset from `scripts/lock_test_set.py` (`ids.json`, `puzzles.npy`, `solutions.npy`, uint8); its hashes are in `experiments/lock/test_set.json`
- `runs/lock/equiv_l12/` (git-ignored): level-12 whole-layer seed probes from `scripts/lock_equiv_l12.py` (`L12_wholelayer_seed{0,1,2}.pt` state dicts, `pca.pt` tensors, `L12_wholelayer.json` config); reload with `load_saved` (`torch.load(weights_only=True)`)
- `runs/e3prep/models/` (git-ignored): selected level-6 linear seed probes from `scripts/e3_probes.py` (`L06_linear_seed{0,1,2}.pt` state dicts, `L06_linear.json` config); loaded with `torch.load(weights_only=True)`
- [.reviews/](.reviews/): external Copilot reviews per artifact (`review-plan.md`, `decisions.md`, briefs, reviewer outputs); transcripts are not committed
- [docs/superpowers/plans/](docs/superpowers/plans/): implementation plans for work packages and selected stages (`YYYY-MM-DD-<topic>.md`)
- [docs/superpowers/specs/](docs/superpowers/specs/): design specs (`YYYY-MM-DD-<topic>-design.md`) for WP4 and WP5, cited by `paper/AGENTS.md`
- [docs/venue/](docs/venue/): target-venue rules from primary sources (`tmlr_submission_rules_2026-11-17.md`: TMLR anonymization, length, style file, LLM policy, OpenReview profile, timeline); re-check before the next OpenReview upload (revision or camera-ready)
- [literature/](literature/): `related_work_novelty_check.md` (related work and novelty verdicts per experiment, 2026-11-08), `presubmission_update_2026-11-16.md` (pre-submission repeat of the search and verification of every `paper/refs.bib` entry), `kniazev_fijalkow_2026_unit_probe.md` (unit-level probe protocol of arXiv:2605.18847 and its code) and `query_log.md` (every search query, tool, and result count)
- [resources/](resources/): source materials; `2610.14162v1.pdf` is the NCM paper (arXiv:2610.14162), local only

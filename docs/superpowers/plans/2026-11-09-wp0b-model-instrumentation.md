# WP0-B: Model Instrumentation and G0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load the NCM Sudoku-hard checkpoint safely on CPU, reproduce the official evaluation (G0), extract teacher codes and full-length cumulative states, and provide a validated `forward_with_intervention` wrapper (four branches A–D) with identity tests and cost measurements.

**Architecture:** Upstream `third_party/ncm` (submodule, commit `c70274273f489abc73832b2b98584a8483b6b203`) is imported unmodified via `sys.path`. Own modules in `src/ncm_sudoku/` mirror the exact upstream evaluation path (`scripts/eval_shard.py`, `scripts/eval_merge.py`) and the generation loop (`NextConceptTransformer.generate`) so that identity tests can compare bit-for-bit. G0 scripts write committed summaries to `experiments/g0/`.

**Tech Stack:** Python 3.12 (uv, native Windows, D30), torch 2.15 CPU, omegaconf, hydra-core, numpy, pytest.

**Spec:** `research_plan_v3.4.md` §2.2 items 1–9, §6, §7.1; `DECISIONS.md` D05, D08, D20, D22, D26, D29, D30.

## Upstream facts this plan relies on (read at the pinned commit, 2026-11-09)

- Config `config/eval/sudoku-hard.yaml` is byte-identical (modulo trailing whitespace) to the checkpoint repo's `sudoku/hard/config.yaml`. Generation: `temperature 0.0, top_k 0, top_p 1.0, cfg_scale 0.0`; model `query_level0: true` (no `l0_autoregressive`), `prefix_len 91`, `use_rope true`; `prefix_pad_id` is None; levels `1,2,4,6,9,13,18,26,37,50,67,89` (sum 322).
- `eval_shard.run`: `g = net.generate(None, x, temperature, top_k, top_p, cfg_scale)`; `_, zl = vq.idx_to_zhats(g, return_zlevels=True)`; tokens = `vqvae.decoder(zl[-1]).argmax(-1)` (no frequency penalty in this config). Prefix = the 91 puzzle tokens.
- `generate` (non-KV, cfg=0, query_level0, no l0_ar path): level 0 from learned queries; then for `level_idx in 0..10`: `z_q = vq.embeddings[level_idx](idx_next)`; `z_hat, x = vq.get_next_autoregressive_input(level_idx, z_hat, z_q)` (in-place `z_hat.add_`); `x = wte(x) + level_pos_embed[...]`; `logits = _decode_level_logits(x, prefix_emb, level_idx, _pbias, hidx=level_idx+1)`; argmax. Each level sees only the prefix and the downsampled cumulative `z_hat`, not earlier tokens.
- `idx_to_zhats` appends the same in-place tensor 12 times (aliasing, D22).
- `eval_merge.exact`: strings via `SudokuTokenizer.decode(skip_special_tokens=True)` (`_` blank, `|` separator); solved = string equality; cell % = mean over `zip(cells(h), cells(r))` (shrinking denominator); valid requires 81 digits, no `0`, all units permutations.
- Checkpoints `generator.pt`, `tokenizer.pt` (HF revision `d342ce8aaea58830eef3b8ad473664673e41f692`) contain only `OrderedDict`, tensor storages, `_rebuild_tensor_v2` → loadable with `torch.load(..., weights_only=True)`. No training metadata (corruption regime not recorded in the checkpoint; §7.1).
- CPU probe: 128 released hard puzzles in 142.6 s (≈1.1 s/puzzle) with deterministic algorithms; 109/128 solved.

## Global Constraints

- Never modify `third_party/ncm`; never call upstream functions that `torch.load` with `weights_only=False` (`VQVAETokenizer.from_config`, `eval_shard.py`).
- All checkpoint loads use `weights_only=True`.
- FP32, eager, `torch.use_deterministic_algorithms(True)`, CPU, `torch.no_grad()`, models in `.eval()`.
- Levels are 1-indexed in public APIs and docs (plan §3); 0-indexed only inside code that mirrors upstream.
- Branches A–D of one puzzle run with identical batch tensors (D20).
- Model-dependent tests are marked `@pytest.mark.slow` and skip when `checkpoints/sudoku/hard` or `data/released/sudoku/hard` is missing.
- Committed outputs only under `experiments/`; per-puzzle raw outputs under `runs/` (git-ignored).

## Review Focus

1. Own continuation loop diverging from upstream `generate` (any numerical or ordering difference) → `continue_generation(..., n_given_levels=0)` must equal `net.generate` bit-for-bit (Task 4 `test_noop_matches_upstream`).
2. In-place `z_hat` updates corrupting saved states → mutating a later state leaves earlier ones unchanged (Task 3 `test_state_storage_isolated`).
3. A checkpoint file carrying a non-tensor global → load refused (Task 1 `test_unsafe_checkpoint_refused`).
4. 1-indexed vs 0-indexed level off-by-one → branch C differs from A only inside the level-ℓ slice; slice lengths equal the level ladder (Task 4 `test_branch_c_only_level_slice`, Task 1 `test_level_slices`).
5. A continuous patch through `z_hat_override` silently ignored or applied at the wrong level → override with the clean state reproduces A, a nonzero change alters downstream codes (Task 4 `test_zhat_override_identity`, `test_zhat_override_changes_output`).
6. Running the same puzzle in different batch sizes giving different codes → measured and reported, not assumed (Task 4 `test_batch_size_effect_recorded` asserts equality for this checkpoint on CPU; if it fails, rule per D20 and keep branch batches identical).

---

### Task 1: Safe checkpoint loading and provenance

**Files:** Create `src/ncm_sudoku/model.py`, `scripts/fetch_checkpoints.py`, `experiments/provenance/checkpoints.json` (script output), `tests/test_model.py`. Modify `pyproject.toml` only via `uv add` (torch, omegaconf, hydra-core are already added), `.gitignore` (add `runs/`), `AGENTS.md` (index: `third_party/ncm`, `checkpoints/`, `experiments/g0/`).

**Interfaces — Produces:**
- `UPSTREAM_DIR: Path` (= repo `third_party/ncm`); `import_upstream()` inserts it into `sys.path` once.
- `@dataclass(frozen=True) NcmModel: net, vqvae, cfg, levels: tuple[int, ...]`.
- `load_model(ckpt_dir: Path) -> NcmModel`: build `VQVAE(**cfg.tokenizer.vqvae minus checkpoint_path)` and `NextConceptTransformer(vqvae_local=vqvae, config=cfg.model)`, load `["model"]` state dicts with `weights_only=True, map_location="cpu"`, `strict=True`, call `.eval()`, set `torch.use_deterministic_algorithms(True)`.
- `level_slices(levels) -> list[slice]` (index 0 ↔ plan level 1).
- Script records HF model revision, file sizes, SHA-256 for `sudoku/hard/{generator.pt,tokenizer.pt,config.yaml}` into `experiments/provenance/checkpoints.json`, plus the upstream submodule commit and licenses (`"checkpoints_license": "MIT"` from the HF card, `"code_license": "MIT"` from `third_party/ncm/LICENSE`).

- [ ] Step 1: tests — `test_level_slices` (lengths `1,2,4,6,9,13,18,26,37,50,67,89`, contiguous, end 322); `test_unsafe_checkpoint_refused` (write `{"model": os.system}` via `torch.save` to tmp, `load_model`-internal `_safe_load(path)` raises `pickle.UnpicklingError`); slow `test_load_model` (levels match config, parameter counts 25.46M ± 0.01M and 14.90M ± 0.01M, both modules not training, `torch.are_deterministic_algorithms_enabled()`); slow `test_checkpoint_hashes` (files match `checkpoints.json`).
- [ ] Step 2: run → FAIL (import error).
- [ ] Step 3: implement `model.py`, run the fetch script.
- [ ] Step 4: `uv run pytest -q` and `uv run pytest -q -m slow` → PASS.
- [ ] Step 5: commit `feat: safe checkpoint loading and provenance` (include submodule, `.gitmodules`, provenance JSON, AGENTS.md).

### Task 2: Official metric mirror

**Files:** Create `src/ncm_sudoku/official.py`, `tests/test_official.py`.

**Interfaces — Produces:** `decode_string(tokens: Sequence[int]) -> str` (mirrors `SudokuTokenizer.decode(skip_special_tokens=True)`: `_`, `1`–`9`, `|`, drops 11); `official_exact(hyps: list[str], refs: list[str]) -> dict` with keys `solved_pct, solved_n, n, cell_pct, valid_pct`, all `*_pct` on the 0–100 scale (as `eval_merge` prints them), reproducing `eval_merge.exact` including its shrinking cell denominator; an empty hyp contributes cell value 0.0 instead of NaN.

- [ ] Step 1: tests — identical strings → solved_pct 100.0; one wrong digit → solved_pct 0.0, cell_pct ≈ 100·80/81; empty hyp → cell value 0.0; truncated hyp (first 5 rows) → cell computed over the shorter zip (mirror, documented as upstream behaviour); hyp containing `_` → not valid; decode of `encode_solution_tokens(S)` contains 8 `|` and no `<BOS>`.
- [ ] Steps 2–4: FAIL → implement → PASS (full suite).
- [ ] Step 5: commit `feat: mirror of the official exact metric`.

### Task 3: Upstream-mirroring runner, teacher codes, cumulative states

**Files:** Create `src/ncm_sudoku/runner.py`, `src/ncm_sudoku/states.py`, `tests/test_runner.py`, `tests/test_states.py`. Modify `src/ncm_sudoku/grid.py`, `tests/test_grid.py`.

**Interfaces — Consumes:** `model.NcmModel`, `grid.encode_puzzle_tokens`, `grid.encode_solution_tokens`.
**Produces:**
- `runner.generate_codes(m, puzzles: np.ndarray (n,81), batch_size: int = 32) -> torch.LongTensor (n, 322)` — exactly `net.generate(None, x, temperature=0.0, top_k=0, top_p=1.0, cfg_scale=0.0)` per batch.
- `runner.decode_codes(m, codes) -> torch.LongTensor (n, 89)` — `vq.idx_to_zhats(codes, return_zlevels=True)[1][-1]` → `vqvae.decoder` → `argmax(-1)`.
- `runner.teacher_codes(m, solutions: np.ndarray (n,81)) -> torch.LongTensor (n, 322)` — `vqvae.encode` on 89-token solutions.
- `states.cumulative_states(m, codes, upto: int = 12) -> list[torch.Tensor]` — `codes` has shape `(n, k)` with `k >= sum(levels[:upto])`; own loop mirroring `idx_to_zhats` (embedding lookup per level, `_up_to_full` for levels < 12, `_apply_quant_resi`, accumulate), returning a `clone()` after each level; element `ℓ-1` is $Z_{\leq\ell}$, shape `(n, 89, 256)`.
- `states.decode_state(m, z) -> torch.LongTensor (n, 89)` — `vqvae.decoder(z).argmax(-1)`; `states.decode_state_logits(m, z) -> torch.Tensor (n, 89, 12)` — `vqvae.decoder(z)` (E4 digit-margin endpoint).
- `grid.CELL_TOKEN_INDICES: np.ndarray` (81,) = `c + c // 9` (cell → position in the 89-token output/state; the 91-token puzzle prefix uses `1 + c + c // 9`); `states.cell_states(z) -> torch.Tensor (n, 81, 256)` = `z[:, CELL_TOKEN_INDICES, :]` (plan §8.1 cell–token mapping fixed in G0).

- [ ] Step 1: tests — fast `test_cell_token_indices` (`np.array(encode_solution_tokens(S))[CELL_TOKEN_INDICES] == S`; puzzle prefix `encode_puzzle_tokens(P)[1 + CELL_TOKEN_INDICES] == P`). Slow tests on 4 released puzzles — `test_generate_codes_shape` (shape, values in 0..15); `test_generate_deterministic` (two runs equal); `test_teacher_reconstruction` (decode of teacher codes of 16 released solutions equals `encode_solution_tokens(solution)` for all); `test_final_state_matches_upstream` (`torch.equal(states[-1], idx_to_zhats(codes)[0][-1])`); `test_state_storage_isolated` (distinct `data_ptr`; `states[11].add_(1.0)` leaves `states[5]` unchanged); `test_prefix_recomputation` (`cumulative_states(m, codes[:, :level_slices(levels)[5].stop], upto=6)[-1]` equals `states[5]`); `test_decode_state_logits_shape` (`(n, 89, 12)`, argmax equals `decode_state`); `test_level12_contribution_nonzero_then_unequal` (if `‖Z≤12 − Z≤11‖ > 0` then not equal, D29); `test_decode_state_matches_runner` (`decode_state(states[-1]) == decode_codes(codes)`).
- [ ] Steps 2–4: FAIL → implement → PASS.
- [ ] Step 5: commit `feat: upstream-mirroring runner, teacher codes, cumulative states`.

### Task 4: `forward_with_intervention` and the four branches

**Files:** Create `src/ncm_sudoku/intervene.py`, `tests/test_intervene.py`.

**Interfaces — Consumes:** Tasks 1–3.
**Produces:**
- `continue_generation(m, prefix_tokens: torch.LongTensor (B,91), given_codes: torch.LongTensor (B, k) | None, n_given_levels: int, z_hat_override: torch.Tensor | None = None) -> torch.LongTensor (B, 322)` — mirrors the upstream `generate` path listed above; `n_given_levels = 0` (with `given_codes=None`) runs level 1 from the learned queries; otherwise levels `1..n_given_levels` are taken from `given_codes` (`k` must equal their total length) and only update `z_hat`; generation continues from level `n_given_levels + 1`. Validates `0 <= n_given_levels <= 12`. `z_hat_override` (shape `(B, 89, 256)`, allowed for `1 <= n_given_levels <= 11`) replaces the cumulative state at the handoff: after the given levels, `z_hat = z_hat_override.clone()` and the next generator input is `F.interpolate(z_hat.transpose(-1,-2), size=(levels[n_given_levels],), mode="area").transpose(-1,-2)`; all later levels accumulate on the patched state (E4 generator-mediated route, plan §9.2). Returned codes for levels `1..n_given_levels` are `given_codes`.
- `forward_with_intervention = continue_generation` (public name required by plan §2.2 item 4).
- `@dataclass(frozen=True) Branches: A, B, C, D: torch.LongTensor`.
- `run_branches(m, prefix_tokens, clean_codes: torch.LongTensor | None, level: int, perturbed_level_codes) -> Branches` for `level in 1..11`: A = `clean_codes`, or, when `None`, `continue_generation(prefix_tokens, None, 0)` on the same batch (callers passing `clean_codes` must have produced them from the identical `prefix_tokens` batch; documented); B = `continue_generation(prefix, clean[:, :end(level)], level)`; C = clean with the level slice replaced; D = `continue_generation(prefix, cat(clean[:, :start(level)], perturbed), level)`. B and D use the same `prefix_tokens` tensor (D20). `level == 12` raises `ValueError` (no suffix).

- [ ] Step 1: slow tests on 4 released puzzles — `test_noop_matches_upstream` (`continue_generation(n_given_levels=0)` equals `generate_codes` bit-for-bit); `test_writeback_all_levels` (given all 12 levels → identical); `test_sham_b_equals_a` for levels 1, 2, 6, 11 (level 1 is the only path through the level-0 query handoff and `learned_up_l1`); `test_zhat_override_identity` (for levels 2 and 6, `z_hat_override = cumulative_states(m, clean)[level-1]` reproduces A bit-for-bit); `test_zhat_override_changes_output` (adding a fixed nonzero tensor to the override at level 2 changes at least one downstream code); `test_branch_c_only_level_slice` (C differs from A only inside `level_slices[level-1]`, using a perturbation that changes one code); `test_branch_d_prefix_fixed` (D equals given codes up to the end of level ℓ); `test_level_12_rejected`; `test_batch_size_effect_recorded` (puzzle 0 alone vs inside the batch of 4 → equal codes; failure is reported to the ledger as a D20 ruling, not silenced).
- [ ] Steps 2–4: FAIL → implement → PASS.
- [ ] Step 5: commit `feat: forward_with_intervention and four-branch runner`.

### Task 5: G0 reproduction and cost measurement

**Files:** Create `src/ncm_sudoku/g0.py`, `scripts/g0_reproduce.py`, `scripts/g0_cost.py`, `tests/test_g0.py`; outputs `experiments/g0/reproduction.json`, `experiments/g0/cost.json` (committed), `runs/g0/` (ignored).

**Interfaces — Produces:**
- `environment_record() -> dict` (python, torch, numpy versions; platform; `torch.get_num_threads()`; deterministic flag; upstream commit from `git -C third_party/ncm rev-parse HEAD`; checkpoint provenance file contents).
- `reproduce(m, puzzles, solutions, batch_size=128) -> dict` with `official` (from `official_exact`), `own` (means of `validate.evaluate` fields), `n`, `batch_size` (128 mirrors the upstream config), `per_puzzle` (list of solve booleans, kept out of the committed summary).
- `identity_checks(m, puzzles: np.ndarray) -> dict[str, bool]` — runs in-process on the loaded model: no-op vs upstream `generate`, write-back of all levels, sham B=A at levels 1, 2, 6, 11, `z_hat_override` identity at levels 2 and 6, final-state parity with `idx_to_zhats`, state storage isolation; returns one boolean per check (no reliance on pytest exit codes).
- `g0_rule(official_solved_pct: float, identity: dict[str, bool]) -> dict` implementing D20 part (a) `abs(x - 86.1) <= 1.0` and part (b) `set(identity) == IDENTITY_KEYS and all(identity.values())`, where `IDENTITY_KEYS` names the 10 checks above, with `changed_output_count: "unavailable"` (D29; no paired reference predictions).
- `g0_reproduce.py`: all 2,000 released hard puzzles; `identity_checks` on the first 8 puzzles; writes summary + environment + identity results + rule outcome.
- `g0_cost.py` (`uv add psutil`): 20 released puzzles; for baseline generation, `cumulative_states`, branch C (decode only), and branch D at levels 2, 6, 11: wall time, process RSS before/after and peak (`psutil.Process().memory_info()`), and bytes of the tensors produced (`sum(t.nbytes)`); storage per puzzle for discrete codes (322 × int8 and as stored int64) versus saved cumulative states (12 × 89 × 256 × 4 B); per-puzzle means into `experiments/g0/cost.json`.

- [ ] Step 1: tests — `test_environment_record_keys`; `test_g0_rule` (86.1 → pass, 84.9 → fail, 87.1 → pass, any identity False → fail, missing identity key → fail, `changed_output_count == "unavailable"`); slow `test_identity_checks_all_true` (4 puzzles); slow `test_reproduce_small` (4 puzzles; keys present including `batch_size`; official solved_n ≤ 4; own solve mean ×100 equals official solved_pct on these well-formed outputs).
- [ ] Steps 2–4: FAIL → implement → PASS.
- [ ] Step 5: run `uv run python scripts/g0_reproduce.py` and `uv run python scripts/g0_cost.py` in the background (≈40 min); read both JSON outputs.
- [ ] Step 6: append the G0 outcome to `DECISIONS.md` (D31: rule (a)/(b) result, official solved %, cost per puzzle) — if (a) fails, record the investigation status instead of continuing silently (D20).
- [ ] Step 7: commit `feat: G0 reproduction and cost measurement` with the outputs.

### Task 6: Documentation pass

**Files:** Create `research_plan_v3.5.md` (copy of v3.4 with: §2.2 item 1 "under WSL2" → "on native Windows (D30)"; §7.1 note that the released checkpoints carry no training metadata; §16 entries 22–23). Modify `DECISIONS.md` (mark D30 wording done), `AGENTS.md` (authoritative plan v3.5; Verification adds `uv run pytest -q -m slow` needs checkpoints and data; index `src/ncm_sudoku/` modules model, official, runner, states, intervene, g0; `scripts/`; `experiments/g0/`).

- [ ] Step 1: make the edits; `uv run pytest -q` → PASS.
- [ ] Step 2: commit `docs: plan v3.5 and DOX update after WP0-B`.

## Out of scope

Perturbation policies and dose grids (WP1/E2), generator development batches and the D27 distribution gate, probes (E3), E4 patching, BF16/CUDA cross-check.

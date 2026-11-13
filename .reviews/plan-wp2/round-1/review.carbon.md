Elolvasom a megadott review briefet (`brief.carbon.md`), hogy pontosan kövessem a csak olvasható ellenőrzési feladat előírásait.

I have read the review brief and will now examine the WP2 implementation plan (`2026-11-13-wp2.md`), the locked protocol (`research_plan_v3.7.md`), and `DECISIONS.md` (D74–D77).

### Verdict
The plan cannot be executed safely as written: two blockers would leak TEST outcomes before runs finish or corrupt metrics/TOST verdicts, and four major defects affect protocol fidelity, crash/resume recovery, and post-freeze dry-run checks. The single most important change is hardening single-look and dry-gate enforcement before `wp2-code` is tagged — removing TEST `generated_solve_share` from `runs/e3_extract.json`, enforcing technical-only stdout and `--resume` across all five runners, gating TEST `guard_start` on `dry/check.json` (`technical_success: true`), and fixing the `hidden_single_f1`, `tost`, and `wp2_dry_check.py` bugs below.

### Findings

```
CARBON-1 | blocker | Task 7 (line 588), Tasks 4/7/10, Task 1 (lines 146, 159-160, 169-171), Task 14 (line 1104)
Claim: The TEST run leaks outcome metrics into the inspected run record and runner stdout before all TEST runs finish, and `guard_start` neither requires a passing `dry/check.json` nor detects dirty files inside `third_party/ncm`.
Evidence: `docs/superpowers/plans/2026-11-13-wp2.md:588` writes `generated_solve_share` into `experiments/wp2/test/runs/e3_extract.json`, which `line 1104` instructs reading after the first 10-minute TEST script, breaking `DECISIONS.md:115` (D76(5)) and Review Focus 3 (`line 93`). Tasks 4, 7, and 10 omit technical-only stdout rules/tests while their template scripts (`scripts/wp1_e1.py:36`, `scripts/e3_extract.py:106`, `scripts/lock_equiv_l12.py:142`) print `solve`, `generated_solve_rate`, `mean_deviation`, and `share_within`. In Task 1, `guard_start` (`lines 159-160`) checks `dry/runs/<runner>.json` completion but never checks `experiments/wp2/dry/check.json` (`technical_success is True` at `tag_commit`), and `freeze_state` (`lines 169-171`, `src/ncm_sudoku/g0.py:51`) checks `third_party/ncm` `HEAD` only, ignoring uncommitted submodule edits (and raising `CalledProcessError` if `wp2-code` does not yet exist).
Recommendation: Omit `generated_solve_share` from `runs/e3_extract.json`; enforce and test technical-only stdout on `wp2_e1.py`, `wp2_e3_extract.py`, and `wp2_equiv.py`; require `dry/check.json` (`technical_success: True`, `code.commit == tag_commit`) in `guard_start(..., role="test", ...)`; check `git -C third_party/ncm status --porcelain == ""` and catch missing-tag errors in `freeze_state`.
Confidence: high
```

```
CARBON-2 | blocker | Task 6 (lines 524, 545-548, 561) and Task 11 (lines 843-846)
Claim: `hidden_single_f1` mis-unpacks `labels.hidden_singles` and penalizes true naked+hidden singles as false positives in `hidden_only`, while `wp2eval.tost` fails to filter NaNs before calling `e2p2.interval` and can declare `equivalent: True` on NaN data.
Evidence: `src/ncm_sudoku/labels.py:41-56` returns `(u, d, c)` 3-tuples with 1-based digits `1..9`, contradicting `2026-11-13-wp2.md:561` ("a set of (u, d) pairs"). Filtering only truth triples whose cell is not a naked single (`line 561`) while keeping all predicted `(u, d)` pairs turns every accurately predicted naked+hidden single into a false positive in `hidden_only` (uncaught by `lines 545-548`, which assert `r["all"]["f1"] == 1.0` only); also when `0 < n_true < N` and `n_pred == 0`, F1 must return `0.0` rather than dividing by zero. In `2026-11-13-wp2.md:843-846`, `contrast` drops NaNs (`line 95`), whereas `tost` passes `values` directly to `src/ncm_sudoku/e2p2.py:234-245`: `np.abs(np.nan) > 1e-12` is `False`, so with `< 20` finite nonzeros `interval` takes the `"bound"` branch using total `n` (e.g., 600 NaNs give `cp_upper(0, 600, 0.9833) = 0.0068 < 0.01`, `equivalent: True`), and with `>= 20` nonzeros a single NaN yields `(nan, nan)`.
Recommendation: In `hidden_single_f1`, unpack `(u, d, c)` (mapping `d - 1`), exclude predicted naked singles (`(pred_grid[p, c] >= 0.5).sum() == 1`) from `hidden_only` predictions (asserting `r["hidden_only"]["f1"] == 1.0` on `truth`), and return `0.0` when both true classes exist and `tp == 0`. In `wp2eval.tost`, apply the same NaN filtering and `n == 0` guard (`equivalent=False`) as `contrast`, and use `abs(v) > 1e-12` in `contrast["discordance"]` to match `e2p2.interval:237`.
Confidence: high
```

```
CARBON-3 | major | Spec ambiguities 2-3 (lines 20-24), Task 8 (lines 643-662), Task 12 (line 957)
Claim: Running §8.2's size-matched random, label-permutation, level-6 teacher, and training-size controls only on the 256-d per-cell readout misses the primary 512-d whole-layer H1 probe and mixes incompatible feature spaces in `e3_main`.
Evidence: `research_plan_v3.7.md:229-237` makes the 512-d cell-relative whole-layer linear probe (`in_dim = 593`, `n_params = 5,346`) primary for H1, while `§8.2` (`lines 247-252`) requires a "Random, size-matched feature" ("Same training cost"), a label-permutation control testing "The probe's capacity", a teacher control, and a training-size curve for "the readout's data requirements". `2026-11-13-wp2.md:20-24, 652-657` runs these only at 256-d per-cell (`n_params = 3,042`), and `line 957` computes `e3_main` relative differences of 256-d controls against the 512-d `wl_L06.generated` probe while omitting `raw_mlp` and `peer_counts_linear` (`§8.2` rows 1-2).
Recommendation: Keep the D64 per-cell `controls` and `training_size` stages for dry-run verification, add whole-layer L06 `random` (512-d), `label_permuted`, `teacher_L06` (from extracted `T06.npy`), and whole-layer L06 training-size fits to `NEW_FITS`, include `raw_mlp` and `peer_counts_linear` in `e3_main`, and compute relative differences within matching feature constructions only.
Confidence: high
```

```
CARBON-4 | major | Task 11 (line 847), Task 12 (line 953)
Claim: `auc_frozen` computes and reports post-hoc TEST-overlap AUCs (`test_own = e2p2.auc_pair`), directly contradicting locked §7.3 and §12.2 rules.
Evidence: `research_plan_v3.7.md:211` states "if TEST nodes do not cover it, no AUC is reported for that pair", and `line 421` locks "2 vs. 11: no positive-width range, so no equal-damage AUC for that pair". `2026-11-13-wp2.md:847` calls `e2p2.auc_pair` (`src/ncm_sudoku/e2p2.py:265-273`), which integrates AUCs over TEST's empirically observed damage overlap for `2-11` and uncovered `6-11`.
Recommendation: Remove `e2p2.auc_pair` (`test_own`) from `auc_frozen`; record only each level's merged TEST `(mean_tv, mean_delta_solve)` nodes and `[min_tv, max_tv]` bounds as coverage diagnostics.
Confidence: high
```

```
CARBON-5 | major | Task 1 (lines 130, 161), Task 3 (lines 295, 334-341), Tasks 4/7/10, Task 8 (lines 643, 656, 667), Task 12 (line 961)
Claim: Crash/resume and stage-reuse contracts fail across `wp2_e2.py`, `wp2e3.py`, and the non-staged TEST runners.
Evidence: In `wp2_e2.py` (`lines 295, 334-341`), `A_sha256` is written only in `finish_run` (Step 11), so an incomplete record after a mid-run crash has no `A_sha256` for Step 7's `--resume` check (and Step 7 fails if crashed before `A.npy` was saved; Step 8 also loads `parts/*.json` even on `--force`, and `np.save` appends `.npy` unless temp paths end in `.tmp.npy`). Tasks 4, 7, and 10 omit `--resume` (`resume_ok=False`, `line 130`), wedging TEST recovery after any mid-run interruption because `guard_start` blocks both bare reruns (`line 161`) and `--force` on `test` (`line 157`), violating `research_plan_v3.7.md:342` and Ambiguity 21 (`line 42`). In `wp2e3.py`, `STAGES` callables take `(Sets, dict)` (`line 643`, budget kwargs only), leaving `"training_size"` unable to reuse `pc_L06.linear` (`line 656`), especially across `--resume` (`line 765`); `save_stage` (`line 667`) and `wp2_evaluate.py` (`line 961`) also fail to exempt reused `n2000` and 27-unit `unit_digit` predictions from 81-cell `secondary_metrics`.
Recommendation: Persist `A_sha256` into `runs/e2.json` immediately after atomic `.tmp.npy` write (recomputing `A` if absent on resume) and load `parts/` only when `resume=True` (clearing stale artifacts on `--force` in `wp2_e2.py`/`wp2_e3.py`); enable `--resume` (clean restart after input/code check) on `wp2_e1.py`, `wp2_e3_extract.py`, and `wp2_equiv.py`; pass stored `stages` to `STAGES` callables and skip model-saving/81-cell `secondary_metrics` for `rule`, `marginal`, `unit_digit`, and reused `n2000`.
Confidence: high
```

```
CARBON-6 | major | Task 13 (lines 1025-1042), Task 7 (line 589), Tasks 8-9 (lines 681, 742)
Claim: `wp2_dry_check.py` will crash on `None` Hamming fields, mis-check dry id counts, fail on boolean `.npy` diffs, and cannot catch `score` vs. `val` mix-ups in E3 because `score == PROBE-VAL` in the dry run.
Evidence: `compare_keyed` (`line 1025`) extends `scripts/lock_level1_check.py:61-64` (`abs(new_by[k][f] - old_by[k][f])`) to all 20 E2 fields, including `hamming_CA` and `hamming_CA_empty`, which are `None` on ~14% of CAL level-1 uniform rows (`DECISIONS.md:62`, D53), raising `TypeError` after freeze. `2026-11-13-wp2.md:1039` checks E1 on "30 ids" instead of `N_DRY = 50` (`line 297`), `lines 1027-1028` omit filtering 300-puzzle `level1_full_batch.json` and `base` references to dry ids, and `compare_dirs` (`line 589`) subtracts `bool` arrays (`solve.npy`, `empty.npy`), which raises `TypeError` in NumPy 2.5.4. In E3 dry, `n_score == n_val == 500` on identical data, while `line 681` tests `score != val` on one stage only instead of all 29 `STAGE_FITS`.
Recommendation: Guard `None` values in `compare_keyed` (counting `None` mismatches in `n_diff` and computing `max_abs_diff` over finite pairs); filter `level1`, `base`, and E1 checks to all 50 dry ids; cast arrays to `float64` in `compare_dirs`; test all 12 E3 stages (29 fits) on a synthetic `score` set with `n_score != n_val` and disjoint ids.
Confidence: high
```

- `CARBON-7 | minor | Task 6 (line 515) & Task 12 (line 960) | research_plan_v3.7.md:136 (§5.2) requires sample size and label proportion per depth stratum, so add candidate-bit positive_rate to depth_breakdown alongside brier, n_cells, and n_puzzles.`
- `CARBON-8 | minor | Task 4 (lines 370-377) | research_plan_v3.7.md:335 (§10) defines Cell Hamming separately for all and originally empty cells; add empty-cell Hamming to e1_records/e1_table and return None on format errors instead of comparing -1 slots as in src/ncm_sudoku/e1.py:36.`
- `CARBON-9 | minor | Task 11 (lines 842, 853-856) & Task 12 (lines 939-969) | Add explicit fallback readings when theta2_prime is non-equivalent with 95% CI excluding 0 or Level 12 fails l95 > 0 / theta_T equivalence, drop dead ACCURATE_MARGIN and EQUIV_SHARE constants superseded by D77(7), and align "equivariance_reading" with results.json.`
- `CARBON-10 | minor | Task 12 (lines 939-977) & Task 13 (lines 1025-1042) | Include date, code_state(), freeze_state(), and environment_record() in results.json and check.json per research_plan_v3.7.md:426 (§12.2), plus downstream_changes_D quantiles and §7.4's disclosure (line 219) that post-intervention intermediate decodings/cell maps are not saved.`
- `CARBON-11 | minor | Spec ambiguities 11 & 13 (lines 34-37) & src/ncm_sudoku/e2p2.py:55,75,76,109,161 | Unlike chunk=50 generation, e2._eval calls decode_codes unchunked (batch 50 in dry, 300 in pilot2.json, 600 in TEST); document this batch-shape difference in Ambiguity 11/13.`

### Claims checked
- Locked SHA-256 hashes (checkpoints, upstream commit, `labels.py`, `PEER_IDX`, `cal_freqs.json`, TEST `ids`/`puzzles`/`solutions`), E2 doses, `run_seed`, and `AUC_RANGES["6-11"]` match `research_plan_v3.7.md` §12.2 and committed JSONs — **holds** (git-ignored binary files on disk were not re-hashed under the no-execution rule: **could not verify** directly).
- Interval levels (98.33% family, 96.67% H1 TOST ±0.01, 90% TOST for $\theta_2'$ ±0.03 and $\theta_T$ ±0.01, 95% otherwise), 10,000-resample cluster bootstrap (`seed=0`), and `< 20` rare-event Clopper–Pearson bounds match v3.7 §8.3, §11.1–§11.4 and `power.py` — **holds** (modulo `tost` NaN filtering, `CARBON-2`).
- H1 two-reading rules and verbatim `S13` rows match v3.7 §8.3, §13 and D77 — **holds** for H1/H2/H3, **does not hold** for unmapped $\theta_2'$ and Level-12 outcomes (`CARBON-9`).
- Every primary, secondary, and exploratory analysis in v3.7 §6–§8, §11, §13 is faithfully specified without post-hoc additions — **does not hold** (`auc_frozen` adds forbidden TEST-own AUCs, `CARBON-4`; §8.2 controls omit 512-d whole-layer counterparts, `CARBON-3`).
- Refactors to `run_pilot2`, `fit_selected`, `fit_cells`/`run_controls`, and `random_rows` keep D53/D64/D67 reproducible (`cal[:50]` and `random_features` preserve prefix RNG streams) — **holds**.
- Single-look safety, freeze guard, and crash/resume prevent premature TEST outcome exposure and deadlocked reruns — **does not hold** (`CARBON-1`, `CARBON-5`).
- Dry-run checks (`wp2_dry_check.py`) pass on real CAL/PROBE-VAL data and cover all TEST score-set code paths — **does not hold** (`CARBON-6`).



Completed the read-only review of docs/superpowers/plans/2026-11-13-wp2.md against
research_plan_v3.7.md, DECISIONS.md (D74–D77), existing src/ncm_sudoku/ and scripts/ modules, and
frozen lock/pilot JSON artifacts, following brief.carbon.md (### Verdict, ### Findings
CARBON-1–CARBON-11, ### Claims checked, in English under 1,200 words) without creating, modifying,
or deleting any files or running execution commands.


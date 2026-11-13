# Roadmap

Single place for work-package status, backlog, and open items. Decisions live in `DECISIONS.md`; the protocol in the authoritative research plan. Effort figures are planning estimates, not plan commitments (plan §12.3: cost estimates follow the measured pilot).

## Work packages

| WP | Content (plan §12.3) | Status | Compute estimate (CPU, measured basis) | Effort estimate |
|---|---|---|---|---|
| WP0-A | Sudoku core: serialization, validator, solvers, labeler, generator, released-data loader | done (2026-11-08) | — | — |
| WP0-B | Safe loading, official-metric mirror, runner, cumulative states, `forward_with_intervention`, G0 reproduction, cost | done (2026-11-09); G0 passed: 86.3% vs 86.1% (D31) | G0 run ≈ 45 min | — |
| WP1 | Generator freeze + terminal distribution gate (D27); E1 tokenizer/generator split; E2 level sensitivity, four-branch compensation, dose calibration | done (2026-11-09): gate passed (D41); E1 on released and CAL; E2 pilot (D42, non-confirmatory) | measured: gate 20 min; E1 on CAL 5 min; E2 pilot (300 × levels 1/2/6/11 × 2 policies × doses × 3 seeds) 2.36 h | 1 session |
| E2 pilot 2 | Plan v3.6 (D43–D52): review, implementation (TV damage, level-1 enumeration, extended doses, diagnostics), second pilot on CAL | done (2026-11-11): D53; E2 TEST requirement 600 | measured: pilot 3.91 h; sample-size simulation about 15 min | 1 session |
| E3 preparation | Solver waves, labels and depth on PROBE subsets; probe and baseline training-size curves; H1 sample size (plan §12.1) | done (2026-11-11): D64; whole-layer diagnostic D65–D67, budget sensitivity D69; H1 form decided (D68) | probes minutes–hours | 2–3 sessions |
| Lock | Sample-size simulation (E2 and H1 → one TEST size), §12.2 checklist, OSF embargoed registration with git tag hash | done (2026-11-12): `research_plan_v3.7.md` reviewed (high tier), tag `prereg-v3.7`, embargoed OSF registration https://osf.io/m28fx (D75) | minutes (simulation) | 1–2 sessions |
| WP2 | Confirmatory TEST runs (D76): E1, E2 (H2, H3) and E3 (H1) on the 600 TEST puzzles with every pre-specified secondary and exploratory analysis; code freeze (tag `wp2-code`), dry run on CAL/PROBE-VAL, TEST runs, pre-written evaluation, report under `experiments/wp2/` | in progress (2026-11-13): implementation plan `docs/superpowers/plans/2026-11-13-wp2.md` reviewed (D77, D78); next: subagent-driven implementation | planning estimate from measured stage times: dry run ≈ 8.1 h, TEST ≈ 17.5 h (E3 ≈ 6.4 h, E2 ≈ 10.1 h incl. ≤ 2 h unmeasured diagnostics; re-estimated from the dry run before TEST) | 4–5 sessions |
| WP3 | E4a / E4b targeted patching (conditional on the E4 gate); needs its own protocol and registration before its test set is generated | conditional | depends on E4-TEST size | 3–6 sessions or dropped, plus the separate registration |
| WP4 | Integrated analysis, figures, manuscript (plan §12.3 fixes the analysis output; manuscript scope and external review rounds are not yet planned) | after WP2; does not wait for WP3 if E4 is dropped | minutes | 4–8 sessions |
| E5 | Optional extension (other checkpoint, retraining, other task) | not planned | — | needs a new protocol |

Measured costs per puzzle (20 released hard puzzles, `experiments/g0/cost.json`): baseline generation 1.30 s; branch D regeneration from level 2 / 6 / 11: 1.13 / 0.69 / 0.19 s; cumulative states 0.02 s; decode only (branch C) 0.02 s; RSS ≈ 0.5–0.65 GB; storage 322 B of codes vs ≈ 1.1 MB of FP32 states per puzzle.

## Backlog

- WP0-A deferred minors: full-contract asserts in Review Focus tests; side effect inside `assert` in `generate.random_solution`; float/bool tokens accepted as digits; fetch-script docstring path; `load_released` provenance hash check and protocol-4 unpickler test.
- WP0-B deferred minors: cost per-step memory fields (lifetime peak, allocator-noise RSS deltas, no warm-up); batch-size effect checked on one puzzle and G0 batches differ from upstream's interleaved shards; prefix recomputation tested only at level 6; `assert`-based validation in `states.py` and no shape checks for `z_hat_override` / `prefix_tokens`; `import_upstream` inserts at `sys.path[0]`; `load_model` does not verify provenance hashes and refuses unsupported configs only at generation time; `.gitignore` duplicates `runs/`; AGENTS.md wording ("planned as" submodule, incomplete dependency list, plans entry).
- Before E4: compare per-level logits (not only argmax codes) in identity checks; consider pinning `torch.set_num_threads`.
- Before reusing `e2.py` for the confirmatory E2: collision-free per-run seeds (current `1000*level + 100*dose + 10*seed + policy` collides for dose ≥ 10 across levels or ≥ 10 seeds); 10,000 bootstrap draws and a pre-specified small-sample interval (§11.1, §11.2); state the whole-puzzle exclusion rule for partially eligible seeds (§7.2); a rerun guard on `scripts/wp1_pilot.py`; inspect a few level-1 runs whose damage is exactly one cell.
- Gate compares the project validator's solve rate with the official-metric 86.3%; identical on the released set (D31), note in the lock checklist.
- E2 pilot-2 deferred minors: see the e2-redesign final review (guards for zero-norm/empty-mask/no-empty-cell edge cases; vectorize level1_weights; a few test-precision items).

## Open items

- Repeat the related-work search before submission (`literature/`).
- Remaining effort (planning estimate, 2026-11-13): 8–13 sessions without WP3, 11–19 with WP3; about 26 h of background CPU for WP2. At the pace of WP0 to the lock (about 9–13 sessions in five days), WP2 takes about 2–4 days, the roadmap without WP3 about 1.5–3 weeks, and WP3 adds about 1–2 weeks including its registration.

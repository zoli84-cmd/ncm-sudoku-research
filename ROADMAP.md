# Roadmap

Single place for work-package status, backlog, and open items. Decisions live in `DECISIONS.md`; the protocol in the authoritative research plan. Effort figures are planning estimates, not plan commitments (plan §12.3: cost estimates follow the measured pilot).

## Work packages

| WP | Content (plan §12.3) | Status | Compute estimate (CPU, measured basis) | Effort estimate |
|---|---|---|---|---|
| WP0-A | Sudoku core: serialization, validator, solvers, labeler, generator, released-data loader | done (2026-11-08) | — | — |
| WP0-B | Safe loading, official-metric mirror, runner, cumulative states, `forward_with_intervention`, G0 reproduction, cost | done (2026-11-09); G0 passed: 86.3% vs 86.1% (D31) | G0 run ≈ 45 min | — |
| WP1 | Generator freeze + terminal distribution gate (D27); E1 tokenizer/generator split; E2 level sensitivity, four-branch compensation, dose calibration | done (2026-11-09): gate passed (D41); E1 on released and CAL; E2 pilot (D42, non-confirmatory) | measured: gate 20 min; E1 on CAL 5 min; E2 pilot (300 × levels 1/2/6/11 × 2 policies × doses × 3 seeds) 2.36 h | 1 session |
| Lock | Revise E2 design from the pilot (D42: non-degenerate damage measure, doses, sample size), sample-size simulation, §12.2 checklist, OSF embargoed registration with git tag hash | next | minutes (simulation); new E2 doses need a pilot re-run | 1–3 sessions |
| WP2 | E3 labels, probes, control matrix, depth, equivariance | after lock | state extraction 0.02 s/puzzle; probes minutes–hours | 3–5 sessions |
| WP3 | E4a / E4b targeted patching (conditional on the E4 gate) | conditional | depends on E4-TEST size | 3–6 sessions or dropped |
| WP4 | Integrated analysis, figures, manuscript | after WP2 (and WP3) | minutes | 4–8 sessions |
| E5 | Optional extension (other checkpoint, retraining, other task) | not planned | — | needs a new protocol |

Measured costs per puzzle (20 released hard puzzles, `experiments/g0/cost.json`): baseline generation 1.30 s; branch D regeneration from level 2 / 6 / 11: 1.13 / 0.69 / 0.19 s; cumulative states 0.02 s; decode only (branch C) 0.02 s; RSS ≈ 0.5–0.65 GB; storage 322 B of codes vs ≈ 1.1 MB of FP32 states per puzzle.

## Backlog

- D26: E2 re-quantization diagnostic for geometric residual cancellation (after the pilot).
- WP0-A deferred minors: full-contract asserts in Review Focus tests; side effect inside `assert` in `generate.random_solution`; float/bool tokens accepted as digits; fetch-script docstring path; `load_released` provenance hash check and protocol-4 unpickler test.
- WP0-B deferred minors: cost per-step memory fields (lifetime peak, allocator-noise RSS deltas, no warm-up); batch-size effect checked on one puzzle and G0 batches differ from upstream's interleaved shards; prefix recomputation tested only at level 6; `assert`-based validation in `states.py` and no shape checks for `z_hat_override` / `prefix_tokens`; `import_upstream` inserts at `sys.path[0]`; `load_model` does not verify provenance hashes and refuses unsupported configs only at generation time; `.gitignore` duplicates `runs/`; AGENTS.md wording ("planned as" submodule, incomplete dependency list, plans entry).
- Before E4: compare per-level logits (not only argmax codes) in identity checks; consider pinning `torch.set_num_threads`.
- Subset screening: the cycle-type signature collides within the released set (75 pairs), so it cannot flag symmetry equivalence; add a canonical-form check before PROBE/SELECT/TEST subsets are generated (D41).
- Before reusing `e2.py` for the confirmatory E2: collision-free per-run seeds (current `1000*level + 100*dose + 10*seed + policy` collides for dose ≥ 10 across levels or ≥ 10 seeds); 10,000 bootstrap draws and a pre-specified small-sample interval (§11.1, §11.2); state the whole-puzzle exclusion rule for partially eligible seeds (§7.2); a rerun guard on `scripts/wp1_pilot.py`; inspect a few level-1 runs whose damage is exactly one cell.
- Gate compares the project validator's solve rate with the official-metric 86.3%; identical on the released set (D31), note in the lock checklist.
- D16: unit–digit label definition and readout mapping aligned with Kniazev & Fijalkow (2026) before PROBE-VAL.

## Open items

- Repeat the related-work search before submission (`literature/`).
- Copilot review runs: reviewers fail when they try to read files outside the repository (`C:\Users\ako2bp\AGENTS.md`); add an explicit "repository files only" line to future briefs.

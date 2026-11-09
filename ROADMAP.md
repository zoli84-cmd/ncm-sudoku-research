# Roadmap

Single place for work-package status, backlog, and open items. Decisions live in `DECISIONS.md`; the protocol in the authoritative research plan. Effort figures are planning estimates, not plan commitments (plan §12.3: cost estimates follow the measured pilot).

## Work packages

| WP | Content (plan §12.3) | Status | Compute estimate (CPU, measured basis) | Effort estimate |
|---|---|---|---|---|
| WP0-A | Sudoku core: serialization, validator, solvers, labeler, generator, released-data loader | done (2026-11-08) | — | — |
| WP0-B | Safe loading, official-metric mirror, runner, cumulative states, `forward_with_intervention`, G0 reproduction, cost | done (2026-11-09); G0 passed: 86.3% vs 86.1% (D31) | G0 run ≈ 45 min | — |
| WP1 | Generator freeze + terminal distribution gate (D27); E1 tokenizer/generator split; E2 level sensitivity, four-branch compensation, dose calibration | next | gate ≈ 0.5 h; E2 pilot (300 puzzles × levels 2/6/11 × 3 repetitions) ≈ 0.5–1 h; full dose grid a few hours | 3–5 sessions |
| Lock | Sample-size simulation, §12.2 checklist, OSF embargoed registration with git tag hash | after WP1 pilot | minutes | 1–2 sessions |
| WP2 | E3 labels, probes, control matrix, depth, equivariance | after lock | state extraction 0.02 s/puzzle; probes minutes–hours | 3–5 sessions |
| WP3 | E4a / E4b targeted patching (conditional on the E4 gate) | conditional | depends on E4-TEST size | 3–6 sessions or dropped |
| WP4 | Integrated analysis, figures, manuscript | after WP2 (and WP3) | minutes | 4–8 sessions |
| E5 | Optional extension (other checkpoint, retraining, other task) | not planned | — | needs a new protocol |

Measured costs per puzzle (20 released hard puzzles, `experiments/g0/cost.json`): baseline generation 1.30 s; branch D regeneration from level 2 / 6 / 11: 1.13 / 0.69 / 0.19 s; cumulative states 0.02 s; decode only (branch C) 0.02 s; RSS ≈ 0.5–0.65 GB; storage 322 B of codes vs ≈ 1.1 MB of FP32 states per puzzle.

## Backlog

- D26: E2 re-quantization diagnostic for geometric residual cancellation (after the pilot).
- WP0-A deferred minors: full-contract asserts in Review Focus tests; side effect inside `assert` in `generate.random_solution`; float/bool tokens accepted as digits; fetch-script docstring path; `load_released` provenance hash check and protocol-4 unpickler test.
- D16: unit–digit label definition and readout mapping aligned with Kniazev & Fijalkow (2026) before PROBE-VAL.

## Open items

- Repeat the related-work search before submission (`literature/`).
- Copilot review runs: reviewers fail when they try to read files outside the repository (`C:\Users\ako2bp\AGENTS.md`); add an explicit "repository files only" line to future briefs.

# E3 probe-suite report

**Non-confirmatory planning output (plan v3.6 §12.1).** PROBE-TRAIN/PROBE-VAL only; these numbers plan the confirmatory E3 study and are not evidence for H1.

- PROBE-TRAIN 2000 puzzles, PROBE-VAL 500 puzzles
- Val Brier: per-puzzle mean over empty cells, then over puzzles (§8.3), at the selected configuration, averaged over seeds 0-2, always scored on unpermuted PROBE-VAL (the permuted control is tuned on its own permuted PROBE-VAL; that tuning value is `tune_brier_mean` in probes.json, not shown here); best epoch / steps / hit cap are the training budget of the selected configuration's seeds (D63; hit cap is over the whole grid)

## Representation levels (generated branch)

| Probe | Val Brier | Config | best epoch | steps | any hit cap | n_params |
|---|---|---|---|---|---|---|
| L01_linear | 0.2319 | [0.1, 0.001] | 17–19 | 2000 | False | 3042 |
| L02_linear | 0.2319 | [0.1, 0.001] | 17–19 | 2000 | False | 3042 |
| L02_mlp | 0.2318 | [0.1, 0.001] | 4–11 | 2000 | False | 22217 |
| L02_permuted_linear | 0.2327 | [0.1, 0.001] | 17–19 | 2000 | False | 3042 |
| L03_linear | 0.2318 | [0.1, 0.001] | 7–7 | 2000 | False | 3042 |
| L04_linear | 0.2317 | [0.1, 0.001] | 7–7 | 2000 | False | 3042 |
| L05_linear | 0.2317 | [0.1, 0.001] | 7–7 | 2000 | False | 3042 |
| L06_linear | 0.2308 | [0.1, 0.001] | 7–7 | 2000 | False | 3042 |
| L06_mlp | 0.2307 | [0.1, 0.003] | 6–15 | 2000 | False | 22217 |
| L07_linear | 0.2285 | [0.1, 0.001] | 7–7 | 2000 | False | 3042 |
| L08_linear | 0.2250 | [0.1, 0.001] | 7–17 | 2000 | False | 3042 |
| L09_linear | 0.2195 | [0.1, 0.001] | 7–13 | 2000 | False | 3042 |
| L10_linear | 0.2141 | [0.1, 0.001] | 27–37 | 2000 | False | 3042 |
| L11_linear | 0.2092 | [0.1, 0.001] | 31–61 | 2000 | False | 3042 |
| L12_linear | 0.1858 | [0, 0.003] | 68–71 | 2000 | True | 3042 |
| L12_mlp | 0.1828 | [0.1, 0.001] | 44–52 | 2000 | False | 22217 |
| L12_permuted_linear | 0.2326 | [0.1, 0.001] | 21–50 | 2000 | False | 3042 |

## Controls (level 6)

| Probe | Val Brier | Config | best epoch | steps | any hit cap | n_params |
|---|---|---|---|---|---|---|
| raw_linear | 0.0105 | [0, 0.003] | 79–79 | 2000 | True | 2628 |
| raw_mlp | 0.0000 | [0, 0.003] | 79–79 | 2000 | True | 19273 |
| peer_counts_linear | 0.0141 | [0, 0.003] | 79–79 | 2000 | True | 819 |
| rule | 0.0000 | – | – | – | – | – |
| surface_linear | 0.2252 | [0, 0.003] | 79–79 | 2000 | True | 828 |
| permuted_linear | 0.2326 | [0.1, 0.001] | 4–7 | 2000 | False | 3042 |
| random_linear | 0.2330 | [0.01, 0.001] | 26–28 | 2000 | False | 3042 |
| label_permuted_linear | 0.2326 | [0.1, 0.001] | 3–5 | 2000 | False | 3042 |
| teacher_L02_linear | 0.2320 | [0.1, 0.001] | 27–37 | 2000 | False | 3042 |
| teacher_L06_linear | 0.2308 | [0.1, 0.001] | 7–7 | 2000 | False | 3042 |
| teacher_L12_linear | 0.1859 | [0, 0.003] | 68–77 | 2000 | True | 3042 |
| marginal | 0.2326 | – | – | – | – | – |

## Unit-digit target (level 6, linear; D62)

Brier is the mean of the per-seed Briers (same scale as above); exact match and ROC-AUC use the seed-averaged predictions (their Brier is `brier_ensemble` in probes.json).

| Input | Exact match | ROC-AUC | Brier | Config | best epoch | steps | any hit cap | n_params |
|---|---|---|---|---|---|---|---|---|
| generated | 0.0076 | 0.5024 | 0.2333 | [0.1, 0.001] | 8–12 | 2002 | False | 2556 |
| raw | 0.4630 | 1.0000 | 0.1362 | [0, 0.003] | 142–142 | 2002 | True | 342 |

## Training-size curve (level 6, linear)

The D63 minimum step count gives small-n fits more epochs and hence more early-stopping checkpoints on PROBE-VAL (e.g. 1,000 epochs at 125 puzzles vs. 80 at 2,000), a small optimistic selection bias at the small-n end of the curve.

| Probe | Val Brier | Config | best epoch | steps | any hit cap | n_params |
|---|---|---|---|---|---|---|
| first 125 puzzles | 0.2314 | [0.1, 0.001] | 35–40 | 2000 | False | 3042 |
| first 250 puzzles | 0.2312 | [0.1, 0.001] | 24–29 | 2000 | False | 3042 |
| first 500 puzzles | 0.2310 | [0.1, 0.001] | 14–19 | 2002 | False | 3042 |
| first 1000 puzzles | 0.2309 | [0.1, 0.001] | 9–11 | 2002 | False | 3042 |
| first 2000 puzzles (reused) | 0.2308 | [0.1, 0.001] | 7–7 | 2000 | False | 3042 |

## Depth breakdown (level 6 linear vs. raw-input linear; Brier per class)

| Depth | Generated | Raw input | cells | puzzles |
|---|---|---|---|---|
| 1 | 0.2183 | 0.0103 | 4952 | 500 |
| 2 | 0.2222 | 0.0103 | 4030 | 498 |
| 3 | 0.2299 | 0.0105 | 3404 | 483 |
| >=4 | 0.2391 | 0.0107 | 10540 | 467 |
| stuck | 0.2381 | 0.0106 | 2574 | 78 |
| censored | – | – | 0 | 0 |

## H1 planning quantity (θ1 preview)

- Level 2, linear: mean per-puzzle B_permuted − B_generated 0.00071, relative improvement (mean diff / mean B_permuted) 0.0031, over 500 PROBE-VAL puzzles (experiments/e3prep/h1_diffs_L02.json)
- Level 6, linear: mean per-puzzle B_permuted − B_generated 0.00183, relative improvement (mean diff / mean B_permuted) 0.0079, over 500 PROBE-VAL puzzles (experiments/e3prep/h1_diffs.json)
- Level 12, linear: mean per-puzzle B_permuted − B_generated 0.04677, relative improvement (mean diff / mean B_permuted) 0.2011, over 500 PROBE-VAL puzzles (experiments/e3prep/h1_diffs_L12.json)
- Saved level-6 seed models: L06_linear_seed0.pt, L06_linear_seed1.pt, L06_linear_seed2.pt at config [0.1, 0.001]; retrain matches the grid fit: True

## Stage run times (s)

- L01_linear: 533.6
- L02_linear: 1809.4
- L02_mlp: 922.6
- L02_permuted_linear: 540.8
- L03_linear: 573.6
- L04_linear: 427.7
- L05_linear: 385.6
- L06_linear: 825.8
- L06_mlp: 756.4
- controls: 5614.4
- unit_digit: 659.8
- training_size: 2320.8
- L07_linear: 387.8
- L08_linear: 295.4
- L09_linear: 379.4
- L10_linear: 419.2
- L11_linear: 356.2
- L12_linear: 435.5
- L12_mlp: 690.0
- L12_permuted_linear: 432.3

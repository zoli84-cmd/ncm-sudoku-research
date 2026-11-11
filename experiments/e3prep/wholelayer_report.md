# E3 whole-layer diagnostic report (D65, D66)

**Non-confirmatory planning output (plan v3.6 §12.1).** PROBE-TRAIN/PROBE-VAL only; this diagnostic informs the form of H1 (D65) and is not evidence for H1.

- PROBE-TRAIN 2000 puzzles, PROBE-VAL 500 puzzles
- Whole-layer input per cell (D66): whitened PCA-256 scores of the states of the cell and its 20 peers (PCA fitted on PROBE-TRAIN empty-cell rows only) || the cell's own state || position one-hot; raw-input control: `raw_features` (own || 20 peer one-hots), whitened-PCA projected and unprojected, || position
- Val Brier: per-puzzle mean over empty cells, then over puzzles (§8.3), at the selected configuration (D55 grid, D63 budget), averaged over seeds 0-2, always scored on unpermuted PROBE-VAL (the permuted control's tuning value is `tune_brier_mean` in wholelayer.json)

| Probe | Val Brier | Config | best epoch | steps | any hit cap | n_params |
|---|---|---|---|---|---|---|
| L06 whole-layer generated | 0.2304 | [0.1, 0.001] | 52–79 | 2000 | True | 5346 |
| L06 whole-layer permuted control | 0.2335 | [0.1, 0.001] | 1–2 | 2000 | False | 5346 |
| L12 whole-layer generated | 0.1833 | [0.1, 0.001] | 57–79 | 2000 | True | 5346 |
| L12 whole-layer permuted control | 0.2336 | [0.1, 0.001] | 2–5 | 2000 | False | 5346 |
| teacher_L12 whole-layer teacher | 0.1836 | [0.1, 0.001] | 57–79 | 2000 | True | 5346 |
| raw input, projected | 0.0014 | [0, 0.003] | 79–79 | 2000 | True | 2628 |
| raw input, unprojected | 0.0105 | [0, 0.003] | 79–79 | 2000 | True | 2628 |

## Per-cell reference rows (scored val Brier, read from experiments/e3prep/probes.json)

- per-cell L06_linear: 0.2308
- per-cell L12_linear: 0.1858
- per-cell L06_permuted_linear: 0.2326
- per-cell L12_permuted_linear: 0.2326
- per-cell surface_linear: 0.2252
- per-cell raw_linear: 0.0105
- whole-layer minus per-cell, L06 linear: -0.00037
- whole-layer minus per-cell, L12 linear: -0.00252

## PCA explained-variance share (top-k; train in-sample, val with the train mean)

- L06: train 0.9035, val 0.9035; k = 256 of 5376 dimensions, 102000 train rows
- L12: train 0.9970, val 0.9970; k = 256 of 5376 dimensions, 102000 train rows
- teacher_L12: train 0.9970, val 0.9970; k = 256 of 5376 dimensions, 102000 train rows
- raw_projected: train 1.0000, val 1.0000; k = 210 of 210 dimensions, 102000 train rows

## H1 planning quantity (θ1 preview, whole-layer)

- Level 6, linear: mean per-puzzle B_permuted − B_generated 0.00311, relative improvement (mean diff / mean B_permuted) 0.0133, over 500 PROBE-VAL puzzles (experiments/e3prep/wholelayer_h1_diffs_L06.json)
- Level 12, linear: mean per-puzzle B_permuted − B_generated 0.05033, relative improvement (mean diff / mean B_permuted) 0.2154, over 500 PROBE-VAL puzzles (experiments/e3prep/wholelayer_h1_diffs_L12.json)

## Secondary contrast preview (level 12, D65)

- Mean per-puzzle B_teacher − B_generated 0.00031 over 500 PROBE-VAL puzzles (per-puzzle values in wholelayer.json)

## Stage run times (s)

- L06: 918.3
- L12: 939.4
- teacher_L12: 509.9
- raw_projected: 292.4
- raw_unprojected: 278.7

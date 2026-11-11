# E3 whole-layer diagnostic report (D65, D66)

**Non-confirmatory planning output (plan v3.6 §12.1).** PROBE-TRAIN/PROBE-VAL only; this diagnostic informs the form of H1 (D65) and is not evidence for H1.

- PROBE-TRAIN 2000 puzzles, PROBE-VAL 500 puzzles
- Whole-layer input per cell (D66): whitened PCA-256 scores of the states of the cell and its 20 peers (PCA fitted on PROBE-TRAIN empty-cell rows only) || the cell's own state || position one-hot; raw-input control: `raw_features` (own || 20 peer one-hots), whitened-PCA projected and unprojected, || position
- Val Brier: per-puzzle mean over empty cells, then over puzzles (§8.3), at the selected configuration (D55 grid, D63 budget), averaged over seeds 0-2, always scored on unpermuted PROBE-VAL (the permuted control's tuning value is `tune_brier_mean` in wholelayer.json)

| Probe | Val Brier | Config | best epoch | steps | any hit cap | n_params |
|---|---|---|---|---|---|---|
| L06 whole-layer generated | 0.2304 | [0.1, 0.001] | 185–231 | 6000 | False | 5346 |
| L06 whole-layer permuted control | 0.2335 | [0.1, 0.001] | 1–2 | 6000 | False | 5346 |

## Per-cell reference rows (scored val Brier, read from probes.json not found)

- per-cell L06_linear: n/a
- per-cell L12_linear: n/a
- per-cell L06_permuted_linear: n/a
- per-cell L12_permuted_linear: n/a
- per-cell surface_linear: n/a
- per-cell raw_linear: n/a
- whole-layer minus per-cell, L06 linear: n/a
- whole-layer minus per-cell, L12 linear: n/a

## PCA explained-variance share (top-k; train in-sample, val with the train mean)

- L06: train 0.9035, val 0.9035; k = 256 of 5376 dimensions, 102000 train rows

## H1 planning quantity (θ1 preview, whole-layer)

- Level 6, linear: mean per-puzzle B_permuted − B_generated 0.00315, relative improvement (mean diff / mean B_permuted) 0.0135, over 500 PROBE-VAL puzzles (experiments/e3prep/wholelayer_h1_diffs_L06.json)

## Stage run times (s)

- L06: 5084.7

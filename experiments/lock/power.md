# Lock power simulations (D70)

non-confirmatory planning output (plan v3.6 §12.1); not evidence for H1, H2 or H3.

## E2 levels 2 vs. 11 equivalence (TOST ±0.03, injection scenario)

n = 600, 2000 simulated samples per scenario, 1000 bootstrap resamples, seed 0. Pilot θ₂′: n = 300, mean 0.0011, zero share 0.987.

| True effect | False-equivalence rate | MC SE | Share on bound path | Rate, bound path | Rate, bootstrap path |
|---|---|---|---|---|---|
| +0.03 | 0.025 | 0.003 | 0.111 | 0.014 | 0.026 |
| -0.03 | 0.036 | 0.004 | 0.070 | 0.007 | 0.039 |

## H1 family-level TOST (±0.01, 96.67% interval)

n = 600, 500 simulated samples per scenario, 2000 bootstrap resamples, seed 0. D67 whole-layer level-6 diffs: n = 500, observed mean 0.0031.

| Quantity | Share |
|---|---|
| Power, true mean 0 | 1.000 |
| Power, observed mean | 1.000 |
| False equivalence, true mean +0.01 | 0.016 |
| False equivalence, true mean -0.01 | 0.014 |
| 98.33% interval excludes 0, observed mean | 1.000 |
| Both (inside ±0.01 and 98.33% lower limit > 0), observed mean | 1.000 |

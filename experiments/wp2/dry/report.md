# WP2 evaluation (dry role)

**DRY RUN (CAL / PROBE-VAL in the TEST role); not TEST**

- Date: 2026-11-14
- Tag commit: 1047668b8954535145a247ed4eb5704d1387bfda
- Frozen now: True

| Runner | Status | Valid | Commit | Seconds | Reasons |
|---|---|---|---|---|---|
| e3_extract | valid | True | 1047668b8954535145a247ed4eb5704d1387bfda | 1226.43 | - |
| e3 | valid | True | 1047668b8954535145a247ed4eb5704d1387bfda | 18817.9 | - |
| equiv | valid | True | 1047668b8954535145a247ed4eb5704d1387bfda | 1660.19 | - |
| e2 | valid | True | 1047668b8954535145a247ed4eb5704d1387bfda | 2558.91 | - |
| e1 | valid | True | 1047668b8954535145a247ed4eb5704d1387bfda | 54.4757 | - |

## Primary contrasts (§11.1)

| Contrast | Estimate | 98.33% interval | 95% interval | Method | n | n nonzero | H1 TOST interval (level, method) | TOST verdict |
|---|---|---|---|---|---|---|---|---|
| H1 | 0.00311054 | [0.00265235, 0.00354334] | [0.00273812, 0.00346908] | bootstrap | 500 | 500 | [0.0027106, 0.00350015], 96.67% interval (bootstrap) | equivalent |
| H2 | -0.0387779 | [-0.0842399, 0.0123297] | [-0.0762188, 0.00264407] | bootstrap | 50 | 20 | - | - |
| H3 | 0.0345511 | [-0.202597, 0.202597] | [-0.173791, 0.173791] | bound | 50 | 4 | - | - |

- H1: the 95% interval is the individual-level 95% interval; the 98.33% family interval is the inferential one.
- H2: the 95% interval is the individual-level 95% interval; the 98.33% family interval is the inferential one.
- H3: the 95% interval is the individual-level (0.95) rare-event bound; the 98.33% family interval is the inferential one.

## §13 readings

- **H1** — H1: 98.33% lower limit > 0 and the 96.67% interval inside ±0.01
  - Justified claim: The candidate mask is readable from the level-6 state above the permuted null control, but by less than the practical threshold, with the examined probe family and budget
  - Does not follow: The representation computes candidates, or carries no candidate information; another readout could not do better
- **H1** — Generated probe beats the null control
  - Justified claim: The label is readable with the examined readout
  - Does not follow: The model contains more information than the input, or the generator uses the read-out feature
- **H2** — Non-significant result
  - Justified claim: The given design provides insufficient evidence for the designated effect
  - Does not follow: The effect or the logical representation is certainly absent
- **H3** — Non-significant result
  - Justified claim: The given design provides insufficient evidence for the designated effect
  - Does not follow: The effect or the logical representation is certainly absent
- **theta2_prime** — Non-significant result
  - Justified claim: The given design provides insufficient evidence for the designated effect
  - Does not follow: The effect or the logical representation is certainly absent
- **level12** — Level-12 readout clearly above the null control and teacher − generated inside ±0.01
  - Justified claim: The level-12 readability is consistent with solution content
  - Does not follow: The generated representation computes candidates or encodes inference steps
- **equivariance**: descriptive (no pre-specified criterion). Inputs: `{"categories": {"all": {"mean_deviation": 0.07891430144720882, "share_within": 0.0, "brier_transformed": 0.18283402419892233, "brier_original": 0.18278442805321063}, "digit": {"mean_deviation": 0.06647426929096939, "share_within": 0.0, "brier_transformed": 0.18263223493302788, "brier_original": 0.18278442805321063}, "geometric": {"mean_deviation": 0.0771610120099211, "share_within": 0.0, "brier_transformed": 0.1826737975407668, "brier_original": 0.18278442805321063}}, "n": 200, "acceptable": 0.0116, "acceptable_source": "fixed", "seed_noise_p95": 0.011644554557515473, "equivariance_reading": "descriptive (no pre-specified criterion)"}`

## Secondary contrasts

| Contrast | Estimate | 95% interval | Method | n | TOST interval (level, method) | TOST verdict |
|---|---|---|---|---|---|---|
| theta_T | 0.000312302 | [6.53892e-05, 0.000556711] | bootstrap | 500 | [0.000108054, 0.000514767], 90% interval (bootstrap) | equivalent |
| theta1_wl.L02 | 0.000847396 | [0.000590033, 0.00110692] | bootstrap | 500 | - | - |
| theta1_wl.L12 | 0.0503316 | [0.0498803, 0.0507801] | bootstrap | 500 | - | - |
| theta1_pc.L02 | 0.000712305 | [0.000579261, 0.000842636] | bootstrap | 500 | - | - |
| theta1_pc.L06 | 0.00182933 | [0.00163308, 0.00203086] | bootstrap | 500 | - | - |
| theta1_pc.L12 | 0.0467744 | [0.0464417, 0.0471048] | bootstrap | 500 | - | - |
| raw_minus_generated.projected | -0.228963 | [-0.22946, -0.228467] | bootstrap | 500 | - | - |
| raw_minus_generated.unprojected | -0.219895 | [-0.22039, -0.219399] | bootstrap | 500 | - | - |
| theta2_prime | 0.0133333 | [-0.0913981, 0.0913981] | bound | 50 | [-0.0913981, 0.0913981], one-sided 95% rare-event bound | not equivalent |
| uniform.theta2 | -0.0973333 | [-0.154667, -0.044] | bootstrap | 50 | - | - |
| uniform.theta_comp | 0.0266667 | [-0.246935, 0.246935] | bound | 50 | - | - |
| uniform.theta2_prime | 0.00666667 | [-0.0913981, 0.0913981] | bound | 50 | - | - |
| correct_baseline.theta2 | -0.059616 | [-0.566526, 0.566526] | bound | 44 | - | - |
| correct_baseline.theta_comp | 0.0237124 | [-0.166899, 0.166899] | bound | 44 | - | - |

## AUC over the frozen range (§7.3, §12.2)

- 6-11: auc_a = n/a, auc_b = n/a, range = [3.29177e-05, 7.93023e-05], TEST coverage = {'a': [1.4316817462827203e-05, 0.00012877556940111385], 'b': [7.664054489850968e-05, 0.0022429977886592196]}, reason = TEST nodes do not cover the frozen range
- 2-11: auc_a = n/a, auc_b = n/a, range = n/a, TEST coverage = {'a': [1.0481741169693727e-05, 3.448970684075903e-05], 'b': [7.664054489850968e-05, 0.0022429977886592196]}, reason = no frozen range (§12.2)

## E1 (§6)

- n = 50, official exact share = 0.88, generated solve = 0.88, teacher exact share = 1
- Hamming: token mean = 0.0130337, cell mean = 0.014321, cell empty mean = 0.0223529, n = 50

## E2 descriptive tables (no statistics)

- sham_mismatch = {"level1_B1": 0, "levels_B": {"2": 0, "6": 0, "11": 0}}, level1_noop_mismatch = 0, code_mismatch = {"level1_B1": 0, "levels_B": {"2": 0, "6": 0, "11": 0}, "level1_noop_D": 0}

| Level | Policy | Dose | Records | Excluded | Solve A | Solve C | Solve D |
|---|---|---|---|---|---|---|---|
| 2 | frequency | 1 | 150 | 0 | 0.88 | 0.88 | 0.893333 |
| 2 | frequency | 2 | 150 | 0 | 0.88 | 0.88 | 0.88 |
| 2 | uniform | 1 | 150 | 0 | 0.88 | 0.88 | 0.886667 |
| 2 | uniform | 2 | 150 | 0 | 0.88 | 0.873333 | 0.88 |
| 6 | frequency | 1 | 150 | 0 | 0.88 | 0.88 | 0.9 |
| 6 | frequency | 2 | 150 | 0 | 0.88 | 0.88 | 0.893333 |
| 6 | frequency | 4 | 150 | 0 | 0.88 | 0.88 | 0.9 |
| 6 | frequency | 8 | 150 | 0 | 0.88 | 0.88 | 0.886667 |
| 6 | frequency | 13 | 150 | 0 | 0.88 | 0.88 | 0.906667 |
| 6 | uniform | 1 | 150 | 0 | 0.88 | 0.88 | 0.893333 |
| 6 | uniform | 2 | 150 | 0 | 0.88 | 0.88 | 0.906667 |
| 6 | uniform | 4 | 150 | 0 | 0.88 | 0.88 | 0.906667 |
| 6 | uniform | 8 | 150 | 0 | 0.88 | 0.88 | 0.913333 |
| 6 | uniform | 13 | 150 | 0 | 0.88 | 0.88 | 0.9 |
| 11 | frequency | 1 | 150 | 0 | 0.88 | 0.88 | 0.88 |
| 11 | frequency | 4 | 150 | 0 | 0.88 | 0.873333 | 0.886667 |
| 11 | frequency | 11 | 150 | 0 | 0.88 | 0.88 | 0.88 |
| 11 | frequency | 21 | 150 | 0 | 0.88 | 0.86 | 0.886667 |
| 11 | frequency | 41 | 150 | 0 | 0.88 | 0.84 | 0.873333 |
| 11 | frequency | 67 | 150 | 0 | 0.88 | 0.806667 | 0.846667 |
| 11 | uniform | 1 | 150 | 0 | 0.88 | 0.88 | 0.88 |
| 11 | uniform | 4 | 150 | 0 | 0.88 | 0.873333 | 0.88 |
| 11 | uniform | 11 | 150 | 0 | 0.88 | 0.873333 | 0.886667 |
| 11 | uniform | 21 | 150 | 0 | 0.88 | 0.853333 | 0.873333 |
| 11 | uniform | 41 | 150 | 0 | 0.88 | 0.866667 | 0.866667 |
| 11 | uniform | 67 | 150 | 0 | 0.88 | 0.82 | 0.873333 |

### E2 propagation diagnostics (D78)

- Weighting: level-1 rows weighted by the policy weights over non-no-op rows; other configurations averaged over eligible seeds within puzzle, then over puzzles. Full maps are in results.json.

| Configuration | Mean later-level D code changes |
|---|---|
| level1-frequency | L2: 0.008581, L3: 0.1496, L4: 0.04962, L5: 0, L6: 0.07581, L7: 0.1821, L8: 0.4572, L9: 0.8365, L10: 1.759, L11: 2.825, L12: 0.8494 |
| level1-uniform | L2: 0.005333, L3: 0.1413, L4: 0.05067, L5: 0, L6: 0.07333, L7: 0.176, L8: 0.4253, L9: 0.76, L10: 1.604, L11: 2.583, L12: 0.804 |
| L02-frequency-d1 | L3: 0.06667, L4: 0.07333, L5: 0, L6: 0.08, L7: 0.1867, L8: 0.28, L9: 0.6133, L10: 1.093, L11: 1.253, L12: 0.6667 |
| L02-frequency-d2 | L3: 0.12, L4: 0.08, L5: 0, L6: 0.02, L7: 0.1, L8: 0.18, L9: 0.3, L10: 0.82, L11: 1, L12: 0.34 |
| L02-uniform-d1 | L3: 0.02667, L4: 0.02, L5: 0, L6: 0.02, L7: 0.04, L8: 0.1267, L9: 0.2533, L10: 0.5067, L11: 0.6333, L12: 0.2467 |
| L02-uniform-d2 | L3: 0.06667, L4: 0.02667, L5: 0, L6: 0.05333, L7: 0.14, L8: 0.2467, L9: 0.4, L10: 0.8467, L11: 1.073, L12: 0.4867 |
| L06-frequency-d1 | L7: 0.2, L8: 0.3067, L9: 0.4333, L10: 0.9333, L11: 1.253, L12: 0.52 |
| L06-frequency-d2 | L7: 0.2267, L8: 0.4733, L9: 0.7667, L10: 1.407, L11: 1.933, L12: 0.4733 |
| L06-frequency-d4 | L7: 0.4333, L8: 0.9267, L9: 1.473, L10: 2.767, L11: 3.633, L12: 0.9933 |
| L06-frequency-d8 | L7: 0.8933, L8: 1.6, L9: 2.627, L10: 5.067, L11: 6.62, L12: 2.207 |
| L06-frequency-d13 | L7: 1.32, L8: 2.227, L9: 3.507, L10: 6.707, L11: 8.7, L12: 2.567 |
| L06-uniform-d1 | L7: 0.1267, L8: 0.32, L9: 0.5333, L10: 1.127, L11: 1.4, L12: 0.5133 |
| L06-uniform-d2 | L7: 0.2667, L8: 0.4133, L9: 0.76, L10: 1.513, L11: 1.807, L12: 0.5333 |
| L06-uniform-d4 | L7: 0.5467, L8: 0.9267, L9: 1.453, L10: 2.94, L11: 3.827, L12: 1.127 |
| L06-uniform-d8 | L7: 0.8467, L8: 1.453, L9: 2.287, L10: 4.447, L11: 5.767, L12: 1.607 |
| L06-uniform-d13 | L7: 1.32, L8: 2.313, L9: 3.64, L10: 6.713, L11: 8.56, L12: 2.673 |
| L11-frequency-d1 | L12: 0.08667 |
| L11-frequency-d4 | L12: 0.2467 |
| L11-frequency-d11 | L12: 0.4867 |
| L11-frequency-d21 | L12: 0.9 |
| L11-frequency-d41 | L12: 1.5 |
| L11-frequency-d67 | L12: 2.3 |
| L11-uniform-d1 | L12: 0.05333 |
| L11-uniform-d4 | L12: 0.2133 |
| L11-uniform-d11 | L12: 0.4867 |
| L11-uniform-d21 | L12: 0.9067 |
| L11-uniform-d41 | L12: 1.473 |
| L11-uniform-d67 | L12: 2.3 |

| Primary configuration | state_dist_C per level | state_dist_D per level |
|---|---|---|
| level1-frequency | [0.9496, 0.8955, 0.8761, 0.8569, 0.8792, 0.8027, 0.6971, 0.5416, 0.4006, 0.3277, 0.2797, 0.1576] | [0.9496, 0.8954, 0.8653, 0.8466, 0.8686, 0.7938, 0.6921, 0.5459, 0.4165, 0.3519, 0.3099, 0.1797] |
| level1-uniform | [1.206, 1.133, 1.112, 1.088, 1.116, 1.019, 0.8852, 0.6871, 0.5085, 0.4159, 0.3549, 0.1999] | [1.206, 1.133, 1.104, 1.08, 1.108, 1.012, 0.8815, 0.6908, 0.5214, 0.4353, 0.3794, 0.2179] |
| L11-frequency-d1 | [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.07722, 0.0435] | [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.07722, 0.04531] |

## E3 main table (§8.2, §12.2)

Brier = seed-mean per-puzzle Brier on the score set; relative difference = (Brier - reference) / reference, only within one construction.

| Row | Group | Construction | Brier | Reference | Relative difference | Config | n_params |
|---|---|---|---|---|---|---|---|
| wl_L06.generated | whole_layer | whole_layer | 0.230403 | - | n/a | [0.1, 0.001] | 5346 |
| wl_L06.permuted | whole_layer | whole_layer | 0.233514 | wl_L06.generated | 0.0135004 | [0.1, 0.001] | 5346 |
| wl_L06_controls.random | whole_layer | whole_layer | 0.233699 | wl_L06.generated | 0.0143028 | [0.001, 0.001] | 5346 |
| wl_L06_controls.label_permuted | whole_layer | whole_layer | 0.233167 | wl_L06.generated | 0.0119955 | [0.1, 0.001] | 5346 |
| wl_teacher_L06.teacher | whole_layer | whole_layer | 0.230456 | wl_L06.generated | 0.000228364 | [0.1, 0.001] | 5346 |
| wl_teacher_L12.teacher | whole_layer | whole_layer | 0.183625 | wl_L12.generated | 0.00170366 | [0.1, 0.001] | 5346 |
| raw_projected.linear | whole_layer | input | 0.00144032 | wl_L06.generated | -0.993749 | [0, 0.003] | 2628 |
| raw_unprojected.linear | whole_layer | input | 0.0105079 | wl_L06.generated | -0.954394 | [0, 0.003] | 2628 |
| pc_L06.linear | per_cell | per_cell | 0.23077 | - | n/a | [0.1, 0.001] | 3042 |
| pc_L06.mlp | per_cell | per_cell | 0.230655 | pc_L06.linear | -0.000498519 | [0.1, 0.003] | 22217 |
| controls.raw_linear | per_cell | input | 0.0105079 | pc_L06.linear | -0.954466 | [0, 0.003] | 2628 |
| controls.raw_mlp | per_cell | input | 3.43113e-08 | pc_L06.mlp | -1 | [0, 0.003] | 19273 |
| controls.peer_counts_linear | per_cell | input | 0.0140825 | pc_L06.linear | -0.938976 | [0, 0.003] | 819 |
| controls.surface_linear | per_cell | input | 0.225203 | pc_L06.linear | -0.0241228 | [0, 0.003] | 828 |
| controls.permuted_linear | per_cell | per_cell | 0.232599 | pc_L06.linear | 0.0079271 | [0.1, 0.001] | 3042 |
| controls.random_linear | per_cell | per_cell | 0.233024 | pc_L06.linear | 0.0097688 | [0.01, 0.001] | 3042 |
| controls.label_permuted_linear | per_cell | per_cell | 0.232575 | pc_L06.linear | 0.00782448 | [0.1, 0.001] | 3042 |
| controls.teacher_L02_linear | per_cell | per_cell | 0.231987 | pc_L02.linear | 0.000164232 | [0.1, 0.001] | 3042 |
| controls.teacher_L06_linear | per_cell | per_cell | 0.230787 | pc_L06.linear | 7.73487e-05 | [0.1, 0.001] | 3042 |
| controls.teacher_L12_linear | per_cell | per_cell | 0.18592 | pc_L12.linear | 0.000490492 | [0, 0.003] | 3042 |
| controls.rule | label_free | input | 0 | - | n/a | n/a | n/a |
| controls.marginal | label_free | input | 0.232555 | - | n/a | n/a | n/a |

| Level | WL generated | WL permuted | PC linear | PC MLP | PC permuted |
|---|---|---|---|---|---|
| L02 | 0.23247 | 0.233318 | 0.231949 | 0.231806 | 0.232661 |
| L06 | 0.230403 | 0.233514 | 0.23077 | 0.230655 | 0.232599 |
| L12 | 0.183313 | 0.233645 | 0.185829 | 0.182838 | 0.232603 |

| Unit-digit fit | Brier | Exact match | ROC-AUC | Brier (ensemble) |
|---|---|---|---|---|
| generated | 0.233297 | 0.00762963 | 0.502361 | 0.233273 |
| raw | 0.136158 | 0.463037 | 1 | 0.13614 |

Training size: whole_layer is the primary probe's curve and the basis for any data-requirement statement; per_cell is secondary (spec ambiguity 3).

| Curve | Fit | n puzzles | Brier | Reused from |
|---|---|---|---|---|
| whole_layer | n125 | 125 | 0.236563 | - |
| whole_layer | n250 | 250 | 0.234645 | - |
| whole_layer | n500 | 500 | 0.232785 | - |
| whole_layer | n1000 | 1000 | 0.231525 | - |
| whole_layer | n2000 | 2000 | 0.230403 | wl_L06.generated |
| per_cell | n125 | 125 | 0.231449 | - |
| per_cell | n250 | 250 | 0.231214 | - |
| per_cell | n500 | 500 | 0.230981 | - |
| per_cell | n1000 | 1000 | 0.230915 | - |
| per_cell | n2000 | 2000 | 0.23077 | pc_L06.linear |

Depth breakdown (descriptive; label rates and sample sizes differ by depth, §5.2, §8.3):

| Depth | n cells | n puzzles | Positive rate | wl_L06.generated | pc_L06.linear | raw_unprojected.linear | raw_projected.linear |
|---|---|---|---|---|---|---|---|
| 1 | 4952 | 500 | 0.317313 | 0.217733 | 0.218288 | 0.0102569 | 0.00137038 |
| 2 | 4030 | 498 | 0.333526 | 0.22149 | 0.22215 | 0.0102804 | 0.00142229 |
| 3 | 3404 | 483 | 0.36369 | 0.229553 | 0.229921 | 0.0105165 | 0.0014466 |
| >=4 | 10540 | 467 | 0.398261 | 0.239328 | 0.239107 | 0.0107078 | 0.00147762 |
| stuck | 2574 | 78 | 0.393292 | 0.237466 | 0.238131 | 0.0106176 | 0.00148348 |
| censored | 0 | 0 | n/a | n/a | n/a | n/a | n/a |

| θ₁ pair | Per-seed θ₁ means (no intervals, spec ambiguity 18) |
|---|---|
| H1 | [0.00308767, 0.00317862, 0.00306533] |
| theta1_wl.L02 | [0.000852118, 0.000828524, 0.000861547] |
| theta1_wl.L12 | [0.0508206, 0.050302, 0.0498722] |
| theta1_pc.L02 | [0.000712846, 0.000711043, 0.000713026] |
| theta1_pc.L06 | [0.00182779, 0.00182375, 0.00183646] |
| theta1_pc.L12 | [0.0469104, 0.0471792, 0.0462336] |

Selected configurations that differ from the pre-lock D64/D67 selection: none.

## Exploratory level-12 equivariance (§8.4)

Reading: descriptive (no pre-specified criterion); tolerance 0.0116 (fixed), TEST seed-noise P95 = 0.0116446.

| Category | Mean deviation | Share within | Brier transformed | Brier original |
|---|---|---|---|---|
| all | 0.0789143 | 0 | 0.182834 | 0.182784 |
| digit | 0.0664743 | 0 | 0.182632 | 0.182784 |
| geometric | 0.077161 | 0 | 0.182674 | 0.182784 |

## §7.4 disclosure

Plan §7.4 reading (D78): full state tensors are not saved. Cumulative-state distances and intermediate decodings exist only for the primary configurations (every level-1 value, weighted under the frequency and the uniform policy; level 11, frequency policy, dose 1, seeds 0-2). Every other configuration has the cell-level change vectors of C and D against A, the per-later-level D code changes and the replacement diagnostics only. This follows §7.4's closing sentence ("We report if only the final sensitivity is estimable") and is a reading, not a deviation.

## Claim boundaries (§13)

Results are stated conditionally on checkpoint and intervention policy. The main risks — distribution shift after code replacement, teacher/generated conflation, data overlap, readout capacity, format errors, and post hoc target selection — appear in the final report together with their assigned controls. No single diagnostic proves in general that a patch is "in-distribution".

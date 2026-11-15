# WP2 evaluation (test role)

**WP2 confirmatory evaluation on TEST (plan v3.7); single look, read only after all TEST runs are complete**

- Date: 2026-11-15
- Tag commit: 1047668b8954535145a247ed4eb5704d1387bfda
- Frozen now: True

| Runner | Status | Valid | Commit | Seconds | Reasons |
|---|---|---|---|---|---|
| e3_extract | valid | True | 1047668b8954535145a247ed4eb5704d1387bfda | 790.99 | - |
| e3 | valid | True | 1047668b8954535145a247ed4eb5704d1387bfda | 17749.6 | - |
| equiv | valid | True | 1047668b8954535145a247ed4eb5704d1387bfda | 1654.12 | - |
| e2 | valid | True | 1047668b8954535145a247ed4eb5704d1387bfda | 32027 | - |
| e1 | valid | True | 1047668b8954535145a247ed4eb5704d1387bfda | 522.674 | - |

## Primary contrasts (§11.1)

| Contrast | Estimate | 98.33% interval | 95% interval | Method | n | n nonzero | H1 TOST interval (level, method) | TOST verdict |
|---|---|---|---|---|---|---|---|---|
| H1 | 0.00289158 | [0.00249257, 0.0032984] | [0.00256179, 0.00322378] | bootstrap | 600 | 600 | [0.00253217, 0.00325151], 96.67% interval (bootstrap) | equivalent |
| H2 | -0.111275 | [-0.136127, -0.0884651] | [-0.131523, -0.0921438] | bootstrap | 600 | 299 | - | - |
| H3 | 0.0165724 | [0.00130923, 0.0334894] | [0.00367136, 0.029902] | bootstrap | 600 | 102 | - | - |

- H1: the 95% interval is the individual-level 95% interval; the 98.33% family interval is the inferential one.
- H2: the 95% interval is the individual-level 95% interval; the 98.33% family interval is the inferential one.
- H3: the 95% interval is the individual-level 95% interval; the 98.33% family interval is the inferential one.

## §13 readings

- **H1** — H1: 98.33% lower limit > 0 and the 96.67% interval inside ±0.01
  - Justified claim: The candidate mask is readable from the level-6 state above the permuted null control, but by less than the practical threshold, with the examined probe family and budget
  - Does not follow: The representation computes candidates, or carries no candidate information; another readout could not do better
- **H1** — Generated probe beats the null control
  - Justified claim: The label is readable with the examined readout
  - Does not follow: The model contains more information than the input, or the generator uses the read-out feature
- **H2** — Early single-code replacement causes greater degradation
  - Justified claim: Greater level sensitivity under the given policy
  - Does not follow: The coarse code explicitly plans an algorithm; a level 1 vs. 11 difference implies a graded sensitivity along the early levels or is independent of level 1's single-code size and learned upsampler
- **H3** — D better than C, corrected for sham
  - Justified claim: Later generation attenuates the intervention effect
  - Does not follow: The improvement is certainly logical error correction
- **H3** — Positive compensation in a checkpoint trained with level corruption
  - Justified claim: Robustness consistent with the training objective
  - Does not follow: The model spontaneously detects and repairs logical errors
- **theta2_prime** — Levels 2 vs. 11 interval inside ±3 pp with adequate precision
  - Justified claim: No practically relevant solve difference between levels 2 and 11 under the given policy
  - Does not follow: Level 2 carries no information or has no causal role
- **level12** — Level-12 readout clearly above the null control and teacher − generated inside ±0.01
  - Justified claim: The level-12 readability is consistent with solution content
  - Does not follow: The generated representation computes candidates or encodes inference steps
- **equivariance**: descriptive (no pre-specified criterion). Inputs: `{"categories": {"all": {"mean_deviation": 0.07910500465602105, "share_within": 0.0, "brier_transformed": 0.18373213023466456, "brier_original": 0.18385353975905716}, "digit": {"mean_deviation": 0.06864203610428397, "share_within": 0.0, "brier_transformed": 0.1834371340233264, "brier_original": 0.18385353975905716}, "geometric": {"mean_deviation": 0.07824575519511853, "share_within": 0.0, "brier_transformed": 0.18378087676744362, "brier_original": 0.18385353975905716}}, "n": 200, "acceptable": 0.0116, "acceptable_source": "fixed", "seed_noise_p95": 0.011747008537198636, "equivariance_reading": "descriptive (no pre-specified criterion)"}`

## Secondary contrasts

| Contrast | Estimate | 95% interval | Method | n | TOST interval (level, method) | TOST verdict |
|---|---|---|---|---|---|---|
| theta_T | 8.65114e-05 | [-0.000127967, 0.000294877] | bootstrap | 600 | [-9.14108e-05, 0.000260656], 90% interval (bootstrap) | equivalent |
| theta1_wl.L02 | 0.000758396 | [0.000524921, 0.000989525] | bootstrap | 600 | - | - |
| theta1_wl.L12 | 0.0505651 | [0.0501641, 0.0509693] | bootstrap | 600 | - | - |
| theta1_pc.L02 | 0.000705208 | [0.000591248, 0.000816712] | bootstrap | 600 | - | - |
| theta1_pc.L06 | 0.00162348 | [0.00144418, 0.00179744] | bootstrap | 600 | - | - |
| theta1_pc.L12 | 0.0467077 | [0.0463791, 0.0470357] | bootstrap | 600 | - | - |
| raw_minus_generated.projected | -0.229214 | [-0.229692, -0.228745] | bootstrap | 600 | - | - |
| raw_minus_generated.unprojected | -0.220133 | [-0.220611, -0.219664] | bootstrap | 600 | - | - |
| theta2_prime | 1.85037e-19 | [-0.0151904, 0.0151904] | bound | 600 | [-0.0151904, 0.0151904], one-sided 95% rare-event bound | equivalent |
| uniform.theta2 | -0.177 | [-0.199778, -0.154778] | bootstrap | 600 | - | - |
| uniform.theta_comp | 0.0187778 | [0.00722222, 0.0308889] | bootstrap | 600 | - | - |
| uniform.theta2_prime | -0.005 | [-0.0301636, 0.0301636] | bound | 600 | - | - |
| correct_baseline.theta2 | -0.131365 | [-0.153829, -0.11053] | bootstrap | 526 | - | - |
| correct_baseline.theta_comp | 0.0146133 | [0.000595432, 0.0297243] | bootstrap | 526 | - | - |

## AUC over the frozen range (§7.3, §12.2)

- 6-11: auc_a = n/a, auc_b = n/a, range = [3.29177e-05, 7.93023e-05], TEST coverage = {'a': [1.6323957646796494e-05, 7.159221665700793e-05], 'b': [2.409767065972331e-05, 0.0016686060638676282]}, reason = TEST nodes do not cover the frozen range
- 2-11: auc_a = n/a, auc_b = n/a, range = n/a, TEST coverage = {'a': [8.786078121774364e-06, 1.4825857305330221e-05], 'b': [2.409767065972331e-05, 0.0016686060638676282]}, reason = no frozen range (§12.2)

## E1 (§6)

- n = 600, official exact share = 0.876667, generated solve = 0.876667, teacher exact share = 1
- Hamming: token mean = 0.0172659, cell mean = 0.0189712, cell empty mean = 0.0301307, n = 600

## E2 descriptive tables (no statistics)

- sham_mismatch = {"level1_B1": 0, "levels_B": {"2": 0, "6": 0, "11": 0}}, level1_noop_mismatch = 0, code_mismatch = {"level1_B1": 0, "levels_B": {"2": 0, "6": 0, "11": 0}, "level1_noop_D": 0}

| Level | Policy | Dose | Records | Excluded | Solve A | Solve C | Solve D |
|---|---|---|---|---|---|---|---|
| 2 | frequency | 1 | 1800 | 0 | 0.876667 | 0.876667 | 0.876667 |
| 2 | frequency | 2 | 1800 | 0 | 0.876667 | 0.876667 | 0.873333 |
| 2 | uniform | 1 | 1800 | 0 | 0.876667 | 0.872778 | 0.871111 |
| 2 | uniform | 2 | 1800 | 0 | 0.876667 | 0.867778 | 0.865556 |
| 6 | frequency | 1 | 1800 | 0 | 0.876667 | 0.876667 | 0.875556 |
| 6 | frequency | 2 | 1800 | 0 | 0.876667 | 0.876667 | 0.87 |
| 6 | frequency | 4 | 1800 | 0 | 0.876667 | 0.876667 | 0.873333 |
| 6 | frequency | 8 | 1800 | 0 | 0.876667 | 0.876667 | 0.860556 |
| 6 | frequency | 13 | 1800 | 0 | 0.876667 | 0.876667 | 0.855556 |
| 6 | uniform | 1 | 1800 | 0 | 0.876667 | 0.876667 | 0.872778 |
| 6 | uniform | 2 | 1800 | 0 | 0.876667 | 0.876667 | 0.868889 |
| 6 | uniform | 4 | 1800 | 0 | 0.876667 | 0.876667 | 0.866111 |
| 6 | uniform | 8 | 1800 | 0 | 0.876667 | 0.876667 | 0.869444 |
| 6 | uniform | 13 | 1800 | 0 | 0.876667 | 0.876667 | 0.86 |
| 11 | frequency | 1 | 1800 | 0 | 0.876667 | 0.876111 | 0.876667 |
| 11 | frequency | 4 | 1800 | 0 | 0.876667 | 0.876111 | 0.874444 |
| 11 | frequency | 11 | 1800 | 0 | 0.876667 | 0.874444 | 0.872778 |
| 11 | frequency | 21 | 1800 | 0 | 0.876667 | 0.866667 | 0.865 |
| 11 | frequency | 41 | 1800 | 0 | 0.876667 | 0.854444 | 0.859444 |
| 11 | frequency | 67 | 1800 | 0 | 0.876667 | 0.836111 | 0.842222 |
| 11 | uniform | 1 | 1800 | 0 | 0.876667 | 0.876667 | 0.876111 |
| 11 | uniform | 4 | 1800 | 0 | 0.876667 | 0.875556 | 0.875 |
| 11 | uniform | 11 | 1800 | 0 | 0.876667 | 0.875 | 0.873333 |
| 11 | uniform | 21 | 1800 | 0 | 0.876667 | 0.867778 | 0.868889 |
| 11 | uniform | 41 | 1800 | 0 | 0.876667 | 0.863333 | 0.859444 |
| 11 | uniform | 67 | 1800 | 0 | 0.876667 | 0.843889 | 0.848889 |

### E2 propagation diagnostics (D78)

- Weighting: level-1 rows weighted by the policy weights over non-no-op rows; other configurations averaged over eligible seeds within puzzle, then over puzzles. Full maps are in results.json.

| Configuration | Mean later-level D code changes |
|---|---|
| level1-frequency | L2: 0.009499, L3: 0.07555, L4: 0.05164, L5: 0, L6: 0.09359, L7: 0.2368, L8: 0.5044, L9: 0.923, L10: 2.087, L11: 3.258, L12: 1.077 |
| level1-uniform | L2: 0.009, L3: 0.07189, L4: 0.04933, L5: 0, L6: 0.08667, L7: 0.2174, L8: 0.4603, L9: 0.8528, L10: 1.938, L11: 3.038, L12: 1.034 |
| L02-frequency-d1 | L3: 0.045, L4: 0.03833, L5: 0, L6: 0.04944, L7: 0.1072, L8: 0.225, L9: 0.3756, L10: 0.7533, L11: 1.103, L12: 0.3539 |
| L02-frequency-d2 | L3: 0.07333, L4: 0.05833, L5: 0, L6: 0.06833, L7: 0.155, L8: 0.275, L9: 0.505, L10: 0.9817, L11: 1.412, L12: 0.3967 |
| L02-uniform-d1 | L3: 0.01833, L4: 0.02333, L5: 0, L6: 0.03111, L7: 0.06778, L8: 0.1267, L9: 0.2361, L10: 0.4461, L11: 0.6606, L12: 0.2372 |
| L02-uniform-d2 | L3: 0.03111, L4: 0.02889, L5: 0, L6: 0.045, L7: 0.095, L8: 0.165, L9: 0.3289, L10: 0.6461, L11: 0.9883, L12: 0.3322 |
| L06-frequency-d1 | L7: 0.145, L8: 0.2728, L9: 0.4717, L10: 0.8894, L11: 1.262, L12: 0.42 |
| L06-frequency-d2 | L7: 0.2694, L8: 0.495, L9: 0.8161, L10: 1.577, L11: 2.187, L12: 0.7133 |
| L06-frequency-d4 | L7: 0.4794, L8: 0.8311, L9: 1.388, L10: 2.671, L11: 3.652, L12: 1.103 |
| L06-frequency-d8 | L7: 0.8739, L8: 1.52, L9: 2.402, L10: 4.458, L11: 6.077, L12: 1.891 |
| L06-frequency-d13 | L7: 1.258, L8: 2.072, L9: 3.349, L10: 6.193, L11: 8.414, L12: 2.548 |
| L06-uniform-d1 | L7: 0.1411, L8: 0.2744, L9: 0.4644, L10: 0.875, L11: 1.247, L12: 0.4083 |
| L06-uniform-d2 | L7: 0.2661, L8: 0.4933, L9: 0.8467, L10: 1.562, L11: 2.189, L12: 0.7167 |
| L06-uniform-d4 | L7: 0.4689, L8: 0.81, L9: 1.374, L10: 2.589, L11: 3.574, L12: 1.122 |
| L06-uniform-d8 | L7: 0.8217, L8: 1.413, L9: 2.306, L10: 4.311, L11: 5.841, L12: 1.717 |
| L06-uniform-d13 | L7: 1.247, L8: 2.011, L9: 3.328, L10: 6.087, L11: 8.202, L12: 2.523 |
| L11-frequency-d1 | L12: 0.065 |
| L11-frequency-d4 | L12: 0.2106 |
| L11-frequency-d11 | L12: 0.5 |
| L11-frequency-d21 | L12: 0.9106 |
| L11-frequency-d41 | L12: 1.497 |
| L11-frequency-d67 | L12: 2.297 |
| L11-uniform-d1 | L12: 0.065 |
| L11-uniform-d4 | L12: 0.1983 |
| L11-uniform-d11 | L12: 0.4883 |
| L11-uniform-d21 | L12: 0.8417 |
| L11-uniform-d41 | L12: 1.47 |
| L11-uniform-d67 | L12: 2.166 |

| Primary configuration | state_dist_C per level | state_dist_D per level |
|---|---|---|
| level1-frequency | [0.9333, 0.8751, 0.8604, 0.8412, 0.8628, 0.7875, 0.6862, 0.5315, 0.3934, 0.3219, 0.2751, 0.1548] | [0.9333, 0.8751, 0.8579, 0.839, 0.8605, 0.7866, 0.6885, 0.5423, 0.416, 0.3558, 0.3152, 0.1864] |
| level1-uniform | [1.204, 1.127, 1.109, 1.084, 1.112, 1.015, 0.8842, 0.6849, 0.5069, 0.4147, 0.3544, 0.1995] | [1.204, 1.127, 1.106, 1.081, 1.109, 1.013, 0.8852, 0.6927, 0.5245, 0.4417, 0.3868, 0.2259] |
| L11-frequency-d1 | [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.07742, 0.04358] | [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.07742, 0.04491] |

## E3 main table (§8.2, §12.2)

Brier = seed-mean per-puzzle Brier on the score set; relative difference = (Brier - reference) / reference, only within one construction.

| Row | Group | Construction | Brier | Reference | Relative difference | Config | n_params |
|---|---|---|---|---|---|---|---|
| wl_L06.generated | whole_layer | whole_layer | 0.230652 | - | n/a | [0.1, 0.001] | 5346 |
| wl_L06.permuted | whole_layer | whole_layer | 0.233543 | wl_L06.generated | 0.0125366 | [0.1, 0.001] | 5346 |
| wl_L06_controls.random | whole_layer | whole_layer | 0.233681 | wl_L06.generated | 0.0131339 | [0.001, 0.001] | 5346 |
| wl_L06_controls.label_permuted | whole_layer | whole_layer | 0.232848 | wl_L06.generated | 0.00951999 | [0.1, 0.001] | 5346 |
| wl_teacher_L06.teacher | whole_layer | whole_layer | 0.230678 | wl_L06.generated | 0.000113822 | [0.1, 0.001] | 5346 |
| wl_teacher_L12.teacher | whole_layer | whole_layer | 0.183394 | wl_L12.generated | 0.000471946 | [0.1, 0.001] | 5346 |
| raw_projected.linear | whole_layer | input | 0.00143797 | wl_L06.generated | -0.993766 | [0, 0.003] | 2628 |
| raw_unprojected.linear | whole_layer | input | 0.0105188 | wl_L06.generated | -0.954395 | [0, 0.003] | 2628 |
| pc_L06.linear | per_cell | per_cell | 0.231001 | - | n/a | [0.1, 0.001] | 3042 |
| pc_L06.mlp | per_cell | per_cell | 0.230916 | pc_L06.linear | -0.000370993 | [0.1, 0.003] | 22217 |
| controls.raw_linear | per_cell | input | 0.0105188 | pc_L06.linear | -0.954464 | [0, 0.003] | 2628 |
| controls.raw_mlp | per_cell | input | 2.0533e-08 | pc_L06.mlp | -1 | [0, 0.003] | 19273 |
| controls.peer_counts_linear | per_cell | input | 0.0141529 | pc_L06.linear | -0.938732 | [0, 0.003] | 819 |
| controls.surface_linear | per_cell | input | 0.225256 | pc_L06.linear | -0.0248736 | [0, 0.003] | 828 |
| controls.permuted_linear | per_cell | per_cell | 0.232625 | pc_L06.linear | 0.007028 | [0.1, 0.001] | 3042 |
| controls.random_linear | per_cell | per_cell | 0.232988 | pc_L06.linear | 0.00860003 | [0.01, 0.001] | 3042 |
| controls.label_permuted_linear | per_cell | per_cell | 0.232551 | pc_L06.linear | 0.00670965 | [0.1, 0.001] | 3042 |
| controls.teacher_L02_linear | per_cell | per_cell | 0.232124 | pc_L02.linear | 0.000366382 | [0.1, 0.001] | 3042 |
| controls.teacher_L06_linear | per_cell | per_cell | 0.231016 | pc_L06.linear | 6.18529e-05 | [0.1, 0.001] | 3042 |
| controls.teacher_L12_linear | per_cell | per_cell | 0.18604 | pc_L12.linear | 0.000528827 | [0, 0.003] | 3042 |
| controls.rule | label_free | input | 0 | - | n/a | n/a | n/a |
| controls.marginal | label_free | input | 0.232492 | - | n/a | n/a | n/a |

| Level | WL generated | WL permuted | PC linear | PC MLP | PC permuted |
|---|---|---|---|---|---|
| L02 | 0.232647 | 0.233405 | 0.232039 | 0.23191 | 0.232744 |
| L06 | 0.230652 | 0.233543 | 0.231001 | 0.230916 | 0.232625 |
| L12 | 0.183308 | 0.233873 | 0.185941 | 0.182818 | 0.232649 |

| Unit-digit fit | Brier | Exact match | ROC-AUC | Brier (ensemble) |
|---|---|---|---|---|
| generated | 0.233315 | 0.00851852 | 0.501938 | 0.233291 |
| raw | 0.136096 | 0.469506 | 1 | 0.136079 |

Training size: whole_layer is the primary probe's curve and the basis for any data-requirement statement; per_cell is secondary (spec ambiguity 3).

| Curve | Fit | n puzzles | Brier | Reused from |
|---|---|---|---|---|
| whole_layer | n125 | 125 | 0.236458 | - |
| whole_layer | n250 | 250 | 0.234717 | - |
| whole_layer | n500 | 500 | 0.232902 | - |
| whole_layer | n1000 | 1000 | 0.2314 | - |
| whole_layer | n2000 | 2000 | 0.230652 | wl_L06.generated |
| per_cell | n125 | 125 | 0.231595 | - |
| per_cell | n250 | 250 | 0.231314 | - |
| per_cell | n500 | 500 | 0.231147 | - |
| per_cell | n1000 | 1000 | 0.231025 | - |
| per_cell | n2000 | 2000 | 0.231001 | pc_L06.linear |

Depth breakdown (descriptive; label rates and sample sizes differ by depth, §5.2, §8.3):

| Depth | n cells | n puzzles | Positive rate | wl_L06.generated | pc_L06.linear | raw_unprojected.linear | raw_projected.linear |
|---|---|---|---|---|---|---|---|
| 1 | 5982 | 600 | 0.313682 | 0.217236 | 0.217368 | 0.0102081 | 0.00135851 |
| 2 | 4874 | 598 | 0.333311 | 0.222016 | 0.222357 | 0.0102796 | 0.00141112 |
| 3 | 4031 | 588 | 0.36313 | 0.229544 | 0.229578 | 0.0104805 | 0.00145263 |
| >=4 | 12871 | 563 | 0.398959 | 0.238681 | 0.238985 | 0.0107278 | 0.00147375 |
| stuck | 2842 | 89 | 0.398585 | 0.239447 | 0.23978 | 0.0106982 | 0.00146402 |
| censored | 0 | 0 | n/a | n/a | n/a | n/a | n/a |

| θ₁ pair | Per-seed θ₁ means (no intervals, spec ambiguity 18) |
|---|---|
| H1 | [0.00287549, 0.00294357, 0.00285569] |
| theta1_wl.L02 | [0.000753785, 0.000771245, 0.000750157] |
| theta1_wl.L12 | [0.0510641, 0.0505208, 0.0501103] |
| theta1_pc.L02 | [0.000704202, 0.000703639, 0.000707783] |
| theta1_pc.L06 | [0.00162536, 0.00161722, 0.00162785] |
| theta1_pc.L12 | [0.0468311, 0.0471226, 0.0461692] |

Selected configurations that differ from the pre-lock D64/D67 selection: none.

## Exploratory level-12 equivariance (§8.4)

Reading: descriptive (no pre-specified criterion); tolerance 0.0116 (fixed), TEST seed-noise P95 = 0.011747.

| Category | Mean deviation | Share within | Brier transformed | Brier original |
|---|---|---|---|---|
| all | 0.079105 | 0 | 0.183732 | 0.183854 |
| digit | 0.068642 | 0 | 0.183437 | 0.183854 |
| geometric | 0.0782458 | 0 | 0.183781 | 0.183854 |

## §7.4 disclosure

Plan §7.4 reading (D78): full state tensors are not saved. Cumulative-state distances and intermediate decodings exist only for the primary configurations (every level-1 value, weighted under the frequency and the uniform policy; level 11, frequency policy, dose 1, seeds 0-2). Every other configuration has the cell-level change vectors of C and D against A, the per-later-level D code changes and the replacement diagnostics only. This follows §7.4's closing sentence ("We report if only the final sensitivity is estimable") and is a reading, not a deviation.

## Claim boundaries (§13)

Results are stated conditionally on checkpoint and intervention policy. The main risks — distribution shift after code replacement, teacher/generated conflation, data overlap, readout capacity, format errors, and post hoc target selection — appear in the final report together with their assigned controls. No single diagnostic proves in general that a patch is "in-distribution".

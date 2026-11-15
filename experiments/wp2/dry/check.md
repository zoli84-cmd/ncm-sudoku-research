# WP2 dry-run check

DRY RUN (CAL / PROBE-VAL in the TEST role); not TEST

- date: 2026-11-14
- code commit: 1047668b8954535145a247ed4eb5704d1387bfda (dirty: False)
- tag commit: 1047668b8954535145a247ed4eb5704d1387bfda; frozen: True
- check state (frozen, clean, unchanged during the check): True
- technical_success: **true**

## Run records

| runner | status | valid | reasons |
|---|---|---|---|
| e3_extract | valid | True | - |
| e3 | valid | True | - |
| equiv | valid | True | - |
| e2 | valid | True | - |
| e1 | valid | True | - |

## Comparisons

| part | ok | detail |
|---|---|---|
| dry_ids | True | 50 ids, first CAL ids in both E2 references |
| e2_records | True | matched 3900, differing values 0, complete coverage True |
| e2_level1 | True | matched 800, differing values 0, complete coverage True |
| e2_base | True | pilot2: matched 50, differing values 0, complete coverage True; level1_full_batch: matched 50, differing values 0, complete coverage True |
| e2_identity | True | solve-based and code-based counts in e2.json and the run record |
| e3 | True | 34 mapped fits, differing: none; depth ok True |
| equivariance | True | deviation, seed_noise, brier, brier_original against experiments/lock/equivariance_l12.json |
| e1 | True | matched 50, differing values 0, complete coverage True |
| extraction | True | matches_e3prep of the e3_extract record |
| probe_inputs | True | 22 PROBE files; changed: none |
| dry_evaluate | True | results.json at the tag commit True, clean True, role dry True; changed inputs: none; unrecorded outputs: none |

New fits without a pre-lock reference: wl_L02.generated, wl_L02.permuted, wl_L06_controls.label_permuted, wl_L06_controls.random, wl_teacher_L06.teacher, wl_training_size.n1000, wl_training_size.n125, wl_training_size.n2000, wl_training_size.n250, wl_training_size.n500.

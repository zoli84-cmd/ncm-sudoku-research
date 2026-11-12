# OSF preregistration text (embargoed)

Prepared for submission to OSF Registries (OSF Preregistration template). The authoritative protocol is the locked plan named below; this text summarizes it and defers to it wherever they differ.

**Locked protocol:** `research_plan_v3.7.md` in the private repository `zoli84-cmd/ncm-sudoku-research`, git tag `prereg-v3.7`, commit `3e39bc8af2ff34cd233588f732a01b484f0d85e1`. The plan file's SHA-256 at that commit: `47f0567e56307b7b9e2f8a4b4ed43423427b8c275929ce42054927f8054f8906`. A copy of the plan file is attached to this registration.

**Embargo:** requested until publication of the results or the maximum embargo period.

---

## Title

Hierarchical sensitivity, compensation and logical readability in Next-Concept Modeling Sudoku generation

## Description

We study a released Next-Concept Modeling (NCM) checkpoint for hard Sudoku puzzles (Kumbong et al., 2026, arXiv:2610.14162). The model generates 12 hierarchical residual-VQ code levels (16 codes per level) from a puzzle and decodes them into a grid. We ask three things:

1. How do discrete code replacements at different hierarchy levels change the solve outcome (level sensitivity)?
2. Does regenerating the later levels after a perturbation change the effect of that perturbation, compared with keeping the original later codes (compensation)?
3. Can the initial candidate mask of the puzzle be read out from the generated intermediate representation better than from a permuted null control (readability)?

A conditional causal-patching study (E4) is not part of this registration; it will receive its own registration before its test set is generated.

## Hypotheses

The primary family has three contrasts, each with a two-sided 98.33% percentile cluster-bootstrap interval (Bonferroni, family-wise error 5%):

- **H1 (readability, E3):** θ₁ = E[B_permuted − B_generated], the improvement in candidate-mask Brier loss at hierarchy level 6, with a cell-relative whole-layer linear probe. Two pre-specified readings: θ₁ ≠ 0 if the 98.33% interval excludes 0; practical equivalence if the 96.67% interval (two one-sided tests at 0.05/3 each) lies inside ±0.01. The positive-but-small reading requires the 98.33% lower limit above 0 and the 96.67% interval inside ±0.01.
- **H2 (level sensitivity, E2):** θ₂ = E[(Y_D,1 − Y_A) − (Y_D,11 − Y_A)], the solve contrast of a single-code replacement at level 1 versus level 11 (minimal practical effect 5 percentage points).
- **H3 (compensation, E2):** θ_comp = E[(Y_D − Y_C) − (Y_B − Y_A)] at level 1 (minimal practical effect 3 percentage points).

Secondary, pre-specified: levels 2 vs. 11 solve contrast with a ±3 pp equivalence range (90% TOST); level-12 teacher − generated Brier contrast with a ±0.01 equivalence range (90% TOST); per-cell probe, level 2 and level 12 versions of θ₁; dose curves matched on decoder total-variation damage over a pre-specified common range. Exploratory: equivariance of the level-12 readout under Sudoku symmetries, GLMM, unit–digit labels, same-solution/different-clue-mask teacher control.

Interpretation rules, including what does **not** follow from each outcome, are fixed in plan §13.

## Design

- **Model:** `hazyresearch/ncm-checkpoints`, revision `d342ce8aaea58830eef3b8ad473664673e41f692`, Sudoku-hard generator and tokenizer (SHA-256 in plan §12.2); upstream code `HazyResearch/ncm` at commit `c70274273f489abc73832b2b98584a8483b6b203`. Reproduction passed: 86.3% official solve rate vs. the published 86.1%.
- **Branches (E2):** for each puzzle, A clean; B sham restart; C perturbed level with the original later codes replayed; D perturbed level with later codes regenerated. All branches of a puzzle run with identical batches (FP32, CPU, deterministic algorithms).
- **Perturbation policy:** level 1 is enumerated over all 15 alternative values weighted by frozen calibration-set (CAL) code frequencies; level 11 draws one position and value with three intervention seeds; the frequency vectors for levels 1, 2, 6 and 11 are frozen from CAL and never estimated on TEST.
- **Probe (E3):** for each originally empty cell, the generated cumulative state of the cell and its 20 peers at level 6, projected by a PCA (256 components) fitted on PROBE-TRAIN empty cells and whitened, plus the cell's own state and a position one-hot; linear probe with nine sigmoid outputs shared across cells; AdamW grid and budget fixed in plan §8.1; three training seeds; permuted control trained on puzzle-permuted PROBE-TRAIN data and tuned on independently permuted PROBE-VAL data.

## Sampling plan

- **Existing data and what has been observed:** model training data is not released. All analysis puzzles come from an own 30-clue generator (frozen; passed a distribution gate against the released hard set). Non-confirmatory pilots were run on a calibration set (CAL, 300 puzzles) and probe sets (PROBE-TRAIN 2,000, PROBE-VAL 500); their results, and the design changes they motivated, are logged in the repository (`DECISIONS.md` D42–D73). The design changes made after these pilots, including the H1 probe and form, are disclosed in plan §7.2 and §8.1.
- **TEST:** 600 puzzles, generated before this registration from seed namespace 6 and screened for exact duplicates and symmetry equivalence against every earlier subset (0 found). No model has been run on TEST. Identity hashes: ids `6e019563448e73408cd24a7ae207f5fd2549f0c881e70a37348d06f21ad6f09e`, puzzles `e9e714c83f333922e55ba36998343e1e0ffa73a75c52e8531f0bf5bed943c886`, solutions `08b333165f081f8c74d6d558372dc02cbb8d4dc35aac40b5da0ac699031fe471` (formats in plan §12.2).
- **Sample size rationale:** simulation of the full analysis procedure from pilot puzzle-level outcomes under the target alternatives (plan §11.4): H2 needs 200–400, H3 300, the levels 2 vs. 11 equivalence claim 600, H1 100; TEST = 600. No optional stopping.

## Variables

- Solve: complete, well-formed 81-cell grid preserving all clues and all Sudoku constraints (own validator).
- Damage: mean cell-wise total variation distance between the decoder output distributions of branches C and A.
- Label: initial candidate mask (nine bits per originally empty cell); Brier loss averaged per cell, then per puzzle over empty cells, then across puzzles.

## Analysis plan

Puzzle-level paired estimates; percentile cluster bootstrap with 10,000 resamples (resampling unit: puzzle); a conservative rare-event bound with a one-sided Clopper–Pearson limit when fewer than 20 puzzles have a nonzero difference (plan §11.2). Simulated operating characteristics at n = 600: H1 equivalence power 1.000 at true θ₁ of 0 and 0.0031, false-equivalence rate 0.016/0.014 at ±0.01; levels 2 vs. 11 false-equivalence rate 0.025/0.036 at ±0.03 (plan §11.4). Exclusions, format errors and all branches are reported; non-significant results are not read as absence without the pre-specified equivalence test.

## Other

Any deviation after this registration is logged with date and reason in `DECISIONS.md` and requires a new plan version. Hypotheses arising from TEST data are exploratory.

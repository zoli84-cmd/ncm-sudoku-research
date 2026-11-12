# NCM–Sudoku: hierarchical sensitivity, error propagation, and logical representations

**Research plan v3.7 — preregistration lock version**  
**Date:** 2026-11-12  
**Predecessors:** `research_plan_v3.6.md`, `research_plan_v3.5.md`, `research_plan_v3.4.md`, `research_plan_v3.3.md`, `research_plan_v3.2.md`, `research_plan_v3.1.md`, `research_plan_v3.md` (English translation of the Hungarian `NCM_Sudoku_kutatasi_terv_v3.md`); all remain unchanged.  
**Status:** G0 passed (D31), the generator passed the distribution gate (D41), two E2 pilots ran on CAL (D42, D53), and the E3 preparation ran on PROBE-TRAIN/PROBE-VAL (D64, D67, D69). This version fills every lock field of Section 12.2 (D53–D71) and is the protocol frozen by the preregistration lock; TEST has been generated (Section 12.2) but no model has been run on it.  
**Versioning:** the English document is authoritative from v3.1 on. Every change from v3.0 is listed in Section 16 and justified in `DECISIONS.md`.

## 1. Goal, research order, and claim boundaries

The research investigates how modifying different hierarchical levels changes the output in Next-Concept Modeling (NCM) Sudoku generation, which logical properties can be read out from the intermediate representations, and which of these can be linked to a targeted causal effect.

The levels of evidence are kept separate: **decodability → generalization under symmetries → targeted causal role**. None of the levels on its own proves explicit search, a human Sudoku strategy, or a complete algorithmic plan. Compression and logical content may be present together.

The first execution unit is the reproduction of one checkpoint and a narrow E1–E2 pilot. The first publication target is the **integrated result of E1 + E2 + E3**, together with appropriate controls and negative results. This is a research goal, not an advance promise of publishability. Starting E3 does not depend on a positive E2 effect; it requires validated representation extraction and an appropriate data split. E4 is a separate, conditional phase.

The change in final performance measures **sensitivity**. We speak of "error propagation" only when we also track the state change of the post-intervention levels, the intermediate reconstructions, and the spatial error pattern. "Compensation" is the operational name for the later attenuation of the original error effect; it is not the same as proven logical error correction.

## 2. Verified sources and open reproduction items

### 2.1 Source identification

The publication, the project page, the official repository, and the checkpoint collection are identifiable as available sources [1–4]. The arXiv entry is dated 9 October 2026, the project post 12 October 2026. Relative to the plan's date of 8 November 2026 these are **not in the future**. We therefore do not adopt the supplementary review's suspicion that they are placeholders.

**Pinned reference for the code review:** `HazyResearch/ncm`, commit `c70274273f489abc73832b2b98584a8483b6b203` (2026-10-14). This is a verified repository identifier, not evidence that a checkpoint has already been reproduced on this commit.

| Item | Starting point verified from sources | To be pinned before running |
|---|---|---|
| First checkpoint | The released Sudoku-hard configuration | Exact checkpoint files, download revision and SHA-256; license |
| Hierarchy | 12 levels; code lengths: 1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89; 16 codes per level | Match between the loaded model and the configuration |
| Representation | 256-dimensional embedding; 89-long output token representation; `compression_factor=1` in the configuration | Tensor shapes, cell–token mapping, cumulative and residual states |
| Generation | The Sudoku configuration has `temperature=0.0`; on this branch the generator uses argmax | `.eval()` mode, numerical determinism, exact sampling settings |
| Conditioning | Later generator levels also receive the puzzle prefix | Whether the wrapper forwards this unchanged on every branch |
| Intervention | Code and state extraction can be built from the examined code | Own tested wrapper that continues from an arbitrary level |

The configuration items above rely on the released files and static source reading [4–9]. The hard/easy/medium label does not replace logical difficulty measured with an independent solver. Comparing separate checkpoints confounds model and data differences.

The original paper already discusses interventions on early codes and coarse representations, as well as training with corruption of earlier levels [1, appendices F.3 and H]. Novelty can therefore come from the Sudoku-specific measurement design, the controlled compensation contrast, the logical labeling, and the targeted causal test; perturbing early codes is not a new method by itself.

Related work (search of 2026-11-08, `literature/related_work_novelty_check.md`): linear readout of Sudoku candidates and a causally verified naked-single circuit already exist for an autoregressive trace-trained transformer [16]; state interventions and probes on Sudoku exist for HRM, where probe directions were decodable but not more causal than random directions [17]; NCM's generated coarse codes are reported to be largely non-canonical under re-encoding [18, not peer reviewed]. The claim of this study is therefore narrower: whether such logical readouts and targeted causal effects exist in a non-autoregressive, discrete, level-indexed latent, and how level-wise perturbations propagate and are compensated. Novelty statements are made "to our knowledge, as of 2026-11-08" and the search is repeated before submission.

### 2.2 G0: reproduction and instrumentation

1. **Environment and provenance:** record commit, dependencies, Python/PyTorch/CUDA, device, precision, configuration, checkpoint and data file hashes, licenses, seeds. **Numerical policy:** all experiments run in FP32, eager mode, with deterministic algorithms enabled, on CPU on native Windows (DECISIONS D30). The upstream evaluation path (`scripts/eval_shard.py`) already runs in FP32 eager mode without autocast or `torch.compile` but hard-codes CUDA; BF16 mixed precision and `torch.compile` belong to the paper's training setup [1, App. C]. The planned difference from the published evaluation is therefore CPU instead of CUDA kernels, through an own runner that mirrors `eval_shard.py` and `eval_merge.py` without modifying upstream code. Results are stated for this numerical configuration. A GPU is introduced only if the measured cost (item 9) requires it; a CUDA cross-check on the same puzzles is optional.
2. **Original run:** debug on a small technical sample, then reproduce the official evaluation with the original metric and with the standalone Sudoku metrics. **G0 acceptance rule:** (a) the official `exact` solve rate on the 2,000 released hard boards lies within ±1.0 percentage point of the published 86.1%; a difference is hypothesized to reflect numerical near-tie argmax flips; a per-board changed-output count is reported only if the optional CUDA cross-check provides paired reference predictions, otherwise it is marked unavailable; (b) the within-device identity tests (item 5) agree exactly, 100%. If (a) fails while (b) passes, the cause is investigated and the decision is logged in `DECISIONS.md`; work does not continue silently.
3. **Data path:** verify what the encoder encodes, what the generator sees, and which representations the intervention passes through. The teacher code is produced from the solution; the generated code is produced conditioned on the puzzle.
4. **Wrapper:** planned own interface: `forward_with_intervention()`. The name is a new implementation proposal, not a claim about an existing upstream API. It must support fixing the prefix, replacing a level, replaying the original suffix, and regenerating the suffix.
5. **Identity tests:** with hooks disabled, the original run must match; writing back the model's own code must leave the result unchanged; sham restart from the same level; RNG state preservation if a stochastic mode is used later. All branches A–D of a puzzle run with identical batch size and batch composition, because deterministic algorithms guarantee repeatability only for identical shapes.
6. **State saving:** upstream `idx_to_zhats` allocates one tensor, updates it in place, and appends the same object at every level, so all returned `z_hats` entries alias the final $Z_{\leq 12}$; the returned `z_levels` are downsampled, not full-length [7]. Full-length cumulative states $Z_{\leq\ell}$ are therefore computed in an own per-level loop that mirrors `idx_to_zhats` (same up-sampling and residual steps) and stores a clone after every level. G0 tests check distinct storage (a later update leaves saved earlier states unchanged), that each prefix $Z_{\leq\ell}$ equals an independent recomputation from levels $1..\ell$ only, and that the own $Z_{\leq 12}$ equals the upstream result exactly; inequality between $Z_{\leq\ell}$ and $Z_{\leq 12}$ is required only on fixtures with a known nonzero remaining contribution. Modifying a later state must not overwrite previously saved states.
7. **Decoding path:** a shorter level representation is not automatically a full Sudoku reconstruction. The partial cumulative state must be brought to the full token length expected by the final decoder, otherwise the result must not be interpreted as a cell-level partial solution [7–9].
8. **Validator:** test cases for a correct grid, altered clues, row/column/box repetition, truncated and over-long output, invalid characters, non-unique and unsatisfiable input. The parser must not silently repair model errors.
9. **Running cost:** measure time, memory, and storage of the baseline, state saving, fixed suffix, and regenerated suffix. The work plan gets a time estimate only after this.

**G0 gate:** E2/E4 are interpretable only with a validated intervention path. E1/E3 may proceed separately if representation extraction is reliable even when the intervention part is not ready. With a non-reproducible baseline, further results are preliminary diagnostics; the discrepancy must be resolved or a new, clearly distinct study protocol must be recorded.

## 3. Definitions, representations, and hypotheses

Let $P$ be the input puzzle, $S$ a verified reference solution, $U(P)$ the set of originally empty cells, and $L$ the number of hierarchy levels. This document **indexes levels from 1**; the mapping to the code's 0-based indices is contained in the run configuration.

| Notation / concept | Operational meaning |
|---|---|
| $C_\ell^T$ | Teacher codes of the solution produced by the encoder at level $\ell$ |
| $C_\ell^G$ | Discrete codes generated from the puzzle at the same level |
| $R_\ell$ | Residual contribution of a level in the decoder space |
| $Z_{\leq\ell}$ | Full-length cumulative state of the first $\ell$ levels |
| $H_\ell$ | A separately designated internal activation of the generator; not identical to the code |
| Coarse/fine | Early/late levels of the hierarchy; not a pre-established global/local semantics |
| Solve | Complete, well-formed 81-cell grid preserving all clues and all Sudoku constraints |

A code index is categorical: its numerical order has no self-evident geometric meaning. Consistently relabeling a codebook is an invertible operation, therefore not an information-removing null control. The very first 16-valued discrete code of the hard configuration can carry at most 4 bits; its high-dimensional embedding does not increase the number of possible states of the discrete variable.

**Teacher vs. logical label:** the same solution with different clue masks can yield different candidate sets while the teacher code is identical. Therefore the primary probes of the puzzle's logical state run on **generated representations**. The teacher branch is a solution-content control. An "input + teacher" probe is a separate analysis, in which the independent contribution of the input must also be measured.

| Hypothesis | Testable claim | Primary or conditional evaluation |
|---|---|---|
| H1: readability | A fixed-capacity probe reads the logical label from the generated representation better than the corresponding null control, and by how much | E3 candidate-mask Brier improvement at level 6 with the cell-relative whole-layer probe (Section 8.1), two-sided, with a pre-specified equivalence range of ±0.01 (Section 11.4); the per-cell probe, level 2 (low capacity) and level 12 (full resolution) are secondary; the raw-input control is a separate mandatory comparison |
| H2: level sensitivity | At an identical, precisely defined discrete edit cost, early and late interventions differ in their solve effect | E2 paired contrast of single-code interventions at levels 1 and 11; levels 2 vs. 11 secondary with an equivalence range |
| H3: adaptation | Regenerating the suffix modifies the perturbation effect relative to a fixed suffix | E2 four-branch interaction; primarily at level 1 with a single-code replacement |
| H4: generalization | Read-out labels follow the expected transformation under symmetries | Exploratory E3 equivariance result at level 12 (Section 8.4); no family holdout, since every puzzle is generated independently |
| H5: causal relevance | A preselected intervention causes a more specific change in the target cell than a matched control | Conditional E4a; for E4b a separate counterfactual protocol |

H1 does not claim more information than the input: the labels are deterministic functions of the puzzle. The question is the accessibility of the information under the given probe family and training setup [10–11]. Instead of v2's general "proof of mediation", H5 receives a narrower, verifiable goal; a mediation claim requires further assumptions and a pre-specified causal model [12–13].

## 4. Data construction and splitting

Every puzzle gets a stable identifier, clue count, source identifier, solution check, generation family identifier where available, solver features, and symmetry group identifier. The main analysis runs on verified unique-solution, consistent puzzles; multi-solution cases go into a separate, optional stratum.

**Grouping before splitting:** identical puzzles, known symmetric variants, clue masks derived from the same complete solution, and minimal counterfactual pairs go into the same top-level group. Splitting follows grouping, and augmentation comes only after that. Sudoku symmetries: digit permutation; row swap within a band; column swap within a stack; band and stack swap; transposition.

Orbit identification is ensured by verified canonicalization or by tracking the full generation provenance. If only partial duplicate detection is possible for an external dataset, the protocol reports this as partial protection and does not call the split provably orbit-independent. For independently generated solutions, provenance records known ancestry only; it does not detect two independent draws in the same symmetry orbit, so fresh data uses provenance plus screening (Section 4.1) and is described as partial protection. Fixing the probe split does not solve possible overlap with the pretrained model's training data; its discoverability is documented separately.

| Subset | Task | Constraint |
|---|---|---|
| CAL / technical pilot | Metrics, dose range, running cost, power inputs | Not a confirmatory result |
| PROBE-TRAIN | Fitting probes and training controls | Own training groups only |
| PROBE-VAL | Regularization, thresholds, early stopping | Not usable as final performance |
| SELECT | Selecting the E4 target, region, donor policy, and controls | An effect optimized here is not E4 evidence |
| TEST | Locked E1–E3 confirmatory evaluation | No post hoc level, label, or dose selection |
| E4-TEST | Fresh evaluation of the selected E4 specification | The full group of donors and pairs belongs here |

Subsets are disjoint at the group level. Shared use of TEST is allowed for pre-specified E1–E3 endpoints, but the related hypotheses are handled by a joint multiple-testing plan. Sample sizes, stratification, and handling of unavailable strata are fixed after the pilot, before TEST is opened.

### 4.1 Data sources

- **Released evaluation set:** `hazyresearch/ncm-datasets`, `sudoku/hard` (MIT): 2,000 boards with exactly 30 clues. The easy/medium/hard sets share the same 2,000 solutions with different clue masks. Used for the G0 reproduction and reported as a secondary "official distribution" stratum. The training data of the checkpoints is not released; it is most likely the synthetic S-FLM set (48k training puzzles, seed 42), which is unverified.
- **Fresh puzzles:** all CAL, PROBE-TRAIN, PROBE-VAL, SELECT, TEST and E4-TEST puzzles come from an own generator, written from scratch (the S-FLM generator has no license). A complete solution is drawn by randomized backtracking with a shuffled digit order per cell (not proven uniform over grids). Clues are removed in one pass over a random cell order, a removal being kept only if the solution stays unique, until exactly 30 clues remain; an attempt that ends above 30 clues restarts with a new order on the same solution, up to a fixed attempt limit, and restart and discard counts are reported. With about $6.7\cdot10^{21}$ valid grids, overlap with the unreleased training data is expected to be negligible, conditional on the sampler being well dispersed and on the unverified training-data assumption. Exact duplicate solutions and a cheap symmetry-invariant signature are screened across all subsets; generation provenance is recorded but is only partial orbit protection.
- **Distribution gate (one terminal validation, before any analysis subset is generated):** (1) during generator development, on development batches that are never reused, the generator version and the validation batch size are chosen; the size is set by simulating the terminal procedure for at least 90% pass probability at zero true difference (planning value at least 1,000 puzzles); (2) the generator is frozen and its code hash recorded, and acceptance thresholds for the model-free check are fixed; (3) one fresh validation batch is drawn and evaluated once: the model-free check compares the solver-depth distribution (waves 1, 2, 3, at least 4, stuck) and the initial single counts with the 2,000 released boards, and the model check tests equivalence of the hard-checkpoint solve rate within ±5 percentage points by two one-sided tests (90% interval) against the finite released benchmark; (4) there is no enlargement, retry, or pooling after this look: if either check fails or is inconclusive, no distributional equivalence is claimed, the fresh-puzzle population is described as its own population, and the released boards remain the secondary stratum; the outcome is logged in `DECISIONS.md`; (5) CAL, PROBE-TRAIN, PROBE-VAL, SELECT, TEST and E4-TEST are generated only after the terminal gate, from the frozen generator.
- **Solver checks:** the uniqueness checker and full solver are own code, cross-checked against an independent second implementation (DLX / Algorithm X) at least on a sample.

## 5. Logical labels: candidate mask and inference depth

### 5.1 Initial state

Label for an originally empty cell $c$ and digit $d\in\{1,\ldots,9\}$:

$$
y_{c,d}^{(0)}=\mathbf{1}\{d\text{ does not appear among the filled row, column, or box peers of }c\}.
$$

This is the **nine-bit candidate mask under direct rules**, not the support set formed from all globally possible solutions. The latter would be a different, stronger label. A naked single is exactly the case where the number of active bits in the mask equals one; candidate count and naked single are therefore not independent evidence.

The hidden single is defined at the unit–digit level: a missing digit has exactly one candidate cell left in the given row, column, or box. We store the unit, the digit, and whether the same cell is also a naked single. Hidden-single-only cases can be reported separately.

The candidate mask is a richer label than the binary single indicator, but it measures a shallow rule. The label can be derived deterministically from the corresponding peer digit counts by thresholding. Hence a suitable raw-input or rule-based control may reach the ceiling. The latent probe is not required to outperform an exact rule implementation. The pilot measures the frequency of single labels; their rarity is not assumed in advance.

### 5.2 Deterministic, synchronous inference waves

The solver starts from the input and uses only naked/hidden single rules; no guessing and no digits taken from the reference solution.

1. $P^{(0)}=P$. Wave $k$ computes from the candidate masks of state $P^{(k-1)}$.
2. All applicable naked/hidden singles are identified simultaneously, before any new value is written.
3. Identical derivations may be merged. A conflicting derivation or a joint constraint violation is an input/implementation error signal; it is not resolved by arbitrary rule priority.
4. New values are written simultaneously. We record the depth of the cell's first determination $d(c)=k$ and the deriving rules.
5. Stop when there is no new fill. Cells not solved by the rule system get a "stuck" status, not a false-negative or zero-depth label. Under a technical step limit, the censored status is distinct from this.

The full solution may be used for input checking, but label construction does not read it. Wave index 1 is the first fill wave following from the initial state. The main secondary depth breakdown: 1, 2, 3, at least 4, stuck; each comes with sample size and label proportion.

The experiment may also measure the candidate mask of later $P^{(k)}$ states, only on cells still empty at that point, as a separate endpoint. The model always receives the original $P$; the solver's intermediate state is not fed back. Level $\ell$ of the model is not automatically identified with solver wave $k$.

## 6. E1 — Tokenizer, generator, and intermediate reconstructions

On the same puzzles we produce the teacher codes of the reference solution and the codes generated from the puzzle. We evaluate separately the full teacher reconstruction, the full generated output, and — with a validated path — the decoding of full-length cumulative states at every selected level.

The main output of E1 is a separate report of the tokenizer reconstruction error and the generation performance. Teacher reconstruction quality is **not a strict upper bound** on the generated output: a different code sequence may also decode to a correct solution. A mismatch between teacher and generated code indices is not a logical error by itself either.

Mandatory metrics: official reference match; own solve; valid-grid; clue preservation; cell accuracy on all cells and on originally empty cells; format error; rule violation; token and cell Hamming separately. Non-unique puzzles and serialization differences can also cause discrepancies between reference match and own solve.

Based on the code review, the definitions of the original `exact` and cell metrics must be audited separately: string matching is not a standalone Sudoku validator, and pairwise iteration over a truncated output produces a wrong denominator [9]. We keep the published metric for reproduction; the main scientific analysis relies on the independent validator.

## 7. E2 — Level sensitivity and four-branch compensation study

### 7.1 Four branches on the same puzzle

We record the full code sequence of the clean run. Codes before the intervention level are identical in every branch. The suffix means the codes of later levels.

| Branch | Intervention level | Later levels | Role |
|---|---|---|---|
| A | Original code | Original suffix replayed | Clean reference |
| B | Original code | Regenerated suffix | Sham restart |
| C | Perturbed code | Original suffix replayed | Direct decoding effect, without adaptation |
| D | Same perturbation | Regenerated suffix | Total intervention effect |

Let $Y_A,\ldots,Y_D$ be the binary solve outcome of each branch. The total effect is $E[Y_D-Y_A]$; the sham-relative version is $E[Y_D-Y_B]$. The compensation contrast:

$$
\theta_{\mathrm{comp}}=E[(Y_D-Y_C)-(Y_B-Y_A)].
$$

A positive value indicates more favorable adaptation relative to the fixed suffix. In a deterministic, correctly restarted run B=A; any difference is an instrumentation or numerical error signal. Branch C's residual codes do not necessarily fit the changed prefix, so improvement in D may be representational refitting. Because the puzzle prefix is available at every level, the result alone does not prove that the coarse code is an executable logical plan.

**Trained robustness.** NCM training includes corruption of earlier levels [1, App. F.3]; the upstream repository contains no generator training configuration, and the released checkpoints carry no training metadata (verified with pickletools on 2026-11-09), so the Sudoku checkpoints' training regime is cited from the paper only. A positive $\theta_{\mathrm{comp}}$ may therefore be a trained robustness property rather than spontaneous error handling. Generated codes may also be non-canonical [18]: a replaced code can be absorbed without a change in the decoded grid, so code-level Hamming is reported only next to cell-level change. The term "compensation" is related to, and kept distinct from, self-repair within a single forward pass [19].

### 7.2 Two separate questions: edit cost and initial damage

**Primary, equal-cost study:** uniform selection of one code position and its replacement according to the level's generated code frequency estimated on CAL, excluding the original value. Contrast of levels 1 and 11 of the hard checkpoint:

$$
\theta_2=E[(Y_{D,1}-Y_A)-(Y_{D,11}-Y_A)].
$$

Level 1 has a single code position, so the replacement is not sampled: all 15 alternative values are run and weighted by their CAL frequency, which gives the exact expectation over the policy without intervention-seed noise. For puzzle $i$ with original level-1 code $a_i$ the weight of value $v\ne a_i$ is $w_{i,v}=\hat f_v/\sum_{k\ne a_i}\hat f_k$, with $\hat f$ the frozen level-1 code frequencies from the CAL generated codes; a value with zero CAL frequency gets weight 0, and a puzzle is ineligible only when the denominator is 0. The same weights apply to every level-1 quantity: the level-1 term of $\theta_2$, $\theta_{\mathrm{comp}}$, damage and format-error summaries. TEST uses the frozen CAL vector. At level 11 a position and a value are drawn with three intervention seeds. The same contrast at levels 2 and 11, $\theta_2'=E[(Y_{D,2}-Y_A)-(Y_{D,11}-Y_A)]$, is secondary and is assessed against an equivalence range of ±3 pp (Section 11.4).

**Why level 1 (v3.6).** In the WP1 pilot on CAL (D42) replacements at the measured levels 2, 6 and 11 changed solve rates by at most about 1 pp, and under the frequency policy branch C at level 2 never differed from A in solve outcome. With the frequency policy, the single level-1 replacement lowered the solve rate from 0.850 to 0.763 in branch D (−8.7 pp, the branch H2 uses) and to 0.756 in branch C (−9.4 pp). The primary contrast was moved before the lock, on CAL data only, so that H2 tests the earliest level at the same edit cost; TEST is untouched. The change and its reason are logged in `DECISIONS.md`.

**Level 1 is architecturally distinct.** In this checkpoint the level-1 code passes through a learned level-1 upsampler (`learned_l1_sampling`) and is the only code of its level, so a single-code replacement changes the whole level-1 state. A level 1 vs. 11 difference therefore does not by itself imply a graded sensitivity along the early levels (Section 13).

A negative value means greater degradation at the early level. This is an equal number of discrete edits, **not equal semantic effect strength**. We report the differing vector norm, frequency, and conditional probability. If the frequency distribution has no alternative value, the case is not replaceable under this policy: we do not silently substitute uniform replacement. The level contrast runs on a common, predefined eligible population; the dropout proportion and the full population are shown separately.

**Secondary study matched on initial damage:** the direct decoded change is measured between C and A, before regeneration. The primary damage measure is the mean cell-wise total variation distance between the decoder's output distributions:

$$
d_{i,\ell,r}=\frac{1}{81}\sum_{c=1}^{81}\operatorname{TV}\!\left(p^C_{i,c},\,p^A_{i,c}\right),
$$

where $p_{i,c}$ is the softmax (temperature 1) of the decoder logits over the full 12-token vocabulary at the output position of cell $c$ (cell-to-position map `CELL_TOKEN_INDICES`), and $\operatorname{TV}(p,q)=\tfrac12\sum_t|p_t-q_t|$. Probability mass on non-digit tokens is therefore included. It is continuous, bounded in $[0,1]$, and defined for every run, including runs with a format error. The WP1 pilot showed why the cell Hamming distance cannot carry the matching: at levels 2–11 it was zero in at least 98% of perturbed runs (D42). The cell Hamming distance is still reported for well-formed outputs:

$$
h_{i,\ell,r}=\frac{1}{81}\sum_{c=1}^{81}\mathbf{1}\{\widehat S^C_{i,c}\ne\widehat S^A_{i,c}\}.
$$

Both are also reported over originally empty cells only. A latent diagnostic, $\lVert z^C-z^A\rVert_2/\lVert z^A\rVert_2$ on the final cumulative state, is recorded next to them. A re-quantization diagnostic (D26) records, per perturbation at level $\ell$: the per-position RMS norm of the replaced codebook-vector differences in the level's embedding space; and the residual $z^A-Z^C_{\le\ell}$ quantized with the codebooks of levels $\ell+1,\dots,12$, reporting the norm left after quantization relative to the norm of the residual (how much of the perturbation the later codebooks can absorb geometrically). It serves the interpretation of insensitive levels and is not an outcome.

The Hamming value is the cell Hamming distance from the clean generated output, not the error relative to the reference solution. The analogous distance measured on the teacher reconstruction may serve as a separate tokenizer control. With a format error the Hamming distance gets a separate status (the TV damage $d$ remains defined); the failed run stays in the solve denominator and does not automatically count as "low damage".

Perturbation policies and doses are chosen on CAL data, then the choice is frozen. The final TEST solve outcome cannot be used for fitting. Initial damage is a post-intervention variable, so the result conditioned on it is a **calibrated descriptive comparison**, not automatically a controlled direct causal effect. We compare not only the mean damage but the full distribution and the format error rate.

### 7.3 Dose curves and lack of overlap

The dose is the number of positions replaced at a level. The first pilot's candidate grid, with duplicates removed, was $0,1,\lceil0.05n_\ell\rceil,\lceil0.15n_\ell\rceil,\lceil0.30n_\ell\rceil$, where $n_\ell$ is the level's code length. Because levels 2–11 were insensitive up to 30% of positions (D42), the grid from v3.6 on is $0,1,\lceil0.05n_\ell\rceil,\lceil0.15n_\ell\rceil,\lceil0.30n_\ell\rceil,\lceil0.60n_\ell\rceil,n_\ell$ (level 6: 1, 2, 4, 8, 13; level 11: 1, 4, 11, 21, 41, 67; level 2: 1, 2; level 1: 1). On short coarse levels, several distinct nonzero doses therefore do not necessarily exist; level 1 has a single nonzero dose, which provides the primary H2/H3 contrasts, not a dose curve.

Per level we plot the solve change as a function of edit count and of initial damage $d$. Areas under the curve are comparable only over a **common range pre-specified on CAL and checked with diagnostics on TEST**, with identical integration rule and weighting. The rule (v3.6): AUC comparisons are pairwise (levels 6 vs. 11 and 2 vs. 11) and only for levels with at least two nonzero doses, so level 1 is excluded. Under the frequency policy, each dose $k$ of level $\ell$ gives one node $(\bar d_{\ell,k},\overline{\Delta Y}_{\ell,k})$: the mean damage and the mean solve change $Y_D-Y_A$, averaged first within puzzle over seeds, then over puzzles. Nodes with equal mean damage are merged by averaging their solve changes. Each curve is the piecewise-linear interpolation of its nodes ordered by $\bar d$ and needs at least two distinct damage values; otherwise no AUC is computed for that pair. The common range is $[\max_\ell\min_k\bar d_{\ell,k},\ \min_\ell\max_k\bar d_{\ell,k}]$ over the pair, so no curve is extrapolated; the area over it is integrated exactly on the piecewise-linear curves and divided by the range width. An AUC is computed only if the range has positive width. The range is fixed from the second CAL pilot before the lock and checked on TEST; if TEST nodes do not cover it, no AUC is reported for that pair. No extrapolation to unobserved small coarse perturbations. Without overlap we publish separate sensitivity curves; the equal-damage level contrast is not estimable. Slope can only be a local, secondary summary.

Further perturbations: uniform code replacement; equal numbers of contiguous or scattered positions, where topology justifies it; validated donor policy. Matching the marginal code frequency or vector norm does not guarantee that the replacement remains natural given the puzzle and prefix.

**Continuous perturbation:** optional separate experiment. Noising the tokenizer's pre-quantization representation tests the tokenizer; it is not the same as discrete code replacement in the generator. For continuous modification of an activation or codebook contribution inside the generator, the intervention site, norm, direction, any requantization, and the continuation method must be recorded. It cannot be used to retroactively fill the missing overlap of the discrete experiment.

### 7.4 Propagation diagnostics

We save the code changes of later levels, the separately copied full-length cumulative states, and the available intermediate decodings. Errors are tracked on a level × cell map, along row/column/box relations, and separately on originally empty versus given cells. We report if only the final sensitivity is estimable. Cases starting from a correct baseline form a separate secondary breakdown; the primary effect is not narrowed post hoc to successful baselines only.

## 8. E3 — Readability, depth, and equivariance

### 8.1 Primary representation and probe

The primary representation is the full-length cumulative $Z_{\leq\ell}$ state of the generated branch. In G0 we fix the serialization's cell–token mapping and read out the position embedding assigned to the given cell. This is a technical position assignment; it does not prove semantic locality of the latent information.

All E3 probes are **linear models shared across cells with nine sigmoid outputs** and a cell-position one-hot (81). They are trained with BCE loss and AdamW over the grid weight decay {0, 1e-4, 1e-3, 1e-2, 1e-1} × learning rate {1e-3, 3e-3}, with three training seeds (0, 1, 2) and early stopping on the PROBE-VAL Brier loss (D55). Each probe trains for max(50 epochs, enough epochs for at least 2,000 optimizer steps) at batch size 4,096 (D63). The configuration is selected by the mean PROBE-VAL Brier loss over the three seeds. Brier-based endpoints ($\theta_1$, $\theta_T$, controls, depth breakdown, equivariance Brier) average the three seed models' puzzle-level Brier losses (not the Brier loss of the seed-averaged prediction); thresholded and ranking metrics (F1, PR-AUC, exact match, ROC-AUC) use the seed-averaged predictions. Best epoch, epochs run, optimizer steps, whether the best epoch hit the cap, and the trainable parameter count are reported per configuration and seed. Three training seeds are repeated fits, not three times as many independent puzzles. The secondary MLP has 64 hidden units on the same grid.

**Primary H1 probe: cell-relative whole layer (v3.7, D66, D68).** Levels below 12 reach the 89 token positions only by interpolating $n_\ell$ points, so the state at one cell's position may miss information held elsewhere in the layer. The primary H1 input for cell $c$ is therefore built from the states of $c$ and its 20 peers (same row, column, or box) in a fixed peer order (`grid.PEER_ORDER`, hash in Section 12.2):
 these $21\times256$ values
 are projected by a PCA with 256 components fitted on the originally empty cells of PROBE-TRAIN only, and the scores are whitened to unit PROBE-TRAIN standard deviation. PCA details (`src/ncm_sudoku/wholelayer.py`): covariance with divisor $N$ (rows = empty cells), accumulated in float64; components ordered by decreasing eigenvalue; each component's sign is set so that its largest-magnitude entry is positive; whitening divides by the square root of the eigenvalue, and a component whose eigenvalue is at most $10^{-10}$ times the largest gets scale 1. The same PCA, fitted on PROBE-TRAIN only, is applied to PROBE-VAL and TEST. The probe input is the whitened scores, the cell's own state, and the position one-hot. A global vector shared by all cells of a puzzle is not used: a shared linear probe could use it only as a per-puzzle offset, which measures surface information (D66). The **per-cell probe** (own state and position only) is a secondary H1 analysis. A budget sensitivity run with three times the optimizer steps changed the level-6 PROBE-VAL estimate by 0.00004 (D69), so the D63 budget is kept.

**Why the primary probe changed (v3.7).** v3.6 allowed a whole-layer probe only if the cell state was inaccessible. The switch to the cell-relative whole-layer probe, and the two-sided form with an equivalence range (Section 8.3), were made after the per-cell PROBE-VAL estimate came out near null (0.0018, D64) and the whole-layer diagnostic gave 0.0031 (D67), with TEST untouched. Both changes make an absence claim harder to obtain: the primary probe is the stronger readout, and equivalence must be shown, not inferred from non-significance. The per-cell probe stays as a secondary H1 analysis, so the original specification is still reported. The change and its reasons are logged in `DECISIONS.md` (D65–D68).

Control seeds: the permuted control permutes PROBE-TRAIN with seed 11 and PROBE-VAL with seed 12; the random-feature and label-permutation controls use seed 0. The configurations selected on PROBE-VAL by the rule above were weight decay 0.1 with learning rate 1e-3 for the whole-layer probes at levels 6 and 12 (generated and teacher) and weight decay 0 with learning rate 3e-3 for both raw-input controls (D67); WP2 reruns the selection with the same deterministic procedure and reports any difference.

The raw-input control uses the same construction on the puzzle: the cell's own one-hot and its 20 peers' one-hots (210 values), reported both projected (whitened PCA, all 210 components) and **unprojected**. On PROBE-VAL the projected version reached a Brier loss of 0.0014 and the unprojected 0.0105 with the same information, so the unprojected raw control is budget-limited and both are reported (D67). We do not train 81 independent per-cell classifiers and select among them post hoc.

Residual level code, cumulative state, and transformer activation are separate experimental conditions. They are not merged under a common "coarse representation" label. A probe result on an activation that sees the full puzzle directly is not automatically a result about the narrow discrete code sequence.

### 8.2 Controls

| Control | What does it isolate? | Requirement |
|---|---|---|
| Raw puzzle, linear and small MLP readout | The representation's advantage over trainable input readout | Same data, training budget; parameter count and capacity difference reported |
| Peer digit counts and exact rule implementation | Shallow, direct computability of the initial mask | Ceiling reference; not evidence of a learned mechanism |
| Clue count, cell position, global digit frequency | Surface correlations | Standalone result |
| Permutation of representations across puzzles | The learnable link between puzzle and representation | Within PROBE-TRAIN/VAL, with pre-specified clue stratification; the full grid structure stays together |
| Random, size-matched feature | Effect of the training setup and chance fit | Same training cost |
| Label permutation control | The probe's capacity and memorization tendency | No transferred pairing across train/val/test; control task precisely documented |
| Teacher representation | Difference between solution content and puzzle state | Separate report; also checked with different clue masks of the same solution |

Null controls cannot be selected post hoc based on which is easiest to beat. The primary control for H1 is a probe retrained with the same procedure on representation–label pairs permuted across puzzles. Permutation is done on train and val data, independently of each other; the final comparison for both probes is on the untouched TEST pairs. Thus the control creates no new dependence among test puzzles. The permuted-control probe selects its regularization and early-stopping point on its own independently permuted PROBE-VAL split, so weights on the representation can shrink to zero; a cell-position marginal baseline, with probabilities estimated on PROBE-TRAIN and its Brier loss evaluated on the same TEST cells with the Section 8.3 aggregation, is reported alongside. The raw-input and rule-based results appear in the same main table. A training-size curve is required to judge whether the difference is mainly explained by the readout's data requirements.

### 8.3 Endpoints

The primary metric for the initial candidate mask is the **Brier loss**: the squared probabilistic error of the nine bits is averaged first per cell, then per puzzle over originally empty cells, finally across puzzles. Thus more empty cells do not automatically get more weight.

Primary effect size of H1 at level 6:

$$
\theta_1=E[B_{\mathrm{permuted}}-B_{\mathrm{generated}}],
$$

where a positive value indicates better generated readout. $B$ is the Section 8.3 Brier loss of the primary cell-relative whole-layer probe (Section 8.1); the permuted control uses the same construction, and the permutation moves a puzzle's whole input block (all 81 cells) to another puzzle's labels.

**Form of H1 (v3.7, D65, D68).** H1 is a two-sided primary contrast with a pre-specified equivalence range of ±0.01 Brier (the D60 practical threshold). Two pre-specified readings are made from the same estimate: (1) $\theta_1\ne0$ when the 98.33% family interval (Section 11.1) excludes 0; (2) practical equivalence, i.e. readability below the practical threshold, when the 96.67% interval (two one-sided tests at $0.05/3$ each) lies inside $(-0.01, 0.01)$. Both can hold at once; the expected outcome from PROBE-VAL is a small positive $\theta_1$ inside the range (PROBE-VAL preview 0.0031, Section 12.1), which is reported as "readable above the null control but below the practical threshold". The relative improvement $\theta_1/E[B_{\mathrm{permuted}}]$ is reported alongside.

**Secondary contrast at level 12 (D65).** $\theta_T=E[B_{\mathrm{teacher}}-B_{\mathrm{generated}}]$ at level 12, both with the whole-layer probe, assessed against an equivalence range of ±0.01 with a 90% TOST interval. It is outside the primary family. Equivalence means that there is no practically meaningful difference, within the pre-specified ±0.01 range and for the examined probe family and budget, between the level-12 readout of the generated representation and that of the teacher's solution representation (PROBE-VAL preview 0.0003).

**Level choice.** $Z_{\leq\ell}$ is a deterministic function of the discrete codes of levels $1..\ell$, each with 16 values. $Z_{\leq 2}$ is built from 3 codes, i.e. at most 12 bits and 4,096 distinct states, far below the information in a full candidate mask. Level 6 (1+2+4+6+9+13 = 35 codes, at most 140 bits) is therefore the primary H1 level. This is a pragmatic capacity choice; neither bound predicts readability, since partial information can improve the Brier loss at level 2 and 140 bits need not suffice at level 6. The same $\theta_1$ is reported at level 2 as a pre-specified low-capacity comparison and at level 12 (89 codes) as a secondary full-resolution comparison, because levels below 12 reach the 89 token positions only by interpolating $n_\ell$ points (13 at level 6). Neither is part of the primary family. The primary level is fixed at 6 by this lock version; the per-cell probe gives a secondary $\theta_1$ at the same levels.

The raw-input difference is a separate estimate; a positive H1 cannot be called an advantage over the raw input unless the latter comparison supports it.

**Secondary exploratory target:** unit–digit labels over the 27 units × 9 digits, comparable with [16], where unit-level probes reached perfect exact match while per-cell candidate probes did not. Fixed definition (D62, from a primary-source extraction of [16]): the label is "digit $d$ is already placed in unit $u$ on the initial board" (27 × 9); the readout is the mean of the unit's nine cell states with a unit one-hot (27), one linear probe shared across units with nine sigmoid outputs, same grid, budget and seeds as Section 8.1. Metrics: exact match (all nine digits correct), ROC-AUC, and Brier loss, with the raw-input control next to them. The global single-token readout of [16] has no counterpart in this model and is not replicated. It is not part of the primary family.


Secondary metrics: per-digit and macro F1; PR-AUC computed for the positive class; full candidate-mask match; candidate-count MAE; naked single derived from the mask; separate hidden single; depth breakdown. Every PR-AUC is accompanied by the positive label rate. If the positive or negative class is missing, the affected metric is not interpretable, not zero. The probability threshold is fixed at 0.5 for every thresholded metric.

The analysis targeting solver depth is a separate task: for example, whether an originally empty cell is determined by wave 2 or 3 at the latest. Stuck case status is preserved. Per depth, we compare the latent and the raw-input readout; given differing label frequencies and sample sizes, we do not infer a deeper algorithm from a bare F1 ranking.

### 8.4 Symmetries and generalization

For per-cell or per-digit outputs the appropriate requirement is **equivariance**: rearranging the grid also rearranges target cells, digit channels, and labels. Invariance is meaningful for a scalar over the full grid. We bring predictions into common coordinates with the inverse transformation and measure both the deviation and the predictive performance.

**Equivariance analysis (v3.7, D68, D70): exploratory, at level 12.** At level 6 the probe is at the level of the permuted control, so a deviation there is mostly noise (D64). The analysis therefore uses the level-12 whole-layer probe (Section 8.1; PCA and three seed models fitted on PROBE-TRAIN and PROBE-VAL). Each of the TEST puzzles with indices 0–199 in TEST generation order gets 8 group elements — 4 from the full group, 2 digit-only and 2 geometric-only — drawn interleaved per puzzle from one `default_rng(0)` stream; transformed puzzles are generated through the model, predictions are back-transformed, and we report the mean absolute deviation from the untransformed predictions over originally empty cells, the share of puzzles within the acceptable deviation, and the Brier loss on transformed vs. untransformed puzzles. The acceptable deviation is fixed at 0.0116 and passed to the analysis as a constant (it is not recomputed on TEST; the TEST seed-noise percentile is reported alongside), the 95th percentile of the deviation between the three seed probes on 200 PROBE-VAL puzzles (D71). On PROBE-VAL the mean deviation was 0.079 for the four full-group elements, 0.066 for the two digit-only and 0.077 for the two geometric-only elements (each category averaged separately; 0% of puzzles within the tolerance in every category) while the Brier loss was unchanged (0.1828 vs. 0.1828), so the expected TEST outcome is "as accurate, not equivariant at seed-noise tolerance". This is not part of any confirmatory family.

This lock specifies only the first kind of result: a probe trained without augmentation, tested on new transformations. Generalization of a probe trained with augmentation is not part of this registration. Transformed grids are re-run through the model; we do not merely permute the old representation. A family holdout is not possible, because every puzzle is generated independently (Section 4.1); all puzzles have 30 clues, so a clue-count holdout does not apply either, and the depth breakdown (Section 8.3) is descriptive.

## 9. E4 — Targeted causal study, conditional

### 9.1 Entry condition and target variable

E4 may start if G0 is validated, there is a reproducible and interpretable logical readout on the SELECT data, equivariance is acceptable, enough target cells and independent puzzles are available, and the chosen outcome is not entirely at floor or ceiling. The required practical effect size and the numerical form of these conditions are fixed based on the target variable, pilot variance, and cost, before E4-TEST is opened.

**We do not apply a universal +0.10 macro-F1 threshold over the raw-input baseline.** Neither a general statistical argument nor the task ceiling justifies it. If there is no adequate target variable or sample size, E4 is dropped; E1–E3 can be evaluated on their own.

On a fixed input, the "naked single" label does not change under an internal patch. The causal outcome is therefore the **emission of the correct, rule-forced digit in a preselected, originally empty target cell**, not a recomputation of the label derived from the input.

### 9.2 E4a: corruption and restoring patch on the same puzzle

On the SELECT set we choose the region linked to the logical property and the corruption mode. On fresh E4-TEST puzzles we produce a clean and a corrupted run. Into the designated region of the corrupted run we copy back representation **from its own clean run**, then continue generation from the same point.

Control branches: clean baseline; corruption without patch; targeted restoring patch; restoring a control region of equal size and similar norm; a random or other-target pre-specified patch. For any intervention along a probe direction, a size- and norm-matched random-direction intervention is an additional mandatory control [17]. Two independent factors describe a patch. **Route:** generator-mediated, where a continuous change to $Z_{\leq\ell}$ or $H_\ell$ reaches the output only through the argmax over downstream discrete codes (the upstream evaluation decodes from discrete codes), or decoder-input, where a continuous change is passed directly to the VQ-VAE decoder. **Geometry:** region patch or probe-direction patch. The Hamming distance of downstream codes is reported for generator-mediated patches and marked not applicable where no downstream codes exist. On SELECT, exactly one route × geometry combination is frozen as the E4 primary contrast, with one comparator: the equal-size control region for a region patch, or the mean over a pre-seeded set of $K$ norm-matched random directions, with fixed distribution and sign, for a probe-direction patch. All other combinations and controls are secondary. The target region and control are not chosen based on the final test effect. Copying the clean state into itself is only a no-op test, not a causal experiment.

The primary contrast is the difference between targeted and control restoration in target-cell correctness. If the number of target cells differs across puzzles, we first average within puzzle. The secondary endpoint is the decoder's digit-logit margin for the target cell:

$$
m_c=z_{c,d^\ast}-\log\sum_{d\ne d^\ast}\exp(z_{c,d}),
$$

where the set contains only the nine digits; the probability of non-digit outputs and format errors are measured separately. The generator's logits over 16 code categories are not the same as the final decoder's digit logits. The logit endpoint is usable only with a verified cell–token–digit mapping.

We measure changes in non-target cells, clue violations, valid-grid, solve, norms, and available distributional diagnostics. The clean–patched activation distance (site, tensor, norm, and normalization fixed on SELECT) is reported for every patch, because interaction effects in patching grow with this distance [20]; large-distance patches are interpreted cautiously. These results are not used for post hoc exclusion of unfavorable test cases. A precisely localized ablation supports at most the causal relevance of that region; semantic mediation along a probe direction is a stronger claim.

### 9.3 E4b: minimal counterfactual puzzle pairs

As a second step, $P^-$ and $P^+$ pairs can be built that differ by 1–2 clue edits and produce, in a preselected cell $c^\ast$, a candidate change such as $\{2,5\}\rightarrow\{2\}$. We verify the consistency and uniqueness of both puzzles, that the target cell is empty, and the exact target change.

First we use pairs with a shared solution. **In this case the correct digit does not change**: in both members of the example the solution may be 2. The expected effect is a shift in internal evidence or output margin for 2; a response switch from 5 to 2 is not necessary. At ceiling, a missing shift is not by itself negative mechanistic evidence.

Adding a clue also changes the clue count. Where feasible, we keep it constant with a two-edit clue relocation; otherwise matched control pairs with the same clue-count change are needed. The control edit does not cause the selected candidate change in the target cell.

Donor and recipient digits, positions, and representation indices are aligned. Proximity of the natural endpoints does not guarantee that the post-patch hybrid state is in-distribution. We report the pair construction success rate, all prior exclusions, and the global damage after patching. Pairs with different solutions, targeting an actual response switch, require a separate protocol.

The exact target model and directed contrast of E4b are fixed after the pair pilot. The claim "the logical variable mediates generation" can be considered only if the intervention alignment, the negative controls, and the examination of alternative explanations separately support it [12–13].

## 10. Shared metric glossary and error handling

| Metric | Fixed meaning |
|---|---|
| Official exact match | Reference match according to the original evaluator; reproduction endpoint |
| Solve rate | Well-formed, complete grid, preserving every clue and with all 27 Sudoku units correct |
| Valid-grid | Well-formed complete grid with valid rows/columns/boxes; separate from clue agreement |
| Clue preservation | Proportion of given cells preserved, and separately the proportion of grids preserving all clues |
| Cell accuracy | Fixed 81-cell denominator; separately also on originally empty cells; reference and serialization rule documented |
| Constraint violations | Number of incorrect rows, columns, and boxes on a well-formed grid, 0–27 in total; format error is a separate status |
| Cell Hamming | Proportion of differing cells between two pre-named grids; separately for all and for originally empty cells |
| Token Hamming | Differences at token positions; does not replace cell-level distance |
| Target-cell correctness | Emission of the forced correct digit in the pre-designated, originally empty target cell |
| Brier, F1, PR-AUC | With the exact label, aggregation, positive class, and threshold stated |

A model output with a format error has solve=0 and valid-grid=0; it is not removed from the main denominator. Cell accuracy can be computed partially if the pre-specified parser unambiguously identifies positions: missing/invalid positions count as errors, the denominator stays 81. If positions cannot be assigned unambiguously, strict cell accuracy is 0 and the format error is reported separately. No solver-based repair or post hoc clue write-back.

An infrastructure error — such as an interrupted GPU run — differs from a model error. The pre-specified rerun rule is identical for every branch. For permanently missing outputs we report the cause and proportion of missingness; we report the number of groups dropped from the paired main analysis and the resulting limitation. Model errors are not reclassified as technical errors.

## 11. Statistical plan

### 11.1 Unit of estimation and uncertainty

The main estimand is the average paired effect in the selected puzzle population. Cells, levels, perturbation repetitions, and training seeds are not independent puzzles. We first average within puzzle with pre-specified weights, then across puzzles. If several puzzles or transformations come from one family, the highest shared family/orbit is the resampling unit. The probe interval is conditional on the fixed training set and fitted models; stability across training seeds is reported separately and not mixed with the sampling uncertainty of test puzzles.

The primary interval procedure is a cluster bootstrap with 10,000 resamples that keeps related branches, pairs, and repetitions together. The bootstrap also preserves stratified sampling. Alongside the reported two-sided individual 95% intervals, for the three contrasts of the primary family we give Bonferroni intervals targeting 5% family-wise error control, each with 98.33% nominal coverage:

1. H1: $\theta_1$, the level-6 initial candidate-mask Brier improvement of the cell-relative whole-layer probe relative to the fixed null control; two-sided, with the family-level equivalence reading of Section 8.3.
2. H2: $\theta_2$, the solve contrast of single-code perturbation at levels 1 and 11.
3. H3: $\theta_{\mathrm{comp}}$, the four-branch interaction of the level-1 single-code perturbation.

The interval variant is the percentile cluster bootstrap with 10,000 resamples (fixed in v3.6 from the pilot); rare events follow the rule in Section 11.2. Limitations of approximate coverage with few clusters are reported. Other levels, doses, probes, and labels are secondary/exploratory; they will not be turned into primary positive results post hoc. H4 estimates performance and deviation; it does not test a universal invariance theorem. E4 gets its own primary contrast examined on fresh data.

### 11.2 Paired binary outcomes

For a single binary baseline–intervention pair, let $b$ be the count with baseline=1, intervention=0, and $c$ the count with baseline=0, intervention=1; $n$ the number of independent pairs. Then

$$
\widehat\delta=\frac{c-b}{n},\qquad
\widehat q=\frac{b+c}{n}.
$$

Asymmetry between the directions can be examined with the **exact McNemar test** [14]. We use it only for a pre-designated single binary pair per independent unit. We do not apply it to perturbation averages, the four-branch interaction, or repeated copies of the same deterministic baseline.

Discordant pairs matter, but statistical power is not determined solely by their number: the ratio of directions, the effect, the sample size, and the dependence structure also matter. For independent pairs, with $\delta=E[Y_D-Y_A]$ and $q=P(Y_D\ne Y_A)$, as our own derivation:

$$
\operatorname{Var}(\widehat\delta)=\frac{q-\delta^2}{n}.
$$

This is not applied unchanged to grouped, multi-repetition data. With zero or very few discordant pairs the usual bootstrap can degenerate. In that case we report the discordance count and an uncertainty bound; a pre-selected small-sample interval procedure is required. **Rule (v3.6):** in E2 the independent unit is the puzzle, because each puzzle comes from its own independently generated group (Section 4). When fewer than 20 puzzles have a nonzero puzzle-level difference (seed- or weight-averaged, so in $[-1,1]$) in a contrast, the bootstrap interval is replaced by the conservative bound $|\delta|\le q$, where $q$ is the share of puzzles with a nonzero difference and its one-sided Clopper–Pearson upper limit is taken at level $1-0.05/3$ for primary contrasts and $0.95$ otherwise. The bound always holds for averages of per-unit differences in $[-1,1]$ and never has zero width; the coverage of the bootstrap-or-bound switch is checked in the planning simulation (Section 11.4). We do not claim equivalence based on a zero-width empirical bootstrap interval.

### 11.3 GLMM: supplementary analysis

The supplementary model examining several levels and doses jointly can be a binomial mixed-effects regression with logit link [15]. Fixed effects are level, dose, branch, and their pre-designated interactions; the random structure handles within-puzzle repetition and, if needed, the shared family. With estimable data volume, relevant random slopes may be included.

The model formula, reference categories, and simplification order are fixed in advance. Convergence failure, singularity, or separation is reported; we do not choose a model tuned to significance. The deterministic baseline remains one observation, not an independent row duplicated for every dose. Alongside the odds ratio we give a model-standardized **probability difference**; the odds ratio is not a percentage-point solve change. The clustered paired analysis remains primary.

### 11.4 Sample size, effect threshold, and stopping

A few hundred independent pilot puzzles can provide planning data, but are not proven sufficient. The confirmatory sample size is determined from the desired minimal practical effect, the expected interval width, the discordance and family dependence measured in the pilot, preferably by simulating the entire planned procedure. The different endpoints of E3 and E4 require separate calculations.

The calculation must include multiple comparisons, the expected eligible target cells, the number of perturbation repetitions, and any loss in counterfactual pair construction. **Thresholds and calculation (v3.6).** Minimal practical effects: 5 pp for H2 ($\theta_2$), 3 pp for H3 ($\theta_{\mathrm{comp}}$); the secondary levels 2 vs. 11 contrast uses an equivalence range of ±3 pp. The TEST size is found by resampling puzzle-level outcomes from the second CAL pilot and simulating the whole procedure (estimators, percentile cluster bootstrap, Bonferroni intervals, rare-event rule) under the target alternatives, not under the observed pilot effect. Every simulated sample keeps puzzle-level differences in $[-1,1]$ and their zeros, and runs the actual bootstrap-or-bound switch of Section 11.2. H2 uses two pre-specified scenarios: (a) thinning — each nonzero puzzle-level difference is kept with probability $0.05/|\hat\theta_2^{\mathrm{CAL}}|$, otherwise set to zero; (b) sign-mixing — the pilot's absolute differences are kept and each nonzero one is given the sign of the pilot effect with the probability that makes the expected effect 5 pp, which keeps the pilot's discordance and gives a larger variance. If $|\hat\theta_2^{\mathrm{CAL}}|\le0.05$ the observed differences are used unchanged and the shortfall is reported. For the levels 2 vs. 11 equivalence claim the null scenario multiplies each pilot puzzle-level difference by an independent random sign (zeros stay zero, the expected effect is 0); equivalence is declared when the two-sided 90% interval (TOST at 5% per side) lies inside ±3 pp, and the error rate of that rule is also checked with the differences shifted to the ±3 pp boundaries by the same sign-mixing. Targets: 90% power for H2 at 5 pp with the Bonferroni interval; an H3 interval half-width of at most 3 pp in at least 80% of simulated runs; 80% power for the equivalence claim. The TEST size is the largest of these E2 requirements, over both H2 scenarios, and the H1 requirement from the E3 preparation (Section 12.1), rounded up to a multiple of 100; it is fixed once, at the lock.

**Values fixed at the lock (v3.7, D53, D60, D70).** The TEST size is **600 puzzles**. E2 requirements from the second CAL pilot: H2 200 (thinning) and 400 (sign-mixing), H3 300, equivalence 600 (D53). H1: at the 0.01 threshold 100 puzzles suffice (D64); the family-level TOST of Section 8.3 has simulated power 1.000 at $n=600$ both at a true $\theta_1$ of 0 and at the PROBE-VAL mean 0.0031, and a false-equivalence rate of 0.016 (+0.01) and 0.014 (−0.01) (500 simulated samples, 2,000 bootstrap resamples; `experiments/lock/power.json`). The levels 2 vs. 11 equivalence rule was checked at its boundaries by an injection scenario, because sign-mixing cannot reach ±0.03 from the pilot (mean absolute puzzle-level difference 0.0100 < 0.03): zero puzzle-level differences are set to ±1 at random so that the expected effect is exactly ±0.03. Its false-equivalence rate at $n=600$ is 0.025 at +0.03 and 0.036 at −0.03 (Monte Carlo SE 0.003–0.004, 2,000 simulated samples), both below the nominal 0.05; 7–11% of these samples fall below 20 nonzero differences and use the conservative bound of Section 11.2. The injection uses whole ±1 puzzle-level jumps, so it is a low-discordance boundary check; boundary alternatives with more, smaller differences were not simulated. All simulations are planning outputs on CAL or PROBE-VAL data, not evidence for any hypothesis.

No outcome-dependent early stopping or repeated testing without a new rule.
 A non-significant result is limited evidence; claiming absence of a practical effect requires a pre-specified equivalence range and adequate precision.

## 12. Execution plan and lock points

### 12.1 Narrow first pilot

The scopes below were the proposed work-organization starting points; the rows marked "Done" record the outcome, and the values fixed at the lock are in Section 12.2.

| Step | Initial scope | Verifiable output |
|---|---|---|
| Technical trial | One hard checkpoint; about 20 different puzzles | Parser, validator, tensor shapes, no-op and sham match |
| G0 reproduction | The checkpoint's original evaluation set and settings | Original and own metrics; causes of discrepancies; environment record |
| E1–E2 pilot | About 300 puzzles, one from each independent group; levels 2, 6, and 11; single-code replacement first | A/B/C/D branches and paired contrasts |
| Perturbation repetition | Initially 3 intervention seeds | Variance of position and replacement choice; with argmax there is no artificial generation-seed variance |
| Dose calibration | Available discrete doses on CAL; frequency-based, then uniform policy | Overlap range or its absence; cost |
| Second E2 pilot (v3.6) | Same 300 CAL puzzles; levels 1, 2, 6 and 11; extended dose grid; TV damage, latent and re-quantization diagnostics; level-1 enumeration | Done (D53): θ₂ −0.089, θ_comp +0.007, θ₂′ +0.001 (rare-event bound ±0.030); E2 requirement 600 |
| E3 preparation | Solver waves, label and depth collection; probe and baseline training-size curves | Done (D64, D67, D69): level-6 θ₁ preview 0.0018 per-cell and 0.0031 whole-layer (threshold 0.01); level 12 0.050, equal to the teacher; flat training-size curve; budget sensitivity +0.00004 |
| Lock preparation (v3.7) | Boundary error rates, H1 TOST power, TEST generation and screen, level-12 acceptable deviation | Done (D71) |
| Confirmatory lock | Every item of the next table filled in | Dated protocol and untouched TEST |
| E4 pilot | Only after the gate is met, on SELECT | Concrete target, region, control, margin, and new sample size |

300 puzzles × 3 levels × 1 dose × 1 replacement policy × 3 repetitions gives **2,700 perturbation settings**; this is our own planning product, not 2,700 independent data points and not a runtime estimate. Branches C and D differ in cost; the clean A result is reusable. The size of the full dose grid must be computed from the distinct doses actually available at each level.

### 12.2 Preregistration lock checklist

| Item | Decision | Value fixed at the lock (v3.7) |
|---|---|---|
| Model | Hard checkpoint; pinned code commit; two-part G0 acceptance rule | `hazyresearch/ncm-checkpoints` revision `d342ce8aaea58830eef3b8ad473664673e41f692`; `sudoku/hard/generator.pt` SHA-256 `9e0bfe44abc1ca3930b7a63cd56cd0b9564b95e29edfe12dd0903207b89df8b8`, `tokenizer.pt` `3bc6aecad8e15820f9d9bb09750e3c59bdf91ca953f1f11dbd109aaed1d80c0b`, `config.yaml` `8d58c49e6fe52e60191e06df4061937d5bb84f97c5ffbcd93ed9830c32f8df2f` (MIT); upstream commit `c70274273f489abc73832b2b98584a8483b6b203`; G0 passed: official solve 86.3% vs. 86.1%, all 17 identity checks true (D31); environment: native Windows, CPU, FP32, eager, deterministic algorithms, recorded per run |
| Data | Grouped split; unique solutions; released 2,000 hard boards for G0 and as a secondary stratum; own 30-clue generator for all other subsets (Section 4.1) | Generator gen-v1 frozen (numpy 2.5.4; `generate.py` SHA-256 `57a8bfe55767c3e0be450307d5a09a390e13fa5aabe884ed826e200276d2a2ec`, `solve.py` `9f3e6df5ca6e0c91c448c459cb164c398ada77c462308d9bc2e07043948c0e5e`); distribution gate passed (D41); seed namespaces gate 1, CAL 2, PROBE-TRAIN 3, PROBE-VAL 4, SELECT 5, TEST 6, E4-TEST 7; every puzzle is its own group (independent generation); exact canonical-form screen over gate, CAL, PROBE-TRAIN, PROBE-VAL, TEST and released (6,400 grids): 0 symmetry classes, 0 duplicates (D71); **TEST = 600 puzzles**, ids SHA-256 `6e019563448e73408cd24a7ae207f5fd2549f0c881e70a37348d06f21ad6f09e`, puzzles `e9e714c83f333922e55ba36998343e1e0ffa73a75c52e8531f0bf5bed943c886`, solutions `08b333165f081f8c74d6d558372dc02cbb8d4dc35aac40b5da0ac699031fe471` (ids: `json.dumps(ids)` over the ids in generation order, default separators, ASCII, UTF-8; puzzles and solutions: uint8 arrays of shape (600, 81), C order, raw bytes, 0 = empty); released set: `hazyresearch/ncm-datasets` revision `6580ba41a4b0a976dde876fbe84d25327617b0e6`, `sudoku/hard/puzzles.pickle` SHA-256 `dd7b6763e5594094a1366ac8423f87fc9431056721c61df52ce3490023f17d5e`, `solutions.pickle` `b52de75f5e4642adca58b18967bcd4bbcafa699c61b21ac33ee0fd7389e0d576`; no model has been run on TEST |

| Logical label | Initial candidate mask; synchronous single waves secondarily | `src/ncm_sudoku/labels.py` SHA-256 `495f9d8b28bbd22dbdf1b4991935fa2ce23db607497bf9253eaf11abb8d517e6`; PROBE prevalence about 0.37 positive bits, 3.3 candidates per empty cell (D64); depth strata waves 1, 2, 3, ≥4, stuck |
| E2 main contrast | Single-code replacement, level 1 vs. 11 (level 2 vs. 11 secondary, ±3 pp equivalence); compensation at level 1; level-1 enumeration weighted by CAL frequency | Frozen CAL generated-code counts per level (values 0–15; `experiments/lock/cal_freqs.json`, SHA-256 `0cc7292718750754baf27b813a4095e2a7479cf4e480fbed50e43c665c7983fb`
; level 1 equals the pilot-2 vector): level 1 (300 codes): 29, 34, 0, 31, 0, 22, 3, 36, 0, 1, 20, 43, 0, 29, 25, 27; level 2 (600): 0, 0, 47, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 553; level 6 (3,900): 184, 156, 223, 183, 314, 226, 358, 188, 226, 0, 517, 344, 139, 152, 350, 340; level 11 (20,100): 17, 1548, 620, 1727, 1461, 636, 1991, 1000, 2112, 725, 1618, 586, 1674, 1736, 608, 2041. The confirmatory E2 run passes these frozen frequencies to the runner (`e2p2.run_pilot2(frozen_freqs=...)`) and never re-estimates them on TEST. A puzzle is ineligible only if all its alternatives have zero frequency (at level 2 the frequency policy can only draw replacement values 2 or 15)
; level 11: three intervention seeds 0, 1, 2 with generator seed `perturb.run_seed(level, policy, dose, seed)` (first 8 bytes of SHA-256 of "level|policy|dose|seed", little-endian, shifted right by 1); bootstrap resampling seed 0; frequency policy primary, uniform secondary; validated wrapper (D31) |
| E2 dose curve | Initial C–A damage as mean cell TV; common range rule (Section 7.3) | Dose grid of Section 7.3; common range 6 vs. 11: [3.291773618630916e-05, 7.930234551597304e-05] mean TV (full precision, `experiments/e2p2/summary.json`); 2 vs. 11: no positive-width range, so no equal-damage AUC for that pair (D53) |
| E3 main contrast | Generated cumulative state at level 6; cell-relative whole-layer linear probe, Brier; two-sided with ±0.01 equivalence; per-cell probe, level 2 and level 12 secondary; teacher − generated at level 12 secondary (±0.01) | Probe, PCA, grid, budget and seeds of Section 8.1 (D55, D63, D66, D68, D69); peer order `grid.PEER_ORDER` (81 × 20), SHA-256 of `wholelayer.PEER_IDX` as int64 C-order bytes `57cc1251a39285a9dc5201f2b0b11d825f3f8850db5b356ab7b8187b4f582e1d`; token mapping `CELL_TOKEN_INDICES` (cell $c$ → $c+\lfloor c/9\rfloor$); unit–digit definition of Section 8.3 (D62); PROBE-TRAIN 2,000 and PROBE-VAL 500 puzzles reused unchanged for training and selection |
| Statistics | Paired, grouped analysis; three main contrasts; thresholds 5 pp (H2), 3 pp (H3), ±0.01 (H1 equivalence), ±3 pp (θ₂′); percentile cluster bootstrap with 10,000 resamples; rare-event rule (Section 11.2) | Simulated requirements and error rates of Section 11.4 (D53, D64, D71); TEST size 600 |
| Symmetry | Equivariance; non-augmented test only (Section 8.4) | Exploratory, level 12, whole-layer probe: TEST puzzles 0–199 × 8 group elements (4 full-group, 2 digit-only, 2 geometric, `default_rng(0)`, interleaved per puzzle); acceptable deviation 0.0116 (95th percentile of seed noise on PROBE-VAL, D71) |
| E4 | Conditional, separate fresh test set | Not fixed at this lock: target variable, region, corruption, controls, patch route and geometry, primary combination and comparator, random-direction distribution and $K$, distance definition, numerical gate and sample size are fixed on SELECT in a separate E4 registration before E4-TEST is generated |
| Report | All branches and negative results; exclusions logged | Run register = `experiments/` JSON files with code state (commit, dirty flag, diff hash) and environment per run; main E3 table: generated, permuted, marginal, raw (projected and unprojected), rule, surface, random, label-permutation and teacher rows |

Open fields deliberately receive no invented hash, power estimate, or result. A methodological change after the lock requires a new version and a deviation log (`DECISIONS.md`). The lock is an embargoed OSF registration citing the git tag hash of the locked plan. A new hypothesis arising from TEST data is exploratory and can be confirmed on fresh data.

### 12.3 Work packages and stopping rules

| Package | Dependency | Output / decision |
|---|---|---|
| WP0: sources, reproduction, instrumentation | Accessible model and data | G0 record; verified intervention path |
| WP1: E1 and E2 | Relevant parts of WP0 | Tokenizer/generator breakdown; sensitivity; four-branch adaptation; dose support |
| WP2: E3 | Validated data path and split | Labeler, probe–control matrix, depth and equivariance results |
| WP3: E4a, then optional E4b | Locked E4 gate and fresh data | Targeted causal effect or documented negative result |
| WP4: integrated analysis | E1–E3 locked | Per-claim evidence, limitations, reproducible figures |
| E5: optional extension | Justified next research question | Other checkpoint, targeted retraining, or other formal task; new protocol |

There is no well-founded 1–2 day commitment for WP0: it depends on the checkpoints, the runtime environment, and the required wrapper. The cost estimate is made after the measured pilot. Absence of a positive E2 effect does not automatically stop E3. Absence of a common calibration range rules out only the equal-damage comparison. If there is no interpretable E4 target, the causal phase is dropped.

## 13. Pre-specified interpretation rules

| Result | Justified claim | Does not follow |
|---|---|---|
| Early single-code replacement causes greater degradation | Greater level sensitivity under the given policy | The coarse code explicitly plans an algorithm; a level 1 vs. 11 difference implies a graded sensitivity along the early levels or is independent of level 1's single-code size and learned upsampler |
| D better than C, corrected for sham | Later generation attenuates the intervention effect | The improvement is certainly logical error correction |
| Positive compensation in a checkpoint trained with level corruption | Robustness consistent with the training objective | The model spontaneously detects and repairs logical errors |
| Generated probe beats the null control | The label is readable with the examined readout | The model contains more information than the input, or the generator uses the read-out feature |
| Raw-input baseline reaches the ceiling | The initial label is directly accessible from the input | There is no logical information in the latent space |
| Label of a later solver wave is well readable | Representation correlated with the result of several steps | The model executes the same steps in the same order |
| Equivariance succeeds | More stable readout under symmetry | General reasoning ability is proven |
| Specific restoring patch effect | The given representational region is relevant to the designated output | The full semantic mechanism named by the probe is proven |
| Even a minimal donor patch degrades valid-grid | The consequence and consistency limit of the hybrid state are measurable | The logical hypothesis is refuted by itself |
| Levels 2 vs. 11 interval inside ±3 pp with adequate precision | No practically relevant solve difference between levels 2 and 11 under the given policy | Level 2 carries no information or has no causal role |
| H1: 98.33% lower limit > 0 and the 96.67% interval inside ±0.01 | The candidate mask is readable from the level-6 state above the permuted null control, but by less than the practical threshold, with the examined probe family and budget | The representation computes candidates, or carries no candidate information; another readout could not do better |
| H1: 96.67% interval inside ±0.01 and the 98.33% interval contains 0 | No practically relevant level-6 readability under the examined probe family and budget | Candidate information is absent from the model |
| H1: 98.33% upper limit < 0 | The generated-representation probe reads the label worse than the permuted null control | Readability; a harmful representation in general |
| H1: 98.33% lower limit > 0 and the 96.67% interval not inside ±0.01 | The label is readable above the null control; practical relevance is not shown to be below the threshold | Explicit candidate computation |
| Level-12 readout clearly above the null control and teacher − generated inside ±0.01 | The level-12 readability is consistent with solution content | The generated representation computes candidates or encodes inference steps |
| Level-12 readout accurate on transformed puzzles but not equivariant at the seed-noise tolerance (exploratory) | Per-cell predictions change under symmetry while accuracy does not | The model lacks symmetry-consistent representations in general |
| Non-significant result | The given design provides insufficient evidence for the designated effect | The effect or the logical representation is certainly absent |

Results are stated conditionally on checkpoint and intervention policy. The main risks — distribution shift after code replacement, teacher/generated conflation, data overlap, readout capacity, format errors, and post hoc target selection — appear in the final report together with their assigned controls. No single diagnostic proves in general that a patch is "in-distribution".

## 14. Version decisions based on the reviews

### 14.1 Assessment of the supplementary review

| Proposal | Decision in v3 | Rationale / incorporation |
|---|---|---|
| Coarse/fine discrete doses may have no common range | Adopted | Common-range check; no extrapolation; separate edit cost and initial damage |
| Teacher Hamming and dose–response AUC | Refined | In the primary generator experiment, C–A generated Hamming; teacher as a separate control; AUC only over a common range |
| Continuous pre-quantization perturbation | Optional, separated experiment | Encoder, generator activation, and codebook space are separate intervention sites; not a substitute for the discrete study |
| Nine-bit candidate mask as primary label | Adopted, with ceiling control | Denser label, but shallow rule; Brier primary, single and candidate count derived |
| Labeling by inference depth | Adopted | Order-independent synchronous single waves; stuck and censored cases separate |
| Fixing the probe's spatial access | Adopted | Cumulative, residual, and activation states separate; readout shared across cells |
| Minimal counterfactual pairs | Adopted as E4b | Targeted clue change, uniqueness, clue-count control; no expected response switch with a shared solution |
| Logit/probability endpoint | Adopted | The final decoder's digit margin; not the latent code generator's logit |
| Dates and URLs are probably placeholders | Rejected based on verification | Sources resolve, dated before 2026-11-08; commit pinned |
| McNemar and GLMM | Adopted, with conditions | McNemar for one independent binary pair; GLMM supplementary; clustered paired estimate primary |
| Power is determined solely by the number of discordant pairs | Refined | Direction asymmetry, effect size, sample size, and dependence structure also matter |
| E1 + E2 + E3 integrated publication target | Adopted | E2 narrow pilot, integrated later result; publishability cannot be guaranteed in advance |
| Own wrapper, within 1–2 days | Wrapper adopted; without time promise | New interface to be validated; effort only based on measured pilot |
| E4 gate: at least +0.10 macro-F1 over the raw MLP | Universal threshold not adopted | Label-dependent ceiling and practical effect; numerical gate after pilot, before fresh test |

### 14.2 Main corrections adopted from the previous detailed review

v3 distinguishes the teacher branch encoding the solution from the generated branch examining the puzzle state; introduces the A/B/C/D compensation design; separates edit cost from decoded initial damage; defines an actual output causal endpoint instead of the input logical label; clarifies the roles of parser and validator; handles the technical risk of cumulative state saving; and addresses the difference between full information and information accessible to a constrained probe.

Concrete directional decisions were thus made for v2's open agenda. Whatever requires run results — such as checkpoint hash, reproduction discrepancy, actual dose overlap, label prevalence, or sample size — remained an explicit lock task in Section 12.2, and is filled there in v3.7.


## 15. Sources and references

Sources verified on 2026-11-08. Repository sources point to the pinned commit. Moving checkpoint links must be supplemented with revision and file hash at actual download. Methodological specifications are decisions of this research plan; the cited works do not validate the expected Sudoku results in advance.

1. Kumbong et al. (2026): **Next-Concept Modeling: Fast, Parallel Coarse-to-Fine Text Generation**. [arXiv:2610.14162](https://arxiv.org/abs/2610.14162); [v1 full text and appendices](https://arxiv.org/html/2610.14162v1).
2. Hazy Research: [NCM project post, 2026-10-12](https://hazyresearch.stanford.edu/blog/2026-10-12-ncm).
3. Official repository: [HazyResearch/ncm — pinned commit](https://github.com/HazyResearch/ncm/tree/c70274273f489abc73832b2b98584a8483b6b203).
4. Official checkpoints: [hazyresearch/ncm-checkpoints](https://huggingface.co/hazyresearch/ncm-checkpoints); [Sudoku-hard configuration](https://huggingface.co/hazyresearch/ncm-checkpoints/blob/main/sudoku/hard/config.yaml).
5. Generator and sampling: [models/next_concept.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/next_concept.py).
6. Evaluation configuration: [config/eval/sudoku-hard.yaml](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/config/eval/sudoku-hard.yaml).
7. Quantization and cumulative states: [models/quant.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/quant.py).
8. Tokenizer and decoder: [tokenization/vqvae_tokenizer.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/tokenization/vqvae_tokenizer.py); [models/vqvae.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/vqvae.py); [models/vae.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/vae.py).
9. Original evaluator: [scripts/eval_merge.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/scripts/eval_merge.py); [scripts/eval_shard.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/scripts/eval_shard.py).
10. Hewitt and Liang (2019): [Designing and Interpreting Probes with Control Tasks](https://aclanthology.org/D19-1275/).
11. Belinkov (2022): [Probing Classifiers: Promises, Shortcomings, and Advances](https://aclanthology.org/2022.cl-1.7/).
12. Zhang and Nanda (2024): [Towards Best Practices of Activation Patching in Language Models: Metrics and Methods](https://proceedings.iclr.cc/paper_files/paper/2024/hash/06a52a54c8ee03cd86771136bc91eb1f-Abstract-Conference.html).
13. Geiger et al. (2021): [Causal Abstractions of Neural Networks](https://papers.neurips.cc/paper_files/paper/2021/hash/4f5c422f4d49a5a807eda27434231040-Abstract.html).
14. statsmodels: [McNemar test documentation](https://www.statsmodels.org/stable/generated/statsmodels.stats.contingency_tables.mcnemar.html).
15. lme4: [Binomial and other generalized mixed models — glmer](https://lme4.github.io/lme4/reference/glmer.html).
16. Kniazev and Fijalkow (2026): [Transformers Linearly Represent Highly Structured World Models](https://arxiv.org/abs/2605.18847).
17. Rodrigues and Kang (2026): [Dissecting Hierarchical Reasoning Models: A Mechanistic Study](https://arxiv.org/abs/2609.22197).
18. Khoury (2026): [Round-Trip Refinement: A Training-Free Sampler for Next-Concept Language Models](https://doi.org/10.5281/zenodo.23737645). Zenodo preprint, not peer reviewed.
19. Ahmad, Seth and Sankarapu (2026): [Every Ablation Is a Dose: Counterweights and the Semblance of Self-Repair](https://arxiv.org/abs/2610.02173).
20. Vaidyanathan et al. (2026): [The Curse of Multiple Mediators: Hidden Interaction Effects in Activation Patching](https://arxiv.org/abs/2606.27510).
21. Shah et al. (2024): [Causal Language Modeling Can Elicit Search and Reasoning Capabilities on Logic Puzzles](https://arxiv.org/abs/2409.10502). Candidate-set evidence there comes from forcing outputs and comparing top-k predictions with a solver, not from a learned probe.

## 16. Changes from v3.0

Rationale and dates for each item are in `DECISIONS.md`.

1. The English document is authoritative; the Hungarian v3 and its English translation are frozen predecessors.
2. H1 primary level moved from 2 to 6; level 2 becomes a pre-specified low-capacity control (Sections 3, 8.3, 11.1, 12.2).
3. Data sources fixed: released 2,000 hard boards for G0 and as a secondary stratum; own 30-clue generator for every other subset, with a ±5 pp distribution gate and an independent solver cross-check (Section 4.1).
4. Numerical policy fixed: FP32, eager mode, deterministic algorithms, CPU first; optional BF16 comparison (Section 2.2, item 1).
5. Preregistration: embargoed OSF registration that cites the git tag hash of the locked plan.

Changes in v3.2 (related-work review):

6. Narrowed novelty claim with closest prior work and a dated hedge (Section 2.1).
7. Secondary exploratory unit–digit probe target (Section 8.3).
8. E4: random-direction control for probe-direction interventions; clean–patched distance reported (Section 9.2).
9. H3 interpretation against corruption training and non-canonical codes (Sections 7.1, 13).
10. References [16]–[21] added (Section 15).

Changes in v3.3 (external review R1, `.reviews/plan-v3-2/decisions.md`):

11. Upstream evaluation is FP32 eager; the planned difference is CPU vs CUDA; two-part G0 acceptance rule; identical batch composition across branches (Section 2.2, items 1, 2, 5).
12. Cumulative states computed in an own per-level loop because upstream `idx_to_zhats` aliases its outputs (Section 2.2, item 6).
13. Generator algorithm specified; provenance described as partial orbit protection with duplicate and invariant screening (Sections 4, 4.1).
14. Distribution gate redesigned: frozen generator, model-free depth gate, simulated-size equivalence test, inconclusive vs mismatch, all subsets generated after the gate (Section 4.1).
15. Level choice reworded; level 12 added as a secondary full-resolution comparison; unit–digit readout mapping fixed before PROBE-VAL (Sections 8.3, 12.2).
16. Permuted null probe tuned on its own permuted PROBE-VAL; marginal-prior Brier reported (Section 8.2).
17. E4 patch classes, primary comparator per class, and distance definition fixed on SELECT (Sections 9.2, 12.2).
18. Corruption-training citation corrected to App. F.3; the training regime is recorded only from checkpoint metadata or the paper (Section 7.1).

Changes in v3.4 (final external review, `.reviews/plan-v3-2/decisions.md`):

19. Distribution gate reduced to one terminal validation without enlargement, retry, or pooling; failure or inconclusive result means no equivalence claim (Section 4.1).
20. E4 patches described by two factors, route and geometry; one primary combination and comparator frozen on SELECT (Sections 9.2, 12.2).
21. G0: numerical flips are a hypothesis; changed-output count only with paired reference predictions; cumulative-state tests use prefix recomputation instead of a general inequality; marginal baseline evaluated on TEST (Sections 2.2, 8.2).

Changes in v3.5 (WP0 implementation facts):

22. Execution environment is native Windows instead of WSL2 (Section 2.2, item 1; D30).
23. The released checkpoints contain no training metadata; the training regime is cited from the paper only (Section 7.1).

Changes in v3.6 (E2 redesign after the WP1 pilot, D43–D50):

24. H2 primary contrast moved to levels 1 vs. 11; levels 2 vs. 11 secondary with a ±3 pp equivalence range; level-1 replacement enumerated over all alternatives weighted by CAL frequency (Sections 3, 7.2, 11.1).
25. H3 moved to level 1, where branch C has initial damage (Sections 3, 7.2, 11.1).
26. Primary damage measure is the mean cell-wise total variation distance of the decoder's 12-token output distributions; cell Hamming, latent and re-quantization diagnostics reported (Section 7.2; D26).
27. Dose grid extended to 60% and 100% of a level's positions; pairwise AUC on per-dose nodes over the jointly covered damage range (Section 7.3).
28. Percentile cluster bootstrap with 10,000 resamples and a rare-event rule on independent units; practical thresholds; sample-size simulation under the target alternatives; one TEST size for E2 and H1 fixed at the lock (Sections 11.1, 11.2, 11.4).
29. Second E2 pilot on the same CAL puzzles before the lock (Section 12.1).
30. Revisions from the external review R1 of v3.6 (`.reviews/plan-v3-6/decisions.md`): enumeration weights written out; level-1 architecture caveat (Sections 7.2, 13); pilot figures quoted per branch and policy.
31. Revisions from the final external review of v3.6: sign-preserving simulation scenarios for H2 and the equivalence claim; tie rule for AUC nodes (Sections 7.3, 11.4).

Changes in v3.7 (preregistration lock, D53–D71):

32. H1 primary probe is the cell-relative whole-layer linear probe (states of the cell and its 20 peers, PCA-256 fitted on PROBE-TRAIN, whitened); the per-cell probe is secondary; the D55 grid and the D63 budget are kept after a budget sensitivity check (Sections 3, 8.1; D66, D68, D69).
33. H1 is two-sided with a family-level equivalence reading inside ±0.01; secondary teacher − generated contrast at level 12 with ±0.01 (Sections 8.3, 11.1; D65, D68, D70).
34. Unit–digit label and readout fixed (Section 8.3; D62).
35. Equivariance analysis moved to level 12 as an exploratory analysis with a fixed acceptable deviation (Section 8.4; D68, D70, D71).
36. Lock values: TEST size 600, simulated error rates including the injection boundary check for the levels 2 vs. 11 equivalence rule, TEST identity hashes, frozen level-1 frequencies and the E2 common range (Sections 11.4, 12.1, 12.2; D53, D70, D71).
37. New interpretation rows for the H1 equivalence outcomes, level-12 solution content and the exploratory equivariance result (Section 13).


# E5 D102 draft: activation-exchange causal test

Status: draft for review, not yet in `DECISIONS.md`. Non-confirmatory pilot design, written after D100–D101 and before the E5 protocol and any TEST data exist.

## Context

E5 asks whether the weak linear readout of the level-6 candidate mask in the NCM Sudoku generator's cumulative state Z<=6 is a property of that state or of the generator. The pilot (D100, D101; `docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md`, results in `experiments/e5/pilot/`) found, on counterfactual pairs (one solution, two 30-clue masks; D97, D99):

- prefix cell positions of the generator (the puzzle encoding that every generation pass attends to; it does not depend on Z<=6): within-pair AUC (W-AUC) 1.0 at layers 2–3 with the shared own-position linear head, 0.958 at layer 8; online MDL compression 195.6 at P2;
- generated Z<=6 cell states: W-AUC 0.504 (AdamW) and 0.504 (converged L-BFGS, standardized inputs), MDL compression 1.029, below the position-only baseline P0 (1.049).

Readability does not show use: the candidate mask is a one-step function of the clues, and its presence in the puzzle encoding does not imply that the generator uses it when it emits codes. D101(1) leaves this to a causal test. This draft specifies that test as a pilot on the PROBE-VAL pairs.

Architecture facts the design relies on (`third_party/ncm/models/next_concept.py`, `src/ncm_sudoku/intervene.py`): generation runs 12 passes, one per level; each pass processes the 91-token puzzle prefix plus that level's query positions; prefix positions attend only to the prefix (mask `gen_mask[:, :, :P, P:] = -inf`), query positions attend to the prefix and to each other; decoding is greedy, so generation is deterministic. Pair members share the solution and differ in the clue mask; on PROBE-VAL, 88 of 250 pairs have identical level 1–6 codes, both members are solved in 77.6% of pairs and exactly one member in 51 pairs.

## Draft decision D102

1. Intervention (interchange intervention, Geiger et al. 2021): for an ordered pair (recipient r, donor d) of the two members of a pair, during the recipient's full generation (all 12 passes), replace at layer k* = 2 (the D101(3) layer) the recipient's prefix residual stream at every cell position that is empty in both members, as follows:
   - probe subspace: x_r ← x_r + Q Qᵀ (x_d − x_r), with Q (512 × 9) an orthonormal basis of the nine digit rows of the frozen pilot P2 shared head restricted to the state coordinates (the cell one-hot part is dropped);
   - random subspace control: the same with Q a random orthonormal 512 × 9 basis (5 fixed seeds);
   - full-vector swap (ceiling): x_r ← x_d at those positions;
   - sham (identity check): x_r ← x_r + Q Qᵀ (x_r − x_r); generated codes must equal the clean run bit for bit.
   Clue positions and positions empty in only one member are never patched, so the recipient keeps its own clue tokens. Both orders (a→b, b→a) are run for every PROBE-VAL pair (500 recipient runs per condition).
2. Representational outcome (does the downstream representation follow the donor?): after patching at layer 2, the recipient's prefix states at layers 4 and 8 are read with the frozen pilot shared heads of those layers; donor-follow rate = share of discordant bits (cell empty in both, digit candidate in exactly one member) on which the patched recipient's probability moves towards the donor's label relative to the clean recipient run.
3. Behavioural outcomes: (a) code change: share of recipient runs whose generated codes at levels 7–12 differ from the clean run, and per-level code change counts; (b) decoded-grid change: cell Hamming distance between the patched and clean decoded grids; (c) rescue: on the 51 pairs with exactly one solved member, solve rate of the unsolved member when the solved member is the donor, and the converse harm rate.
4. Primary pilot contrast: per recipient, probe-subspace effect minus the mean effect of the five random subspaces of equal rank, for the donor-follow rate and for the code-change indicator; paired over recipients, pair-level bootstrap (resampling pairs, both orders together). The full swap bounds what any prefix-cell intervention at layer 2 can change; the sham must show zero change.
5. Readout of the result for the protocol: probe-subspace effect clearly above the random subspaces on the behavioural outcomes → the generator uses the candidate directions of its puzzle encoding; probe-subspace effect only on the representational outcome → the directions propagate inside the encoder but do not drive code choice; no effect beyond random → the readable candidate information is not used through this subspace (not that it is unused in general). Thresholds are fixed in the protocol, not here.
6. Cost (measured basis: generation 1.7 s per puzzle on CPU, `experiments/e5/cost.json`): 8 conditions (sham, probe, 5 random, full) × 500 recipient runs ≈ 1.9 h.

## Open questions for the review

- Is patching at all both-empty cell positions in every pass the right scope, or should the intervention be restricted to the passes after level 6 (keeping Z<=6 fixed) to separate the effect on Z<=6 from the effect on later levels?
- Is a nine-dimensional probe subspace from one linear head, applied position-wise, a fair "candidate subspace", and is a random orthonormal subspace of equal rank the right control (norm of the projected difference, alignment with high-variance directions)?
- Is the donor-follow rate well defined when the clean recipient prediction is already saturated (P2 probabilities near 0 or 1)?
- Does the shared solution make behavioural outcomes uninformative (both members should produce the same grid), and is the rescue analysis on 51 pairs too small to be useful?
- Are there identity checks missing (for example, that patching with the recipient's own activations at all positions reproduces the clean codes, and that the hook does not alter the query positions)?

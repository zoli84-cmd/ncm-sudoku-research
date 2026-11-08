# Decision log

One entry per decision: date, decision, rationale. Plan-affecting entries name the plan version that incorporates them. After the preregistration lock, entries here are the deviation log.

## 2026-11-08 — Project setup (grilling session)

| ID | Decision | Rationale | Plan |
|---|---|---|---|
| D01 | The English plan is authoritative from v3.1; the Hungarian v3 and its English translation are frozen | All project files are in English; avoids two diverging versions | v3.1 header |
| D02 | Personal research project, no deadline; E4 stays optional; first milestone is G0 + E1–E2 pilot | Scope follows capacity; no time promise before the measured pilot | — |
| D03 | Targets: arXiv preprint plus an interpretability workshop | Fits the integrated E1+E2+E3 goal | — |
| D04 | Git with a private GitHub remote; made public at publication | Dated, hash-identified snapshots for the lock and deviation log | — |
| D05 | Upstream `HazyResearch/ncm` as a git submodule at commit `c70274273f489abc73832b2b98584a8483b6b203`, never modified; hooks and `forward_with_intervention()` live in `src/ncm_sudoku/` | G0 identity tests are only meaningful against unmodified upstream code | — |
| D06 | H1 primary level is 6; level 2 is a pre-specified low-capacity control | $Z_{\leq 2}$ holds at most 12 bits (3 codes × 4 bits), too little for a candidate-mask readout; level 6 holds up to 140 bits | v3.1 §3, §8.3, §11.1, §12.2 |
| D07 | Compute: WSL2, CPU, `uv`-managed Python 3.12, CPU PyTorch; GPU only if the measured pilot cost requires it | No local GPU; generator 25.5M and tokenizer 14.9M parameters; no CUDA-only kernels in the Sudoku path | v3.1 §2.2 |
| D08 | FP32, eager mode, deterministic algorithms; deviation from the published BF16 + `torch.compile` numbers is reported, not corrected; BF16 run optional | Sham (B=A) and no-op tests require exact equality | v3.1 §2.2 |
| D09 | Preregistration: embargoed OSF registration citing the git tag hash of the locked plan | Independent timestamp; no employer constraint | v3.1 §12.2, §16 |
| D10 | Data: released 2,000 hard boards for G0 and as a secondary stratum; own 30-clue generator for all other subsets | 2,000 boards are too few for six group-disjoint subsets; training data unreleased; S-FLM generator unlicensed | v3.1 §4.1 |
| D11 | Distribution gate: 95% interval of the solve-rate difference (fresh vs released, ~500 puzzles, CAL) within ±5 pp; tuning only on CAL, logged here | Fresh data must match the checkpoint's evaluation distribution before TEST | v3.1 §4.1 |
| D12 | Own solver, uniqueness checker, and labeler, cross-checked against an independent DLX implementation | Plan requires an independent validator; catches silent label errors | v3.1 §4.1 |
| D13 | Main analysis in Python; supplementary GLMM as one R script with lme4 on exported CSV | lme4 is the tool cited by the plan; GLMM is supplementary | — |
| D14 | Related-work novelty search (Consensus API, arXiv, Exa) before WP0, saved under `literature/` with a query log | Novelty claims in §2.1 are unverified; cheaper to learn before engineering | — |
| D15 | Layout: `src/ncm_sudoku/`, `tests/` (pytest), `third_party/ncm` submodule, `uv` lockfile, `experiments/`, `literature/` | G0 identity and validator tests become the project's verification | — |

## 2026-11-08 — Related-work review (`literature/related_work_novelty_check.md`)

| ID | Decision | Rationale | Plan |
|---|---|---|---|
| D16 | Add a secondary exploratory unit–digit probe target (27 units × 9 digits), label definition aligned with Kniazev & Fijalkow (2026) before PROBE-VAL | Direct comparison with the closest prior Sudoku probing result, where unit-level probes succeed and per-cell candidate probes plateau | v3.2 §8.3 |
| D17 | E4: size- and norm-matched random-direction control for every probe-direction intervention; report the clean–patched distance for every patch | HRM study found probe directions decodable but not more causal than random; patching interaction effects grow with distance | v3.2 §9.2 |
| D18 | Interpret H3 against NCM's corruption training and non-canonical codes; G0 records the checkpoint's training regime; new §13 interpretation row | A positive compensation effect may be a trained robustness property; replaced codes may be absorbed | v3.2 §7.1, §13 |
| D19 | Narrow and date the novelty claim ("to our knowledge, as of 2026-11-08"); add references [16]–[21]; repeat the search before submission | Sudoku candidate decodability is not new; NCM follow-ups appear within weeks | v3.2 §2.1, §15 |

## 2026-11-08 — External review R1 (`.reviews/plan-v3-2/decisions.md`)

| ID | Decision | Rationale | Plan |
|---|---|---|---|
| D20 | Two-part G0 acceptance rule: official solve rate within ±1.0 pp of 86.1% on the 2,000 released boards, and 100% agreement of within-device identity tests; identical batch composition across branches A–D | Upstream eval is already FP32 eager (verified), so only CPU/CUDA argmax flips remain; deterministic algorithms guarantee repeatability only for identical shapes | v3.3 §2.2 items 1, 2, 5 |
| D21 | Supersedes D11: frozen generator, separate development batch, model-free solver-depth gate, TOST equivalence (±5 pp, 90% interval) with a simulated batch size (at least 1,000 planned), inconclusive is not mismatch, all analysis subsets generated after the gate | Both reviewers: the 500-puzzle 95%-containment gate passes only about 65% of the time at true equality, and tuning on CAL cannot validate itself | v3.3 §4.1 |
| D22 | Cumulative states via an own per-level loop with clones | Upstream `idx_to_zhats` returns 12 references to one tensor (verified) | v3.3 §2.2 item 6 |
| D23 | E4: generator-mediated vs decoder-input patch classes; one primary comparator per class; random-direction distribution, K, and distance definition fixed on SELECT | Upstream decodes only from discrete codes (verified); controls were underspecified | v3.3 §9.2, §12.2 |
| D24 | Provenance is partial orbit protection; generator algorithm specified; duplicate and symmetry-invariant screening | Independent draws can share an orbit; the sampler is not proven uniform | v3.3 §4, §4.1 |
| D25 | Level 2 reworded as a low-capacity comparison; level 12 added as a secondary full-resolution comparison; permuted null probe tuned on its own permuted PROBE-VAL | Bit bounds do not predict readability; interpolation bottleneck below level 12; avoid inflating theta_1 | v3.3 §8.2, §8.3 |
| D26 | Deferred: re-quantization diagnostic for geometric residual cancellation in E2 (backlog, after the pilot); WP0-B must load checkpoints with `weights_only=True` or inspect them first (upstream uses `weights_only=False`) | Scope control; untrusted checkpoint pickle | — |

## 2026-11-08 — External review, final round (`.reviews/plan-v3-2/decisions.md`)

| ID | Decision | Rationale | Plan |
|---|---|---|---|
| D27 | Supersedes the retry parts of D21: generator and batch size chosen during development, then one terminal validation gate without enlargement, retry, or pooling; failure or inconclusive result means no equivalence claim | Outcome-dependent enlargement and repeated gates break fixed-look TOST error control | v3.4 §4.1 |
| D28 | Supersedes the class wording of D23: E4 patches are described by route (generator-mediated / decoder-input) and geometry (region / probe direction); one primary combination and comparator frozen on SELECT | The single class label mixed two independent factors and left the primary contrast ambiguous | v3.4 §9.2, §12.2 |
| D29 | G0 refinements: numerical flips are a hypothesis; changed-output count only with paired reference predictions; prefix recomputation instead of a general inequality invariant; marginal baseline evaluated on TEST | Final-round minor findings; all verified against the plan text | v3.4 §2.2, §8.2 |

## 2026-11-08 — Execution environment

| ID | Decision | Rationale | Plan |
|---|---|---|---|
| D30 | Supersedes the WSL2 part of D07: the Python environment runs natively on Windows with `uv` (Python 3.12, CPU, FP32); plan §2.2 item 1 wording ("under WSL2") is updated in the next plan version | WSL cannot reach the network through the corporate proxy; Windows reaches PyPI through the local proxy; the Sudoku path needs no Linux-only kernels | v3.4 §2.2 item 1 (wording pending) |

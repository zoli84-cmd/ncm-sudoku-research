### Verdict
The protocol is sound enough to start WP0 as a gated pilot, but not yet to lock the confirmatory study. The most important change is to replace the adaptive, single-endpoint distribution gate with validation of a frozen generator on fresh data—or explicitly study the fresh distribution without claiming distribution equivalence.

### Findings

```text
SOL-1 | major | research_plan_v3.2.md:107; DECISIONS.md:D11
Claim: The distribution gate does not specify independent validation after generator tuning, so an eventual pass can reflect adaptation to CAL rather than successful out-of-sample validation. Agreement in one checkpoint's mean solve rate also does not establish agreement between puzzle distributions.
Evidence: Section 4.1 permits tuning against the depth distribution on CAL after a failed gate, without specifying a fresh validation batch, attempt limit, or stopping rule. Solver-depth distributions are merely reported; no acceptance criterion covers them or candidate-label prevalence. Greedy uniqueness-preserving removal can select different clue-mask structures from another 30-clue generator, regardless of whether their aggregate solve rates agree; the actual S-FLM generator could not be checked.
Recommendation: Separate generator-development CAL from fresh gate data, freeze the generator before that gate, and specify permitted attempts and the target of validation. Add preselected difficulty/label-distribution checks if distribution matching is required. The simpler alternative is to retain a fixed generator, describe its population explicitly, and report the released set as a secondary distribution. Tuning on CAL is not itself leakage into untouched, group-disjoint TEST, but it cannot validate distribution matching on the data used for tuning.
Confidence: high
```

```text
SOL-2 | major | research_plan_v3.2.md:86-90,106
Claim: Generation provenance alone is not an orbit identifier for independently generated solutions. The total number of valid grids supports the negligible-overlap argument only under a sufficiently dispersed solution sampler, not merely because puzzles are generated locally.
Evidence: Section 4 requires symmetry-related puzzles and masks of the same solution to share a group, but Section 4.1 treats generation provenance as the orbit identifier. Independent draws of random symmetries of one base solution can have different generation identifiers while all belonging to the same orbit. Provenance tracks known ancestry; it does not detect equivalence between independently produced ancestors. No implemented solution sampler exists in this checkout to verify the asserted uniformity.
Recommendation: Specify and validate the solution-sampling algorithm and the restart/discard policy for attempts that do not reach exactly 30 unique-solution clues. Use verified solution-orbit canonicalization, or explicitly describe provenance-only protection as partial. Keep the training-overlap statement conditional on the sampler and on the unverified training-data assumptions; document any acceptance-induced sampling bias.
Confidence: high
```

```text
SOL-3 | major | research_plan_v3.2.md:245; DECISIONS.md:D06
Claim: The capacity arithmetic is correct, but it does not justify an expected near-null Brier improvement at level 2. Inability to encode an entire candidate mask is not inability to encode useful partial information about that mask.
Evidence: Under the stated 16-valued codebooks, levels 1–2 contain three codes and at most 12 bits; levels 1–6 contain 35 codes and at most 140 bits. However, candidate bits are correlated, their entropy has not been measured, and even one bit encoding a puzzle-level statistic can improve candidate probabilities beyond position-dependent priors. H1 tests probabilistic improvement, not lossless reconstruction of the complete label tensor. The same argument also cannot establish that 140 bits are sufficient.
Recommendation: Retain level 6 as a pragmatic, preselected capacity choice, but remove the implication that the bit bound predicts a near-null level-2 result. Call level 2 a low-capacity comparison rather than an information-free null; use CAL code diversity and training-size curves to assess practical readability. No change to the three-member Bonferroni family is needed merely because H1 and H2/H3 use different levels.
Confidence: high
```

```text
SOL-4 | minor | research_plan_v3.2.md:107; DECISIONS.md:D11
Claim: Approximately 500 fresh puzzles has not been shown to provide adequate operating power for the stated equivalence gate. Failure of interval containment can mean insufficient precision rather than evidence of a distribution shift, so it should not automatically trigger generator tuning.
Evidence: Using the paper's 86.1% hard result only as a planning assumption for equal population solve rates, independent samples of 500 and 2,000 give SE ≈ 1.73 percentage points and a normal-approximation 95% half-width ≈ 3.39 points. The approximate probability of passing the ±5-point gate at true equality is only 64.8%. If the released 2,000 outcomes instead define a fixed finite benchmark, excluding their sampling uncertainty raises that approximation to 79.7%; these are different inferential targets. These calculations are planning approximations, not measured checkpoint results or validated power estimates for the eventual interval procedure.
Recommendation: Specify whether the target is the finite released benchmark or an underlying population, then simulate the chosen interval procedure and clustering to select the gate sample size. Distinguish inconclusive precision from a detected mismatch. A 95% containment rule is valid but conservative; retain that coverage deliberately rather than treating the proposed sample size as already adequate.
Confidence: high
```

```text
SOL-5 | minor | research_plan_v3.2.md:44-45,59; DECISIONS.md:D08
Claim: The all-FP32 policy and the requirement to reproduce the original settings need separate operational definitions. Exact sham/no-op agreement does not require FP32 and does not demonstrate equivalence to BF16 published behaviour.
Evidence: Section 2.2 mandates FP32 eager execution while making the BF16 comparison optional; Section 12.1 describes G0 as using the original evaluation set and settings. The local paper, Appendix C, PDF page 22, states BF16 mixed precision and torch.compile. Lower-precision arithmetic can change close argmax decisions and subsequent generated levels, even when aggregate solve rates remain similar; deterministic execution within either numerical mode does not rule this out.
Recommendation: Separate published-mode reproduction from FP32 wrapper validation. Require a prespecified, same-puzzle cross-mode calibration when claiming reproduction of published behaviour, recording code/output disagreement as well as aggregate metrics. If that comparison is unavailable, identify the study as an FP32 replication and bind E2 interpretations explicitly to that numerical configuration; the existing G0 discrepancy rule should remain enforced.
Confidence: high
```

```text
SOL-6 | minor | research_plan_v3.2.md:275-285,394
Claim: The new random-direction control and clean–patched distance are sensible additions but are not yet reproducible specifications. The E4 primary targeted-versus-control contrast also needs an explicit comparator once the additional random-direction branch is introduced.
Evidence: Section 9.2 requires size- and norm-matched random directions without defining the intervention space, direction distribution, sign, number of draws, or averaging rule. It requires clean–patched distance without specifying the tensor/site, norm, normalization, or whether the measurement concerns the patched region or the full state. The lock checklist leaves controls open but does not explicitly enumerate these choices.
Recommendation: Freeze these fields on SELECT before E4-TEST, including random seeds, dose matching, distance definition, and the single primary comparator. Treat other control comparisons as secondary or specify their multiplicity treatment. For a claim that a probe direction is causally special, compare it directly with the matched random directions, not only with a different spatial region.
Confidence: high
```

```text
SOL-7 | nit | research_plan_v3.2.md:171
Claim: The trained-robustness paragraph cites the wrong appendix and contains a malformed theta expression.
Evidence: The local paper's Appendix F.3, PDF page 29, describes conditioning-code corruption; Appendix H, beginning on PDF page 32, concerns hierarchy interventions. At plan line 171, the inline expression contains a literal tab followed by heta rather than the LaTeX command \theta; the displayed definition at line 166 is correct.
Recommendation: Cite Appendix F.3 for corruption training and restore \theta_{\mathrm{comp}} in the inline expression in the next plan version.
Confidence: high
```

### Claims checked

No upstream checkout is present. Online GitHub/Hugging Face retrieval was unavailable, and the GitHub MCP request failed. Paper corroboration below is therefore **not verification of the pinned implementation**.

- **Holds — paper-level architecture:** 12 Sudoku levels, 16 codebook entries, latent width 256, target length 89, approximately 14.90M tokenizer and 25.46M generator parameters: local paper, Appendix C, PDF pages 23–24. Their correspondence to the released checkpoint **could not verify**; Confidence: low.
- **Holds — paper-level numerical/training description:** BF16 mixed precision and `torch.compile` appear in Appendix C, PDF page 22. Uniform replacement of conditioning codes with clean targets appears in §3.4 and Appendix F.3, PDF pages 7 and 29. The released Sudoku checkpoint's actual corruption schedule **could not verify**; Confidence: low.
- **Holds — paper-level conditioning:** each target block attends to the prompt under the prefix-LM pattern, §3.4, PDF page 7. Unchanged puzzle forwarding at every implemented generation/restart level **could not verify**; Confidence: low.
- **Could not verify — checkpoint/configuration claims:** exact ladder `1,2,4,6,9,13,18,26,37,50,67,89`, `compression_factor=1`, `temperature=0.0` and its argmax implementation, checkpoint files/licenses, and CPU-path compatibility. Confidence: low.
- **Could not verify — implementation claims:** teacher solution encoding versus puzzle-conditioned generation in the cited paths; feasibility of arbitrary-level continuation; `idx_to_zhats` in-place/list aliasing; full-length partial-decoding requirements; original evaluator string matching and truncated-output denominator behaviour. `forward_with_intervention()` is correctly identified as a proposed local interface, not an existing API. Confidence: low for upstream behaviour.
- **Could not verify — released-data claims:** 2,000 hard boards, exact clue counts in the files, shared easy/medium/hard solutions, MIT licensing, unreleased training data, the S-FLM 48k/seed-42 provenance, and the generator's license status. The paper does state the 40/35/30 clue-count difficulty convention, §4.5 and Appendix D.3. Confidence: low for repository/data-file claims.
- **Holds — primary-family consistency:** §§3, 8.3, 11.1 and 12.2 consistently assign H1 to level 6, H2 to levels 2/11, and H3 to level 2. Coverage is exactly `1 − 0.05/3 = 98.333…%`; different levels do not invalidate Bonferroni control, subject to the bootstrap intervals' actual coverage.
- **Holds — statistical definitions:** for independent paired binary differences X, `E[X²]=q`, hence `Var(delta_hat)=(q−delta²)/n`. Exact McNemar is correctly restricted to one independent binary pair per unit. Puzzle averaging, highest-shared-group resampling, paired branch preservation, conditional-on-fitted-probe intervals, and the rare-event caveat are appropriate; the concrete bootstrap/rare-event procedures remain legitimate pre-lock open items.
- **Holds — interpretation and multiplicity safeguards:** with deterministic B=A, the compensation contrast reduces to `E[Y_D−Y_C]`. Puzzle conditioning does not prevent identifying that operational contrast, but it prevents attributing improvement uniquely to logical repair or coarse-code mediation. The unit–digit target is explicitly exploratory and its label is to be fixed before PROBE-VAL, so it does not enlarge the primary family; its label, representation pooling and probe specification still need completion before evaluation.

---

<sub>Generated by [GitHub Copilot CLI](https://github.com/features/copilot/cli)</sub>

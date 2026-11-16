# External AI peer reviews of the WP4 manuscript (2026-11-16)

Two journal-style reviews, commissioned by the author outside any journal process and written in Hungarian, were run on the 26-page `main.pdf` of 2026-11-16 (before the D86 revision). This file summarizes them in English; the Hungarian originals were not kept in the repository. Neither review is a human expert review.

| Reviewer | Model family | Recommendation |
|---|---|---|
| Astra | OpenAI (ChatGPT) | Major revision |
| Carbon | Google (Gemini) | Accept with minor revisions (as a TMLR-style review) |

## Shared assessment

Both reviewers found the confirmatory numbers consistent with the committed result files and no error that invalidates a main result. Both praised the separation of pilot and TEST data, the documented design changes, the control matrix, the sham restart and the claim boundaries ("does not follow"). Both identified the same two scope limits: the probes read the decoder's cumulative state, not the generator's activations, and the level-1 contrast mixes an architectural difference (a single code behind a learned upsampler) with the edit itself.

## Astra (major revision)

1. Narrow the framing to the code hierarchy's behavioral sensitivity and candidate-mask accessibility; suggested title change from "logical readability" to "candidate-mask readability".
2. Present H2 as a policy-bound sensitivity result; the missing equal-damage comparison limits its meaning.
3. Solution-digit baseline: a predictor that knows the solution digit and gives the other eight digits one common probability q, with 1 + 8q = 9p for label rate p, has Brier loss 8/9 q(1 - q), about 0.182 on TEST, close to both level-12 probes. Also reported exploratory paired bootstrap differences (teacher minus generated at level 6, marginal minus generated, generated minus surface).
4. Check PCA and probe capacity (higher rank or unprojected regularized probe); the level-6 projection keeps about 90% of the training variance (reviewer's computation).
5. Split the H3 net effect into improving and worsening puzzles; state that the H3 interval crosses the 3-point threshold; justify the ±0.01 Brier margin.
6. Symmetry analysis: check teacher and raw-input readouts too.
7. Editorial: shorten repeated statements, clarify "whole-layer", move Table 2 closer to its first mention, zoom figure insets, archived release (e.g. Zenodo), reviewer access to the OSF registration.

## Carbon (minor revision)

1. Stress, as the most likely architectural explanation of the weak H1 result, that the cumulative state lives in the space of a tokenizer trained to compress solutions, while any candidate reasoning would happen in the generator.
2. Emphasize the sharp gap between level 1 (-11.1 pp) and level 2 (0.0 pp, equivalent to level 11), and qualify "equal edit cost" as one replaced code per level.
3. State that the nonlinear (MLP) capacity check covered only the per-cell probe.
4. Minor: formalize the cumulative state and per-level code counts; map E2/E3 to H2, H3 and H1 explicitly; Tables 2 and 3 had drifted to the end of the document (pages 20-21); split dense paragraphs in Sections 6.4 and 7.2.
5. Venue suggestions: TMLR (primary), Royal Society Open Science or PLOS ONE, JAIR or Machine Learning, mechanistic-interpretability workshops.

## Disposition

The adopted and rejected items, with reasons, are recorded in `DECISIONS.md` D86 (commit `f7cf57e`). In short: adopted the abstract statement of the level 2 vs. 11 equivalence, the E-to-H map, the one-code wording, the H3 discordance counts, the cumulative-state paragraph, the readout-capacity limits, the solution-digit reference (labelled as an exploratory analytic value computed after TEST), the split E3 paragraph and the float placement fix. Not adopted, because they need new model runs or analyses after TEST: higher-rank or unprojected probes, teacher and raw-input equivariance, generator activations, the reviewer's paired bootstrap differences and figure insets. The title change is the author's decision and was open when this summary was written; the recommendation was to keep the title, for consistency with the OSF registration title and because the abstract already specifies the candidate mask. The ±0.01 margin is registered and was not changed.

## Fable 5.2 (third review, after the D86 revision)

An informal review, also in Hungarian, of the revised manuscript. It recomputed derivable values (solve shares, the rare-event bound, the Wilson interval, the cell count, the contrasts) and found them consistent; it could not open the repository (rate limit) or read the OSF page.

1. H1: at level 6 the teacher state reaches the same Brier loss as the generated state, so the small gain over the control may be solution content; suggested an exploratory probe on the eight non-solution digits.
2. H2: one replacement is not the same intervention at the two levels; replacing all level-11 codes gives an initial damage close to the single level-1 replacement but a much smaller solve loss, which should be stated in Section 6.2.
3. The registration lists the GLMM and the same-solution/different-clue-mask teacher control as exploratory; the manuscript should say that they were not run.
4. E4: the registration excludes E4, while the manuscript said the registered plan included it.
5. Rounding: differences of rounded numbers in the text differ in the last digit from the contrasts.
6. References: check every entry by hand; suggested citing a published version of Kniazev & Fijalkow and rechecking the per-cell probe sentence against its abstract.
7. For a later TMLR submission: anonymization (name, ORCID, repository and OSF links), length (main text about 18 pages), AI statement against the venue policy, public access to the repository and tags.

Disposition: `DECISIONS.md` D87. Items 1 (disclosure only, no new probe), 2 to 5 and the per-cell clause of 6 were adopted after checking the sources; no published venue of Kniazev & Fijalkow was found, so the arXiv citation stays. Item 7 concerns a future journal submission, not the arXiv preprint.

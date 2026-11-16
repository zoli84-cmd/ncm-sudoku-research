Verdict

The core numerical results are sound, but the two major corrections below should precede
publication. Most importantly, propagate the checkpoint-training caveat into the abstract,
introduction and interpretation table rather than presenting corruption training as verified
checkpoint provenance.

Findings

ASTRA-1 | major | paper\main.tex:12; paper\sections\introduction.tex:16;
paper\generated\tables\readings.tex:9
Claim: The new training-provenance qualification is incomplete. The abstract still attributes
compensation to “the model’s training against corrupted levels,” the introduction says “the
checkpoint’s training,” and the interpretation table presents the trained-checkpoint row as
triggered without stating its unverified premise.
Evidence: paper\sections\e2.tex:33 and discussion.tex:23 correctly make this interpretation
conditional. literature\presubmission_update_2026-11-16.md:12,68 explicitly distinguishes the method
description from unavailable Sudoku-specific training metadata; research_plan_v3.7.md:171 records
the same limitation.
Recommendation: Use “consistent with the corruption-training procedure described for NCM, assuming
this checkpoint followed it” throughout. Preserve the verbatim registered row, but annotate its
application as conditional outside the quoted wording; no change to frozen results is needed.
Confidence: high

ASTRA-2 | major | paper\sections\appendix.tex:17–20
Claim: Reproducibility describes the code freeze and regeneration of manuscript assets, but leaves
data/output availability and computational cost unspecified. Readers cannot tell which artifacts
will accompany publication and which require downloading or rerunning; this is separate from the
acknowledged repository-URL placeholder.
Evidence: .gitignore:7–12 excludes checkpoints, datasets, root run outputs and probe weights.
experiments\provenance\checkpoints.json and released_data.json contain the download identities and
revisions, but the paper does not point to them. experiments\wp2\test\results.json:20–87 records the
environment, four PyTorch threads and runner timings; ROADMAP.md:15 reports approximately 14.7 hours
for TEST alone.
Recommendation: Add a short availability-and-compute paragraph identifying the provenance manifests,
puzzle identities/hashes and regeneration instructions; state whether raw outputs and fitted probes
are released or regenerated. Report the recorded environment and TEST runtime, explicitly
distinguishing it from total project compute.
Confidence: high

ASTRA-3 | minor | paper\sections\introduction.tex:12; e3.tex:15; discussion.tex:7 | The remaining
“unrelated state” wording misdescribes the comparison despite the corrected procedural definition:
both probes receive intact TEST states (src\ncm_sudoku\e3controls.py:174–188). Say “a probe trained
on independently permuted representation–label pairs,” not a readout from an unrelated TEST state.

ASTRA-4 | minor | paper\sections\setup.tex:16,28 | State CAL’s size and briefly explain why TEST
contains 600 puzzles: research_plan_v3.7.md §11.4 selects the maximum simulated requirement, driven
by the levels-2-versus-11 equivalence analysis. Currently the sample-size rationale is absent.

ASTRA-5 | minor | paper\sections\e2.tex:40–41 | The missing frozen-range AUC does not prevent the
registered solve-change-versus-initial-damage curves. Plan §7.3 requires separate sensitivity curves
without overlap; wp4figures.py:32–55 plots edit count only, although results.json:1025 onward stores
the damage nodes. Show those descriptive curves or explicitly disclose their omission separately
from the unavailable AUC.

ASTRA-6 | minor | paper\sections\e2.tex:62; appendix.tex:25 | “Configurations with saved states”
still conflicts with the explicit disclosure that full state tensors were not saved. Replace it with
“configurations with recorded cumulative-state distances and intermediate decodings.”

ASTRA-7 | minor | paper\sections\setup.tex:14,28 | Identify the distribution-gate interval as a 90%
Wilson interval relative to the fixed released-set benchmark, rather than leaving it under the later
blanket bootstrap description; this is its actual construction in src\ncm_sudoku\gate.py:51–64.

ASTRA-8 | minor | paper\sections\discussion.tex:7 | “Errors are most costly at the coarsest level”
implies a maximum across the hierarchy, which the level-1-versus-11 confirmatory contrast does not
establish. Replace it with the measured policy-conditional comparison; not every level received a
sensitivity test.

Claims checked

 - holds — H1 is 0.0029 Brier, with 98.33% interval [0.0025, 0.0033]; its distinct 96.67% TOST
interval lies within ±0.01.
 - holds — H2 is −11.1 pp [−13.6, −8.8]; the positive-magnitude interval is correctly reversed. H3
is +1.7 pp [0.1, 3.3], so practical relevance at 3 pp remains unsettled.
 - holds — Levels 2 versus 11 use the rare-event bound, approximately ±1.519 pp; level-12
teacher–generated equivalence uses the separate 90% TOST interval.
 - holds — Checked prose macro mappings and numerical values agree with KEYS and the stored
results/report, including E1 reconstruction, surface/raw controls, secondary metrics and depth
counts.
 - holds — All six figure functions draw the stated series and interval types; forest thresholds are
restricted to their intended rows. The saved-state wording exception is identified above.
 - holds — Revised Quantix-eng, Khoury, Oh and Garg claims match the repository’s quoted evidence;
recorded bibliography fields agree, and no unsupported “first interpretability study” claim remains.
 - holds — Local records support preregistration before TEST model runs, analysis commit 1047668,
one evaluation, disclosed pilot-driven changes and the post-TEST decision to omit E4 without
evaluating SELECT.
 - does not hold — Checkpoint corruption training is not established as verified provenance; its
unconditional presentation remains inconsistent across sections.
 - holds — Author/affiliation, licence wording and AI-use disclosure are consistent with repository
declarations; source cross-references resolve to the intended sections, tables and figures.
 - could not verify — Live OSF/ORCID records, external-source authenticity and rendered PDF layout
were outside this repository-only, non-executing review.


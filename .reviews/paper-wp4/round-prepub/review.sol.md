Verdict

The core numerical conclusions are consistent with the locked analysis, but the major reporting
issues below should be corrected before publication. Most importantly, describe H1 as a comparison
with a permutation-trained control, not with an unrelated TEST state.

Findings

SOL-1 | major | paper\sections\e3.tex:15; paper\sections\introduction.tex:12;
paper\sections\discussion.tex:7
Claim: The final-round clarification of the permuted control is incomplete: E3 correctly says both
probes receive intact TEST pairs, then interprets the contrast as performance against “a state from
an unrelated puzzle.” The introduction and discussion repeat that different comparator.
Evidence: research_plan_v3.7.md §8.2 and src\ncm_sudoku\e3controls.py:174–189 specify permutation
during training and validation only; the control receives the unpermuted TEST representation. H1
therefore compares differently trained probes, not related versus unrelated representations at
evaluation.
Recommendation: Replace the “unrelated state” formulations with “a control probe trained and
selected on independently permuted representation–label pairs.” Preserve the registered contrast and
intact TEST evaluation; no new analysis is needed.
Confidence: high

SOL-2 | major | paper\main.tex:12; paper\sections\introduction.tex:16;
paper\generated\tables\readings.tex:9
Claim: The new checkpoint-training qualification has not propagated throughout the manuscript. The
abstract and introduction still assert corruption training for this checkpoint, and the
interpretation table presents the corresponding conditional row as triggered without identifying its
unverified premise.
Evidence: research_plan_v3.7.md:171 explicitly records missing checkpoint training metadata.
paper\sections\e2.tex:33 and paper\sections\discussion.tex:23 now correctly make this interpretation
conditional, unlike the headline summaries.
Recommendation: Attribute corruption training to the NCM method in the abstract and introduction, or
state the checkpoint assumption explicitly. Annotate the interpretation table’s training premise as
assumed rather than verified, while preserving the verbatim registered row and frozen evaluation
outputs.
Confidence: high

SOL-3 | major | paper\sections\appendix.tex:20
Claim: The reproducibility paragraph does not identify the upstream checkpoint/data versions,
explain which underlying artifacts readers receive versus regenerate, or disclose measured compute.
This omission is separate from the acknowledged repository-URL placeholder.
Evidence: .gitignore:7–12 excludes datasets, checkpoints, raw runs and fitted .pt files. The missing
provenance is available in experiments\provenance\checkpoints.json:18–20 and
experiments\provenance\released_data.json:13–15; experiments\wp2\test\results.json:20–87 records the
environment and runner durations. scripts\lock_test_set.py documents fresh-data regeneration and
identity hashes.
Recommendation: Add a concise availability/compute paragraph pointing to the pinned provenance
manifests and fresh-data regeneration recipe; distinguish committed summaries from raw outputs and
fitted probes. Report hardware/thread settings and measured runtimes, clearly distinguishing TEST
execution from preparation and pilots.
Confidence: high

SOL-4 | minor | paper\sections\e3.tex:22; research_plan_v3.7.md:271 | The separately specified
raw-input-minus-generated estimates and intervals are omitted, although individual Briers are shown;
add both contrasts from experiments\wp2\test\results.json:533–584 to a supplementary table.

SOL-5 | minor | paper\sections\e2.tex:41; src\ncm_sudoku\wp4figures.py:32–53 | The registered
damage-axis sensitivity curves are absent: plan §7.3 requires them, and results.json:1039 onward
contains their nodes. Unavailable common-range AUC does not prevent plotting separate curves;
include them or explicitly disclose this reporting omission.

SOL-6 | minor | paper\sections\discussion.tex:14 | “A many-to-one quantizer can absorb a replaced
code” misidentifies the relevant mapping: replacements occur after code selection, and branch C
simply substitutes indices (src\ncm_sudoku\intervene.py, run_branches). Say that different code
sequences can decode to the same grid.

SOL-7 | minor | paper\sections\e2.tex:9 | “One position and one value” per dose incorrectly
describes multi-code doses; clarify that dose k selects k distinct positions and replacement values,
with three seeds (src\ncm_sudoku\perturb.py:41–71).

Claims checked

 - holds — H1 is 0.0029 Brier, 98.33% interval [0.0025, 0.0033]; its separate 96.67% TOST interval
establishes equivalence within ±0.01.
 - holds — H2 is −11.1 percentage points, family interval [−13.6, −8.8]; the magnitude interval
[8.8, 13.6] is transformed correctly.
 - holds — H3 is +1.7 points, family interval [0.1, 3.3]; attenuation is supported, but exceeding
the 3-point practical threshold is not established.
 - holds — E1 teacher reconstruction is 100%, generated solve share 87.7%; reproduction and
distribution-gate values match their source records and macro mappings.
 - holds — Levels 2 versus 11 use the one-sided 95% rare-event bound; level-12 teacher equivalence
uses 90% TOST, not a primary-family interval.
 - holds — All six figure functions match their captions’ series and interval conventions; forest
thresholds are row-specific, propagation distances relative, and inspected cross-references resolve
correctly.
 - holds — The substantive citation claims, including Quantix-eng, narrowed Khoury, Oh and Garg,
match the repository’s verified quotations; the eight original bibliography entries match the
recorded metadata.
 - holds — Local lock/run records support registration before TEST model execution, wp2-code commit
1047668, and disclosure that E4 was dropped after TEST without evaluating SELECT.
 - holds — The author line matches the local author decision; the AI-use disclosure is consistent
with the recorded workflow, and MIT code/CC BY 4.0 paper licensing is locally consistent.
 - could not verify — Expanded given names in the new Oh/Garg entries are absent from the
abbreviated verification notes; live OSF/ORCID status and final PDF appearance cannot be established
from the permitted file-only review.


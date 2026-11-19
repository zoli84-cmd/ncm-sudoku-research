Verdict

I would make one wording change before submission: say the repository link is withheld for
double-blind review, not that the already-public code will be released. The anonymous PDF itself
contains no identifying author link, the main text ends on page 12, and the new numerical
disclosures check out.

Findings

ASTRA-1 | minor | paper\sections\appendix.tex:20
Claim: “The code in the repository will be released under the MIT license” implies that release and
licensing are still pending. The offer of an anonymized archive is compatible with double-blind
review, but the committed files cannot be sent unchanged.
Evidence: DECISIONS.md:123,125–126 records that the repository was public and its frozen tags
reachable without login; LICENSE:1–5 already grants the MIT license. pyproject.toml:5–6 identifies
the author, and experiments\wp2\test\results.json:5–13 contains the project's own commit and tag.
None of those identifiers appears in the submitted PDF.
Recommendation: “The code is MIT-licensed. We withhold the repository link for double-blind review
and will include it in the final version.” Keep the archive offer; screen the package metadata and
result files before providing it through OpenReview.
Confidence: high

ASTRA-2 | minor | paper\sections\discussion.tex:27
Claim: The untested readout is a nonlinear readout of the latent cell and peer states. Without that
qualifier, the sentence also describes a raw-input control that was tested.
Evidence: src\ncm_sudoku\e3controls.py:276–279 fits an MLP to the raw cell and all 20 peers without
PCA. The whole-layer latent fits are linear (src\ncm_sudoku\wp2e3.py:186–192). The marginal per-cell
gain is accurate at level 6: Brier fell from 0.2310 to 0.2309, versus 0.1859 to 0.1828 at level 12
(experiments\wp2\test\results.json:18243–18262).
Recommendation: Specify “a nonlinear readout of the cell and peer states” and “at level 6, the
per-cell MLP improved only marginally.”
Confidence: high

ASTRA-3 | minor | paper\sections\discussion.tex:31
Claim: The revised E2 paragraph gives both reasons the area comparisons were unavailable, but the
discussion still attributes the result solely to missing TEST coverage. That explanation does not
apply to 2 vs. 11.
Evidence: research_plan_v3.7.md:211,422 defines two pairwise comparisons. For 6 vs. 11, level 11
covered the frozen interval; level 6 stopped at 7.16×10⁻⁵, short of the 7.93×10⁻⁵ upper endpoint.
For 2 vs. 11, CAL had no positive-width common range to freeze
(experiments\wp2\test\results.json:1025–1109).
Recommendation: Cut the repeated explanation from the discussion and refer to §6.4, where both
reasons are given.
Confidence: high

ASTRA-4 | minor | paper\sections\e2.tex:40
Claim: The new propagation sentence gives the correct count but omits the branch. It applies only
when later codes are regenerated; replay leaves those codes unchanged.
Evidence: scripts\wp2_evaluate.py:435–437 aggregates later_changes_D;
experiments\wp2\test\results.json:10436–10447 gives 3.2581 at level 11. Branch C replays the
original codes (paper\sections\e2.tex:7).
Recommendation: Write “Under the frequency policy, regenerating after one level-1 replacement
changed an average of 3.3 level-11 codes relative to the clean run (branch D).”
Confidence: high

ASTRA-5 | minor | paper\sections\appendix.tex:22–41,70–86
Claim: The page breaks stop floats from drifting into later material, but the A.3 heading is alone
at the end of page 14; both E1 objects are on page 15. Figures A.2 and A.5 also print above their
own subsection headings on pages 16 and 18, so following the subsection link lands below the figure.
Evidence: The PDF placements agree with paper\build\main_anon.aux:130–138,145–147. The figure and
subsection destinations are distinct and correctly numbered.
Recommendation: Start A.3 with its table on page 15 and prevent the first E2 and E3 figures from
floating above their headings. No numbering change is needed.
Confidence: high

ASTRA-6 | nit | anonymous PDF, pp. 9–10 (§7.3)
Claim: The reflow leaves “Still, the teacher’s” at the foot of page 9; “level-12 state” follows
Figure 2 and its caption on page 10.
Evidence: The split is inside the subject of the sentence at paper\sections\e3.tex:30; the previous
rendered page kept that subject together
(.reviews\paper-wp5-tmlr\round-final\transcript.astra.md:1652–1655).
Recommendation: Keep “the level-12 teacher state” together when reflowing the final copy.
Confidence: high

Claims checked

 - holds — The solution-digit reference is post-TEST and exploratory. The TEST candidate rate gives
Brier 0.1822575, printed as 0.1823, close to the level-12 generated and teacher whole-layer losses
of 0.1833 and 0.1834. It is an analytic comparator, not another fitted probe
(src\ncm_sudoku\wp4numbers.py:340–347; DECISIONS.md:124).
 - holds — Level-1 branch-C format errors are 13.9% under uniform weighting and 0.7% under frequency
weighting. Malformed outputs score zero and remain in the solve denominator
(experiments\wp2\test\results.json:3068,3133; src\ncm_sudoku\validate.py:68–85;
src\ncm_sudoku\e2p2.py:625–638).
 - holds — §6.4 correctly reports both unavailable areas as pre-specified outcomes, not run
failures. The 3.3 propagation value is descriptive and correct for D. Does not hold — the
discussion's single explanation covers both pairs, or the propagation count applies to replay.
 - holds — The primary training-size curve falls from 0.2365 at 125 puzzles to 0.2307 at 2,000; the
text does not claim an observed gain beyond 2,000. The per-cell MLP comparison holds at level 6.
Does not hold — nonlinear cell-plus-peer readouts were untested irrespective of input
representation.
 - holds — The locked plan explicitly expected similar Brier loss but non-equivariance at the
seed-noise tolerance, based on PROBE-VAL; the registration calls this exploratory. TEST gives
deviation 0.0791 against 0.0116 and transformed/original Brier 0.1837/0.1839
(research_plan_v3.7.md:283; osf\registration.md:3–5,33; experiments\wp2\test\results.json:997–1021).
 - holds — The PDF links take E1 to Table A.2 and Figure A.1 in Appendix A.3, E2 to Figures A.2–A.4
in A.4, and the E3 training curve to Figure A.5, left, in A.5. The equivariance detail is in A.5 and
Table A.11 in A.7. The object names distinguish figures, tables and subsections even when their
numbers match. All four requested \clearpage breaks are present.
 - holds — The anonymous branch rendered without the author's name, own repository or registration
identifiers in the visible text, PDF Info, bookmarks or external link targets; the PDF has no XMP
packet or embedded archive. The AI-use statement ends and references begin on page 12
(paper\build\main_anon.aux:111). Could not verify — the contents of a future reviewer archive; none
was supplied for this review.


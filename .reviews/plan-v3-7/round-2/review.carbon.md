Elolvasom a megadott review briefet (`brief.carbon.md`), és pontosan követem az abban foglalt csak olvasható ellenőrzési utasításokat.

Elolvastam a review briefet; most áttekintem a round-1 döntéseket, a terv diffjét és az új kódváltoztatásokat.

Verdict

Yes — all ten round-1 findings (CARBON-1..CARBON-6, ASTRA-1..ASTRA-4) are substantively and
correctly resolved in research_plan_v3.7.md and the codebase, with no blocker or major issues
remaining, so v3.7 is ready to proceed to the final review. Before tagging the lock, reconcile the
stale frozen level-1 frequencies and D53–D71 summary text in §16 (research_plan_v3.7.md:580, 586)
and §7.2 (research_plan_v3.7.md:180) with §12.2 and DECISIONS.md D72–D73, and pin cal_freqs.json's
SHA-256 in tests/test_lock_cal_freqs.py.

Findings

CARBON-1 | minor | research_plan_v3.7.md:6, 180, 580, 586; DECISIONS.md:111–112 | Claim: Section 16
(research_plan_v3.7.md:580, 586), Status: (line 6), and §7.2 (line 180) were not updated alongside
§12.2 and D72–D73, leaving §16 item 36 stating frozen level-1 frequencies instead of frozen CAL
frequencies across levels 1, 2, 6, and 11 and omitting the R1 revision entry required by line 7.
Evidence: r1-fixes.diff ends at §14.2 (line 500), leaving research_plan_v3.7.md:580, 586 at D53–D71
and frozen level-1 frequencies (unlike v3.6 items 30–31 at lines 576–577), while
research_plan_v3.7.md:180 still reads TEST uses the frozen CAL vector (singular) even though
DECISIONS.md:111 (D72) cites v3.7 §7.2 as updated. Recommendation: Update research_plan_v3.7.md:6,
580 to D53–D73, clarify in line 180 that levels 2, 6, and 11 also use frozen CAL frequency vectors
(Section 12.2), change line 586 from frozen level-1 frequencies to frozen CAL code frequencies, and
add a Section 16 bullet summarizing the v3.7 R1 revisions (D72–D73). Confidence: high

CARBON-2 | minor | tests/test_lock_cal_freqs.py:42–79; src/ncm_sudoku/e2p2.py:59–70;
research_plan_v3.7.md:426 | Claim: Unlike wholelayer.PEER_IDX (tests/test_peer_order.py:10, 20–22)
and the generator files (src/ncm_sudoku/subsets.py:12–25), the locked
experiments/lock/cal_freqs.json artifact and its SHA-256 (0cc72927...) are not checked by any test
or loader guard. Evidence: research_plan_v3.7.md:426 and DECISIONS.md:112 (D73) lock
experiments/lock/cal_freqs.json SHA-256
0cc7292718750754baf27b813a4095e2a7479cf4e480fbed50e43c665c7983fb, but
tests/test_lock_cal_freqs.py:42–79 and tests/test_e2p2.py:173–185 run only on synthetic tmp_path
JSONs and never load or hash the committed file. Recommendation: Add a test in
tests/test_lock_cal_freqs.py asserting that experiments/lock/cal_freqs.json matches SHA-256
0cc7292718750754baf27b813a4095e2a7479cf4e480fbed50e43c665c7983fb and loads cleanly via
e2p2.load_frozen_freqs. Confidence: high

Claims checked

 - Holds: experiments/lock/cal_freqs.json counts at levels 1 (sum 300), 2 (600), 6 (3,900), and 11
(20,100) match research_plan_v3.7.md:426–427, level-1 frequencies match
experiments/e2p2/summary.json:10–27 identically, deterministic: true is recorded after load_model
(scripts/lock_cal_freqs.py:47–48), e2p2.run_pilot2(frozen_freqs=...) and load_frozen_freqs enforce
exact float64→float32 count consistency, and perturb.run_seed plus bootstrap seed 0 match §12.2
(line 428).
 - Holds: grid.PEER_ORDER (81 × 20) preserves the exact CPython frozenset peer sets
(src/ncm_sudoku/grid.py:34–116, tests/test_peer_order.py:13–41), wires into e3data._PEERS_IDX and
wholelayer.PEER_IDX with SHA-256 57cc1251a39285a9dc5201f2b0b11d825f3f8850db5b356ab7b8187b4f582e1d
(research_plan_v3.7.md:430), and §8.1 (lines 231, 235) matches wholelayer.py:45–66,
e3controls.py:31, 38–49, and wholelayer_report.md:13–19 on 1/N float64 covariance, sign rule, 1e-10
whitening threshold, seeds 11/12/0, and selected configs [0.1, 1e-3] / [0, 3e-3].
 - Holds: §8.1 (research_plan_v3.7.md:227) and §8.3 (line 278) match probes.py:265–272,
e3controls.py:92–100, 215–217, scripts/e3_probes.py:91–100, and e3equiv.py:82–84 (all Brier
endpoints average per-seed puzzle-level Briers; thresholded and ranking metrics use seed-averaged
predictions with probability threshold fixed at 0.5).
 - Holds: The four H1 rows in §13 (research_plan_v3.7.md:465–468) together with Non-significant
result (line 471) mutually exclusively and exhaustively partition all (98.33% CI, 96.67% TOST CI)
outcomes, require 98.33% lower limit > 0 for above-null readability matching §8.3 (line 266) and
power.h1_tost (src/ncm_sudoku/power.py:251–260), and §8.3 (line 268) qualifies level-12
teacher–generated equivalence within ±0.01.
 - Holds: §8.1 (research_plan_v3.7.md:233) transparently justifies the pre-TEST switch from per-cell
(0.0018, D64) to cell-relative whole-layer (0.0031, D67) with ±0.01 equivalence, and §11.4 (line
392) accurately cites mean|x| = 0.0100 < 0.03 (experiments/e2p2/sample_size_e2.json:11–12) and notes
the low-discordance ±1 injection caveat.
 - Holds: e3equiv.equivariance_pilot accepts fixed acceptable (0.0116, locked from 0.01164455 in
experiments/lock/equivariance_l12.json:301) on puzzles[:200] while reporting seed_noise_p95
(src/ncm_sudoku/e3equiv.py:45, 89–101), §8.4 (line 286) matches the stored per-category deviations
(0.079 full-group, 0.066 digit-only, 0.077 geometric-only; 0% within; Brier 0.1828 vs. 0.1828), and
§3/§8.4/§12.2/§13 consistently scope registration to the non-augmented test without family holdout.
 - Holds: Full-precision 6 vs. 11 AUC bounds [3.291773618630916e-05, 7.930234551597304e-05]
(research_plan_v3.7.md:429) match experiments/e2p2/summary.json:2075–2078, TEST hash formats and
SHA-256s (line 423) match scripts/lock_test_set.py:42–48, 76–78 and
experiments/lock/test_set.json:615–623, and released-dataset revision 6580ba41... plus pickle
SHA-256s match experiments/provenance/released_data.json:6–16.
 - Could not verify: Byte-level SHA-256 digests (0cc72927... for experiments/lock/cal_freqs.json,
57cc1251... for wholelayer.PEER_IDX, and git-ignored TEST/checkpoint binaries) were cross-checked
against DECISIONS.md:112, tests/test_peer_order.py:10, and committed JSON records, not recomputed
via command execution per the read-only brief.


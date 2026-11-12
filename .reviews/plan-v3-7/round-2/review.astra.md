VERDICT: PASS
The review satisfies the brief’s scope, structure, and length limits. Independent inspection supports both minor findings and the central fix checks. The denied home-level `AGENTS.md` read is disclosed and unnecessary; execution and fresh-digest limitations are clearly stated.

Verdict

The substantive round-1 fixes are sound enough to proceed to final review; I found no remaining
blocker or major issue within scope. The most important correction is that explicitly supplied CAL
frequencies now drive both level-1 weights and level-2/6/11 replacement draws, rather than
estimating the intervention policy on TEST.

Findings

ASTRA-1 | minor | research_plan_v3.7.md:424–435 — Claim: The round-1 edits break the rendered lock
checklist. Evidence: The blank line at 424 terminates the table; the E2 row spans physical lines
426–428, and its seed specification contains unescaped pipes. Recommendation: Restore a continuous
table, keep each row on one physical line, and escape the seed-string pipes. Confidence: high.

ASTRA-2 | minor | research_plan_v3.7.md:580–587 — Claim: The version history does not record the
round-1 corrections despite the completeness promise at line 7. Evidence: §16 still ends at D71 and
names only frozen level-1 frequencies, whereas DECISIONS.md:110–111 records D72/D73, including
freezing additional levels and correcting the H1 interpretation rule. Recommendation: Add a concise
D72/D73 revision entry covering the accepted fixes. Confidence: high.

Claims checked

 - holds — CARBON-1: e2p2.py:43–74,91–92,137,156–161 routes supplied frequencies to both
intervention paths; the loader checks count–frequency consistency. All four printed count vectors
match cal_freqs.json, totaling 300/600/3,900/20,100; level-1 frequencies exactly match
summary.json:11–28.
 - holds — CARBON-2: Both feature builders use the literal PEER_ORDER; the plan’s peer digest
matches tests\test_peer_order.py:11. PCA divisor, float64 accumulation, sign and whitening rules
match wholelayer.py; control seeds and selected configurations match the implementation and
wholelayer.json.
 - holds — CARBON-3/4: Per-seed Brier averaging matches probes.py:264–281, depth aggregation and
equivariance scoring. §8.1 explicitly discloses the outcome-informed H1 switch; the revised
mean-absolute-difference explanation is consistent with power.sign_mix’s feasibility condition.
 - holds — R1 ASTRA-1/3: §13 now requires a positive 98.33% lower limit plus the 96.67% equivalence
interval, matching §8.3 and power.py:237–279; teacher–generated equivalence is appropriately
restricted to ±0.01 and the examined readout.
 - holds — CARBON-5 and R1 ASTRA-2: e3equiv.py uses the supplied tolerance without replacing it with
TEST seed noise, while reporting that noise separately; selection is the first 200 puzzles. The
three deviation figures and zero within-tolerance shares match equivariance_l12.json:300–316;
augmentation/family holdout are explicitly excluded.
 - holds — The full-precision AUC endpoints match summary.json:2068–2070; TEST hash encodings match
lock_test_set.py:44–50 and test_set.json:620–623; released-data revision/hash strings match their
provenance record. The probability threshold is explicitly fixed at 0.5.
 - holds — R1 ASTRA-4: lock_cal_freqs.py:47–48 captures the environment after model loading, which
enables deterministic algorithms; cal_freqs.json:16 records true. D73 explicitly identifies the
older pilot’s stale false flag rather than silently revising its provenance.
 - could not verify — Freshly computed file/array digests or test execution: execution was
prohibited, so these checks were limited to source and recorded values. An initial home-level
AGENTS.md read was denied; its content was not accessed. No files were changed.

Blocked actions:

 - read (tool call call_sCLrM0tpTH7QbUhmzycADDGK)


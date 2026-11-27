# E5 dry_perm results

DRY RUN on the PROBE-VAL pairs (protocol §9.4); not TEST

- Run status: finished
- Claim A outcome: holds
- Claim B outcome: holds
- Conditions: {"A1_lower": true, "A1_upper": true, "A2": true, "A": true, "B1": true, "B2": true, "B3": true, "B4": true, "B": true}
- log K: {"A1_lower": 12.015770183150437, "A1_upper": 9.14065117065617, "A2": 33.45214654228771, "B1": 7.239700034191623, "B2": 8.535168037741592, "B3": 5.284611603665436, "B4": 22.065950670114887}
- Invalid reasons: {"shared": [], "A": [], "B": []}

## Interpretation (protocol §8)

Rows selected by the outcomes; text copied verbatim from `e5_protocol_v1.md` §8.

| Result | Justified claim | Does not follow |
|---|---|---|
| Claim A holds | On average over the eligible pairs (equal weight per pair), the frozen own-position linear probe reads the one-step candidate mask within pairs from the prefix at layer 2 far better than from Z<=6 (difference > 0.25), and its within-pair readout of Z<=6 is practically equivalent to non-discrimination (within 6 net correct orderings per 100 discordant comparisons, forced ties included) | Exact or calibrated decoding of the full candidate mask (the test ranks discordant bits within pairs); Z<=6 carries no candidate information; no other readout could read it; equal capacity of the two readouts (256- vs. 512-dimensional inputs); the generator uses the encoded candidates |
| Claim B holds | Under this interchange intervention with levels 1–6 fixed, the T = 1 level-7 code distribution moves towards the both-empty full-swap reference by more than 1 percentage point of TV on average, and more than under norm-matched random subspaces, the high-variance control and the shuffled-digit control | A digit-specific mechanism (the controls are matched in norm, not in alignment with the full difference); changes of argmax codes, later levels or solving; the generator performs candidate reasoning |
| Claims A and B hold | The average of the three frozen P2 heads ranks the discordant candidate bits of the eligible pairs far better than the Z<=6 readout, which is practically equivalent to non-discrimination, and the level-7 code distribution is sensitive to the candidate subspace beyond the named controls: the weak level-6 readout is consistent with a property of the cumulative state rather than with an absence of the information in the generator | Exact or calibrated decoding of the full candidate mask; the generator reasons about candidates; the result transfers to other checkpoints, levels, readouts or interventions |

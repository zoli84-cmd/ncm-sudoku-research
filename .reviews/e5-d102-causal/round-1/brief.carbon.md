# Review brief: E5 D102 draft: activation-exchange causal test

You are an independent senior reviewer giving a second opinion. You have no access to the conversation that produced the artifact; everything you need is in this brief, the artifact and the repository.

## Hard rule: read-only

Do NOT create, modify, move or delete any file, and do not run commands that change state (no git commit/checkout/stash/reset, no package installs, no formatters). Read files and search the code only. Return your review as your final answer; do not write it to disk.

## Artifact

- C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/docs/superpowers/specs/2026-11-25-e5-d102-causal-design.md (the artifact)
- Context it builds on: C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md, decisions D91–D101 in C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/DECISIONS.md, pilot results C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/experiments/e5/pilot/*.json
- Code: C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/third_party/ncm/models/next_concept.py (generate, _decode_level_logits), C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/intervene.py, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/e5extract.py, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/e5pilot.py, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/probes.py, C:/Users/ako2bp/Documents/VS Code Projects/NCM-research/src/ncm_sudoku/e5pairs.py

## Context

The project studies a released Next-Concept Modeling (NCM) Sudoku generator; its submitted manuscript (under review, unchanged) found the candidate mask only weakly readable from the cumulative latent state Z<=6. E5, a separately preregistered follow-up, asks whether that weakness is a property of the state or of the generator. A non-confirmatory pilot on counterfactual pairs (one solution, two clue masks) found the candidate mask perfectly linearly readable within pairs from the generator's prefix (puzzle-encoding) positions at layers 2-3, but at control level in Z<=6, also with a converged L-BFGS reference and by online MDL (D100, D101). Readability does not show use, so the artifact specifies a pilot causal test: an interchange intervention swapping a probe subspace of the layer-2 prefix states between pair members during generation, with random equal-rank subspaces, a full swap and a sham as controls. Risk tier: medium (pilot design, revertable, no high trigger); it will shape a later preregistration, so causal-inference validity matters most.

## Decision log from previous rounds

none

If a decision log is given: do not re-raise a rejected point unless you have new evidence, and then say what is new.

## What to check

Generic checks, always:
1. **Fact-check**: verify every concrete claim about the code (files, lines, behaviour) directly in the repository. Say for each checked claim whether it holds.
2. **Hidden risks in the proposed solution**: failure modes, edge cases, concurrency, serialization, migration and rollback, performance under real load, security.
3. **Missing issues or simpler alternatives**: anything important the artifact misses, and any simpler approach that would achieve the same goal.
4. **Prioritization and scope**: is the proposed order and scope right? What should be cut?

Specific focus for this artifact:
- Feasibility against the code: can the intervention be implemented as specified with forward hooks on `net.transformer.blocks[k]` during `NextConceptTransformer.generate` (third_party/ncm/models/next_concept.py) in every pass, patching only prefix cell positions (PREFIX_CELLS in src/ncm_sudoku/e5extract.py), and is the claim right that prefix positions attend only to the prefix so the patch affects queries only through attention?
- Validity of the probe subspace: Q is built from the nine digit rows of the frozen pilot P2 shared head (src/ncm_sudoku/probes.py `_make_model`, linear on state || cell one-hot) restricted to state coordinates; is that a sensible candidate subspace, given that the shared head is shared across cells and inputs were not standardized? Is a random orthonormal 9-dim subspace the right control (norm of the projected difference, alignment with high-variance directions)?
- Whether the behavioural outcomes can show anything: both members share the solution, so a solver should output the same grid; is code change / grid change / rescue on the 51 one-solved pairs informative, or should the primary behavioural outcome be something else (e.g. code logits at the level-7 pass, or KL between patched and clean level logits, cf. src/ncm_sudoku/intervene.py `level_logits`)?
- Scope of the patch: all 12 passes vs. only passes after level 6 (keeping Z<=6 fixed); what each design can and cannot attribute (effect through Z<=6 vs. through direct prefix attention at later levels).
- The donor-follow rate definition under saturation (P2 probabilities near 0 or 1), and the primary contrast (probe minus mean of 5 random subspaces, pair-level bootstrap): statistical validity and whether 500 recipient runs suffice for a pilot.
- Missing identity checks or confounds (e.g. patching both-empty cells only while clue positions differ; whether swapping at positions empty in only one member should be included; position embeddings/RoPE unaffected).



## Output format

Respond in Hungarian. Use exactly this structure so the findings can be processed automatically.

### Verdict
One or two sentences: is the artifact sound enough to proceed, and what is the single most important change?

### Findings
One block per finding, most severe first. ID prefix: `CARBON`.

```
CARBON-<n> | <blocker|major|minor|nit> | <file:line or artifact section>
Claim: <what is wrong or missing, one or two sentences>
Evidence: <what you checked in the code, with file:line>
Recommendation: <concrete change>
Confidence: <high|medium|low>
```

Severity definitions:
- **blocker**: proceeding as written causes incorrect behaviour, data loss, a security issue, or a design that must be redone.
- **major**: a significant risk, a wrong claim that drives a decision, or a clearly better alternative that changes the plan.
- **minor**: a real but contained issue; fix if cheap.
- **nit**: wording, style or preference. Report at most three nits.

Rules: only report what you checked or can argue concretely. If you could not verify a claim, say so with Confidence: low. Do not pad: zero findings in a category is a valid result.

### Claims checked
A short list of the artifact's code claims you verified, each marked holds / does not hold / could not verify.

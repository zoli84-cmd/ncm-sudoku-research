# Pre-submission related-work update and bibliography check

**Date:** 2026-11-16
**Scope:** (a) work that appeared after, or was missed by, the search of 2026-11-08 ([related_work_novelty_check.md](related_work_novelty_check.md)); (b) verification of every entry of `paper/refs.bib` and of each sentence in `paper/sections/background.tex` and `paper/sections/discussion.tex` that cites it (with spot checks of the other citing sentences in `introduction.tex`, `setup.tex`, `e2.tex` and `e3.tex`); (c) recommended changes.
**Tools:** Consensus API, arXiv export API, Semantic Scholar Graph API, Exa search and contents API (`EXA_API_KEY` was set), GitHub REST API and raw file fetch, Zenodo records API, arXiv HTML full text, ACL Anthology, NeurIPS proceedings. Every query is in [query_log.md](query_log.md), section "Pre-submission update (2026-11-16)".
**Status:** a search and verification record, not a plan decision. Nothing in `paper/` or `refs.bib` was changed. Any adoption of the recommendations in section (c) is an editorial decision for the manuscript; it does not touch the locked plan, hypotheses or results.

## Summary

- **One finding affects a framing claim.** An unreviewed, AI-assisted GitHub repository (Quantix-eng, "NCM experiment notes", created 2026-10-26) contains exploratory probes and interventions on the released NCM Sudoku checkpoints: a naked-single probe on generator states with a shuffled-label control and a non-specific causal ablation, a residual omission with native versus regenerated later contributions, input/state exchanges under fixed and regenerated tails, per-level reversals of decoded digits, and output equivariance of the checkpoint under digit relabelling, rotation and reflection. It does not run a preregistered level-1 versus level-11 replacement contrast, candidate-mask probes on cumulative states, or a permuted/teacher/raw-input control matrix. The paper makes no explicit "first study" claim (checked: no "to our knowledge", "first" or "novel" in `paper/sections/*.tex`), so no sentence becomes false. But the "Relation to prior work" subsection now omits the closest NCM-on-Sudoku interpretability work. The earlier search note's claim that "none of [the NCM follow-ups] does mechanistic or probing work on Sudoku" no longer holds as of 2026-11-16.
- **One citing sentence is only partly supported.** Khoury (2026) reports 61–96% code rewrites on re-encoding for *text* samples, but only 2–20% per level on the Sudoku-hard checkpoint (Section 5.8 of the v2 PDF). The discussion sentence presents non-canonicality as a property of "generated NCM codes" without this qualification. The 2026-11-08 search had read only the abstract.
- **The trained-robustness sentences are supported for the NCM method, not specifically for the Sudoku checkpoint.** The NCM paper describes conditioning corruption as part of generator training (Section 3.4) and ablates it on TinyStories (Appendix F.3). It gives no Sudoku-specific corruption setting, and the plan (§7, "Trained robustness") already records that the released checkpoints carry no training metadata.
- **Kniazev & Fijalkow are cited correctly in the paper.** The per-cell *candidate* probes reach 1.0 exact match in layers 4–6 (Section 3.1); the 0.8 plateau belongs to the per-cell *filled-digit* probes. The 2026-11-08 novelty note says the reverse ("per-cell candidate probes plateau at about 80%"); the paper text is right and the note is wrong.
- **Bibliography:** all 8 entries resolve to the cited works; titles and years are correct. All entries need full author lists. Venue or identifier fields are missing for Shah et al. (NeurIPS 2024), Hewitt & Liang (EMNLP-IJCNLP 2019) and Belinkov (Computational Linguistics 48(1)). Khoury's DOI is the concept DOI; the latest version (v2) has its own DOI.
- **Citation graph:** Semantic Scholar still lists 0 citing papers for NCM (arXiv:2610.14162), Kniazev & Fijalkow and Rodrigues & Kang. Its keyword search was rate-limited (HTTP 429) on several calls; see the query log.
- **Other new work** (probing methodology, Sudoku diffusion diagnostics) supports the paper's design choices and changes no claim. Garg (2026, "floors and ceilings") is the closest methodological match to the raw-input and surface-statistics controls.

## (a) New or newly relevant works

Only works whose primary source (abstract at minimum) I opened are listed. "Rel." = relevance: H = high, M = medium, L = low. "Verdict" states whether the work changes a novelty claim or the paper's related-work text.

### NCM follow-ups

| Citation | Link | What they did (quoted passage) | Relevance | Verdict | Rel. |
|---|---|---|---|---|---|
| Quantix-eng (2026). NCM experiment notes: twenty exploratory studies and related controls. GitHub repository, MIT licence, no DOI, not peer reviewed; created 2026-10-26, HEAD `89a165ce01f06ce27dc097c2b2f805c288d6dde3`. The author is identified only by the GitHub account name (`CITATION.cff`: `name: "Quantix-eng"`). | [github.com/Quantix-eng/ncm-experiment-notes](https://github.com/Quantix-eng/ncm-experiment-notes) (README, `docs/scope.md`, `docs/related-work.md`, `CITATION.cff`, experiment READMEs 01, 06, 09, 10, 12, 16, and `experiments/10-initial-audit/src/analyze.py`, `recorded/symmetry.json`, `recorded/constant_level.json`, `recorded/naked_single.json` read at that commit) | 20 exploratory studies, 11 on NCM, mostly Sudoku. Exp. 10 (E05): "Fit a naked-single probe with shuffled-label control, then test whether the feature-specific causal intervention is selective. **Result.** The audit found the constant intermediate level and a naked-single probe with AUROC 0.877 versus 0.496 with shuffled labels. The causal ablation was not specific." The code comment in `analyze.py` describes the probe input as "final-level states at cells; labels are computed only from the initial prompt", and the record notes `explicit_candidate_baseline_auc=1.0`. Exp. 09 (E08): "Omit residual 9, cross native and regenerated later contributions … The announced joint criterion fails." Exp. 16 (E13): "Exchange input and retained state across Sudoku families under fixed and regenerated tails … Regeneration returns the recipient solution in 32/32 swaps, but a recipient-native frozen continuation does so too." Exp. 06 (E03): "25.04% of the cells corrected between levels 8 and 9 become wrong again later." `symmetry.json` (128 puzzles; the difficulty is not stated in the file): output cell agreement under digit relabelling 0.981, rotation 0.975, reflection 0.979. `constant_level.json`: zeroing the level-5 residual changed 4 of 128 boards and no solve outcome ("Selected after observing constant VQ codes"). The README says: "AI tools contributed substantially to planning, code, analysis and writing" and "There is no claimed model-performance breakthrough or independent human replication." | E1 (level-wise decoding), E2 (fixed versus regenerated tails, omission), E3 (naked-single probe with shuffled-label control, decodable but not causally specific; output equivariance) | **Changes the related-work text, not a confirmatory claim.** It is the only other probing and intervention work on the NCM Sudoku checkpoint that I found. Differences: no preregistration ("Local freezes … do not turn the whole exploratory history into a prospective preregistered study", `docs/scope.md`); probe target is naked singles on generator states, not the candidate mask on the cumulative state $Z_{\le\ell}$; no permuted-state, teacher or raw-input control; omission and exchange interventions rather than single-code replacement at equal edit cost; equivariance tested on outputs, not on probe predictions. Their "decodable, causal ablation not specific" result agrees in direction with Rodrigues & Kang and with our weak level-6 readout. The repository states that full inference workflows "remain unvalidated after relocation", so its numbers are unverified recorded outputs. I did not rerun anything. | H |
| Khoury, P. (2026). Round-Trip Refinement: A Training-Free Sampler for Next-Concept Language Models. Zenodo preprint v2 (2026-10-31), not peer reviewed. *Already tabled; newly relevant through the Sudoku section.* | [doi:10.5281/zenodo.23826875](https://doi.org/10.5281/zenodo.23826875) (v2); concept DOI [10.5281/zenodo.23737645](https://doi.org/10.5281/zenodo.23737645); PDF read | Section 5.8: "On the released Sudoku-hard model (1,000 test puzzles, greedy decoding as configured), every restart level solves more puzzles than the released sampler (Table 10): from 84.1% to 85.5% with RT6 … here the round trip changes only 2–20% of the codes per level, far less than the 61–96% on stories, because a Sudoku board leaves the tokenizer little freedom." Section 1: "In training, by contrast, the coarser levels are the tokenizer's codes for real text, perturbed by uniform code replacement ['conditioning corruption'; 13, §3.4]." | E1, E2 | **Changes one discussion sentence (partly supported, see (b)).** Non-canonicality is large for text and small for the Sudoku-hard checkpoint. The rationale for reporting cell-level outcomes next to code-level counts still holds, but it should not rest on the text-checkpoint figure. No change to novelty: Khoury does not run a fixed-suffix control or an equal-cost level contrast. | H |
| Seemann, R. (2026). Fast but Imprecise? Next-Concept Models versus Autoregressive Language Models, and Fusing Them with PlanSpec. Zenodo preprint v1, not peer reviewed. | [zenodo.org/records/23564347](https://zenodo.org/records/23564347) (abstract and first page read) | "We compare a released NCM with AR models on speed, quality and precision (numbers, names, code), and find that NCM's tokenizer and generator lose names far more often than ordinary tokens." | E1 (tokenizer versus generator errors, text) | No change. Text tasks only; a text analogue of the E1 decomposition. | L |
| Rahmani, A. (2026). Next-Concept Models on a Laptop GPU: A Fair Benchmark Against Autoregressive Models, and What Their Speed Is Worth in RAG and Agents. Zenodo report, not peer reviewed. | [doi:10.5281/zenodo.23837501](https://doi.org/10.5281/zenodo.23837501) (abstract only) | "The official NCM checkpoints are compared with same-size autoregressive models … on summarization, translation and Sudoku … A suite of eight experiments probes input and output length, batch size, faithfulness, robustness, out-of-distribution Sudoku, and agent reliability." | G0 context | No change. Behavioural benchmarking; "probes" means test conditions, not representation probes. The Sudoku details were not read. | L |

### Sudoku and masked-diffusion diagnostics

| Citation | Link | What they did (quoted passage) | Relevance | Verdict | Rel. |
|---|---|---|---|---|---|
| Oh, M., Kim, J., Koo, J., Kim, Y., Seo, J., Seol, M. & Lee, J. (2026). Learning When Diffusion Language Models Should Regenerate. | [arXiv:2611.17320](https://arxiv.org/abs/2611.17320) (abstract) | "Our diagnosis on Sudoku reveals two gaps. Hidden states contain error information that token confidence does not reliably expose, and remasking an isolated error usually reproduces it when the surrounding context remains fixed." | E2 (fixed versus regenerated context) | No change. A masked-diffusion analogue of the observation that regeneration with a fixed context does not undo an error. It could be cited next to the H3 discussion, but it is a method paper with a behavioural diagnosis, not a controlled contrast. | M |

### Probing methodology (decodability, controls, validity)

| Citation | Link | What they did (quoted passage) | Relevance | Verdict | Rel. |
|---|---|---|---|---|---|
| Garg, P. (2026). How High Is 0.6? Floors, Ceilings, and Headroom in Interpretability Probing. | [arXiv:2610.08544](https://arxiv.org/abs/2610.08544) (abstract) | "We propose reading every probe score against two reference points: a floor, what a declared set of simple inputs already predicts, and a ceiling, what the full input can predict. … Against a floor computed from the input text alone, some of these claims hold, while others are largely explained by the text itself." | E3 (raw-input and surface-statistics controls) | No change to novelty. Concurrent support for reading the level-6 readout against the raw-input and surface-statistics references. A candidate citation for the "Probing with controls" paragraph. | M |
| Kutluozen, N., Internò, C. & Klindt, D. (2026). Is a Linear Probe Evidence of a Linear Representation? NeurIPS 2026 (per arXiv comment). | [arXiv:2610.22655](https://arxiv.org/abs/2610.22655) (abstract) | "Asymptotically, any sufficiently rich feature map, including a random one, admits a linear readout, so high probe accuracy is consistent with two very different geometries." | E3 (random-feature control) | No change. Supports the random-feature control and the claim boundary that readability is not representation. | M |
| Muthya Sudheendra, S. & Srivastava, J. (2026). When Decodability Is Not Enough: Logical Validity Representations, Behavioral Dissociation, and Causal Tests in Language Models. | [arXiv:2609.02438](https://arxiv.org/abs/2609.02438) (abstract) | "interventions along probe-derived validity directions have only weak, nonspecific effects compared with random controls." | E3 (framing) | No change. Same pattern as Rodrigues & Kang, in LLMs. | L |
| Xun, X. (2026). Lagged Coupling: Internal Representations Become Readable Before They Become Causal. | [arXiv:2609.01048](https://arxiv.org/abs/2609.01048) (abstract) | "a linear probe can read a target variable from the residual stream as early as step 1,000 at every scale -- yet steering along that same reading direction remains null-equivalent in 43 of 48 model-checkpoint cells." | E3 (framing) | No change. | L |
| Che, T. & Li, Y. (2026). Does the Model Use the Feature? Separating Steering from Mechanism in LLMs. | [arXiv:2610.07270](https://arxiv.org/abs/2610.07270) (abstract) | "Tracking a concept and steering a behavior therefore do not by themselves show that the model uses a feature, and each conclusion holds only for the intervention tested." | E3/E4 (claim boundaries) | No change. | L |
| Pereira, D. & Zuidema, W. (2026). Transformers Struggle to Use Their Emergent World Models: Revisiting the Tower of Hanoi, and the Illusion of Thinking. | [arXiv:2608.07077](https://arxiv.org/abs/2608.07077) (abstract) | "we show that these Transformers develop an emergent world model: a linearly decodable, geometrically faithful representation of the puzzle's state space … that is causally involved in solving the puzzles." | E3 (puzzle world-model probes) | No change. Missed on 2026-11-08 (posted 2026-08-07); puzzle task, not Sudoku. | L |
| Klein, A. (2026). Decodability Is Not Validity: Evaluating Nuisance Sensitivity in Language Model Concept Probes. | [arXiv:2611.07805](https://arxiv.org/abs/2611.07805) (abstract) | "extractors that are statistically equivalent in held-out AUROC differ up to several-fold in nuisance sensitivity … Concept measurements should be validated, not just decoded." | E3 (equivariance as a validity check) | No change. Loosely parallel to using symmetry consistency as a validity check of a probe. | L |

Read at abstract level and not tabled (judged not relevant enough): 2610.37411 (Sudoku difficulty under IP/CP-SAT formulations), 2610.29255 (hierarchical masked diffusion; Sudoku priority levels), 2610.02193 (hierarchical continuous diffusion LM), 2610.18174, 2610.18127, 2610.25646, 2610.16427, 2609.26487, 2611.08977, 2611.17309, 2610.26542, 2610.15081 (looped, recursive or energy-based Sudoku solvers, no probing of a discrete hierarchy), 2611.05033 (learned subspace patching), 2609.35475 (context restoration in LLMs), 2606.03003, 2602.04054 (equivariance metrics outside puzzles), 2607.05381, 2611.03454 (discrete diffusion theory). Blogs and news pages on NCM (falsegreen.dev, gautamparab.com, tensorjournal.com, devplace.net, beyondmarketintelligence.com) were read only to locate primary sources; none contains new analysis of the Sudoku checkpoint beyond pointers to the Quantix-eng repository.

Could not be verified: the Reddit post behind the VineOK aggregator (`reddit.com/r/MachineLearning/comments/1xh3e7o`) returned HTTP 403 to curl and to Exa contents. The repository it links was reached directly through the GitHub API, so the content above rests on the repository, not on the post.

## (b) Bibliography verification

Sources were checked on 2026-11-16. "Verified fields" are copied from the primary source. Support levels: **supported**, **partly** (the source supports a narrower statement), **not supported**.

### kumbong2026ncm

- **Verified fields:** author = Hermann Kumbong and Ishan S. Khare and Iddah Mlauzi and Andrew Woen and Charles Ding and E. Kelly Buchanan and Simran Arora and Azalia Mirhoseini and Christopher Ré; title = Next-Concept Modeling: Fast, Parallel Coarse-to-Fine Text Generation; year = 2026; eprint = 2610.14162 (v1, submitted 2026-10-09; no later version listed); archivePrefix = arXiv; primaryClass = cs.CL.
- **Source:** [arXiv API entry and abstract page](https://arxiv.org/abs/2610.14162); full text [arxiv.org/html/2610.14162v1](https://arxiv.org/html/2610.14162v1).
- **Current bib:** author `Kumbong and others` (incomplete); other fields correct.

| Citing sentence | Support | Quoted passage (section) |
|---|---|---|
| background: "NCM trains a tokenizer that encodes an output … into a hierarchy of discrete codes, one codebook per level, with more codes at each finer level. The decoder sums the contributions of all levels into a cumulative state and maps it to output tokens." | supported | §3.2: "where $\mathcal{V}_{k}$ is level $k$'s codebook … and $\ell_{1}<\ell_{2}<\cdots<\ell_{K}=L$. Each level encodes the residual left by the earlier ones." §3.3: "The reconstruction operator $R_{k}$ maps the selected codebook vectors to a length-$L$ contribution, which we add to the cumulative reconstruction"; "The VQ-VAE decoder defines token distributions $p_{\psi}(x^{i}\mid\hat{z}^{(k)})$ at all $L$ positions from a cumulative reconstruction". |
| background: "A generator, conditioned on the input (here the puzzle), produces the codes level by level, coarse to fine, and the puzzle remains available to the generator at every level." | supported | §3.2: "The generator predicts the levels from coarse to fine, conditioning on earlier levels through their cumulative reconstruction". §3.4, paragraph "Conditional generation": "Prompt positions attend to each other; each target block attends to the prompt and itself". Table 6 caption: "The prefix holds the source (XSum, WMT14), the puzzle (Sudoku), or a null token." |
| background: "The NCM paper also discusses interventions on early codes and trains the generator with corruption of earlier levels" | supported (the interventions are shown on the TinyStories model) | App. H: "We use the 12-level TinyStories model." "Perturbing Early Codes. We perturb a story's coarse representation by replacing two codes with random codes observed at the same level across validation stories, then generate the finer levels." §3.4: "we train with a fraction of conditioning codes replaced by other codes from the same level's codebook, keeping the ground-truth codes intact as labels." |
| discussion (Limitations, "Trained robustness"): "The checkpoint was trained with corruption of earlier levels" | partly | §3.4 (quoted above) states corruption as part of the NCM training method; App. F.3 ablates it on TinyStories ("This ablation … use TinyStories"). I found no Sudoku-specific corruption setting in the paper (Table 6 lists no corruption row), and the plan (§7) records that the released checkpoints carry no training metadata. The statement about *this* checkpoint is an inference from the method description. |
| e2.tex: "NCM training corrupts earlier levels" (spot check) | supported | §3.4 (quoted above). |
| setup.tex / introduction.tex: description of levels, codebooks, greedy generation (spot check) | supported for the method; checkpoint-specific numbers come from the released configuration, not from the paper | §3.2–3.4 as above. |

### kniazev2026linear

- **Verified fields:** author = Roman Kniazev and Nathanaël Fijalkow; title = Transformers Linearly Represent Highly Structured World Models; year = 2026; eprint = 2605.18847 (v1, submitted 2026-05-13); archivePrefix = arXiv; primaryClass = cs.LG.
- **Source:** [arxiv.org/abs/2605.18847](https://arxiv.org/abs/2605.18847); full text [arxiv.org/html/2605.18847v1](https://arxiv.org/html/2605.18847v1).
- **Current bib:** author `Kniazev and Fijalkow` (surnames only); other fields correct.

| Citing sentence | Support | Quoted passage (section) |
|---|---|---|
| discussion: "Linear readouts of Sudoku candidates, and a causally verified circuit for naked singles, have been reported for an autoregressive transformer trained on solver traces" | supported | Abstract: "We train an 8-layer transformer on Sudoku solving traces … we identify a naked-single circuit". §1: "we train a causal transformer on Norvig-style solving traces with backtracking". §5.3: "ablating these neurons drops the correct digit's logit by 11.4 and its softmax probability by 0.59 … The same ablation barely affects the other NS cell". |
| discussion: "in that work both per-cell candidate probes and unit-level digit-placement probes reached perfect exact match in the middle layers" | supported | §3.1: "these candidate-set probes achieve $1.0$ exact match accuracy through layers 4 to 6 when predicting the full 9-digit candidate set for any given cell". §3.2: "We train 243 binary linear probes that predict a global constraint: 'Is digit $d$ present in substructure $S$?' … these substructure probes achieve perfect exact match accuracy in mid-layers". (The 0.8 plateau in §3.1 and §6 refers to the 81 filled-digit probes: "The accuracy peaks after layer 4 at $0.8$".) |
| e3.tex: "The pooled readout is our own construction and is not the single-position readout of prior work on this target" (spot check) | supported | §2: "probes are trained on 5,120 puzzles from the test set and evaluated on 1,280, probing activations at the [clues_end] position after each layer." |

### rodrigues2026hrm

- **Verified fields:** author = Leo Raphael Rodrigues and Jian Kang; title = Dissecting Hierarchical Reasoning Models: A Mechanistic Study; year = 2026; eprint = 2609.22197 (v1, submitted 2026-08-30; arXiv comment "7 pages, 5 figures, Under Review"); archivePrefix = arXiv; primaryClass = cs.LG.
- **Source:** [arxiv.org/abs/2609.22197](https://arxiv.org/abs/2609.22197); full text [arxiv.org/html/2609.22197v1](https://arxiv.org/html/2609.22197v1).
- **Current bib:** author `Rodrigues and Kang` (surnames only); other fields correct.

| Citing sentence | Support | Quoted passage (section) |
|---|---|---|
| discussion: "In a hierarchical reasoning model, probe directions for Sudoku were decodable but not more causal than random directions" | supported | §5: "Each probe-direction ablation is compared with rank-matched random controls obtained by sampling directions from Gaussian distribution. … From Figure 5, probe-direction ablations on Sudoku and Maze produce small behavioral changes relative to full-state interventions and are comparable to random controls." Abstract: "Selected task variables are linearly decodable from the recurrent states in HRM, yet ablating probe directions produce effects comparable to random controls." |

### khoury2026roundtrip

- **Verified fields:** author = Pierre Khoury (King's College London); title = Round-Trip Refinement: A Training-Free Sampler for Next-Concept Language Models; year = 2026; publisher = Zenodo; type = preprint; latest version v2, published 2026-10-31, doi = 10.5281/zenodo.23826875; concept DOI (all versions) = 10.5281/zenodo.23737645. The record lists the code repository `https://github.com/PierreKhoury1/ncm-round-trip`.
- **Source:** [Zenodo records API, concept 23737645](https://zenodo.org/api/records/23737645) (resolves to record 23826875); PDF `Round-Trip Refinement - draft.pdf` from that record.
- **Current bib:** author `Khoury` (surname only); DOI is the concept DOI. That is acceptable, but the version read should be named.

| Citing sentence | Support | Quoted passage (section) |
|---|---|---|
| discussion: "Generated NCM codes have also been reported, in a preprint that is not peer reviewed, to be largely non-canonical under re-encoding, which is one reason why we report cell-level outcomes next to every code-level count" | partly | Introduction: "decoding a generated sample and re-encoding the text changes 61–96% of the codes at each of the six coarsest levels (20–72% at the finer ones), yet decoding the re-encoded stack gives back exactly the same text for 98% of samples" (text checkpoints). §5.8 (Sudoku-hard): "here the round trip changes only 2–20% of the codes per level, far less than the 61–96% on stories, because a Sudoku board leaves the tokenizer little freedom". "Largely non-canonical" holds for the text checkpoints, not for the Sudoku checkpoint we study. |

### ahmad2026dose

- **Verified fields:** author = Areeb Ahmad and Pratinav Seth and Vinay Kumar Sankarapu; title = Every Ablation Is a Dose: Counterweights and the Semblance of Self-Repair; year = 2026; eprint = 2610.02173 (v1, submitted 2026-10-01); archivePrefix = arXiv; primaryClass = cs.LG.
- **Source:** [arxiv.org/abs/2610.02173](https://arxiv.org/abs/2610.02173); full text [arxiv.org/html/2610.02173v1](https://arxiv.org/html/2610.02173v1).
- **Current bib:** author list has surnames only; other fields correct.

| Citing sentence | Support | Quoted passage (section) |
|---|---|---|
| discussion: "the compensation we measure is related to, and kept distinct from, self-repair within a single forward pass" | supported | §1: "Ablating a component causes downstream components to adjust, so the behavior partly survives, and ablation can underestimate the component's importance". §2: "We treat the forward pass as a deterministic structural causal model". The phenomenon is defined within one forward pass, which matches the contrast the sentence draws. |

### shah2024logic

- **Verified fields:** author = Kulin Shah and Nishanth Dikkala and Xin Wang and Rina Panigrahy; title (proceedings capitalization) = Causal language modeling can elicit search and reasoning capabilities on logic puzzles; booktitle = Advances in Neural Information Processing Systems; volume = 37; pages = 56674–56702; year = 2024; publisher = Curran Associates, Inc.; doi = 10.52202/079017-1805; editors = A. Globerson, L. Mackey, D. Belgrave, A. Fan, U. Paquet, J. Tomczak, C. Zhang; url = https://proceedings.neurips.cc/paper_files/paper/2024/hash/67b31ca159553d5593e62d7b998d63ea-Abstract-Conference.html; also eprint = 2409.10502 (arXiv v1, 2024-09-16, cs.LG).
- **Source:** [NeurIPS 2024 proceedings page](https://proceedings.neurips.cc/paper_files/paper/2024/hash/67b31ca159553d5593e62d7b998d63ea-Abstract-Conference.html) and its BibTeX file; [arXiv:2409.10502](https://arxiv.org/abs/2409.10502); full text [arxiv.org/html/2409.10502v1](https://arxiv.org/html/2409.10502v1).
- **Current bib:** `@misc` with `Shah and others`, arXiv only. Should be `@inproceedings` (NeurIPS 2024) with the full author list.

| Citing sentence | Support | Quoted passage (section) |
|---|---|---|
| discussion: "Candidate-set evidence in other work on logic puzzles comes from forcing outputs and comparing top-ranked predictions with a solver rather than from a learned probe" | supported (the abstract says otherwise; the body text controls) | §4.4: "To extract the candidate set from the model at the state $s$ of the puzzle and at an empty cell $(r,c)$, we feed $(s,r,c)$ as the prefix to the model and values corresponding to top-$k$ output logits where $k=|f^{*}(s,r,c)|$ becomes the candidate set of the model." "Note that to extract the candidate set of the model, we are just reading the logits and not even training a linear function." Abstract, for contrast: "through linear probing, we can decode information about the set of possible values in any given cell". |

### hewitt2019control

- **Verified fields:** author = John Hewitt and Percy Liang; title = Designing and Interpreting Probes with Control Tasks; booktitle = Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing (EMNLP-IJCNLP); editors = Kentaro Inui, Jing Jiang, Vincent Ng, Xiaojun Wan; month = nov; year = 2019; address = Hong Kong, China; publisher = Association for Computational Linguistics; pages = 2733–2743; doi = 10.18653/v1/D19-1275; url = https://aclanthology.org/D19-1275/.
- **Source:** [ACL Anthology D19-1275](https://aclanthology.org/D19-1275/) and its `.bib` file.
- **Current bib:** `@inproceedings` without booktitle, pages or DOI; author surnames only.

| Citing sentence | Support | Quoted passage (section) |
|---|---|---|
| background: "Control tasks and matched baselines are needed to separate what the representation provides from what the probe can learn on its own" | supported | Abstract: "we propose control tasks, which associate word types with random outputs, to complement linguistic tasks. By construction, these tasks can only be learned by the probe itself. So a good probe, (one that reflects the representation), should be selective, achieving high linguistic task accuracy and low control task accuracy." ("Matched baselines" is not Hewitt & Liang's term; Belinkov §4.1 "Comparisons and controls" covers baselines, and the sentence cites both works.) |
| discussion: "The probing methodology follows the control-task tradition" | supported | Same passage. |

### belinkov2022probing

- **Verified fields:** author = Yonatan Belinkov; title = Probing Classifiers: Promises, Shortcomings, and Advances; journal = Computational Linguistics; volume = 48; number = 1; pages = 207–219; month = mar; year = 2022; publisher = MIT Press; address = Cambridge, MA; doi = 10.1162/coli_a_00422; url = https://aclanthology.org/2022.cl-1.7/.
- **Source:** [ACL Anthology 2022.cl-1.7](https://aclanthology.org/2022.cl-1.7/), its `.bib` file and the PDF.
- **Current bib:** `@article` without journal, volume, number, pages or DOI; author surname only.

| Citing sentence | Support | Quoted passage (section) |
|---|---|---|
| background: "A probe that predicts a label from a representation shows that the label is accessible to that probe, not that the model uses it" | supported | §4.3 "Correlation vs. Causation": "the probing framework may indicate correlations between representations $f_l(x)$ and linguistic property $z$, but it does not tell us whether this property is involved in predictions of $f$." |
| discussion: "The probing methodology follows the control-task tradition" | supported | §4.1 covers comparisons and controls, including control tasks and control datasets. |

### Verified BibTeX (for reference; not applied to `paper/refs.bib`)

```bibtex
@misc{kumbong2026ncm,
  author = {Kumbong, Hermann and Khare, Ishan S. and Mlauzi, Iddah and Woen, Andrew and Ding, Charles and Buchanan, E. Kelly and Arora, Simran and Mirhoseini, Azalia and R{\'e}, Christopher},
  title = {Next-Concept Modeling: Fast, Parallel Coarse-to-Fine Text Generation},
  year = {2026},
  eprint = {2610.14162},
  archivePrefix = {arXiv},
  primaryClass = {cs.CL}
}

@misc{kniazev2026linear,
  author = {Kniazev, Roman and Fijalkow, Nathana{\"e}l},
  title = {Transformers Linearly Represent Highly Structured World Models},
  year = {2026},
  eprint = {2605.18847},
  archivePrefix = {arXiv},
  primaryClass = {cs.LG}
}

@misc{rodrigues2026hrm,
  author = {Rodrigues, Leo Raphael and Kang, Jian},
  title = {Dissecting Hierarchical Reasoning Models: A Mechanistic Study},
  year = {2026},
  eprint = {2609.22197},
  archivePrefix = {arXiv},
  primaryClass = {cs.LG}
}

@misc{khoury2026roundtrip,
  author = {Khoury, Pierre},
  title = {Round-Trip Refinement: A Training-Free Sampler for Next-Concept Language Models},
  year = {2026},
  publisher = {Zenodo},
  howpublished = {Zenodo preprint, version 2, not peer reviewed},
  doi = {10.5281/zenodo.23826875},
  note = {Concept DOI 10.5281/zenodo.23737645}
}

@misc{ahmad2026dose,
  author = {Ahmad, Areeb and Seth, Pratinav and Sankarapu, Vinay Kumar},
  title = {Every Ablation Is a Dose: Counterweights and the Semblance of Self-Repair},
  year = {2026},
  eprint = {2610.02173},
  archivePrefix = {arXiv},
  primaryClass = {cs.LG}
}

@inproceedings{shah2024logic,
  author = {Shah, Kulin and Dikkala, Nishanth and Wang, Xin and Panigrahy, Rina},
  title = {Causal Language Modeling Can Elicit Search and Reasoning Capabilities on Logic Puzzles},
  booktitle = {Advances in Neural Information Processing Systems},
  volume = {37},
  pages = {56674--56702},
  year = {2024},
  publisher = {Curran Associates, Inc.},
  doi = {10.52202/079017-1805}
}

@inproceedings{hewitt2019control,
  author = {Hewitt, John and Liang, Percy},
  title = {Designing and Interpreting Probes with Control Tasks},
  booktitle = {Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing (EMNLP-IJCNLP)},
  pages = {2733--2743},
  year = {2019},
  address = {Hong Kong, China},
  publisher = {Association for Computational Linguistics},
  doi = {10.18653/v1/D19-1275},
  url = {https://aclanthology.org/D19-1275/}
}

@article{belinkov2022probing,
  author = {Belinkov, Yonatan},
  title = {Probing Classifiers: Promises, Shortcomings, and Advances},
  journal = {Computational Linguistics},
  volume = {48},
  number = {1},
  pages = {207--219},
  year = {2022},
  publisher = {MIT Press},
  doi = {10.1162/coli_a_00422},
  url = {https://aclanthology.org/2022.cl-1.7/}
}
```

The title case for `shah2024logic` follows the arXiv title; the proceedings page uses sentence case. Either is accurate.

## (c) Recommended changes (not applied)

1. **Discussion, "Relation to prior work": add the Quantix-eng repository.** It is the only other probing and intervention work on the NCM Sudoku checkpoint that I found. Suggested content: exploratory, unreviewed, AI-assisted notes report a naked-single probe on generator states that is decodable above a shuffled-label control but whose causal ablation was not specific, and fixed versus regenerated tail exchanges whose benefit was not established; our study differs by preregistration, the equal-cost level contrast, the candidate-mask target on the cumulative state, and the control matrix. Cite it as software with the commit hash, for example `@misc{quantix2026ncmnotes, author = {{Quantix-eng}}, title = {{NCM} experiment notes: twenty exploratory studies and related controls}, year = {2026}, howpublished = {GitHub repository, commit 89a165ce01f06ce27dc097c2b2f805c288d6dde3, not peer reviewed}, url = {https://github.com/Quantix-eng/ncm-experiment-notes}}`. The author is identified only by the GitHub account name; do not invent a personal name.
2. **Discussion, Khoury sentence: narrow it to what the source shows.** For example: "Generated NCM codes for text have been reported, in a preprint that is not peer reviewed, to be largely non-canonical under re-encoding (61–96% of codes rewritten at the coarse levels); for the Sudoku-hard checkpoint the same preprint reports 2–20% per level \citep{khoury2026roundtrip}." The rationale for reporting cell-level outcomes next to code-level counts still holds, because a many-to-one quantizer can absorb a replaced code.
3. **Discussion, "Trained robustness": attribute the corruption to the method, not to verified checkpoint metadata.** For example: "NCM generators are trained with corruption of earlier levels \citep{kumbong2026ncm}; the released checkpoint carries no training metadata, so we assume it was trained this way." The same applies, less strongly, to the background sentence and to e2.tex ("NCM training corrupts earlier levels"), which are accurate as statements about the method.
4. **Background, "Probing with controls" (optional):** cite Garg (2026, arXiv:2610.08544) next to Hewitt & Liang for reading a probe score against a floor from simple inputs and a ceiling from the full input. This is the closest methodological match to the raw-input and surface-statistics references in E3.
5. **Discussion, H3 context (optional):** Oh et al. (2026, arXiv:2611.17320) report on Sudoku that "remasking an isolated error usually reproduces it when the surrounding context remains fixed". This is a masked-diffusion parallel to the fixed versus regenerated suffix contrast. Cite only if space allows; it is a method paper.
6. **`refs.bib`:** replace all 8 entries with the verified BibTeX above. In summary: full author lists everywhere; `shah2024logic` becomes `@inproceedings` (NeurIPS 2024, vol. 37, pp. 56674–56702, DOI 10.52202/079017-1805); `hewitt2019control` gains booktitle, pages and DOI; `belinkov2022probing` gains journal, volume, number, pages and DOI; `khoury2026roundtrip` names v2 (DOI 10.5281/zenodo.23826875) and keeps the concept DOI in a note. Remove the stale comment line `% Phase 2 verifies every entry …`.
7. **Novelty statement (if one is added before submission):** do not claim to be the first interpretability study of NCM on Sudoku. A defensible form is "to our knowledge, as of 2026-11-16, the first preregistered study of level sensitivity, compensation and candidate-mask readability in a coarse-to-fine discrete-code generator", with the Quantix-eng repository cited as prior exploratory work.
8. **Outside the paper (for the project record, not applied here):** the 2026-11-08 note `related_work_novelty_check.md` (Summary bullet on E3, Kniazev table row, implication 2) says that Kniazev & Fijalkow's per-cell *candidate* probes plateau at about 80%. The source says 1.0 exact match for per-cell candidate probes in layers 4–6 and 0.8 for per-cell *filled-digit* probes (§3.1). The paper text is already correct. The note's statement "None of them does mechanistic or probing work on Sudoku" is superseded by item 1.

## Limitations of this update

- Consensus supports only a year filter (`year_min=2026`), so its results were screened for posting dates after 2026-10-01 by hand. Most relevant hits again came from Exa and arXiv.
- Semantic Scholar keyword search returned HTTP 429 on several calls. The citation endpoints for NCM, Kniazev & Fijalkow and Rodrigues & Kang returned 0 citing papers, which probably reflects indexing lag. Google Scholar and OpenReview were not searched.
- The Quantix-eng repository was read at the level of READMEs, scope notes, selected source files and recorded JSON. Its probe representation is described from a code comment ("final-level states at cells"); I did not trace the extraction code that produces `local_hidden`, and I did not rerun anything. Its results are AI-assisted, unreviewed and, by its own statement, partly unvalidated after relocation.
- Full text was read for the five arXiv papers in `refs.bib`, the Belinkov PDF and the Khoury v2 PDF. Everything else in table (a) is verified at the abstract level only.
- Works posted after 2026-11-16 are not covered.

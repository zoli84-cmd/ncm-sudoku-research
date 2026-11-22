# Query log: related-work novelty check

All queries were run on 2026-11-08. API keys were read from environment variables and are not recorded. "Kept" = number of new items from that query that entered the table in [related_work_novelty_check.md](related_work_novelty_check.md). An item found again by a later query is counted only at its first appearance.

## Consensus API (`GET https://api.consensus.app/v1/search`, parameter `year_min=2018`; 17 calls)

| # | Tool | Exact query | Results | Kept |
|---|---|---|---|---|
| C1 | Consensus | probing neural network trained on Sudoku for candidate sets and constraint propagation | 20 | 1 |
| C2 | Consensus | mechanistic interpretability of transformer trained to solve Sudoku | 20 | 4 |
| C3 | Consensus | linear probe transformer constraint satisfaction puzzle internal representation of candidates | 20 | 1 |
| C4 | Consensus | interpretability of language models solving logic puzzles search | 20 | 0 |
| C5 | Consensus | residual vector quantization hierarchical levels intervention code replacement sensitivity | 20 | 0 |
| C6 | Consensus | coarse-to-fine autoregressive image generation next-scale prediction error accumulation self-correction | 20 | 3 |
| C7 | Consensus | activation patching counterfactual pairs causal mediation transformer | 20 | 2 |
| C8 | Consensus | interpretability of diffusion language model solving Sudoku internal representations | 20 | 0 |
| C9 | Consensus | probing equivariance under symmetry transformations of board game world model representations | 20 | 3 |
| C10 | Consensus | hierarchical reasoning model Sudoku latent reasoning interpretability fixed point | 20 | 2 |
| C11 | Consensus | masked diffusion model Sudoku planning order of unmasking reasoning | 20 | 1 |
| C12 | Consensus | intervening on discrete tokens of visual autoregressive model scale-wise interpretability | 20 | 0 |
| C13 | Consensus | next-concept modeling hierarchical latent concepts coarse-to-fine generation | 20 | 1 |
| C14 | Consensus | probe decodability versus causal use amnesic probing intervention representation | 20 | 3 |
| C15 | Consensus | self-repair compensation after ablation in transformer later layers | 20 | 2 |
| C16 | Consensus | hierarchical discrete latent generation corrupting earlier level codes during training robustness exposure bias | 20 | 0 |
| C17 | Consensus | linear probe world model transformer causal intervention board game puzzle 2025 2026 | 20 | 2 |

## Exa search API (`POST https://api.exa.ai/search`, `type=auto`, `numResults=12`; lower bound on publication date in brackets)

| # | Tool | Exact query | Results | Kept |
|---|---|---|---|---|
| E1 | Exa [2022-01-01] | linear probes of a transformer trained on Sudoku reveal candidate sets and constraint propagation | 12 | 1 |
| E2 | Exa [2022-01-01] | mechanistic interpretability of a neural Sudoku solver: what does the network compute internally | 12 | 0 |
| E3 | Exa [2022-01-01] | activation patching in a model that solves Sudoku puzzles | 12 | 0 |
| E4 | Exa [2022-01-01] | interpretability of Next-Concept Modeling NCM coarse-to-fine text generation residual codes | 11 | 2 |
| E5 | Exa [2026-10-10] | arXiv paper citing Next-Concept Modeling Kumbong 2026 coarse-to-fine residual vector quantized latent generation | 12 | 1 |
| E6 | Exa [2023-01-01] | intervening on coarse scale tokens in next-scale prediction model, effect on finer scales and self-correction | 12 | 1 |
| E7 | Exa [2024-01-01] | interpretability of discrete diffusion model on Sudoku: probing intermediate denoising states for constraint information | 12 | 2 |
| E8 | Exa [2022-01-01] | probe equivariance under board symmetries Othello world model representation consistency | 12 | 0 |
| E9 | Exa [2022-01-01] | residual vector quantization codebook levels semantic meaning interpretability perturbing codes per level | 12 | 1 |
| E10 | Exa [2023-01-01] | neural network implicit search versus constraint propagation Sudoku depth of reasoning probes per propagation step | 12 | 0 |
| E11 | Exa [2024-06-01] | mechanistic interpretability of visual autoregressive next-scale prediction model: which scale encodes what, interventions on scale tokens | 12 | 3 |
| E12 | Exa [2023-01-01] | swapping or replacing coarse codebook tokens in residual vector quantized audio language model, effect on fine tokens | 12 | 0 |
| E13 | Exa [2023-01-01] | counterfactual puzzle pairs interchange intervention transformer constraint puzzle causal abstraction | 12 | 0 |
| E14 | Exa [2022-01-01] | probing classifier equivariance test under input symmetry group transformations as validity check for probes | 12 | 2 |
| E15 | Exa [2025-01-01] | interpretability of masked diffusion language model hidden states on Sudoku linear probe constraint | 12 | 0 |
| E16 | Exa [2026-10-09] | Next-Concept Modeling Sudoku latent codes analysis levels hierarchy | 12 | 3 |
| E17 | Exa [2023-01-01] | probing which layer of a transformer encodes k-step deductions: reasoning depth decoded layer by layer in constraint propagation or graph search | 12 | 1 |
| E18 | Exa [2023-01-01] | Sudoku neural network probe digit permutation equivariance board symmetry generalization of probes | 12 | 0 |

## Exa contents API (`POST https://api.exa.ai/contents`, text extraction of known URLs)

| # | Tool | URLs requested | Results | Kept |
|---|---|---|---|---|
| X1 | Exa contents | greaterwrong.com LessWrong post WvRQ9NoWKhBTansAy; doi:10.5281/zenodo.23737645; doi:10.5281/zenodo.23620791; dev.to/janmusic/lower-loss-worse-stories-small-ncms-trained-on-tinystories-6k3 | 4 | 3 (Zenodo 23620791, the NCM-MLX software record, was read but not tabled; the related working paper 23620913 is tabled) |
| X2 | Exa contents | doi:10.5281/zenodo.23590380; doi:10.5281/zenodo.23620913; aibeatnews.com/analysis/next-concept-modeling-tested/ | 3 | 3 (counted in E16) |

## arXiv export API, keyword search (`https://export.arxiv.org/api/query?search_query=...&max_results=25&sortBy=submittedDate`)

| # | Tool | Exact `search_query` | Results | Kept |
|---|---|---|---|---|
| A1 | arXiv API | `all:"next-concept modeling"` | 1 | 0 (NCM itself only) |
| A2 | arXiv API | `abs:sudoku AND abs:probe` | 7 | 0 |
| A3 | arXiv API | `abs:sudoku AND abs:interpretability` | 15 | 1 |
| A4 | arXiv API | `abs:sudoku AND abs:mechanistic` | 6 | 1 |
| A5 | arXiv API | `abs:"residual quantization" AND abs:interpretability` | 3 | 0 |
| A6 | arXiv API | `abs:"next-scale prediction" AND abs:"error propagation"` | 3 | 1 |
| A7 | arXiv API | `abs:"self-repair" AND abs:ablation` | 8 | 1 |

## arXiv export API, abstract retrieval by id (`id_list=...`; verification, not discovery)

| # | IDs requested | Results |
|---|---|---|
| V1 | 2409.10502, 2607.19635, 2609.22197, 2605.18847, 2605.22488, 2605.08605, 2601.10679, 2604.04902, 2605.24843, 2601.20363, 2609.09009, 2610.28543, 2307.15771, 2404.15255, 2309.16042, 2606.27510, 2309.00941 | 17 |
| V2 | 2503.04421, 2602.23164, 2603.02193, 2510.08632, 2602.08984, 2610.14162, 2505.21473, 2307.04895, 2509.22023, 2202.03229, 2610.20955, 2502.06768, 2410.14157, 2310.17230, 2506.20040, 2603.16661, 2605.22967, 2210.13382, 2404.02905, 2510.01384 | 20 |
| V3 | 2605.20187, 2605.17811, 2606.18022, 2610.02173, 2607.01940, 2402.15390, 2608.07948 | 7 |
| V4 | 2610.40061, 2606.13558, 2510.02826, 2605.11448, 2509.22636, 2610.17269 | 6 |
| V5 | 2412.11867, 2406.00877, 2604.22128, 2510.09794, 2609.18080 | 5 |
| V6 | 2402.11917, 2507.02199 | 2 |

Abstracts read but not tabled (judged not relevant enough): 2601.20363, 2604.04902, 2309.16042 (already cited in the plan), 2503.04421, 2510.08632, 2602.08984, 2505.21473, 2307.04895, 2509.22023, 2202.03229, 2410.14157, 2506.20040, 2603.16661, 2605.22967, 2606.18022, 2509.22636, 2507.02199.

## arXiv HTML full text (`https://arxiv.org/html/<id>`, keyword search inside the text)

| # | ID | Purpose |
|---|---|---|
| H1 | 2409.10502 | Checked how the candidate-set "probing" works (§4.4) |
| H2 | 2605.18847 | Checked the probe types, patching, naked/hidden-single circuit, symmetry mentions |
| H3 | 2609.22197 | Checked the Sudoku probe targets (App. A.7) and the probe-vs-random ablation finding |
| H4 | 2607.19635 | Checked the symmetry-augmentation and equivariance discussion |

## Semantic Scholar Graph API (`/graph/v1/paper/arXiv:<id>/citations`)

| # | Paper | Results |
|---|---|---|
| S1 | arXiv:2610.14162 (NCM) | 0 citing papers |
| S2 | arXiv:2605.18847 (Kniazev & Fijalkow) | 0 citing papers |

## Follow-up deep dive, 2026-11-11: Kniazev & Fijalkow (2605.18847) unit-level probe protocol

| # | Tool | Target | Purpose | Kept |
|---|---|---|---|---|
| H5 | arXiv HTML (`https://arxiv.org/html/2605.18847`, raw download + stdlib HTML-to-text) | full paper text incl. Appendices A–D | Pin down the exact substructure-probe label, readout position, probe form/training, metrics, and per-cell candidate definition for `literature/kniazev_fijalkow_2026_unit_probe.md` | 1 (full text) |
| G1 | GitHub REST API (`api.github.com/repos/kameronton/sudoku-residual`, tree + raw file fetch, unauthenticated) | `sudoku/probes/modes.py`, `sudoku/probes/probing.py`, `sudoku/probes/activations.py`, `sudoku/probes/session.py`, `plots/scripts/fig_probe_acc_by_layer.py` at commit `a9b206955bfd1089a7253511fa9371066ecca570` | Verify the paper's probe-protocol prose against the actual probe code (label construction, activation extraction position, probe fitting, exact-match/AUC metric definitions) | 1 (code repo linked from the paper, confirmed via HTML `href` around "Code is available at the link") |

## Pre-submission update (2026-11-16)

All queries were run on 2026-11-16 for [presubmission_update_2026-11-16.md](presubmission_update_2026-11-16.md). API keys were read from environment variables and are not recorded. "Kept" = number of new items from that query that entered table (a) of the update. An item found again by a later query is counted only at its first appearance. The queries ran in this order: Consensus, arXiv, Semantic Scholar (round 1), Exa, then Semantic Scholar (round 2) together with arXiv An8–An11.

### Consensus API (`GET https://api.consensus.app/v1/search`, header `x-api-key`; 11 calls)

The API offers only a year filter, so `year_min=2026` was used. Posting dates after 2026-10-01 were checked by hand.

| # | Tool | Exact query | Date filter | Results | Kept |
|---|---|---|---|---|---|
| C1 | Consensus | probing neural network trained on Sudoku for candidate sets and constraint propagation | year_min=2026 | 20 | 0 |
| C2 | Consensus | mechanistic interpretability of transformer trained to solve Sudoku | year_min=2026 | 20 | 0 |
| C3 | Consensus | linear probe transformer constraint satisfaction puzzle internal representation of candidates | year_min=2026 | 20 | 1 (2610.22655) |
| C6 | Consensus | coarse-to-fine autoregressive image generation next-scale prediction error accumulation self-correction | year_min=2026 | 20 | 0 |
| C9 | Consensus | probing equivariance under symmetry transformations of board game world model representations | year_min=2026 | 20 | 0 |
| C13 | Consensus | next-concept modeling hierarchical latent concepts coarse-to-fine generation | year_min=2026 | 20 | 0 |
| C14 | Consensus | probe decodability versus causal use amnesic probing intervention representation | year_min=2026 | 20 | 2 (2609.02438, 2609.01048) |
| C15 | Consensus | self-repair compensation after ablation in transformer later layers | year_min=2026 | 20 | 0 |
| C17 | Consensus | linear probe world model transformer causal intervention board game puzzle 2025 2026 | year_min=2026 | 20 | 1 (2608.07077) |
| Cn1 | Consensus | interventions on discrete residual quantized codes hierarchical text generation level sensitivity | year_min=2026 | 20 | 0 |
| Cn2 | Consensus | Sudoku neural solver internal representation intermediate states probing 2026 | year_min=2026 | 20 | 0 |

### arXiv export API, keyword search (`https://export.arxiv.org/api/query?search_query=<query> AND submittedDate:[202610010000 TO 202611162359]&max_results=50&sortBy=submittedDate`)

| # | Tool | Exact `search_query` (before the date clause) | Date filter | Results | Kept |
|---|---|---|---|---|---|
| A1 | arXiv API | `all:"next-concept modeling"` | 2026-10-01 to 2026-11-16 | 1 | 0 (NCM itself only) |
| A2 | arXiv API | `abs:sudoku AND abs:probe` | same | 1 | 0 |
| A3 | arXiv API | `abs:sudoku AND abs:interpretability` | same | 3 | 0 |
| A4 | arXiv API | `abs:sudoku AND abs:mechanistic` | same | 0 | 0 |
| A6 | arXiv API | `abs:"next-scale prediction" AND abs:"error propagation"` | same | 0 | 0 |
| A7 | arXiv API | `abs:"self-repair" AND abs:ablation` | same | 1 | 0 (Ahmad et al., already cited) |
| An1 | arXiv API | `abs:sudoku` | same | 36 | 1 (2611.17320) |
| An2 | arXiv API | `abs:"coarse-to-fine" AND abs:"residual" AND abs:quantiz*` | same | 2 | 0 |
| An3 | arXiv API | `abs:"next-scale" AND (abs:interpretability OR abs:intervention)` | same | 2 | 0 (LoCo, already tabled on 2026-11-08) |
| An4 | arXiv API | `abs:probe AND abs:equivariance` | same | 8 | 0 |
| An5 | arXiv API | `abs:decodab* AND abs:causal AND abs:probe` | same | 0 | 0 |
| An6 | arXiv API | `all:"next-concept"` | same | 1 | 0 (NCM itself only) |
| An7 | arXiv API | `abs:"constraint propagation" AND abs:transformer` | same | 0 | 0 |
| An8 | arXiv API | `abs:"coarse-to-fine" AND abs:"text generation"` | same | 1 | 0 |
| An9 | arXiv API | `abs:"residual" AND abs:"vector quantiz*" AND abs:probe` | same | 1 | 0 |
| An10 | arXiv API | `abs:sudoku AND abs:"linear probe"` | same | 0 | 0 |
| An11 | arXiv API | `abs:"self-repair"` | same | 5 | 0 |

### Semantic Scholar Graph API (`https://api.semanticscholar.org/graph/v1/`, unauthenticated)

| # | Tool | Exact query or endpoint | Date filter | Results | Kept |
|---|---|---|---|---|---|
| S1 | Semantic Scholar | `paper/arXiv:2610.14162/citations` (NCM) | none | 0 citing papers (after one HTTP 429 retry) | 0 |
| S2 | Semantic Scholar | `paper/arXiv:2605.18847/citations` (Kniazev & Fijalkow) | none | 0 citing papers (after two 429 retries) | 0 |
| S3 | Semantic Scholar | `paper/arXiv:2609.22197/citations` (Rodrigues & Kang) | none | 0 citing papers | 0 |
| S4 | Semantic Scholar | `paper/search`, query `next-concept modeling` | `publicationDateOrYear=2026-10-01:` | **failed**: HTTP 429 on all 9 attempts (two rounds) | – |
| S5 | Semantic Scholar | `paper/search`, query `sudoku interpretability probe` | `publicationDateOrYear=2026-10-01:` | 50 of 370 (round 2; round 1 failed with 429) | 1 (2610.08544) |
| S6 | Semantic Scholar | `paper/search`, query `coarse-to-fine residual quantized generator intervention` | `publicationDateOrYear=2026-10-01:` | **failed**: HTTP 429 on all 9 attempts | – |
| S7 | Semantic Scholar | `paper/search`, query `self-repair compensation ablation` | `publicationDateOrYear=2026-10-01:` | **failed**: HTTP 429 on all 9 attempts | – |
| S8 | Semantic Scholar | `paper/arXiv:2610.14162` (citation count) | none | **failed**: HTTP 429 on all 5 attempts | – |
| S9 | Semantic Scholar | `paper/arXiv:2409.10502` (venue lookup for Shah et al.) | none | **failed**: HTTP 429 | – (venue verified on the NeurIPS proceedings page instead) |

Retry of the failed Semantic Scholar calls later on 2026-11-16 (same endpoints, parameters and date filter; `fields` = title, external ids, publication date, venue, url, abstract; `limit=100`; unauthenticated, no `S2_API_KEY` in the environment; up to 6 attempts per call with exponential backoff from 5 s):

| # | Exact call | Results | Kept |
|---|---|---|---|
| S4r | S4 repeated | **failed**: HTTP 429 on all 6 attempts | – |
| S6r | S6 repeated | **failed**: HTTP 429 on all 6 attempts | – |
| S7r | S7 repeated | 25 of 25 (first attempt) | 0 (the only relevant hit, arXiv:2610.02173, is already `ahmad2026dose`; the rest are from unrelated fields) |
| S8r | S8 repeated | NCM (arXiv:2610.14162): citationCount 0, referenceCount 52 (second attempt) | – |
| S9r | S9 repeated | **failed**: HTTP 429 on all 6 attempts | – (venue already verified on the proceedings page) |

### Exa search API (`POST https://api.exa.ai/search`, `type=auto`, `numResults=12`)

| # | Tool | Exact query | Date filter (`startPublishedDate`) | Results | Kept |
|---|---|---|---|---|---|
| E1 | Exa | linear probes of a transformer trained on Sudoku reveal candidate sets and constraint propagation | 2026-10-01 | 12 | 0 |
| E4 | Exa | interpretability of Next-Concept Modeling NCM coarse-to-fine text generation residual codes | 2026-10-01 | 12 | 1 (VineOK aggregator page, which led to the Quantix-eng repository) |
| E5 | Exa | arXiv paper citing Next-Concept Modeling Kumbong 2026 coarse-to-fine residual vector quantized latent generation | 2026-10-01 | 12 | 0 |
| E6 | Exa | intervening on coarse scale tokens in next-scale prediction model, effect on finer scales and self-correction | 2026-10-01 | 12 | 0 |
| E7 | Exa | interpretability of discrete diffusion model on Sudoku: probing intermediate denoising states for constraint information | 2026-10-01 | 12 | 0 |
| E14 | Exa | probing classifier equivariance test under input symmetry group transformations as validity check for probes | 2026-10-01 | 12 | 1 (2611.07805) |
| E16 | Exa | Next-Concept Modeling Sudoku latent codes analysis levels hierarchy | 2026-10-01 | 12 | 0 |
| En1 | Exa | Next-Concept Modeling follow-up study, NCM checkpoint analysis or extension | 2026-10-01 | 12 | 2 (Zenodo 23564347, Zenodo 23837501) |
| En2 | Exa | decodable but not causally used: linear probe versus intervention evidence in a puzzle-solving transformer | 2026-10-01 | 12 | 1 (2610.07270) |
| En3 | Exa | self-repair or compensation when later stages regenerate after an early error in a hierarchical generator | 2026-10-01 | 12 | 0 |
| En4 | Exa | mechanistic interpretability of a recurrent or looped reasoning model on Sudoku | 2026-10-01 | 12 | 0 |
| En5 | Exa | github repository exploratory studies and controls Next-Concept Modeling NCM interpretability | 2026-10-01 | 12 | 0 (secondary pages pointing to the same repository; counted in E4) |
| En6 | Exa | Sudoku next-concept model probing levels candidate mask code replacement | 2026-10-01 | 12 | 0 |
| EV1 | Exa, `includeDomains` = proceedings.neurips.cc, papers.nips.cc, neurips.cc, openreview.net, `numResults=8` (verification, not discovery) | Causal Language Modeling Can Elicit Search and Reasoning Capabilities on Logic Puzzles | none | 8 | – |

### Exa contents API (`POST https://api.exa.ai/contents`, text extraction of known URLs)

| # | Tool | URLs requested | Results | Kept |
|---|---|---|---|---|
| X1 | Exa contents | vineok.com/items/103127; falsegreen.dev/posts/the-most-interesting-checkpoint-is-five-bytes-long/; gautamparab.com/writing/twelve-steps-coarse-to-fine/; zenodo.org/records/23564347; doi:10.5281/zenodo.23837501 | 5 | counted in E4/En1 |
| X2 | Exa contents | reddit.com/r/MachineLearning/comments/1xh3e7o/ (the source post behind VineOK) | **failed**: HTTP 403 `SOURCE_NOT_AVAILABLE` (direct curl of the Reddit JSON also returned 403) | – |
| X3 | Exa contents | tensorjournal.com/en/news/ncm-experiment-notes-exploratory-repository; devplace.net (Reddit repost with the repository link); beyondmarketintelligence.com (same) | 3 | 0 (pointers only) |

### Primary-source retrieval (verification, not discovery)

| # | Tool | Target | Results |
|---|---|---|---|
| G2 | GitHub REST API (unauthenticated) and raw file fetch | `api.github.com/repos/Quantix-eng/ncm-experiment-notes` (metadata, recursive tree at `89a165ce01f06ce27dc097c2b2f805c288d6dde3`); raw `README.md`, `CITATION.cff`, `docs/scope.md`, `docs/related-work.md`, `experiments/README.md`, `experiments/catalog.csv`, READMEs of experiments 01, 06, 09, 10, 12, 16; from `experiments/10-initial-audit/`: `experiment.json`, `src/analyze.py`, `src/experiments.py`, `src/extract.py`, `src/prepare.py`, `src/continue.py`, `recorded/summary.csv`, `recorded/probes.csv`, `recorded/symmetry.json`, `recorded/constant_level.json`, `recorded/tokenizer_errors.json`, `recorded/naked_single.json` | all fetched; the extraction code that produces `local_hidden` was not found in the two adapter files searched |
| Z1 | Zenodo records API | `zenodo.org/api/records/23737645` (resolves to the latest version, 23826875, v2 of 2026-10-31) and its PDF | fetched; the first attempt failed with curl exit 35 (TLS), the retry succeeded |
| R1 | arXiv API `id_list` | 2610.14162, 2605.18847, 2609.22197, 2610.02173, 2409.10502 (bib entries) | 5 |
| V7 | arXiv API `id_list` | 2610.22655, 2611.07805, 2610.37411, 2611.17320, 2610.18174, 2610.18127, 2610.29255, 2610.02193, 2610.07270, 2611.05033, 2608.07077, 2609.01048 | 12 |
| V8 | arXiv API `id_list` | 2609.35475, 2609.02438, 2606.03003, 2602.04054, 2610.16427, 2610.25646, 2611.17309, 2609.26487, 2610.15081, 2607.05381, 2611.03454, 2611.08977, 2610.26542 | 13 |
| V9 | arXiv API `id_list` | 2610.08544 | 1 |
| H6 | arXiv HTML full text | 2610.14162v1, 2605.18847v1, 2609.22197v1, 2610.02173v1, 2409.10502v1 | 5 (keyword-searched for each citing sentence) |
| P1 | ACL Anthology | D19-1275 page and `.bib`; 2022.cl-1.7 page, `.bib` and PDF | all fetched |
| P2 | NeurIPS proceedings | `proceedings.neurips.cc/paper_files/paper/2024/hash/67b31ca159553d5593e62d7b998d63ea-Abstract-Conference.html` and its BibTeX file | fetched |
| D1 | DBLP search API | `q=Causal Language Modeling Can Elicit Search and Reasoning` | **failed**: HTTP 202 with an empty body |

Abstracts read but not tabled: 2610.37411, 2610.29255, 2610.02193, 2610.18174, 2610.18127, 2610.25646, 2610.16427, 2609.26487, 2611.08977, 2611.17309, 2610.26542, 2610.15081, 2611.05033, 2609.35475, 2606.03003, 2602.04054, 2607.05381, 2611.03454.

## Lacuna MCP evaluation (2026-11-22)

All queries were run on 2026-11-22 through the project MCP server `lacuna-research` (https://lacuna.tiptreesystems.com/api/mcp, read-only, no credentials). Purpose: decide whether Lacuna is useful for this project, not a full related-work search. "Kept" = number of items not already in `paper/refs.bib`, `related_work_novelty_check.md` or `presubmission_update_2026-11-16.md` that are worth a follow-up.

| # | Tool | Exact query or identifier | Parameters | Results | Kept |
|---|---|---|---|---|---|
| L1 | `get_paper` | 2610.14162 | `figure_limit=0` | found (NCM paper; 0 citations listed in Lacuna) | 0 |
| L2 | `search_lacuna` | next-concept modeling coarse-to-fine residual vector quantization text generation | `search_type=paper`, `date_from=2026-10`, `limit=10` | 11 (only the NCM paper is relevant) | 0 |
| L3 | `search_lacuna` | probing Sudoku reasoning transformer candidate representations | `search_type=cluster`, `limit=5` | 1 (direction 13064, numerical reasoning in transformers; not relevant) | 0 |
| L4 | `search_lacuna` | error propagation across scales in coarse-to-fine hierarchical generation interventions | `search_type=hypothesis`, `limit=5` | 5 (other domains: parsing, slide search, flow generation, dialogue, vision; not relevant) | 0 |
| L5 | `search_lacuna` | linear probes Sudoku transformer candidates causal patching interpretability | `search_type=paper`, `ranking_profile=semantic`, `limit=10` | 10 (Shah et al. 2024 found again; the rest are general interpretability papers) | 0 |
| L6 | `get_paper` | 2605.18847 (Kniazev & Fijalkow 2026) | `view=neighbors` | **not found** in Lacuna | – |
| L7 | `get_paper` | 10.5281/zenodo.23737645 (Khoury 2026) | `view=preview` | **not found** in Lacuna | – |
| L8 | `search_lacuna` | Transformers Linearly Represent Highly Structured World Models | `search_type=paper`, `limit=3` | 3, `exact_title_missing=true` (the Kniazev & Fijalkow title is not indexed) | 0 |
| L9 | `get_paper` | 2609.22197 (Rodrigues & Kang 2026) | `view=preview` | **not found** in Lacuna | – |
| L10 | `search_lacuna` | Sudoku hierarchical reasoning model mechanistic probing | `search_type=paper`, `date_from=2026-11-10`, `limit=8` | 14 total, 8 returned | 1 (2611.20371) |
| L11 | `get_paper` | 2611.20371 | `view=blog` | Lacuna-generated summary read; the primary paper was not read | counted in L10 |

New item (not applied to `paper/refs.bib`; the claims below come from the Lacuna summary only and must be checked against the primary paper before any use):

- "Pretty Linear Liars: Unregularized Probes Favor Intervention-Unfaithful Features", arXiv:2611.20371, 2026-11-16 ([Lacuna](https://lacuna.tiptreesystems.com/work/pretty-linear-liars-unregularized-probes-favor-intervention)). According to the summary, unregularized (OLS) regression probes give large weights to low-variance directions that the model does not use, and ridge regularization moves the probe direction towards the direction found by Distributed Alignment Search (DAS). Tested on a toy HMM transformer and on Llama-2-7B. Relevance: E3 decodability versus causal use (plan §1). Our level-wise probes use AdamW with weight decay (`src/ncm_sudoku/probes.py`), and the whole-layer probes read a PCA truncated to 256 components. These PCA components are whitened, and whitening may partly re-amplify the low-variance directions among those 256 components. This is an unverified possible reviewer question, not a finding.

Assessment of the tool (as of 2026-11-22): Lacuna covers arXiv and OpenReview papers, including very recent ones, but it does not index Zenodo and it is missing the two closest prior works (L6, L8, L9). It has no citation graph, and no research direction covers Sudoku or puzzle-model interpretability (L3). It is useful as a supplementary tool for watching recent arXiv papers with date-filtered or semantic paper search. It does not replace Consensus, the arXiv API, Semantic Scholar or Exa.

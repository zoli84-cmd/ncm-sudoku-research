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

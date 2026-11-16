# paper

## Purpose

WP4 manuscript: the arXiv preprint of the preregistered E1–E3 study (design `docs/superpowers/specs/2026-11-15-wp4-manuscript-design.md`).

## Ownership

- `main.tex`, `preamble.tex`, `sections/*.tex`, `refs.bib`: hand-written manuscript sources
- `generated/`: written only by `scripts/wp4_figures.py`; never edited by hand; committed
- `build/`: Tectonic output, git-ignored

## Local Contracts

- Number rule: every result number reaches the text only through `\R{key}` (keys defined in `generated/numbers.tex`, listed in `generated/numbers.json`) or a generated table or figure; no numeric result literal is typed in a section file. `\R` with an unknown key stops the build.
- Claim rule: each confirmatory result is stated with its plan §13 justified claim and "does not follow" boundary; results are conditional on the checkpoint and the intervention policy; descriptive tables carry no inference.
- Author line (user decision 2026-11-16): Zoltán Kárász, independent researcher, ORCID only, no employer affiliation; paper licence CC BY 4.0 (`\paperlicence` in `preamble.tex`), code licence MIT (root `LICENSE`); `sections/statements.tex` holds the AI-use statement and must stay accurate.
- Placeholders: only the repository URL remains a `\placeholder{...}` until the repository is public; `scripts/wp4_build.py --arxiv` fails while any remains.
- Language: English, no compressed prose.
- Figures: drawn at final size (`wp4figures.WIDTH` = text width from `geometry` letterpaper, margin=1.1in in `preamble.tex`; change both together), Computer Modern (`cmr10`, mathtext `cm`), no text below 6 pt, symbols and comparisons as mathtext, not unicode or plain `<`/`>`; pinned by `tests/test_wp4figures.py`.

## Work Guidance

- Tectonic 0.17.0 at `C:\Users\ako2bp\.local\bin\tectonic.exe`; it downloads LaTeX packages on first use through the Px proxy (`HTTPS_PROXY`).
- `refs.bib` entries are verified against their primary sources (all verified 2026-11-16, `literature/presubmission_update_2026-11-16.md`); verify any new entry the same way, never invent author names; arXiv `@misc` entries carry `howpublished = {arXiv:<id>}` because `plainnat` ignores `eprint`.

## Verification

- Regenerate after any input or generator change: `uv run --locked python scripts/wp4_figures.py`; `--check` verifies the committed `generated/` files are current
- Build: `uv run --locked python scripts/wp4_build.py` (PDF in `paper/build/main.pdf`); `--arxiv` adds the placeholder check
- Visual check (no poppler on this machine): render pages to PNG with `uv run --no-project --with pymupdf python -I -c ...` into the git-ignored `.superpowers/preview/`, then inspect them
- Tests: `uv run --locked pytest -q tests/test_wp4_build_script.py tests/test_wp4_figures_script.py tests/test_texlint.py` (the lint test checks `main.tex`, including the abstract, and every section file against `generated/numbers.json`)

## Child DOX Index

- `main.tex`, `preamble.tex`: document and shared preamble (page geometry, `\placeholder`, `\input{generated/numbers.tex}`)
- `sections/`: one file per section (introduction, background, setup, summary, e1, e2, e3, discussion, statements, appendix)
- `refs.bib`: bibliography
- `generated/`: number macros, tables and figures from `scripts/wp4_figures.py`

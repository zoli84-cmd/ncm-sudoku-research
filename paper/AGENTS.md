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
- Placeholders: author, affiliation and licence use `\placeholder{...}` until the user decides; `scripts/wp4_build.py --arxiv` fails while any remains.
- Language: English, no compressed prose.

## Work Guidance

- Tectonic 0.17.0 at `C:\Users\ako2bp\.local\bin\tectonic.exe`; it downloads LaTeX packages on first use through the Px proxy (`HTTPS_PROXY`).
- `refs.bib` entries are verified against their sources before submission.

## Verification

- Regenerate after any input or generator change: `uv run --locked python scripts/wp4_figures.py`; `--check` verifies the committed `generated/` files are current
- Build: `uv run --locked python scripts/wp4_build.py` (PDF in `paper/build/main.pdf`); `--arxiv` adds the placeholder check
- Tests: `uv run --locked pytest -q tests/test_wp4_build_script.py tests/test_wp4_figures_script.py tests/test_texlint.py` (the lint test checks every section file against `generated/numbers.json`)

## Child DOX Index

- `main.tex`, `preamble.tex`: document and shared preamble (`\placeholder`, `\input{generated/numbers.tex}`)
- `sections/`: one file per section (introduction, background, setup, e1, e2, e3, discussion, appendix)
- `refs.bib`: bibliography
- `generated/`: number macros, tables and figures from `scripts/wp4_figures.py`

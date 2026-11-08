# WP0-A: Sudoku Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Model-independent Sudoku tooling for G0/E1–E3: NCM token serialization, output parser and validator metrics, independent solvers, logical labeler, fresh-puzzle generator, and a safe loader for the released evaluation set.

**Architecture:** One pure-Python package `src/ncm_sudoku/` with one module per responsibility, numpy for grids and masks, pytest for every contract. Nothing here imports torch or the upstream `ncm` code; WP0-B (model instrumentation) consumes these modules.

**Tech Stack:** Python 3.12 (uv-managed, WSL2 Ubuntu), numpy, pytest, huggingface_hub (download only).

**Spec:** `research_plan_v3.4.md` (§2.2 items 2, 8; §4, §4.1; §5; §6 metrics; §10) and `DECISIONS.md` D07, D10–D12, D15. Upstream facts: `literature/` is unrelated; serialization facts come from `HazyResearch/ncm@c70274273f489abc73832b2b98584a8483b6b203` `tokenization/sudoku_tokenizer.py`.

## Global Constraints

- All commands run inside WSL2 Ubuntu from the project root (`/mnt/c/Users/ako2bp/Documents/VS Code Projects/NCM-research`); export `UV_LINK_MODE=copy` (the project lives on the Windows filesystem).
- Python pinned with `uv python pin 3.12`; dependencies managed only through `uv add`; `uv.lock` committed.
- Grid representation everywhere: `numpy.ndarray`, shape `(81,)`, dtype `int8`, row-major (cell index `c = 9*row + col`), `0` = blank, `1..9` = digits.
- NCM token ids: `0` blank, `1..9` digits, `10` row separator, `11` BOS. Puzzle sequence = 91 ints: `[11] + 89 + [11]`. Solution/output sequence = 89 ints: 9 rows of 9 digits joined by `10`.
- The parser never repairs model output (§2.2/8, §10): no solver-based fixing, no clue write-back.
- Formatting errors stay in denominators: solve = 0, valid-grid = 0, cell-accuracy denominator stays 81 (§10).
- Labels never read the reference solution (§5.2).
- Released data is untrusted: pickles are never loaded with plain `pickle.load`.
- All files and identifiers in English.

## Review Focus

1. Output of correct length with a digit in a separator slot or a separator in a digit slot → `format_error=True`, positions still identified, bad digit slots count as wrong cells (Task 2 test `test_parse_misplaced_separator`).
2. Inconsistent puzzle input (two equal clues in one unit) → `check_puzzle` reports `consistent=False`; the labeler raises `ConflictError` instead of emitting labels (Task 3 `test_check_inconsistent`, Task 4 `test_waves_inconsistent_input_raises`).
3. Puzzle unsolvable by singles → cells get `STUCK`, never depth 0 or a guessed value (Task 4 `test_waves_stuck_cells`).
4. Generator clue removal that cannot reach 30 clues for a given removal order → deterministic retry with a new order, bounded by `max_attempts`, then `GenerationError` (Task 5 `test_generate_retry_bound`).
5. Released pickle containing a global outside the allowlist → loader raises `UnsafePickleError` (Task 6 `test_safe_unpickler_rejects_global`).

---

### Task 1: Environment, package skeleton, serialization

**Files:**
- Create: `pyproject.toml`, `.python-version`, `uv.lock` (via uv), `src/ncm_sudoku/__init__.py`, `src/ncm_sudoku/grid.py`, `tests/test_grid.py`
- Modify: `AGENTS.md` (Verification section, Child DOX Index entries for `src/`, `tests/`, `docs/`, `pyproject.toml`)

**Interfaces:**
- Produces (`grid.py`): constants `BLANK=0, SEP=10, BOS=11`; `UNITS: np.ndarray` shape `(27, 9)` cell indices (rows 0–8, columns 9–17, boxes 18–26); `PEERS: tuple[frozenset[int], ...]` length 81 (20 peers each); `encode_puzzle_tokens(grid) -> list[int]` (len 91); `encode_solution_tokens(grid) -> list[int]` (len 89); `grid_from_string(s: str) -> np.ndarray` (81 chars, `.` or `0` blank) for tests.

- [ ] **Step 1:** In WSL: install uv if missing (`curl -LsSf https://astral.sh/uv/install.sh | sh`), then `uv init --package --name ncm-sudoku --python 3.12`, `uv python pin 3.12`, `uv add numpy`, `uv add --dev pytest`. Keep `src/` layout.
- [ ] **Step 2: Write failing tests** in `tests/test_grid.py`:
  - `test_units_shape_and_coverage`: `UNITS.shape == (27, 9)`; every cell appears in exactly 3 units.
  - `test_peers`: `len(PEERS[c]) == 20` for all c; `c not in PEERS[c]`; `PEERS[0]` contains 1, 9, 10.
  - `test_encode_puzzle_tokens`: for a grid with `grid[0]=5` and rest blank: length 91, `[0] == [-1] == 11`, token index 1 is 5, token index 10 is `SEP`, count of `SEP` is 8.
  - `test_encode_solution_tokens`: length 89, `tokens[9] == 10`, digits round-trip in row-major order.
- [ ] **Step 3:** Run `uv run pytest tests/test_grid.py -v` → FAIL (import error).
- [ ] **Step 4:** Implement `grid.py`.
- [ ] **Step 5:** Run `uv run pytest -q` → PASS.
- [ ] **Step 6:** Set AGENTS.md `## Verification` to: `In WSL2 from the project root: UV_LINK_MODE=copy uv run pytest -q`. Add index entries for `pyproject.toml`/`uv.lock`, `src/ncm_sudoku/`, `tests/`, `docs/superpowers/plans/`.
- [ ] **Step 7: Commit** `feat: package skeleton and NCM Sudoku serialization`.

### Task 2: Output parser and validator metrics

**Files:**
- Create: `src/ncm_sudoku/validate.py`, `tests/test_validate.py`

**Interfaces:**
- Consumes: `grid.py` (`UNITS`, `SEP`, `encode_solution_tokens`).
- Produces:
  - `@dataclass(frozen=True) ParsedOutput: cells: np.ndarray` (shape 81, int8; `-1` where a slot is missing/invalid), `positions_identified: bool`, `format_error: bool`.
  - `parse_output_tokens(tokens: Sequence[int]) -> ParsedOutput`. Rule: positions are identified iff `len(tokens) == 89`. Digit slot = index `i` with `i % 10 != 9`; separator slot = `i % 10 == 9`. Any non-digit in a digit slot → that cell `-1` and `format_error`; any non-`SEP` in a separator slot → `format_error`. Wrong length → `positions_identified=False`, `format_error=True`, all cells `-1`.
  - `@dataclass(frozen=True) Metrics: well_formed, solve, valid_grid, all_clues_preserved: bool; clue_preservation: float; cell_acc_all, cell_acc_empty: float; constraint_violations: int | None; reference_match: bool`.
  - `evaluate(puzzle: np.ndarray, out: ParsedOutput, reference: np.ndarray) -> Metrics`. `well_formed = not out.format_error`. `constraint_violations` = number of the 27 units that are not a permutation of 1..9, only when well-formed (else `None`). `valid_grid = well_formed and violations == 0`. `solve = valid_grid and all_clues_preserved`. Cell accuracy against `reference`, denominator 81 (all) or number of blanks in `puzzle` (empty); `-1` cells count as wrong; if `not positions_identified` both are `0.0`. `reference_match = well_formed and np.array_equal(out.cells, reference)`.
  - `cell_hamming(a: np.ndarray, b: np.ndarray, cells: np.ndarray | None = None) -> float` — fraction of differing cells over `cells` (default all 81).

- [ ] **Step 1: Write failing tests** (`tests/test_validate.py`), using one fixed valid solution `S` and puzzle `P` (S with 51 cells blanked, written inline as strings):
  - `test_correct_grid`: tokens of `S` → solve, valid_grid, reference_match True; violations 0; cell accuracies 1.0.
  - `test_altered_clue`: valid grid that differs from `P` at a clue (use digit relabeling of S: swap all 1↔2) → valid_grid True, solve False, all_clues_preserved False.
  - `test_row_repeat`, `test_col_repeat`, `test_box_repeat`: single-cell edits of S → valid_grid False, violations ≥ 1 counted on the right unit type.
  - `test_truncated` (88 tokens) and `test_over_long` (90 tokens) → format_error, positions_identified False, solve False, cell_acc_all 0.0.
  - `test_invalid_char`: one digit slot set to 11 → format_error, positions_identified True, that cell `-1`, cell_acc_all == 80/81, solve False.
  - `test_parse_misplaced_separator` (Review Focus 1): digit slot set to 10 and separator slot set to 4 → format_error True, positions_identified True, constraint_violations None.
  - `test_no_repair`: output equal to S except one clue cell changed → reported as clue violation, `out.cells` unchanged.
  - `test_cell_hamming`: identical → 0.0; one cell differs → 1/81; restricted to blanks of P → 1/51 when the differing cell is blank.
- [ ] **Step 2:** `uv run pytest tests/test_validate.py -v` → FAIL.
- [ ] **Step 3:** Implement `validate.py`.
- [ ] **Step 4:** `uv run pytest -q` → PASS.
- [ ] **Step 5: Commit** `feat: output parser and validator metrics`.

### Task 3: Independent solvers and puzzle checks

**Files:**
- Create: `src/ncm_sudoku/solve.py`, `src/ncm_sudoku/dlx.py`, `tests/test_solve.py`

**Interfaces:**
- Consumes: `grid.py` (`UNITS`, `PEERS`).
- Produces:
  - `solve.py`: `count_solutions(grid, limit: int = 2) -> int` (backtracking with minimum-remaining-values cell choice and bitmask candidates; stops at `limit`); `solve_one(grid) -> np.ndarray | None`; `@dataclass(frozen=True) PuzzleStatus: consistent: bool, n_solutions: int` (capped at 2; 0 if inconsistent); `check_puzzle(grid) -> PuzzleStatus` (`consistent` = no unit contains a repeated clue).
  - `dlx.py`: `dlx_count_solutions(grid, limit: int = 2) -> int` — Knuth's Algorithm X with dancing links over the 324-column exact-cover matrix (81 cell, 81 row-digit, 81 col-digit, 81 box-digit constraints). Written independently of `solve.py`; must not import it.

- [ ] **Step 1: Write failing tests:**
  - `test_unique_puzzle`: `P` from Task 2 → both counters return 1; `solve_one(P)` equals `S`.
  - `test_multiple_solutions`: `S` keeping only its first three rows (27 clues) → both return 2 (capped).
  - `test_unsatisfiable`: row 0 holds 1–8 in columns 0–7, a 9 sits in column 8 at row 4, all else blank (consistent clues, r0c8 has no candidate) → both return 0.
  - `test_check_inconsistent` (Review Focus 2): two 5s in row 0 → `consistent=False, n_solutions=0`.
  - `test_empty_grid_limit`: empty grid → both return exactly `limit` for `limit=2`.
  - `test_cross_check_random_masks`: with `np.random.default_rng(0)`, 50 random masks of `S` with 22–35 clues → `count_solutions == dlx_count_solutions` for every mask.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `solve.py`, then `dlx.py`.
- [ ] **Step 4:** `uv run pytest -q` → PASS.
- [ ] **Step 5: Commit** `feat: backtracking and DLX solvers with puzzle checks`.

### Task 4: Logical labeler (candidate mask and synchronous single waves)

**Files:**
- Create: `src/ncm_sudoku/labels.py`, `tests/test_labels.py`

**Interfaces:**
- Consumes: `grid.py` (`UNITS`, `PEERS`); `solve.check_puzzle`.
- Produces:
  - `candidate_mask(grid) -> np.ndarray` shape `(81, 9)` bool; row `c` is meaningful only where `grid[c] == 0`, all-False for given cells. Bit `d-1` true iff digit d is absent among the filled peers of c (§5.1).
  - `naked_singles(grid) -> dict[int, int]` (cell → digit) and `hidden_singles(grid) -> list[tuple[int, int, int]]` (unit, digit, cell) computed from `candidate_mask(grid)`.
  - Constants `STUCK = -1`, `CENSORED = -2`; `class ConflictError(ValueError)`.
  - `@dataclass(frozen=True) WaveResult: depth: np.ndarray` (81, int16; `0` for given cells, `k ≥ 1` first-determination wave, `STUCK`, or `CENSORED`), `rules: tuple[frozenset[str], ...]` (per cell subset of `{"naked", "hidden"}`), `n_waves: int`.
  - `inference_waves(grid, max_waves: int = 81) -> WaveResult` implementing §5.2: from state `P^(k-1)` collect all naked and hidden singles before writing; merge identical derivations; two different digits for one cell, or a derived digit equal to an existing peer value → `ConflictError`; write all at once; stop when no new fill. Unsolved cells → `STUCK`; if `max_waves` is reached with fills still possible → remaining cells `CENSORED`. Raises `ConflictError` if `check_puzzle(grid).consistent` is False.

- [ ] **Step 1: Write failing tests:**
  - `test_candidate_mask_basic`: blank cell whose row holds 1–8 → only bit for 9 set; given cells all-False.
  - `test_naked_equals_popcount`: on `P`, `naked_singles` keys equal cells with exactly one candidate bit.
  - `test_hidden_single`: inline puzzle where digit 7 has exactly one candidate cell in row 0 while that cell has ≥ 2 candidates → `(0, 7, cell)` in `hidden_singles`, cell not in `naked_singles`.
  - `test_waves_depth_one`: grid = `S` with exactly one blank cell → depth 1 at that cell, `rules` contains `"naked"`, `n_waves == 1`.
  - `test_waves_synchronous`: inline puzzle where cell B becomes a single only after cell A is filled → depth(A)=1, depth(B)=2 (no same-wave chaining).
  - `test_waves_solves_easy`: `P` (singles-solvable; assert during test writing) → no `STUCK`, filled values equal `S` (comparison done in the test only; labeler never receives `S`).
  - `test_waves_stuck_cells` (Review Focus 3): Inkala puzzle `800000000003600000070090200050007000000045700000100030001000068008500010090000400` (not solvable by singles) → some cells `STUCK`, none with depth 0 among blanks.
  - `test_waves_censored`: `max_waves=1` on a puzzle needing ≥ 2 waves → wave-2 cells are `CENSORED`.
  - `test_waves_inconsistent_input_raises` (Review Focus 2): two 5s in row 0 → `ConflictError`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `labels.py`.
- [ ] **Step 4:** `uv run pytest -q` → PASS.
- [ ] **Step 5: Commit** `feat: candidate-mask labels and synchronous single waves`.

### Task 5: Fresh-puzzle generator

**Files:**
- Create: `src/ncm_sudoku/generate.py`, `tests/test_generate.py`

**Interfaces:**
- Consumes: `solve.count_solutions`, `solve.check_puzzle`.
- Produces:
  - `random_solution(rng: np.random.Generator) -> np.ndarray` — randomized backtracking fill (shuffled digit order per cell).
  - `@dataclass(frozen=True) GeneratedPuzzle: puzzle: np.ndarray, solution: np.ndarray, puzzle_id: str, seed: int, index: int, attempts: int`.
  - `class GenerationError(RuntimeError)`.
  - `generate_puzzle(seed: int, index: int, n_clues: int = 30, max_attempts: int = 50) -> GeneratedPuzzle`. RNG = `np.random.default_rng([seed, index])`. Draw a solution; then per attempt draw a random cell order and remove cells one by one, keeping a removal only if `count_solutions(..., limit=2) == 1`, stopping at `n_clues`. If an attempt ends above `n_clues`, start a new attempt with a new order on the same solution; after `max_attempts` raise `GenerationError`. `puzzle_id = f"gen-v1-{seed}-{index}"` (provenance = orbit identifier, plan §4.1).
  - `generate_many(seed: int, n: int, n_clues: int = 30) -> list[GeneratedPuzzle]`.

- [ ] **Step 1: Write failing tests:**
  - `test_random_solution_valid`: 5 seeds → every unit is a permutation of 1..9.
  - `test_generate_contract`: `generate_puzzle(1, 0)` → exactly 30 nonzero cells; puzzle agrees with solution on clues; `count_solutions == 1`; `dlx_count_solutions == 1`.
  - `test_generate_deterministic`: same `(seed, index)` → identical puzzle and solution; different index → different solution.
  - `test_generate_retry_bound` (Review Focus 4): `n_clues=17, max_attempts=2` → raises `GenerationError` (17-clue minimal puzzles are practically unreachable by greedy removal).
  - `test_generate_many_ids_unique`: `generate_many(3, 10)` → 10 distinct ids and distinct solutions.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `generate.py`.
- [ ] **Step 4:** `uv run pytest -q` → PASS; note the wall time of `test_generate_contract` in the commit message body (input to the plan's cost measurement, §2.2/9).
- [ ] **Step 5: Commit** `feat: deterministic 30-clue puzzle generator`.

### Task 6: Released evaluation set: download, provenance, safe loading, real-data checks

**Files:**
- Create: `src/ncm_sudoku/released.py`, `scripts/fetch_released_data.py`, `experiments/provenance/released_data.json` (written by the script, committed), `tests/test_released.py`
- Modify: `AGENTS.md` (index entries for `scripts/`, `experiments/provenance/`)

**Interfaces:**
- Consumes: `solve.check_puzzle`, `solve.count_solutions`, `dlx.dlx_count_solutions`.
- Produces:
  - `class UnsafePickleError(ValueError)`; `safe_load_pickle(path: Path) -> object` using a `pickle.Unpickler` subclass whose `find_class` permits only an explicit allowlist `ALLOWED_GLOBALS: frozenset[tuple[str, str]]`, else raises `UnsafePickleError`.
  - `load_released(split_dir: Path) -> tuple[np.ndarray, np.ndarray]` → `(puzzles, solutions)`, each shape `(n, 81)` int8, 0 = blank.
  - Script: `uv run python scripts/fetch_released_data.py --difficulty hard` downloads `sudoku/hard/puzzles.pickle` and `solutions.pickle` from dataset `hazyresearch/ncm-datasets` via `huggingface_hub.hf_hub_download` into `data/released/hard/`, and writes `experiments/provenance/released_data.json` with repo id, resolved commit revision, file names, byte sizes, SHA-256.

- [ ] **Step 1:** `uv add huggingface_hub`. Run the script once. Then inspect each pickle with `python -m pickletools data/released/hard/puzzles.pickle | grep -E "GLOBAL|STACK_GLOBAL" -A1` (no unpickling) and set `ALLOWED_GLOBALS` to exactly the globals found (empty if only builtin containers/ints). Record the found structure in the module docstring.
- [ ] **Step 2: Write failing tests:**
  - `test_safe_unpickler_rejects_global` (Review Focus 5): a pickle built in the test with `pickle.dumps(os.system)`-style global (`b"cos\nsystem\n."`) → `UnsafePickleError`.
  - `test_safe_unpickler_accepts_plain`: `pickle.dumps([[1, 2], [3]])` round-trips.
  - `test_released_hard` (skip with `pytest.skip` if `data/released/hard` is missing): 2000 puzzles; every puzzle has exactly 30 clues; all consistent; each puzzle agrees with its solution on clues; every solution is a valid grid; SHA-256 of both files equals `experiments/provenance/released_data.json`.
  - `test_released_unique_sample` (same skip rule, mark `@pytest.mark.slow`): first 200 puzzles → `count_solutions == 1` and `dlx_count_solutions == 1`.
- [ ] **Step 3:** Run → FAIL.
- [ ] **Step 4:** Implement `released.py` and finish the script.
- [ ] **Step 5:** `uv run pytest -q` and `uv run pytest -q -m slow` → PASS. Register the `slow` marker in `pyproject.toml`.
- [ ] **Step 6:** Update AGENTS.md index; record any surprise (e.g., non-unique released puzzles) as a new `DECISIONS.md` entry instead of silently filtering.
- [ ] **Step 7: Commit** `feat: released evaluation set provenance and safe loader`.

---

## Out of scope (WP0-B, separate plan after reading upstream code)

Upstream submodule, torch CPU environment, checkpoint download with hashes, own CPU runner, G0 reproduction, `forward_with_intervention()`, no-op / sham (B=A) / aliasing identity tests, cost measurement, the D11 distribution gate, and the D16 unit–digit label (its definition must first be aligned with Kniazev & Fijalkow 2026).

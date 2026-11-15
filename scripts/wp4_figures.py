"""Generate the WP4 manuscript numbers, tables and figures into `paper/generated/` from committed results.

Reads only committed files (`ncm_sudoku.wp4numbers.SOURCE_FILES` and `DECISIONS.md`); no model, no
network, no statistic. `--check` regenerates into a temporary directory and exits 1 if any committed
generated file is missing, extra or different.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

from ncm_sudoku import wp4figures, wp4tables
from ncm_sudoku.wp4numbers import collect, load_sources, numbers_json, numbers_tex

ROOT = Path(__file__).resolve().parents[1]

TABLES = {
    "summary": wp4tables.summary_table,
    "readings": wp4tables.readings_table,
    "secondary": wp4tables.secondary_table,
    "depth": wp4tables.depth_table,
    "levels": wp4tables.levels_table,
    "e2_diagnostics": wp4tables.e2_diagnostics_table,
    "e3_matrix": wp4tables.e3_matrix_table,
    "e2_dose": wp4tables.e2_dose_table,
    "e1": wp4tables.e1_table,
    "equivariance": wp4tables.equivariance_table,
}
FIGURES = ("dose_curves", "contrasts_forest", "propagation", "e3_readability", "e3_supporting", "e1_levels")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def generate(root: Path, out: Path) -> list[Path]:
    sources = load_sources(root)
    results = sources["results"]
    numbers = collect(sources)
    written = [_write(out / "numbers.tex", numbers_tex(numbers)), _write(out / "numbers.json", numbers_json(numbers))]
    for name, fn in TABLES.items():
        written.append(_write(out / "tables" / f"{name}.tex", fn(results)))
    written.append(_write(out / "tables" / "deviations.tex", wp4tables.deviations_table(root / "DECISIONS.md")))
    for name in FIGURES:
        path = out / "figures" / f"{name}.pdf"
        wp4figures.save_pdf(getattr(wp4figures, name)(results), path)
        written.append(path)
    return sorted(written)


def _files(base: Path) -> dict[str, bytes]:
    return {p.relative_to(base).as_posix(): p.read_bytes() for p in base.rglob("*") if p.is_file()} if base.exists() else {}


def check(root: Path) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        generate(root, Path(tmp))
        fresh = _files(Path(tmp))
    committed = _files(root / "paper" / "generated")
    problems = [f"missing: {k}" for k in sorted(set(fresh) - set(committed))]
    problems += [f"extra: {k}" for k in sorted(set(committed) - set(fresh))]
    problems += [f"stale: {k}" for k in sorted(set(fresh) & set(committed)) if fresh[k] != committed[k]]
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="compare instead of writing")
    args = ap.parse_args(argv)
    if args.check:
        problems = check(ROOT)
        for p in problems:
            print(p)
        print(json.dumps({"check": "ok" if not problems else "failed", "problems": len(problems)}))
        return 1 if problems else 0
    out = ROOT / "paper" / "generated"
    for path in generate(ROOT, out):
        print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())

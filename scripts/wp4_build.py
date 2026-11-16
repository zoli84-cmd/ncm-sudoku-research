"""Build the WP4 manuscript with Tectonic (`paper/main.tex` -> `paper/build/main.pdf`).

`--arxiv` refuses to build while any `\\placeholder{...}` remains in the manuscript sources.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"\\placeholder\{([^}]*)\}")
COMMENT = re.compile(r"(?<!\\)%.*")


def find_placeholders(paths: list[Path]) -> list[tuple[Path, int, str]]:
    found = []
    for path in paths:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for m in PLACEHOLDER.finditer(COMMENT.sub("", line)):
                found.append((path, i, m.group(1)))
    return found


def sources(root: Path) -> list[Path]:
    paper = root / "paper"
    return [paper / "main.tex", *sorted((paper / "sections").glob("*.tex"))]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arxiv", action="store_true", help="fail while any placeholder remains")
    args = ap.parse_args(argv)
    if args.arxiv:
        found = find_placeholders(sources(ROOT))
        for path, line, text in found:
            print(f"placeholder: {path.relative_to(ROOT)}:{line}: {text}")
        if found:
            return 2
    paper = ROOT / "paper"
    cmd = ["tectonic", "-X", "compile", "main.tex", "--outdir", "build"]
    (paper / "build").mkdir(exist_ok=True)
    return subprocess.run(cmd, cwd=paper).returncode


if __name__ == "__main__":
    sys.exit(main())

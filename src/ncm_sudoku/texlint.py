"""Manuscript lint: no hand-typed result numbers, and every `\\R{key}` is a generated key.

Allowed in section text: integers 0..12 (levels, waves, small counts) and anything inside the
arguments of `\\R`, `\\ref`, `\\eqref`, `\\cite*`, `\\label`, `\\input`, `\\includegraphics`, `\\url`
and the first argument of `\\href`. Comments are ignored. Everything else that looks like a
number (a decimal, a thousands-grouped number, a number followed by `\\%` or `pp`, an integer
above 12) is reported. Arguments are matched within one line.
"""

import re
from pathlib import Path

COMMENT = re.compile(r"(?<!\\)%.*")
SKIP_ARG = re.compile(
    r"\\(?:R|ref|eqref|cite[a-zA-Z]*\*?|label|input|url|includegraphics|href)"
    r"\s*(?:\[[^\]]*\])?\s*\{[^}]*\}"
)
_SEP = r"(?:,|\{,\}|\\,|~)"  # thousands separators: 2,000  2{,}000  2\,000  2~000
_GAP = r"(?:\s|~|\\,)*"  # space before a unit: 5 \%  5~\%  5\,\%
NUMBER = re.compile(
    r"(?<![\w\\])(?<!\d[.,])"
    r"(\d{1,3}(?:" + _SEP + r"\d{3})+"  # grouped
    r"|\d+(?:\.\d+)?[eE][-+]?\d+"  # 1e-3
    r"|\d+\^\{?[-+]?\d+\}?"  # 10^{-3}
    r"|\d*\.\d+|\d+)"
    r"(" + _GAP + r"(?:\\%|pp\b|percentage points\b|percent\b))?"
)
KEY = re.compile(r"\\R\{([^}]*)\}")
MAX_PLAIN_INT = 12


def strip_comments(tex: str) -> str:
    return "\n".join(COMMENT.sub("", line) for line in tex.split("\n"))


def numeric_literals(tex: str) -> list[tuple[int, str]]:
    found = []
    for i, line in enumerate(strip_comments(tex).split("\n"), start=1):
        line = SKIP_ARG.sub(" ", line)
        for m in NUMBER.finditer(line):
            number, suffix = m.group(1), m.group(2)
            plain_small = suffix is None and number.isdigit() and int(number) <= MAX_PLAIN_INT
            if not plain_small:
                found.append((i, m.group(0)))
    return found


def used_keys(tex: str) -> set[str]:
    return set(KEY.findall(strip_comments(tex)))


def manuscript_files(root: Path) -> list[Path]:
    """The top-level files and the shared body (title, abstract) that exist, then every section file in name order."""
    paper = root / "paper"
    tops = [paper / name for name in ("main.tex", "main_anon.tex", "body.tex") if (paper / name).exists()]
    return [*tops, *sorted((paper / "sections").glob("*.tex"))]


def lint(section_paths: list[Path], numbers: dict[str, str]) -> list[str]:
    problems = []
    for path in section_paths:
        tex = path.read_text(encoding="utf-8")
        for line, lit in numeric_literals(tex):
            problems.append(f"{path.name}:{line}: hand-typed number {lit!r}")
        for key in sorted(used_keys(tex) - set(numbers)):
            problems.append(f"{path.name}: unknown result key {key!r}")
    return problems

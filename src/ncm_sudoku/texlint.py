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
NUMBER = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(\s*\\%|\s*pp\b)?")
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


def lint(section_paths: list[Path], numbers: dict[str, str]) -> list[str]:
    problems = []
    for path in section_paths:
        tex = path.read_text(encoding="utf-8")
        for line, lit in numeric_literals(tex):
            problems.append(f"{path.name}:{line}: hand-typed number {lit!r}")
        for key in sorted(used_keys(tex) - set(numbers)):
            problems.append(f"{path.name}: unknown result key {key!r}")
    return problems

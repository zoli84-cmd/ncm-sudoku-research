"""Build the manuscript with Tectonic: the named build (`paper/main.tex` -> `paper/build/main.pdf`) or the anonymous
TMLR submission (`paper/main_anon.tex` -> `paper/build/main_anon.pdf`).

`--check` (alias `--arxiv`) refuses to build while any `\\placeholder{...}` remains; for the anonymous variant it also
checks, after compiling, that the PDF text and metadata contain no identifying string (`FORBIDDEN`) and that the main
text (up to `\\label{main-end}`) ends on page `MAX_MAIN_PAGES` or earlier (TMLR Regular submission).
"""

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"\\placeholder\{([^}]*)\}")
COMMENT = re.compile(r"(?<!\\)%.*")
TOP = {"named": "main", "anon": "main_anon"}
MAX_MAIN_PAGES = 12
# Identifying strings for the double-blind TMLR submission (normalized: lower case, no accents).
FORBIDDEN = (
    "karasz", "zoltan", "0009-0009-7094-6727", "orcid", "zoli84", "ncm-sudoku-research", "osf.io", "hb8vq",
    "m28fx", "10.17605", "1047668", "prereg-v3.7", "wp2-code", "bosch", "ppke", "sztaki", "independent researcher",
)
MAIN_END = re.compile(r"\\newlabel\{main-end\}\{\{[^{}]*\}\{(\d+)\}")


def find_placeholders(paths: list[Path]) -> list[tuple[Path, int, str]]:
    found = []
    for path in paths:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for m in PLACEHOLDER.finditer(COMMENT.sub("", line)):
                found.append((path, i, m.group(1)))
    return found


def sources(root: Path) -> list[Path]:
    paper = root / "paper"
    tops = [paper / name for name in ("main.tex", "main_anon.tex", "body.tex") if (paper / name).exists()]
    return [*tops, *sorted((paper / "sections").glob("*.tex"))]


def normalize(text: str) -> str:
    """Lower case without accents, so that 'Kárász' and 'KARASZ' both match 'karasz'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def anon_violations(pdf_text: str, metadata: dict[str, str]) -> list[str]:
    """Forbidden identifying strings found in the PDF text or in any metadata value, in `FORBIDDEN` order."""
    haystack = normalize(" ".join([pdf_text, *[str(v) for v in metadata.values() if v]]))
    haystack = re.sub(r"\s+", " ", haystack)
    return [s for s in FORBIDDEN if s in haystack]


def main_end_page(aux_text: str) -> int:
    """Page of `\\label{main-end}` from a hyperref `\\newlabel` line of the `.aux` file."""
    m = MAIN_END.search(aux_text)
    if not m:
        raise ValueError("no \\label{main-end} in the aux file")
    return int(m.group(1))


def compile_variant(variant: str) -> int:
    paper = ROOT / "paper"
    (paper / "build").mkdir(exist_ok=True)
    cmd = ["tectonic", "-X", "compile", f"{TOP[variant]}.tex", "--outdir", "build", "--keep-intermediates"]
    return subprocess.run(cmd, cwd=paper).returncode


def read_pdf(path: Path) -> tuple[str, dict[str, str]]:
    import pymupdf  # dev dependency; only needed for the anonymous check

    with pymupdf.open(path) as doc:
        return " ".join(page.get_text() for page in doc), dict(doc.metadata or {})


def read_aux(variant: str) -> str:
    return (ROOT / "paper" / "build" / f"{TOP[variant]}.aux").read_text(encoding="utf-8", errors="replace")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--variant", choices=sorted(TOP), default="named", help="named (default) or anon (TMLR submission)")
    ap.add_argument("--check", "--arxiv", dest="check", action="store_true",
                    help="fail on placeholders; for anon also on identifying strings and a main text over the page limit")
    args = ap.parse_args(argv)
    if args.check:
        found = find_placeholders(sources(ROOT))
        for path, line, text in found:
            print(f"placeholder: {path.relative_to(ROOT)}:{line}: {text}")
        if found:
            return 2
    code = compile_variant(args.variant)
    if code or not (args.check and args.variant == "anon"):
        return code
    problems = []
    text, metadata = read_pdf(ROOT / "paper" / "build" / f"{TOP['anon']}.pdf")
    problems += [f"identifying string in the anonymous PDF: {s}" for s in anon_violations(text, metadata)]
    page = main_end_page(read_aux("anon"))
    if page > MAX_MAIN_PAGES:
        problems.append(f"main text ends on page {page}, above the limit of {MAX_MAIN_PAGES}")
    for p in problems:
        print(p)
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

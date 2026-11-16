"""Build the arXiv source package of the WP4 manuscript.

Steps: refuse while any `\\placeholder{...}` remains (as `wp4_build.py --arxiv`); compile `paper/main.tex` with
Tectonic keeping intermediates, to get the bibliography as `main.bbl` (arXiv does not run BibTeX); copy the
sources and generated inputs plus `main.bbl` into `paper/build/arxiv/`; write `paper/build/arxiv.tar.gz`; report
any non-ASCII character in the staged `.tex`/`.bbl` files (arXiv compiles with pdfLaTeX, not XeTeX).
`refs.bib`, `numbers.json`, `AGENTS.md` and build outputs are not packaged.
"""

import importlib.util
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package_files(paper: Path) -> list[str]:
    """Relative paths (POSIX) of the files arXiv needs, in a fixed order."""
    files = ["main.tex", "preamble.tex"]
    files += [f"sections/{p.name}" for p in sorted((paper / "sections").glob("*.tex"))]
    files += ["generated/numbers.tex"]
    files += [f"generated/tables/{p.name}" for p in sorted((paper / "generated" / "tables").glob("*.tex"))]
    files += [f"generated/figures/{p.name}" for p in sorted((paper / "generated" / "figures").glob("*.pdf"))]
    return files


def stage(paper: Path, bbl: Path, dest: Path) -> list[str]:
    """Copy the package files and `bbl` (as `main.bbl`) into a fresh `dest`; returns the staged relative paths."""
    if not bbl.is_file():
        raise FileNotFoundError(f"bibliography not found: {bbl}")
    if dest.exists():
        shutil.rmtree(dest)
    files = package_files(paper)
    for rel in files:
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(paper / rel, dest / rel)
    shutil.copyfile(bbl, dest / "main.bbl")
    return files + ["main.bbl"]


def make_tarball(dest: Path, files: list[str], out: Path) -> Path:
    with tarfile.open(out, "w:gz") as t:
        for rel in files:
            t.add(dest / rel, arcname=rel)
    return out


def non_ascii(dest: Path, files: list[str]) -> list[tuple[str, int, str]]:
    found = []
    for rel in files:
        if not rel.endswith((".tex", ".bbl")):
            continue
        for i, line in enumerate((dest / rel).read_text(encoding="utf-8").splitlines(), start=1):
            found += [(rel, i, ch) for ch in line if ord(ch) > 127]
    return found


def _build_module():
    spec = importlib.util.spec_from_file_location("wp4_build", ROOT / "scripts" / "wp4_build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    build = _build_module()
    found = build.find_placeholders(build.sources(ROOT))
    for path, line, text in found:
        print(f"placeholder: {path.relative_to(ROOT)}:{line}: {text}")
    if found:
        return 2
    paper = ROOT / "paper"
    work = paper / "build" / "arxiv-work"
    work.mkdir(parents=True, exist_ok=True)
    code = subprocess.run(["tectonic", "-X", "compile", "main.tex", "--outdir", str(work), "--keep-intermediates"],
                          cwd=paper).returncode
    if code:
        return code
    dest = paper / "build" / "arxiv"
    files = stage(paper, work / "main.bbl", dest)
    out = make_tarball(dest, files, paper / "build" / "arxiv.tar.gz")
    for rel, line, ch in non_ascii(dest, files):
        print(f"non-ascii: {rel}:{line}: {ch!r} (U+{ord(ch):04X})")
    print(f"wrote {out.relative_to(ROOT)} ({len(files)} files, {out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

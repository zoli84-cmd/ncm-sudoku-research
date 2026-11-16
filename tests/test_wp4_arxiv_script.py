import importlib.util
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("wp4_arxiv", ROOT / "scripts" / "wp4_arxiv.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def _fake_paper(root: Path) -> Path:
    paper = root / "paper"
    for rel in ("main.tex", "preamble.tex", "refs.bib", "AGENTS.md", "sections/e1.tex", "sections/setup.tex",
                "generated/numbers.tex", "generated/numbers.json", "generated/tables/e1.tex",
                "generated/figures/e1_levels.pdf", "build/main.pdf"):
        (paper / rel).parent.mkdir(parents=True, exist_ok=True)
        (paper / rel).write_text(rel, encoding="utf-8")
    return paper


def test_package_files_lists_sources_and_generated_inputs_only(tmp_path):
    paper = _fake_paper(tmp_path)
    assert mod.package_files(paper) == [
        "main.tex", "preamble.tex", "sections/e1.tex", "sections/setup.tex", "generated/numbers.tex",
        "generated/tables/e1.tex", "generated/figures/e1_levels.pdf",
    ]


def test_stage_copies_files_and_the_bbl_as_main_bbl(tmp_path):
    paper = _fake_paper(tmp_path)
    bbl = tmp_path / "x.bbl"
    bbl.write_text("\\begin{thebibliography}{1}\\end{thebibliography}", encoding="utf-8")
    dest = tmp_path / "out"
    files = mod.stage(paper, bbl, dest)
    assert files[-1] == "main.bbl"
    assert (dest / "main.bbl").read_text(encoding="utf-8").startswith("\\begin{thebibliography}")
    assert (dest / "generated/figures/e1_levels.pdf").exists()
    assert not (dest / "refs.bib").exists() and not (dest / "generated/numbers.json").exists()


def test_stage_refuses_without_bbl(tmp_path):
    paper = _fake_paper(tmp_path)
    with pytest.raises(FileNotFoundError):
        mod.stage(paper, tmp_path / "missing.bbl", tmp_path / "out")


def test_stage_replaces_an_old_staging_directory(tmp_path):
    paper = _fake_paper(tmp_path)
    bbl = tmp_path / "x.bbl"
    bbl.write_text("b", encoding="utf-8")
    dest = tmp_path / "out"
    (dest / "stale").mkdir(parents=True)
    (dest / "stale" / "old.tex").write_text("old", encoding="utf-8")
    mod.stage(paper, bbl, dest)
    assert not (dest / "stale").exists()


def test_tarball_holds_the_staged_files_at_the_archive_root(tmp_path):
    paper = _fake_paper(tmp_path)
    bbl = tmp_path / "x.bbl"
    bbl.write_text("b", encoding="utf-8")
    dest = tmp_path / "out"
    files = mod.stage(paper, bbl, dest)
    tar = mod.make_tarball(dest, files, tmp_path / "arxiv.tar.gz")
    with tarfile.open(tar) as t:
        assert t.getnames() == files


def test_non_ascii_report_names_file_and_character(tmp_path):
    (tmp_path / "main.tex").write_text("\\author{Zolt\u00e1n}\n\u2264\n", encoding="utf-8")
    assert mod.non_ascii(tmp_path, ["main.tex"]) == [("main.tex", 1, "\u00e1"), ("main.tex", 2, "\u2264")]

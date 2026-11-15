import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("wp4_build", ROOT / "scripts" / "wp4_build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def test_find_placeholders_reports_file_line_and_text(tmp_path):
    f = tmp_path / "a.tex"
    f.write_text("x\n\\author{\\placeholder{Author name}}\n% \\placeholder{commented}\n")
    assert mod.find_placeholders([f]) == [(f, 2, "Author name")]


def test_escaped_percent_does_not_start_a_comment(tmp_path):
    f = tmp_path / "a.tex"
    f.write_text("5\\% \\placeholder{Licence}\n")
    assert mod.find_placeholders([f]) == [(f, 1, "Licence")]


def test_arxiv_mode_fails_on_placeholder(tmp_path, monkeypatch, capsys):
    paper = tmp_path / "paper"
    (paper / "sections").mkdir(parents=True)
    (paper / "main.tex").write_text("\\author{\\placeholder{Author name}}\n")
    (paper / "sections" / "setup.tex").write_text("\\section{Setup}\n")
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    def boom(*a, **k):
        raise AssertionError("tectonic must not run in a failing --arxiv check")

    monkeypatch.setattr(subprocess, "run", boom)
    assert mod.main(["--arxiv"]) == 2
    assert "Author name" in capsys.readouterr().out


@pytest.mark.skipif(shutil.which("tectonic") is None, reason="no tectonic")
def test_skeleton_builds():
    assert mod.main([]) == 0
    assert (ROOT / "paper" / "build" / "main.pdf").exists()

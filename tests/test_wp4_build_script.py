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


# --- WP5: anonymous TMLR build checks -------------------------------------------------------------

def test_anon_check_flags_generated_commit():
    assert mod.anon_violations("frozen at commit 1047668", {}) == ["1047668"]


def test_anon_check_ignores_accents_and_case():
    found = mod.anon_violations("Zolt\u00e1n K\u00c1R\u00c1SZ", {})
    assert "karasz" in found and "zoltan" in found


def test_anon_check_reads_metadata():
    assert mod.anon_violations("", {"author": "Zoltan Karasz"})


def test_anon_check_passes_clean_text():
    assert mod.anon_violations("Anonymous authors Paper under double-blind review", {"author": ""}) == []


def test_main_end_page_reads_hyperref_newlabel():
    aux = r"\newlabel{main-end}{{8.3}{12}{The causal study}{section*.4}{}}"
    assert mod.main_end_page(aux) == 12
    with pytest.raises(ValueError):
        mod.main_end_page(r"\newlabel{sec:e1}{{5}{5}{E1}{section.5}{}}")


def test_check_fails_on_page_overrun(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mod, "compile_variant", lambda variant: 0)
    monkeypatch.setattr(mod, "read_pdf", lambda path: ("Anonymous authors", {"author": ""}))
    monkeypatch.setattr(mod, "read_aux", lambda variant: r"\newlabel{main-end}{{8}{13}{x}{y}{}}")
    monkeypatch.setattr(mod, "find_placeholders", lambda paths: [])
    assert mod.main(["--variant", "anon", "--check"]) == 2
    assert "13" in capsys.readouterr().out


def test_check_passes_clean_anon_build(monkeypatch):
    monkeypatch.setattr(mod, "compile_variant", lambda variant: 0)
    monkeypatch.setattr(mod, "read_pdf", lambda path: ("Anonymous authors", {"author": ""}))
    monkeypatch.setattr(mod, "read_aux", lambda variant: r"\newlabel{main-end}{{8}{12}{x}{y}{}}")
    monkeypatch.setattr(mod, "find_placeholders", lambda paths: [])
    assert mod.main(["--variant", "anon", "--check"]) == 0


# --- final review fixes -----------------------------------------------------------------------------

def test_anon_check_survives_line_breaks_in_urls():
    assert "osf.io" in mod.anon_violations("see https://osf.\nio/abcde for the registration", {})


def test_anon_check_survives_hyphenation():
    assert "karasz" in mod.anon_violations("written by K\u00e1-\nr\u00e1sz", {})


def test_anon_check_flags_extra_generated_identifiers():
    assert mod.anon_violations("code at abc1234 frozen", {}, extra=("abc1234",)) == ["abc1234"]


def test_generated_identifiers_read_the_commit_from_numbers_tex(tmp_path):
    gen = tmp_path / "paper" / "generated"
    gen.mkdir(parents=True)
    (gen / "numbers.tex").write_text("\\wpdef{code.commit}{abc1234}\n\\wpdef{n.test}{600}\n", encoding="utf-8")
    assert mod.generated_identifiers(tmp_path) == ("abc1234",)


def test_log_warnings_finds_overfull_and_undefined():
    log = "Overfull \\hbox (3.0pt too wide) in paragraph\nLaTeX Warning: Reference `x' on page 2 undefined\nok line\n"
    found = mod.log_warnings(log)
    assert len(found) == 2


def test_log_warnings_ignores_underfull():
    assert mod.log_warnings("Underfull \\hbox (badness 10000) in paragraph\n") == []


def test_check_fails_on_log_warning(monkeypatch):
    monkeypatch.setattr(mod, "compile_variant", lambda variant: 0)
    monkeypatch.setattr(mod, "read_pdf", lambda path: ("Anonymous authors", {"author": ""}))
    monkeypatch.setattr(mod, "read_aux", lambda variant: r"\newlabel{main-end}{{8}{12}{x}{y}{}}")
    monkeypatch.setattr(mod, "read_log", lambda variant: "LaTeX Warning: Label `a' multiply defined.\n")
    monkeypatch.setattr(mod, "find_placeholders", lambda paths: [])
    monkeypatch.setattr(mod, "generated_identifiers", lambda root: ())
    assert mod.main(["--variant", "anon", "--check"]) == 2


def test_check_does_not_read_outputs_when_compile_fails(monkeypatch):
    monkeypatch.setattr(mod, "compile_variant", lambda variant: 1)
    monkeypatch.setattr(mod, "find_placeholders", lambda paths: [])

    def boom(*a, **k):
        raise AssertionError("must not read a stale PDF after a failed compile")

    monkeypatch.setattr(mod, "read_pdf", boom)
    assert mod.main(["--variant", "anon", "--check"]) == 1

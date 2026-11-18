import json
from pathlib import Path

import pytest

from ncm_sudoku.texlint import lint, numeric_literals, strip_comments, used_keys

ROOT = Path(__file__).resolve().parents[1]


def lits(tex):
    return [lit for _, lit in numeric_literals(tex)]


def test_decimal_found_everywhere():
    tex = "a \\textbf{0.23} b $98.33\\%$ c & 5\\% & d 1,726"
    assert lits(tex) == ["0.23", "98.33\\%", "5\\%", "1,726"]


def test_percentage_points_and_negative_numbers():
    assert lits("a drop of 11 pp and $-0.5$") == ["11 pp", "0.5"]


def test_comments_and_R_arguments_ignored():
    assert numeric_literals("\\R{h1.fam.lo} % 0.5 here\n\\ref{fig:2} \\cite{x2026}") == []


def test_escaped_percent_is_not_a_comment():
    assert lits("we saw 0.7 \\% here % 0.9 hidden") == ["0.7 \\%"]


def test_other_skipped_arguments():
    tex = "\\label{sec:e2} \\input{generated/tables/e3_matrix.tex} \\includegraphics[width=0.9\\linewidth]{generated/figures/f1.pdf} \\url{https://osf.io/m28fx} \\href{https://arxiv.org/abs/2610.14162}{arXiv}"
    assert lits(tex) == []


def test_small_integers_allowed_large_flagged():
    assert lits("level 6 and 12, n = 600") == ["600"]


def test_line_numbers():
    assert numeric_literals("a\nb 0.5\n") == [(2, "0.5")]


def test_strip_comments_keeps_escaped_percent():
    assert strip_comments("5\\% a % b\nc") == "5\\% a \nc"


def test_used_keys():
    assert used_keys("\\R{h1.est} and \\R{h2.fam.lo} % \\R{commented}") == {"h1.est", "h2.fam.lo"}


def test_unknown_key_and_literal_reported(tmp_path):
    f = tmp_path / "s.tex"
    f.write_text("\\R{nope} and 0.25\n")
    problems = lint([f], {"h1.est": "0.0029"})
    assert any("nope" in p for p in problems)
    assert any("0.25" in p and "s.tex:1" in p for p in problems)


@pytest.mark.parametrize("tex,expected", [
    (r"we used 2\,000 puzzles", [r"2\,000"]),
    (r"and 10{,}000 draws", [r"10{,}000"]),
    (r"a value of .5 here", [r".5"]),
    (r"about 5\,\% of cells", [r"5\,\%"]),
    (r"about 5~\% of cells", [r"5~\%"]),
    (r"a drop of 11~pp", [r"11~pp"]),
    (r"a drop of 11\,pp", [r"11\,pp"]),
    (r"about 11 percentage points", [r"11 percentage points"]),
    (r"about 5 percent", [r"5 percent"]),
    (r"learning rate 1e-3", [r"1e-3"]),
    (r"learning rate $10^{-3}$", [r"10^{-3}"]),
])
def test_common_latex_number_spellings_are_caught(tex, expected):
    assert lits(tex) == expected


def test_manuscript_files_include_main_with_abstract(tmp_path):
    from ncm_sudoku.texlint import manuscript_files

    (tmp_path / "paper" / "sections").mkdir(parents=True)
    (tmp_path / "paper" / "main.tex").write_text(r"\begin{abstract}Solved 0.25 of them\end{abstract}" + "\n")
    (tmp_path / "paper" / "sections" / "e1.tex").write_text(r"\section{E1}" + "\n")
    files = manuscript_files(tmp_path)
    assert files[0].name == "main.tex" and files[1].name == "e1.tex"
    assert any("0.25" in p for p in lint(files, {}))


def test_manuscript_files_include_body_and_both_top_files():
    from ncm_sudoku.texlint import manuscript_files

    names = [p.name for p in manuscript_files(ROOT)]
    assert {"main.tex", "main_anon.tex", "body.tex"} <= set(names)


def test_repo_manuscript_is_clean():
    from ncm_sudoku.texlint import manuscript_files

    path = ROOT / "paper" / "generated" / "numbers.json"
    nums = json.loads(path.read_text(encoding="utf-8"))
    assert lint(manuscript_files(ROOT), nums) == []




def test_manuscript_labels_are_unique():
    import collections
    import re as _re

    labels = collections.Counter()
    for path in [ROOT / "paper" / "main.tex", *sorted((ROOT / "paper" / "sections").glob("*.tex"))]:
        labels.update(_re.findall(r"\\label\{([^}]+)\}", path.read_text(encoding="utf-8")))
    assert [k for k, n in labels.items() if n > 1] == []

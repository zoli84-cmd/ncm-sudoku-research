"""WP4 LaTeX tables from committed results; each function returns a complete booktabs tabular.

The section file supplies the table float, caption and label. Values are formatted with
`wp4numbers.fmt`; a stored None (not applicable) prints as "--".
"""

import re
from pathlib import Path

from ncm_sudoku.wp4numbers import fmt, lookup

TEXT = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\\": r"\textbackslash{}"}
MATH = {"±": r"\pm", "θ": r"\theta", "₁": "_1", "₂": "_2", "′": "'", "−": "-", "≈": r"\approx",
        "≤": r"\le", "≥": r"\ge", "×": r"\times", "Δ": r"\Delta"}

DEVIATIONS = {
    "D78": "Plan review reading of plan section 7.4: full state tensors are not saved; cumulative-state distances and intermediate decodings exist for the primary configurations only",
    "D79": "Implementation reading of the naked-single F1 (secondary metric), fixed before the code freeze",
    "D81": "Post-freeze fix before any TEST run: retry of a directory rename on Windows",
    "D82": "Correction of D81: the rename failed because of an unreleased memory map; fixed at the source and re-tagged before any TEST run",
    "D84": "E4 dropped: the plan section 9.1 entry condition is not met given the TEST readout and equivariance results; SELECT and E4-TEST were never generated",
}


def escape(text: str) -> str:
    parts: list[tuple[bool, str]] = []
    for ch in text:
        if ch in MATH:
            parts.append((True, MATH[ch]))
        else:
            parts.append((False, TEXT.get(ch, ch)))
    out, math = [], []
    for is_math, s in parts + [(False, "")]:
        if is_math:
            math.append(s)
            continue
        if math:
            out.append("$" + "".join(math) + "$")
            math = []
        out.append(s)
    return "".join(out)


def req(doc: dict, path: str):
    """Value at a dotted path that must exist and not be None; KeyError names the path otherwise."""
    value = lookup(doc, path)
    if value is None:
        raise KeyError(path)
    return value


def _cell(x, kind: str) -> str:
    return "--" if x is None else fmt(x, kind)


def _tabular(spec: str, header: list[str], rows: list[list[str]]) -> str:
    lines = [f"\\begin{{tabular}}{{{spec}}}", "\\toprule", " & ".join(header) + " \\\\", "\\midrule"]
    lines += [" & ".join(r) + " \\\\" for r in rows]
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def _interval(ci: list, kind: str) -> str:
    return f"[{fmt(ci[0], kind)}, {fmt(ci[1], kind)}]"


def _reading(results: dict, hyp: str) -> dict:
    reading = next((r for r in results["readings"] if r["hypothesis"] == hyp), None)
    if reading is None:
        raise KeyError(f"no §13 reading for {hyp}")
    return reading


PRIMARY = (("H1", "dec4", "Brier"), ("H2", "pp1", "pp"), ("H3", "pp1", "pp"))


def primary_table(results: dict) -> str:
    """Estimates, family and 95% intervals and the registered result row of H1-H3."""
    rows = []
    for hyp, kind, scale in PRIMARY:
        base = f"primary.{hyp}"
        rows.append([hyp, scale, fmt(req(results, f"{base}.estimate"), kind),
                     _interval(req(results, f"{base}.family.ci"), kind),
                     _interval(req(results, f"{base}.ci95.ci"), kind), escape(_reading(results, hyp)["result"])])
    header = ["", "Scale", "Estimate", "Family interval", "95\\% interval", "Registered result"]
    return _tabular("llrll p{3.3cm}", header, rows)


def readings_table(results: dict) -> str:
    """The §13 justified claim and its "does not follow" boundary for H1-H3."""
    rows = [[hyp, escape(_reading(results, hyp)["claim"]), escape(_reading(results, hyp)["does_not_follow"])]
            for hyp, _, _ in PRIMARY]
    return _tabular("l p{5.0cm} p{5.8cm}", ["", "Justified claim", "Does not follow"], rows)


def e3_matrix_table(results: dict) -> str:
    # Not applicable (None -> "--"): reference, relative_difference and n_params of label-free rows.
    rows = [[escape(r["row"]), escape(r["construction"]), fmt(req(results, f"tables.e3_main.{i}.brier"), "dec4"),
             escape(r["reference"]) if r["reference"] else "--", _cell(r["relative_difference"], "pct1"),
             _cell(r["n_params"], "int")]
            for i, r in enumerate(results["tables"]["e3_main"])]
    header = ["Row", "Constr.", "Brier", "Reference", "Rel.\\ diff.\\ (\\%)", "Params"]
    return _tabular("llrlrr", header, rows)


def e2_dose_table(results: dict) -> str:
    e2 = results["tables"]["e2"]
    rows = []
    for policy in ("frequency", "uniform"):
        l1 = e2["level1"][policy]
        s = l1["solve_mean"]
        rows.append(["1", policy, "enumerated", fmt(l1["n_eligible"], "int"), fmt(l1["excluded_share"], "pct1"),
                     fmt(s["A"], "pct1"), fmt(s["C"], "pct1"), fmt(s["D"], "pct1")])
    for c in e2["configurations"]:
        s = c["solve_mean"]
        rows.append([str(c["level"]), c["policy"], fmt(c["dose"], "int"), fmt(c["n_records"], "int"),
                     fmt(c["excluded_share"], "pct1"), fmt(s["A"], "pct1"), fmt(s["C"], "pct1"),
                     fmt(s["D"], "pct1")])
    header = ["Level", "Policy", "Dose", "Runs", "Excl.\\ (\\%)", "A (\\%)", "C (\\%)", "D (\\%)"]
    return _tabular("rllrrrrr", header, rows)


def e1_table(results: dict) -> str:
    e1 = results["tables"]["e1"]
    g = e1["generated"]
    items = [
        ("Generated: solved (\\%)", fmt(g["solve"], "pct1")),
        ("Generated: valid grid (\\%)", fmt(g["valid_grid"], "pct1")),
        ("Generated: well formed (\\%)", fmt(g["well_formed"], "pct1")),
        ("Generated: cell accuracy, all cells (\\%)", fmt(g["cell_acc_all"], "pct1")),
        ("Generated: cell accuracy, empty cells (\\%)", fmt(g["cell_acc_empty"], "pct1")),
        ("Official metric: exact (\\%)", fmt(e1["official_exact_share"], "pct1")),
        ("Teacher codes decoded: exact (\\%)", fmt(e1["teacher"]["exact_share"], "pct1")),
        ("Hamming distance, tokens", fmt(e1["hamming"]["token_mean"], "dec4")),
        ("Hamming distance, cells", fmt(e1["hamming"]["cell_mean"], "dec4")),
        ("Hamming distance, originally empty cells", fmt(e1["hamming"]["cell_empty_mean"], "dec4")),
        ("Puzzles", fmt(e1["n"], "int")),
    ]
    return _tabular("lr", ["Quantity", "Value"], [[a, b] for a, b in items])


def equivariance_table(results: dict) -> str:
    cats = results["tables"]["equivariance"]["categories"]
    rows = [[name, fmt(c["mean_deviation"], "dec4"), fmt(c["share_within"], "pct1"),
             fmt(c["brier_transformed"], "dec4"), fmt(c["brier_original"], "dec4")]
            for name, c in cats.items()]
    header = ["Category", "Mean deviation", "Within tol.\\ (\\%)", "Brier, transformed", "Brier, original"]
    return _tabular("lrrrr", header, rows)


def deviations_table(decisions: Path) -> str:
    text = decisions.read_text(encoding="utf-8")
    rows = []
    for did, summary in DEVIATIONS.items():
        if not re.search(rf"^\| {did} \|", text, flags=re.M):
            raise KeyError(f"{did} not found in {decisions.name}")
        rows.append([did, escape(summary)])
    return _tabular("l p{10.8cm}", ["Entry", "Decision (DECISIONS.md)"], rows)

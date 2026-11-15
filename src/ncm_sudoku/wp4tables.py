"""WP4 LaTeX tables from committed results; each function returns a complete booktabs tabular.

The section file supplies the table float, caption and label. Values are formatted with
`wp4numbers.fmt`; a stored None (not applicable) prints as "--".
"""

import re
from pathlib import Path

from ncm_sudoku.wp4numbers import (
    H1_MARGIN, H2_PRACTICAL, H3_PRACTICAL, THETA2P_MARGIN, THETA_T_MARGIN, fmt, lookup,
)

TEXT = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\\": r"\textbackslash{}"}
MATH = {"±": r"\pm", "θ": r"\theta", "₁": "_1", "₂": "_2", "′": "'", "−": "-", "≈": r"\approx",
        "≤": r"\le", "≥": r"\ge", "×": r"\times", "Δ": r"\Delta"}

DEVIATIONS = {
    ("D77",): "Implementation readings of details the protocol text left open, fixed before the code freeze (for example: the level-12 readability criterion is the 95% interval of its whole-layer contrast above zero; the equivariance result gets no mechanical reading)",
    ("D78",): "Plan review: the plan section 8.2 controls (random features, label permutation, teacher state, training-size curve) also run on the primary whole-layer probe; full state tensors are not saved, so cumulative-state distances and intermediate decodings exist only for the level-1 enumeration and the single level-11 replacement under the frequency policy (plan section 7.4 reading); the hidden-single F1 scores (puzzle, unit, digit, cell) items, so a prediction must name the right cell",
    ("D79",): "Definition of the naked-single F1 (secondary metric): items are cells; a true item has exactly one candidate, a predicted item exactly one digit with probability at least 0.5; a match needs the same cell and digit",
    ("D81", "D82"): "An implementation defect that stopped the dry run (a directory holding an unreleased memory-mapped file could not be renamed) was diagnosed and fixed, the code re-tagged and the dry run repeated, before any model ran on TEST",
    ("D84",): "E4 dropped after the TEST results: its entry condition was judged very unlikely to hold given the level-6 readout below the practical threshold and the non-equivariant level-12 readout; the formal gate on SELECT was not evaluated, and SELECT and E4-TEST were never generated",
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


PRIMARY_HYPS = ("H1", "H2", "H3")

# (label, result path, format kind, scale, interval field, threshold code)
SUMMARY = (
    ("H1: level-6 readability", "primary.H1", "dec4", "Brier", "family", "h1"),
    ("H2: level 1 vs.\\ 11", "primary.H2", "pp1", "pp", "family", "h2"),
    ("H3: compensation", "primary.H3", "pp1", "pp", "family", "h3"),
    ("Level 2 vs.\\ 11 (secondary)", "secondary.theta2_prime", "pp1", "pp", "ci95", "theta2p"),
    ("Level 12, teacher vs.\\ generated (secondary)", "secondary.theta_T", "sig2", "Brier", "ci95", "thetaT"),
)
EQUIVALENCE = ("h1", "theta2p", "thetaT")


def _threshold(code: str) -> str:
    return {
        "h1": f"$\\pm${fmt(H1_MARGIN, 'g')}",
        "h2": f"{fmt(H2_PRACTICAL, 'pp1')} pp",
        "h3": f"{fmt(H3_PRACTICAL, 'pp1')} pp",
        "theta2p": f"$\\pm${fmt(THETA2P_MARGIN, 'pp1')} pp",
        "thetaT": f"$\\pm${fmt(THETA_T_MARGIN, 'g')}",
    }[code]


def summary_table(results: dict) -> str:
    """Confirmatory and registered secondary contrasts: estimate, interval, equivalence interval, threshold."""
    rows = []
    for label, path, kind, scale, interval, code in SUMMARY:
        ci = _interval(req(results, f"{path}.{interval}.ci"), kind)
        eq = _interval(req(results, f"{path}.tost.ci"), kind) if code in EQUIVALENCE else "--"
        rows.append([label, scale, fmt(req(results, f"{path}.estimate"), kind), ci, eq, _threshold(code)])
    header = ["Contrast", "Scale", "Estimate", "Interval", "Equiv.\\ interval", "Threshold"]
    return _tabular("p{3.3cm}lrllr", header, rows)


def _reading(results: dict, hyp: str) -> dict:
    reading = next((r for r in results["readings"] if r["hypothesis"] == hyp), None)
    if reading is None:
        raise KeyError(f"no §13 reading for {hyp}")
    return reading


READING_LABELS = {"H1": "H1", "H2": "H2", "H3": "H3", "theta2_prime": "Level 2 vs.\\ 11", "level12": "Level 12"}


def readings_table(results: dict) -> str:
    """Every triggered §13 row: registered result, justified claim and "does not follow"."""
    for hyp in PRIMARY_HYPS:
        _reading(results, hyp)
    rows = [[READING_LABELS.get(r["hypothesis"], escape(r["hypothesis"])), escape(r["result"]), escape(r["claim"]),
             escape(r["does_not_follow"])]
            for r in results["readings"] if r["row"]]
    header = ["", "Registered result", "Justified claim", "Does not follow"]
    return _tabular("p{1.3cm} p{2.9cm} p{3.2cm} p{3.9cm}", header, rows)


SECONDARY_ROWS = (
    ("wl_L06.generated", "Whole-layer, level 6"), ("wl_L06.permuted", "Whole-layer, level 6, permuted"),
    ("pc_L06.linear", "Per-cell, level 6"), ("pc_L06.mlp", "Per-cell MLP, level 6"),
    ("wl_L12.generated", "Whole-layer, level 12"), ("wl_teacher_L12.teacher", "Whole-layer, teacher level 12"),
    ("raw_projected.linear", "Raw input, projected"), ("raw_unprojected.linear", "Raw input, unprojected"),
    ("controls.raw_mlp", "Raw input, MLP"), ("controls.peer_counts_linear", "Peer digit counts"),
    ("controls.surface_linear", "Surface features"), ("controls.rule", "Exact rule"),
)


def _sec(results: dict, row: str, field: str):
    value = results["tables"]["secondary_metrics"].get(row)
    for part in field.split("."):
        if not isinstance(value, dict) or value.get(part) is None:
            raise KeyError(f"tables.secondary_metrics[{row}].{field}")
        value = value[part]
    return value


def secondary_table(results: dict) -> str:
    """Registered secondary candidate-mask metrics (threshold 0.5) per probe and control."""
    rows = [[label, fmt(_sec(results, row, "f1.macro"), "dec4"), fmt(_sec(results, row, "ranking.pr_auc_macro"), "dec4"),
             fmt(_sec(results, row, "mask_exact_match"), "pct1"), fmt(_sec(results, row, "count_mae"), "sig2"),
             fmt(_sec(results, row, "naked_single_f1"), "dec4"), fmt(_sec(results, row, "hidden_single_f1.all.f1"), "dec4"),
             fmt(_sec(results, row, "hidden_single_f1.hidden_only.f1"), "dec4")]
            for row, label in SECONDARY_ROWS]
    header = ["Readout", "Macro F1", "PR-AUC", "Mask exact (\\%)", "Count MAE", "Naked F1", "Hidden F1", "Hidden-only F1"]
    return _tabular("lrrrrrrr", header, rows)


DEPTHS = ((("1", "1"), ("2", "2"), ("3", "3"), (">=4", "$\\ge$4"), ("stuck", "stuck")))
DEPTH_ROWS = ("wl_L06.generated", "pc_L06.linear", "raw_unprojected.linear", "raw_projected.linear")


def _depth(results: dict, row: str, part: str, stratum: str, field: str):
    try:
        value = results["tables"]["depth"][row][part][stratum][field]
    except (KeyError, TypeError):
        value = None
    if value is None:
        raise KeyError(f"tables.depth[{row}].{part}.{stratum}.{field}")
    return value


def depth_table(results: dict) -> str:
    """Level-6 Brier by inference depth with sample sizes and label rates (descriptive)."""
    rows = []
    for stratum, label in DEPTHS:
        base = DEPTH_ROWS[0]
        rows.append([label, fmt(_depth(results, base, "label_rates", stratum, "n_cells"), "int"),
                     fmt(_depth(results, base, "label_rates", stratum, "n_puzzles"), "int"),
                     fmt(_depth(results, base, "label_rates", stratum, "positive_rate"), "pct1")]
                    + [fmt(_depth(results, row, "brier", stratum, "brier"), "dec4") for row in DEPTH_ROWS])
    header = ["Depth", "Cells", "Puzzles", "Positive (\\%)", "Whole-layer", "Per-cell", "Raw, unproj.", "Raw, proj."]
    return _tabular("lrrrrrrr", header, rows)


def levels_table(results: dict) -> str:
    """Brier by level for whole-layer and per-cell probes and their permuted controls."""
    rows = []
    for lv in ("L02", "L06", "L12"):
        base = f"tables.e3_levels.{lv}"
        rows.append([str(int(lv[1:]))] + [fmt(req(results, f"{base}.{p}"), "dec4") for p in (
            "whole_layer.generated", "whole_layer.permuted", "per_cell.linear", "per_cell.mlp", "per_cell.permuted")])
    header = ["Level", "Whole-layer", "Whole-layer permuted", "Per-cell", "Per-cell MLP", "Per-cell permuted"]
    return _tabular("rrrrrr", header, rows)


def e2_diagnostics_table(results: dict) -> str:
    """Initial damage (median and upper-quartile TV, empty-cell TV), latent distance and format errors."""
    entries = [(lv, pol, dose, path) for lv, pol, dose, path, _ in _e2_entries(results)]
    rows = []
    for level, policy, dose, path in entries:
        rows.append([level, policy, dose, fmt(req(results, f"{path}.quantiles.tv.2"), "sig2"),
                     fmt(req(results, f"{path}.quantiles.tv.3"), "sig2"),
                     fmt(req(results, f"{path}.quantiles.tv_empty.2"), "sig2"),
                     fmt(req(results, f"{path}.quantiles.latent.2"), "sig2"),
                     fmt(req(results, f"{path}.format_error_share.C"), "pct1"),
                     fmt(req(results, f"{path}.format_error_share.D"), "pct1")])
    header = ["Level", "Policy", "Dose", "TV median", "TV $Q_3$", "TV empty, median", "Latent, median",
              "Format C (\\%)", "Format D (\\%)"]
    return _tabular("rllrrrrrr", header, rows)


def _e2_entries(results: dict) -> list[tuple[str, str, str, str, str]]:
    """(level, policy, dose label, damage path, replacement key) for the level-1 rows and every configuration."""
    e2 = results["tables"]["e2"]
    entries = [("1", p, "enum.", f"tables.e2.level1.{p}", f"level1-{p}") for p in ("frequency", "uniform")]
    for c in e2["configurations"]:
        lv, pol, dose = c["level"], c["policy"], c["dose"]
        entries.append((str(lv), pol, str(dose), f"tables.e2.configurations[level={lv},policy={pol},dose={dose}]",
                        f"L{lv:02d}-{pol}-d{dose}"))
    return entries


def e2_replacement_table(results: dict) -> str:
    """Replacement diagnostics: generator probability of the original and the new code, CAL frequency of the
    new code, replacement vector norm and re-quantization ratio (medians)."""
    rows = []
    for level, policy, dose, path, key in _e2_entries(results):
        rp = f"tables.e2_diagnostics.replacement.{key}"
        rows.append([level, policy, dose, fmt(req(results, f"{rp}.p_orig.2"), "sig2"),
                     fmt(req(results, f"{rp}.p_new.2"), "sig2"), fmt(req(results, f"{rp}.freq_new.2"), "sig2"),
                     fmt(req(results, f"{rp}.replacement_norm.2"), "sig2"),
                     fmt(req(results, f"{path}.quantiles.requant_ratio.2"), "sig2")])
    header = ["Level", "Policy", "Dose", "$p$ original", "$p$ new", "CAL freq.\\ new", "Replacement norm",
              "Re-quant.\\ ratio"]
    return _tabular("rllrrrrr", header, rows)


def per_digit_f1_table(results: dict) -> str:
    """Per-digit F1 (threshold 0.5) of the primary probe and the projected raw-input probe."""
    rows = []
    for row, label in (("wl_L06.generated", "Whole-layer, level 6"), ("raw_projected.linear", "Raw input, projected")):
        values = _sec(results, row, "f1.per_digit")
        if len(values) != 9:
            raise KeyError(f"tables.secondary_metrics[{row}].f1.per_digit must have 9 entries")
        rows.append([label] + [fmt(v, "dec4") for v in values])
    return _tabular("l" + "r" * 9, ["Readout"] + [str(d) for d in range(1, 10)], rows)


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
    names = {"all": "full group", "digit": "digit permutations only", "geometric": "grid transformations only"}
    rows = [[names.get(name, escape(name)), fmt(c["mean_deviation"], "dec4"), fmt(c["share_within"], "pct1"),
             fmt(c["brier_transformed"], "dec4"), fmt(c["brier_original"], "dec4")]
            for name, c in cats.items()]
    header = ["Category", "Mean deviation", "Within tol.\\ (\\%)", "Brier, transformed", "Brier, original"]
    return _tabular("lrrrr", header, rows)


def deviations_table(decisions: Path) -> str:
    text = decisions.read_text(encoding="utf-8")
    rows = []
    for ids, summary in DEVIATIONS.items():
        for did in ids:
            if not re.search(rf"^\| {did} \|", text, flags=re.M):
                raise KeyError(f"{did} not found in {decisions.name}")
        rows.append([", ".join(ids), escape(summary)])
    return _tabular("l p{10.6cm}", ["Entry", "Decision (DECISIONS.md)"], rows)

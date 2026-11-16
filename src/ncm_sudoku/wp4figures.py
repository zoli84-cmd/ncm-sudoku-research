"""WP4 figures from committed results; every function takes the parsed `results.json` and returns a Figure.

No file is read here and no statistic is computed: intervals and estimates are the stored ones.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ncm_sudoku.wp4numbers import H1_MARGIN, H2_PRACTICAL, H3_PRACTICAL, THETA2P_MARGIN  # noqa: E402
from ncm_sudoku.wp4tables import req  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "font.family": "serif", "font.serif": ["cmr10"],
                     "mathtext.fontset": "cm", "axes.formatter.use_mathtext": True, "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
                     "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7})
# Okabe-Ito colour-blind-safe palette
BLUE, ORANGE, GREEN, VERMILLION, PURPLE, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#999999"
WIDTH = 6.3  # inches, the text width set by geometry (letterpaper, margin=1.1in) in paper/preamble.tex


def save_pdf(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf", bbox_inches="tight",
                metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
    plt.close(fig)


def dose_curves(results: dict):
    """Solve share of branches C and D against dose for levels 2, 6, 11 under both policies (descriptive)."""
    configs = results["tables"]["e2"]["configurations"]
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 2.2), sharey=True)
    for ax, level in zip(axes, (2, 6, 11)):
        for policy, style in (("frequency", "-"), ("uniform", "--")):
            rows = sorted((c for c in configs if c["level"] == level and c["policy"] == policy),
                          key=lambda c: c["dose"])
            if not rows:
                raise KeyError(f"no E2 configuration for level {level}, policy {policy}")
            dose = [c["dose"] for c in rows]
            for branch, colour in (("C", ORANGE), ("D", BLUE)):
                ax.plot(dose, [100 * c["solve_mean"][branch] for c in rows], style, color=colour, marker="o",
                        markersize=3, label=f"{branch}, {policy}")
        ax.set_title(f"Level {level}")
        ax.set_xscale("log")
        ax.minorticks_off()
        ax.set_xticks(dose, [str(d) for d in dose])
        ax.set_xlabel("Dose (replaced codes)")
    axes[0].set_ylabel("Solved (%), descriptive")
    axes[0].legend(frameon=False)
    fig.tight_layout()
    return fig


FOREST_ROWS = (
    ("H2 (level 1 vs. 11)", "primary.H2", True),
    ("H3 (compensation)", "primary.H3", True),
    (r"$\theta_2'$ (level 2 vs. 11)", "secondary.theta2_prime", False),
    (r"Uniform: $\theta_2$", "secondary.uniform.theta2", False),
    (r"Uniform: $\theta_{\mathrm{comp}}$", "secondary.uniform.theta_comp", False),
    (r"Uniform: $\theta_2'$", "secondary.uniform.theta2_prime", False),
    (r"Correct baseline: $\theta_2$", "secondary.correct_baseline.theta2", False),
    (r"Correct baseline: $\theta_{\mathrm{comp}}$", "secondary.correct_baseline.theta_comp", False),
)


def contrasts_forest(results: dict):
    """E2 contrasts in percentage points: family interval (primary, thick) and 95% interval (thin)."""
    fig, ax = plt.subplots(figsize=(WIDTH, 2.8))
    n = len(FOREST_ROWS)
    for i, (label, path, primary) in enumerate(FOREST_ROWS):
        y = n - 1 - i
        lo, hi = (100 * v for v in req(results, f"{path}.ci95.ci"))
        ax.plot([lo, hi], [y, y], color=GREY if not primary else BLUE, linewidth=1)
        if primary:
            flo, fhi = (100 * v for v in req(results, f"{path}.family.ci"))
            ax.plot([flo, fhi], [y, y], color=BLUE, linewidth=3, alpha=0.5)
        ax.plot([100 * req(results, f"{path}.estimate")], [y], "o", color=BLUE if primary else "black", markersize=4)
    ax.axvline(0, color="black", linewidth=0.6)
    # Each registered threshold is drawn only on the rows it applies to; drawn across all rows,
    # the H3 threshold (+3 pp) and the theta_2' equivalence bound (+3 pp) would coincide.
    row_y = {path: n - 1 - i for i, (_, path, _) in enumerate(FOREST_ROWS)}
    marks = (
        ("H2 practical threshold", "H2 practical threshold", (-100 * H2_PRACTICAL,), ("primary.H2",), VERMILLION, ":", 1.2),
        ("H3 practical threshold", "H3 practical threshold", (100 * H3_PRACTICAL,), ("primary.H3",), GREEN, ":", 1.2),
        ("equivalence", r"$\theta_2'$ equivalence range", (-100 * THETA2P_MARGIN, 100 * THETA2P_MARGIN),
         ("secondary.theta2_prime", "secondary.uniform.theta2_prime"), PURPLE, "--", 0.9),
    )
    for gid, label, xs, paths, colour, style, width in marks:
        first = True
        for path in paths:
            y = row_y[path]
            for x in xs:
                line, = ax.plot([x, x], [y - 0.4, y + 0.4], color=colour, linestyle=style, linewidth=width,
                                label=label if first else None)
                line.set_gid(f"{gid}:{path}:{x}")
                first = False
    ax.set_yticks(range(n), [r[0] for r in reversed(FOREST_ROWS)])
    ax.set_xlabel("Difference in solve share (percentage points)")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    fig.tight_layout()
    return fig


PRIMARY_PROPAGATION = ("level1-frequency", "level1-uniform", "L11-frequency-d1")


def propagation(results: dict):
    """Mean later-level D code changes per configuration, and per-level state distances (primary configurations)."""
    diag = results["tables"]["e2_diagnostics"]
    changes = diag["later_level_changes"]
    names = list(changes)
    grid = np.full((len(names), 12), np.nan)
    for i, name in enumerate(names):
        for level, v in changes[name].items():
            grid[i, int(level) - 1] = v
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH, 4.2), gridspec_kw={"width_ratios": [1.3, 1]})
    im = ax1.imshow(grid, aspect="auto", cmap="viridis", interpolation="nearest")
    ax1.set_xticks(range(12), [str(i) for i in range(1, 13)])
    ax1.set_yticks(range(len(names)), names, fontsize=6)
    ax1.set_xlabel("Later level")
    fig.colorbar(im, ax=ax1, label="Mean changed D codes")
    prop = diag["propagation"]
    for name, colour in zip(PRIMARY_PROPAGATION, (BLUE, ORANGE, GREEN)):
        levels = range(1, 13)
        ax2.plot(levels, prop[name]["state_dist_C"], "--", color=colour, label=f"{name}, C")
        ax2.plot(levels, prop[name]["state_dist_D"], "-", color=colour, label=f"{name}, D")
    ax2.set_xticks(range(1, 13), [str(i) for i in range(1, 13)])
    ax2.set_xlabel("Level")
    ax2.set_ylabel("Relative cumulative-state distance to A")
    ax2.legend(frameon=False, fontsize=6)
    fig.tight_layout()
    return fig


def _main_row(results: dict, row: str) -> float:
    return next(r["brier"] for r in results["tables"]["e3_main"] if r["row"] == row)


def e3_readability(results: dict):
    """Brier by level (whole-layer generated, permuted, teacher; raw input) and θ₁ per level with the ±margin band."""
    levels = results["tables"]["e3_levels"]
    xs = (2, 6, 12)
    keys = ("L02", "L06", "L12")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH, 2.4))
    ax1.plot(xs, [levels[k]["whole_layer"]["generated"] for k in keys], "o-", color=BLUE, label="Generated")
    ax1.plot(xs, [levels[k]["whole_layer"]["permuted"] for k in keys], "s--", color=GREY, label="Permuted null")
    ax1.plot((6, 12), (_main_row(results, "wl_teacher_L06.teacher"), _main_row(results, "wl_teacher_L12.teacher")),
             "^:", color=ORANGE, label="Teacher (levels 6 and 12)")
    ax1.axhline(_main_row(results, "raw_unprojected.linear"), color=GREEN, linewidth=0.8, label="Raw input, unprojected (linear)")
    ax1.set_xticks(xs)
    ax1.set_xlabel("Level")
    ax1.set_ylabel("Brier loss (TEST)")
    ax1.legend(frameon=False)
    rows = ((2, req(results, "secondary.theta1_wl.L02.estimate"), req(results, "secondary.theta1_wl.L02.ci95.ci")),
            (6, req(results, "primary.H1.estimate"), req(results, "primary.H1.family.ci")),
            (12, req(results, "secondary.theta1_wl.L12.estimate"), req(results, "secondary.theta1_wl.L12.ci95.ci")))
    ax2.axhspan(-H1_MARGIN, H1_MARGIN, color=GREY, alpha=0.2, label=r"$\pm$practical threshold")
    for x, est, ci in rows:
        label = ("H1 family interval" if x == 6 else "95% interval") if x in (6, 12) else None
        ax2.plot([x, x], ci, color=BLUE, linewidth=2 if x == 6 else 1, label=label)
        ax2.plot([x], [est], "o", color=BLUE, markersize=4)
    ax2.axhline(0, color="black", linewidth=0.6)
    ax2.set_xticks(xs)
    ax2.set_xlabel("Level")
    ax2.set_ylabel(r"$\theta_1$ (permuted $-$ generated Brier)")
    ax2.legend(frameon=False)
    fig.tight_layout()
    return fig


DEPTHS = ("1", "2", "3", ">=4", "stuck")


def e3_supporting(results: dict):
    """Training-size curves (whole-layer primary, per-cell secondary) and the level-6 depth breakdown."""
    ts = results["tables"]["training_size"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH, 2.4))
    for curve, colour, label in (("whole_layer", BLUE, "Whole-layer (primary)"), ("per_cell", ORANGE, "Per-cell")):
        pts = sorted((v["n_puzzles"], v["brier"]) for k, v in ts[curve].items() if isinstance(v, dict))
        ax1.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=colour, label=label)
    ax1.set_xscale("log")
    ax1.minorticks_off()
    ns = sorted(v["n_puzzles"] for v in ts["whole_layer"].values() if isinstance(v, dict))
    ax1.set_xticks(ns, [str(n) for n in ns])
    ax1.set_xlabel("Training puzzles")
    ax1.set_ylabel("Brier loss (TEST)")
    ax1.legend(frameon=False)
    depth = results["tables"]["depth"]
    x = np.arange(len(DEPTHS))
    for j, (row, colour, label) in enumerate((("wl_L06.generated", BLUE, "Whole-layer, level 6"),
                                               ("pc_L06.linear", ORANGE, "Per-cell, level 6"))):
        vals = []
        for d in DEPTHS:
            value = (depth.get(row, {}).get("brier", {}).get(d) or {}).get("brier")
            if value is None:
                raise KeyError(f"tables.depth[{row}].brier.{d}.brier")
            vals.append(value)
        ax2.bar(x + (j - 0.5) * 0.35, vals, width=0.35, color=colour, label=label)
    ax2.set_xticks(x, [r"$\geq$4" if d == ">=4" else d for d in DEPTHS])
    ax2.set_xlabel("Inference depth (descriptive)")
    ax2.set_ylabel("Brier loss (TEST)")
    ax2.set_ylim(0, 0.3)
    ax2.legend(frameon=False, loc="upper left", ncol=2)
    fig.tight_layout()
    return fig


def e1_levels(results: dict):
    """Per level: agreement of generated with teacher codes, and cell accuracy of the decoded partial state."""
    per_level = req(results, "tables.e1.per_level")
    levels = [row["level"] for row in per_level]
    if levels != list(range(1, 13)):
        raise KeyError(f"tables.e1.per_level must hold levels 1..12 in order, got {levels}")
    fig, ax = plt.subplots(figsize=(WIDTH, 2.4))
    ax.plot(levels, [100 * row["code_agreement"] for row in per_level], "o-", color=BLUE,
            label="Generated codes equal to teacher codes")
    ax.plot(levels, [100 * row["cell_acc_all"] for row in per_level], "s--", color=ORANGE,
            label="Cell accuracy of the decoded cumulative state")
    ax.set_xticks(levels, [str(lv) for lv in levels])
    ax.set_xlabel("Level")
    ax.set_ylabel("% (descriptive)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    return fig


def damage_curves(results: dict):
    """Registered sensitivity curves on the damage axis (plan §7.3): per level, the stored frequency-policy nodes
    (mean initial damage, mean solve change of D against A), with the frozen 6-vs-11 range shaded; descriptive."""
    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    auc = results["auc"]
    series = (("Level 2", auc["2-11"]["nodes"]["a"], GREEN, "^"), ("Level 6", auc["6-11"]["nodes"]["a"], BLUE, "o"),
              ("Level 11", auc["6-11"]["nodes"]["b"], ORANGE, "s"))
    lo, hi = auc["6-11"]["range"]
    span = ax.axvspan(lo, hi, color=GREY, alpha=0.25, label="Range frozen on CAL (levels 6 vs. 11)")
    span.set_gid("frozen-range")
    for label, pts, colour, marker in series:
        ax.plot([p[0] for p in pts], [100 * p[1] for p in pts], marker=marker, color=colour, label=label)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("Mean initial damage (total variation distance, C vs. A)")
    ax.set_ylabel("Mean solve change of D (pp)")
    ax.legend(frameon=False, loc="lower left")
    fig.tight_layout()
    return fig

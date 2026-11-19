import builtins
import json
from pathlib import Path

import pytest

from ncm_sudoku import wp4figures as f

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def results():
    return json.loads((ROOT / "experiments/wp2/test/results.json").read_text(encoding="utf-8"))


@pytest.fixture
def no_file_reads(monkeypatch):
    real_open = builtins.open

    def guarded(file, mode="r", *a, **k):
        if "r" in mode and str(file).endswith(".json"):
            raise AssertionError(f"figure functions must not read files: {file}")
        return real_open(file, mode, *a, **k)

    monkeypatch.setattr(builtins, "open", guarded)


@pytest.mark.parametrize("name,axes", [("dose_curves", 3), ("contrasts_forest", 1), ("propagation", 2),
                                       ("e3_readability", 2), ("e3_supporting", 2), ("e1_levels", 1)])
def test_figure_axes(results, no_file_reads, name, axes):
    fig = getattr(f, name)(results)
    assert len([ax for ax in fig.axes if ax.get_label() != "<colorbar>"]) == axes
    f.plt.close(fig)


def test_dose_curves_four_lines_per_level_panel(results):
    fig = f.dose_curves(results)
    for ax in fig.axes:
        assert len(ax.get_lines()) == 4
    f.plt.close(fig)


def test_contrasts_forest_rows(results):
    fig = f.contrasts_forest(results)
    labels = [t.get_text() for t in fig.axes[0].get_yticklabels()]
    assert len(labels) == 8
    f.plt.close(fig)


def test_save_pdf_is_byte_identical(results, tmp_path):
    for i in (1, 2):
        fig = f.contrasts_forest(results)
        f.save_pdf(fig, tmp_path / f"a{i}.pdf")
    assert (tmp_path / "a1.pdf").read_bytes() == (tmp_path / "a2.pdf").read_bytes()


def test_forest_missing_interval_names_the_path(results):
    import copy

    broken = copy.deepcopy(results)
    broken["secondary"]["uniform"]["theta2"]["ci95"] = None
    with pytest.raises(KeyError, match="secondary.uniform.theta2.ci95"):
        f.contrasts_forest(broken)


def test_dose_curves_missing_level_raises(results):
    import copy

    broken = copy.deepcopy(results)
    broken["tables"]["e2"]["configurations"] = [c for c in broken["tables"]["e2"]["configurations"] if c["level"] != 6]
    with pytest.raises(KeyError, match="level 6"):
        f.dose_curves(broken)


def test_depth_missing_stratum_names_the_path(results):
    import copy

    broken = copy.deepcopy(results)
    del broken["tables"]["depth"]["wl_L06.generated"]["brier"]["2"]
    with pytest.raises(KeyError, match="depth"):
        f.e3_supporting(broken)


def test_e1_levels_two_series_over_twelve_levels(results):
    fig = f.e1_levels(results)
    lines = fig.axes[0].get_lines()
    assert len(lines) == 2 and all(len(line.get_xdata()) == 12 for line in lines)
    f.plt.close(fig)


def test_propagation_labels_relative_distance(results):
    fig = f.propagation(results)
    assert "Relative" in fig.axes[1].get_ylabel()
    f.plt.close(fig)


def test_readability_names_unprojected_raw_input(results):
    fig = f.e3_readability(results)
    labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert any("unprojected" in label for label in labels)
    f.plt.close(fig)


FIGURES = ["dose_curves", "contrasts_forest", "propagation", "e3_readability", "e3_supporting", "e1_levels",
           "damage_curves"]


def _texts(fig):
    return [t for t in fig.findobj(f.matplotlib.text.Text) if t.get_text()]


@pytest.mark.parametrize("name", FIGURES)
def test_figure_text_is_ascii_mathtext_and_readable(results, tmp_path, name):
    import warnings

    fig = getattr(f, name)(results)
    for t in _texts(fig):
        # U+2212 is matplotlib's own tick-label minus inside mathtext
        assert t.get_text().replace("−", "-").isascii(), f"use mathtext, not unicode: {t.get_text()!r}"
        assert t.get_fontsize() >= 6, f"text below 6 pt at final size: {t.get_text()!r}"
        # cmr10 has no < or > glyphs outside math (they render as inverted punctuation)
        plain = "".join(t.get_text().split("$")[::2])
        assert "<" not in plain and ">" not in plain, f"use mathtext for comparisons: {t.get_text()!r}"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        f.save_pdf(fig, tmp_path / f"{name}.pdf")


def test_figure_font_matches_computer_modern():
    assert f.plt.rcParams["mathtext.fontset"] == "cm"
    assert f.plt.rcParams["font.family"] == ["serif"]
    assert f.plt.rcParams["font.serif"][0] == "cmr10"


def test_figure_width_fits_tmlr_text_width():
    # tmlr.sty sets a 6.5 in text width; figures are drawn at WIDTH and must not be scaled down
    assert f.WIDTH <= 6.5
    assert r"\usepackage{tmlr}" in (ROOT / "paper/main_anon.tex").read_text(encoding="utf-8")
    assert r"\usepackage[preprint]{tmlr}" in (ROOT / "paper/main.tex").read_text(encoding="utf-8")


def test_preamble_has_no_layout_overrides():
    preamble = (ROOT / "paper/preamble.tex").read_text(encoding="utf-8")
    for forbidden in ("geometry", "[numbers]{natbib}", "fontenc"):
        assert forbidden not in preamble, forbidden


def test_forest_thresholds_drawn_only_on_their_rows(results):
    fig = f.contrasts_forest(results)
    n = len(f.FOREST_ROWS)
    row_y = {path: n - 1 - i for i, (_, path, _) in enumerate(f.FOREST_ROWS)}
    expected = {
        "H2 practical threshold": {row_y["primary.H2"]},
        "H3 practical threshold": {row_y["primary.H3"]},
        "equivalence": {row_y["secondary.theta2_prime"], row_y["secondary.uniform.theta2_prime"]},
    }
    seen = {k: set() for k in expected}
    for line in fig.axes[0].get_lines():
        gid = line.get_gid() or ""
        for key in expected:
            if key in gid:
                ys = line.get_ydata()
                assert max(ys) - min(ys) < 1, f"{gid} spans more than one row"
                seen[key].add(round(sum(ys) / len(ys)))
    assert seen == expected
    f.plt.close(fig)


def test_damage_curves_plot_the_stored_nodes_per_level(results):
    fig = f.damage_curves(results)
    ax = fig.axes[0]
    lines = {line.get_label(): line for line in ax.get_lines()}
    nodes = {"Level 2": results["auc"]["2-11"]["nodes"]["a"], "Level 6": results["auc"]["6-11"]["nodes"]["a"],
             "Level 11": results["auc"]["6-11"]["nodes"]["b"]}
    assert set(nodes) <= set(lines)
    for label, pts in nodes.items():
        assert list(lines[label].get_xdata()) == [p[0] for p in pts]
        assert list(lines[label].get_ydata()) == pytest.approx([100 * p[1] for p in pts])
    assert ax.get_xscale() == "log"
    f.plt.close(fig)


def test_damage_curves_shade_the_frozen_range(results):
    fig = f.damage_curves(results)
    lo, hi = results["auc"]["6-11"]["range"]
    spans = [p for p in fig.axes[0].patches if p.get_gid() == "frozen-range"]
    assert len(spans) == 1
    x0, width = spans[0].get_x(), spans[0].get_width()
    assert x0 == pytest.approx(lo) and x0 + width == pytest.approx(hi)
    f.plt.close(fig)


@pytest.mark.parametrize("name", FIGURES)
def test_figure_labels_use_reader_terms(results, name):
    fig = getattr(f, name)(results)
    for t in _texts(fig):
        assert "score set" not in t.get_text(), t.get_text()
    f.plt.close(fig)

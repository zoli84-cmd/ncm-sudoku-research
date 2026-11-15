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


FIGURES = ["dose_curves", "contrasts_forest", "propagation", "e3_readability", "e3_supporting", "e1_levels"]


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


def test_figure_width_equals_text_width():
    preamble = (ROOT / "paper/preamble.tex").read_text(encoding="utf-8")
    assert r"\usepackage[letterpaper,margin=1.1in]{geometry}" in preamble
    assert f.WIDTH == pytest.approx(8.5 - 2 * 1.1)

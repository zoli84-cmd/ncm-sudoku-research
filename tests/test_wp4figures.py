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
                                       ("e3_readability", 2), ("e3_supporting", 2)])
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

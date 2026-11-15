import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "numbers.tex", "numbers.json",
    "tables/primary.tex", "tables/e3_matrix.tex", "tables/e2_dose.tex", "tables/e1.tex",
    "tables/equivariance.tex", "tables/deviations.tex",
    "figures/dose_curves.pdf", "figures/contrasts_forest.pdf", "figures/propagation.pdf",
    "figures/e3_readability.pdf", "figures/e3_supporting.pdf",
}


def _load():
    spec = importlib.util.spec_from_file_location("wp4_figures", ROOT / "scripts" / "wp4_figures.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def rel(paths, base):
    return {p.relative_to(base).as_posix() for p in paths}


def test_generate_writes_every_file_deterministically(tmp_path):
    a = mod.generate(ROOT, tmp_path / "a")
    b = mod.generate(ROOT, tmp_path / "b")
    assert rel(a, tmp_path / "a") == EXPECTED
    for p in a:
        q = tmp_path / "b" / p.relative_to(tmp_path / "a")
        assert p.read_bytes() == q.read_bytes(), p.name
    assert a == sorted(a)


def _copy_inputs(dst: Path):
    for rel_path in ("experiments/wp2/test/results.json", "experiments/g0/reproduction.json",
                     "experiments/lock/test_set.json", "experiments/wp1/gate.json",
                     "experiments/e3prep/extract.json", "DECISIONS.md"):
        (dst / rel_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel_path, dst / rel_path)


def test_check_mode_detects_stale_and_missing_files(tmp_path, monkeypatch, capsys):
    _copy_inputs(tmp_path)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    mod.generate(tmp_path, tmp_path / "paper" / "generated")
    assert mod.main(["--check"]) == 0
    target = tmp_path / "paper" / "generated" / "tables" / "primary.tex"
    target.write_text(target.read_text(encoding="utf-8") + "%", encoding="utf-8")
    (tmp_path / "paper" / "generated" / "numbers.json").unlink()
    assert mod.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "tables/primary.tex" in out and "numbers.json" in out


def test_committed_generated_files_are_current():
    if not (ROOT / "paper" / "generated" / "numbers.json").exists():
        pytest.skip("generated files not committed yet")
    assert mod.main(["--check"]) == 0


def test_script_does_not_import_torch():
    code = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('m', r'{ROOT / 'scripts' / 'wp4_figures.py'}')\n"
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
        "print('torch' in sys.modules)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "False"

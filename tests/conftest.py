from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CKPT_DIR = ROOT / "checkpoints" / "sudoku" / "hard"
DATA_DIR = ROOT / "data" / "released" / "sudoku" / "hard"

needs_model = pytest.mark.skipif(
    not (CKPT_DIR / "generator.pt").exists() or not DATA_DIR.exists(),
    reason="checkpoints or released data not downloaded",
)


@pytest.fixture(scope="session")
def model():
    from ncm_sudoku.model import load_model

    return load_model(CKPT_DIR)


@pytest.fixture(scope="session")
def released():
    from ncm_sudoku.released import load_released

    return load_released(DATA_DIR)

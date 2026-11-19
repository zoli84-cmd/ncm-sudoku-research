import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# JmlrOrg/tmlr-style-file at commit 7bf90efe3a0debbba703c05c43f3ff7e4d4a2992; TMLR may reject modified style files
PINNED = {
    "tmlr.sty": "816214ff5919aa457b6b443bee52b15d9561421417b7f8a50cc84651519f0002",
    "tmlr.bst": "306fd454cf40771bee01293eeb98d2c1cd5f4e11ed0cd7296b335f354fc45206",
    "fancyhdr.sty": "3d2922548e0e5f1a6c5676eda6ebb6dc20d7d305b4d8c2be5f1c833fb1084e6d",
}


@pytest.mark.parametrize("name,digest", sorted(PINNED.items()))
def test_vendored_style_files_are_unmodified(name, digest):
    assert hashlib.sha256((ROOT / "paper" / name).read_bytes()).hexdigest() == digest

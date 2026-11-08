"""Download the released NCM Sudoku evaluation set and record its provenance.

Usage: uv run python scripts/fetch_released_data.py --difficulty hard

Writes the pickles to data/released/<difficulty>/ (git-ignored) and the
resolved dataset revision, sizes and SHA-256 hashes to
experiments/provenance/released_data.json (committed). The pickles are
untrusted: load them only with ncm_sudoku.released.safe_load_pickle.
"""

import argparse
import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

REPO_ID = "hazyresearch/ncm-datasets"
FILES = ("puzzles.pickle", "solutions.pickle")
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--difficulty", default="hard", choices=["easy", "medium", "hard"])
    args = ap.parse_args()

    revision = HfApi().dataset_info(REPO_ID).sha
    out_dir = ROOT / "data" / "released"
    record = {"repo_id": REPO_ID, "repo_type": "dataset", "revision": revision, "files": {}}
    for name in FILES:
        remote = f"sudoku/{args.difficulty}/{name}"
        local = Path(
            hf_hub_download(REPO_ID, remote, repo_type="dataset", revision=revision, local_dir=out_dir)
        )
        record["files"][remote] = {"bytes": local.stat().st_size, "sha256": sha256(local)}

    prov_path = ROOT / "experiments" / "provenance" / "released_data.json"
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(prov_path.read_text()) if prov_path.exists() else {}
    existing[args.difficulty] = record
    prov_path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", newline="\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()

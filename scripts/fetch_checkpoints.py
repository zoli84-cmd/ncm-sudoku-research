"""Download the NCM Sudoku-hard checkpoints and record their provenance.

Usage: uv run python scripts/fetch_checkpoints.py

Files go to checkpoints/sudoku/hard/ (git-ignored); revision, sizes, SHA-256,
licenses and the upstream submodule commit go to
experiments/provenance/checkpoints.json (committed). Load the checkpoints only
through ncm_sudoku.model.load_model (weights_only=True).
"""

import hashlib
import json
import subprocess
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

REPO_ID = "hazyresearch/ncm-checkpoints"
FILES = ("generator.pt", "tokenizer.pt", "config.yaml")
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    info = HfApi().model_info(REPO_ID)
    record = {
        "repo_id": REPO_ID,
        "revision": info.sha,
        "checkpoints_license": (info.card_data or {}).get("license", "unknown").upper(),
        "code_license": "MIT" if "MIT License" in (ROOT / "third_party/ncm/LICENSE").read_text() else "unknown",
        "upstream_commit": subprocess.check_output(
            ["git", "-C", str(ROOT / "third_party" / "ncm"), "rev-parse", "HEAD"], text=True
        ).strip(),
        "files": {},
    }
    for name in FILES:
        remote = f"sudoku/hard/{name}"
        local = Path(hf_hub_download(REPO_ID, remote, revision=info.sha, local_dir=ROOT / "checkpoints"))
        record["files"][remote] = {"bytes": local.stat().st_size, "sha256": sha256(local)}
    out = ROOT / "experiments" / "provenance" / "checkpoints.json"
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", newline="\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()

"""E5 NCM activations of the counterfactual PROBE pairs (step 4 input; non-confirmatory).

Usage: uv run --locked python scripts/e5_extract.py [--batch 50] [--force]

For PROBE-TRAIN and PROBE-VAL (runs/e5/pairs/<subset>/, checked against
experiments/e5/pairs.json) and both pair members a and b, runs
`ncm_sudoku.e5extract.extract_batch` and writes runs/e5/acts/<subset>/<member>/
(prefix_cells.npy (n, 9, 81, 512) fp16, prefix_bos.npy (n, 9, 512) fp16,
level7_queries.npy (n, 9, 18, 512) fp16, z6.npy and z6_teacher.npy (n, 81, 256) fp32,
codes.npy int8, solved.npy bool). Each (subset, member) unit is finished by a
done.json with the SHA-256 of its files; a rerun skips finished units, so an
interrupted run continues where it stopped. --force deletes every unit first.
Record: experiments/e5/extract.json.
"""

import argparse
import gc
import hashlib
import json
import shutil
import time

import numpy as np

from ncm_sudoku.e5extract import extract_batch
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.model import ROOT, load_model
from ncm_sudoku.subsets import sha256_array

PAIRS = ROOT / "runs" / "e5" / "pairs"
ACTS = ROOT / "runs" / "e5" / "acts"
OUT = ROOT / "experiments" / "e5" / "extract.json"
SUBSETS = ("probe_train", "probe_val")


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_unit(m, puzzles, solutions, d, batch) -> dict:
    d.mkdir(parents=True, exist_ok=True)
    n = len(puzzles)
    maps = {}
    t0 = time.perf_counter()
    for start in range(0, n, batch):
        out = extract_batch(m, puzzles[start : start + batch], solutions[start : start + batch])
        if not maps:
            maps = {k: np.lib.format.open_memmap(d / f"{k}.npy", mode="w+", dtype=v.dtype, shape=(n, *v.shape[1:]))
                    for k, v in out.items()}
        for k, v in out.items():
            maps[k][start : start + len(v)] = v
        print(f"{d.relative_to(ACTS)} {min(start + batch, n)}/{n} ({time.perf_counter() - t0:.0f} s)", flush=True)
    for v in maps.values():
        v.flush()
    names = list(maps)
    maps.clear()
    gc.collect()  # release every write mapping before hashing (Windows, D82)
    files = {k: sha256(d / f"{k}.npy") for k in names}
    solved = np.load(d / "solved.npy")
    done = {"n": n, "seconds": round(time.perf_counter() - t0, 1), "files": files, "solved": int(solved.sum())}
    (d / "done.json").write_text(json.dumps(done, indent=2) + "\n", encoding="utf-8", newline="\n")
    return done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=50)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.force and ACTS.exists():
        shutil.rmtree(ACTS)
    pairs_rec = json.loads((ROOT / "experiments" / "e5" / "pairs.json").read_text())
    m = load_model(ROOT / "checkpoints" / "sudoku" / "hard")
    record = {"note": "E5 NCM activations of the PROBE pairs (non-confirmatory)", "date": time.strftime("%Y-%m-%d"),
              "pass": "level-7 generation pass (pass index 6, reads Z<=6)", "layers": "0 = block-1 input, k = block-k output",
              "environment": environment_record(), "code_state": code_state(), "units": {}}
    for subset in SUBSETS:
        src = PAIRS / subset
        sha = pairs_rec["subsets"][subset]["sha256"]
        arrays = {k: np.load(src / f"{k}.npy") for k in ("a", "b", "solutions")}
        for k, v in arrays.items():
            if sha256_array(v) != sha[k]:
                raise SystemExit(f"{src / k}.npy does not match experiments/e5/pairs.json")
        for member in ("a", "b"):
            d = ACTS / subset / member
            if (d / "done.json").exists():
                done = json.loads((d / "done.json").read_text())
            else:
                if d.exists():
                    shutil.rmtree(d)
                done = run_unit(m, arrays[member], arrays["solutions"], d, args.batch)
            record["units"][f"{subset}/{member}"] = done
            OUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: {"n": v["n"], "solved": v["solved"], "seconds": v["seconds"]} for k, v in record["units"].items()}))


if __name__ == "__main__":
    main()

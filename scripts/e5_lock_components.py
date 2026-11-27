"""E5 pre-lock tasks 1-2 (protocol e5_protocol_v1.md §9.1-9.2): freeze the primary components.

Usage: uv run --locked python scripts/e5_lock_components.py [--force]

1. Refits the Z<=6 shared head (`ncm_sudoku.e5causal.refit_head`, rep `z6`) and requires the
   §9.1 reproduction check (`compare_predictions`: shape, NaN pattern, finiteness, exact
   equality with runs/e5/pilot/z6__shared__none.npy); stops without saving if it fails.
2. Loads the saved P2, P4 and P8 heads and verifies their SHA-256 against
   experiments/e5/causal/heads.json; computes W (seed-averaged P2 state rows), Q
   (`orthonormal_rows`), H (`high_variance_basis` on the PROBE-TRAIN both-empty layer-2
   differences, as in scripts/e5_causal.py), R_0..R_19 (`random_basis(1000 + j)`) and
   Pi (`DERANGEMENT`).

Saves runs/e5/lock/z6.pt (torch.save of the seed state dicts) and runs/e5/lock/{W,Q,H,R,Pi}.npy,
re-loads each file and checks it equals the computed object, checks that saving is
byte-deterministic, and writes experiments/e5/lock/components.json (file SHA-256,
shapes, dtypes, the reproduction record). Refuses to overwrite unless --force.
"""

import hashlib
import io
import json
import sys
import time

import numpy as np
import torch

from ncm_sudoku.e5causal import (
    DERANGEMENT,
    high_variance_basis,
    orthonormal_rows,
    random_basis,
    refit_head,
    state_weights,
)
from ncm_sudoku.e5pilot import load_subset
from ncm_sudoku.g0 import code_state, environment_record
from ncm_sudoku.model import ROOT

OUT = ROOT / "experiments" / "e5" / "lock" / "components.json"
DIR = ROOT / "runs" / "e5" / "lock"
HEADS = ROOT / "experiments" / "e5" / "causal" / "heads.json"
DRAWS = 20


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def npy_bytes(a: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, a, allow_pickle=False)
    return buf.getvalue()


def torch_bytes(obj) -> bytes:
    buf = io.BytesIO()
    torch.save(obj, buf)
    return buf.getvalue()


def main() -> None:
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT.relative_to(ROOT)} exists; use --force")
    t0 = time.perf_counter()
    torch.set_num_threads(4)

    z6 = refit_head(ROOT, "z6")
    print("z6 reproduction", json.dumps(z6["reproduction"]), flush=True)
    if not z6["reproduction"]["passed"]:
        sys.exit("Z<=6 head does not reproduce the saved pilot predictions; nothing saved")

    heads_rec = json.loads(HEADS.read_text())["heads"]
    heads = {}
    for rep in ("P2", "P4", "P8"):
        path = ROOT / heads_rec[rep]["file"]
        if sha(path.read_bytes()) != heads_rec[rep]["sha256"]:
            sys.exit(f"{rep} head hash differs from {HEADS.relative_to(ROOT)}")
        heads[rep] = torch.load(path, weights_only=True)

    W = state_weights(heads["P2"])
    Q, s = orthonormal_rows(W)
    tr = load_subset(ROOT, "probe_train")
    nt = tr["n_pairs"]
    ta = np.load(tr["acts"] / "a" / "prefix_cells.npy", mmap_mode="r")[:, 2].astype(np.float64)
    tb = np.load(tr["acts"] / "b" / "prefix_cells.npy", mmap_mode="r")[:, 2].astype(np.float64)
    be = tr["empty"][:nt] & tr["empty"][nt:]
    H = high_variance_basis((tb - ta)[be], Q)
    R = np.stack([random_basis(1000 + j) for j in range(DRAWS)])
    arrays = {"W": W, "Q": Q, "H": H, "R": R, "Pi": DERANGEMENT.astype(np.int64)}

    DIR.mkdir(parents=True, exist_ok=True)
    files = {}
    zb = torch_bytes(z6["state_dicts"])
    deterministic = zb == torch_bytes(z6["state_dicts"])
    (DIR / "z6.pt").write_bytes(zb)
    back = torch.load(DIR / "z6.pt", weights_only=True)
    same = all(torch.equal(a[k], b[k]) for a, b in zip(back, z6["state_dicts"]) for k in a)
    files["z6_head"] = {"file": "runs/e5/lock/z6.pt", "sha256": sha(zb), "format": "torch.save list of 3 seed state dicts",
                        "reload_equal": same}
    for name, a in arrays.items():
        b = npy_bytes(a)
        deterministic &= b == npy_bytes(a)
        (DIR / f"{name}.npy").write_bytes(b)
        back = np.load(DIR / f"{name}.npy", allow_pickle=False)
        files[name] = {"file": f"runs/e5/lock/{name}.npy", "sha256": sha(b), "shape": list(a.shape),
                       "dtype": str(a.dtype), "reload_equal": bool(np.array_equal(back, a) and back.dtype == a.dtype)}
    if not deterministic or not all(f["reload_equal"] for f in files.values()):
        sys.exit("saving is not byte-deterministic or a reload differs")

    checks = {
        "Q_orthonormal_max_abs": float(np.abs(Q.T @ Q - np.eye(9)).max()),
        "H_orthonormal_max_abs": float(np.abs(H.T @ H - np.eye(9)).max()),
        "QtH_max_abs": float(np.abs(Q.T @ H).max()),
        "R_orthonormal_max_abs": float(max(np.abs(r.T @ r - np.eye(9)).max() for r in R)),
        "P2_state_row_singular_values": [float(x) for x in s],
        "n_probe_train_both_empty_rows": int(be.sum()),
    }
    rec = {"note": "E5 pre-lock components (protocol §9.1-9.2); PROBE data only, no TEST data",
           "date": time.strftime("%Y-%m-%d"), "threads": torch.get_num_threads(),
           "z6_head": {"config": z6["config"], "reproduction": z6["reproduction"]},
           "verified_heads": {k: {"file": heads_rec[k]["file"], "sha256": heads_rec[k]["sha256"]} for k in heads},
           "files": files, "byte_deterministic_save": deterministic, "checks": checks,
           "seconds": round(time.perf_counter() - t0, 1),
           "environment": environment_record(), "code_state": code_state()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v["sha256"] for k, v in files.items()}, indent=1))


if __name__ == "__main__":
    main()

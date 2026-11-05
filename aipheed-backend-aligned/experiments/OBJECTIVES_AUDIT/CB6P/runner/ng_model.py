"""C-B6D-E-X-NG (../PREREGISTRATION_NG.md, hash checked): C-B6D-E-X with the teammate's FI6-N news (z_G) added to the
regional hunger part. fi_provincial.run() unchanged (cut-off 11.0); outputs -> out/ng/.

    python ng_model.py fit      # regional walk-forward -> out/ng/cb6e_ng_fits.csv
    python ng_model.py prov     # provincial Eq. 3 + acceptance -> out/ng/
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
import shutil
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN))
sys.path.insert(0, str(RUN.parents[1] / "runner"))
import cb6_model as CB  # noqa: E402

HERE = RUN.parent
AUD = HERE.parent
PLAN = HERE / "PREREGISTRATION_NG.md"
OUT = HERE / "out" / "ng"
N, V, H = CB.N, CB.V, CB.H
COLS = CB.PC.CB + CB.ST + ["E1", "E2", "z_G"]
NAME = "C-B6E-NG"


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "NG pre-registration changed"
    return h


def _init():
    CB._init()
    N._G["T"] = N._G["T"].merge(pd.read_csv(AUD / "out" / "cb7_features.csv")[["t", "z_G"]], on="t", how="left")


def _origin(t):
    return CB._origin((t, NAME, COLS))


def fit():
    pre = check()
    OUT.mkdir(parents=True, exist_ok=True)
    origins = [t for t in V.ORIGINS if t >= H.qi("2012-Q3")]
    with Pool(8, initializer=_init) as pool:
        F = pd.concat(pool.map(_origin, origins), ignore_index=True)
    F.to_csv(OUT / "cb6e_ng_fits.csv", index=False)
    print({"prereg_sha256": pre, "rows": len(F), "origins": len(origins)})


def prov():
    pre = check()
    import fi_provincial as FP
    src = HERE / "out"
    for f in ("cb6p_labels.csv", "fi_regional_fits.csv", "cb6d_fits.csv", "cb6p2_fits.csv"):
        shutil.copyfile(src / f, OUT / f)
    A = pd.read_csv(OUT / "cb6e_ng_fits.csv")
    orig = FP.D.regional
    FP.D.regional = lambda n: ({(int(r.t), int(r.lead)): r for r in A.itertuples()} if n == "C-B6E" else orig(n))
    FP.OUT = OUT
    assert FP.THR == 11.0
    FP.run()
    res = json.loads((OUT / "fi_provincial_results.json").read_text(encoding="utf-8"))
    base = json.loads((src / "fi_provincial_results.json").read_text(encoding="utf-8"))
    out, ok = {"prereg_sha256": pre, "leads": {}}, True
    for k in ("1", "2"):
        a, b = res["B_ext"][k]["C-B6D-E-X"], base["B_ext"][k]["C-B6D-E-X"]
        out["leads"][k] = {m: {"NG": a[m], "X": b[m]} for m in ("accuracy", "balanced", "auc", "brier")}
        ok &= a["brier"] < b["brier"] and a["accuracy"] >= b["accuracy"]
    out["acceptance_pass"] = bool(ok)
    (OUT / "ng_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"fit": fit, "prov": prov}[sys.argv[1]]()

"""C-B6D-E-X-PM-AD (../PREREGISTRATION_AD.md, hash checked, owner directive): every risk driver in every forecast.

The regional hunger part is the C-B6P4 hybrid (logistic driver base + LightGBM) on C-B6E's inputs; the provincial
Eq. 3 step is fi_provincial.run() unchanged with the paper median cut-off. Outputs -> out/ad/ (originals untouched).

    python ad_model.py fit       # regional walk-forward -> out/ad/cb6e_ad_fits.csv
    python ad_model.py prov      # provincial Eq. 3 -> out/ad/fi_provincial_*.{csv,json}
    python ad_model.py check     # driver coverage and acceptance -> out/ad/ad_results.json
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

import numpy as np
import pandas as pd

RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN))
sys.path.insert(0, str(RUN.parents[1] / "runner"))
import cb6_model as CB  # noqa: E402
import cb6p4_model as P4  # noqa: E402

HERE = RUN.parent
PLAN = HERE / "PREREGISTRATION_AD.md"
OUT = HERE / "out" / "ad"
N, V, H = CB.N, CB.V, CB.H
COLS = CB.PC.CB + CB.ST + ["E1", "E2"]          # C-B6E inputs
GROUPS = P4.DRV_GROUPS
THR = 14.325
NAME = "C-B6E-AD"


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "AD pre-registration changed"
    return h


def select(tr):
    folds = H.inner_folds(tr)
    if not folds:
        return H.GRID[0], P4.CS[0]
    ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
    best = None
    for C in P4.CS:
        for c in H.GRID:
            p = np.clip(np.concatenate([P4.Hybrid4(c, COLS, C).fit(f).predict(h) for f, h in folds]), 1e-6, 1 - 1e-6)
            key = (round(float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p))), 9), C, c["id"])
            if best is None or key < best[0]:
                best = (key, c, C)
    return best[1], best[2]


def _origin(t):
    """cb6_model._origin with the hybrid model."""
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(N.TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"], te["cfg"], te["C"] = np.nan, False, None, np.nan
    sh = None
    if H.eligible(trb):
        cfg, C = select(tr)
        m = P4.Hybrid4(cfg, COLS, C).fit(tr)
        te["p"], te["cfg"], te["C"] = m.predict(te), cfg["id"], C
        if m.m is not None:
            sh = m.shap(te)
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    out = te[["t", "lead", "q", "p", "fallback", "cfg", "C"]].assign(name=NAME).reset_index(drop=True)
    sh = sh.reset_index(drop=True) if sh is not None else pd.DataFrame(0.0, index=out.index, columns=COLS)
    return pd.concat([out, sh.add_prefix("shap_")], axis=1)


def fit():
    pre = check()
    OUT.mkdir(parents=True, exist_ok=True)
    origins = [t for t in V.ORIGINS if t >= H.qi("2012-Q3")]
    with Pool(8, initializer=CB._init) as pool:
        F = pd.concat(pool.map(_origin, origins), ignore_index=True)
    F.to_csv(OUT / "cb6e_ad_fits.csv", index=False)
    print({"prereg_sha256": pre, "rows": len(F), "origins": len(origins),
           "C": F.groupby("t")["C"].first().value_counts().to_dict()})


def prov():
    check()
    import fi_provincial as FP
    src = HERE / "out"
    for f in ("cb6p_labels.csv", "fi_regional_fits.csv", "cb6d_fits.csv", "cb6p2_fits.csv"):
        shutil.copyfile(src / f, OUT / f)
    A = pd.read_csv(OUT / "cb6e_ad_fits.csv")
    orig = FP.D.regional
    FP.D.regional = lambda n: ({(int(r.t), int(r.lead)): r for r in A.itertuples()} if n == "C-B6E" else orig(n))
    FP.THR, FP.OUT = THR, OUT
    FP.run()


def accept():
    pre = check()
    A = pd.read_csv(OUT / "cb6e_ad_fits.csv")
    res = json.loads((OUT / "fi_provincial_results.json").read_text(encoding="utf-8"))
    pm = json.loads((HERE / "out" / "pm" / "fi_provincial_results.json").read_text(encoding="utf-8"))
    s = A[A["lead"].isin([1, 2]) & (A["q"] >= H.qi("2013-Q1"))]
    g = pd.DataFrame({n: sum(s[f"shap_{c}"].fillna(0) for c in cs) for n, cs in GROUPS.items()})
    cov = {n: float((g[n].abs() > 1e-12).mean()) for n in GROUPS}
    out = {"prereg_sha256": pre, "driver_nonzero_share": cov, "leads": {}}
    ok = all(v >= .99 for v in cov.values())
    for k in ("1", "2"):
        a, b = res["B_ext"][k]["C-B6D-E-X"], pm["B_ext"][k]["C-B6D-E-X"]
        out["leads"][k] = {"AD": {x: a[x] for x in ("accuracy", "balanced", "auc", "brier")},
                           "PM": {x: b[x] for x in ("accuracy", "balanced", "auc", "brier")}}
        ok &= a["accuracy"] >= .75 and a["brier"] <= b["brier"] + .01
    out["algorithm3"] = res["algorithm3_ext"]["C-B6D-E-X"]
    out["acceptance_pass"] = bool(ok)
    (OUT / "ad_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"fit": fit, "prov": prov, "check": accept}[sys.argv[1]]()

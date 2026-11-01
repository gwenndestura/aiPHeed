"""Y11 development (EXPERIMENT_PLAN_PHASE2_ADDENDUM_C.md): parsimonious continuous world-price model WAR (top-3 world
features chosen inside each fold) and its no-world ablation WAR0, vs PERS-PROB, on the Y8 rows and gate.
Writes out/y11_dev.json, out/y11_dev_rows.csv.

    python -B run_dev.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402

import p2lib as P  # noqa: E402

R = P.R
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
_s = importlib.util.spec_from_file_location("y10", P.RES / "y10_world_prices" / "run_dev.py")
Y10 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(Y10)
Y8 = Y10.Y8
WF = [f"{c}_d{k}" for c in ("rice", "crude", "urea", "maize", "wheat", "palm") for k in (6, 12)]


def plan_ok():
    want = (P.RES / "common" / "PLAN2C_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((P.RES / "EXPERIMENT_PLAN_PHASE2_ADDENDUM_C.md").read_bytes()).hexdigest() == want


def ols(tr: pd.DataFrame, x0: dict, ycol: str, cols: list[str]) -> tuple[float, float]:
    X = np.column_stack([np.ones(len(tr))] + [tr[c].to_numpy(float) for c in cols])
    y = tr[ycol].to_numpy(float)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    sig = math.sqrt(float(np.mean((y - X @ b) ** 2)))
    mu = float(np.r_[1.0, [x0[c] for c in cols]] @ b)
    return mu, sig


def war(tr: pd.DataFrame, x0: dict, world: bool) -> tuple[float, list]:
    tr = tr.dropna(subset=WF if world else [])
    if len(tr) < 20:
        return np.nan, []
    top = []
    if world:
        avail = [c for c in WF if not math.isnan(x0[c])]
        cr = {c: abs(tr[c].corr(tr["F_tgt"] - tr["F3"])) for c in avail}
        top = sorted(cr, key=cr.get, reverse=True)[:3]
    mf, sf = ols(tr, x0, "F_tgt", ["F3", "F_base"] + top)
    mg, sg = ols(tr, x0, "G_tgt", ["G3", "G_base"])
    pf = norm.cdf((mf - Y8.TF) / max(sf, 0.1))
    pg = norm.cdf((mg - Y8.TG) / max(sg, 0.05))
    return float(1 - (1 - pf) * (1 - pg)), top


def main():
    plan_ok()
    Y10.plan_ok()
    Y10.W = Y10.world()
    allr = {}
    for t in range(R.qi("1995-Q1"), Y8.T_LAST + 1):
        r = Y8.row(t)
        if r is not None:
            allr[t] = {**r, **Y10.wfeats(t)}
    rows = []
    for t in range(Y8.T_FIRST, Y8.T_LAST + 1):
        if t not in allr or "y" not in allr[t]:
            continue
        tr = pd.DataFrame([r for tt, r in allr.items() if tt <= t - 3 and "y" in r])
        x0 = allr[t]
        p = Y8.fit_predict(tr, x0)
        w, top = war(tr, x0, True)
        w0, _ = war(tr, x0, False)
        rows.append({"t": t, "target": R.qs(t + 2), "y": x0["y"], "pers_bin": x0["pers_bin"], "PERS_PROB": p["PERS_PROB"],
                     "WAR": w, "WAR0": w0, "top3": "|".join(top), "trainRows": len(tr)})
    d = pd.DataFrame(rows).dropna(subset=["PERS_PROB", "WAR", "WAR0"])
    res = {"rows": len(d), "prevalence": float(d["y"].mean()), "period": f"{d['target'].min()}..{d['target'].max()}",
           "top3_frequency": pd.Series("|".join(d["top3"]).split("|")).value_counts().to_dict()}
    for c in ("pers_bin", "PERS_PROB", "WAR", "WAR0"):
        res[c] = R.metrics(d["y"], d[c])
    for c in ("WAR", "WAR0"):
        res[f"{c}_vs_PERS_PROB"] = {"iid": Y8.boot(d, c, "PERS_PROB"), "block4": Y8.boot(d, c, "PERS_PROB", 4)}
    res["WAR_vs_WAR0"] = {"iid": Y8.boot(d, "WAR", "WAR0"), "block4": Y8.boot(d, "WAR", "WAR0", 4)}
    res["WAR_gate"] = {"G1": res["WAR_vs_PERS_PROB"]["iid"]["diff"] < 0 and res["WAR_vs_PERS_PROB"]["iid"]["p_one_sided"] < .10,
                       "G2": (res["WAR"]["balanced"] or 0) >= (res["PERS_PROB"]["balanced"] or 0)}
    res["passedGate"] = ["WAR"] if all(res["WAR_gate"].values()) else []
    OUT.mkdir(exist_ok=True)
    (OUT / "y11_dev.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    d.to_csv(OUT / "y11_dev_rows.csv", index=False, lineterminator="\n", float_format="%.5f")
    print({k: res[k] for k in ("rows", "prevalence", "period", "top3_frequency")})
    for c in ("pers_bin", "PERS_PROB", "WAR", "WAR0"):
        m = res[c]
        print(f"{c:10s} acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} "
              f"spec {m['specificity'] or 0:.2f} AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f}")
    for k in ("WAR_vs_PERS_PROB", "WAR0_vs_PERS_PROB", "WAR_vs_WAR0"):
        print(k, res[k])
    print("gate", res["WAR_gate"], "passed:", res["passedGate"])


if __name__ == "__main__":
    main()

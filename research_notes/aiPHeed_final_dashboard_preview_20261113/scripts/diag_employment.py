r"""Diagnostic (read-only): per-input breakdown of FINAL's employment contribution for the live 2026-Q4 issue, Lead 1, all five seeds,
g variant (own survey gap). For each employment input: live value, training mean and percentile, fixed monotone sign, exact
LightGBM contribution (logit, x g). Run from C:\Users\admin\aipheed_hcw\backend with AIPHEED_LIVE_ASOF=2026-11-01 PYTHONPATH=."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_corrected as B
from app.hcw import engine as H
from app.hcw import final_engine as FE
from app.e151 import prov as Pv

CAP = {}
_fp = FE.fit_predict
def _cap(tr, te, AN, seed, FS=None):
    out = _fp(tr, te, AN, seed) if FS is None else _fp(tr, te, AN, seed, FS)
    CAP[seed] = (tr, te, out)
    return out
FE.fit_predict = _cap

rows = []
for seed in B.SEEDS:
    r = B._one(1, seed)
    tr, te, out = CAP[seed]
    mdl = out["model"]
    n5 = len(r["province"])
    cols = r["cols"]
    C = r["contrib"][:n5]
    Xte = out["te"].iloc[:n5] if "te" in out else te.iloc[:n5]
    for j, c in enumerate(cols):
        base = c[3:] if c.startswith("mi_") else c
        if H.group_of(base) != "employment":
            continue
        sign = H.NEW_SIGN.get(c, Pv.SIGN.get(c, 0))
        trv = tr[c].dropna() if c in tr else pd.Series(dtype=float)
        for k, prov in enumerate(r["province"][:n5]):
            v = Xte[c].iloc[k] if c in Xte else np.nan
            rows.append({"seed": seed, "input": c, "sign": sign, "province": prov, "live_value": v,
                         "train_mean": trv.mean(), "train_min": trv.min(), "train_max": trv.max(),
                         "live_pctile": (trv < v).mean() if len(trv) and v == v else np.nan,
                         "contribution_logit": C[k][j]})
D = pd.DataFrame(rows)
out = Path(__file__).resolve().parents[1] / "out_corrected" / "employment_breakdown.csv"
D.to_csv(out, index=False)
pd.set_option("display.width", 250)
print(D.groupby(["input", "sign"]).agg(live=("live_value", "mean"), tr_mean=("train_mean", "mean"), tr_min=("train_min", "mean"),
      tr_max=("train_max", "mean"), pct=("live_pctile", "mean"), contrib=("contribution_logit", "mean"), seeds=("seed", "nunique")).round(4).to_string())
print("\nsum per province (mean over seeds):")
print(D.groupby(["province", "seed"])["contribution_logit"].sum().groupby("province").mean().round(4).to_string())

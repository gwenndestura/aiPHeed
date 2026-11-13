r"""Rule 7e (missing groups) and 7g (90 % training-province perturbation, reported only) for FINAL and FINAL-ET at Lead 1, seed 168.
FINAL-ET's 2018/2019 rows equal FINAL's (same model, same inputs); its 2021 rows come from parts_et. Run: python -I stability_et.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]; SA = HERE.parent / "aiPHeed_final_standalone_20261113"
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
lab = LAB[LAB.lead == 1][["key", "survey", "y_high"]]
def ba(g):
    h, y = g.p >= .5, g.y_high == 1
    return float(0.5 * ((h & y).sum() / y.sum() + (~h & ~y).sum() / (~y).sum()))
def rec(g, sv):
    x = g[(g.survey == sv) & (g.y_high == 1)]
    return float((x.p >= .5).mean())
# 7e
R = pd.concat([pd.read_csv(f) for f in glob.glob(str(SA / "parts_rerun" / "FINALR__*__1__168.csv"))])        # FINAL incl. missing-group copies
E = pd.read_csv(HERE / "parts_et" / "ET__ENNS2021__1__168.csv")
out = {"7e": []}
for v in ("none", "market", "climate", "employment", "poverty", "agri_fish", "news_aggregate"):
    fin = R[R.variant == ("none" if v == "none" else f"missing_{v}")][["key", "survey", "p"]]
    et21 = E[E.variant == ("ET" if v == "none" else f"ET_missing_{v}")][["key", "survey", "p"]]
    et = pd.concat([fin[fin.survey != "ENNS2021"], et21]).merge(lab, on=["key", "survey"])
    out["7e"].append({"variant": v, "FINAL_ET_BA": round(ba(et), 3), "FINAL_ET_2021_recall": rec(et, "ENNS2021")})
base = out["7e"][0]["FINAL_ET_BA"]
for r in out["7e"]:
    r["delta_BA"] = round(r["FINAL_ET_BA"] - base, 3)
out["7e_severe_any"] = any(abs(r["delta_BA"]) > .10 for r in out["7e"])
# 7g
P = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts_et" / "PERT__*.csv"))])
rows = []
for sub, g in P.groupby("sub"):
    for arm, var in (("FINAL", "FINAL"), ("FINAL-ET", "ET")):
        x = g[g.variant == var][["key", "survey", "p"]].merge(lab, on=["key", "survey"])
        rows.append({"subsample": int(sub), "arm": arm, "BA": round(ba(x), 3), "recall_2018": rec(x, "ENNS2018"), "recall_2019": rec(x, "ENNS2019"),
                     "recall_2021": rec(x, "ENNS2021")})
out["7g"] = rows
full = {"FINAL": 0.847, "FINAL-ET": base}
out["7g_max_abs_delta_BA"] = {a: round(max(abs(r["BA"] - full[a]) for r in rows if r["arm"] == a), 3) for a in full}
json.dump(out, open(HERE / "evidence" / "R7_et_sensitivity.json", "w"), indent=1)
print(json.dumps(out, indent=1))

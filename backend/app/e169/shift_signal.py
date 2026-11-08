"""Diagnostic (post-hoc, uses test errors): was the round/region shift visible in SWS area hunger available at the origin?
Only SWS rows published through 2021 are read."""
import json, sys
import numpy as np, pandas as pd

from app.paths import BACKEND_DIR
B = str(BACKEND_DIR / "data")
G = pd.read_csv(f"{B}/e158/out/oof.csv")
G = G[G.lead == 1]
E = pd.read_csv(f"{B}/e168/out/all_rows.csv")
E = E[(E["mode"] == "main") & (E.lead == 1)][["key", "survey", "mu"]]
X = G.merge(E, on=["key", "survey"]).reset_index(drop=True)
S = pd.read_csv(f"{B}/fi5/raw/sws/sws_area_rounds_full.csv")
S = S[S.quarter.str[:4].astype(int) <= 2021].copy()
S["pubT"] = pd.to_datetime(S.published).dt.year * 4 + (pd.to_datetime(S.published).dt.month - 1) // 3
S["qT"] = S.quarter.str[:4].astype(int) * 4 + S.quarter.str[-1].astype(int) - 1


def area(r):
    if r.region == "NCR":
        return "metro_manila"
    return {"Luzon": "balance_luzon", "Visayas": "visayas", "Mindanao": "mindanao"}[r.island]


def level(col, t_ref, t_pub):
    """mean of the 4 SWS rounds whose fieldwork quarter <= t_ref and published <= t_pub (as-of)"""
    s = S[(S.qT <= t_ref) & (S.pubT <= t_pub)].sort_values("qT").tail(4)
    return float(s[col].mean())


rows = []
for _, r in X.iterrows():
    a = area(r)
    origin = r["T"] - (r["lead"] + 1)          # Lead k = k+1 quarters before the survey quarter
    anchor = r["T"] - r["gap_q"]
    l0, l1 = level(a, anchor, origin), level(a, origin, origin)
    lg = lambda v: np.log(v / (100 - v))
    rows.append({"survey": r.survey, "region": r.region, "err": r.mu - r.y_true, "true_change": r.y_true - r.y_anchor,
                 "pred_change": r.mu - r.y_anchor, "sws_change_logit": lg(l1) - lg(l0)})
D = pd.DataFrame(rows)
out = {"row_corr(sws_change, true_change)": round(float(D[["sws_change_logit", "true_change"]].corr().iloc[0, 1]), 3),
       "row_corr(sws_change, error)": round(float(D[["sws_change_logit", "err"]].corr().iloc[0, 1]), 3),
       "row_corr(model_change, true_change)": round(float(D[["pred_change", "true_change"]].corr().iloc[0, 1]), 3)}
R = D.groupby(["survey", "region"]).mean(numeric_only=True).reset_index()
out["region_round_cells"] = len(R)
out["cell_corr(sws_change, true_change)"] = round(float(R[["sws_change_logit", "true_change"]].corr().iloc[0, 1]), 3)
out["cell_corr(sws_change, error)"] = round(float(R[["sws_change_logit", "err"]].corr().iloc[0, 1]), 3)
out["by_round"] = {s: {"mean_true_change": round(float(g.true_change.mean()), 3), "mean_model_change": round(float(g.pred_change.mean()), 3),
                       "mean_sws_change": round(float(g.sws_change_logit.mean()), 3)} for s, g in D.groupby("survey")}
# What 1:1 logit transfer of SWS change would have done (fixed, not fitted) - diagnostic only
X["mu_sws"] = X.mu + D.sws_change_logit.values
X["mu_shift_only"] = X.y_anchor + D.sws_change_logit.values
for c in ("mu", "mu_sws", "mu_shift_only", "y_anchor"):
    out[f"acc_{c}"] = round(float(((X[c] >= 0) == (X.y_high == 1)).mean()), 3)
json.dump(out, sys.stdout, indent=1)

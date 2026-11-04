"""
E144 provincial forecast issue (candidate): issued at the start of the viewing quarter for the next four quarters.

    python -m app.e144.issue  -> data/e144/out/issue/{forecast.json, lgus_next_quarter.csv, sealed_prediction_<date>.json}

Per province and target quarter T = V+1..V+4:
  area hunger forecast for Balance Luzon (Stage A level regressor, news and nowcast as inputs; logit and SD)
  -> link M1 (all four HFIAS rounds) with the province's C4 relative risk (E143 C4, live)
  -> P(province HFIAS moderate-or-severe > 42.8 %), the expected prevalence and its 90 % interval.
Class: HIGH if P >= 0.80, LOW if P <= 0.20, otherwise UNCERTAIN (P already carries the forecast, link, residual and
C4 uncertainty). p_interval90 = P with the area-hunger forecast at its 5th and 95th percentiles.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.e140 import issue as I140
from app.e141 import panel as P
from app.e143 import issue as I143
from app.e143 import model as M143
from app.e144 import OUT
from app.e144 import data as D
from app.e144 import link as L
from app.e144 import model as MA
from app.fi5.target import qindex, qlabel
from app.quarterly.target import forecast_target
from app.registry import prospective_provincial as PP

MODEL_ID = "e144-lbf-1.0"
AREA = "balance_luzon"


def run(issue: pd.Timestamp | None = None, status: str = "CANDIDATE - see data/e144/out/results.json decisions") -> dict:
    ft = forecast_target()
    if issue is None:
        issue = pd.Timestamp(ft["origin"])
    i = qindex(f"{issue.year}-Q{(issue.month - 1) // 3 + 1}") - 1           # last complete quarter at issue
    d = D.q_end(i)
    X = MA.panel(last_issue=i)
    tr = X[X["y"].notna() & (X["label_published"] <= d)]
    q = X[(X["issue_qi"] == i) & (X["area"] == AREA)].sort_values("h")
    clf = MA.LGBC(MA.SETS["A LightGBM (full)"]).fit(tr, tr["y"].astype(int))
    lv = MA.LGBLevel(MA.SETS["A LightGBM (full)"]).fit(tr)
    p_area = clf.predict_proba(q)
    h_mu, h_sd = lv.predict(q)
    # C4 live relative risk (no time decay in the hierarchical form, so one value per province)
    Xp = P.data(1)
    Z = I143._frame(issue, Xp)
    an = M143.Anchored("hre", "lgbm").fit(Xp)
    yh, V = an.predict(Z, target_q=i + 2)
    cal = Z.index[Z["k"].isin(I140.CAL)]
    R = Z.loc[cal, ["key", "province"]].assign(r_hat=yh[cal], r_var=V[cal]).reset_index(drop=True)
    m1 = L.fit(L.rows(), True)
    out_rows = []
    for j, (_, row) in enumerate(q.iterrows()):
        T = int(row["target_qi"])
        hm, hs = float(h_mu[j]), float(h_sd[j])
        mu, var = L.predict(m1, R, np.full(len(R), hm), np.full(len(R), hs))
        p = norm.cdf((mu - L.LT) / np.sqrt(var))
        lo_mu, _ = L.predict(m1, R, np.full(len(R), hm - 1.645 * hs), None)
        hi_mu, _ = L.predict(m1, R, np.full(len(R), hm + 1.645 * hs), None)
        v0 = var - m1["beta"][2] ** 2 * hs ** 2
        p_lo, p_hi = norm.cdf((lo_mu - L.LT) / np.sqrt(v0)), norm.cdf((hi_mu - L.LT) / np.sqrt(v0))
        for k in range(len(R)):
            prev = 1 / (1 + np.exp(-mu[k]))
            sd = np.sqrt(var[k])
            out_rows.append({
                "province": R.at[k, "province"], "issue_date": issue.date().isoformat(), "viewing_quarter": qlabel(i + 1),
                "target_quarter": qlabel(T), "h": int(row["h"]), "p_high": round(float(p[k]), 4),
                "p_interval90": [round(float(min(p_lo[k], p_hi[k])), 4), round(float(max(p_lo[k], p_hi[k])), 4)],
                "risk_class": "HIGH" if p[k] >= 0.8 else "LOW" if p[k] <= 0.2 else "UNCERTAIN",
                "expected_prevalence_pct": round(100 * float(prev), 1),
                "prevalence_interval90_pct": [round(100 / (1 + np.exp(-(mu[k] - 1.645 * sd))), 1),
                                              round(100 / (1 + np.exp(-(mu[k] + 1.645 * sd))), 1)],
                "area_hunger_forecast_pct": round(100 / (1 + np.exp(-hm)), 1),
                "area_p_above_normal": round(float(p_area[j]), 4),
                "c4_relative_logit": round(float(R.at[k, "r_hat"]), 3),
                "contributions_logit": {"structural_and_survey_anchor (C4)": round(float(m1["beta"][1] * R.at[k, "r_hat"]), 3),
                                        "area_hunger_forecast (news + history + national)": round(float(m1["beta"][2] * hm), 3),
                                        "intercept": round(float(m1["beta"][0]), 3)}})
    F = pd.DataFrame(out_rows)
    out = {"model": f"{MODEL_ID} (Stage A LightGBM news-fed area forecast -> Stage C link -> C4)",
           "validation_status": status, "issue_date": issue.date().isoformat(), "information_cutoff": d.date().isoformat(),
           "viewing_quarter": qlabel(i + 1), "dashboard_target_quarter": qlabel(i + 2),
           "threshold": "HIGH risk = province HFIAS moderate-or-severe above 42.8 % (national, pooled ENNS 2018/2019)",
           "link": {k: float(v) for k, v in zip(m1["names"], m1["beta"])} | {"residual_var": m1["s2"]},
           "class_rule": "HIGH if P >= 0.80; LOW if P <= 0.20; otherwise UNCERTAIN",
           "meaning": "Probability that the province's household food insecurity (HFIAS moderate-or-severe) exceeds the "
                      "national reference level in the target quarter. A risk estimate, not a measured prevalence.",
           "forecasts": F.to_dict(orient="records")}
    out_dir = OUT / "issue"
    out_dir.mkdir(parents=True, exist_ok=True)
    nxt = F[F["h"] == 1]
    I140.lgu_priority([{"province": r["province"], "p_elevated": r["p_high"], "p_interval90": r["p_interval90"],
                        "risk_class": r["risk_class"]} for _, r in nxt.iterrows()], qlabel(i + 2), out_dir)
    seal = {"model": MODEL_ID, "issue_date": out["issue_date"], "predictions": F[["province", "target_quarter", "p_high",
                                                                                     "expected_prevalence_pct"]].to_dict(orient="records"),
            "sealed_utc": datetime.now(timezone.utc).isoformat()}
    sp = out_dir / f"sealed_prediction_{out['issue_date']}.json"
    if not sp.exists():
        sp.write_text(json.dumps(seal, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    sha = hashlib.sha256(sp.read_text(encoding="utf-8").encode()).hexdigest()
    PP.register(MODEL_ID, sp, sha, out["issue_date"])
    out["sealed_prediction_sha256"] = sha
    (out_dir / "forecast.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8", newline="\n")
    return out


if __name__ == "__main__":
    o = run()
    for r in o["forecasts"]:
        print(r["target_quarter"], r["province"], r["p_high"], r["p_interval90"], r["risk_class"], r["expected_prevalence_pct"],
              r["area_hunger_forecast_pct"])

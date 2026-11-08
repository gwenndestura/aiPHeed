"""
Quarterly provincial table and sealed candidate forecast from the arm selected under the E146 lock (E2E-clean: the shock model
was never selected). Not a validated forecast. Registry, production pointer and dashboard are not touched.

    python -m app.e146.issue -> data/e146/out/issue/{quarterly_table.csv, forecast.json, lgu_priority_<quarter>.csv, sealed_prediction_<date>.json}

Every row is marked:
  measured   a survey round (HFIAS)
  estimated  a past quarter with no provincial measurement: link + province position + published SWS hunger. Never scored.
  forecast   target quarters after the issue date, from the Stage A area forecast at that lead.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.e140 import issue as I140
from app.e141 import evaluate as E141
from app.e141 import panel as P
from app.e143 import issue as I143
from app.e143 import model as M143
from app.e144 import data as D
from app.e144 import link as L
from app.e144 import model as MA
from app.e145 import lgu as LGU
from app.e145.evaluate import Level
from app.e146 import OUT
from app.fi5.target import qindex, qlabel

AREA = "balance_luzon"
STATUS = "CANDIDATE - development evidence only; fails the locked reliability rule (does not beat persistence); not validated"


def _expit(x):
    return 1 / (1 + np.exp(-np.asarray(x, float)))


def run(issue: pd.Timestamp = pd.Timestamp("2026-10-01")) -> dict:
    out_dir = OUT / "issue"
    out_dir.mkdir(parents=True, exist_ok=True)
    i = qindex(f"{issue.year}-Q{(issue.month - 1) // 3 + 1}") - 1
    d = D.q_end(i)
    # province position and link, every round; training positions out of fold (protocol section 3)
    Xp = P.data(1)
    lk = L.rows()[["key", "survey", "H", "y_abs", "se_abs", "q_star"]]
    tr = Xp.merge(lk, on=["key", "survey"], how="inner").reset_index(drop=True)
    an = M143.Anchored("hre", "lgbm").fit(tr, Level().fit(tr))
    tr = tr.assign(r_hat=an.lv_.oof_, r_var=0.0)
    m1 = L.fit(tr, True)
    Z = I143._frame(issue, Xp)
    yh, V = an.predict(Z, target_q=i + 2)
    cal = Z.index[Z["k"].isin(I140.CAL)]
    R = Z.loc[cal, ["key", "province"]].assign(r_hat=yh[cal], r_var=V[cal]).reset_index(drop=True)
    R["p_above_national"] = norm.cdf(R["r_hat"] / np.sqrt(R["r_var"]))
    rows = []
    # estimated: published SWS Balance Luzon hunger
    s = D.sws_quarterly()
    s = s[(s["area"] == AREA) & (s["published"] <= d) & (s["qi"] >= qindex("2012-Q1"))].sort_values("qi")
    for _, q in s.iterrows():
        mu, var = L.predict(m1, R, np.full(len(R), MA._logit(np.array([q["hunger"]]))[0]), None)
        for k in range(len(R)):
            sd = np.sqrt(var[k])
            rows.append({"province": R.at[k, "province"], "quarter": qlabel(int(q["qi"])), "row_type": "estimated", "prevalence_pct": round(100 * float(_expit(mu[k])), 1),
                         "low90": round(100 * float(_expit(mu[k] - 1.645 * sd)), 1), "high90": round(100 * float(_expit(mu[k] + 1.645 * sd)), 1), "instrument": "HFIAS-scale estimate",
                         "lead": None, "p_above_42_8": round(float(norm.cdf((mu[k] - L.LT) / sd)), 3), "p_above_national": round(float(R.at[k, "p_above_national"]), 3)})
    # forecast: Stage A at each lead
    X = MA.panel(last_issue=i)
    A = X[X["y"].notna() & (X["label_published"] <= d)]
    q = X[(X["issue_qi"] == i) & (X["area"] == AREA)].sort_values("h")
    lv = MA.LGBLevel(MA.SETS["A LightGBM (full)"]).fit(A)
    hm, hs = lv.predict(q)
    fc = []
    for j, (_, row) in enumerate(q.iterrows()):
        mu, var = L.predict(m1, R, np.full(len(R), hm[j]), np.full(len(R), hs[j]))
        for k in range(len(R)):
            sd = np.sqrt(var[k])
            r = {"province": R.at[k, "province"], "quarter": qlabel(int(row["target_qi"])), "row_type": "forecast", "prevalence_pct": round(100 * float(_expit(mu[k])), 1),
                 "low90": round(100 * float(_expit(mu[k] - 1.645 * sd)), 1), "high90": round(100 * float(_expit(mu[k] + 1.645 * sd)), 1), "instrument": "HFIAS-scale forecast",
                 "lead": int(row["h"]), "p_above_42_8": round(float(norm.cdf((mu[k] - L.LT) / sd)), 3), "p_above_national": round(float(R.at[k, "p_above_national"]), 3)}
            rows.append(r)
            fc.append({**r, "area_hunger_forecast_pct": round(100 * float(_expit(hm[j])), 1), "area_hunger_sd_logit": round(float(hs[j]), 3)})
    # measured HFIAS rounds replace the estimate of that quarter
    T = pd.DataFrame(rows)
    meas = P.outcomes()
    meas = meas[meas["province"].isin(E141.CAL)]
    for _, m in meas.iterrows():
        T = T[~((T["province"] == m["province"]) & (T["quarter"] == m["ref_quarter"]))]
    M = pd.DataFrame({"province": meas["province"], "quarter": meas["ref_quarter"], "row_type": "measured", "prevalence_pct": meas["p"],
                      "low90": (meas["p"] - 1.645 * meas["se_p"]).round(1), "high90": (meas["p"] + 1.645 * meas["se_p"]).round(1), "instrument": "HFIAS " + meas["survey"]})
    T = pd.concat([T, M], ignore_index=True).sort_values(["province", "quarter"])
    T.to_csv(out_dir / "quarterly_table.csv", index=False, lineterminator="\n")
    first = qlabel(i + 2)
    p_map = dict(zip(R["province"], R["p_above_national"]))
    LGU.rank(p_map, first).to_csv(out_dir / f"lgu_priority_{first}.csv", index=False, lineterminator="\n")
    out = {"status": STATUS, "issue_date": issue.date().isoformat(), "information_cutoff": d.date().isoformat(), "viewing_quarter": qlabel(i + 1), "lead_1_target": first,
           "link": {k: float(v) for k, v in zip(m1["names"], m1["beta"])} | {"residual_var": m1["s2"]},
           "class_note": "p_above_national is the survey-validated class (E143 C4) and does not move by quarter. p_above_42_8 moves with area hunger but over-warns: false-alarm rate 0.93 on measured rows.",
           "forecasts": fc}
    (out_dir / "forecast.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    sp = out_dir / f"sealed_prediction_{out['issue_date']}.json"
    if not sp.exists():
        sp.write_text(json.dumps({"model": "e146 E2E-clean", "issue_date": out["issue_date"], "sealed_utc": datetime.now(timezone.utc).isoformat(), "predictions": fc}, indent=1, sort_keys=True, default=float), newline="\n")
    print("sealed sha256", hashlib.sha256(sp.read_bytes()).hexdigest())
    for r in fc:
        print(r["quarter"], r["province"], "L", r["lead"], r["prevalence_pct"], [r["low90"], r["high90"]], "P>42.8", r["p_above_42_8"], "P>national", r["p_above_national"], "SWS", r["area_hunger_forecast_pct"])
    print(T["row_type"].value_counts().to_dict(), {k: round(float(v), 3) for k, v in out["link"].items()})
    return out


if __name__ == "__main__":
    run()

"""
Dashboard export for the approved E168 model (registry e168-lgbm-1.0): the same 2026-Q4 issue as data/e168/out/live_2027.json
(app.e168.serve._forecast, unchanged), plus each trigger group's exact additive contribution to the LightGBM change
(LightGBM pred_contrib on the logit scale) and the input values the forecast used. The forecast values are checked against
the approved artifact; nothing is re-selected by hand.

    python -m app.e168.dashboard_export   -> data/e168/out/dashboard_rows.csv
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e168" / "out"
ROWS = OUT / "dashboard_rows.csv"
CODES = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000", "Batangas": "PH040500000"}
GROUPS = {"market": "market", "climate": "climate", "employment": "employment", "remittance": "ofw_remittance", "poverty": "poverty"}
# The thesis's five triggers (Chapter III, Algorithm 2) are market, climate, employment, OFW remittance and fish kill;
# fisheries production is therefore its own bar, not part of climate. Poverty columns are exported separately (shap_poverty):
# poverty belongs to the LGU weighting (Objective 3) and is not drawn as a trigger bar.
OWN_BAR = {"c_fish_yoy": "fish_kill"}
BARS = list(GROUPS.values()) + ["fish_kill"]
VALUES = ["cpi_food_yoy", "cpi_rice_yoy", "c_tc_4q", "c_agri_yoy", "c_fish_yoy", "oni", "unemp_rate", "unemp_yoy", "remit_yoy",
          "p_poverty", "p_density", "p_e_net", "a_e_net", "n_e_net", "gap_q"]
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def _cutoff(issue: str) -> str:
    """Information cut-off of the issue: the quarter's first day, or the live refresh's as-of date (app.e148.panel.q_start)."""
    from app.e148 import panel as Pn
    from app.fi5.target import qindex
    return Pn.q_start(qindex(issue)).date().isoformat()


def _lead(lead: int, issue: str = "2026-Q4") -> pd.DataFrame:
    from app.e163 import model as C
    from app.e168 import lgbm_only as E
    from app.e168 import serve as SV
    cap = {}
    orig_predict = E.LGBRes.predict

    def predict(self, X):
        if len(X) == len(SV.CAL):          # the final model's call on the five live rows (inner folds use training rows)
            cap["contrib"] = self.m_.predict(X[self.use_], pred_contrib=True)
            cap["cols"], cap["X"] = list(self.use_), X.reset_index(drop=True)
        return orig_predict(self, X)

    E.LGBRes.predict = predict
    rows = SV._forecast(lead, issue)
    news = set(E.NEWS)
    out = []
    for k, r in enumerate(rows):
        contrib, cols, X = cap["contrib"][k], cap["cols"], cap["X"]
        g = {v: 0.0 for v in BARS}
        g_news = {v: 0.0 for v in BARS}
        other = 0.0
        for j, c in enumerate(cols):
            grp = OWN_BAR.get(c) or (GROUPS.get(C.gmap(c)) if C.gmap(c) else None)
            if grp is None:
                other += contrib[j]
            else:
                g[grp] += contrib[j]
                if c in news:
                    g_news[grp] += contrib[j]
        change = float(contrib.sum())               # LightGBM change on the logit scale (bias column included)
        mu = np.log(r["score_pct"] / (100 - r["score_pct"]))
        o = {"province_code": CODES[r["province"]], "province": r["province"], "quarter": r["target_quarter"], "lead": lead,
             "issue_date": _cutoff(issue), "probability": r["p_high"], "class": r["risk_class"], "score_pct": r["score_pct"],
             "range90_low": r["range90_pct"][0], "range90_high": r["range90_pct"][1], "config": r["config"],
             "baseline_pct": round(float(pct(mu - change)), 2), "change_logit": round(change, 6), "bias_logit": round(float(contrib[-1]), 6),
             "shap_other": round(float(other), 6), "model": "e168-lgbm-1.0"}
        for v in BARS:
            o[f"shap_{v}"], o[f"shap_news_{v}"] = round(g[v], 6), round(g_news[v], 6)
        for c in VALUES:
            o[f"val_{c}"] = None if c not in X or pd.isna(X.at[k, c]) else float(X.at[k, c])
        out.append(o)
    return pd.DataFrame(out)


def run():
    D = pd.concat(Parallel(n_jobs=3)(delayed(_lead)(l) for l in (1, 2, 3)), ignore_index=True)
    live = json.loads((OUT / "live_2027.json").read_text())
    ref = {(r["province"], r["lead"]): r for r in live["provinces"]}
    for _, r in D.iterrows():
        a = ref[(r["province"], int(r["lead"]))]
        assert (a["score_pct"], a["p_high"], a["risk_class"]) == (r["score_pct"], r["probability"], r["class"]), (r["province"], r["lead"])
    D.to_csv(ROWS, index=False, lineterminator="\n")
    print(D[["province", "lead", "quarter", "score_pct", "probability", "class", "baseline_pct"] + [f"shap_{v}" for v in BARS] + ["shap_other"]].to_string())


if __name__ == "__main__":
    run() if sys.argv[1:] in ([], ["run"]) else None

"""FI10 live provincial outputs (offline issue; the API only reads the written files).

    python -m app.fi10.serve issue [--as-of YYYY-MM-DD]

For each of Cavite, Laguna, Batangas, Rizal, Quezon:
  * DIRECT, measured: provincial food-price pressure outlook, Leads 1 and 2. The model is the one the locked FI10
    protocol selected on the development period. Status is provisional: no lead met every adoption requirement.
    Leads 3-4 are not issued (no skill on the test period).
  * CONTEXT: latest poverty incidence and the validated province priority (FI9, 0.65 poverty weight).
  * REGIONAL REFERENCE: the Balance Luzon hunger outlook (FI9), identical for all provinces and labelled as such.
  * FOOD-ACCESS PRESSURE VIEW (proxy, not validated): price-pressure outlook beside poverty above/below the
    CALABARZON median, following the vulnerability-plus-price-shock framework (PIDS 2025; FAO SOFI 2025).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.fi9 import prospective as PR
from app.fi9 import quarters as Q
from app.fi10 import OUT, PROVINCES, VERSION
from app.fi10 import data as DATA
from app.fi10 import study as S
from app.paths import BACKEND_DIR

GROUP_OF = {c: g for g, cols in DATA.GROUPS.items() for c in cols} | {c: "season" for c in DATA.SEASON} | {c: "province" for c in DATA.PROV_FE}
LABEL = {"market": "Market and food prices", "climate": "Climate and agricultural supply", "employment": "Employment and remittances",
         "poverty": "Poverty and social vulnerability", "news": "News and NLP", "season": "Season", "province": "Province"}
REGISTER = OUT / "register.jsonl"


def today() -> pd.Timestamp:
    return pd.Timestamp(os.getenv("AIPHEED_NOW") or datetime.now().date().isoformat()).normalize()


def _lgb_contrib(feats, tr, te, params):
    import lightgbm as lgb
    cols = S._usable(tr, feats)
    hp = {k: v for k, v in params.items() if k != "sd"}
    m = lgb.LGBMRegressor(**hp, subsample=0.8, subsample_freq=1, random_state=7, verbose=-1).fit(tr[cols], tr["delta"])
    c = m.predict(te[cols], pred_contrib=True)[:, :-1]
    out = []
    for row in c:
        g = {}
        for col, v in zip(cols, row):
            g[GROUP_OF.get(col, "market")] = g.get(GROUP_OF.get(col, "market"), 0.0) + float(v)
        out.append(dict(sorted(g.items(), key=lambda kv: -abs(kv[1]))))
    return out


def issue(as_of=None) -> dict:
    ev = json.loads((OUT / "evaluation.json").read_text())
    live = pd.Timestamp(as_of) if as_of else today()
    D = DATA.build(live=live)
    c = Q.qi_of(live)
    d = D.loc[D["issue_quarter"] == Q.label(c), "issue_date"].max()
    hunger = json.loads((BACKEND_DIR / "data" / "fi9" / "out" / "forecast.json").read_text())
    prio = pd.read_csv(BACKEND_DIR / "data" / "fi9" / "out" / "province_priority.csv").set_index("province_name")
    pov_med = float(D[D["issue_quarter"] == Q.label(c)].groupby("province")["poverty_inc"].first().median())
    leads = {}
    for h in (1, 2):
        sel = ev["selection"][str(h)]["selected"]
        L = D[(D["lead"] == h) & D["y"].notna() & (D["target_published"] <= d)]
        te = D[(D["lead"] == h) & (D["issue_quarter"] == Q.label(c))].sort_values("province")
        members = S.ENSEMBLE[1] if sel == S.ENSEMBLE[0] else [sel]
        ps, lvs, taus, contrib, params = [], [], [], None, {}
        for name in members:
            kind, feats, _ = S.CONFIGS[name]
            fn, prm = S.fit(kind, feats, L)
            params[name] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in prm.items()}
            a, b = S._split(L)
            fa, _ = S.fit(kind, feats, a, prm if kind in S.TREE else None)
            taus.append(S._tau(fa(b)[0], b["y"].to_numpy(int)))
            p_, lv = fn(te)
            ps.append(p_)
            lvs.append(lv)
            if kind == "lgb_reg":
                contrib = _lgb_contrib(feats, L, te, prm)
        p, lv, tau = np.mean(ps, axis=0), np.nanmean(lvs, axis=0), float(np.mean(taus))
        tr = ev["by_lead"][str(h)][sel]["test_by_province"]
        rows = []
        for i, (_, r) in enumerate(te.iterrows()):
            m = tr[r["province"]]
            rows.append({"province": r["province"], "target_quarter": r["target_quarter"], "class": "HIGH" if p[i] >= tau else "LOW",
                         "p_high": round(float(p[i]), 2), "p_low": round(1 - float(p[i]), 2), "decision_threshold": round(tau, 2),
                         "projected_food_inflation_pct": round(float(lv[i]), 1), "province_high_line_pct": round(float(r["thr_known"]), 1),
                         "latest_food_inflation_pct": round(float(r["f_m"]), 1),
                         "latest_cpi_month": f"{int(r['cpi_month']) // 12}-{int(r['cpi_month']) % 12 + 1:02d}",
                         "drivers": [{"group": LABEL[g], "pp": round(v, 2)} for g, v in list(contrib[i].items())[:3]] if contrib else [],
                         "track_record": {"period": "test 2016-2026", "high_caught": m["tp"], "n_high": m["n_high"], "false_high": m["fp"],
                                          "n_low": m["n_low"], "balanced_accuracy": round(m["balanced_accuracy"] or 0, 2)}})
        t = ev["by_lead"][str(h)][sel]["test"]
        leads[h] = {"model": sel, "params_at_this_issue": params, "decision_threshold": round(tau, 3), "status": "provisional: did not meet every locked adoption requirement",
                    "failed_requirements": [k for k, v in ev["selection"][str(h)]["checks"].items() if v is False],
                    "test_overall": {k: round(t[k], 2) for k in ["accuracy", "balanced_accuracy", "macro_f1", "high_recall", "high_precision", "low_recall", "low_precision", "brier"]},
                    "provinces": rows}
    provinces = []
    for p in PROVINCES:
        cur = D[(D["issue_quarter"] == Q.label(c)) & (D["province"] == p) & (D["lead"] == 1)].iloc[0]
        l1 = next(x for x in leads[1]["provinces"] if x["province"] == p)
        high_pov = float(cur["poverty_inc"]) > pov_med
        view = ("elevated" if l1["class"] == "HIGH" and high_pov else "price shock, lower poverty" if l1["class"] == "HIGH"
                else "higher poverty, no price shock expected" if high_pov else "lower")
        provinces.append({"province": p, "lead1": l1, "lead2": next(x for x in leads[2]["provinces"] if x["province"] == p),
                          "poverty_incidence_pct": round(float(cur["poverty_inc"]), 1), "priority_score": round(float(prio.loc[p, "priority_score"]), 1),
                          "priority_rank": int(prio.index.get_loc(p) + 1), "food_access_pressure_view": view})
    body = {"version": VERSION, "issued_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "as_of": live.date().isoformat(),
            "issue_quarter": Q.label(c), "issue_date": str(pd.Timestamp(d).date()),
            "what_is_forecast": "Food-price pressure in each province: whether the province's food CPI inflation in the target quarter "
                                "will be unusually high (above its own 5-year normal plus one standard deviation). Measured by PSA for "
                                "each province. It is a driver of food access, not a measure of food insecurity.",
            "lead_status": {"1": leads[1]["status"], "2": leads[2]["status"], "3": "not issued: no skill on the test period",
                            "4": "not issued: no skill on the test period"},
            "leads": leads, "provinces": provinces,
            "regional_hunger_reference": {"area": "Balance Luzon (regional, same for every province)", "target_quarter": hunger.get("target_quarter"),
                                          "class": hunger.get("forecast", {}).get("class"), "p_high": hunger.get("forecast", {}).get("p_high"),
                                          "status": hunger.get("status")},
            "food_access_pressure_note": "Proxy view, not validated: combines the province's price-pressure outlook with whether its poverty "
                                         "incidence is above the CALABARZON median, following the vulnerability-plus-price-shock framework "
                                         "(PIDS 2025; FNRI 2024; FAO SOFI 2025). Poverty x price interactions did not improve the regional "
                                         "hunger forecast (FI10-A), so this view is descriptive.",
            "poverty_median_pct": round(pov_med, 1)}
    s = json.dumps(body, sort_keys=True, default=str)
    body["sha256"] = hashlib.sha256(s.encode()).hexdigest()
    (OUT / "forecast.json").write_text(json.dumps(body, indent=1, default=str))
    PR.append({"issue_date": body["issue_date"], "target_quarter": f"{Q.label(c + 1)} (provincial)", "generated_utc": body["issued_utc"],
               "version": VERSION, "forecast_sha256": body["sha256"],
               "forecast": {"class": None, "p_high": None, "interval95_pct": [None, None]}, "baselines": {},
               "provinces": {x["province"]: {"lead1": {k: x["lead1"][k] for k in ("target_quarter", "class", "p_high", "projected_food_inflation_pct")},
                                             "lead2": {k: x["lead2"][k] for k in ("target_quarter", "class", "p_high", "projected_food_inflation_pct")}}
                             for x in provinces}}, REGISTER)
    return body


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["issue"])
    ap.add_argument("--as-of", default=None)
    a = ap.parse_args()
    b = issue(a.as_of)
    for x in b["provinces"]:
        print(x["province"], x["lead1"]["target_quarter"], x["lead1"]["class"], x["lead1"]["p_high"], x["lead1"]["projected_food_inflation_pct"],
              "| L2", x["lead2"]["class"], x["lead2"]["p_high"], "| pov", x["poverty_incidence_pct"], "| view", x["food_access_pressure_view"])

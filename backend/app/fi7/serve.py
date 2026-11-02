"""FI7 live issue: forecasts for every lead, the served (validated) probability, LightGBM driver context, rankings.

    python -m app.fi7.serve issue [--as-of 2026-11-03]

Serving rule (pre-declared in docs/fi7): the probability shown to DA for a lead is the forecaster that passed the
reliability rules at that lead with the lowest Brier score; when none passed, the lead is shown as indicative only
(LightGBM probability, labelled not reliable). The proposed LightGBM always supplies the five-domain explanation
(its SHAP contributions), labelled as the indicators the model leaned on, not as the source of the served number.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.fi5 import rankings as R
from app.fi5.explain import PHRASES, _cap, _join
from app.fi5.target import qindex, qlabel
from app.fi6.features import DOMAIN
from app.fi6.news_model import NEWS_DOMAIN
from app.fi7 import VERSION
from app.fi7 import models as M
from app.fi7.design import Designer
from app.fi7.experiments import FINAL_PROPOSED, FINAL_SPECS
from app.fi7.paths import MODELS, OUT

DOM = {**DOMAIN, **NEWS_DOMAIN, "world_rice_yoy": "market", "world_rice_3m": "market", "world_urea_yoy": "market"}
NAMES = {"Damped persistence (statistical)": "damped", "Naive persistence (latest reading)": "persistence",
         FINAL_PROPOSED: "lightgbm"}
MIN_PP = 0.3


def _sentence(blocks: dict, tq: str) -> str:
    up = [b for b, v in sorted(blocks.items(), key=lambda kv: -kv[1]) if v >= MIN_PP][:2]
    down = [b for b, v in sorted(blocks.items(), key=lambda kv: kv[1]) if v <= -MIN_PP][:2]
    u, d = [PHRASES[b]["up"] for b in up], [PHRASES[b]["down"] for b in down]
    if u and d:
        s = f"{_cap(_join(u))} pointed to more hunger in {tq}, while {_join(d)} pointed to less."
    elif u:
        s = f"{_cap(_join(u))} pointed to more hunger in {tq}."
    elif d:
        s = f"{_cap(_join(d))} pointed to less hunger in {tq}."
    else:
        s = f"No indicator moved the outlook for {tq} much; it stays close to the latest survey reading."
    return s + " These are the conditions the model weighed, not proven causes."


def issue(as_of: str | None = None) -> dict:
    import shap

    as_of_ts = pd.Timestamp(as_of or datetime.now().date().isoformat())
    D = Designer("operational", as_of=as_of_ts)
    ev = json.loads((OUT / "final_evaluation.json").read_text())
    sens_p = OUT / "sensitivity_alternation.json"
    robust = json.loads(sens_p.read_text())["robust_reliable"] if sens_p.exists() else {}
    issue_qi = D.issue_qis[-1]
    out = []
    for h in [0, 1, 2, 3]:
        X = D.frame(h) if h else D.frame(0)
        L = X[X["y"].notna()]
        tr = L[L["target_published"] <= D.dates[issue_qi]]
        live = pd.DataFrame([D.row(issue_qi, issue_qi + h)])
        per = {}
        for tag in NAMES:
            t, kind, feats, _ = FINAL_SPECS[tag]
            m = M.fit(M.make(kind, feats), kind, tr)
            p = float(m.predict_proba(live)[0])
            cls = int(m.predict_class(live)[0]) if hasattr(m, "predict_class") else int(p >= 0.5)
            rel = ev["by_lead"][str(h)]["models"][tag]
            per[NAMES[tag]] = {"p_high": round(p, 4), "class": "HIGH" if cls else "LOW",
                               "reliable": bool(rel["reliability"]["reliable"]), "brier": rel["brier"], "model": m}
        lg = per["lightgbm"]["model"].inner
        sv = np.asarray(shap.TreeExplainer(lg.est).shap_values(live[lg.cols]))[0]
        blocks: dict[str, float] = {}
        for c, s in zip(lg.cols, sv):
            blocks[DOM[c]] = blocks.get(DOM[c], 0.0) + float(s)
        lg.est.booster_.save_model(str(MODELS / f"fi7_lightgbm_h{h}.txt"))
        reliable = [k for k in per if per[k]["reliable"]]
        served = min(reliable, key=lambda k: per[k]["brier"]) if reliable else "lightgbm"
        tag_of = {v: k for k, v in NAMES.items()}
        is_robust = bool(reliable) and bool(robust.get(tag_of[served], {}).get(str(h), robust.get(tag_of[served], {}).get(h, False)))
        tq = qlabel(issue_qi + h)
        lvl = float(live["hunger_last"].iloc[0])
        thr = float(live["threshold_known"].iloc[0])
        out.append({
            "h": h, "meaning": {0: "current quarter (nowcast)", 1: "NEXT QUARTER (operational outlook)",
                                2: "two quarters ahead", 3: "three quarters ahead"}[h],
            "issue_date": D.dates[issue_qi].date().isoformat(), "current_quarter": qlabel(issue_qi), "target_quarter": tq,
            "served_model": served, "served_reliable": bool(reliable), "p_high": per[served]["p_high"], "class": per[served]["class"],
            "status": ("validated forecast" if reliable and is_robust else
                       "provisional: passes the reliability rules on the full test set but not the survey-alternation "
                       "sensitivity check" if reliable else "indicative only: no method passed the reliability rules at this lead"),
            "robust_to_alternation_check": is_robust,
            "latest_hunger_pct": lvl, "latest_reading_quarter": live["last_reading_quarter"].iloc[0], "significance_line_pct": round(thr, 2),
            "plain_reading": (f"The latest survey reading ({lvl:.1f}%) is {'above' if lvl > thr else 'below'} the "
                              f"significantly-above-normal line ({thr:.1f}%)."),
            "drivers_explanation": _sentence(blocks, tq),
            "domain_contributions_pp": {k: round(v, 3) for k, v in sorted(blocks.items(), key=lambda kv: -abs(kv[1]))},
            "all_models": {k: {kk: vv for kk, vv in v.items() if kk != "model"} for k, v in per.items()},
        })
    nq = next(f for f in out if f["h"] == 1)
    status = (f"{nq['served_model']} next-quarter forecast ({'validated' if nq['served_reliable'] else 'indicative'}); every LGU "
              "shares the regional probability, so the order of LGUs comes from vulnerability")
    lgus = R.rank_lgus(nq["p_high"], {"forecast_target_quarter": nq["target_quarter"], "forecast_status": status})
    lgus.to_csv(OUT / "lgu_rankings.csv", index=False, lineterminator="\n")
    prov = R.province_priority(lgus)
    prov["forecast_basis"] = "Balance Luzon next-quarter forecast (covers all 5 provinces); province figures are vulnerability-adjusted priority"
    prov.to_csv(OUT / "province_priority.csv", index=False, lineterminator="\n")
    R.sensitivity(lgus).to_csv(OUT / "lgu_weight_sensitivity.csv", index=False, lineterminator="\n")
    seal = pd.DataFrame([{"issue_date": f["issue_date"], "target_quarter": f["target_quarter"], "h": f["h"], "served_model": f["served_model"],
                          "p_high": f["p_high"], "class": f["class"], **{f"p_{k}": v["p_high"] for k, v in f["all_models"].items()}} for f in out])
    seal_csv = seal.to_csv(index=False, lineterminator="\n")
    (OUT / "SEAL_fi7.csv").write_text(seal_csv)
    body = {"version": VERSION, "issued_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "as_of": as_of_ts.date().isoformat(), "current_quarter": qlabel(issue_qi), "forecasts": out,
            "furthest_reliable_lead_by_model": ev["furthest_reliable_lead"], "seal_sha256": hashlib.sha256(seal_csv.encode()).hexdigest(),
            "what_is_forecast": "Probability that SWS involuntary hunger in Balance Luzon (the SWS area containing all of "
                                "CALABARZON) is significantly above its five-year normal (beyond the survey margin of error)."}
    (OUT / "forecast.json").write_text(json.dumps(body, indent=1, default=str))
    return body


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["issue"])
    ap.add_argument("--as-of", default=None)
    a = ap.parse_args()
    b = issue(a.as_of)
    for f in b["forecasts"]:
        print(f["h"], f["target_quarter"], f["served_model"], f["p_high"], f["class"], f["status"], "|", f["plain_reading"], "|", f["drivers_explanation"])

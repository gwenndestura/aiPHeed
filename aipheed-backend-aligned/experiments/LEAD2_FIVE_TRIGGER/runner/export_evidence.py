"""Exports the measured five-trigger evidence (ablation.json) for the dashboard: per group its indicators, the held-out
leave-one-group-out change in Brier score at Leads 1-2, its SHAP share, and one plain sentence generated from those
numbers. A practical floor of 0.001 Brier separates "measurable" from "negligible".

    python export_evidence.py   # backend/data/ch1_trigger_evidence.json
"""
from __future__ import annotations

import json

import lt_lib as T

DEST = T.EXP.parents[1] / "backend" / "data" / "ch1_trigger_evidence.json"
FLOOR = 0.001
INDICATORS = {"market": "PSA food CPI projection and momentum, headline inflation, rice prices, world rice, cereal and oil prices",
              "climate": "PAGASA El Nino status, typhoons within 300 km, rice and corn harvest change, world fertilizer price",
              "employment": "PSA Labor Force Survey unemployment change (national)",
              "fish_kill": "PSA fisheries production change",
              "ofw_remittance": "BSP OFW cash remittance change (national)"}


def sentence(b: str, r: dict) -> str:
    l1, l2 = r["1"][b]["loo_t43c"], r["2"][b]["loo_t43c"]

    def state(x):
        if x["ci90"][0] > 0 and x["diff"] >= FLOOR:
            return "worse"
        if x["ci90"][1] < 0 and -x["diff"] >= FLOOR:
            return "better"
        return "unchanged" if abs(x["diff"]) < FLOOR else "uncertain"
    s1, s2 = state(l1), state(l2)
    words = {"worse": "made the forecasts worse", "better": "made the forecasts slightly better",
             "unchanged": "made no meaningful difference", "uncertain": "made a difference too small to confirm"}
    txt = (f"Tested on past quarters: leaving this group out {words[s1]} for the current quarter (Lead 1) and {words[s2]} "
           "for the next quarter (Lead 2).")
    if s1 == "worse" or s2 == "worse":
        txt += " Its contribution is measurable."
    elif s1 == "better" or s2 == "better":
        txt += " Its contribution is not established; at that horizon it adds more noise than information."
    else:
        txt += " Its contribution could not be established with the data available."
    return txt


def main():
    T.check_protocol(addendum=True)
    a = json.loads((T.OUT / "ablation.json").read_text())
    r = a["leads"]
    out = {"source": "aipheed-backend-aligned/experiments/LEAD2_FIVE_TRIGGER (Addendum 1 groups; protocol a80e927f)",
           "method": "leave-one-group-out walk-forward refits of the served unified LightGBM; Brier change of the risk "
                     "probability (P0H4-U schedule); development evidence", "floor": FLOOR,
           "all_triggers_removed": {k: r[k]["no_triggers"]["loo_t43c"] for k in ("1", "2")}, "groups": {}}
    for b in T.GROUPS:
        out["groups"][b] = {"label": T.GROUP_LABEL[b], "indicators": INDICATORS[b], "columns": T.GROUPS[b],
                            "class": a["classification"][b]["class"],
                            "brier_change_without": {k: r[k][b]["loo_t43c"] for k in ("1", "2", "3", "4")},
                            "shap_share": {k: r[k][b]["shap_share"] for k in ("1", "2")},
                            "sentence": sentence(b, r)}
        print(b, out["groups"][b]["sentence"])
    DEST.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()

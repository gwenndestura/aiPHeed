"""Exports the measured five-trigger evidence (ablation.json) for the dashboard: per group its indicators, the held-out
leave-one-group-out change in Brier score at Leads 1-2, its SHAP share, and one plain sentence generated from those
numbers. A practical floor of 0.001 Brier separates "measurable" from "negligible". A group is called measurable at a
lead only when the Holm-corrected p (over the five groups) is below ALPHA; a 90% interval above zero that does not
survive the correction is stated as not confirmed. Employment's card keeps the approved wording (CR_REVIEW 20.8).

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


ALPHA = 0.05
PERIOD = {"1": "the current quarter (Lead 1)", "2": "the next quarter (Lead 2)"}
# approved card wording (2026-10-29) for a group whose contribution no corrected test establishes
APPROVED = {"employment": "Employment-related indicators are included in the LightGBM model. However, their independent "
                          "contribution to forecasting has not been established by the current evaluation."}


def state(x: dict) -> str:
    if x["ci90"][0] > 0 and x["diff"] >= FLOOR:
        return "worse" if x.get("holm_p_hurts", 1.0) < ALPHA else "unconfirmed"
    if x["ci90"][1] < 0 and -x["diff"] >= FLOOR:
        return "better"
    return "unchanged" if abs(x["diff"]) < FLOOR else "uncertain"


def sentence(b: str, r: dict) -> str:
    st = {k: state(r[k][b]["loo_t43c"]) for k in ("1", "2")}
    words = {"worse": "made the forecasts worse for {}", "better": "made the forecasts slightly better for {}",
             "unconfirmed": "made the forecasts worse for {}, a difference not confirmed after correcting for multiple tests",
             "unchanged": "made no meaningful difference for {}", "uncertain": "made a difference too small to confirm for {}"}
    c1, c2 = (words[st[k]].format(PERIOD[k]) for k in ("1", "2"))
    txt = f"Tested on past quarters: leaving this group out {c1}{',' if st['1'] == 'unconfirmed' else ''} and {c2}."
    confirmed = [k for k in ("1", "2") if st[k] == "worse"]
    if confirmed:
        where = "the current and next quarters" if len(confirmed) == 2 else PERIOD[confirmed[0]]
        txt += f" Its contribution is measurable for {where}."
    elif b in APPROVED:
        txt += " " + APPROVED[b]
    elif "unconfirmed" in st.values():
        txt += " Its contribution is not established after correcting for multiple tests."
    elif "better" in st.values():
        txt += " Its contribution is not established; at that horizon it adds more noise than information."
    else:
        txt += " Its contribution could not be established with the data available."
    return txt


def build() -> dict:
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
    return out


def main():
    T.check_protocol(addendum=True)
    out = build()
    for b, g in out["groups"].items():
        print(b, g["sentence"])
    DEST.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()

"""Build dashboard_dev/public/e18_dashboard.json from an E18 run (reads only E18 files).
Usage: python -B runner/build_dashboard_json.py <run_dir_name>"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

EXP = Path(__file__).resolve().parents[1]
RUN = EXP / "runs" / sys.argv[1]
PROV = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
        "PH040500000": "Batangas"}


def nz(x):
    return None if x is None or (isinstance(x, float) and x != x) else x


def main():
    m = json.loads((RUN / "metrics.json").read_text(encoding="utf-8"))
    fc = json.loads((RUN / "forecast_2027Q1.json").read_text(encoding="utf-8"))
    comp = pd.read_csv(RUN / "components_2021Q1_2026Q2.csv", dtype={"province_code": str})
    hist = []
    for q, g in comp.groupby("quarter"):
        complete = g["D"].notna().all() and len(g) == 5
        hist.append({"quarter": q, "hunger_balance_luzon": nz(float(g["H"].iloc[0])) if g["H"].notna().any() else None,
                     "provinces": [{"code": r.province_code, "name": PROV[r.province_code], "F": nz(float(r.F)),
                                    "D": nz(float(r.D)) if complete else None,
                                    "S1": nz(float(r.S1)) if r.S1 == r.S1 else None} for r in g.itertuples()],
                     "complete_five": bool(complete)})
    cls_rows = []
    for key, r in m["classification"].items():
        h, s = key.split("|")
        for arm, v in r["arms"].items():
            cls_rows.append({"h": int(h[1:]), "set": s, "arm": arm, "quarters": r["n_quarters"], "accuracy": v["accuracy"],
                             "balanced_accuracy": v["balanced_accuracy"], "F1_HIGH": v["F1_HIGH"], "ROC_AUC": v["ROC_AUC"],
                             "HIGH": v["HIGH"], "LOW": v["LOW"], "TP": v["TP"], "FP": v["FP"], "FN": v["FN"], "TN": v["TN"]})
    sel = {k: {"selected": r["selection"]["selected"], "supported": r["selection"]["reliability_working_criterion_met"],
               "quarters": r["n_quarters"], "insufficient": r["selection"]["insufficient"],
               "test_HIGH": r["selection"]["test_HIGH"], "test_LOW": r["selection"]["test_LOW"]}
           for k, r in m["classification"].items() if "selection" in r}
    con_rows = []
    for key, r in m["continuous"].items():
        tg, h = key.split("|")
        for c, v in r["candidates"].items():
            con_rows.append({"target": tg, "h": int(h[1:]), "candidate": c, "origins": r["n_origins"], "MAE": v["MAE"],
                             "RMSE": v["RMSE"], "bias": v["bias"],
                             "selected": c == r.get("selection", {}).get("selected"), "evidence": r["evidence"]})
    out = {
        "generated_from_run": RUN.name,
        "status": "Development research view (E18). Not the production model; not deployed.",
        "caveats": [
            "Regional hunger is one SWS Balance-Luzon value per quarter, not a provincial measurement.",
            "Provincial food inflation and relative price pressure are price indicators, not food insecurity.",
            "The HIGH/LOW label is a constructed composite (hunger + 2 x relative price pressure > 14.6); it is not "
            "independently measured provincial food insecurity.",
            "A ranking always has a top province even when differences are small; D values are shown.",
            "No forecast horizon met the E18 reliability working criterion; all forecasts are research outputs.",
        ],
        "history": hist,
        "forecast_2027Q1": fc,
        "classification_metrics": cls_rows,
        "classification_selection": sel,
        "continuous_metrics": con_rows,
        "lead_time": {"max_supported": None,
                      "note": "No horizon met the E18 working criterion (selected model, >=8 test quarters, >=5 HIGH and "
                              ">=5 LOW cases). Chapter I does not define 'reliable'; adviser approval needed."},
    }
    dest = EXP / "dashboard_dev" / "public" / "e18_dashboard.json"
    dest.write_text(json.dumps(out, indent=1, default=lambda o: None), encoding="utf-8", newline="\n")
    print(dest, dest.stat().st_size)


if __name__ == "__main__":
    main()

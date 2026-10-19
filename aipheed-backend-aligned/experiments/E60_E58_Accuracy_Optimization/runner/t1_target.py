"""E60 step T1 (labels only, no model scores): what the T43 target measures and whether a stronger target exists.

    backend/venv/Scripts/python.exe -B runner/t1_target.py  -> out/target_analysis.json, out/target_by_quarter.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E60 = Path(__file__).resolve().parents[1]
EXP = E60.parent
sys.path.insert(0, str(EXP / "E55_Food_Insecurity_LightGBM" / "runner"))
import e55_lib as F  # noqa: E402

L, np, pd = F.L, F.np, F.pd


def main():
    d = L.load()
    th = L.e40_spec()
    Y = F.t43_labels(d)
    Y = Y[Y["T43"].notna()].copy()
    Y["food_hi"] = (Y["F"] > Y["province_code"].map(th["food"])).astype(int)
    Y["gap_hi"] = ((Y["F"] - Y["HL"]) > Y["province_code"].map(th["gap"])).astype(int)
    Y["hunger_hi"] = (Y["H_all"] > th["H"]).astype(int)
    Y["year"] = Y["q"] // 4
    ev = Y[(Y["q"] >= L.qi("2024-Q2")) & (Y["q"] <= L.qi("2026-Q3"))]
    q = Y.groupby("quarter").agg(H=("H_all", "first"), hunger_hi=("hunger_hi", "first"), PS_HIGH=("PS", "sum"),
                                 T43_HIGH=("T43", "sum"), food_hi=("food_hi", "sum"), gap_hi=("gap_hi", "sum"), n=("T43", "size"))
    v = Y["T43"].astype(float)
    within = float(((v - Y.groupby("q")["T43"].transform("mean")) ** 2).sum() / ((v - v.mean()) ** 2).sum())
    vev = ev["T43"].astype(float)
    within_ev = float(((vev - ev.groupby("q")["T43"].transform("mean")) ** 2).sum() / ((vev - vev.mean()) ** 2).sum())
    out = {
        "labelled_province_quarters": int(len(Y)), "labelled_quarters": int(Y["q"].nunique()),
        "T43_equals_PS": {"all": float((Y["T43"] == Y["PS"]).mean()), "evaluation_rows": float((ev["T43"] == ev["PS"]).mean()),
                          "rows_where_they_differ": int((Y["T43"] != Y["PS"]).sum()),
                          "quarters_where_they_differ": sorted(Y[Y["T43"] != Y["PS"]]["quarter"].unique().tolist())},
        "hunger_condition": {"quarters_above_11.3": int(q["hunger_hi"].sum()), "quarters": int(len(q)),
                             "state_changes": int((q["hunger_hi"].diff().abs() > 0).sum()),
                             "evaluation_quarters_above": int(ev.groupby("q")["hunger_hi"].first().sum())},
        "prevalence_by_year": Y.groupby("year").agg(T43=("T43", "mean"), PS=("PS", "mean"), n=("T43", "size")).round(3).to_dict("index"),
        "evaluation_rows": {"n": int(len(ev)), "HIGH": int(ev["T43"].sum()), "LOW": int((ev["T43"] == 0).sum()),
                            "quarters_with_both_classes": int((ev.groupby("q")["T43"].nunique() == 2).sum()),
                            "quarters_all_LOW": int((ev.groupby("q")["T43"].sum() == 0).sum())},
        "which_condition_makes_HIGH_eval": {"food_only": int(((ev["T43"] == 1) & (ev["food_hi"] == 1) & (ev["gap_hi"] == 0)).sum()),
                                            "gap_only": int(((ev["T43"] == 1) & (ev["food_hi"] == 0) & (ev["gap_hi"] == 1)).sum()),
                                            "both": int(((ev["T43"] == 1) & (ev["food_hi"] == 1) & (ev["gap_hi"] == 1)).sum())},
        "within_quarter_variance_share": {"all": within, "evaluation_rows": within_ev},
        "direct_outcomes_available": {
            "SWS hunger": "quarterly, Balance Luzon only (one value for all five provinces)",
            "PSA subsistence incidence": "provincial, 2021 and 2023 only",
            "FNRI FIES": "regional, survey years (CALABARZON 19.1% in 2023)",
            "CBMS / provincial FIES": "not available to the project"},
    }
    (E60 / "out").mkdir(exist_ok=True)
    q.to_csv(E60 / "out" / "target_by_quarter.csv")
    (E60 / "out" / "target_analysis.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
    print(q.to_string())


if __name__ == "__main__":
    main()

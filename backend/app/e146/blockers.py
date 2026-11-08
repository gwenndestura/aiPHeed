"""
Exact counts and arithmetic behind the reported blockers, from the locked outputs. Fits nothing.

    python -m app.e146.blockers -> data/e146/out/blockers.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import beta, spearmanr

from app.e141 import evaluate as E141
from app.e141 import panel as P
from app.e144 import OUT as O144
from app.e144 import link as L
from app.e145 import OUT as O145
from app.e146 import OUT


def cp(k, n):
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return [lo, hi]


def main():
    o = P.outcomes()
    cal = o[o["province"].isin(E141.CAL)]
    R5, R6, R4 = (json.loads((p / "results.json").read_text(encoding="utf-8")) for p in (O145, OUT, O144))
    out = {}
    quarters = pd.period_range("2013Q1", "2026Q3", freq="Q").size
    out["B1_labels"] = {"calabarzon_hfias_province_rounds": int(len(cal)), "possible_province_quarters_2013Q1_2026Q3": int(5 * quarters),
                        "measured_share": float(len(cal) / (5 * quarters)), "status_counts": cal["status"].value_counts().to_dict(), "rounds": int(o["survey"].nunique()), "rolling_origins": 3,
                        "panel_rows": int(len(o))}
    rows = L.rows()
    c2 = rows[rows["province"].isin(E141.CAL)]
    dec = np.abs(c2["y_abs"] - L.LT) > 1.645 * c2["se_abs"]
    out["B2_high_class_in_calabarzon"] = {"above_national_same_round_decisive": int((cal["status"] == "ELEVATED").sum()),
                                          "above_fixed_42_8_decisive": int(((c2["y_abs"] > L.LT) & dec).sum()), "fies_province_rounds_above_national": 0, "fies_province_rounds": 4}
    oof = pd.read_csv(O145 / "oof.csv")
    a = oof[(oof["lead"] == 1) & oof["province"].isin(E141.CAL)]
    d = a[a["status"].isin(["ELEVATED", "LOWER"])]
    k = int((d["C4"] < 0.5).sum())
    out["B2_calabarzon_test_rows"] = {"rows": int(len(a)), "decisive": int(len(d)), "correct_C4": k, "accuracy_ci95_exact": cp(k, len(d)), "always_low_correct": int(len(d)),
                                      "rank_rho_C4_vs_y_2015_n5": float(spearmanr(a[a["survey"] == "FNRI2015"]["C4"], a[a["survey"] == "FNRI2015"]["y"]).statistic)}
    x = oof[oof["lead"] == 1]
    out["B3_sampling_ceiling"] = {"oracle_expected_accuracy_all_rows": float(np.mean(np.maximum(x["q"], 1 - x["q"]))), "share_rows_not_decisive": float((~x["status"].isin(["ELEVATED", "LOWER"])).mean())}
    n = R5["by_lead"]["L1"]["news"]["FULL_minus_C4"]
    se = (n["ci95"][1] - n["ci95"][0]) / (2 * 1.96)
    out["B4_news_power"] = {"diff": n["diff"], "ci95": n["ci95"], "se": se, "mde_80pct_power": 2.8 * se, "evidence_multiple_needed": float((2.8 * se / abs(n["diff"])) ** 2),
                            "placebo_share_better_or_equal": R5["placebo_L1"]["share_placebo_better_or_equal"]}
    v = R5["by_lead"]["L1"]["vs_persistence"]["FULL"]
    se2 = (v["ci95"][1] - v["ci95"][0]) / (2 * 1.96)
    out["B5_persistence_power"] = {"FULL_minus_PERS": v["diff"], "ci95": v["ci95"], "mde_80pct_power": 2.8 * se2, "evidence_multiple_needed": float((2.8 * se2 / abs(v["diff"])) ** 2)}
    m = R6["by_lead"]["L1"]["metrics"]
    out["B6_trivial_rules_on_rows"] = {"E146_abs_42_8": {"model_accuracy": m["E2E-clean"]["accuracy"], "always_high": m["E2E-clean"]["n_high"] / m["E2E-clean"]["n_decisive"], "false_alarm_rate": m["E2E-clean"]["false_alarm_rate"]},
                                       "E145_relative": {"C4_accuracy": R5["by_lead"]["L1"]["metrics"]["C4"]["accuracy"], "always_high": 40 / 62, "persistence": R5["by_lead"]["L1"]["metrics"]["PERS"]["accuracy"]}}
    p1 = R4["primary"]["by_horizon"]["h1"]["metrics"]["A LightGBM (full)"]
    out["B7_quarterly_area"] = {"accuracy_h1": p1["accuracy"], "ece_h1": p1["ece"], "n": p1["n"], "base_rate_high": p1["n_high"] / p1["n"], "calabarzon_share_of_balance_luzon_population": 0.337}
    out["gamma_by_origin_clean"] = {p["origin"]: p["gamma"] for p in R6["params"] if p["lead"] == 1}
    (OUT / "blockers.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()

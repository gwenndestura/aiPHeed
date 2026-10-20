"""E67 r4 (PROTOCOL 5): El Nino trace per province for targets 2026-Q3 / 2026-Q4 / 2027-Q1. It joins the reproduced
E66 r5 inputs and contributions with the E67 R1 forward-origin ablations (P_price without each trigger group) and the
D-E66-5 typhoon sensitivity, and checks that the served E58 record equals A0 at the 2027-Q1 origin.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E67_Lead2_Best_Model_Objectives_1_4/runner/r4_el_nino.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e67_lib as K  # noqa: E402

H, L, np, pd = K.H, K.L, K.np, K.pd
R5 = K.EXP / "E66_Best_Methodology_Review" / "tables" / "r5_el_nino_province_q3_q4_q1.csv"
CFSW = K.EXP / "E66_Best_Methodology_Review" / "tables" / "r5_cfsw_forward.csv"
REC = H.BACKEND / "data" / "e58" / "e58_record.json"


def main():
    K.verify_protocol()
    T = pd.read_csv(R5)
    A = pd.read_csv(K.TABLES / "r1_ablation_predictions.csv", dtype={"province_code": str})
    A["province"] = A["province_code"].map(L.NAMES)
    A = A[A["target"].isin(["2026-Q3", "2026-Q4", "2027-Q1"])]
    wide = A.pivot_table(index=["target", "province"], columns="arm", values="p_price").add_prefix("p_price_").reset_index()
    cfg = A[A["arm"] == "A0"][["target", "province", "config", "p"]].rename(columns={"config": "A0_config", "p": "A0_p"})
    S = pd.read_csv(K.TABLES / "r1_typhoon_nan_sensitivity_2027Q1.csv")[["province", "tcNaN_p", "tcNaN_p_price"]]
    S["target"] = "2027-Q1"
    C = pd.read_csv(CFSW)[["target", "province", "level"]].rename(columns={"level": "CFSW"})
    M = (T.merge(wide, on=["target", "province"], how="left").merge(cfg, on=["target", "province"], how="left")
         .merge(S, on=["target", "province"], how="left").merge(C, on=["target", "province"], how="left"))
    M["CFSW"] = M["CFSW"].fillna("not in force at issue (only an El Nino Watch before 2026-04-01)")
    M["A0_equals_E66_P"] = (M["A0_p"] - M["P"]).abs() < 1e-6
    assert M["A0_equals_E66_P"].all(), "A0 differs from the E66 r5 reproduction"
    M["max_p_price_any_ablation"] = M[[c for c in M.columns if c.startswith("p_price_")]].max(axis=1)
    M["food_projection_gap_to_threshold"] = M["threshold_food"] - M["food_projection"]
    rec = json.loads(REC.read_text(encoding="utf-8"))
    served = {v["name"]: v["forecast"]["probability"] for v in rec["provinces"].values()}
    q1 = M[M["target"] == rec["targetQuarter"]]
    err = float(max(abs(served[r.province] - r.A0_p) for r in q1.itertuples()))
    assert err < 1e-6, f"served E58 record differs from A0 ({err})"
    keep = ["province", "target", "issue_date", "A0_config", "P", "P_hunger", "P_price", "sws_latest_posted_H", "cpi_through",
            "food_yoy_latest", "headline_yoy_latest", "food_projection", "threshold_food", "food_projection_gap_to_threshold",
            "gap_projection", "threshold_gap", "offset_logit_cpi_projection", "trees_cpi_market", "trees_climate",
            "trees_employment", "trees_ofw_fx", "enso", "enso_l2", "tc_count", "palay_yoy", "corn_yoy",
            "remittance_input_missing", "CFSW", "p_price_A0", "p_price_X_climate", "p_price_X_news", "p_price_X_employment",
            "p_price_X_ofw", "p_price_X_fish", "p_price_M_only", "max_p_price_any_ablation", "tcNaN_p", "observed_T43"]
    H.write_csv(M[keep], K.TABLES / "r4_el_nino_trace.csv")
    H.dump({"protocol_sha256": K.verify_protocol(), "served_record_vs_A0_max_abs_diff": err,
            "max_p_price_any_ablation_2027Q1": float(q1["max_p_price_any_ablation"].max()),
            "max_p_price_any_ablation_2026Q4": float(M[M["target"] == "2026-Q4"]["max_p_price_any_ablation"].max())},
           K.OUT / "r4_el_nino.json")
    pd.set_option("display.width", 250)
    print(M[["province", "target", "P", "P_price", "food_projection", "threshold_food", "gap_projection", "threshold_gap",
             "p_price_X_climate", "p_price_M_only", "max_p_price_any_ablation", "CFSW"]].round(3).to_string())


if __name__ == "__main__":
    main()

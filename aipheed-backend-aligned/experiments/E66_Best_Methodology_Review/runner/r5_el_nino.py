"""E66 r5 (PROTOCOL 2.5, 4): El Nino. (a) Province-by-province 2026-Q3 / 2026-Q4 / 2027-Q1 table from the served E58
record and the E65 trace; (b) the Climate Food-Stress Watch (CFSW) at every issue date 2021-10-01..2026-10-01 from
information dated before the issue date; (c) CFSW against later outcomes (descriptive only).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E66_Best_Methodology_Review/runner/r5_el_nino.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e66_lib as H  # noqa: E402

sys.path.insert(0, str(H.EXP / "E65_El_Nino_Risk_Drop_Audit" / "runner"))
import e65_lib as E65  # noqa: E402

np, pd = H.np, H.pd
L = E65.L
sys.path.insert(0, str(H.BACKEND))
from app.ml.inference import climate_watch as CW  # noqa: E402

TRACE = H.EXP / "E65_El_Nino_Risk_Drop_Audit" / "tables" / "r1_trace_by_province.csv"
RECORD = H.BACKEND / "data" / "e58" / "e58_record.json"
N_ARMS = H.TABLES / "r2_new_arm_predictions.csv"


def province_table() -> pd.DataFrame:
    T = pd.read_csv(TRACE, dtype={"province_code": str})
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    N = pd.read_csv(N_ARMS, dtype={"province_code": str})
    served = {}
    for code, p in rec["provinces"].items():
        for f in p["pastForecasts"]:
            served[(code, f["targetQuarter"])] = f["probability"]
        for f in p.get("earlierForecasts", []):
            served[(code, f["targetQuarter"])] = f["probability"]
        served[(code, p["forecast"]["targetQuarter"])] = p["forecast"]["probability"]
    T["P_served_e58_record"] = [served.get((c, q)) for c, q in zip(T["province_code"], T["target"])]
    T = T.merge(N[["target", "province_code", "N2_p_price", "N2_p"]].rename(
        columns={"N2_p_price": "N2_LR_proj_p_price", "N2_p": "N2_LR_proj_p"}), on=["target", "province_code"], how="left")
    cols = ["province", "target", "issue_date", "config", "P", "P_served_e58_record", "P_hunger", "P_price",
            "sws_latest_posted_H", "sws_latest_posted_quarter", "cpi_through", "food_yoy_latest", "headline_yoy_latest",
            "gap_latest", "food_projection", "threshold_food", "gap_projection", "threshold_gap",
            "offset_logit_cpi_projection", "trees_cpi_market", "trees_climate", "trees_employment", "trees_ofw_fx",
            "enso", "enso_l2", "tc_count", "palay_yoy", "corn_yoy", "remittance_input_missing", "observed_T43",
            "observed_food_yoy", "observed_headline_yoy", "observed_hunger", "N2_LR_proj_p_price", "N2_LR_proj_p"]
    T = T[cols].sort_values(["province", "target"]).reset_index(drop=True)
    T["dlogP_from_prev_target"] = T.groupby("province")["P"].transform(lambda s: np.log(s).diff())
    return T


def watch_history() -> pd.DataFrame:
    import e56_lib as G  # noqa: F401  (path set by e65_lib)
    d, X, B = E65.E.load()
    lab = pd.read_csv(H.LABELS, dtype={"province_code": str})
    lab["qi"] = lab["quarter"].map(L.qi)
    rows = []
    for t in range(L.qi("2021-Q4"), L.qi("2026-Q3") + 1):
        issue = str(L.origin(t).date())
        x = X[X["t"] == t].set_index("province_code")
        for p in L.PROVS:
            r = x.loc[p] if p in x.index else None
            h_last = float(r["H_last"]) if r is not None and pd.notna(r["H_last"]) else None
            w = CW.watch(issue, h_last,
                         None if r is None or pd.isna(r["palay_yoy"]) else float(r["palay_yoy"]),
                         None if r is None or pd.isna(r["corn_yoy"]) else float(r["corn_yoy"]))
            out = lab[(lab["province_code"] == p) & (lab["qi"] == t + 2)]
            rows.append({"origin_quarter": L.qs(t), "issue_date": issue, "target": L.qs(t + 2), "province_code": p,
                         "province": L.NAMES[p], "hazard": w["hazard"], "hazard_status": w["hazardStatus"],
                         "latest_hunger": h_last, "palay_yoy_known": None if r is None else r["palay_yoy"],
                         "corn_yoy_known": None if r is None else r["corn_yoy"], "level": w["level"],
                         "e65_status_code": E65.PAGASA_STATUS.get(issue, (np.nan, ""))[0],
                         "T43_target": float(out["T43"].iloc[0]) if len(out) and pd.notna(out["T43"].iloc[0]) else None,
                         "PS_target": float(out["PS"].iloc[0]) if len(out) else None,
                         "H_target": float(out["H_all"].iloc[0]) if len(out) and pd.notna(out["H_all"].iloc[0]) else None,
                         "food_yoy_target": float(out["F"].iloc[0]) if len(out) else None})
    W = pd.DataFrame(rows)
    # consistency of the backend hazard rule with E65's independently coded status (Alert/Advisory = +1/+2)
    W["e65_hazard"] = W["e65_status_code"] >= 1
    return W


def main():
    H.verify_protocol()
    T = province_table()
    H.write_csv(T, H.TABLES / "r5_el_nino_province_q3_q4_q1.csv")
    W = watch_history()
    H.write_csv(W, H.TABLES / "r5_cfsw_history.csv")
    mism = W[W["hazard"] != W["e65_hazard"]][["issue_date", "hazard_status", "e65_status_code"]].drop_duplicates()
    W["watch"] = W["level"].str.startswith("CLIMATE WATCH")
    W["H_change"] = W["H_target"] - W["latest_hunger"]
    obs = W[W["PS_target"].notna()]
    desc = []
    for k, g in obs.groupby("watch"):
        desc.append({"watch": bool(k), "rows": int(len(g)), "quarters": int(g["target"].nunique()),
                     "T43_HIGH_rate": float(g["T43_target"].mean()), "PS_rate": float(g["PS_target"].mean()),
                     "mean_food_yoy_target": float(g["food_yoy_target"].mean()),
                     "mean_hunger_target": float(g["H_target"].mean()),
                     "mean_hunger_change_vs_latest": float(g["H_change"].mean())})
    D = pd.DataFrame(desc)
    H.write_csv(D, H.TABLES / "r5_cfsw_vs_outcomes.csv")
    fwd = W[W["target"].isin(["2026-Q4", "2027-Q1"])][["target", "issue_date", "province", "level", "hazard_status",
                                                        "latest_hunger", "palay_yoy_known", "corn_yoy_known"]]
    H.write_csv(fwd, H.TABLES / "r5_cfsw_forward.csv")
    H.dump({"protocol_sha256": H.verify_protocol(), "hazard_rule_mismatches_vs_e65": mism.to_dict("records"),
            "watch_issue_dates": sorted(W.loc[W["watch"], "issue_date"].unique().tolist()),
            "cfsw_vs_outcomes": D.to_dict("records"), "forward": fwd.to_dict("records"),
            "note": "Descriptive only: one El Nino episode (2023-24) in the window; CFSW is a hazard watch, not a "
                    "forecast of T43 or of food insecurity."}, H.OUT / "r5_el_nino.json")
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(T[["province", "target", "P", "P_served_e58_record", "P_hunger", "P_price", "food_yoy_latest", "headline_yoy_latest",
             "food_projection", "threshold_food", "gap_projection", "threshold_gap", "N2_LR_proj_p"]].round(3).to_string(index=False))
    print("hazard mismatches vs E65:", mism.to_string(index=False))
    print(D.round(3).to_string(index=False))
    print(fwd.to_string(index=False))


if __name__ == "__main__":
    main()

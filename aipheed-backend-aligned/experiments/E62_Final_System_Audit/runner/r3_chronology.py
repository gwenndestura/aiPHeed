"""E62 r3: chronological forecast-versus-observation table per province, and the decomposition of every change between
consecutive forecasts (the 2027-Q1 drop included).

For each province and each Lead-2 forecast of the served E58/E56 procedure (10 rolling-origin back-tests, targets
2024-Q2..2026-Q3; the earlier live-style forecast for 2026-Q4; the issued 2027-Q1 forecast):
  * issue date, target, model configuration selected at that origin, P(HIGH), P_hunger, P_price, warning level;
  * the as-of inputs the model saw (rebuilt with the E56 library at that origin: latest food and headline YoY, gap,
    CPI projection, rice wholesale YoY, unemployment change, remittance availability, news volume and shares,
    latest posted SWS hunger and its age);
  * the observed outcome (labels recomputed from raw files in r1) and the observed food / headline / hunger values;
  * the change from the previous forecast, decomposed exactly:
        delta log P(HIGH) = delta log P_hunger + delta log P_price
        delta logit P_price = delta CPI-projection offset + delta tree baseline + sum over groups of delta tree effect
    using the served record's own per-origin TreeSHAP attributions (pastDrivers / forecast).

Consistency checks: the record's back-test probabilities equal the sealed E57 file; the record's attribution adds up to
its P_price at every origin.

    backend/venv/Scripts/python.exe -B runner/r3_chronology.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E62 = Path(__file__).resolve().parents[1]
EXP = E62.parent
ROOT = EXP.parents[1]
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
RECORD = ROOT / "backend" / "data" / "e58" / "e58_record.json"
S57 = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"
LAB = E62 / "tables" / "r1_labels_independent.csv"
GROUPS = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]


def logit(p):
    p = min(max(float(p), 1e-9), 1 - 1e-9)
    return math.log(p / (1 - p))


def record_entries(rec: dict) -> pd.DataFrame:
    rows = []
    for code, v in rec["provinces"].items():
        blocks = dict(v["pastDrivers"])
        f = v["forecast"]
        blocks[rec["targetQuarter"]] = {
            "origin": rec["origin"], "originQuarter": rec["originQuarter"], "probability": f["probability"],
            "probabilityPricePressure": f["components"]["probabilityPricePressure"],
            "probabilityHungerElevated": f["components"]["probabilityHungerElevated"],
            "modelConfig": v["modelConfig"], "fiveTriggerContributions": v["fiveTriggerContributions"],
            "otherContribution": v["otherContribution"], "povertyContribution": v["povertyContribution"],
            "baselineLogOdds": v["baselineLogOdds"], "hungerGate": v["hungerGate"], "earlyWarning": v["earlyWarning"]}
        for q, b in blocks.items():
            c = b["fiveTriggerContributions"]
            r = {"province_code": code, "province": v["name"], "target": q, "issue_date": b["origin"],
                 "origin_quarter": b["originQuarter"], "rec_p": b["probability"],
                 "rec_p_price": b["probabilityPricePressure"], "rec_p_hunger": b["probabilityHungerElevated"],
                 "config_id": b["modelConfig"]["id"], "config_m": b["modelConfig"]["m"],
                 "config_feat": b["modelConfig"]["feat"], "config_trees": b["modelConfig"]["trees"],
                 "baseline_logodds": b["baselineLogOdds"],
                 "cpi_projection_logodds": c["market"].get("cpiProjectionLogOdds", 0.0),
                 "market_tree_logodds": c["market"]["logOddsEffect"] - c["market"].get("cpiProjectionLogOdds", 0.0),
                 "other_news_n_logodds": b["otherContribution"]["logOddsEffect"],
                 "poverty_logodds": b["povertyContribution"]["logOddsEffect"],
                 "forecast_H": b["hungerGate"]["forecastH"],
                 "warning": (b.get("earlyWarning") or {}).get("level")}
            for g in GROUPS[1:]:
                r[f"{g}_logodds"] = c[g]["logOddsEffect"]
            r["attribution_sum_logit"] = (r["baseline_logodds"] + r["cpi_projection_logodds"] + r["market_tree_logodds"]
                                          + sum(r[f"{g}_logodds"] for g in GROUPS[1:]) + r["other_news_n_logodds"]
                                          + r["poverty_logodds"])
            r["attribution_check_abs_err"] = abs(1 / (1 + math.exp(-r["attribution_sum_logit"])) - r["rec_p_price"])
            rows.append(r)
    return pd.DataFrame(rows)


def asof_inputs(d, X, B, t: int) -> pd.DataFrame:
    _, te = F.frame(d, X, B, t, "AS")
    dc = d.cut(t)
    sws = dc.sws.sort_values("published")
    last = sws.iloc[-1]
    te = te.copy()
    out = pd.DataFrame({
        "province_code": te["province_code"].to_numpy(),
        "cpi_through": L.ym_s(L.m0_of(t)),
        "food_yoy_latest": te["F_now"].round(2), "headline_yoy_latest": (te["F_now"] - te["gap_now"]).round(2),
        "gap_latest": te["gap_now"].round(2), "food_yoy_projected_m0": te["base_0.0"].round(2),
        "gap_projected_m0": te["gbase_0.0"].round(2), "food_yoy_projected_m1": te["base_1.0"].round(2),
        "rice_wholesale_yoy_prevq": te["rice_whsl_yoy"].round(1), "unemployment_change_pts": te["ur_yoy"].round(2),
        "remittance_input_missing": te["remit_usd_yoy"].isna().to_numpy(),
        "news_articles_q": te["news_n"].to_numpy(), "news_market_share": te["news_market"].round(3),
        "news_climate_share": te["news_climate"].round(3), "news_fish_kill_share": te["news_fish_kill"].round(3),
        "news_employment_share": te["news_employment"].round(3), "news_ofw_share": te["news_ofw_remittance"].round(3),
        "sws_latest_posted_H": float(last["H"]), "sws_latest_posted_quarter": L.qs(int(last["q"])),
        "sws_latest_posted_on": str(pd.Timestamp(last["published"]).date()), "sws_age_quarters": t - int(last["q"])})
    return out


def main():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    R = record_entries(rec)
    s57 = pd.read_csv(S57, dtype={"province_code": str})
    chk = R.merge(s57[["target", "province_code", "E56_p", "E56_p_price", "E56_config"]], on=["target", "province_code"])
    rec_vs_sealed = {"rows": int(len(chk)), "max_abs_diff_p": float((chk["rec_p"] - chk["E56_p"]).abs().max()),
                     "max_abs_diff_p_price": float((chk["rec_p_price"] - chk["E56_p_price"]).abs().max()),
                     "config_mismatches": int((chk["config_id"] != chk["E56_config"]).sum())}
    d, X, B = E.load()
    ins = []
    for oq in sorted(R["origin_quarter"].unique(), key=L.qi):
        t = L.qi(oq)
        ins.append(asof_inputs(d, X, B, t).assign(origin_quarter=oq))
    I = pd.concat(ins)
    lab = pd.read_csv(LAB, dtype={"province_code": str}).rename(columns={"quarter": "target"})
    C = R.merge(I, on=["province_code", "origin_quarter"]).merge(
        lab[["target", "province_code", "T43", "PS", "F", "HL", "G", "H_all"]], on=["target", "province_code"], how="left")
    C = C.rename(columns={"T43": "observed_T43", "PS": "observed_PS", "F": "observed_food_yoy",
                          "HL": "observed_headline_yoy", "G": "observed_gap", "H_all": "observed_hunger"})
    C["kind"] = np.where(C["target"] == rec["targetQuarter"], "issued forecast (outcome unknown)",
                         np.where(C["target"] == "2026-Q4", "earlier forecast (outcome unknown)", "rolling-origin back-test"))
    C["qi"] = C["target"].map(L.qi)
    C = C.sort_values(["province", "qi"]).reset_index(drop=True)
    # change from the previous comparable forecast (previous target of the same procedure, same province)
    dec = []
    for _, g in C.groupby("province"):
        g = g.sort_values("qi")
        prev = None
        for i, r in g.iterrows():
            row = {"idx": i}
            if prev is not None:
                row.update({
                    "delta_p": r["rec_p"] - prev["rec_p"],
                    "delta_log_p_hunger": math.log(r["rec_p_hunger"]) - math.log(prev["rec_p_hunger"]),
                    "delta_log_p_price": math.log(r["rec_p_price"]) - math.log(prev["rec_p_price"]),
                    "delta_logit_p_price": logit(r["rec_p_price"]) - logit(prev["rec_p_price"]),
                    "d_cpi_projection": r["cpi_projection_logodds"] - prev["cpi_projection_logodds"],
                    "d_tree_baseline": r["baseline_logodds"] - prev["baseline_logodds"],
                    "d_trees_market": r["market_tree_logodds"] - prev["market_tree_logodds"],
                    "d_trees_nonmarket": sum(r[f"{x}_logodds"] - prev[f"{x}_logodds"] for x in GROUPS[1:])
                    + (r["other_news_n_logodds"] - prev["other_news_n_logodds"]) + (r["poverty_logodds"] - prev["poverty_logodds"]),
                    "d_food_yoy_latest": r["food_yoy_latest"] - prev["food_yoy_latest"],
                    "d_gap_latest": r["gap_latest"] - prev["gap_latest"],
                    "config_changed": r["config_id"] != prev["config_id"],
                    "drift_m_changed": r["config_m"] != prev["config_m"]})
            dec.append(row)
            prev = r
    D = pd.DataFrame(dec).set_index("idx")
    C = C.join(D)
    C["error_y_minus_p"] = C["observed_T43"] - C["rec_p"]
    C["large_change_flag"] = C["delta_p"].abs() >= 0.25
    cols = ["province", "target", "kind", "issue_date", "origin_quarter", "config_id", "config_m", "config_feat",
            "rec_p", "rec_p_hunger", "rec_p_price", "warning", "observed_T43", "error_y_minus_p", "observed_food_yoy",
            "observed_headline_yoy", "observed_gap", "observed_hunger", "cpi_through", "food_yoy_latest",
            "headline_yoy_latest", "gap_latest", "food_yoy_projected_m0", "gap_projected_m0", "rice_wholesale_yoy_prevq",
            "unemployment_change_pts", "remittance_input_missing", "news_articles_q", "news_market_share",
            "news_climate_share", "news_fish_kill_share", "sws_latest_posted_H", "sws_latest_posted_quarter",
            "sws_latest_posted_on", "sws_age_quarters", "forecast_H", "delta_p", "delta_log_p_hunger", "delta_log_p_price",
            "delta_logit_p_price", "d_cpi_projection", "d_tree_baseline", "d_trees_market", "d_trees_nonmarket",
            "d_food_yoy_latest", "d_gap_latest", "config_changed", "drift_m_changed", "large_change_flag",
            "attribution_check_abs_err"]
    C[cols].to_csv(E62 / "tables" / "r3_chronology_by_province.csv", index=False, float_format="%.4f", lineterminator="\n")
    # region view: mean of the five provinces (the dashboard's region aggregation for this record)
    Rg = C.groupby(["target", "kind", "issue_date"]).agg(
        mean_p=("rec_p", "mean"), min_p=("rec_p", "min"), max_p=("rec_p", "max"), p_hunger=("rec_p_hunger", "first"),
        mean_p_price=("rec_p_price", "mean"), HIGH_observed=("observed_T43", "sum"),
        mean_food_yoy_latest=("food_yoy_latest", "mean"), mean_gap_latest=("gap_latest", "mean"),
        mean_rice_whsl_yoy=("rice_wholesale_yoy_prevq", "mean"), sws_latest=("sws_latest_posted_H", "first"),
        configs=("config_id", lambda s: sorted(set(int(x) for x in s))), drift_m=("config_m", "first"),
    ).reset_index()
    Rg["qi"] = Rg["target"].map(L.qi)
    Rg = Rg.sort_values("qi").drop(columns="qi")
    Rg["delta_mean_p"] = Rg["mean_p"].diff()
    Rg.to_csv(E62 / "tables" / "r3_chronology_region.csv", index=False, float_format="%.4f", lineterminator="\n")
    big = C[C["large_change_flag"] == True]  # noqa: E712
    res = {"record_vs_sealed_E57": rec_vs_sealed,
           "max_attribution_check_error": float(C["attribution_check_abs_err"].max()),
           "large_changes": big[["province", "target", "delta_p", "delta_log_p_hunger", "delta_logit_p_price",
                                 "d_cpi_projection", "d_trees_market", "d_trees_nonmarket", "d_tree_baseline",
                                 "config_changed", "d_food_yoy_latest", "d_gap_latest"]].round(3).to_dict("records")}
    (E62 / "out" / "r3_chronology.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(json.dumps(res["record_vs_sealed_E57"]), res["max_attribution_check_error"])
    print(Rg.to_string())
    print(big[["province", "target", "rec_p", "delta_p", "delta_log_p_hunger", "delta_logit_p_price", "d_cpi_projection",
               "d_trees_market", "d_trees_nonmarket", "d_tree_baseline", "config_changed"]].round(3).to_string())
    last = C[C["target"].isin(["2026-Q3", "2026-Q4", "2027-Q1"])]
    print(last[["province", "target", "rec_p", "rec_p_hunger", "rec_p_price", "config_id", "config_m", "food_yoy_latest",
                "gap_latest", "rice_wholesale_yoy_prevq", "delta_p", "delta_logit_p_price", "d_cpi_projection",
                "d_trees_market", "d_trees_nonmarket", "d_tree_baseline"]].round(3).to_string())


if __name__ == "__main__":
    main()

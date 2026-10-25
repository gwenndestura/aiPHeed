"""Export the final forecasting engine for the backend (backend/data/final_engine/). Nothing is refitted here: every
number comes from the frozen FINAL / FINAL_OBJECTIVE_ACHIEVEMENT outputs, the verified SWS file, PSA CPI and the news
corpus, so the served values reproduce the reported ones.

    python export_engine.py [--as-of 2026-10-25]
"""
from __future__ import annotations

import json
import shutil
import sys

import oa_lib as O

M, NF, np, pd = O.M, O.NF, O.np, O.pd
FINAL = O.EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM"
DEST = O.EXP.parents[1] / "backend" / "data" / "final_engine"
AS_OF = sys.argv[sys.argv.index("--as-of") + 1] if "--as-of" in sys.argv else "2026-10-25"
DRIVER_GROUPS = {"Market and prices": ["A1", "A2", "A3"], "Climate and food production": ["C1", "C2", "C3", "C4"],
                 "Employment and remittances": ["E1", "E2"], "News": ["N1"], "Poverty and vulnerability": ["V1"],
                 "Regional hunger history (SWS)": ["H1", "H (hunger history)"]}
PROV = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
        "PH040500000": "Batangas"}


def _j(p):
    return json.loads(p.read_text(encoding="utf-8"))


def sws_block() -> dict:
    r = pd.read_csv(FINAL / "data" / "sws_area_rounds_2021.csv")
    rows = []
    for x in r.itertuples():
        fw_end = M._fw_end(x.fieldwork)
        rows.append({"quarter": x.quarter, "fieldwork": x.fieldwork, "published": x.published,
                     "respondentBase": x.respondent_base, "national": x.national, "ncr": x.metro_manila,
                     "balanceLuzon": x.balance_luzon, "visayas": x.visayas, "mindanao": x.mindanao,
                     "balanceLuzonMarginPts": x.area_moe_bl, "otherAreaMarginPts": x.area_moe_other,
                     "publicationDelayDays": (pd.Timestamp(x.published) - pd.Timestamp(fw_end)).days,
                     "source": x.source})
    pub = [x for x in rows if x["published"] <= AS_OF]
    last = pub[-1]
    fw_end = M._fw_end(last["fieldwork"])
    return {"measure": "SWS involuntary ('Total') hunger: % of families who experienced hunger at least once in the "
                       "past three months", "geography": "SWS areas: NCR, Balance Luzon (contains CALABARZON), Visayas,"
                       " Mindanao. No province or municipality is surveyed separately.",
            "latest": {**last, "fieldworkEnd": fw_end,
                       "ageDaysAtAsOf": (pd.Timestamp(AS_OF) - pd.Timestamp(fw_end)).days},
            "asOf": AS_OF, "rounds": rows,
            "notes": ["Respondents were household heads until December 2024 and adults from April 2025; there is no "
                      "bridging round.", "The commissioned March 2025 (Stratbase) voter round is excluded.",
                      "SWS publishes 17-99 days after fieldwork (median 42)."]}


def outlook_block(sws: dict) -> dict:
    """Persistence outlook from the latest published reading, with empirical 80% ranges by true horizon, and the
    sealed FIL-OA LightGBM forecasts issued 2026-10-01."""
    P = pd.read_csv(O.OUT / "panel_features.csv")
    P = P[P["y"].notna()]
    err = P["y"] - P["h_last"]
    bands = {int(h): [float(np.quantile(err[P["true_horizon"] == h], 0.1)),
                      float(np.quantile(err[P["true_horizon"] == h], 0.9)), int((P["true_horizon"] == h).sum())]
             for h in range(1, 6) if (P["true_horizon"] == h).sum() >= 10}
    last = sws["latest"]
    lq = M.qi(last["quarter"])
    areas = {"NCR": "ncr", "BL": "balanceLuzon", "VIS": "visayas", "MIN": "mindanao"}
    pers = []
    for a, key in areas.items():
        h0 = float(last[key])
        for h in range(1, 5):
            if h in bands:
                pers.append({"area": a, "targetQuarter": M.qs(lq + h), "trueHorizon": h, "level": h0,
                             "range80": [round(h0 + bands[h][0], 1), round(h0 + bands[h][1], 1)],
                             "basisRows": bands[h][2]})
    S = pd.read_csv(O.OUT / "sealed_prospective.csv")
    fil = S[S["model"] == "FIL-OA"]
    lgbm = [{"area": r.area, "issueDate": r.issue_date, "lead": int(r.lead), "targetQuarter": r.target_quarter,
             "newestSwsQuarterUsed": r.sws_newest_q, "forecastLevel": float(r.forecast_level),
             "referenceLevel": float(r.ref_hat), "elevatedScore": float(r.p_elevated)} for r in fil.itertuples()]
    return {"persistence": pers, "persistenceBandsByTrueHorizon": {str(k): v for k, v in bands.items()},
            "lightgbm": lgbm,
            "status": "No forecast horizon is established as reliable. The latest-reading outlook is the evaluated "
                      "best method on 2021-2026; the LightGBM forecast is shown as a research output.",
            "elevatedScoreNote": "elevatedScore is the model's score for 'hunger above its previous-year average'. It "
                                 "is not a calibrated probability: its Brier score did not beat climatology (R4)."}


def evaluation_block() -> dict:
    res = _j(O.OUT / "results_primary.json")
    ver = _j(O.OUT / "results_verify.json")
    R = pd.read_csv(O.OUT / "predictions_primary.csv")
    leads = []
    for k in O.LEADS:
        d = res["FIL_OA"][str(k)]
        D = R[R["lead"] == k]
        e1, e0 = (D["FIL_level"] - D["y"]).abs(), (D["h_last"] - D["y"]).abs()
        bt = M.boot_diff(D, e1.to_numpy(), e0.to_numpy())
        b = d["baselines"]
        leads.append({"lead": k, "rows": d["n"], "targetQuarters": d["quarters"], "metrics": d["metrics"],
                      "baselineAccuracy": {n: v["accuracy"] for n, v in b.items()},
                      "baselineBalancedAccuracy": {n: v["balanced_accuracy"] for n, v in b.items()},
                      "maePts": d["mae"], "persistenceMaePts": d["mae_persist"],
                      "rmsePts": float(np.sqrt(((D["FIL_level"] - D["y"]) ** 2).mean())),
                      "persistenceRmsePts": float(np.sqrt(((D["h_last"] - D["y"]) ** 2).mean())),
                      "maeVsPersistence": {"diff": bt["diff"], "pOneSided": bt["p_less"]},
                      "criteria": d["criteria"], "reliable": d["pass"]})
    variants = {n: {str(k): (v[str(k)]["metrics"]["accuracy"] if v[str(k)].get("metrics") else None) for k in O.LEADS}
                for n, v in res["variants"].items()}
    plac = _j(O.OUT / "results_placebo.json") if (O.OUT / "results_placebo.json").exists() else None
    fin = _j(FINAL / "out" / "results_long.json")
    add1 = _j(FINAL / "out" / "results_addendum1.json")
    return {"model": "FIL-OA: one LightGBM regressor, pooled over 4 SWS areas and Leads 0-4, all 12 indicator "
                     "families; learns the change from the latest SWS reading",
            "target": "SWS involuntary hunger by area (continuous, percentage points) and ELEVATED = hunger above the "
                      "area's average of the previous four quarters (researcher-defined, not an SWS/PSA class)",
            "accuracyTarget": 0.75, "accuracyTargetReached": False,
            "maxReliableLead": res["max_reliable_lead"], "leads": leads, "variantsAccuracy": variants,
            "newsAblation": res["S3_news_ablation"], "newsPlacebo": plac, "surges": res["S2_surges"],
            "leaveOneQuarterOut": res["S1_loqo"], "shapShare": res["shap_share"],
            "ceiling": {"testRetest": {k: ver["V1_test_retest"][k] for k in ("n_pairs_with_label", "agreement",
                                                                             "mean_abs_diff")},
                        "simulationValidated": ver["V2_ceiling_validated"], "simulationShareInside": ver["V2_share_inside"],
                        "bayesAccuracyByTrueHorizon": {h: v["bayes"]["mean"] for h, v in ver["V2_simulated"].items()},
                        "nullBootstrapRejection": ver["V3_null_bootstrap"]["rejection_rate_at_0.10"]},
            "longHistorySecondary": {"untouched_2003_2020_accuracy": {k: fin["untouched_2003_2020"][k]["metrics"]["accuracy"]
                                                                       for k in ("1", "2", "3", "4")},
                                     "bayesRandomWalk": add1["simulation_mean"]["random_walk"],
                                     "flag": "uses pre-2021 SWS; secondary, needs adviser approval"},
            "evidenceStatus": "Development evidence: every 2021-2026 quarter was examined in E107-E114; untouched "
                              "confirmation needs the sealed forecasts to be scored from SWS 2026-Q4 onward."}


def archive_rows() -> pd.DataFrame:
    R = pd.read_csv(O.OUT / "predictions_primary.csv")
    A = pd.DataFrame({
        "kind": "retrospective (walk-forward, development)", "model": "FIL-OA", "area": R["area_name"],
        "issue_date": R["issue_date"], "lead": R["lead"], "target_quarter": R["target_quarter"],
        "true_horizon": R["true_horizon"], "sws_newest_quarter": R["sws_newest_q"],
        "sws_newest_published": R["sws_newest_published"], "psa_newest_month": R["psa_newest_month"],
        "news_latest_published": R["gkg_latest_published"], "h_age_days": R["h_age_days"],
        "forecast_level": R["FIL_level"].round(2), "persistence_level": R["h_last"], "actual_level": R["y"],
        "reference_level": R["ref_hat"].round(2), "forecast_elevated": (R["FIL_p"] > 0.5).astype(int),
        "actual_elevated": R["label"].astype(int)})
    seals = []
    for name, p in (("FIL-OA", O.OUT / "sealed_prospective.csv"),
                    ("FINAL", FINAL / "out" / "sealed_prospective.csv")):
        S = pd.read_csv(p)
        seals.append(pd.DataFrame({
            "kind": f"prospective (sealed, sha256 {M.sha256(p)[:12]})", "model": S["model"], "area": S["area"],
            "issue_date": S["issue_date"], "lead": S["lead"], "target_quarter": S["target_quarter"],
            "sws_newest_quarter": S["sws_newest_q"], "forecast_level": S["forecast_level"],
            "persistence_level": S["persistence_level"], "reference_level": S["ref_hat"],
            "forecast_elevated": (S["p_elevated"] > 0.5).astype(int)}))
    return pd.concat([A] + seals, ignore_index=True)


def seals_index() -> list[dict]:
    out = []
    for p in sorted(O.EXP.glob("*/out/sealed_prospective*.csv")):
        h = p.with_name(p.name + ".sha256")
        out.append({"experiment": p.parent.parent.name, "file": p.name,
                    "sha256": h.read_text().split()[0] if h.exists() else M.sha256(p),
                    "verified": (not h.exists()) or M.sha256(p) == h.read_text().split()[0]})
    return out


def news_rows() -> pd.DataFrame:
    d = NF.NI.corpus_frame()
    c = NF.corpus().set_index("article_key")
    d = d.set_index("article_key")
    d["anticipatory"], d["event_dup"] = c["anticipatory"], c["event_dup"]
    d = d[d[NF.CATS].any(axis=1) & ~d["event_dup"].astype(bool) & (d["published"] < pd.Timestamp(AS_OF))]
    d = d[d["published"] >= pd.Timestamp(AS_OF) - pd.Timedelta(days=365)].reset_index()
    return pd.DataFrame({
        "published": d["published"].dt.strftime("%Y-%m-%d"), "outlet": d["outlet"], "title": d["title"],
        "link": d["link"], "province": d["province_code"].map(PROV),
        "categories": d[NF.CATS].apply(lambda r: ";".join(k for k in NF.CATS if r[k]), axis=1),
        "kind": np.where(d["anticipatory"].astype(bool), "possible future risk (forward-looking wording)",
                         "reported event")}).sort_values("published", ascending=False)


def cpi_block() -> dict:
    g = pd.read_csv(FINAL / "out" / "psa_fpd_province_quarter.csv")
    d, _ = M.E.data()
    y = d.yoy.pivot_table(index=["province_code", "ym"], columns="commodity", values="yoy").reset_index()
    m0 = int(y["ym"].max())
    last = y[y["ym"] == m0]
    return {"definition": "Food-price squeeze (FPD) = province food CPI YoY minus all-items CPI YoY (PSA, 2018=100); "
                          "> 0 means food prices are rising faster than general prices. An economic-access indicator, "
                          "not a hunger measure.",
            "latestMonth": M.L.ym_s(m0),
            "latest": [{"province": PROV[r.province_code], "foodYoY": r.food, "allItemsYoY": r.all_items,
                        "fpd": round(r.food - r.all_items, 2), "squeeze": bool(r.food > r.all_items)}
                       for r in last.itertuples()],
            "quarterly": g.to_dict("records"),
            "persistenceSignAccuracy": _j(FINAL / "out" / "results_psa.json")["persistence_forecastability"],
            "linkToHunger": "No measurable link to SWS hunger (concurrent rho 0.14, p .59; leading Holm p = 1)."}


def families_block() -> dict:
    fm = pd.read_csv(O.DATA / "feature_map.csv")
    return {"families": fm.to_dict("records"), "driverGroups": DRIVER_GROUPS}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    sws = sws_block()
    engine = {"asOf": AS_OF, "protocolSha256": M.sha256(O.OA / "FINAL_FORECASTING_PROTOCOL.md"),
              "sws": sws, "outlook": outlook_block(sws), "evaluation": evaluation_block(), "cpi": cpi_block(),
              "families": families_block(), "seals": seals_index()}
    M.write_json(DEST / "engine.json", engine)
    archive_rows().to_csv(DEST / "archive.csv", index=False, lineterminator="\n")
    news_rows().to_csv(DEST / "news_events.csv", index=False, lineterminator="\n")
    shutil.copy(O.OUT / "predictions_primary.csv", DEST / "predictions_fil_oa.csv")
    print("exported to", DEST, {p.name: p.stat().st_size for p in DEST.iterdir()})


if __name__ == "__main__":
    main()

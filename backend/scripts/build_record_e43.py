"""Build the E43 five-trigger food-stress risk record served when AIPHEED_LEAD2_MODEL=e43.

    backend/venv/Scripts/python.exe -B scripts/build_record_e43.py [--run 20261015T134756Z]
      -> data/e43/e43_record.json

Inputs (read-only): the E43 frozen 2027-Q1 forecast (sha-checked), the E43 evaluation run, and the E43 library to
recompute, from the same origin data, the served model's hunger/price components, the five-trigger LightGBM's grouped
SHAP and the observed evidence. No new forecast is made: every probability equals the frozen value.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
E43 = BACKEND.parent / "aipheed-backend-aligned" / "experiments" / "E43_Five_Trigger_Risk"
OUT = BACKEND / "data" / "e43" / "e43_record.json"
sys.path.insert(0, str(E43 / "runner"))

SCORE_DEF = ("Probability that the province is in concurrent elevated food stress in the target quarter: SWS "
             "self-rated hunger in Balance Luzon above 11.3% (regional; shared by all five provinces) AND the "
             "province's PSA food inflation above its 2021-2022 60th percentile, or food minus headline inflation above "
             "its 2021-2022 60th percentile (E40 signals, single quarter). An exploratory food-stress outcome from the two "
             "sources Chapter I section 1.7 names; not independently verified household food insecurity.")
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def band(p: float) -> str:
    return "High" if p >= 2 / 3 else ("Watch" if p >= 1 / 3 else "Low")


def fnum(x, n=3):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="20261015T134756Z")
    a = ap.parse_args()
    import e43_lib as K
    L, np, pd = K.L, K.np, K.pd

    fz = E43 / "frozen" / "E43_PROSPECTIVE_2027Q1.json"
    if sha(fz) != (E43 / "frozen" / "E43_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]:
        raise SystemExit("E43 frozen forecast failed its hash check")
    F = json.loads(fz.read_text())
    res = json.loads((E43 / "runs" / a.run / "results.json").read_text())
    served = F["served_arm"]
    t = L.qi("2026-Q3")
    d, x = L.load(), K.load_extra()
    c = d.cut(t)
    origins = list(range(L.qi("2021-Q3"), t + 1))
    X = K.features(d, x, origins)
    te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    comp = K.simulate(c, t, "T43", components=True)
    tr = K.training_pairs(X, d, t)
    gb = K.GBModel(K.COMB).fit(tr)
    contrib = gb.row_shap(te)
    hq = L.h_quarters(c).sort_values("q")
    H_last, H_q = float(hq["H"].iloc[-1]), int(hq["q"].iloc[-1])
    th = L.e40_spec()
    obs_lab = K.available_labels(d, t)
    last_obs = obs_lab.sort_values("q").groupby("province_code").last()
    hist = pd.read_csv(E43 / "runs" / a.run / "predictions_T43.csv", dtype={"province_code": str})
    ofw_last = int(x["ofw"].dropna(subset=["ofw_cash_remit_usd_bn"])["q"].max())

    provinces = {}
    for i, p in enumerate(L.PROVS):
        name = L.NAMES[p]
        v = F["provinces"][name]
        prob = v[f"{served}_p"]
        cp = comp[p]
        assert abs(cp["joint"] - prob) < 1e-9, "components do not reproduce the frozen forecast"
        r = te.iloc[i]
        # drivers of the served structural model: every five-trigger input it uses is a price input (Market / Prices);
        # the rest of the probability comes from the regional hunger component (reported as otherPct)
        lh, lp = abs(math.log(max(cp["hunger"], 1e-6))), abs(math.log(max(cp["price"], 1e-6)))
        lg = math.log(max(prob, 1e-6) / max(1 - prob, 1e-6))
        drivers = [{"driver_group": g, "driver_label": LABELS[g], "group_shap": round(lg, 4) if g == "market" else 0.0,
                    "direction": ("increases_risk" if lg >= 0 else "protective") if g == "market" else "increases_risk",
                    "trigger_proportion": fnum(r[K.NEWS[g]], 4)} for g in LABELS]
        drivers.sort(key=lambda dd: abs(dd["group_shap"]), reverse=True)
        five = {}
        for g, cols in K.TRIGGER_COLS.items():
            j = [K.COMB.index(cc) for cc in cols]
            five[g] = round(float(contrib[i, j].sum()), 4)
        five["hunger_history"] = round(float(contrib[i, [K.COMB.index(cc) for cc in K.GROUPS["hunger_history"]]].sum()), 4)
        stale_ofw = (t - 1) - ofw_last > 2
        lo = last_obs.loc[p] if p in last_obs.index else None
        hp = hist[(hist["province_code"] == p) & hist["y"].notna() & hist[f"{served}_p"].notna()].sort_values("target_q")
        provinces[p] = {
            "provinceCode": p, "name": name,
            "forecast": {
                "targetQuarter": F["target_quarter"], "lead": 2, "scoreType": "food_stress_risk_probability",
                "probability": prob, "band": band(prob), "servedModel": served,
                "components": {"regionalHungerAbove11_3": round(cp["hunger"], 3),
                               "provincialPriceSignal": round(cp["price"], 3)},
                "explanation": (f"Probability that {name} is in concurrent elevated food stress in {F['target_quarter']}: "
                                f"{prob:.0%} ({band(prob)}). Chance that regional hunger stays above 11.3%: "
                                f"{cp['hunger']:.0%} (latest approved round {H_last:.1f}%, {L.qs(H_q)}). Chance that "
                                f"{name}'s food prices are above its 2021-22 reference: {cp['price']:.0%}."),
                "variants": {"SIM-5T (hunger path informed by triggers)": fnum(v.get("SIM-5T_p")),
                             "LGBM-COMB (five-trigger LightGBM, Chapter I model)": fnum(v.get("LGBM-COMB_p")),
                             "LGBM-GOV (government triggers only)": fnum(v.get("LGBM-GOV_p")),
                             "LR-COMB (logistic baseline)": fnum(v.get("LR-COMB_p")),
                             "B-clim (province base rate)": fnum(v.get("B-clim_p"))},
                "sensitivityL4": fnum(v.get(f"L4_{served}_p")),
            },
            "fiveTriggerModel": {"model": "LGBM-COMB", "probability": fnum(v.get("LGBM-COMB_p")),
                                 "groupContributionsLogOdds": five,
                                 "note": "TreeSHAP of the five-trigger LightGBM at this origin. A contribution is a model "
                                         "attribution, not proof that the event causes food insecurity. This model was "
                                         "not served: it over-predicts HIGH (calibration-in-the-large -0.40) and its "
                                         "Brier is worse than the base rate on the common evaluation quarters."},
            "observed": {
                "hungerRegional": {"value": H_last, "quarter": L.qs(H_q), "ageQuarters": int(t - H_q),
                                   "above11_3": H_last > th["H"], "level": "region (Balance Luzon)",
                                   "source": "SWS approved rounds"},
                "foodInflationLatestMonths": {"value": fnum(r["F_now"], 2), "provinceReferenceP60": round(th["food"][p], 2),
                                              "above4pct": bool(r["F_now"] > 4.0), "level": "province",
                                              "source": "PSA CPI (OpenStat 0012M4ACP23)"},
                "foodMinusHeadline": {"value": fnum(r["gap_now"], 2), "provinceReferenceP60": round(th["gap"][p], 2)},
                "latestObservedSignals": None if lo is None else {
                    "quarter": L.qs(int(lo["q"])), "count": int(lo["signals"]),
                    "category": ["LOW", "WATCH", "HIGH"][int(lo["signals"])]},
                "climate": {"typhoonsWithin300km": fnum(r["tc_count"], 0), "maxSignalBand": fnum(r["tc_max_signal"], 0),
                            "quarter": L.qs(t), "ensoPhasePreviousQuarter": {1.0: "El Nino", 0.0: "Neutral",
                                                                              -1.0: "La Nina"}.get(r["enso"]),
                            "palayProductionYoY": fnum(r["palay_yoy"], 1), "cornProductionYoY": fnum(r["corn_yoy"], 1),
                            "source": "NOAA IBTrACS and CPC ONI (not PAGASA); PSA palay/corn production",
                            "level": "province (typhoons, production); global index (ENSO)"},
                "fisheries": {"fisheriesProductionYoY": fnum(r["fish_yoy"], 1), "aquacultureYoY": fnum(r["aqua_yoy"], 1),
                              "quarter": L.qs(t - 1), "source": "PSA fisheries production (no BFAR fish-kill event series)",
                              "level": "province"},
                "employment": {"unemploymentRate": fnum(r["ur_last"], 2), "unemploymentChangeYoY": fnum(r["ur_yoy"], 2),
                               "underemploymentRate": fnum(r["under_last"], 2), "quarter": L.qs(t - 1),
                               "source": "PSA LFS", "level": "national only"},
                "ofwRemittance": {"remittanceUsdYoY": fnum(r["remit_usd_yoy"], 2), "usdPhpYoY": fnum(r["fx_yoy"], 2),
                                  "latestRemittanceQuarter": L.qs(ofw_last), "stale": stale_ofw,
                                  "source": "BSP cash remittances curated in bsp_macro.parquet (national; unverified "
                                            "re-download); ECB USD/PHP", "level": "national only"},
                "news": {"articles": fnum(r["news_n"], 0), "quarter": L.qs(t), "sufficient": bool((r["news_n"] or 0) >= 5),
                         "triggerShares": {g: fnum(r[K.NEWS[g]], 4) for g in K.NEWS},
                         "fssiV2": fnum(r["fssi_v2"], 4)},
            },
            "triggerStatus": {
                "market": {"status": "contributes", "evidence": "food and headline CPI enter the served price component"},
                "climate": {"status": "data_not_in_model", "evidence": "typhoons, ENSO, palay/corn shown; used by the "
                            "five-trigger LightGBM, not by the served model"},
                "fish_kill": {"status": "data_not_in_model", "evidence": "fisheries production shown"},
                "employment": {"status": "data_not_in_model", "evidence": "national LFS shown"},
                "ofw_remittance": {"status": "stale" if stale_ofw else "data_not_in_model",
                                   "evidence": f"national remittances through {L.qs(ofw_last)}"},
            },
            "drivers": {"drivers": drivers, "article_count": int(r["news_n"] or 0),
                        "other_pct": round(100 * lh / (lh + lp), 1) if lh + lp else 0.0, "evidence_quarter": L.qs(t)},
            "operational": {"category": band(prob), "alertCandidate": band(prob) == "High"},
            "pastForecasts": [{"targetQuarter": L.qs(int(qq)), "probability": round(float(pp), 3), "band": band(float(pp)),
                               "observedHigh": bool(int(yy))}
                              for qq, pp, yy in zip(hp["target_q"], hp[f"{served}_p"], hp["y"])],
            "pastForecastsNote": "Development backtest of the served model at each past origin (information available "
                                 "then); not forecasts issued live at the time.",
            "warnings": [w for w in [
                "SWS hunger is regional (Balance Luzon); provinces differ only through food prices.",
                "Exploratory food-stress outcome; not verified household food insecurity.",
                "No model met the E43 gates; Lead-2 operational use remains experimental.",
                "Employment and OFW evidence are national, not provincial." ,
                "OFW remittance data are more than two quarters old." if stale_ofw else None,
                f"Only {int(r['news_n'] or 0)} province-attributed articles this quarter." if (r["news_n"] or 0) < 5 else None]
                if w],
        }
    t43 = res["T43"]
    sc, ss = t43["S_C"], t43["S_SIM"]
    pick = lambda m: {k: fnum(m.get(k)) for k in ("accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "brier",  # noqa: E731
                                                  "roc_auc")}
    body = {
        "schema": "e43/1", "name": "aiPHeed five-trigger food-stress risk forecast (E43 candidate)",
        "status": "EXPERIMENTAL CANDIDATE: not the served dashboard model; enabled only with AIPHEED_LEAD2_MODEL=e43",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "origin": F["origin"], "targetQuarter": F["target_quarter"], "lead": 2,
        "information": {"cpiMonthsThrough": F["cpi_months_used_through"], "swsLatestQuarter": L.qs(H_q),
                        "rule": "only data published before the origin (E43 PROTOCOL section 2)"},
        "indicator": {"id": "food_stress_risk_probability", "name": "Food-Stress Risk Probability (exploratory)",
                      "definition": SCORE_DEF, "unit": "probability (0-1)",
                      "horizon": f"Lead 2: issued {F['origin']} for {F['target_quarter']}; experimental (E43)",
                      "source": "SWS Balance Luzon hunger (approved rounds) and PSA provincial food and headline CPI; "
                                "five-trigger evidence from PSA, NOAA, BSP (curated) and news",
                      "caveat": "Exploratory food-stress estimate, not verified household food insecurity; SWS is "
                                "regional. Decision support only; not an official classification."},
        "scoreTypes": {"food_stress_risk_probability": SCORE_DEF},
        "operationalRules": {"band": "Low if P < 0.33; Watch if 0.33 <= P < 0.67; High if P >= 0.67",
                             "alert": "Alert candidate when the band is High; staged for administrator confirmation.",
                             "municipal": "No municipal probability; LGU rankings are relative prioritization."},
        "provinces": provinces,
        "evaluation": {"S_C": {"dates": sc["dates"], "rows": sc["rows"], "HIGH": sc["HIGH_rows"], "period": sc["period"],
                               "arms": {k: pick(m) for k, m in sc["metrics"].items()}},
                       "S_SIM": {"dates": ss["dates"], "rows": ss["rows"], "HIGH": ss["HIGH_rows"], "period": ss["period"],
                                 "arms": {k: pick(m) for k, m in ss["metrics"].items()}},
                       "gates": t43["gates"], "status": "development evidence (all quarters seen; E40 holdout exposed)"},
        "limitations": ["Target needs adviser approval (E40 signals without the sustain-2 rule).",
                        "Only 5 common evaluation quarters (25 rows, 5 HIGH); 12 quarters for the structural models.",
                        "Climate data are NOAA-derived (not PAGASA); OFW and employment are national.",
                        "No model beat the base rate convincingly; 75% accuracy is reachable by always-LOW (0.80)."],
        "sources": {"frozen_forecast": fz.name, "frozen_sha256": sha(fz), "evaluation_run": a.run,
                    "protocol_sha256": F["protocol_sha256"]},
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, indent=1, default=str), encoding="utf-8")
    print(OUT, body["content_sha256"][:16])


if __name__ == "__main__":
    main()

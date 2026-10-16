"""Build the E44 five-trigger component-model record served when AIPHEED_LEAD2_MODEL=e44.

    backend/venv/Scripts/python.exe -B scripts/build_record_e44.py
      -> data/e44/e44_record.json

The served model is the pre-declared final candidate I2 (E44 PROTOCOL section 4; no iteration passed the acceptance
gates). Its 2027-Q1 probabilities are the frozen run-1 values; the model is refitted at the same origin only to
recover each trigger's contribution, and the refit must reproduce the frozen probabilities. Observed evidence is taken
from the E43 record (same origin, same as-of data).
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
E44 = BACKEND.parent / "aipheed-backend-aligned" / "experiments" / "E44_Five_Trigger_Optimization"
OUT = BACKEND / "data" / "e44" / "e44_record.json"
E43_REC = BACKEND / "data" / "e43" / "e43_record.json"
RUN1 = E44 / "runs" / "20261015T150213Z"
sys.path.insert(0, str(E44 / "runner"))
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
SCORE_DEF = ("Probability that the province is in concurrent elevated food stress in the target quarter (target T43): "
             "SWS self-rated hunger in Balance Luzon above 11.3% (regional) AND the province's PSA food inflation above "
             "its 2021-2022 60th percentile, or food minus headline inflation above its 2021-2022 60th percentile. "
             "Estimated by the E44 five-trigger component model. Exploratory food-stress outcome; not independently "
             "verified household food insecurity.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def band(p: float) -> str:
    return "High" if p >= 2 / 3 else ("Watch" if p >= 1 / 3 else "Low")


def checked(p: Path) -> dict:
    rec = json.loads(p.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == rec["content_sha256"]
    return rec


def main():
    import e44_components as P2
    C, K, L, np, pd = P2.C, P2.K, P2.L, P2.np, P2.pd
    from scipy.stats import norm

    fz = E44 / "frozen" / "E44_PROSPECTIVE_2027Q1.json"
    assert sha(fz) == (E44 / "frozen" / "E44_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    F = json.loads(fz.read_text())
    assert F["final_candidate"] == "I2" and F["forecasting_acceptance_met"] is False
    res1 = json.loads((RUN1 / "results.json").read_text())
    i4 = json.loads(sorted((E44 / "runs").glob("i4_*/results_i4.json"))[0].read_text())
    i5 = json.loads(sorted((E44 / "runs").glob("i5_*/results_i5.json"))[0].read_text())
    ceiling = json.loads((E44 / "runs" / "blocker" / "discrimination_ceiling.json").read_text())
    e43 = checked(E43_REC)
    t = L.qi("2026-Q3")
    d, x = L.load(), K.load_extra()
    origins = list(range(L.qi("2021-Q3"), t + 1))
    X = P2.features(d, x, origins)
    B = P2.bases(d, origins)
    f = P2.forecast(d, X, B, t, n_jobs=8)
    sel = F["selections_at_origin"]["I2"]
    mult = f["price_cfg"]["mult"]
    te = f["te"]
    HL = te[f"hl_{mult}"].to_numpy()
    pc = f["price_model"].contributions(te)                       # food-YoY points per feature
    hc = f["hunger_model"].contributions(f["hte"]) if f["hunger_model"] is not None else None   # H points
    hist = pd.read_csv(RUN1 / "predictions.csv", dtype={"province_code": str})
    sel_hist = json.loads((RUN1 / "selections.json").read_text())["I2"]

    def p_raw(F_hat, H_hat):
        ph = 1 - norm.cdf((L.e40_spec()["H"] - H_hat) / max(f["hunger_rmse"], 1e-6))
        return ph * P2.p_price(F_hat, HL, f["price_rmse"], te["province_code"])

    base_raw = p_raw(f["F_hat"], f["H_hat"])
    provinces = {}
    for i, p in enumerate(L.PROVS):
        name = L.NAMES[p]
        prob = F["provinces"][name]["I2_p"]
        assert abs(float(f["p"][i]) - prob) < 1e-9, "refit does not reproduce the frozen forecast"
        ob = e43["provinces"][p]["observed"]

        def fmt(v, suf=""):
            return "n/a" if v is None else f"{v}{suf}"
        cl, fi, em, of, fo = ob["climate"], ob["fisheries"], ob["employment"], ob["ofwRemittance"], ob["foodInflationLatestMonths"]
        notes = {
            "market": f"Food inflation {fmt(fo['value'], '%')} in the latest two months vs this province's reference "
                      f"{fo['provinceReferenceP60']}%; food minus headline {fmt(ob['foodMinusHeadline']['value'])} points.",
            "climate": f"{fmt(cl['typhoonsWithin300km'])} typhoon(s) within 300 km in {cl['quarter']}; ENSO "
                       f"{cl['ensoPhasePreviousQuarter'] or 'n/a'} in the previous quarter; palay production "
                       f"{fmt(cl['palayProductionYoY'], '%')} year on year.",
            "fish_kill": f"Fisheries production {fmt(fi['fisheriesProductionYoY'], '%')} and aquaculture "
                         f"{fmt(fi['aquacultureYoY'], '%')} year on year ({fi['quarter']}); no official fish-kill event series.",
            "employment": f"National unemployment {fmt(em['unemploymentRate'], '%')} ({em['quarter']}), "
                          f"{fmt(em['unemploymentChangeYoY'])} points year on year; national figure, the same for every province.",
            "ofw_remittance": f"National cash remittances {fmt(of['remittanceUsdYoY'], '%')} year on year (latest "
                              f"{of['latestRemittanceQuarter']}); USD/PHP {fmt(of['usdPhpYoY'], '%')}; national figure.",
        }
        contrib, drivers, status = {}, [], {}
        for g in LABELS:
            pcols = [c for c in P2.PRICE_GROUPS[g] if c in pc.columns]
            hcols = [c for c in P2.HUNGER_GROUPS[g] if hc is not None and c in hc.columns]
            dp = float(pc.iloc[i][pcols].sum()) if pcols else 0.0
            dh = float(hc.iloc[0][hcols].sum()) if hcols else 0.0
            Fg = f["F_hat"].copy()
            Fg[i] -= dp
            without = p_raw(Fg, f["H_hat"] - dh)[i]
            lg = math.log(max(base_raw[i], 1e-6) / max(1 - base_raw[i], 1e-6)) - math.log(max(without, 1e-6) / max(1 - without, 1e-6))
            contrib[g] = {"foodInflationPoints": round(dp, 3), "hungerPoints": round(dh, 3), "logOddsEffect": round(lg, 4),
                          "features": pcols + [c for c in hcols if c not in pcols]}
            st = "contributes" if abs(dp) >= 0.1 or abs(dh) >= 0.1 else "no_effect"
            status[g] = {"status": st, "evidence": e43["provinces"][p]["triggerStatus"][g]["evidence"],
                         "evidenceNote": notes[g]}
            drivers.append({"driver_group": g, "driver_label": LABELS[g], "group_shap": round(lg, 4) if st == "contributes" else 0.0,
                            "direction": "increases_risk" if lg >= 0 else "protective",
                            "trigger_proportion": e43["provinces"][p]["observed"]["news"]["triggerShares"].get(g)})
        drivers.sort(key=lambda dd: abs(dd["group_shap"]), reverse=True)
        hp = hist[(hist["province_code"] == p) & hist["y"].notna() & hist["I2_p"].notna() & (hist["target_q"] <= L.qi("2026-Q3"))]
        thr = sel["threshold"]
        provinces[p] = {
            "provinceCode": p, "name": name,
            "forecast": {"targetQuarter": F["target_quarter"], "lead": 2, "scoreType": "food_stress_risk_probability",
                         "probability": prob, "band": band(prob), "decisionThreshold": thr,
                         "decision": "HIGH" if prob >= thr else "LOW", "servedModel": "E44-I2 five-trigger component model",
                         "components": {"regionalHungerAbove11_3": round(float(f["p_hunger"]), 3),
                                        "provincialPriceSignal": round(float(f["p_price"][i]), 3),
                                        "foodInflationForecast": round(float(f["F_hat"][i]), 2),
                                        "hungerForecast": round(float(f["H_hat"]), 1)},
                         "explanation": (f"{name}, {F['target_quarter']}: estimated probability of concurrent elevated "
                                         f"food stress {prob:.0%} ({band(prob)}; decision {('HIGH' if prob >= thr else 'LOW')} at the "
                                         f"training-selected threshold {thr}). Regional hunger is forecast at "
                                         f"{f['H_hat']:.1f}% (chance above 11.3%: {f['p_hunger']:.0%}); {name}'s food "
                                         f"inflation is forecast at {f['F_hat'][i]:.1f}% (chance its price signal is on: "
                                         f"{f['p_price'][i]:.0%})."),
                         "variants": {"SIM-5T": F["provinces"][name].get("SIM-5T_p"), "SIM-0": F["provinces"][name].get("SIM-0_p"),
                                      "I3 (extra SWS observations)": F["provinces"][name].get("I3_p"),
                                      "I1 (tuned classifier)": F["provinces"][name].get("I1_p"),
                                      "I2-MKT (market only)": F["provinces"][name].get("I2-MKT_p")}},
            "fiveTriggerContributions": contrib,
            "fiveTriggerNote": ("Contributions of each trigger group to the food-inflation and hunger forecasts of the "
                                "served model (model attributions, not proof that an event causes food insecurity). "
                                "Employment and OFW indicators are national, so they shift every province equally."),
            "triggerStatus": status,
            "drivers": {"drivers": drivers, "article_count": e43["provinces"][p]["observed"]["news"]["articles"] or 0,
                        "other_pct": 0.0, "evidence_quarter": e43["provinces"][p]["observed"]["news"]["quarter"]},
            "observed": e43["provinces"][p]["observed"],
            "operational": {"category": band(prob), "alertCandidate": band(prob) == "High"},
            "pastForecasts": [{"targetQuarter": L.qs(int(r.target_q)), "probability": round(float(r.I2_p), 3),
                               "decision": "HIGH" if r.I2_yhat == 1 else "LOW", "observedHigh": bool(int(r.y))}
                              for r in hp.itertuples()],
            "pastForecastsNote": "Development backtest of the I2 procedure at each past origin (information available "
                                 "then); not forecasts issued live at the time.",
            "warnings": ["FORECASTING ACCEPTANCE NOT MET: no E44 iteration reached 75% Lead-2 accuracy with balanced "
                         "discrimination; treat as experimental decision support.",
                         "SWS hunger is regional; provinces differ through food prices and provincial trigger data.",
                         "Employment and OFW evidence are national.",
                         "Exploratory food-stress outcome; not verified household food insecurity."],
        }
    s44 = res1["S44"]
    pick = lambda m: {k: (None if m.get(k) is None else round(float(m[k]), 3)) for k in  # noqa: E731
                      ("accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "brier", "roc_auc")}
    iters = {k: pick(s44["metrics"][k]) for k in ("I1", "I2", "I3")}
    iters["I4"] = pick(i4["S44"]["metrics"]["I4"])
    iters["I5"] = pick(i5["S44"]["metrics"]["I5"])
    body = {
        "schema": "e44/1", "name": "aiPHeed five-trigger food-stress risk forecast (E44 final candidate, I2)",
        "status": "EXPERIMENTAL - FORECASTING ACCEPTANCE NOT MET; enabled only with AIPHEED_LEAD2_MODEL=e44",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "origin": F["origin"], "originQuarter": F["origin_quarter"], "targetQuarter": F["target_quarter"],
        "lead": 2, "leadFromOrigin": F["lead_from_origin"],
        "information": {"cpiMonthsThrough": F["cpi_months_used_through"], "swsLatestQuarter": e43["information"]["swsLatestQuarter"],
                        "rule": "only data published before the origin (E43/E44 protocols)"},
        "indicator": {"id": "food_stress_risk_probability", "name": "Food-Stress Risk Probability (exploratory)",
                      "definition": SCORE_DEF, "unit": "probability (0-1)",
                      "horizon": f"Lead 2: issued {F['origin']} (latest completed quarter {F['origin_quarter']}) for "
                                 f"{F['target_quarter']}; experimental (E44)",
                      "source": "SWS Balance Luzon hunger; PSA provincial food and headline CPI and wholesale rice; NOAA "
                                "typhoon tracks and ENSO; PSA palay/corn and fisheries production; PSA LFS (national); "
                                "BSP remittances and ECB USD/PHP (national); province-attributed news",
                      "caveat": "Forecasting acceptance (75% Lead-2 accuracy with balanced discrimination) was not met. "
                                "Exploratory estimate; not an official classification."},
        "scoreTypes": {"food_stress_risk_probability": SCORE_DEF},
        "operationalRules": {"band": "Low if P < 0.33; Watch if 0.33 <= P < 0.67; High if P >= 0.67",
                             "decision": "HIGH/LOW decision at the threshold selected inside training (E44 PROTOCOL 3)",
                             "alert": "Alert candidate when the band is High; staged for administrator confirmation.",
                             "municipal": "No municipal probability; LGU rankings are relative prioritization."},
        "provinces": provinces,
        "assessment": {"forecastingAcceptanceMet": False, "finalCandidate": "I2",
                       "S44": {"dates": s44["dates"], "rows": s44["rows"], "HIGH": s44["HIGH"], "period": s44["period"]},
                       "iterations": iters,
                       "baselines": {k: pick(s44["metrics"][k]) for k in ("B-maj", "B-persist", "B-clim", "SIM-0", "SIM-5T",
                                                                          "E38-served", "E41-M1", "I2-MKT")},
                       "discriminationCeiling": {"requiredAUC_binormal": ceiling["binormal_min_auc_for_A1_A2"]["auc"],
                                                 "bestFiveTriggerAUC": max(v["auc"] for k, v in ceiling["arms"].items()
                                                                           if k in ("I1", "I2", "I3", "I4", "I5"))},
                       "softwareReadiness": "tested (backend, frontend, E44 suites)",
                       "forecastingReadiness": "not accepted; experimental"},
        "limitations": ["No iteration (I1-I5) met A1 (accuracy >= 0.75) with A2 (balanced discrimination).",
                        "Gates need AUC ~0.78 at this class balance; five-trigger candidates reach 0.27-0.63.",
                        "7 common outer quarters (35 rows, 9 HIGH); every quarter seen; E40 holdout exposed.",
                        "Target T43 needs adviser approval; SWS is regional; employment and OFW are national."],
        "sources": {"frozen_forecast": fz.name, "frozen_sha256": sha(fz), "evaluation_run": RUN1.name,
                    "protocol_sha256": F["protocol_sha256"], "e43_record_sha256": e43["content_sha256"]},
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, indent=1, default=str), encoding="utf-8")
    print(OUT, body["content_sha256"][:16], {L.NAMES[p]: (v["forecast"]["probability"], v["forecast"]["decision"],
                                                         {g: s["status"] for g, s in v["triggerStatus"].items()})
                                            for p, v in provinces.items()})


if __name__ == "__main__":
    main()

"""Build the E46 record served when AIPHEED_LEAD2_MODEL=e46: the defect-corrected component model (E46 I7).

    backend/venv/Scripts/python.exe -B scripts/build_record_e46.py
      -> data/e46/e46_record.json

I7 corrects the E44 I2 defects (D1 inconsistent food/headline gap, D2 per-origin Platt/threshold refit, D3 residual
intercepts that do not transfer). Its 2027-Q1 probabilities are the frozen values in
experiments/E46_Rice_Policy/frozen/E46_I7_PROSPECTIVE_2027Q1.json (issued 2026-10-01, same issue convention as the
dashboard); the model is refitted at that origin only to recover each trigger group's contribution, and the refit must
reproduce the frozen probabilities. I7 did NOT pass its pre-registered final-candidate rule (HIGH recall 0.44), so the
record states that forecasting acceptance is not met. Observed evidence comes from the E43 record (same origin).
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
E46 = BACKEND.parent / "aipheed-backend-aligned" / "experiments" / "E46_Rice_Policy"
OUT = BACKEND / "data" / "e46" / "e46_record.json"
E43_REC = BACKEND / "data" / "e43" / "e43_record.json"
RUN7 = E46 / "runs" / "i7_20261017T000111Z"
RUN1 = E46.parent / "E44_Five_Trigger_Optimization" / "runs" / "20261015T150213Z"
sys.path.insert(0, str(E46 / "runner"))
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
SCORE_DEF = ("Probability that the province is in concurrent elevated food stress in the target quarter (target T43): "
             "SWS self-rated hunger in Balance Luzon above 11.3% (regional) AND the province's PSA food inflation above "
             "its 2021-2022 60th percentile, or food minus headline inflation above its 2021-2022 60th percentile. "
             "Estimated by the E46 defect-corrected five-trigger component model (I7). Exploratory food-stress "
             "outcome; not independently verified household food insecurity.")


# E47 trigger-status rule (documented): a group "contributes" when removing its inputs moves the food-inflation,
# food-minus-headline or hunger forecast by at least NEGLIGIBLE_POINTS percentage points; below that it has
# "no_effect" (a computed, negligible contribution); it is "insufficient_data" when none of its observed inputs has a
# value at that issue date (any contribution would come only from imputation and missing flags, not evidence).
NEGLIGIBLE_POINTS = 0.1
OBSERVED_INPUTS = {"market": ["F_now", "gap_now", "F_hat_M1", "rice_whsl_yoy"],
                   "climate": ["tc_count", "enso", "palay_yoy", "corn_yoy"],
                   "fish_kill": ["fish_yoy", "aqua_yoy"],
                   "employment": ["ur_yoy", "under_yoy"],
                   "ofw_remittance": ["remit_usd_yoy", "remit_php_yoy", "fx_yoy"]}


def group_status(row, g, dF, dG, dH) -> str:
    vals = [row.get(c) for c in OBSERVED_INPUTS[g]]
    if all(v is None or not math.isfinite(float(v)) for v in vals):
        return "insufficient_data"
    return "contributes" if max(abs(dF), abs(dG), abs(dH)) >= NEGLIGIBLE_POINTS else "no_effect"


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
    import e46_i7 as I7
    M, K, L, P2, np, pd = I7.M, I7.K, I7.L, I7.P2, I7.np, I7.pd

    fz = E46 / "frozen" / "E46_I7_PROSPECTIVE_2027Q1.json"
    assert sha(fz) == (E46 / "frozen" / "E46_I7_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    F = json.loads(fz.read_text())
    res7 = json.loads((RUN7 / "results_i7.json").read_text())
    e43 = checked(E43_REC)
    t = L.qi("2026-Q3")
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    origins = list(range(L.qi("2021-Q3"), t + 1))
    X = M.features(d, x, origins, ev)
    B = P2.bases(d, origins)
    f = I7.forecast(d, X, B, t, n_jobs=8)
    te = f["te"]
    fcon = f["food_model"].contributions(te) if f["food_model"] is not None else None   # food-YoY points
    gcon = f["gap_model"].contributions(te) if f["gap_model"] is not None else None     # gap points
    hcon = f["hunger_model"].contributions(f["hte"]) if f["hunger_model"] is not None else None   # H points
    P7 = pd.read_csv(RUN7 / "predictions_i7.csv", dtype={"province_code": str})
    truth = pd.read_csv(RUN1 / "predictions.csv", dtype={"province_code": str})[["t", "province_code", "target_q", "y"]]
    hist = P7.merge(truth, on=["t", "province_code"], how="left")
    th = L.e40_spec()

    def p_joint(i, dF=0.0, dG=0.0, dH=0.0):
        ph = 1 - I7.norm.cdf((th["H"] - (f["H_hat"] - dH)) / max(f["hunger_rmse"], 1e-6))
        pp = P2.p_price_biv([f["F_hat"][i] - dF], [f["G_hat"][i] - dG], f["food_rmse"], f["gap_rmse"], f["rho"],
                            [te["province_code"].iloc[i]])[0]
        return ph * pp

    def grp(con, cols, i):
        if con is None:
            return 0.0, []
        c = [k for k in cols if k in con.columns]
        return (float(con.iloc[i][c].sum()) if c else 0.0), c

    provinces = {}
    for i, p in enumerate(L.PROVS):
        name = L.NAMES[p]
        prob = F["provinces"][name]["I7_p"]
        assert abs(float(f["p"][i]) - prob) < 1e-9, "refit does not reproduce the frozen I7 forecast"
        base = p_joint(i)
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
            dF, fc = grp(fcon, P2.PRICE_GROUPS[g], i)
            dG, gc = grp(gcon, P2.PRICE_GROUPS[g], i)
            dH, hc = grp(hcon, P2.HUNGER_GROUPS.get(g, []), 0)
            without = p_joint(i, dF, dG, dH)
            lg = (math.log(max(base, 1e-6) / max(1 - base, 1e-6)) - math.log(max(without, 1e-6) / max(1 - without, 1e-6)))
            contrib[g] = {"foodInflationPoints": round(dF, 3), "gapPoints": round(dG, 3), "hungerPoints": round(dH, 3),
                          "logOddsEffect": round(lg, 4),
                          "features": sorted(set(P2.PRICE_GROUPS[g]) | set(P2.HUNGER_GROUPS.get(g, []))),
                          "featuresWithNonzeroWeight": sorted(set(fc) | set(gc) | set(hc))}
            st = group_status(X[(X["t"] == t) & (X["province_code"] == p)].iloc[0], g, dF, dG, dH)
            status[g] = {"status": st, "evidence": e43["provinces"][p]["triggerStatus"][g]["evidence"],
                         "evidenceNote": notes[g]}
            drivers.append({"driver_group": g, "driver_label": LABELS[g],
                            "group_shap": round(lg, 4) if st == "contributes" else 0.0,
                            "direction": "increases_risk" if lg >= 0 else "protective",
                            "trigger_proportion": e43["provinces"][p]["observed"]["news"]["triggerShares"].get(g)})
        drivers.sort(key=lambda dd: abs(dd["group_shap"]), reverse=True)
        hp = hist[(hist["province_code"] == p) & hist["I7_p"].notna()]
        past = hp[hp["y"].notna() & (hp["target_q"] <= t)]
        earlier = hp[(hp["t"] + 2 > t) & (hp["t"] + 2 < L.qi(F["target_quarter"]))]
        provinces[p] = {
            "provinceCode": p, "name": name,
            "forecast": {"targetQuarter": F["target_quarter"], "lead": 2, "scoreType": "food_stress_risk_probability",
                         "kind": "FORECAST (outcome not yet known)",
                         "probability": prob, "band": band(prob), "decisionThreshold": 0.5,
                         "decision": "HIGH" if prob >= 0.5 else "LOW",
                         "servedModel": "E46-I7 defect-corrected five-trigger component model",
                         "components": {"regionalHungerAbove11_3": round(float(f["p_hunger"]), 3),
                                        "provincialPriceSignal": round(float(f["p_price"][i]), 3),
                                        "foodInflationForecast": round(float(f["F_hat"][i]), 2),
                                        "foodMinusHeadlineForecast": round(float(f["G_hat"][i]), 2),
                                        "hungerForecast": round(float(f["H_hat"]), 1)},
                         "explanation": (f"{name}, {F['target_quarter']} (forecast issued {F['origin']}): estimated "
                                         f"probability of concurrent elevated food stress {prob:.0%} ({band(prob)}; "
                                         f"decision {'HIGH' if prob >= 0.5 else 'LOW'} at p >= 0.5). Regional hunger is "
                                         f"forecast at {f['H_hat']:.1f}% (chance above 11.3%: {f['p_hunger']:.0%}); "
                                         f"{name}'s food inflation at {f['F_hat'][i]:.1f}% and food minus headline at "
                                         f"{f['G_hat'][i]:+.1f} points (chance its price signal is on: {f['p_price'][i]:.0%})."),
                         "variants": {"I7-BASE (no residual)": F["provinces"][name].get("I7-BASE_p"),
                                      "I7-MKT (market residual only)": F["provinces"][name].get("I7-MKT_p")}},
            "fiveTriggerContributions": contrib,
            "fiveTriggerNote": ("Contributions of each trigger group to the food-inflation, food-minus-headline and "
                                "hunger forecasts of the served model (model attributions, not proof that an event causes "
                                "food insecurity). Employment and OFW indicators are national."),
            "triggerStatus": status,
            "drivers": {"drivers": drivers, "article_count": e43["provinces"][p]["observed"]["news"]["articles"] or 0,
                        "other_pct": 0.0, "evidence_quarter": e43["provinces"][p]["observed"]["news"]["quarter"]},
            "observed": e43["provinces"][p]["observed"],
            "operational": {"category": band(prob), "alertCandidate": band(prob) == "High"},
            "pastForecasts": [{"targetQuarter": L.qs(int(r.target_q)), "probability": round(float(r.I7_p), 3),
                               "origin": str(L.origin(int(r.t)).date()),
                               "decision": "HIGH" if r.I7_yhat == 1 else "LOW", "observedHigh": bool(int(r.y))}
                              for r in past.itertuples()],
            "earlierForecasts": [{"targetQuarter": L.qs(int(r.t) + 2), "probability": round(float(r.I7_p), 3),
                                  "origin": str(L.origin(int(r.t)).date()),
                                  "decision": "HIGH" if r.I7_yhat == 1 else "LOW"} for r in earlier.itertuples()],
            "pastForecastsNote": "Development backtest of the I7 procedure at each past origin (only information "
                                 "published before that origin; verified by deleting all later data); not forecasts "
                                 "issued live, and the outcomes were examined while the correction was designed.",
            "warnings": ["FORECASTING ACCEPTANCE NOT MET: I7 reaches 0.800 accuracy on the 35 development rows but "
                         "detects 4 of 9 HIGH quarters (HIGH recall 0.44); experimental decision support only.",
                         "Historical scores are development evidence (outcomes examined while diagnosing the defect); "
                         "acceptance requires the prospective quarters 2027-Q1..Q4.",
                         "SWS hunger is regional; provinces differ through food prices and provincial trigger data.",
                         "Employment and OFW evidence are national.",
                         "Exploratory food-stress outcome; not verified household food insecurity."],
        }
    # ---- E47: five-trigger attributions for every past quarter on the timeline (backtests and the earlier 2026-Q4
    # forecast). The I7 model is refitted at each quarter's own issue date with only the data published before it; the
    # refit must reproduce the committed backtest probability, and the evidence notes are that origin's own inputs.
    enso_name = {1.0: "El Nino", 0.0: "neutral", -1.0: "La Nina"}

    def num(v, fmt="{:.1f}", suf=""):
        return "n/a (no published figure)" if v is None or (isinstance(v, float) and not math.isfinite(v)) else fmt.format(v) + suf

    def attribute(fx, i):
        tex = fx["te"]
        fc_ = fx["food_model"].contributions(tex) if fx["food_model"] is not None else None
        gc_ = fx["gap_model"].contributions(tex) if fx["gap_model"] is not None else None
        hc_ = fx["hunger_model"].contributions(fx["hte"]) if fx["hunger_model"] is not None else None

        def pj(dF=0.0, dG=0.0, dH=0.0):
            ph = 1 - I7.norm.cdf((th["H"] - (fx["H_hat"] - dH)) / max(fx["hunger_rmse"], 1e-6))
            return ph * P2.p_price_biv([fx["F_hat"][i] - dF], [fx["G_hat"][i] - dG], fx["food_rmse"], fx["gap_rmse"],
                                       fx["rho"], [tex["province_code"].iloc[i]])[0]
        base_ = pj()
        out = {}
        for g in LABELS:
            dF, a = grp(fc_, P2.PRICE_GROUPS[g], i)
            dG, b = grp(gc_, P2.PRICE_GROUPS[g], i)
            dH, c = grp(hc_, P2.HUNGER_GROUPS.get(g, []), 0)
            wo = pj(dF, dG, dH)
            lg = math.log(max(base_, 1e-6) / max(1 - base_, 1e-6)) - math.log(max(wo, 1e-6) / max(1 - wo, 1e-6))
            out[g] = (dF, dG, dH, lg, sorted(set(a) | set(b) | set(c)))
        return out

    origins_past = sorted({L.qi(x["targetQuarter"]) - 2 for v in provinces.values()
                           for x in v["pastForecasts"] + v["earlierForecasts"]})
    committed = P7.set_index(["t", "province_code"])["I7_p"]
    for tp in origins_past:
        fx = I7.forecast(d, X, B, tp, n_jobs=8)
        q = L.qs(tp + 2)
        row = X[X["t"] == tp].set_index("province_code")
        for i, p in enumerate(L.PROVS):
            assert abs(float(fx["p"][i]) - float(committed[(tp, p)])) < 1e-9, f"refit at {L.qs(tp)} differs from the backtest"
            r = row.loc[p]
            notes = {
                "market": f"Food inflation {num(r['F_now'], suf='%')} in the latest two months (through "
                          f"{L.ym_s(L.m0_of(tp))}) vs this province's reference {th['food'][p]:.2f}%; food minus headline "
                          f"{num(r['gap_now'], '{:+.1f}')} points.",
                "climate": f"{num(r['tc_count'], '{:.0f}')} typhoon(s) within 300 km in {L.qs(tp)}; ENSO "
                           f"{enso_name.get(r['enso'], 'n/a')} in {L.qs(tp - 1)}; palay production "
                           f"{num(r['palay_yoy'], suf='%')} year on year ({L.qs(tp - 1)}).",
                "fish_kill": f"Fisheries production {num(r['fish_yoy'], suf='%')} and aquaculture "
                             f"{num(r['aqua_yoy'], suf='%')} year on year ({L.qs(tp - 1)}); no official fish-kill event series.",
                "employment": f"National unemployment {num(r['ur_last'], '{:.2f}', '%')} ({L.qs(tp - 1)}), "
                              f"{num(r['ur_yoy'], '{:+.2f}')} points year on year; national figure, the same for every province.",
                "ofw_remittance": f"National cash remittances {num(r['remit_usd_yoy'], suf='%')} year on year "
                                  f"({L.qs(tp - 1)}); USD/PHP {num(r['fx_yoy'], suf='%')}; national figure.",
            }
            att = attribute(fx, i)
            # additivity: the ridge residuals have no intercept, so the per-feature contributions must sum exactly to
            # each component's correction of its base projection (food, gap) or of the latest hunger level
            tex = fx["te"]
            checks = {}
            for nm, mdl, frame, hat, base, k in (("food", fx["food_model"], tex, fx["F_hat"][i], fx["F_base"][i], i),
                                                 ("gap", fx["gap_model"], tex, fx["G_hat"][i], fx["G_base"][i], i),
                                                 ("hunger", fx["hunger_model"], fx["hte"], fx["H_hat"],
                                                  float(fx["hte"]["H_base"].iloc[0]), 0)):
                tot = 0.0 if mdl is None else float(mdl.contributions(frame).iloc[k].sum())
                # the E44 hunger ridge keeps its intercept (a constant shift attributed to no trigger group)
                icpt = 0.0 if mdl is None else float(getattr(mdl.m, "intercept_", 0.0))
                checks[f"{nm}_intercept_not_attributed"] = icpt
                checks[f"{nm}_additivity_error"] = abs(tot + icpt - (float(hat) - float(base)))
                assert checks[f"{nm}_additivity_error"] < 1e-8, (L.qs(tp), p, nm, checks)
            sws_cut = d.cut(tp).sws
            contrib, drivers, status = {}, [], {}
            for g, (dF, dG, dH, lg, nz) in att.items():
                st = group_status(r, g, dF, dG, dH)
                contrib[g] = {"foodInflationPoints": round(dF, 3), "gapPoints": round(dG, 3), "hungerPoints": round(dH, 3),
                              "logOddsEffect": round(lg, 4), "featuresWithNonzeroWeight": nz}
                status[g] = {"status": st, "evidenceNote": notes[g]}
                share = r.get(f"news_{g}")
                drivers.append({"driver_group": g, "driver_label": LABELS[g],
                                "group_shap": round(lg, 4) if st == "contributes" else 0.0,
                                "direction": "increases_risk" if lg >= 0 else "protective",
                                "trigger_proportion": None if share is None or not math.isfinite(share) else float(share)})
            drivers.sort(key=lambda dd: abs(dd["group_shap"]), reverse=True)
            nn = r.get("news_n")
            provinces[p].setdefault("pastDrivers", {})[q] = {
                "origin": str(L.origin(tp).date()), "originQuarter": L.qs(tp), "probability": round(float(fx["p"][i]), 4),
                "informationCutoff": {"cpiThrough": L.ym_s(int(d.cut(tp).idx["ym"].max())),
                                      "swsLatestQuarter": L.qs(int(sws_cut.loc[sws_cut["published"].idxmax(), "q"])),
                                      "swsLatestPosted": str(sws_cut["published"].max().date()),
                                      "typhoonsAndNewsThrough": L.qs(tp), "productionLfsRemittancesThrough": L.qs(tp - 1)},
                "checks": {k: float(v) for k, v in checks.items()},
                "fiveTriggerContributions": contrib, "triggerStatus": status,
                "drivers": {"drivers": drivers, "article_count": int(nn) if nn is not None and math.isfinite(nn) else 0,
                            "other_pct": 0.0, "evidence_quarter": L.qs(tp)}}
    s44, ext = res7["S44"], res7["EXT"]
    pick = lambda m: {k: (None if m.get(k) is None else round(float(m[k]), 3)) for k in  # noqa: E731
                      ("accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "precision_HIGH", "f1_HIGH",
                       "brier", "roc_auc")}
    body = {
        "schema": "e46/1", "name": "aiPHeed five-trigger food-stress risk forecast (E46 I7, defect-corrected)",
        "status": "EXPERIMENTAL - FORECASTING ACCEPTANCE NOT MET; enabled only with AIPHEED_LEAD2_MODEL=e46",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modelVersion": "E46-I7 (ADDENDUM_I7 sha256 " + F["addendum_sha256"][:16] + ")",
        "origin": F["origin"], "originQuarter": F["origin_quarter"], "targetQuarter": F["target_quarter"],
        "lead": 2, "leadFromOrigin": F["lead_from_origin"],
        "information": {"cpiMonthsThrough": L.ym_s(L.m0_of(t)), "swsLatestQuarter": e43["information"]["swsLatestQuarter"],
                        "rule": "only data published before the origin 2026-10-01 (E41/E46 protocols)"},
        "indicator": {"id": "food_stress_risk_probability", "name": "Food-Stress Risk Probability (exploratory)",
                      "definition": SCORE_DEF, "unit": "probability (0-1)",
                      "horizon": f"Lead 2: issued {F['origin']} (latest completed quarter {F['origin_quarter']}) for "
                                 f"{F['target_quarter']}; experimental (E46 I7)",
                      "source": "SWS Balance Luzon hunger; PSA provincial food and headline CPI and wholesale rice; NOAA "
                                "typhoon tracks and ENSO; PSA palay/corn and fisheries production; PSA LFS (national); "
                                "BSP remittances and ECB USD/PHP (national); province-attributed news; official "
                                "rice-policy orders (as of announcement)",
                      "caveat": "Forecasting acceptance (75% Lead-2 accuracy with balanced discrimination) was not met. "
                                "Exploratory estimate; not an official classification."},
        "scoreTypes": {"food_stress_risk_probability": SCORE_DEF},
        "operationalRules": {"band": "Low if P < 0.33; Watch if 0.33 <= P < 0.67; High if P >= 0.67",
                             "decision": "HIGH if P >= 0.5 (fixed; ADDENDUM_I7)",
                             "alert": "Alert candidate when the band is High; staged for administrator confirmation.",
                             "municipal": "No municipal probability; LGU rankings are relative prioritization."},
        "provinces": provinces,
        "assessment": {"forecastingAcceptanceMet": False, "finalCandidate": None, "servedCandidate": "I7",
                       "S44": {"dates": s44["dates"], "rows": s44["rows"], "HIGH": s44["HIGH"],
                               "metrics": {k: pick(s44["metrics"][k]) for k in ("I7", "I2", "B-maj", "B-persist", "SIM-0")},
                               "confusion_I7": s44["robustness"]["I7"]["confusion"]},
                       "EXT": {"dates": ext["dates"], "rows": ext["rows"], "metrics": {k: pick(ext["metrics"][k])
                                                                                       for k in ("I7", "I2", "B-maj")}},
                       "gates": s44["gates_I7"], "evidenceStatus": res7["evidence_status"],
                       "forecastingReadiness": "not accepted; experimental; prospective validation 2027-Q1..Q4"},
        "limitations": ["I7 fails A2: HIGH recall 0.44 on 9 HIGH development rows.",
                        "No untouched historical evaluation exists; every 2022-2026 quarter was examined.",
                        "7 independent development quarters; accuracy CI 0.66-0.94.",
                        "Target T43 needs adviser approval; SWS is regional; employment and OFW are national."],
        "sources": {"frozen_forecast": fz.name, "frozen_sha256": sha(fz), "evaluation_run": RUN7.name,
                    "addendum_sha256": F["addendum_sha256"], "e43_record_sha256": e43["content_sha256"]},
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, indent=1, default=str), encoding="utf-8")
    print(OUT, body["content_sha256"][:16], {L.NAMES[p]: (v["forecast"]["probability"], v["forecast"]["decision"],
                                                         {g: s["status"] for g, s in v["triggerStatus"].items()})
                                            for p, v in provinces.items()})


if __name__ == "__main__":
    main()

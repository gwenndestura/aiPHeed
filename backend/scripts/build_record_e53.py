"""Build the E53 record served when AIPHEED_LEAD2_MODEL=e53: provincial FOOD-PRICE PRESSURE probability (target PS)
from the E52 price model with the arm adopted under experiments/E53_LightGBM_Calibration/PROTOCOL.md section 4, and
the corrected five-trigger attribution (DEVIATIONS.md D-1: rice-policy -> Market, news_<group> -> its group,
news_n -> other).

    backend/venv/Scripts/python.exe -B scripts/build_record_e53.py [R0|C1|C2]   -> data/e53/e53_record.json

At every issue date (each past quarter's own origin, the 2026-Q4 earlier forecast, the 2027-Q1 forecast) the model is
refitted with only data published before that date and must reproduce the E53 run's probability for that arm.
Each group's effect = change in the log-odds of the SERVED probability when the group's inputs (all of them, D-1) are
set to their training mean; Market includes the base-effect CPI projections. Checks per row: ridge + base reconcile
with the model's forecasts (< 1e-8) and the served probability is reproduced (< 1e-9).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
EXP = BACKEND.parent / "aipheed-backend-aligned" / "experiments"
E53 = EXP / "E53_LightGBM_Calibration"
OUT = BACKEND / "data" / "e53" / "e53_record.json"
E43_REC = BACKEND / "data" / "e43" / "e43_record.json"
sys.path.insert(0, str(E53 / "runner"))
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
SCORE_DEF = ("Probability that the province's food-price pressure signal is on in the target quarter (target PS): PSA "
             "food inflation (quarter mean, year on year) above the province's 2021-2022 60th percentile, or food minus "
             "headline inflation above its 2021-2022 60th percentile. Estimated by the E53 food-price-pressure model. "
             "Food-price pressure is not hunger and not verified household food insecurity.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def band(p: float) -> str:
    return "High" if p >= 2 / 3 else ("Watch" if p >= 1 / 3 else "Low")


def _e46_builder():
    spec = importlib.util.spec_from_file_location("b46", BACKEND / "scripts" / "build_record_e46.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    import e53_lib as E
    L, P2, np, pd = E.L, E.P2, E.np, E.pd
    b46 = _e46_builder()
    run = sorted(p for p in (E53 / "runs").glob("2026*") if not (p / "ABORTED.txt").exists())[0]
    res = json.loads((run / "results.json").read_text())
    arm = sys.argv[1] if len(sys.argv) > 1 else (res["decision"]["calibrated_replaces_R0"] or "R0")
    assert arm in ("R0", "C1", "C2")
    proto = (E53 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    P = pd.read_csv(run / "predictions.csv", dtype={"province_code": str}).set_index(["t", "province_code"])
    e43 = json.loads(E43_REC.read_text(encoding="utf-8"))
    cpi = pd.read_csv(EXP / "E51_Target_Definition" / "data" / "labels_cpi.csv", dtype={"province_code": str})
    ps = {(p, int(q)): int(y) for p, q, y in zip(cpi["province_code"], cpi["q"], cpi["PS"])}
    d, X, B = E.load()
    th = L.e40_spec()
    enso_name = {1.0: "El Nino", 0.0: "neutral", -1.0: "La Nina"}
    oper = int(P.index.get_level_values("t").max())

    def num(v, fmt="{:.1f}", suf=""):
        return ("n/a (not in the dataset at the issue date)" if v is None or (isinstance(v, float) and not math.isfinite(v))
                else fmt.format(v) + suf)

    def lo(a, b):
        return math.log(max(a, 1e-9) / max(1 - a, 1e-9)) - math.log(max(b, 1e-9) / max(1 - b, 1e-9))

    def news_share(row, g):
        v = row.get(f"news_{g}")
        return "" if v is None or not math.isfinite(float(v)) else f" News tagged {LABELS[g]}: {v:.0%} of articles."

    def explain(fx, cal, tq, i, p):
        tex = fx["te"]
        fc = fx["food_model"].contributions(tex) if fx["food_model"] is not None else None
        gc = fx["gap_model"].contributions(tex) if fx["gap_model"] is not None else None
        tr = fx["tr"]
        mf, mg = fx["food_cfg"]["mult"], fx["gap_cfg"]["mult"]
        trq = tr[tr["t"] + 2 <= tq - 1]
        mF, mG = float(trq[f"base_{mf}"].mean()), float(trq[f"gbase_{mg}"].mean())
        Fh, Gh = float(fx["F_hat"][i]), float(fx["G_hat"][i])

        def pp(dF=0.0, dG=0.0):
            raw = P2.p_price_biv([Fh - dF], [Gh - dG], fx["food_rmse"], fx["gap_rmse"], fx["rho"], [p])
            return float(E.apply_calibrator(cal, raw)[0]) if cal else float(raw[0])
        served = pp()
        sF = 0.0 if fc is None else float(fc.iloc[i].sum())
        sG = 0.0 if gc is None else float(gc.iloc[i].sum())
        checks = {"food_reconciliation_error": abs(float(fx["F_base"][i]) + sF - Fh),
                  "gap_reconciliation_error": abs(float(fx["G_base"][i]) + sG - Gh)}
        assert max(checks.values()) < 1e-8, checks
        row = X[(X["t"] == tq) & (X["province_code"] == p)].iloc[0]
        out = {}
        for g in list(LABELS) + ["other"]:
            def part(c):
                return 0.0 if c is None else float(sum(c.iloc[i][k] for k in c.columns if E.group_of(k) == g))
            dF, dG = part(fc), part(gc)
            bF = bG = 0.0
            if g == "market":
                bF, bG = float(fx["F_base"][i]) - mF, float(fx["G_base"][i]) - mG
            eff = lo(served, pp(dF + bF, dG + bG))
            out[g] = {"foodInflationPoints": round(dF + bF, 3), "gapPoints": round(dG + bG, 3), "logOddsEffect": round(eff, 4),
                      **({"baseProjectionFoodPoints": round(bF, 3), "baseProjectionGapPoints": round(bG, 3)} if g == "market" else {})}
            if g in LABELS:
                obs = b46.OBSERVED_INPUTS[g]
                present = [c for c in obs if row.get(c) is not None and math.isfinite(float(row.get(c)))]
                out[g]["status"] = b46.group_status(row, g, dF + bF, dG + bG, 0.0)
                out[g]["inputsPresent"] = round(len(present) / len(obs), 3)
        notes = {
            "market": f"Food inflation {num(row['F_now'], suf='%')} in the latest two months (through {L.ym_s(L.m0_of(tq))}) "
                      f"vs this province's reference {th['food'][p]:.2f}%; food minus headline {num(row['gap_now'], '{:+.1f}')} "
                      f"points; rice-policy orders in force for the target quarter are included. Source: PSA CPI, DA/BOC orders."
                      + news_share(row, "market"),
            "climate": f"{num(row['tc_count'], '{:.0f}')} typhoon(s) within 300 km in {L.qs(tq)}; ENSO "
                       f"{enso_name.get(row['enso'], 'n/a')} in {L.qs(tq - 1)}; palay production {num(row['palay_yoy'], suf='%')} "
                       f"year on year ({L.qs(tq - 1)}). Sources: typhoon tracks, NOAA ONI, PSA." + news_share(row, "climate"),
            "fish_kill": f"Fisheries production {num(row['fish_yoy'], suf='%')} and aquaculture {num(row['aqua_yoy'], suf='%')} "
                         f"year on year ({L.qs(tq - 1)}); no official fish-kill event series exists. Source: PSA."
                         + news_share(row, "fish_kill"),
            "employment": f"National unemployment {num(row['ur_last'], '{:.2f}', '%')} ({L.qs(tq - 1)}), "
                          f"{num(row['ur_yoy'], '{:+.2f}')} points year on year; national figure. Source: PSA LFS."
                          + news_share(row, "employment"),
            "ofw_remittance": f"National cash remittances {num(row['remit_usd_yoy'], suf='%')} year on year ({L.qs(tq - 1)}); "
                              f"USD/PHP {num(row['fx_yoy'], suf='%')}; national figures. Sources: BSP, ECB."
                              + news_share(row, "ofw_remittance"),
        }
        status = {g: {"status": out[g]["status"], "evidenceNote": notes[g], "inputsPresent": out[g]["inputsPresent"]}
                  for g in LABELS}
        tot = sum(abs(out[g]["logOddsEffect"]) for g in LABELS if out[g]["status"] == "contributes") + abs(out["other"]["logOddsEffect"])
        other_pct = round(100 * abs(out["other"]["logOddsEffect"]) / tot, 1) if tot > 0 else 0.0
        drivers = sorted(({"driver_group": g, "driver_label": LABELS[g],
                           "group_shap": out[g]["logOddsEffect"] if out[g]["status"] == "contributes" else 0.0,
                           "direction": "increases_risk" if out[g]["logOddsEffect"] >= 0 else "protective",
                           "trigger_proportion": None if pd.isna(row.get(f"news_{g}")) else float(row.get(f"news_{g}"))}
                          for g in LABELS), key=lambda dd: abs(dd["group_shap"]), reverse=True)
        nn = row.get("news_n")
        return served, out, status, drivers, checks, other_pct, (int(nn) if pd.notna(nn) else 0)

    provinces = {p: {"provinceCode": p, "name": L.NAMES[p], "pastForecasts": [], "earlierForecasts": [], "pastDrivers": {}}
                 for p in L.PROVS}
    for tq in sorted(set(P.index.get_level_values("t"))):
        fx = E.price_forecast(d, X, B, tq)
        cal = None if arm == "R0" else E.fit_calibrator(fx["oof"]["p_oof"], fx["oof"]["y_oof"], arm)
        q = L.qs(tq + 2)
        for i, p in enumerate(L.PROVS):
            served, out, status, drivers, checks, opct, nn = explain(fx, cal, tq, i, p)
            ref = float(P.loc[(tq, p), f"{arm}_p"])
            assert abs(served - ref) < 1e-9, (q, p, served, ref)
            checks["probability_reproduction_error"] = abs(served - ref)
            entry = {"origin": str(L.origin(tq).date()), "originQuarter": L.qs(tq), "probability": round(served, 4),
                     "informationCutoff": {"cpiThrough": L.ym_s(L.m0_of(tq)), "typhoonsAndNewsThrough": L.qs(tq),
                                           "productionLfsRemittancesThrough": L.qs(tq - 1)},
                     "checks": checks, "calibrator": cal,
                     "fiveTriggerContributions": {g: {k: v for k, v in c.items() if k not in ("status", "inputsPresent")}
                                                  for g, c in out.items() if g in LABELS},
                     "otherContribution": {**out["other"], "inputs": "total news article volume (news_n)"},
                     "triggerStatus": status,
                     "drivers": {"drivers": drivers, "article_count": nn, "other_pct": opct, "evidence_quarter": L.qs(tq)}}
            v = provinces[p]
            if tq == oper:
                v.update({"forecast": {"targetQuarter": q, "lead": 2, "scoreType": "food_price_pressure_probability",
                                       "kind": "FORECAST (outcome not yet known)", "probability": served, "band": band(served),
                                       "decisionThreshold": 0.5, "decision": "HIGH" if served >= 0.5 else "LOW",
                                       "servedModel": f"E53 food-price-pressure model, arm {arm}",
                                       "components": {"foodInflationForecast": round(float(fx["F_hat"][i]), 2),
                                                      "foodMinusHeadlineForecast": round(float(fx["G_hat"][i]), 2)},
                                       "explanation": (f"{L.NAMES[p]}, {q} (forecast issued {entry['origin']}): estimated "
                                                       f"probability that food-price pressure is HIGH {served:.0%} "
                                                       f"({'HIGH' if served >= 0.5 else 'LOW'} at p >= 0.5). Food inflation is "
                                                       f"forecast at {fx['F_hat'][i]:.1f}% and food minus headline at "
                                                       f"{fx['G_hat'][i]:+.1f} points.")},
                          **{k: entry[k] for k in ("fiveTriggerContributions", "otherContribution", "triggerStatus",
                                                   "drivers", "checks", "calibrator")},
                          "observed": e43["provinces"][p]["observed"],
                          "operational": {"category": band(served), "alertCandidate": band(served) == "High"}})
            else:
                rec_ = {"targetQuarter": q, "probability": round(served, 3), "origin": entry["origin"],
                        "decision": "HIGH" if served >= 0.5 else "LOW"}
                if (p, tq + 2) in ps and tq + 2 <= oper:
                    v["pastForecasts"].append(rec_ | {"observedHigh": bool(ps[(p, tq + 2)])})
                else:
                    v["earlierForecasts"].append(rec_)
                v["pastDrivers"][q] = entry
    m = res["metrics"][arm]
    for v in provinces.values():
        v["pastForecastsNote"] = ("Development backtest of the E53 procedure at each past origin (only information "
                                  "published before that origin); not forecasts issued live, and these quarters were "
                                  "examined while the model was designed.")
        v["warnings"] = ["EXPERIMENTAL: development evidence only (E53); acceptance requires the prospective quarters "
                         "2027-Q1..Q4.", "Food-price pressure is not hunger and not verified household food insecurity.",
                         "Employment, OFW and ENSO evidence are national.", "Target PS needs adviser approval.",
                         "Not LightGBM: the Chapter 1 model-family deviation needs adviser approval (E53 report)."]
    pick = lambda mm: {k: (None if mm.get(k) is None else round(float(mm[k]), 3)) for k in  # noqa: E731
                       ("accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "precision_HIGH", "f1_HIGH", "brier", "auc")}
    t0 = sorted(set(P.index.get_level_values("t")))
    body = {
        "schema": "e53/1", "name": f"aiPHeed provincial food-price pressure forecast (E53 arm {arm}, experimental)",
        "status": "EXPERIMENTAL - development evidence, not independently validated; enabled only with AIPHEED_LEAD2_MODEL=e53",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modelVersion": f"E53-{arm} = E46-I7 price component" + ("" if arm == "R0" else f" + {arm} calibration") +
                        f" (E53 protocol sha {proto[:16]})",
        "origin": str(L.origin(oper).date()), "originQuarter": L.qs(oper), "targetQuarter": L.qs(oper + 2),
        "lead": 2, "leadFromOrigin": 2,
        "information": {"cpiMonthsThrough": L.ym_s(L.m0_of(oper)), "rule": "only data published before the origin"},
        "indicator": {"id": "food_price_pressure_probability", "name": "Food-Price Pressure Probability (experimental)",
                      "definition": SCORE_DEF, "unit": "probability (0-1)",
                      "horizon": f"Lead 2: issued {L.origin(oper).date()} (latest completed quarter {L.qs(oper)}) for "
                                 f"{L.qs(oper + 2)}; experimental (E53)",
                      "source": "PSA provincial food and headline CPI and wholesale rice; typhoon tracks and ENSO; PSA "
                                "production; PSA LFS (national); BSP remittances and ECB USD/PHP (national); news; "
                                "official rice-policy orders",
                      "caveat": "Food-price pressure, not food insecurity. Development evidence only (E53), not "
                                "independently validated. Indicative decision support only."},
        "scoreTypes": {"food_price_pressure_probability": SCORE_DEF},
        "attributionMethod": ("Log-odds change of the served probability when each trigger group's inputs are set to "
                              "their training mean, all else fixed. Market / Prices includes the projected food "
                              "inflation and gap built from PSA CPI and the rice-policy orders; each group includes its "
                              "own news share; total news volume is reported as other. Model attributions, not causes."),
        "operationalRules": {"band": "Low if P < 0.33; Watch if 0.33 <= P < 0.67; High if P >= 0.67",
                             "decision": "HIGH if P >= 0.5 (fixed)", "alert": "Alert candidate when the band is High; "
                             "staged for administrator confirmation.", "municipal": "No municipal probability; LGU "
                             "rankings are relative prioritization."},
        "provinces": provinces,
        "assessment": {"forecastingAcceptanceMet": False, "arm": arm,
                       "E53": {"rows": res["rows"], "HIGH": res["HIGH"], "metrics": pick(m),
                               "calibration_in_the_large": res["calibration"][arm]["citl"],
                               "criteria": res["criteria"].get(arm), "decision": res["decision"]},
                       "evidenceStatus": res["evidence_status"]},
        "limitations": ["Development evidence only; independent test = 2027-Q1..Q4 (frozen).",
                        "Target PS needs adviser approval; it measures food-price pressure, not food insecurity.",
                        "Employment, OFW, ENSO and policy inputs are national; 2026 BSP remittances are not in the dataset."],
        "sources": {"evaluation_run": run.name, "e53_protocol_sha256": proto, "origins": [L.qs(t) for t in t0]},
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, indent=1, default=str), encoding="utf-8")
    print(OUT, arm, body["content_sha256"][:16], {v["name"]: (round(v["forecast"]["probability"], 3), v["forecast"]["decision"],
                                                             [dd["driver_group"] for dd in v["drivers"]["drivers"][:3]],
                                                             v["drivers"]["other_pct"]) for v in provinces.values()})


if __name__ == "__main__":
    main()

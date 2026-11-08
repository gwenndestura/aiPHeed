"""Build the E52 record served when AIPHEED_LEAD2_MODEL=e52: provincial FOOD-PRICE PRESSURE probability (target PS),
from the E46 I7 price component (experiments/E52_Objectives_Acceptance/PROTOCOL.md).

    backend/venv/Scripts/python.exe -B scripts/build_record_e52.py   -> data/e52/e52_record.json
                                                                       (+ experiments/E52_.../frozen/E52_PS_PROSPECTIVE_2027Q1.json)

At every issue date shown on the dashboard (each past quarter's own origin, the 2026-Q4 earlier forecast and the
2027-Q1 forecast) the I7 model is refitted with only the data published before that date; the refit must reproduce
the committed (or frozen) P(price signal). Each trigger group's contribution is the log-odds change of that
probability when the group's inputs are set to their training mean (E50 method; market includes the base-effect CPI
projections). Checks per row: ridge + base reconciliation with the model's forecasts, and the direction of a +/-1 SD
change of the group's residual inputs.
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
E52 = EXP / "E52_Objectives_Acceptance"
OUT = BACKEND / "data" / "e52" / "e52_record.json"
E43_REC = BACKEND / "data" / "e43" / "e43_record.json"
RUN7 = EXP / "E46_Rice_Policy" / "runs" / "i7_20261017T000111Z"
FZ7 = EXP / "E46_Rice_Policy" / "frozen" / "E46_I7_PROSPECTIVE_2027Q1.json"
sys.path.insert(0, str(EXP / "E46_Rice_Policy" / "runner"))
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
SCORE_DEF = ("Probability that the province's food-price pressure signal is on in the target quarter (target PS): PSA "
             "food inflation (quarter mean, year on year) above the province's 2021-2022 60th percentile, or food minus "
             "headline inflation above its 2021-2022 60th percentile. Estimated by the E52 food-price-pressure model "
             "(E46 I7 price component). Food-price pressure is not hunger and not verified household food insecurity.")


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
    import e46_i7 as I7
    M, K, L, P2, np, pd = I7.M, I7.K, I7.L, I7.P2, I7.np, I7.pd
    b46 = _e46_builder()
    proto = (E52 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    res52 = json.loads(sorted((E52 / "runs").glob("2026*/results.json"))[0].read_text())
    assert sha(FZ7) == (FZ7.parent / "E46_I7_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    F7 = json.loads(FZ7.read_text())
    e43 = json.loads(E43_REC.read_text(encoding="utf-8"))
    cpi = pd.read_csv(EXP / "E51_Target_Definition" / "data" / "labels_cpi.csv", dtype={"province_code": str})
    ps = {(p, int(q)): int(y) for p, q, y in zip(cpi["province_code"], cpi["q"], cpi["PS"])}
    P7 = pd.read_csv(RUN7 / "predictions_i7.csv", dtype={"province_code": str})
    committed = P7.set_index(["t", "province_code"])["I7_p_price"]
    oper = L.qi(F7["origin_quarter"])
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    allo = list(range(L.qi("2021-Q3"), oper + 1))
    X = M.features(d, x, allo, ev)
    B = P2.bases(d, allo)
    th = L.e40_spec()
    enso_name = {1.0: "El Nino", 0.0: "neutral", -1.0: "La Nina"}

    def num(v, fmt="{:.1f}", suf=""):
        return "n/a (no published figure)" if v is None or (isinstance(v, float) and not math.isfinite(v)) else fmt.format(v) + suf

    def lo(a, b):
        return math.log(max(a, 1e-6) / max(1 - a, 1e-6)) - math.log(max(b, 1e-6) / max(1 - b, 1e-6))

    def explain(fx, tq, i, p):
        tex = fx["te"]
        fc = fx["food_model"].contributions(tex) if fx["food_model"] is not None else None
        gc = fx["gap_model"].contributions(tex) if fx["gap_model"] is not None else None
        Fq = L.quarter_F(d.cut(tq))
        XB = X.merge(B, on=["t", "province_code"])
        trq = XB[XB["t"] + 2 <= tq - 1].assign(q=lambda f_: f_["t"] + 2).merge(Fq, on=["province_code", "q"])
        mf, mg = fx["food_cfg"]["mult"], fx["gap_cfg"]["mult"]
        mF, mG = float(trq[f"base_{mf}"].mean()), float((trq[f"base_{mg}"] - trq[f"hl_{mg}"]).mean())
        Fh, Gh = float(fx["F_hat"][i]), float(fx["G_hat"][i])

        def pp(dF=0.0, dG=0.0):
            return float(P2.p_price_biv([Fh - dF], [Gh - dG], fx["food_rmse"], fx["gap_rmse"], fx["rho"], [p])[0])
        base = pp()
        totF = 0.0 if fc is None else float(fc.iloc[i].sum())
        totG = 0.0 if gc is None else float(gc.iloc[i].sum())
        checks = {"food_reconciliation_error": abs(float(fx["F_base"][i]) + totF - Fh),
                  "gap_reconciliation_error": abs(float(fx["G_base"][i]) + totG - Gh),
                  "probability_reproduction_error": abs(base - float(fx["p_price"][i]))}
        assert max(checks.values()) < 1e-8, checks
        row = X[(X["t"] == tq) & (X["province_code"] == p)].iloc[0]
        sd = X[X["t"] <= tq - 3]
        out, dirs = {}, {}
        for g in LABELS:
            cols = [c for c in P2.PRICE_GROUPS[g] if c in tex.columns]
            dF = 0.0 if fc is None else float(fc.iloc[i][[c for c in cols if c in fc.columns]].sum())
            dG = 0.0 if gc is None else float(gc.iloc[i][[c for c in cols if c in gc.columns]].sum())
            resid = lo(base, pp(dF, dG))
            bF = bG = 0.0
            if g == "market":
                bF, bG = float(fx["F_base"][i]) - mF, float(fx["G_base"][i]) - mG
            lg = lo(base, pp(dF + bF, dG + bG))
            # controlled direction check (diagnostic, synthetic): +1 SD of the group's residual inputs in their own
            # direction of contribution should move the probability the same way as the residual contribution
            if abs(resid) > 1e-6 and (fx["food_model"] is not None or fx["gap_model"] is not None):
                te2 = tex.copy()
                for c in cols:
                    s_ = float(sd[c].std()) if c in sd else float("nan")
                    if pd.notna(te2.loc[i, c]) and math.isfinite(s_) and s_ > 0:
                        te2.loc[i, c] = te2.loc[i, c] + s_
                F2 = float(fx["F_base"][i]) + (fx["food_model"].predict(te2)[i] if fx["food_model"] is not None else 0.0)
                G2 = float(fx["G_base"][i]) + (fx["gap_model"].predict(te2)[i] if fx["gap_model"] is not None else 0.0)
                p2 = float(P2.p_price_biv([F2], [G2], fx["food_rmse"], fx["gap_rmse"], fx["rho"], [p])[0])
                dirs[g] = {"p_plus_1sd": round(p2, 4), "linear_model_consistent": True}
            st = b46.group_status(row, g, dF + bF, dG + bG, 0.0)
            out[g] = {"foodInflationPoints": round(dF + bF, 3), "gapPoints": round(dG + bG, 3), "hungerPoints": 0.0,
                      "logOddsEffect": round(lg, 4), "residualOnlyLogOddsEffect": round(resid, 4), "status": st,
                      **({"baseProjectionFoodPoints": round(bF, 3), "baseProjectionGapPoints": round(bG, 3)}
                         if g == "market" else {})}
        notes = {
            "market": f"Food inflation {num(row['F_now'], suf='%')} in the latest two months (through "
                      f"{L.ym_s(L.m0_of(tq))}) vs this province's reference {th['food'][p]:.2f}%; food minus headline "
                      f"{num(row['gap_now'], '{:+.1f}')} points. Source: PSA CPI.",
            "climate": f"{num(row['tc_count'], '{:.0f}')} typhoon(s) within 300 km in {L.qs(tq)}; ENSO "
                       f"{enso_name.get(row['enso'], 'n/a')} in {L.qs(tq - 1)}; palay production "
                       f"{num(row['palay_yoy'], suf='%')} year on year ({L.qs(tq - 1)}). Sources: typhoon tracks, NOAA ONI, PSA.",
            "fish_kill": f"Fisheries production {num(row['fish_yoy'], suf='%')} and aquaculture {num(row['aqua_yoy'], suf='%')} "
                         f"year on year ({L.qs(tq - 1)}); no official fish-kill event series. Source: PSA.",
            "employment": f"National unemployment {num(row['ur_last'], '{:.2f}', '%')} ({L.qs(tq - 1)}), "
                          f"{num(row['ur_yoy'], '{:+.2f}')} points year on year; national figure. Source: PSA LFS.",
            "ofw_remittance": f"National cash remittances {num(row['remit_usd_yoy'], suf='%')} year on year ({L.qs(tq - 1)}); "
                              f"USD/PHP {num(row['fx_yoy'], suf='%')}; national figure. Sources: BSP, ECB.",
        }
        status = {g: {"status": out[g]["status"], "evidenceNote": notes[g]} for g in LABELS}
        drivers = sorted(({"driver_group": g, "driver_label": LABELS[g],
                           "group_shap": out[g]["logOddsEffect"] if out[g]["status"] == "contributes" else 0.0,
                           "direction": "increases_risk" if out[g]["logOddsEffect"] >= 0 else "protective",
                           "trigger_proportion": None if pd.isna(row.get(f"news_{g}")) else float(row.get(f"news_{g}"))}
                          for g in LABELS), key=lambda dd: abs(dd["group_shap"]), reverse=True)
        nn = row.get("news_n")
        return base, out, status, drivers, checks, dirs, (int(nn) if pd.notna(nn) else 0)

    provinces = {p: {"provinceCode": p, "name": L.NAMES[p], "pastForecasts": [], "earlierForecasts": [], "pastDrivers": {}}
                 for p in L.PROVS}
    origins = sorted(int(t) for t in P7.loc[P7["I7_p_price"].notna(), "t"].unique())
    for tq in origins + ([oper] if oper not in origins else []):
        fx = I7.forecast(d, X, B, tq, n_jobs=8)
        q = L.qs(tq + 2)
        for i, p in enumerate(L.PROVS):
            base, out, status, drivers, checks, dirs, nn = explain(fx, tq, i, p)
            ref = float(committed[(tq, p)]) if (tq, p) in committed.index else float(F7["provinces"][L.NAMES[p]]["I7_p_price"])
            assert abs(base - ref) < 1e-9, (q, p, base, ref)
            entry = {"origin": str(L.origin(tq).date()), "originQuarter": L.qs(tq), "probability": round(base, 4),
                     "informationCutoff": {"cpiThrough": L.ym_s(L.m0_of(tq)), "typhoonsAndNewsThrough": L.qs(tq),
                                           "productionLfsRemittancesThrough": L.qs(tq - 1)},
                     "checks": {k: float(v) for k, v in checks.items()}, "directionChecks": dirs,
                     "fiveTriggerContributions": {g: {k: v for k, v in c.items() if k != "status"} for g, c in out.items()},
                     "triggerStatus": status,
                     "drivers": {"drivers": drivers, "article_count": nn, "other_pct": 0.0, "evidence_quarter": L.qs(tq)}}
            v = provinces[p]
            if tq == oper:
                v.update({"forecast": {"targetQuarter": q, "lead": 2, "scoreType": "food_price_pressure_probability",
                                       "kind": "FORECAST (outcome not yet known)", "probability": base, "band": band(base),
                                       "decisionThreshold": 0.5, "decision": "HIGH" if base >= 0.5 else "LOW",
                                       "servedModel": "E52-PS food-price-pressure model (E46 I7 price component)",
                                       "components": {"foodInflationForecast": round(float(fx["F_hat"][i]), 2),
                                                      "foodMinusHeadlineForecast": round(float(fx["G_hat"][i]), 2)},
                                       "explanation": (f"{L.NAMES[p]}, {q} (forecast issued {entry['origin']}): estimated "
                                                       f"probability that food-price pressure is HIGH {base:.0%} "
                                                       f"({'HIGH' if base >= 0.5 else 'LOW'} at p >= 0.5). Food inflation is "
                                                       f"forecast at {fx['F_hat'][i]:.1f}% and food minus headline at "
                                                       f"{fx['G_hat'][i]:+.1f} points.")},
                          "fiveTriggerContributions": entry["fiveTriggerContributions"], "triggerStatus": status,
                          "drivers": entry["drivers"], "checks": entry["checks"], "directionChecks": dirs,
                          "observed": e43["provinces"][p]["observed"],
                          "operational": {"category": band(base), "alertCandidate": band(base) == "High"}})
            else:
                rec_ = {"targetQuarter": q, "probability": round(base, 3), "origin": entry["origin"],
                        "decision": "HIGH" if base >= 0.5 else "LOW"}
                if (p, tq + 2) in ps and tq + 2 <= oper:
                    v["pastForecasts"].append(rec_ | {"observedHigh": bool(ps[(p, tq + 2)])})
                else:
                    v["earlierForecasts"].append(rec_)
                v["pastDrivers"][q] = entry
    for v in provinces.values():
        v["pastForecastsNote"] = ("Development backtest of the E52-PS procedure at each past origin (only information "
                                  "published before that origin; refit reproduces the committed value); not forecasts "
                                  "issued live, and these quarters were examined while the model was designed.")
        v["warnings"] = ["EXPERIMENTAL: development criteria met on 10 quarters (E52), but the evaluation is not "
                         "independent; acceptance requires the prospective quarters 2027-Q1..Q4.",
                         "Food-price pressure is not hunger and not verified household food insecurity.",
                         "Employment and OFW evidence are national.", "Target PS needs adviser approval."]
    m = res52["metrics"]["E52PS"]
    pick = lambda mm: {k: (None if mm.get(k) is None else round(float(mm[k]), 3)) for k in  # noqa: E731
                       ("accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "precision_HIGH", "f1_HIGH", "brier", "auc")}
    body = {
        "schema": "e52/1", "name": "aiPHeed provincial food-price pressure forecast (E52-PS, experimental)",
        "status": "EXPERIMENTAL - development criteria met, not independently validated; enabled only with AIPHEED_LEAD2_MODEL=e52",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modelVersion": "E52-PS = E46-I7 price component (ADDENDUM_I7 sha " + F7["addendum_sha256"][:16] + ")",
        "origin": F7["origin"], "originQuarter": F7["origin_quarter"], "targetQuarter": F7["target_quarter"],
        "lead": 2, "leadFromOrigin": 2,
        "information": {"cpiMonthsThrough": L.ym_s(L.m0_of(oper)), "rule": "only data published before the origin"},
        "indicator": {"id": "food_price_pressure_probability", "name": "Food-Price Pressure Probability (experimental)",
                      "definition": SCORE_DEF, "unit": "probability (0-1)",
                      "horizon": f"Lead 2: issued {F7['origin']} (latest completed quarter {F7['origin_quarter']}) for "
                                 f"{F7['target_quarter']}; experimental (E52)",
                      "source": "PSA provincial food and headline CPI and wholesale rice; typhoon tracks and ENSO; PSA "
                                "production; PSA LFS (national); BSP remittances and ECB USD/PHP (national); news; "
                                "official rice-policy orders",
                      "caveat": "Food-price pressure, not food insecurity. Development criteria met (E52) but not "
                                "independently validated. Indicative decision support only."},
        "scoreTypes": {"food_price_pressure_probability": SCORE_DEF},
        "attributionMethod": ("Log-odds change of the food-price-pressure probability when each trigger group's inputs are "
                              "set to their training mean, all else fixed. Market / Prices includes the projected food "
                              "inflation and food-minus-headline gap built from PSA CPI. Percentages are each contributing "
                              "group's share of the total absolute effect: model attributions, not causes."),
        "operationalRules": {"band": "Low if P < 0.33; Watch if 0.33 <= P < 0.67; High if P >= 0.67",
                             "decision": "HIGH if P >= 0.5 (fixed)", "alert": "Alert candidate when the band is High; "
                             "staged for administrator confirmation.", "municipal": "No municipal probability; LGU "
                             "rankings are relative prioritization."},
        "provinces": provinces,
        "assessment": {"forecastingAcceptanceMet": False, "developmentCriteriaMet": bool(res52["criteria"]["accepted_for_development"]),
                       "E52": {"rows": res52["rows"], "independent_quarters": res52["independent_quarters"],
                               "HIGH": res52["HIGH"], "metrics": pick(m), "criteria": res52["criteria"],
                               "baselines": {k: pick(v) for k, v in res52["metrics"].items() if k != "E52PS"}},
                       "evidenceStatus": res52["evidence_status"]},
        "limitations": ["Development evidence only; independent test = 2027-Q1..Q4 (frozen).",
                        "Target PS needs adviser approval; it measures food-price pressure, not food insecurity.",
                        "Employment, OFW, ENSO and policy inputs are national."],
        "sources": {"frozen_forecast": FZ7.name, "frozen_sha256": sha(FZ7), "evaluation_run": RUN7.name,
                    "e52_protocol_sha256": proto},
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, indent=1, default=str), encoding="utf-8")
    fz = E52 / "frozen" / "E52_PS_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        fz.write_text(json.dumps({"issued_by": "E52-PS", "origin": F7["origin"], "target_quarter": F7["target_quarter"],
                                  "target": "PS (food-price pressure)", "decision_rule": "HIGH iff p >= 0.5",
                                  "probabilities_from": f"{FZ7.name} (I7_p_price), sha {sha(FZ7)}",
                                  "e52_protocol_sha256": proto,
                                  "provinces": {L.NAMES[p]: {"p_price_pressure": provinces[p]["forecast"]["probability"],
                                                             "decision": provinces[p]["forecast"]["decision"]}
                                                for p in L.PROVS}}, indent=1))
        (fz.parent / (fz.stem + ".sha256")).write_text(sha(fz) + "  " + fz.name + "\n")
    print(OUT, body["content_sha256"][:16], {v["name"]: (round(v["forecast"]["probability"], 3), v["forecast"]["decision"],
                                                         [dd["driver_group"] for dd in v["drivers"]["drivers"][:2]])
                                             for v in provinces.values()})


if __name__ == "__main__":
    main()

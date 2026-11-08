"""Build the E55 record served when AIPHEED_LEAD2_MODEL=e55: provincial FOOD-INSECURITY RISK probability (target T43,
Chapter I section 1.7: regional SWS hunger above 11.3% AND provincial PSA food-price pressure) from the E55 LightGBM
model (experiments/E55_Food_Insecurity_LightGBM/PROTOCOL.md section 4), with exact TreeSHAP explanations.

    backend/venv/Scripts/python.exe -B scripts/build_record_e55.py   -> data/e55/e55_record.json

At every issue date (each past quarter's own origin, the 2026-Q4 earlier forecast, the 2027-Q1 forecast) the model is
refitted with only data published before that date and must reproduce the E55 run's probability (< 1e-9).

Explanation (PROTOCOL section 9): P = P_hunger x P_price. The price part's log-odds is decomposed exactly:
    logit P_price = baseline + Market projection (CPI base-effect offset minus its training mean) + sum_g TreeSHAP_g
with LightGBM pred_contrib (TreeSHAP); each feature's value goes to its trigger group (rice policy -> Market,
news_<group> -> that group, news volume -> other, poverty -> poverty). The regional hunger gate is reported as its own
factor. Reconstruction error < 1e-9 on every entry.
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
E55 = EXP / "E55_Food_Insecurity_LightGBM"
OUT = BACKEND / "data" / "e55" / "e55_record.json"
E43_REC = BACKEND / "data" / "e43" / "e43_record.json"
sys.path.insert(0, str(E55 / "runner"))
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
CONTRIBUTES = 0.05          # |grouped log-odds effect| at or above which a group "contributes" (PROTOCOL section 9)
SCORE_DEF = ("Probability that the province is at HIGH food-insecurity risk in the target quarter (target T43, Chapter I "
             "section 1.7): the regional SWS hunger rate (Balance Luzon) above 11.3% AND provincial food-price pressure "
             "(PSA food inflation, or food minus headline inflation, above the province's 2021-2022 60th percentile). "
             "Estimated by the E55 LightGBM model. It is a risk classification, not a measured prevalence of household "
             "food insecurity; hunger is measured only for the whole region.")


def band(p: float) -> str:
    return "High" if p >= 2 / 3 else ("Watch" if p >= 1 / 3 else "Low")


def _e46_builder():
    spec = importlib.util.spec_from_file_location("b46", BACKEND / "scripts" / "build_record_e46.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    import e55_lib as F
    L, np, pd = F.L, F.np, F.pd
    b46 = _e46_builder()
    run = sorted(p for p in (E55 / "runs").glob("2026*") if (p / "results.json").exists())[0]
    res = json.loads((run / "results.json").read_text())
    sel = json.loads((run / "selections.json").read_text())
    arm = res["served_arm"]
    kw = {"E55-LGBM": {}, "POV-AS": {"pov": "AS"}}[arm]
    proto = (E55 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    P = pd.read_csv(run / "predictions.csv", dtype={"province_code": str})
    P = P[P["arm"] == arm].set_index(["t", "province_code"])
    e43 = json.loads(E43_REC.read_text(encoding="utf-8"))
    d, X, B = F.E.load()
    Y = F.t43_labels(d)
    t43 = {(p, int(q)): int(v) for p, q, v in zip(Y["province_code"], Y["q"], Y["T43"]) if v == v}
    th = L.e40_spec()
    enso_name = {1.0: "El Nino", 0.0: "neutral", -1.0: "La Nina"}
    oper = int(P.index.get_level_values("t").max())

    def num(v, fmt="{:.1f}", suf=""):
        return ("n/a (not in the dataset at the issue date)" if v is None or (isinstance(v, float) and not math.isfinite(v))
                else fmt.format(v) + suf)

    def news_share(row, g):
        v = row.get(f"news_{g}")
        return "" if v is None or not math.isfinite(float(v)) else f" News tagged {LABELS[g]}: {v:.0%} of articles."

    def explain(fx, tq, i, p):
        a = F.attribution(fx, i)
        assert a["error"] < 1e-9, a["error"]
        row = fx["te"].iloc[i]
        out = {}
        for g in list(LABELS) + ["poverty", "other"]:
            eff = float(a["groups"].get(g, 0.0))
            out[g] = {"logOddsEffect": round(eff, 4)}
            if g == "market":
                out[g]["cpiProjectionLogOdds"] = round(a["offset"] - a["offset_train_mean"], 4)
            if g in LABELS:
                obs = b46.OBSERVED_INPUTS[g]
                present = [c for c in obs if row.get(c) is not None and math.isfinite(float(row.get(c)))]
                out[g]["inputsPresent"] = round(len(present) / len(obs), 3)
                out[g]["status"] = ("insufficient_data" if not present else
                                    ("contributes" if abs(eff) >= CONTRIBUTES else "no_effect"))
        notes = {
            "market": f"Food inflation {num(row['F_now'], suf='%')} in the latest two months (through {L.ym_s(L.m0_of(tq))}) "
                      f"vs this province's reference {th['food'][p]:.2f}%; food minus headline {num(row['gap_now'], '{:+.1f}')} "
                      f"points; the projected food inflation for the target quarter and rice-policy orders in force are "
                      f"included. Source: PSA CPI, DA/BOC orders." + news_share(row, "market"),
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
        shown = [g for g in LABELS if out[g]["status"] == "contributes"]
        tot = sum(abs(out[g]["logOddsEffect"]) for g in shown) + abs(out["other"]["logOddsEffect"]) + abs(out["poverty"]["logOddsEffect"])
        other_pct = round(100 * (abs(out["other"]["logOddsEffect"]) + abs(out["poverty"]["logOddsEffect"])) / tot, 1) if tot > 0 else 0.0
        drivers = sorted(({"driver_group": g, "driver_label": LABELS[g],
                           "group_shap": out[g]["logOddsEffect"] if out[g]["status"] == "contributes" else 0.0,
                           "direction": "increases_risk" if out[g]["logOddsEffect"] >= 0 else "protective",
                           "trigger_proportion": None if pd.isna(row.get(f"news_{g}")) else float(row.get(f"news_{g}"))}
                          for g in LABELS), key=lambda dd: abs(dd["group_shap"]), reverse=True)
        nn = row.get("news_n")
        return a, out, status, drivers, other_pct, (int(nn) if pd.notna(nn) else 0)

    provinces = {p: {"provinceCode": p, "name": L.NAMES[p], "pastForecasts": [], "earlierForecasts": [], "pastDrivers": {}}
                 for p in L.PROVS}
    for tq in sorted(set(P.index.get_level_values("t"))):
        fx = F.lgbm_forecast(d, X, B, tq, **kw)
        assert fx["cfg"] == sel[arm][L.qs(tq)]["cfg"], (tq, fx["cfg"])
        q = L.qs(tq + 2)
        for i, p in enumerate(L.PROVS):
            served = float(fx["p"][i])
            ref = float(P.loc[(tq, p), "p"])
            assert abs(served - ref) < 1e-9, (q, p, served, ref)
            a, out, status, drivers, opct, nn = explain(fx, tq, i, p)
            entry = {"origin": str(L.origin(tq).date()), "originQuarter": L.qs(tq), "probability": round(served, 4),
                     "probabilityPricePressure": round(float(fx["p_price"][i]), 4),
                     "probabilityHungerElevated": round(float(fx["p_hunger"]), 4),
                     "informationCutoff": {"cpiThrough": L.ym_s(L.m0_of(tq)), "typhoonsAndNewsThrough": L.qs(tq),
                                           "productionLfsRemittancesThrough": L.qs(tq - 1),
                                           "swsHungerPostedBefore": str(L.origin(tq).date())},
                     "checks": {"probability_reproduction_error": abs(served - ref), "treeshap_reconstruction_error": a["error"]},
                     "modelConfig": fx["cfg"],
                     "fiveTriggerContributions": {g: {k: v for k, v in c.items() if k not in ("status", "inputsPresent")}
                                                  for g, c in out.items() if g in LABELS},
                     "otherContribution": {**out["other"], "inputs": "total news article volume (news_n)"},
                     "povertyContribution": {**out["poverty"],
                                             "inputs": "PSA 2021 municipal SAE poverty, province mean" if kw.get("pov") else
                                                       "not a model input (E55: poverty did not improve the forecast)"},
                     "baselineLogOdds": round(a["baseline"], 4),
                     "hungerGate": {"probabilityAbove11_3": round(float(fx["p_hunger"]), 4),
                                    "forecastH": round(float(fx["H_hat"]), 2),
                                    "note": "Regional SWS hunger (Balance Luzon), one value for all five provinces."},
                     "triggerStatus": status,
                     "drivers": {"drivers": drivers, "article_count": nn, "other_pct": opct, "evidence_quarter": L.qs(tq)}}
            v = provinces[p]
            if tq == oper:
                v.update({"forecast": {"targetQuarter": q, "lead": 2, "scoreType": "food_insecurity_risk_probability",
                                       "kind": "FORECAST (outcome not yet known)", "probability": served, "band": band(served),
                                       "decisionThreshold": 0.5, "decision": "HIGH" if served >= 0.5 else "LOW",
                                       "servedModel": f"E55 LightGBM food-insecurity model ({arm})",
                                       "components": {"probabilityHungerElevated": round(float(fx["p_hunger"]), 4),
                                                     "probabilityPricePressure": round(float(fx["p_price"][i]), 4)},
                                       "explanation": (f"{L.NAMES[p]}, {q} (forecast issued {entry['origin']}): estimated "
                                                       f"probability of HIGH food-insecurity risk {served:.0%} "
                                                       f"({'HIGH' if served >= 0.5 else 'LOW'} at p >= 0.5) = probability "
                                                       f"that regional hunger stays above 11.3% ({float(fx['p_hunger']):.0%}) x "
                                                       f"probability of provincial food-price pressure ({float(fx['p_price'][i]):.0%}).")},
                          **{k: entry[k] for k in ("fiveTriggerContributions", "otherContribution", "povertyContribution",
                                                   "hungerGate", "baselineLogOdds", "triggerStatus", "drivers", "checks",
                                                   "modelConfig")},
                          "observed": e43["provinces"][p]["observed"],
                          "operational": {"category": band(served), "alertCandidate": band(served) == "High"}})
            else:
                rec_ = {"targetQuarter": q, "probability": round(served, 3), "origin": entry["origin"],
                        "decision": "HIGH" if served >= 0.5 else "LOW"}
                if (p, tq + 2) in t43 and tq + 2 <= oper:
                    v["pastForecasts"].append(rec_ | {"observedHigh": bool(t43[(p, tq + 2)])})
                else:
                    v["earlierForecasts"].append(rec_)
                v["pastDrivers"][q] = entry
    m = res["metrics"][arm]
    acc_ok = res["criteria"][arm]["criteria"]["accepted_for_development"]
    for v in provinces.values():
        v["pastForecastsNote"] = ("Development backtest of the E55 LightGBM procedure at each past origin (only "
                                  "information published before that origin); not forecasts issued live, and these "
                                  "quarters were examined in earlier experiments.")
        v["warnings"] = ["EXPERIMENTAL: development evidence only (E55); independent test = the frozen 2027-Q1..Q4 forecasts.",
                         "Hunger is measured only for the whole region (SWS Balance Luzon); provincial differences come "
                         "from food prices.", "Employment, OFW and ENSO evidence are national.",
                         "Target T43 (single quarter, no sustain rule) needs adviser approval."]
        if not acc_ok:
            v["warnings"].append("The E55 development acceptance criteria (A1-A5) were not all met; see the E55 report.")
    pick = lambda mm: {k: (None if mm.get(k) is None else round(float(mm[k]), 3)) for k in  # noqa: E731
                       ("accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "precision_HIGH", "f1_HIGH", "brier", "auc")}
    body = {
        "schema": "e55/1", "name": f"aiPHeed provincial food-insecurity risk forecast (E55 LightGBM, {arm}, experimental)",
        "status": "EXPERIMENTAL - development evidence, not independently validated; enabled only with AIPHEED_LEAD2_MODEL=e55",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modelVersion": f"E55-{arm}: LightGBM price-signal classifier (structural CPI offset, intercept-free stumps) x "
                        f"I7 regional hunger component (E55 protocol sha {proto[:16]})",
        "modelFamily": "LightGBM",
        "origin": str(L.origin(oper).date()), "originQuarter": L.qs(oper), "targetQuarter": L.qs(oper + 2),
        "lead": 2, "leadFromOrigin": 2,
        "information": {"cpiMonthsThrough": L.ym_s(L.m0_of(oper)), "rule": "only data published before the origin"},
        "indicator": {"id": "food_insecurity_risk_probability", "name": "Food-Insecurity Risk Probability (experimental)",
                      "definition": SCORE_DEF, "unit": "probability (0-1)",
                      # the approved frontend renders "This is a {horizon} for {quarter}, based only on ..."
                      "horizon": f"one-quarter-ahead (Lead 2) forecast issued {L.origin(oper).date()}",
                      "source": "SWS hunger (Balance Luzon); PSA provincial food and headline CPI and wholesale rice; "
                                "typhoon tracks and ENSO; PSA production; PSA LFS (national); BSP remittances and ECB "
                                "USD/PHP (national); news; official rice-policy orders",
                      "caveat": "Risk classification from regional hunger and provincial food prices, not a measured "
                                "provincial prevalence. Development evidence only (E55). Indicative decision support only."},
        "scoreTypes": {"food_insecurity_risk_probability": SCORE_DEF},
        "attributionMethod": ("Exact TreeSHAP (LightGBM pred_contrib) of the food-price part of the forecast, in "
                              "log-odds, grouped by trigger; Market / Prices also carries the projected food inflation "
                              "built from PSA CPI (the model's starting point) and the rice-policy orders; each group "
                              "includes its own news share; total news volume is reported as other. A group whose "
                              "inputs were all missing at the issue date is shown as insufficient data. The regional "
                              "hunger part is shown separately. Model attributions, not causes."),
        "operationalRules": {"band": "Low if P < 0.33; Watch if 0.33 <= P < 0.67; High if P >= 0.67",
                             "decision": "HIGH if P >= 0.5 (fixed)", "alert": "Alert candidate when the band is High; "
                             "staged for administrator confirmation.", "municipal": "No municipal probability; LGU "
                             "rankings are relative prioritization weighted by PSA 2021 poverty and 2024 population density."},
        "provinces": provinces,
        "assessment": {"forecastingAcceptanceMet": bool(acc_ok), "arm": arm,
                       "E55": {"rows": res["rows"], "HIGH": res["HIGH"], "metrics": pick(m),
                               "calibration_in_the_large": res["calibration"][arm]["citl"],
                               "criteria": res["criteria"][arm]["criteria"]},
                       "evidenceStatus": res["evidence_status"]},
        "limitations": ["Development evidence only; independent test = 2027-Q1..Q4 (frozen).",
                        "Hunger is regional; on every evaluated quarter (2024-Q2..2026-Q3) it was above 11.3%, so the "
                        "evaluated skill is the food-price part under elevated hunger.",
                        "Employment, OFW, ENSO and policy inputs are national; 2026 BSP remittances are not in the dataset."],
        "sources": {"evaluation_run": run.name, "e55_protocol_sha256": proto,
                    "origins": [L.qs(t) for t in sorted(set(P.index.get_level_values("t")))]},
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, indent=1, default=str), encoding="utf-8")
    print(OUT, arm, body["content_sha256"][:16], {v["name"]: (round(v["forecast"]["probability"], 3), v["forecast"]["decision"],
                                                             [dd["driver_group"] for dd in v["drivers"]["drivers"][:3]],
                                                             v["drivers"]["other_pct"]) for v in provinces.values()})


if __name__ == "__main__":
    main()

"""Build the E56 record served when AIPHEED_LEAD2_MODEL=e56: provincial FOOD-INSECURITY RISK probability (target T43,
Chapter I section 1.7: regional SWS hunger above 11.3% AND provincial PSA food-price pressure), two quarters ahead of
the latest predictor quarter, from the final model of the E56 optimization cycle
(experiments/E56_LightGBM_Optimization/PROTOCOL.md), with exact TreeSHAP explanations, data-freshness disclosure and
the saved final-model artifacts.

    backend/venv/Scripts/python.exe -B scripts/build_record_e56.py   -> data/e56/e56_record.json, data/e56/model/*

At every issue date (each past quarter's own origin, the 2026-Q4 earlier forecast, the 2027-Q1 forecast) the model is
refitted with the configuration that the nested selection chose at that origin, using only data published before that
date, and must reproduce the E56 run's probability (< 1e-9). The 2027-Q1 model is saved (booster text, schema, offset
and hunger parameters, feature rows); tests/integration/test_e56_final_model.py reproduces the served probabilities from
those files alone.

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
E56 = EXP / "E56_LightGBM_Optimization"
OUT = BACKEND / "data" / "e56" / "e56_record.json"
ART = BACKEND / "data" / "e56" / "model"
E43_REC = BACKEND / "data" / "e43" / "e43_record.json"
sys.path.insert(0, str(E56 / "runner"))
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
CONTRIBUTES = 0.05          # |grouped log-odds effect| at or above which a group "contributes" (PROTOCOL section 9)
SCORE_DEF = ("Probability that the province is at HIGH food-insecurity risk in the target quarter (target T43, Chapter I "
             "section 1.7): the regional SWS hunger rate (Balance Luzon) above 11.3% AND provincial food-price pressure "
             "(PSA food inflation, or food minus headline inflation, above the province's 2021-2022 60th percentile). "
             "Estimated by the E56 LightGBM model (two quarters ahead of the latest predictor quarter). It is a risk classification, not a measured prevalence of household "
             "food insecurity; hunger is measured only for the whole region.")


def band(p: float) -> str:
    return "High" if p >= 2 / 3 else ("Watch" if p >= 1 / 3 else "Low")


def _e46_builder():
    spec = importlib.util.spec_from_file_location("b46", BACKEND / "scripts" / "build_record_e46.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    import e56_lib as G
    F = G.F
    L, np, pd = F.L, F.np, F.pd
    b46 = _e46_builder()
    run = sorted(p for p in (E56 / "runs").glob("2026*") if (p / "results.json").exists())[0]
    res = json.loads((run / "results.json").read_text())
    sel = json.loads((run / "selections.json").read_text())
    arm = res["final_model"]
    assert arm == "E56-TUNED", "E55-LGBM retained: serve AIPHEED_LEAD2_MODEL=e55 instead"
    proto = (E56 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    horizon = json.loads((E56 / "tables" / "horizon.json").read_text())
    fresh = pd.read_csv(E56 / "tables" / "data_freshness.csv")
    P = pd.read_csv(run / "predictions.csv", dtype={"province_code": str})
    P = P[P["arm"] == arm].set_index(["t", "province_code"])

    def refit(tq):
        """The selected configuration at origin tq, refitted on data published before O(tq) (no re-search)."""
        c = sel[L.qs(tq)]["cfg"]
        tr, te = F.frame(d, X, B, tq, "AS")
        hc = F.hunger(d, X, tq)
        fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
        mdl = G.PriceLGB2(G.cols_for(c), c).fit(fit)
        pp = mdl.predict(te)
        return {"p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "H_hat": hc["H_hat"], "hc": hc, "cfg": c,
                "model": mdl, "te": te, "tr": fit}

    manifest = {}

    def save_artifacts(fx, tq):
        """Final model at the operational origin: everything needed to recompute the served probabilities without the
        training code (LightGBM booster, offset and hunger parameters, ordered feature schema, feature rows)."""
        ART.mkdir(parents=True, exist_ok=True)
        mdl, te, c, hc = fx["model"], fx["te"], fx["cfg"], fx["hc"]
        th = L.e40_spec()
        txt = mdl.model.booster_.model_to_string().replace("\r\n", "\n")
        (ART / "booster.txt").write_bytes(txt.encode("utf-8"))
        audit = pd.read_csv(E55 / "tables" / "feature_audit.csv").set_index("feature")
        schema = [{"name": col, "group": F.group_of(col),
                   "source": str(audit.loc[col, "source"]) if col in audit.index else "",
                   "reference_at_issue": str(audit.loc[col, "reference_at_issue"]) if col in audit.index else ""}
                  for col in mdl.feat]
        (ART / "feature_schema.json").write_text(json.dumps({"features": schema, "missing": "native LightGBM (NaN)"}, indent=1))
        (ART / "config.json").write_text(json.dumps({"configuration": c, "lgb_fixed": dict(F.LGB_BASE),
                                                    "decision_threshold": 0.5, "origin": str(L.origin(tq).date()),
                                                    "target_quarter": L.qs(tq + 2)}, indent=1, default=str))
        sF, sG, rho = mdl.scale
        (ART / "offset.json").write_text(json.dumps({
            "drift_multiplier": mdl.m, "food_rmse": sF, "gap_rmse": sG, "error_correlation": float(np.clip(rho, -0.95, 0.95)),
            "logit_clip": F.ZCLIP, "tree_mean_constant": mdl.c,
            "threshold_food": th["food"], "threshold_gap": th["gap"],
            "formula": "p_struct = 1 - BVN_cdf([(thr_food - base)/food_rmse, (thr_gap - gbase)/gap_rmse], rho); "
                       "init = clip(logit(p_struct), -6, 6); p_price = sigmoid(init + booster_raw - tree_mean_constant)"},
            indent=1))
        hm = hc["model"]
        hcols = [cc for g in F.P2.ALL_GROUPS if g in F.P2.HUNGER_GROUPS for cc in F.P2.HUNGER_GROUPS[g]]
        _, hte = F.P2.hunger_frame(X, F.P2.h_series(d, tq, False), tq, hcols)
        hz = hm._z(hte)
        (ART / "hunger.json").write_text(json.dumps({
            "H_base": float(hte["H_base"].iloc[0]), "z_row": dict(zip(map(str, hz.columns), map(float, hz.iloc[0]))),
            "coef": dict(zip(map(str, hz.columns), map(float, hm.m.coef_))), "intercept": float(hm.m.intercept_),
            "rmse": float(hc["rmse"]), "threshold_H": th["H"], "alpha": hc["alpha"], "H_hat": float(hc["H_hat"]),
            "formula": "H_hat = H_base + intercept + sum(z_row * coef); p_hunger = 1 - Phi((threshold_H - H_hat) / rmse)"},
            indent=1))
        rows = te[["province_code"] + mdl.feat + [f"base_{mdl.m}", f"gbase_{mdl.m}"]].copy()
        rows.to_csv(ART / "features_2027Q1.csv", index=False, float_format="%.17g")
        for f in sorted(ART.glob("*")):
            if f.name != "manifest.json":
                manifest[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        (ART / "manifest.json").write_text(json.dumps(manifest, indent=1))
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
        fx = refit(tq)
        if tq == oper:
            save_artifacts(fx, tq)
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
                                             "inputs": "PSA 2021 municipal SAE poverty, province mean (as-of)" if fx["cfg"]["pov"]
                                                       else "not an input of the configuration selected at this origin"},
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
                                       "servedModel": f"E56 LightGBM food-insecurity model ({arm}, configuration {fx['cfg']['id']})",
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
        v["pastForecastsNote"] = ("Development backtest of the E56 LightGBM procedure at each past origin (only "
                                  "information published before that origin); not forecasts issued live, and these "
                                  "quarters were examined in earlier experiments.")
        v["warnings"] = ["EXPERIMENTAL: development evidence only (E56); independent test = the frozen 2027-Q1..Q4 forecasts.",
                         "Hunger is measured only for the whole region (SWS Balance Luzon); provincial differences come "
                         "from food prices.", "Employment, OFW and ENSO evidence are national.",
                         "Target T43 (single quarter, no sustain rule) needs adviser approval."]
        if not acc_ok:
            v["warnings"].append("The E56 development acceptance criteria (A1-A5) were not all met; see the E56 report.")
    pick = lambda mm: {k: (None if mm.get(k) is None else round(float(mm[k]), 3)) for k in  # noqa: E731
                       ("accuracy", "balanced_accuracy", "recall_HIGH", "precision_HIGH", "recall_LOW", "precision_LOW",
                        "f1_HIGH", "brier", "auc")}
    issue = str(L.origin(oper).date())
    freshness = {
        "issueDate": issue, "predictorQuarter": L.qs(oper), "intermediateQuarter": L.qs(oper + 1),
        "targetQuarter": L.qs(oper + 2), "horizonQuarters": 2,
        "latestTargetQuarterKnownAtIssue": horizon["latest_target_label_known_at_issue"],
        "latestTargetQuarterInData": horizon["latest_target_label_quarter_in_data"],
        "latestPredictorPeriods": {r.dataset: r.latest_used_for_2027Q1_forecast for r in fresh.itertuples()},
        "latestObservationInData": {r.dataset: r.latest_observation_in_dataset for r in fresh.itertuples()},
        "note": ("Target data (SWS hunger and PSA CPI) were known through " + horizon["latest_target_label_known_at_issue"]
                 + " at the issue date; predictors run through " + L.qs(oper) + " (CPI through "
                 + horizon["latest_cpi_month_used"] + "). The 2026-Q3 SWS round and September 2026 CPI were released after "
                 "the issue date and are not used. Direct food-insecurity surveys (FNRI FIES, PSA subsistence) end in 2023.")}
    body = {
        "schema": "e56/1", "name": "aiPHeed provincial food-insecurity risk forecast (E56 LightGBM, experimental)",
        "status": "EXPERIMENTAL - development evidence, not independently validated; enabled only with AIPHEED_LEAD2_MODEL=e56",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modelVersion": f"E56-TUNED: LightGBM price-signal classifier (structural CPI offset, intercept-free boosting; "
                        f"configuration chosen per origin by nested chronological validation) x I7 regional hunger "
                        f"component (E56 protocol sha {proto[:16]})",
        "modelFamily": "LightGBM", "finalModelArtifacts": manifest,
        "origin": issue, "originQuarter": L.qs(oper), "targetQuarter": L.qs(oper + 2),
        "lead": 2, "leadFromOrigin": 2, "dataFreshness": freshness,
        "information": {"cpiMonthsThrough": L.ym_s(L.m0_of(oper)), "rule": "only data published before the origin"},
        "indicator": {"id": "food_insecurity_risk_probability", "name": "Food-Insecurity Risk Probability (experimental)",
                      "definition": SCORE_DEF, "unit": "probability (0-1)",
                      # the approved frontend renders "This is a {horizon} for {quarter}, based only on ..."
                      "horizon": (f"two-quarter-ahead forecast issued {issue} from predictors through {L.qs(oper)} "
                                  f"(latest observed food-insecurity risk data: {horizon['latest_target_label_known_at_issue']})"),
                      "source": "SWS hunger (Balance Luzon); PSA provincial food and headline CPI and wholesale rice; "
                                "typhoon tracks and ENSO; PSA production; PSA LFS (national); BSP remittances and ECB "
                                "USD/PHP (national); news; official rice-policy orders; PSA 2021 SAE poverty (candidate input)",
                      "caveat": "Risk classification from regional hunger and provincial food prices, not a measured "
                                "provincial prevalence. Development evidence only (E56). Indicative decision support only. "
                                + freshness["note"]},
        "scoreTypes": {"food_insecurity_risk_probability": SCORE_DEF},
        "attributionMethod": ("Exact TreeSHAP (LightGBM pred_contrib) of the food-price part of the forecast, in "
                              "log-odds, grouped by trigger; Market / Prices also carries the projected food inflation "
                              "built from PSA CPI (the model's starting point) and the rice-policy orders; each group "
                              "includes its own news share; total news volume and poverty (when selected) are reported "
                              "outside the five bars. A group whose inputs were all missing at the issue date is shown as "
                              "insufficient data. The regional hunger part is shown separately. Model attributions, not causes."),
        "operationalRules": {"band": "Low if P < 0.33; Watch if 0.33 <= P < 0.67; High if P >= 0.67",
                             "decision": "HIGH if P >= 0.5 (fixed)", "alert": "Alert candidate when the band is High; "
                             "staged for administrator confirmation.", "municipal": "No municipal probability; LGU "
                             "rankings are relative prioritization weighted by PSA 2021 poverty and 2024 population density.",
                             "rollback": "unset AIPHEED_LEAD2_MODEL (or set e38) to return to the production default E38"},
        "provinces": provinces,
        "assessment": {"forecastingAcceptanceMet": bool(acc_ok), "arm": arm,
                       "E56": {"rows": res["rows"], "quarters": len(res["quarters"]), "HIGH": res["HIGH"],
                               "metrics": pick(m), "calibration_in_the_large": res["calibration"][arm]["citl"],
                               "calibration_slope": res["calibration"][arm]["slope"],
                               "within_quarter_auc": res["province_spread"][arm]["within_quarter_auc"],
                               "criteria": res["criteria"][arm]["criteria"], "selection_rule": res["selection_rule"]},
                       "evidenceStatus": res["evidence_status"]},
        "limitations": ["Development evidence only; independent test = 2027-Q1..Q4 (frozen).",
                        "Hunger is regional; on every evaluated quarter it was above 11.3%, so the evaluated skill is the "
                        "food-price part under elevated hunger.",
                        "Accuracy 95% CI 0.69-0.87 on 9 quarters; the configuration chosen by nested selection varies "
                        "between origins.",
                        "Employment, OFW, ENSO and policy inputs are national; 2026 BSP remittances are not in the dataset."],
        "sources": {"evaluation_run": run.name, "e56_protocol_sha256": proto,
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

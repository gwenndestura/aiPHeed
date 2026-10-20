"""Build the E64 record served when AIPHEED_LEAD2_MODEL=e64 (experiments/E64_Objectives_1_3_Completion/PROTOCOL.md):
the final E64 candidate (chosen on DEV by the frozen rule), two quarters ahead of the latest predictor quarter (Lead-2:
issued day 1 of quarter t+1, target t+2), target T43, with
  * the improved news pipeline (app/news/pipeline_v3.py: classifier v2, de-syndication, FSSI-v3, N3 features) built by
    the same backend functions at training and at inference;
  * exact TreeSHAP grouped by trigger (N3 trigger signals -> their group; national signals -> their group;
    coverage, outlets and FSSI -> other);
  * the news article IDs behind every forecast;
  * the E58 early-warning levels (same rule);
  * the saved 2027-Q1 model artifacts and a write-once prospective seal in the experiment folder.

    backend/venv/Scripts/python.exe -B scripts/build_record_e64.py   -> data/e64/e64_record.json, data/e64/model/*

Every refit must reproduce the sealed E64 probability (< 1e-9).
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
E64X = EXP / "E64_Objectives_1_3_Completion"
OUT = BACKEND / "data" / "e64" / "e64_record.json"
ART = BACKEND / "data" / "e64" / "model"
E43_REC = BACKEND / "data" / "e43" / "e43_record.json"
SEAL = E64X / "sealed" / "prospective_2027Q1.json"
sys.path.insert(0, str(E64X / "runner"))
sys.path.insert(0, str(BACKEND))
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
CONTRIBUTES = 0.05
N3_GROUP = {"n3_market_rw": "market", "n3_climate_rw": "climate", "n3_fish_kill_rw": "fish_kill",
            "n3_employment_rw": "employment", "n3_nat_market_rw": "market", "n3_nat_employment_rw": "employment",
            "n3_nat_ofw_remittance_rw": "ofw_remittance"}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def low_price_backtest(final: str, pd, np, cutoff: float = 0.2) -> dict:
    """How many of the final candidate's back-test price-part values below the cutoff were followed by HIGH (50 rows,
    from the E64 scored rows file), for the dashboard caveat."""
    R = pd.read_csv(E64X / "tables" / "c2_rows50.csv", dtype={"province_code": str})
    s = R[R[f"{final}_p_price"] < cutoff]
    return {"n": int(len(s)), "high": int(s["y"].sum()), "cutoff": cutoff, "source": "E64 tables/c2_rows50.csv"}


def band(p: float) -> str:
    return "High" if p >= 2 / 3 else ("Watch" if p >= 1 / 3 else "Low")


def main():
    import e64_lib as K
    import c1_candidates as C1
    from app.news import pipeline_v3 as P3

    K.verify_protocol()
    G, F, L, np, pd = K.G, K.F, K.L, K.np, K.pd
    F.E.NEWS_TO_GROUP.update(N3_GROUP)                       # trigger-group attribution of the N3 columns
    b46 = _load("b46", BACKEND / "scripts" / "build_record_e46.py")
    b58 = _load("b58", BACKEND / "scripts" / "build_record_e58.py")
    score = json.loads((E64X / "out" / "c2_score.json").read_text())
    final = score["selection"]["final"]
    sels = json.loads((E64X / "sealed" / "selections.json").read_text())
    sealed = pd.read_csv(E64X / "sealed" / "candidates.csv", dtype={"province_code": str}).set_index(["t", "province_code"])
    proto = (E64X / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    d, X0, B = F.E.load()
    n3 = K.n3_table()
    hist = pd.read_csv(K.E60_FEAT, dtype={"province_code": str})[["t", "province_code"] + K.HIST_COLS]
    X = X0.merge(n3.drop(columns=["fssi_status", "n_admitted"]), on=["t", "province_code"], how="left")
    X = X.merge(hist, on=["t", "province_code"], how="left")
    space = {c["id"]: c for c in G.search_space()}
    cols = C1.cols_for(final)
    Y = F.t43_labels(d)
    t43 = {(p, int(q)): int(v) for p, q, v in zip(Y["province_code"], Y["q"], Y["T43"]) if v == v}
    th = L.e40_spec()
    e43 = json.loads(E43_REC.read_text(encoding="utf-8"))
    origins = sorted(set(sealed.index.get_level_values("t")))
    oper = max(origins)
    enso_name = {1.0: "El Nino", 0.0: "neutral", -1.0: "La Nina"}

    def refit(tq):
        c = space[sels[L.qs(tq)][final]["cfg"]]
        tr, te = F.frame(d, X, B, tq, "AS")
        hc = F.hunger(d, X, tq)
        fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
        mdl = G.PriceLGB2(cols(c), c).fit(fit)
        pp = mdl.predict(te)
        return {"p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "H_hat": hc["H_hat"], "hc": hc, "cfg": c,
                "model": mdl, "te": te, "tr": fit}

    def num(v, fmt="{:.1f}", suf=""):
        return ("n/a (not in the dataset at the issue date)" if v is None or (isinstance(v, float) and not math.isfinite(v))
                else fmt.format(v) + suf)

    def news_note(news, g):
        arts = [a for a in news["articles"] if a["trigger"] == g]
        nat = [a for a in news["national"] if a["trigger"] == g]
        s = f" News (classifier v2, published before the issue date): {len(arts)} {LABELS[g]} article(s) for this province"
        if g in P3.NATIONAL_TRIGGERS:
            s += f" and {len(nat)} national"
        return s + "."

    def explain(fx, tq, i, p, news):
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
                      f"included. Source: PSA CPI, DA/BOC orders." + news_note(news, "market"),
            "climate": f"{num(row['tc_count'], '{:.0f}')} typhoon(s) within 300 km in {L.qs(tq)}; ENSO "
                       f"{enso_name.get(row['enso'], 'n/a')} in {L.qs(tq - 1)}; palay production {num(row['palay_yoy'], suf='%')} "
                       f"year on year ({L.qs(tq - 1)}). Sources: typhoon tracks, NOAA ONI, PSA." + news_note(news, "climate"),
            "fish_kill": f"Fisheries production {num(row['fish_yoy'], suf='%')} and aquaculture {num(row['aqua_yoy'], suf='%')} "
                         f"year on year ({L.qs(tq - 1)}); no official fish-kill event series exists. Source: PSA."
                         + news_note(news, "fish_kill"),
            "employment": f"National unemployment {num(row['ur_last'], '{:.2f}', '%')} ({L.qs(tq - 1)}), "
                          f"{num(row['ur_yoy'], '{:+.2f}')} points year on year; national figure. Source: PSA LFS."
                          + news_note(news, "employment"),
            "ofw_remittance": f"National cash remittances {num(row['remit_usd_yoy'], suf='%')} year on year ({L.qs(tq - 1)}); "
                              f"USD/PHP {num(row['fx_yoy'], suf='%')}; national figures. Sources: BSP, ECB."
                              + news_note(news, "ofw_remittance"),
        }
        status = {g: {"status": out[g]["status"], "evidenceNote": notes[g], "inputsPresent": out[g]["inputsPresent"]}
                  for g in LABELS}
        shown = [g for g in LABELS if out[g]["status"] == "contributes"]
        tot = sum(abs(out[g]["logOddsEffect"]) for g in shown) + abs(out["other"]["logOddsEffect"]) + abs(out["poverty"]["logOddsEffect"])
        other_pct = round(100 * (abs(out["other"]["logOddsEffect"]) + abs(out["poverty"]["logOddsEffect"])) / tot, 1) if tot > 0 else 0.0
        nprov = len(news["articles"])
        drivers = sorted(({"driver_group": g, "driver_label": LABELS[g],
                           "group_shap": out[g]["logOddsEffect"] if out[g]["status"] == "contributes" else 0.0,
                           "direction": "increases_risk" if out[g]["logOddsEffect"] >= 0 else "protective",
                           "trigger_proportion": (round(sum(1 for a in news["articles"] if a["trigger"] == g) / nprov, 4)
                                                  if nprov else None)}
                          for g in LABELS), key=lambda dd: abs(dd["group_shap"]), reverse=True)
        return a, out, status, drivers, other_pct

    def news_block(tq, p):
        feats = {r["province_code"]: r for r in P3.n3_features(tq)}[p]
        byk = {a["article_key"]: a for a in P3.admitted()}
        pick = lambda keys: [{"key": k, "title": byk[k]["title"], "outlet": byk[k]["outlet"],  # noqa: E731
                              "publishedPH": byk[k]["published_ph"], "trigger": byk[k]["trigger"],
                              "province": byk[k]["province_code"]} for k in keys]
        return {"articles": pick(feats["article_keys"]), "national": pick(feats["national_keys"]),
                "features": {k: (None if isinstance(v, float) and not math.isfinite(v) else v)
                             for k, v in feats.items() if k.startswith("n3_")},
                "fssiStatus": feats["fssi_status"], "issueCutoffPH": P3.origin(tq).isoformat()}

    manifest = {}

    def save_artifacts(fx, tq, rows):
        ART.mkdir(parents=True, exist_ok=True)
        mdl, te, c = fx["model"], fx["te"], fx["cfg"]
        (ART / "booster.txt").write_bytes(mdl.model.booster_.model_to_string().replace("\r\n", "\n").encode("utf-8")
                                          if mdl.const is None else b"constant model\n")
        (ART / "feature_schema.json").write_text(json.dumps({"features": [{"name": f, "group": F.group_of(f)} for f in mdl.feat],
                                                             "missing": "native LightGBM (NaN)"}, indent=1))
        (ART / "config.json").write_text(json.dumps({"candidate": final, "configuration": c, "origin": str(L.origin(tq).date()),
                                                    "target_quarter": L.qs(tq + 2), "decision_threshold": 0.5}, indent=1, default=str))
        te[["province_code"] + mdl.feat + [f"base_{mdl.m}", f"gbase_{mdl.m}"]].to_csv(
            ART / "features_2027Q1.csv", index=False, float_format="%.17g", lineterminator="\n")
        for f in sorted(ART.glob("*")):
            if f.name != "manifest.json":
                manifest[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        (ART / "manifest.json").write_text(json.dumps(manifest, indent=1))

    provinces = {p: {"provinceCode": p, "name": L.NAMES[p], "pastForecasts": [], "earlierForecasts": [], "pastDrivers": {}}
                 for p in L.PROVS}
    seal_rows = []
    for tq in origins:
        fx = refit(tq)
        if tq == oper:
            save_artifacts(fx, tq, None)
        q = L.qs(tq + 2)
        for i, p in enumerate(L.PROVS):
            served = float(fx["p"][i])
            ref = float(sealed.loc[(tq, p), f"{final}_p"])
            assert abs(served - ref) < 1e-9, (q, p, served, ref)
            news = news_block(tq, p)
            a, out, status, drivers, opct = explain(fx, tq, i, p, news)
            entry = {"origin": str(L.origin(tq).date()), "originQuarter": L.qs(tq), "probability": round(served, 4),
                     "probabilityPricePressure": round(float(fx["p_price"][i]), 4),
                     "probabilityHungerElevated": round(float(fx["p_hunger"]), 4),
                     "informationCutoff": {"cpiThrough": L.ym_s(L.m0_of(tq)), "typhoonsAndNewsThrough": L.qs(tq),
                                           "newsPublishedBefore": news["issueCutoffPH"],
                                           "productionLfsRemittancesThrough": L.qs(tq - 1),
                                           "swsHungerPostedBefore": str(L.origin(tq).date())},
                     "checks": {"probability_reproduction_error": abs(served - ref), "treeshap_reconstruction_error": a["error"]},
                     "modelConfig": fx["cfg"], "candidate": final,
                     "fiveTriggerContributions": {g: {k: v for k, v in c.items() if k not in ("status", "inputsPresent")}
                                                  for g, c in out.items() if g in LABELS},
                     "otherContribution": {**out["other"], "inputs": "news coverage, outlets, FSSI-v3 and total news volume where used"},
                     "povertyContribution": {**out["poverty"], "inputs": "PSA 2021 municipal SAE poverty, province mean (as-of)"
                                             if fx["cfg"]["pov"] else "not an input of the configuration selected at this origin"},
                     "baselineLogOdds": round(a["baseline"], 4),
                     "hungerGate": {"probabilityAbove11_3": round(float(fx["p_hunger"]), 4), "forecastH": round(float(fx["H_hat"]), 2),
                                    "note": "Regional SWS hunger (Balance Luzon), one value for all five provinces."},
                     "triggerStatus": status,
                     "drivers": {"drivers": drivers, "article_count": len(news["articles"]), "other_pct": opct,
                                 "evidence_quarter": L.qs(tq)},
                     "newsEvidence": news}
            v = provinces[p]
            if tq == oper:
                v.update({"forecast": {"targetQuarter": q, "lead": 2, "scoreType": "food_insecurity_risk_probability",
                                       "kind": "FORECAST (outcome not yet known)", "probability": served, "band": band(served),
                                       "decisionThreshold": 0.5, "decision": "HIGH" if served >= 0.5 else "LOW",
                                       "servedModel": f"E64 candidate {final} (configuration {fx['cfg']['id']})",
                                       "components": {"probabilityHungerElevated": round(float(fx["p_hunger"]), 4),
                                                     "probabilityPricePressure": round(float(fx["p_price"][i]), 4)},
                                       "explanation": (f"{L.NAMES[p]}, {q} (forecast issued {entry['origin']}): model score "
                                                       f"{served:.0%} = regional hunger part ({float(fx['p_hunger']):.0%}) x "
                                                       f"provincial food-price part ({float(fx['p_price'][i]):.0%}).")},
                          **{k: entry[k] for k in ("fiveTriggerContributions", "otherContribution", "povertyContribution",
                                                   "hungerGate", "baselineLogOdds", "triggerStatus", "drivers", "checks",
                                                   "modelConfig", "newsEvidence", "informationCutoff")},
                          "observed": e43["provinces"][p]["observed"],
                          "operational": {"category": band(served), "alertCandidate": band(served) == "High"}})
                seal_rows.append({"province": L.NAMES[p], "province_code": p, "target": q, "issued": entry["origin"],
                                  "probability": served, "components": v["forecast"]["components"],
                                  "configuration": fx["cfg"]["id"], "features": {c: (None if pd.isna(fx["te"].iloc[i][c])
                                                                                      else float(fx["te"].iloc[i][c]))
                                                                                  for c in fx["model"].feat},
                                  "fiveTriggerContributions": entry["fiveTriggerContributions"],
                                  "newsArticleKeys": [x["key"] for x in news["articles"]],
                                  "newsNationalKeys": [x["key"] for x in news["national"]],
                                  "newsPublishedBefore": news["issueCutoffPH"]})
            else:
                rec_ = {"targetQuarter": q, "probability": round(served, 3), "origin": entry["origin"],
                        "decision": "HIGH" if served >= 0.5 else "LOW"}
                if (p, tq + 2) in t43 and tq + 2 <= oper:
                    v["pastForecasts"].append(rec_ | {"observedHigh": bool(t43[(p, tq + 2)])})
                else:
                    v["earlierForecasts"].append(rec_)
                v["pastDrivers"][q] = entry
    # E58 early warning (same rule), as of each origin
    d0 = L.load()
    memo = {}

    def asof(origin_q):
        if origin_q not in memo:
            t = L.qi(origin_q)
            hs = d0.cut(t).sws.groupby("q")["H"].mean().sort_index()
            memo[origin_q] = (F.t43_last(d0, t), float(hs.iloc[-1]), L.qs(int(hs.index[-1])))
        return memo[origin_q]
    for code, v in provinces.items():
        last, h, hq = asof(L.qs(oper))
        lab, lq = last[code]
        f = v["forecast"]
        v["earlyWarning"] = b58.warning(f["probability"], f["components"]["probabilityPricePressure"],
                                        None if lab != lab else int(lab), None if lq is None else L.qs(lq), h, hq)
        for q, e in v["pastDrivers"].items():
            last, h, hq = asof(e["originQuarter"])
            lab, lq = last[code]
            e["earlyWarning"] = b58.warning(e["probability"], e["probabilityPricePressure"],
                                            None if lab != lab else int(lab), None if lq is None else L.qs(lq), h, hq)
        v["pastForecastsNote"] = ("Development backtest of the E64 candidate procedure at each past origin (only "
                                  "information published before that origin); not forecasts issued live; these quarters "
                                  "were examined in earlier experiments.")
        v["warnings"] = ["EXPERIMENTAL: development evidence only (E64); independent test = the sealed 2027-Q1 forecast.",
                         "Hunger is measured only for the whole region (SWS Balance Luzon); provincial differences come "
                         "from food prices.", "Employment, OFW and ENSO evidence are national.",
                         "Early-warning levels are model warnings for DA review, not official classifications."]
    m = score["metrics_50"][f"E64-{final}"]
    issue = str(L.origin(oper).date())
    sdef = ("Model score for HIGH food-insecurity risk in the target quarter (target T43, Chapter I section 1.7): regional "
            "SWS hunger (Balance Luzon) above 11.3% AND provincial food-price pressure (PSA food inflation, or food minus "
            "headline inflation, above the province's 2021-2022 60th percentile). The regional hunger part and the "
            "provincial price part are estimated separately and multiplied; the two conditions are not independent, so the "
            "product is a model score, not a tested joint probability. A food-stress risk indicator, not a measured "
            "prevalence of household food insecurity.")
    body = {
        "schema": "e64/1", "name": "aiPHeed provincial food-stress risk forecast (E64 candidate, experimental)",
        "status": "EXPERIMENTAL - development evidence, not independently validated; enabled only with AIPHEED_LEAD2_MODEL=e64",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modelVersion": f"E64-{final}: E56 LightGBM procedure family (structural CPI offset, intercept-free boosting, nested "
                        f"chronological selection) x I7 regional hunger component; news = pipeline v3 (protocol sha {proto[:16]})",
        "modelFamily": "LightGBM", "candidate": final, "finalModelArtifacts": manifest,
        "origin": issue, "originQuarter": L.qs(oper), "targetQuarter": L.qs(oper + 2), "lead": 2, "leadFromOrigin": 2,
        "quarterConvention": ("Lead-2: predictor quarter t = latest quarter with complete news; issue date = day 1 of "
                              "quarter t+1; target = quarter t+2 (the quarter after the issue quarter)."),
        "dataFreshness": json.loads((BACKEND / "data" / "e58" / "e58_record.json").read_text(encoding="utf-8"))["dataFreshness"],
        "information": {"cpiMonthsThrough": L.ym_s(L.m0_of(oper)), "rule": "only data published before the origin"},
        "indicator": {"id": "food_insecurity_risk_probability", "name": "Food-Stress Risk Score (experimental)",
                      "definition": sdef, "unit": "model score (0-1)",
                      "horizon": f"two-quarter-ahead forecast issued {issue} from predictors through {L.qs(oper)}",
                      "source": "SWS hunger (Balance Luzon); PSA provincial food and headline CPI and wholesale rice; "
                                "typhoon tracks and ENSO; PSA production; PSA LFS (national); BSP remittances and ECB "
                                "USD/PHP (national); news pipeline v3 (classifier v2, FSSI-v3); official rice-policy orders",
                      "caveat": "Food-stress risk indicator from regional hunger and provincial food prices, not a measured "
                                "provincial prevalence. Development evidence only (E64). Indicative decision support only."},
        "scoreTypes": {"food_insecurity_risk_probability": sdef},
        "attributionMethod": ("Exact TreeSHAP (LightGBM pred_contrib) of the food-price part, in log-odds, grouped by "
                              "trigger; Market / Prices carries the projected food inflation built from PSA CPI; each "
                              "group includes its own news signals (classifier v2); news coverage, outlets and FSSI-v3 "
                              "are reported outside the five bars. Model attributions, not causes."),
        "operationalRules": {"band": "Low if P < 0.33; Watch if 0.33 <= P < 0.67; High if P >= 0.67",
                             "decision": "HIGH if P >= 0.5 (fixed)", "alert": "Alert candidate when the band is High; "
                             "staged for administrator confirmation.", "municipal": "No municipal probability; LGU "
                             "rankings are relative prioritization weighted by PSA 2021 poverty and 2024 population density.",
                             "rollback": "unset AIPHEED_LEAD2_MODEL (or set e38) to return to the production default E38"},
        "earlyWarningRule": json.loads((BACKEND / "data" / "e58" / "e58_record.json").read_text(encoding="utf-8"))["earlyWarningRule"],
        "provinces": provinces,
        "assessment": {"candidate": final, "selection": score["selection"], "metrics50": m,
                       "claims": {k: v for k, v in score["claims"].items()},
                       "lowPriceBacktest": low_price_backtest(final, pd, np)},
        "limitations": ["Development evidence only; every evaluation quarter was examined before E64.",
                        "Hunger is regional; on every evaluated quarter it was above 11.3%, so the evaluated skill is the "
                        "food-price part under elevated hunger.",
                        "The target's gap condition counts a faster rise of non-food prices as less food-price pressure.",
                        "News titles were collected retrospectively in October 2026; headlines only."],
        "sources": {"e64_protocol_sha256": proto, "origins": [L.qs(t) for t in origins],
                    "news_pipeline": {"classifier_v2_sha256": P3.classifier_sha(), "corpus_articles": len(P3.corpus()),
                                      "admitted": len(P3.admitted())}},
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, indent=1, default=str), encoding="utf-8")
    if not SEAL.exists():                                     # write-once prospective record of the Lead-2 forecast
        seal = {"sealed_at": body["generated_at"], "candidate": final, "target": L.qs(oper + 2), "issued": issue,
                "model": body["modelVersion"], "protocol_sha256": proto, "artifacts": manifest, "forecasts": seal_rows,
                "rule": "score against T43 when the 2027-Q1 SWS round and March 2027 CPI are published; never edit"}
        SEAL.write_text(json.dumps(seal, indent=1, default=str), encoding="utf-8")
        (SEAL.parent / (SEAL.name + ".sha256")).write_text(hashlib.sha256(SEAL.read_bytes()).hexdigest() + f"  {SEAL.name}\n")
    print(OUT, final, body["content_sha256"][:16],
          {v["name"]: (round(v["forecast"]["probability"], 3), v["earlyWarning"]["level"],
                       [dd["driver_group"] for dd in v["drivers"]["drivers"][:3]]) for v in provinces.values()})


if __name__ == "__main__":
    main()

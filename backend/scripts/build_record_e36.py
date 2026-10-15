"""
scripts/build_record_e36.py
---------------------------
The served record of the E36 LightGBM (aiPHeed-E36-LGBM, version E36.1): ONE JSON read by the API
(/api/v1/quarterly/e31/* keeps its paths), the dashboard engine (app/ml/inference/e31_engine.py), /da-brief and the PDF.

    python -B scripts/build_record_e36.py            (run from backend/)

Inputs (read-only, hash-checked):
  * E36 frozen serving bundle and model artifact (aipheed-backend-aligned/experiments/E36_LightGBM_One_Quarter_Ahead):
    backtests 2023-Q1..2026-Q3 under the nested rule, the frozen 2026-Q4 one-quarter-ahead forecast (origin
    2026-10-01), exact TreeSHAP drivers, the evaluation against the six Chapter I baselines;
  * data/e31/e31_record.json: the measured regional hunger rounds, the label definition, the news funnel and the
    validated articles, the news-relevance validation (unchanged sources; E36 adds no news collection);
  * data/inputs/lgu_vulnerability.csv + data/reference/calabarzon_lgus.csv: PSA 2021 municipal SAE (141 LGUs) and
    2024 POPCEN (142 LGUs), vintage 2;
  * data/inputs/d_quarterly_panel.csv: measured relative food inflation.

Writes data/e36/e36_record.json, data/e36/aiPHeed_E36_assessment_report.pdf (Subject = record hash) and copies of the
frozen artifacts under data/e36/model/. Nothing here fits a model.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.news.alignment import evidence_window  # noqa: E402
from app.quarterly.lgu_audit import build_ranking  # noqa: E402

E36 = ROOT.parent / "aipheed-backend-aligned" / "experiments" / "E36_LightGBM_One_Quarter_Ahead"
BUNDLE = E36 / "frozen" / "E36_SERVING_BUNDLE.json"
PROSPECTIVE = E36 / "frozen" / "E36_PROSPECTIVE_2026Q4.json"
MODEL_TXT = E36 / "models" / "E36-LGBM_O2026-10-01.txt"
MODEL_CFG = E36 / "models" / "E36-LGBM_O2026-10-01.json"
OUT = ROOT / "data" / "e36"
BASE = ROOT / "data" / "e31" / "e31_record.json"
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
ORDER = ["PH040100000", "PH040200000", "PH040500000", "PH040400000", "PH040300000"]
BASELINE_LABEL = {
    "E36-LGBM": "Proposed: combined LightGBM (government + news), nested selection",
    "B1_PERSISTENCE": "B1 Naive persistence",
    "B2_LR_COMB": "B2 Logistic regression, combined features",
    "B3_LR_GOV": "B3 Logistic regression, government indicators only",
    "B4_LR_NLP": "B4 Logistic regression, NLP features only",
    "B5_LGBM_GOV": "B5 LightGBM, government indicators only",
    "B6_LGBM_NLP": "B6 LightGBM, NLP features only",
    "ALWAYS_HIGH": "Diagnostic: always HIGH (majority class)",
}
DISCLAIMER = ("aiPHeed produces potential food-insecurity risk indicators for review. They are not official "
              "food-insecurity classifications and do not replace assessments by authorized government agencies.")
DRIVER_METHOD = ("exact TreeSHAP contribution of each input to this estimate, in log-odds (positive raises the "
                 "probability of HIGH); associations the model learned from 2021-2026 data, not causes")


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen_ok(p: Path) -> dict:
    want = p.with_suffix(".sha256").read_text().split()[0]
    b = p.read_bytes()
    if hashlib.sha256(b).hexdigest() != want and hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest() != want:
        raise SystemExit(f"frozen file changed: {p}")
    return json.loads(b.decode("utf-8"))


def r4(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 4)


def signal(p: float) -> str:
    return "STRONG" if p >= .8 or p <= .2 else "MODERATE" if p >= .65 or p <= .35 else "UNCERTAIN"


# Plain-language factor names for DA readers (the frozen bundle keeps the technical ones; keys are unchanged).
PLAIN = {"fssi_v2": "Food-stress tone of the province's validated news",
         "fssi_missing": "No usable food-stress news reading for the province this quarter"}


def estimate(v: dict) -> dict:
    out = {"province": v["province"], "p_high": r4(v["p_high"]), "signal": signal(v["p_high"]),
           "drivers": [{"key": d["key"], "factor": PLAIN.get(d["key"], d["factor"]), "value": r4(d["value"]),
                        "contribution": r4(d["contribution"]),
                        "kind": "government indicator" if d["source"] == "government" else "news signal"}
                       for d in v["drivers"]],
           "driver_method": DRIVER_METHOD, "shap_expected_value_logodds": r4(v["expected_value_logodds"]),
           "persistence_p": v.get("persistence_p")}
    if "observed_label" in v:
        out.update(observed_label=v["observed_label"], observed_S1=r4(v["observed_S1"]))
    return out


def news_window(target: str, origin: str) -> dict:
    return evidence_window(target, "forecast", f"{origin}T00:00:00+08:00").to_dict()


def quarters(b: dict, base: dict) -> list[dict]:
    funnel = {(r["province_code"], r["quarter"]): r for r in base["news"]["by_province_quarter"]}
    out = []
    for q in b["backtests"] + [b["forecast"]]:
        mode = q["mode"]
        ev = news_window(q["quarter"], q["origin"])
        used = sum((funnel.get((c, ev["evidence_quarter"])) or {}).get("admitted_after_dedup", 0) for c in ORDER)
        out.append({
            "quarter": q["quarter"], "mode": mode, "lead": 1, "origin": q["origin"],
            "information_cutoff": q["information_cutoff"],
            "status": ("development backtest: nested walk-forward, refitted at this origin with only information "
                       "published before it; the outcome had been examined in earlier experiments" if mode == "BACKTEST"
                       else "one-quarter-ahead forecast frozen before the outcome exists; reliability not established"),
            "threshold": r4(q["tau"]), "model_config": q["config"],
            "feature_availability": q["feature_availability"],
            "provenance": {"mode": "forecast", "generated_at": b["forecast"]["frozen_at_utc"] if mode == "FORECAST"
                           else b["evaluation"]["run"], "information_cutoff": q["information_cutoff"],
                           "news_evidence_window": ev, "n_articles_used_by_model": used,
                           "news_version": {"store": base["news"]["source"],
                                            "articles_jsonl_sha256": base["news"]["articles_jsonl_sha256"]}},
            "provinces": {c: estimate(q["provinces"][c]) for c in ORDER},
        })
    return out


def provinces_now(fc: dict, last: dict, base: dict) -> dict:
    D = pd.read_csv(ROOT / "data" / "inputs" / "d_quarterly_panel.csv", dtype={"province_code": str})
    funnel = {(r["province_code"], r["quarter"]): r for r in base["news"]["by_province_quarter"]}
    ev_q = fc["provenance"]["news_evidence_window"]["evidence_quarter"]
    out = {}
    for c in ORDER:
        dd = D[D.province_code == c].sort_values("quarter").tail(3)
        d_last = float(dd.D.iloc[-1])
        ppress = "above" if d_last > 0.25 else "below" if d_last < -0.25 else "close to"
        e = fc["provinces"][c]
        top = [d for d in e["drivers"] if d["contribution"] is not None][:3]
        raised = [d["factor"] for d in top if d["contribution"] > 0]
        lowered = [d["factor"] for d in top if d["contribution"] < 0]
        p = e["p_high"]
        out[c] = {
            "province": NAMES[c], "forecast_quarter": fc["quarter"], "forecast": e,
            "latest_backtest": {"quarter": last["quarter"], **last["provinces"][c]},
            "measured_relative_food_inflation_pp": {r.quarter: r4(r.D) for r in dd.itertuples()},
            "price_pressure_text": f"Food inflation in {NAMES[c]} was {abs(d_last):.2f} pp {ppress} the five-province "
                                   f"average in {dd.quarter.iloc[-1]} (PSA, measured).",
            "news_evidence": funnel.get((c, ev_q)), "news_evidence_quarter": ev_q,
            "explanation_text": (f"The model puts {NAMES[c]} at {round(100 * p)}% for {fc['quarter']}. "
                                 + (f"Raised mainly by: {'; '.join(raised)}. " if raised else "")
                                 + (f"Lowered mainly by: {'; '.join(lowered)}." if lowered else "")).strip(),
            "attention": ("Review: the model estimate is high; check provincial market prices and field reports"
                          if p >= .8 else "Monitor: the estimate is above one half with less certainty" if p >= .5
                          else "Lower estimate: the model expects this province below the threshold; it can still "
                               "be wrong (12 of 65 development estimates were wrong)"),
            "suggested_use": "Prioritise for review by DA Region IV-A; do not allocate resources on this estimate alone.",
            "evidence_status": "EXPERIMENTAL", "disclaimer": DISCLAIMER}
    return out


def validation(b: dict, base: dict) -> dict:
    ev = b["evaluation"]
    m = ev["metrics_all"]
    t = ev["target_75"]
    rows = [{"arm": BASELINE_LABEL[a], "key": a, "correct": m[a]["correct"], "n": m[a]["n"],
             "accuracy_lead1": r4(m[a]["accuracy"]), "accuracy_ci95": [round(x, 6) for x in m[a]["accuracy_ci95"]],
             "balanced_accuracy": r4(m[a]["balanced_accuracy"]), "precision": r4(m[a]["precision"]),
             "recall": r4(m[a]["recall"]), "specificity": r4(m[a]["specificity"]), "f1": r4(m[a]["f1"]),
             "roc_auc": r4(m[a]["roc_auc"]), "brier": r4(m[a]["brier"]), "above_75pct": bool(m[a]["accuracy"] >= .75)}
            for a in BASELINE_LABEL]
    pv = {k: {"mean_brier_gain_vs_ref": r4(v["mean_brier_gain_vs_ref"]), "p_two_sided": r4(v["p_two_sided"]),
              "holm": r4(v.get("holm_two_sided_over_six_baselines")), "accuracy_diff": r4(v["accuracy_diff"])}
          for k, v in ev["paired_vs_baselines"].items()}
    verdict = (f"One-quarter-ahead accuracy of the proposed LightGBM on {t['n']} development estimates "
               f"({len(ev['dates'])} quarters, 2023-Q1 to 2026-Q3): {t['correct']}/{t['n']} = {t['accuracy']:.3f}. "
               f"The point estimate is above 75%, but the 95% date-bootstrap interval "
               f"({t['date_bootstrap_ci95'][0]:.3f} to {t['date_bootstrap_ci95'][1]:.3f}) reaches below 75%, so the "
               f"target is not demonstrated. Always-HIGH reaches the same accuracy ({t['always_high_accuracy']:.3f}) "
               f"and persistence a higher one ({t['persistence_accuracy']:.3f}). Unlike always-HIGH, the model does "
               f"identify LOW quarters (balanced accuracy {t['balanced_accuracy']:.3f}). No paired difference with any "
               f"of the six baselines is significant. These are development dates; the 2026-Q4 forecast is the first "
               f"untouched test.")
    return {
        "news_relevance": base["validation"]["news_relevance"],
        "model_evaluation": {"basis": f"E36 frozen protocol {b['model']['protocol_sha256'][:12]}; lead 1; nested "
                                      f"rolling-origin; run {ev['run']}", "dates": ev["dates"], "rows": rows,
                             "paired_vs_baselines": pv},
        "threshold_75pct": {"source": "the researcher's brief; Chapter I states no numeric threshold",
                            "rows": [{"arm": r["arm"], "accuracy_lead1": r["accuracy_lead1"],
                                      "above_75pct": r["above_75pct"]} for r in rows],
                            "point_met": t["statement1_point_ge_0.75"],
                            "demonstrated": t["statement2_demonstrated_lower_bound_ge_0.75"], "verdict": verdict},
        "prospective_2026Q4": {"frozen_sha256": b["prospective_sha256"], "origin": b["forecast"]["origin"],
                               "status": "awaiting the SWS December 2026 round; scored once, never re-fitted before"},
    }


def _clean(o):
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return o


def build() -> dict:
    b = frozen_ok(BUNDLE)
    frozen_ok(PROSPECTIVE)
    if sha_file(MODEL_TXT) != b["model"]["artifact_sha256"] and hashlib.sha256(
            MODEL_TXT.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != b["model"]["artifact_sha256"]:
        raise SystemExit("model artifact does not match the bundle")
    base = json.loads(BASE.read_text(encoding="utf-8"))
    qs = quarters(b, base)
    fc = qs[-1]
    vul = pd.read_csv(ROOT / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    ros = pd.read_csv(ROOT / "data" / "reference" / "calabarzon_lgus.csv", dtype={"lgu_psgc": str})
    rk = build_ranking(vul, ros, {c: fc["provinces"][c]["p_high"] for c in ORDER},
                       {"source": f"E36 FORECAST {fc['quarter']} (aiPHeed-E36-LGBM, origin {fc['origin']})",
                        "evidence_status": "EXPERIMENTAL"})
    n_sae = int(vul["poverty_lgu_estimate"].notna().sum())
    mc = b["model"]
    rec = {
        "schema": "e36/1",
        "title": "aiPHeed: food-insecurity risk indicators for CALABARZON (DA Region IV-A)",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "information_cutoff": fc["information_cutoff"],
        "data_authorization": base["data_authorization"],
        "served_engine": {
            "name": "aiPHeed-E36-LGBM (LightGBM, government indicators + news signals)", "version": mc["version"],
            "file": "data/e36/model/" + MODEL_TXT.name, "sha256": mc["artifact_sha256"],
            "config": {"feature_set": mc["feature_set"], "features": mc["features"], "grid_id": mc["grid_id"],
                       "params": mc["params"], "training_rows": mc["training_rows"],
                       "training_target_quarters": mc["training_target_quarters"]},
            "why_served": ("Chapter I's proposed model is a LightGBM combining news and government data. This is the "
                           "configuration chosen by the frozen E36 nested rule at the operational origin "
                           "2026-10-01; it was evaluated against all six Chapter I baselines on identical rows."),
            "evidence_status": "EXPERIMENTAL / NOT VALIDATED (no baseline is beaten significantly; development "
                               "dates only)"},
        "target_definition": base["target_definition"],
        "regional_hunger": base["regional_hunger"],
        "quarters": qs,
        "provinces_now": provinces_now(fc, qs[-2], base),
        "lgu_ranking": rk,
        "news": base["news"],
        "validation": validation(b, base),
        "limitations": [
            "The label is dominated by one regional SWS hunger value, so in most quarters all five provinces share a "
            "label; 53 of 65 development labels are HIGH. Provincial differences come mainly from relative food "
            "prices.",
            "One-quarter-ahead accuracy is 0.815 on 65 development estimates, the same as always-HIGH and below "
            "persistence (0.877). The 75% target is met as a point estimate but not demonstrated (95% interval "
            "reaches 0.738). No baseline is beaten significantly.",
            "News signals added no measurable skill: the government-only LightGBM (B5) scores as well or better than "
            "the combined model on the same rows.",
            "News evidence is title-only (Google News RSS), thin in older quarters, and its relevance labels were made "
            "by the AI assistant; a researcher re-review is pending.",
            f"LGU rankings re-weight the province forecast by PSA 2021 municipal poverty ({n_sae} of 142 LGUs; Lucena "
            "City, a highly urbanized city absent from the PSA no-HUC table, uses a province substitute of "
            "unverified source) and 2024 POPCEN density. They are relative positions, not municipal forecasts.",
            "The 2026-Q4 forecast is the first untouched test; it can be scored only after the SWS December 2026 "
            "round is released.",
        ],
        "disclaimer": DISCLAIMER,
    }
    rec = _clean(rec)
    rec["content_sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return rec


def write_pdf(rec: dict, path: Path):
    """Chapter I 1.7: forecast scores, SHAP driver breakdowns, performance metrics and data-sufficiency disclosures.
    The record hash is the PDF Subject; the API refuses a PDF that does not match."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table

    st = getSampleStyleSheet()
    P = lambda t, s="Normal": Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;"), st[s])  # noqa: E731
    pct = lambda x: "-" if x is None else f"{100 * x:.0f}%"  # noqa: E731
    f3 = lambda x: "-" if x is None else f"{x:.3f}"  # noqa: E731
    se = rec["served_engine"]
    fcq = next(q for q in rec["quarters"] if q["mode"] == "FORECAST")
    els = [P(rec["title"], "Title"),
           P(f"Model {se['name']} {se['version']}. Forecast quarter {fcq['quarter']}, issued at origin {fcq['origin']} "
             f"with information published before it. Record SHA-256 {rec['content_sha256']}."),
           P(rec["disclaimer"]), P("What is estimated", "Heading2")]
    td = rec["target_definition"]
    els += [P(td["label"]), P("H: " + td["H"]), P("D: " + td["D"]), P("Not: " + td["is_not"]),
            P("Evidence status: " + se["evidence_status"])]
    rh = rec["regional_hunger"]
    els += [P("CALABARZON: official regional hunger (measured)", "Heading2"),
            Table([["Quarter", "Round", "Hunger %", "Posted"]] + [[o["quarter"], o["round"][:45], o["hunger_pct"],
                                                                 o["published"]] for o in rh["rounds"]]),
            P(rh["geographic_level"]), PageBreak()]
    for c, b in rec["provinces_now"].items():
        e, lb = b["forecast"], b["latest_backtest"]
        ne = b["news_evidence"] or {}
        els += [P(f"{b['province']}: {b['forecast_quarter']} forecast (lead 1)", "Heading2"),
                Table([["", f"{b['forecast_quarter']} FORECAST", f"{lb['quarter']} backtest (observed {lb.get('observed_label')})"],
                       ["P(HIGH)", pct(e["p_high"]), pct(lb["p_high"])], ["Signal", e["signal"], lb["signal"]]]),
                P("Main drivers (TreeSHAP, log-odds):"),
                Table([["Factor", "Value", "Contribution"]] +
                      [[d["factor"][:70], "-" if d["value"] is None else f"{d['value']:.2f}", f"{d['contribution']:+.2f}"]
                       for d in e["drivers"][:6]]),
                P(e["driver_method"]), P(b["explanation_text"]), P(b["price_pressure_text"]),
                P(f"News evidence ({b['news_evidence_quarter']}): {ne.get('admitted_after_dedup', 0)} validated "
                  f"article(s) of {ne.get('province_attributed', 0)} province-attributed; status "
                  f"{ne.get('evidence_status_v2', 'NO_USABLE_EVIDENCE')}."),
                P(b["attention"] + ". " + b["suggested_use"]), Spacer(1, 4)]
        top = sorted([r for r in rec["lgu_ranking"]["rows"] if r["province_code"] == c and r["rank_in_province"]],
                     key=lambda r: r["rank_in_province"])[:5]
        els.append(Table([["Top LGUs (relative position)", "Risk index", "Poverty used", "Kind"]] +
                         [[r["lgu_name"], r["risk_index"], r["poverty_value_used"], r["poverty_value_kind"][:34]]
                          for r in top]))
    v = rec["validation"]
    els += [PageBreak(), P("Model evaluation: one quarter ahead, development quarters", "Heading2"), P(v["model_evaluation"]["basis"])]
    rows = [["Approach", "Correct/n", "Acc", "Acc 95% CI", "Bal.acc", "Prec", "Recall", "F1", "ROC-AUC", "Brier"]]
    for r in v["model_evaluation"]["rows"]:
        rows.append([r["arm"][:52], f"{r['correct']}/{r['n']}", f3(r["accuracy_lead1"]),
                     f"{f3(r['accuracy_ci95'][0])}-{f3(r['accuracy_ci95'][1])}", f3(r["balanced_accuracy"]),
                     f3(r["precision"]), f3(r["recall"]), f3(r["f1"]), f3(r["roc_auc"]), f3(r["brier"])])
    els += [Table(rows), P(v["threshold_75pct"]["verdict"])]
    ho = v["news_relevance"]["holdout"]["gates"]["R1"]
    els += [P("News relevance validation (blind holdout)", "Heading2"),
            P(f"Rule R1: precision {ho['precision']}, recall {ho['recall']}, F1 {ho['f1']}."),
            P("Data sufficiency (news, FSSI-v2): " + json.dumps(rec["news"]["totals"])),
            P("City and municipal ranking", "Heading2"), P(rec["lgu_ranking"]["meaning"])]
    els += [P("- " + t) for t in rec["lgu_ranking"]["does_not_mean"]]
    els += [P("Limitations", "Heading2")] + [P("- " + t) for t in rec["limitations"]] + [P(rec["disclaimer"])]
    SimpleDocTemplate(str(path), pagesize=landscape(A4), title=rec["title"], subject=rec["content_sha256"],
                      invariant=1, pageCompression=0).build(els)


def main():
    rec = build()
    (OUT / "model").mkdir(parents=True, exist_ok=True)
    for src in (MODEL_TXT, MODEL_CFG, BUNDLE, PROSPECTIVE, BUNDLE.with_suffix(".sha256"), PROSPECTIVE.with_suffix(".sha256")):
        shutil.copyfile(src, OUT / "model" / src.name)
    blob = json.dumps(rec, indent=1, ensure_ascii=False, default=str, allow_nan=False).encode("utf-8")
    (OUT / "e36_record.json").write_bytes(blob)
    write_pdf(rec, OUT / "aiPHeed_E36_assessment_report.pdf")
    front = ROOT.parent / "frontend" / "public"
    if front.exists():
        (front / "e36_record.json").write_bytes(blob)
    print(rec["content_sha256"], len(blob), "bytes;", len(rec["quarters"]), "quarters;",
          len(rec["lgu_ranking"]["rows"]), "LGUs;", sum(r["poverty_value_kind"].startswith("PSA municipal")
                                                       for r in rec["lgu_ranking"]["rows"]), "with municipal SAE")


if __name__ == "__main__":
    main()

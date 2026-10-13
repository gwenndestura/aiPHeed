"""Build the dashboard JSON and the PDF report from ONE source each (no typed numbers):
  * forecast period/status   <- aipheed-backend-aligned/data/quarterly_runs/latest forecast record (also served by
                                 GET /api/v1/quarterly/forecast-period)
  * evaluation / hypotheses   <- E23 results.json and E23-B results_e23b.json (sealed runs)
  * rankings                  <- rankings/lgu_rankings_backtest_2026Q1.csv + ranking_verification.json
Usage: python -B runner/build_outputs.py <E23 run> <E23B run>"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
AL = EXP.parents[1]
sys.path.insert(0, str(AL))
from app.quarterly.update import load_latest  # noqa: E402

MODELS = {"PROPOSED_lgbm_combined": "Proposed LightGBM (news + government)",
          "B1_naive_persistence": "B1 Naive persistence (Obj. 4-I)",
          "B2_lr_combined": "B2 Logistic regression, combined (Obj. 4-IV)",
          "B3_lr_gov_only": "B3 Logistic regression, government only (Obj. 4-II)",
          "B4_lr_nlp_only": "B4 Logistic regression, news only (Obj. 4-III)",
          "B5_lgbm_gov_only": "B5 LightGBM, government only (SOP Q3)",
          "B6_lgbm_nlp_only": "B6 LightGBM, news only (SOP Q3)",
          "S_lr_psa_only": "Supplementary: LR on the 20 PSA series (Obj. 4-II literal)"}
NNS = {"source": "DOST-FNRI 2023 National Nutrition Survey, 'Household & Food Security' (enutrition.fnri.dost.gov.ph/"
                 "images/nns-2023/2. Household & Food Security .pdf), retrieved 2026-10-13",
       "calabarzon_2023_moderate_severe_pct": 19.1, "calabarzon_2023_ci95": [17.0, 21.1],
       "national_2023_moderate_severe_pct": 31.4, "calabarzon_rank": "lowest of 17 regions",
       "nns_2019_calabarzon": "not verified: the 2018-2019 ENNS used the HFIAS scale (not FIES) and its regional "
                              "figure was not located in an FNRI primary source; not comparable with the 2023 FIES value",
       "use": "Descriptive regional anchor only; one regional value cannot validate provincial forecasts."}


def main():
    r23, r23b = sys.argv[1], sys.argv[2]
    rec = load_latest(AL / "data" / "quarterly_runs")
    R = json.loads((EXP / "runs" / r23 / "results.json").read_text(encoding="utf-8"))
    B = json.loads((EXP / "runs" / r23b / "results_e23b.json").read_text(encoding="utf-8"))
    ver = json.loads((EXP / "rankings" / "ranking_verification.json").read_text(encoding="utf-8"))
    with open(EXP / "rankings" / "lgu_rankings_backtest_2026Q1.csv", encoding="utf-8") as f:
        ranks = list(csv.DictReader(f))
    evals = {}
    for mode in ("origin", "fixed"):
        rows = []
        for k, v in R[mode]["by_lead"].items():
            if not v.get("n_origins"):
                rows.append({"lead": int(k), "n_origins": 0, "evaluable": False}); continue
            row = {"lead": int(k), "n_origins": v["n_origins"], "HIGH": v["test_HIGH"], "LOW": v["test_LOW"],
                   "evaluable": v["evaluable"], "target_quarters": v["target_quarters"],
                   "reliable": R[mode]["reliability"][k]["reliable"], "models": {}}
            for m, name in MODELS.items():
                x = v["metrics"][m]
                row["models"][m] = {"name": name, **{q: x[q] for q in ("accuracy", "precision", "recall", "F1",
                                                                     "ROC_AUC", "Brier", "TP", "FP", "FN", "TN")}}
            b = B[mode].get(k)
            if b:
                row["improved"] = {"accuracy": b["accuracy"]["IMP_lgbm_selected"],
                                   "always_HIGH_accuracy": b["accuracy"]["REF_always_HIGH"],
                                   "strongest_baseline": b["strongest_baseline"],
                                   "strongest_baseline_accuracy": b["accuracy"][b["strongest_baseline"]],
                                   "beats_strongest": b["beats_strongest"], "exceeds_75": b["exceeds_75"],
                                   "ROC_AUC": b["imp_metrics"]["ROC_AUC"], "Brier": b["imp_metrics"]["Brier"]}
            rows.append(row)
        evals[mode] = rows
    H = R["origin"]["hypotheses"]
    data = {
        "generated_from": {"e23_run": r23, "e23b_run": r23b, "forecast_record_sha256": rec["content_sha256"]},
        "period": rec["period"], "status": rec["status"], "missing": rec["missing"], "labels": rec["labels"],
        "cutoff_reached": rec["cutoff_reached"], "requirements": rec["requirements"],
        "supporting_news": {k: v for k, v in rec["supporting_news"].items() if k != "articles"},
        "supporting_articles": rec["supporting_news"]["articles"], "forecast": rec["forecast"],
        "evaluation": evals, "max_reliable_lead": R["origin"]["max_reliable_lead"],
        "hypotheses": {h: {"decision": H[h]["decision"], "why": H[h].get("why")} for h in ("H1", "H2", "H3", "H4", "H5")},
        "sensitivity_fixed_threshold_hypotheses": {h: R["fixed"]["hypotheses"][h]["decision"] for h in ("H1", "H2", "H3")},
        "rankings": {"quarter": ranks[0]["quarter"], "rows": ranks, "verification": ver,
                     "for_target_quarter": "UNAVAILABLE for " + rec["period"]["target_quarter"]},
        "face_validity": NNS,
        "caveats": ["Development copy. Nothing here is deployed or published.",
                    "Risk rankings are relative ordinal estimates, not official food insecurity classifications.",
                    f"{ver['poverty_province_fallback_lgus']} of 142 LGUs use a province-mean poverty value "
                    "(no LGU-specific PSA estimate); their within-province order reflects population density only.",
                    "Accuracy above 75% is reachable without skill on these test rows (always-HIGH is shown beside it)."]}
    pub = EXP / "dashboard_dev" / "public"
    (pub / "e23_dashboard.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    pdf = pub / f"aiPHeed_forecast_report_{rec['period']['target_quarter']}.pdf"
    build_pdf(data, pdf)
    print(json.dumps({"json_sha256": hashlib.sha256((pub / "e23_dashboard.json").read_bytes()).hexdigest(),
                      "pdf": pdf.name}, indent=1))


def build_pdf(d, path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    st = getSampleStyleSheet()
    s = []
    P = lambda t, k="BodyText": s.append(Paragraph(t, st[k]))  # noqa: E731
    P("aiPHeed quarterly forecast report — DA Region IV-A (development copy)", "Title")
    for k in ("target", "news", "cutoff"):
        P(d["labels"][k])
    P(f"Status: <b>{d['status']}</b>")
    P("No forecast has been produced for this period. Missing or blocking items:" if d["forecast"] is None
      else "Forecast produced.")
    for m in d["missing"]:
        P("- " + m.replace("&", "&amp;").replace("<", "&lt;"))
    n = d["supporting_news"]
    P(f"Eligible supporting articles ({d['period']['news_display']}): {n['eligible']}. "
      "Province-quarters with fewer than five articles are flagged LIMITED_SIGNAL.")
    s.append(Spacer(1, 8))
    P("Back-test evaluation (primary target: training-window median threshold)", "Heading2")
    rows = [["Lead", "Origins", "HIGH/LOW", "Evaluable", "Proposed acc", "Persistence acc", "Proposed AUC", "Proposed Brier"]]
    for r in d["evaluation"]["origin"]:
        if not r.get("n_origins"):
            rows.append([r["lead"], 0, "-", "no", "-", "-", "-", "-"]); continue
        p, b = r["models"]["PROPOSED_lgbm_combined"], r["models"]["B1_naive_persistence"]
        f = lambda x: "-" if x is None else f"{x:.3f}"  # noqa: E731
        rows.append([r["lead"], r["n_origins"], f"{r['HIGH']}/{r['LOW']}", "yes" if r["evaluable"] else "no",
                     f(p["accuracy"]), f(b["accuracy"]), f(p["ROC_AUC"]), f(p["Brier"])])
    t = Table(rows)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    s.append(t)
    P(f"Maximum reliable lead time: {d['max_reliable_lead'] or 'none'}.")
    P("Null hypotheses", "Heading2")
    for h, v in d["hypotheses"].items():
        P(f"{h}: {v['decision']}" + (f" — {v['why']}" if v.get("why") else ""))
    P("Municipal and city rankings", "Heading2")
    P(f"{d['rankings']['for_target_quarter']}. Shown in the dashboard as a back-test example only: "
      f"{d['rankings']['quarter']}. {d['caveats'][2]}")
    P("Face-validity anchor", "Heading2")
    fv = d["face_validity"]
    P(f"DOST-FNRI 2023 NNS: CALABARZON moderate-to-severe household food insecurity {fv['calabarzon_2023_moderate_severe_pct']}% "
      f"(95% CI {fv['calabarzon_2023_ci95'][0]}–{fv['calabarzon_2023_ci95'][1]}), {fv['calabarzon_rank']}; national "
      f"{fv['national_2023_moderate_severe_pct']}%. {fv['use']}")
    P(d["labels"]["caveat"])
    P(f"Generated from forecast record {d['generated_from']['forecast_record_sha256'][:16]}… and E23 run "
      f"{d['generated_from']['e23_run']}.", "Italic")
    SimpleDocTemplate(str(path), pagesize=A4, title="aiPHeed forecast report").build(s)


if __name__ == "__main__":
    main()

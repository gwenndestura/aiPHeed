"""E24 dashboard JSON + PDF from single sources (no typed numbers): forecast record (backend_dev), E24 sealed results,
LGU_RANKING_VALIDATION.csv, minimum_data.json. Also writes BASELINE_COMPARISON.csv and FEATURE_ABLATION_RESULTS.csv.
Usage: python -B runner/build_outputs.py <E24 run id>"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "backend_dev"))
from app.quarterly.update import load_latest  # noqa: E402

NAMES = {"PROPOSED_lgbm_combined": "Proposed LightGBM (news + government)",
         "B1_naive_persistence": "B1 Naive persistence (Obj. 4-I)", "B2_lr_combined": "B2 LR combined (Obj. 4-IV)",
         "B3_lr_gov_only": "B3 LR government (Obj. 4-II)", "B4_lr_nlp_only": "B4 LR news (Obj. 4-III)",
         "B5_lgbm_gov_only": "B5 LightGBM government (SOP Q3)", "B6_lgbm_nlp_only": "B6 LightGBM news (SOP Q3)",
         "MAJ_training_majority": "Training majority (imbalance diagnostic only)",
         "FINAL_E24F": "E24-F persistence-gated final candidate"}
GROUP = {"ABL_lr_P": ("LR", "P"), "ABL_lr_GP": ("LR", "G+P"), "ABL_lr_NP": ("LR", "N+P"), "ABL_lr_GNP": ("LR", "G+N+P"),
         "ABL_lrc_GNP": ("LR, nested C", "G+N+P"), "ABL_lgbm_P": ("LightGBM", "P"), "ABL_lgbm_GP": ("LightGBM", "G+P"),
         "ABL_lgbm_NP": ("LightGBM", "N+P"), "ABL_lgbm_GNP": ("LightGBM", "G+N+P"),
         "B2_lr_combined": ("LR", "G+N"), "B3_lr_gov_only": ("LR", "G"), "B4_lr_nlp_only": ("LR", "N"),
         "B5_lgbm_gov_only": ("LightGBM", "G"), "B6_lgbm_nlp_only": ("LightGBM", "N"),
         "PROPOSED_lgbm_combined": ("LightGBM", "G+N"), "B1_naive_persistence": ("Persistence", "last label")}


def main():
    run = sys.argv[1]
    rd = EXP / "runs" / run
    R = json.loads((rd / "results.json").read_text(encoding="utf-8"))
    M = pd.read_csv(rd / "metrics_all.csv")
    rec = load_latest(EXP / "backend_dev" / "data" / "quarterly_runs")
    md = json.loads((EXP / "runs" / "minimum_data.json").read_text(encoding="utf-8"))
    # ---- BASELINE_COMPARISON.csv and FEATURE_ABLATION_RESULTS.csv
    base = M[M["model"].isin(list(NAMES))].copy()
    base.insert(3, "model_name", base["model"].map(NAMES))
    base["role"] = base["model"].map(lambda m: "diagnostic" if m == "MAJ_training_majority" else
                                     ("final candidate" if m == "FINAL_E24F" else "required"))
    extra = []
    for t in ("T1", "T2"):
        pr = pd.read_csv(rd / f"predictions_{t}.csv", dtype={"province_code": str})
        for k, g in pr[pr["model"] == "B1_naive_persistence"].groupby("lead"):
            y = g["y"]
            extra.append({"target": t, "lead": k, "model": "REF_always_HIGH",
                          "model_name": "Always HIGH (reference; uses the test-set class balance, not a forecaster)",
                          "n_rows": len(y), "n_test_quarters": g["origin"].nunique(), "HIGH": int(y.sum()),
                          "LOW": int((1 - y).sum()), "accuracy": float(y.mean()), "balanced_accuracy": 0.5,
                          "recall": 1.0 if y.sum() else None, "specificity": 0.0 if (1 - y).sum() else None,
                          "role": "reference"})
    base = pd.concat([base, pd.DataFrame(extra)], ignore_index=True).sort_values(["target", "lead", "model"])
    base.to_csv(EXP / "BASELINE_COMPARISON.csv", index=False, lineterminator="\n")
    ab = M[M["model"].isin(list(GROUP))].copy()
    ab.insert(3, "family", ab["model"].map(lambda m: GROUP[m][0]))
    ab.insert(4, "feature_groups", ab["model"].map(lambda m: GROUP[m][1]))
    pers = M[M["model"] == "B1_naive_persistence"][["target", "lead", "accuracy", "Brier"]].rename(
        columns={"accuracy": "persistence_accuracy", "Brier": "persistence_Brier"})
    ab = ab.merge(pers, on=["target", "lead"])
    ab["accuracy_minus_persistence"] = ab["accuracy"] - ab["persistence_accuracy"]
    ab["Brier_minus_persistence"] = ab["Brier"] - ab["persistence_Brier"]
    ab.to_csv(EXP / "FEATURE_ABLATION_RESULTS.csv", index=False, lineterminator="\n")
    # ---- dashboard JSON
    with open(EXP / "LGU_RANKING_VALIDATION.csv", encoding="utf-8") as f:
        ranks = list(csv.DictReader(f))
    lgu = json.loads((EXP / "runs" / "lgu_validation.json").read_text(encoding="utf-8"))
    ev = {}
    for t in ("T1", "T2"):
        ev[t] = []
        for k, v in R[t].items():
            ev[t].append({"lead": int(k), "n_origins": v["n_test_quarters"], "HIGH": v["HIGH"], "LOW": v["LOW"],
                          "evaluable": v["evaluable"], "strongest_baseline": v["strongest_baseline"],
                          "criteria": v["criteria"], "final_choice_share": v["final_choice_share"],
                          "models": {m: {"name": NAMES[m], **{q: v["metrics"][m][q] for q in
                                         ("accuracy", "balanced_accuracy", "precision", "recall", "F1", "ROC_AUC",
                                          "Brier", "TP", "FP", "FN", "TN")}} for m in NAMES}})
    data = {"generated_from": {"e24_run": run, "forecast_record_sha256": rec["content_sha256"]},
            "period": rec["period"], "status": rec["status"], "missing": rec["missing"], "labels": rec["labels"],
            "cutoff_reached": rec["cutoff_reached"],
            "supporting_news": {k: v for k, v in rec["supporting_news"].items() if k != "articles"},
            "supporting_articles": rec["supporting_news"]["articles"], "forecast": rec["forecast"],
            "evaluation": ev, "minimum_new_quarters": md,
            "rankings": {"quarter": ranks[0]["ranking_quarter"], "rows": ranks, "verification": lgu,
                         "for_target_quarter": "UNAVAILABLE for " + rec["period"]["target_quarter"]},
            "caveats": ["Development copy. Nothing here is deployed or published.",
                        "Risk rankings are relative ordinal estimates, not official food-insecurity measurements.",
                        f"{lgu['lgus_with_substitute']} of 142 LGUs have no PSA municipal poverty estimate in the "
                        "authorized data; their poverty term is a labelled province-mean substitute.",
                        "T2 (relative price pressure) is exploratory and is not a food-insecurity outcome."]}
    pub = EXP / "dashboard_dev" / "public"
    (pub / "e24_dashboard.json").write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    build_pdf(data, pub / f"aiPHeed_forecast_report_{rec['period']['target_quarter']}.pdf")
    print(json.dumps({"json_sha256": hashlib.sha256((pub / "e24_dashboard.json").read_bytes()).hexdigest()}))


def build_pdf(d, path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    st = getSampleStyleSheet()
    s = []
    P = lambda t, k="BodyText": s.append(Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;"), st[k]))  # noqa
    f = lambda x: "-" if x is None else f"{x:.3f}"  # noqa: E731
    P("aiPHeed quarterly forecast report - DA Region IV-A (development copy)", "Title")
    for k in ("target", "news", "cutoff"):
        P(d["labels"][k])
    P(f"Status: {d['status']}. No forecast is shown for this period." if d["forecast"] is None else f"Status: {d['status']}")
    for m in d["missing"]:
        P("- " + m)
    P("Back-test evaluation, approved target (T1), development origins", "Heading2")
    rows = [["Lead", "Quarters", "HIGH/LOW", "Evaluable", "Final acc", "Bal. acc", "Persistence acc", "Strongest", "Goal met"]]
    for r in d["evaluation"]["T1"]:
        fm, pm = r["models"]["FINAL_E24F"], r["models"]["B1_naive_persistence"]
        met = all(v is True for k, v in r["criteria"].items() if k != "C9_generalizes_unseen")
        rows.append([r["lead"], r["n_origins"], f"{r['HIGH']}/{r['LOW']}", "yes" if r["evaluable"] else "no",
                     f(fm["accuracy"]), f(fm["balanced_accuracy"]), f(pm["accuracy"]), r["strongest_baseline"].split("_")[0],
                     "no (C9 not assessable)" if not met else "C1-C8 yes; C9 not assessable"])
    t = Table(rows)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 7)]))
    s.append(t)
    s.append(Spacer(1, 6))
    P("Municipal and city rankings", "Heading2")
    P(d["rankings"]["for_target_quarter"] + ". " + d["caveats"][2])
    P(d["labels"]["caveat"])
    P(f"Generated from forecast record {d['generated_from']['forecast_record_sha256'][:16]} and E24 run "
      f"{d['generated_from']['e24_run']}.", "Italic")
    SimpleDocTemplate(str(path), pagesize=A4, title="aiPHeed forecast report").build(s)


if __name__ == "__main__":
    main()

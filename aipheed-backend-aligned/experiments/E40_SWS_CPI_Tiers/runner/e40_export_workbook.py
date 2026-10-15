"""Regenerate the results workbook for the E40 binary label in the layout of the E39/v1 workbook (same nine sheets),
adding a calibrated-score column and a reliability flag. Every value comes from the frozen label, the single
evaluation run and the sealed forecasts. Holdout outcomes (2025-Q4..2026-Q3) are NOT shown: their observed label
cells read "holdout (not read)".

    <backend venv python> -B runner/e40_export_workbook.py runs/eval_<stamp>      (cwd = backend/)
    -> docs/aiPHeed_Results_All_Quarters_E40_BinaryLabel_2026-10-15.xlsx
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

E40 = Path(__file__).resolve().parents[1]
ROOT = E40.parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_s = importlib.util.spec_from_file_location("e39wb", E40.parent / "E39_Label_V2" / "runner" / "e39_export_workbook.py")
W = importlib.util.module_from_spec(_s)
_s.loader.exec_module(W)
NAMES, ORDER, r4, write_xlsx = W.NAMES, W.ORDER, W.r4, W.write_xlsx


def main(run_dir: str):
    run = Path(run_dir) if Path(run_dir).is_absolute() else E40 / run_dir
    spec = json.loads((E40 / "label_spec.json").read_text())
    ev = json.loads((run / "evaluation.json").read_text(encoding="utf-8"))
    dg = json.loads((run / "diagnostics.json").read_text(encoding="utf-8"))
    sealed = json.loads((E40 / "frozen" / "E40_HOLDOUT_FORECASTS.json").read_text())
    lab = pd.read_csv(E40 / "label_primary.csv", dtype={"province_code": str})
    comp = pd.read_csv(E40 / "runs" / "triggers" / "composition.csv", dtype={"province_code": str})
    P = pd.read_csv(run / "predictions_dev.csv", dtype={"province_code": str})
    hold = set(spec["holdout_quarters_untouched"])
    dev = spec["development_quarters"]
    fc = {(p, f["target"]): v for f in sealed["forecasts"] for p, v in f["provinces"].items()}
    gate = {f["target"]: f for f in ev["folds"]}
    news_ok = {(r.province_code, r.quarter): bool(r.reliable) for r in comp.itertuples()}
    pers = P[P.method == "PERSISTENCE"].set_index(["province_code", "target"])["p"]
    quarters = sorted(lab["quarter"].unique()) + ["2026-Q4"]

    def score(p, q):
        """(calibrated score, raw/uncalibrated score, reliability flag)."""
        if (p, q) in fc:
            return None, fc[(p, q)]["score"], "UNRELIABLE: uncalibrated sealed forecast (no out-of-fold scores); not scored"
        if q in gate and gate[q]["status"].startswith("fold"):
            return None, None, f"NO MODEL: training fold has {gate[q]['train_HIGH']} HIGH rows (< 2, gate failed)"
        if q in dev:
            return None, None, "NO MODEL: fewer than 8 training quarters at the origin"
        return None, None, "burn-in / reference window (label for training only, never scored)"

    def observed(p, q):
        if q in hold:
            return "holdout (not read)"
        if q == "2026-Q4":
            return "no outcome yet"
        r = lab[(lab.province_code == p) & (lab.quarter == q)]
        return None if r.empty or pd.isna(r["label"].iloc[0]) else r["label"].iloc[0]

    readme = [["aiPHeed results by province and city/municipality: E40 binary food-stress label (exploratory)"],
              ["Built from the frozen E40 outputs (aipheed-backend-aligned/experiments/E40_SWS_CPI_Tiers), not from a live API."],
              [""], ["Rule"], [spec["rule"]],
              ["Signals: SWS Balance Luzon hunger above the P60 of the frozen 2021-Q1..2022-Q4 window (regional), AND "
               "province food CPI YoY or (food - headline) gap above that province's window P60. Binary: HIGH / LOW only."],
              [f"Thresholds (frozen): H > {spec['thresholds']['H']:.2f}%; food and gap thresholds per province in label_spec.json."],
              [f"Development quarters: {', '.join(dev)}. Holdout (untouched, not shown): {', '.join(sorted(hold))}."],
              [""], ["Result of the single evaluation run"], [ev["verdict"]],
              [f"Gate: every walk-forward training fold must hold >= 2 HIGH rows. Failed folds: {', '.join(ev['gate_failed_folds'])}."],
              [f"Band cutoff: {ev['band_cutoff']} ({ev['band_cutoff_rule']})."],
              ["Calibrated score: empty everywhere, because no fold produced out-of-fold scores to calibrate on. The sealed "
               "forecasts for 2025-Q4..2026-Q4 are uncalibrated, clipped to [0.02, 0.98], and not scored."],
              ["Reliability flag: says why a score is missing or unreliable. 'Insufficient news' = fewer than 5 "
               "province-attributed articles in the quarter (the trigger mix is then shown at region level, 4 quarters pooled)."],
              ["Ranks: by score, ties broken by the CPI gap; remaining ties share the rank."],
              ["City/municipality index = province score x within-province vulnerability (PSA 2021 SAE poverty, POPCEN 2024): "
               "a relative position, not a municipal forecast; shown only where a province score exists."],
              [""], ["Indicative, not an official classification. Not a validated measure of food insecurity."]]
    pbq = [["Province", "Code", "Row"] + quarters]
    for p in ORDER:
        pbq.append([NAMES[p], p, "Observed label"] + [observed(p, q) for q in quarters])
        pbq.append([NAMES[p], p, "Score (uncalibrated, sealed)"] + [score(p, q)[1] for q in quarters])
    detail = [["Quarter", "Quarter type", "Province", "Calibrated score", "Uncalibrated score", "Band (score >= cutoff)",
               "Reliability flag", "Persistence prediction", "Observed label", "SWS hunger % (regional)", "sws_hi",
               "Food CPI YoY %", "Headline CPI YoY %", "CPI gap (pp)", "cpi_rel (pp)", "cpi_hi", "gap_hi",
               "both (this quarter)", "News reliable (>= 5 articles)", "Rank (of 5)"]]
    for q in quarters:
        for p in ORDER:
            r = lab[(lab.province_code == p) & (lab.quarter == q)]
            r = r.iloc[0] if len(r) else None
            cal, raw, flag = score(p, q)
            shown = r is not None and q not in hold
            kind = ("Forecast" if q == "2026-Q4" else "Holdout (sealed)" if q in hold else
                    "Development" if q in dev else "Burn-in")
            detail.append([q, kind, NAMES[p], cal, raw, None if raw is None else ("HIGH" if raw >= ev["band_cutoff"] else "LOW"),
                           flag, r4(pers.get((p, q))), observed(p, q),
                           r4(r["H"]) if shown else None, r4(r["sws_hi"]) if shown else None,
                           r4(r["food"]) if shown else None, r4(r["headline"]) if shown else None,
                           r4(r["cpi_gap"]) if shown else None, r4(r["cpi_rel"]) if shown else None,
                           r4(r["cpi_hi"]) if shown else None, r4(r["gap_hi"]) if shown else None,
                           r4(r["both"]) if shown else None,
                           None if (p, q) not in news_ok else ("yes" if news_ok[(p, q)] else "insufficient news"),
                           fc[(p, q)]["rank"] if (p, q) in fc else None])
    ovp = [["Province", "Row"] + quarters]
    for p in ORDER:
        ovp.append([NAMES[p], "Predicted (band)"] + [None if score(p, q)[1] is None else
                                                    ("HIGH" if score(p, q)[1] >= ev["band_cutoff"] else "LOW") for q in quarters])
        ovp.append([NAMES[p], "Persistence"] + [None if pd.isna(pers.get((p, q), float("nan"))) else
                                               ("HIGH" if pers[(p, q)] >= 0.5 else "LOW") for q in quarters])
        ovp.append([NAMES[p], "Observed"] + [observed(p, q) for q in quarters])
    from app.quarterly.lgu_audit import build_ranking

    vul = pd.read_csv(ROOT / "backend" / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    ros = pd.read_csv(ROOT / "backend" / "data" / "reference" / "calabarzon_lgus.csv", dtype={"lgu_psgc": str})
    sq = sorted({q for (_, q) in fc})
    lgu_idx, lgu_rank, long = {}, {}, [["Quarter", "Province", "City / Municipality", "Type", "PSGC code", "Risk index",
                                       "Rank in province", "Tied", "Reliability flag"]]
    for q in sq:
        rk = build_ranking(vul, ros, {p: float(fc[(p, q)]["score"]) for p in ORDER}, {"source": f"E40 sealed {q}"})
        for r in rk["rows"]:
            lgu_idx[(r["lgu_code"], q)] = r["risk_index"]
            lgu_rank[(r["lgu_code"], q)] = r["rank_in_province"]
            long.append([q, r["province"], r["lgu_name"], r["lgu_type"], r["lgu_code"], r["risk_index"],
                         r["rank_in_province"], bool(r["tied"]), "UNRELIABLE: uncalibrated sealed province score"])
    v2 = vul.sort_values(["province", "lgu_name"])
    lgu = [["Province", "City / Municipality", "Type", "PSGC code", "Population 2024", "Poverty rate (%)"] + sq]
    lgr = [["Province", "City / Municipality"] + sq]
    for r in v2.itertuples():
        lgu.append([r.province, r.lgu_name, r.lgu_type, r.lgu_code, int(r.population_2024), r4(r.poverty_value_used)]
                   + [lgu_idx.get((r.lgu_code, q)) for q in sq])
        lgr.append([r.province, r.lgu_name] + [lgu_rank.get((r.lgu_code, q)) for q in sq])
    methods = ["E40_BLEND", "E40_BLEND_NO_CPI", "LR_GOV_ONLY", "LR_NLP_ONLY", "PERSISTENCE", "ALWAYS_MAJORITY"]
    fm = {(x["method"], x["target"]): x for x in ev["fold_metrics"]}
    sbd = [["Fold (target)", "Origin", "Train quarters", "Train rows", "Train HIGH", "Gate (>= 2 HIGH)", "Test HIGH",
            "Metric"] + methods]
    for f in ev["folds"]:
        if not f["status"].startswith("fold"):
            continue
        sbd.append([f["target"], f["origin"], f["train_label_quarters"], f["train_rows"], f["train_HIGH"],
                    "pass" if f["gate_ge2_HIGH"] else "FAIL", f["test_HIGH"], "Brier"] +
                   [r4(fm[(m, f["target"])]["Brier"]) if (m, f["target"]) in fm else "no model (gate)" for m in methods])
    bl = [["Method", "n", "HIGH", "Accuracy", "Accuracy 95% CI", "Balanced accuracy", "Bal. acc 95% CI", "Precision HIGH",
           "Recall HIGH", "F1 HIGH", "AUC", "Brier", "Brier 95% CI", "Mean per-quarter Spearman", "Status"]]
    ci = lambda v: None if not v else f"{v[0]:.3f} to {v[1]:.3f}"  # noqa: E731
    for m in methods:
        t = ev["table"][m]
        if "status" in t:
            bl.append([m] + [None] * 13 + [t["status"]])
            continue
        bl.append([m, t["n"], t["HIGH"], r4(t["accuracy"]), ci(t["CI95_accuracy"]), r4(t["balanced_accuracy"]),
                   ci(t["CI95_balanced_accuracy"]), r4(t["precision_HIGH"]), r4(t["recall_HIGH"]), r4(t["F1_HIGH"]),
                   r4(t["AUC"]), r4(t["Brier"]), ci(t["CI95_Brier"]), r4(t["spearman_per_quarter_mean"]),
                   "scored on all 6 folds (quarter-cluster bootstrap, 2000 draws)"])
    bl += [[""], ["Label-recovery rule check (fixed rules on origin-time inputs; not fitted, not a forecast evaluation)"]]
    for k, v in dg["label_recovery_rule_check"].items():
        if isinstance(v, dict):
            bl.append([k, None, None, r4(v["accuracy"]), None, r4(v["balanced_accuracy"]), None, None, r4(v["recall_HIGH"]),
                       None, None, None, None, None, "uses CPI" if v["uses_cpi"] else "no CPI"])
    out = E40 / "docs" / "aiPHeed_Results_All_Quarters_E40_BinaryLabel_2026-10-15.xlsx"
    out.parent.mkdir(exist_ok=True)
    write_xlsx(out, [("Read me", readme), ("Provinces by quarter", pbq), ("Province detail", detail),
                     ("Observed vs predicted", ovp), ("Cities-Municipalities", lgu), ("City-Mun rank in province", lgr),
                     ("City-Mun detail", long), ("Scores by date", sbd), ("Baselines", bl)])
    print(out, len(detail) - 1, "province rows;", len(long) - 1, "LGU rows")


if __name__ == "__main__":
    main(sys.argv[1])

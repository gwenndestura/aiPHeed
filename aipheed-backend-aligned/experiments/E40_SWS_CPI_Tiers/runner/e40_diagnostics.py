"""E40 diagnostics after the single evaluation run: (1) label-recovery rule check (no model, no tuning): how much of the
target label fixed rules on origin-time inputs reproduce, with and without CPI; (2) face validity against
researcher-supplied reference statistics; (3) the before (served v1 / E36) vs after (E40) table.
Development quarters only; holdout labels are never read.

    <backend venv python> -B runner/e40_diagnostics.py <eval run folder name>   (cwd = backend/, for the v1 API)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e40_model as M  # noqa: E402

qi, qn = M.qi, M.qn
REFERENCES = {   # researcher-supplied (2026-10-15); not re-verified in this run (no SWS/PSA web search, by rule)
    "FIES moderate-to-severe, national, 2023 NNS (DOST-FNRI)": 31.4,
    "FIES moderate-to-severe, national, 2021 ENNS (DOST-FNRI)": 33.4,
    "SWS hunger, national, March 2026": 23.2,
    "SWS hunger, national, September 2026": 22.6,
    "PSA poverty incidence among families/population, CALABARZON, 2023": 7.9,
    "PSA poverty incidence, CALABARZON, 2021": 10.2}


def label_recovery(d: M.Data, dev: list[int]) -> dict:
    rows = []
    for tgt in dev:
        X = d.features(tgt - 1)
        for r in X.itertuples():
            y = d.y.get((r.province_code, tgt))
            if y is not None:
                rows.append({"target": qn(tgt), "y": int(y), "both_proxy": r.both_proxy, "cpi_sig": r.cpi_sig_now,
                             "sws_hi": r.sws_last_hi, "y_last": r.y_last})
    g = pd.DataFrame(rows)
    out = {"rows": len(g), "HIGH": int(g["y"].sum()),
           "note": "fixed rules, not fitted; a rule that matches the label shows how much of the target is already "
                   "fixed by origin-time inputs (the label is a deterministic function of SWS and CPI)"}
    for rule in ["both_proxy", "cpi_sig", "sws_hi", "y_last"]:
        yh = g[rule].fillna(0).astype(int)
        out[rule] = {"accuracy": float((yh == g["y"]).mean()), "balanced_accuracy": M.balanced_acc(g["y"], yh),
                     "recall_HIGH": float(yh[g["y"] == 1].mean()) if g["y"].sum() else None,
                     "flags": int(yh.sum()), "uses_cpi": rule in ("both_proxy", "cpi_sig", "y_last")}
    return out


def v1_before() -> dict:
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    rows = []
    for y in range(2021, 2027):
        for k in range(1, 5):
            q = f"{y}-Q{k}"
            r = c.get(f"/api/v1/provinces?quarter={q}&horizon=forecast")
            if r.status_code != 200:
                continue
            for p in r.json()["data"]:
                if p.get("riskScore") is not None:
                    rows.append({"quarter": q, "score": p["riskScore"], "level": p["riskLevel"],
                                 "tied": bool(p.get("rankTied"))})
    g = pd.DataFrame(rows)
    rec = json.loads(Path("data/e36/e36_record.json").read_text(encoding="utf-8"))
    return {"source": "served v1 dashboard (/api/v1/provinces?horizon=forecast), engine aiPHeed-E36-LGBM",
            "province_quarters": len(g), "quarters": sorted(g["quarter"].unique()) if len(g) else [],
            "HIGH_share_overall": float((g["level"] == "high").mean()),
            "HIGH_share_by_year": g.assign(y=g["quarter"].str[:4]).groupby("y")["level"].apply(lambda s: float((s == "high").mean())).to_dict(),
            "score_P10_P50_P90": [float(np.percentile(g["score"], x)) for x in (10, 50, 90)],
            "share_score_gt_0_95": float((g["score"] > 0.95).mean()),
            "rows_in_a_tie": int(g["tied"].sum()),
            "quarters_with_a_tie": int(g.groupby("quarter")["tied"].any().sum()),
            "metrics": rec["validation"]["model_evaluation"]}


def main():
    run = M.E40 / "runs" / sys.argv[1]
    ev = json.loads((run / "evaluation.json").read_text(encoding="utf-8"))
    d = M.Data()
    dev = [qi(q) for q in d.spec["development_quarters"]]
    lab = d.lab[d.lab["quarter"].isin(d.spec["development_quarters"]) & d.lab["y_high"].notna()]
    assert lab["quarter"].map(qi).min() >= qi("2021-Q1") and d.m["reference_month"].min() >= "2021-01"
    rec = label_recovery(d, dev)
    sealed = json.loads((M.E40 / "frozen" / "E40_HOLDOUT_FORECASTS.json").read_text())
    sc = pd.DataFrame([{"target": f["target"], **v} for f in sealed["forecasts"] for v in f["provinces"].values()])
    mk = json.loads((M.E40 / "runs" / "triggers" / "market_audit.json").read_text(encoding="utf-8"))
    after_share = float(lab["y_high"].mean())
    after = {"label": "E40 binary label (P60, sustain 2), development quarters 2023-Q1..2025-Q1",
             "HIGH_share_overall": after_share,
             "HIGH_share_by_year": lab.assign(y=lab["quarter"].str[:4]).groupby("y")["y_high"].mean().to_dict(),
             "dev_quarters_per_year": lab.groupby(lab["quarter"].str[:4])["quarter"].nunique().to_dict(),
             "quarters_all_five_identical": int(lab.groupby("quarter")["y_high"].nunique().eq(1).sum()),
             "calibrated_dev_scores": "none: every development fold failed the >= 2-HIGH training gate",
             "sealed_forecast_scores_P10_P50_P90 (uncalibrated, not scored)":
                 [float(np.percentile(sc["score"], x)) for x in (10, 50, 90)] if len(sc) else None,
             "sealed_share_gt_0_95": float((sc["score"] > 0.95).mean()) if len(sc) else None,
             "sealed_rows_in_a_tie": int(sc.groupby("target")["rank"].apply(lambda s: s.duplicated(keep=False).sum()).sum()) if len(sc) else None,
             "metrics": {"E40_BLEND": ev["table"]["E40_BLEND"], "PERSISTENCE": {k: ev["table"]["PERSISTENCE"][k] for k in
                         ("n", "accuracy", "balanced_accuracy", "Brier", "CI95_balanced_accuracy", "CI95_Brier")},
                         "ALWAYS_MAJORITY": {k: ev["table"]["ALWAYS_MAJORITY"][k] for k in
                                             ("n", "accuracy", "balanced_accuracy", "Brier", "CI95_Brier")}}}
    market = {"news_market_share_of_trigger_hits_v1": mk["market_share_of_trigger_hits_attributed"]["before_v1"],
              "news_market_share_of_trigger_hits_v2": mk["market_share_of_trigger_hits_attributed"]["after_v2"],
              "dashboard_driver_split_market": "100% in every province-quarter (SHAP grouping artefact, not news)"}
    face = {"E40_dev_HIGH_share_pct": round(100 * after_share, 1), "references_pct": REFERENCES,
            "reading": ("Not like-for-like: the E40 share is the fraction of province-quarters flagged HIGH by a "
                        "relative (window-percentile) rule, not a household prevalence. The references bound what an "
                        "absolute food-insecurity rate looks like (FIES 31-33% national; SWS hunger 22-23% national in "
                        "2026; CALABARZON poverty 8-10%). A province-quarter HIGH share of 11% says the label marks the "
                        "upper tail of the region's own 2021-2022 experience, not that 11% of households are food "
                        "insecure."),
            "chapter1_44pct_claim": {
                "text": "Chapter I (verbatim extraction, line 9): '... with 44% of households experiencing moderate to "
                        "severe food insecurity in 2023', attributed to DOST-FNRI (2024).",
                "issue": "The researcher-supplied national figure for moderate-to-severe food insecurity in 2023 (FIES, "
                         "2023 NNS) is 31.4%, not 44%. 44% may be a different measure (for example mild-to-severe, or a "
                         "sub-population); this run did not verify either figure.",
                "proposed_correction": "'... with 31.4% of households experiencing moderate to severe food insecurity "
                                       "in 2023 (DOST-FNRI, 2024)' -- after checking the FNRI 2023 NNS FIES table; the "
                                       "thesis file was not edited."}}
    out = {"eval_run": run.name, "label_recovery_rule_check": rec, "face_validity": face,
           "before_after": {"before_v1": v1_before(), "after_E40": after, "market": market}}
    (run / "diagnostics.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"label_recovery": rec, "before": {k: v for k, v in out["before_after"]["before_v1"].items() if k != "metrics"},
                      "after": {k: v for k, v in after.items() if k != "metrics"}}, indent=1, default=float))


if __name__ == "__main__":
    main()

"""
E130 tabular deliverables that record what was and was not run: walk-forward splits, training results, predictions,
the Lead 1-4 comparison, the baseline comparison, the feature-group ablation and the reliable-horizon comparison.
With the gate BLOCKED every quarterly cell is marked not evaluable and its reason; the survey-year seal is the only
prediction set.

Run:  python runner/report_e130.py      (after build_e130.py, seal_e130.py and diagnostics_e130.py)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e130_lib as L  # noqa: E402

ROOT, OUT = L.ROOT, L.OUT
ORIGINS = [L.qs(i) for i in range(L.qi("2021-Q1"), L.qi("2026-Q3") + 1)]
MODELS = {"M1_LightGBM": "proposed (LightGBM regression)", "M2_Persistence": "baseline", "M3_PSA_only": "baseline",
          "M4_NLP_only": "baseline", "M5_Linear": "baseline (continuous counterpart of logistic regression)"}
BLOCKED = "not evaluable: gate BLOCKED (no quarterly provincial reference; G3/G8 fail)"
GROUPS = ["1 Market and food prices", "2 Climate and environmental stress", "3 Employment and OFW remittances",
          "4 News and NLP", "5 Poverty and social vulnerability"]


def _save(df: pd.DataFrame, path: Path) -> None:
    """Write only when the content changes, so a deliverable that is open elsewhere (Windows locks files open in
    Excel) is left alone when nothing in it would change."""
    new = df.to_csv(index=False, lineterminator="\n").encode("utf-8")
    if path.exists() and path.read_bytes().replace(b"\r\n", b"\n") == new:
        return
    try:
        path.write_bytes(new)
    except PermissionError as e:
        raise SystemExit(f"{path.name} must change but is locked (close it, e.g. in Excel, and re-run)") from e


def splits() -> pd.DataFrame:
    rows = []
    for k in L.LEADS:
        s = L.walk_forward_splits({}, k, ORIGINS)
        s.insert(0, "design", "quarterly provincial (protocol section 9)")
        s["status"] = BLOCKED
        rows.append(s)
    sy = pd.DataFrame([{"design": "survey-year seal (protocol section 7)", "origin": "2023 round (published 2024-08-15)",
                        "issue_date": "2026-10-31 (seal)", "lead": "next survey round", "target_quarter": "next provincial round after 2023 (none published as of 2026-10-31)",
                        "n_train_targets": 1, "train_last_target": "2023 round (5 province changes 2021->2023)",
                        "target_has_reference": True, "executable": False,
                        "status": "sealed; scoring waits for PSA to publish provincial subsistence after 2023"}])
    df = pd.concat(rows + [sy], ignore_index=True)
    _save(df, ROOT / "E130_WALK_FORWARD_SPLITS.csv")
    return df


def training_results() -> pd.DataFrame:
    rows = []
    for m, role in MODELS.items():
        for k in L.LEADS:
            rows.append({"task": "quarterly provincial risk score", "model": m, "role": role, "lead": k, "trained": False,
                         "n_train_rows": 0, "n_eval_rows": 0, "train_mae": np.nan, "oos_mae": np.nan, "status": BLOCKED})
    for m, why in (("S1_persistence", "non-learned; sealed"), ("S2_two_round_mean", "non-learned; sealed"),
                   ("S3_eb_shrunk_2023", "non-learned (EB weights from the 2023 cross-section); sealed")):
        rows.append({"task": "survey-year provincial PFDR", "model": m, "role": "survey-year forecaster", "lead": "next round",
                     "trained": False, "n_train_rows": 0, "n_eval_rows": 5, "train_mae": np.nan, "oos_mae": np.nan, "status": why})
    for m in ("M1_LightGBM", "M3_PSA_only", "M4_NLP_only", "M5_Linear"):
        rows.append({"task": "survey-year provincial PFDR", "model": m, "role": MODELS[m], "lead": "next round", "trained": False,
                     "n_train_rows": 5, "n_eval_rows": 5, "train_mae": np.nan, "oos_mae": np.nan,
                     "status": "not trainable: 5 training rows (one change per province) < protocol minimum 20"})
    df = pd.DataFrame(rows)
    _save(df, ROOT / "E130_MODEL_TRAINING_RESULTS.csv")
    return df


def predictions() -> pd.DataFrame:
    s = pd.read_csv(L.SEALED / "E130_SURVEY_YEAR_SEAL.csv")
    scored = (OUT / "seal_scores.json").exists()
    s["task"] = "survey-year provincial PFDR (% of population below the food threshold)"
    s["reference_value"] = np.nan
    s["status"] = "scored (see out/seal_scores.json)" if scored else "sealed; no provincial subsistence round after 2023 is published (owner-verified 2026-10-31); unscored"
    s["seal_sha256"] = L.sha256(L.SEALED / "E130_SURVEY_YEAR_SEAL.csv")
    _save(s, ROOT / "E130_NUMERICAL_RISK_SCORE_PREDICTIONS.csv")
    return s


def lead_comparison(mp: pd.DataFrame) -> pd.DataFrame:
    one = mp[mp.province == L.PROVINCES[0]]
    rows = []
    for k in L.LEADS:
        o = one[one.operational_lead == k]
        hs = pd.to_numeric(o.sws_information_horizon_q, errors="coerce")
        ha = pd.to_numeric(o.sws_information_horizon_release_anchored_q, errors="coerce")
        hp = pd.to_numeric(o.pfdr_information_horizon_q, errors="coerce")
        for m in MODELS:
            rows.append({"lead": k, "operational_meaning": o.operational_meaning.iloc[0], "model": m,
                         "valid_evaluation_origins": 0, "independent_target_observations": 0,
                         "mae": np.nan, "rmse": np.nan, "r2": np.nan, "within_tolerance": np.nan, "direction_accuracy": np.nan,
                         "classification_accuracy": np.nan, "balanced_accuracy": np.nan,
                         "N1_N7": "not evaluable", "R1_R7": "not evaluable (no approved PFDR category thresholds)",
                         "sws_info_horizon_quarter_start_median": float(hs.median()),
                         "sws_info_horizon_release_anchored_median": float(ha.median()),
                         "pfdr_info_horizon_median_q": float(hp.median()) if hp.notna().any() else np.nan,
                         "status": BLOCKED})
    df = pd.DataFrame(rows)
    _save(df, ROOT / "E130_LEAD_1_TO_4_NUMERICAL_COMPARISON.csv")
    return df


def baseline_comparison() -> pd.DataFrame:
    rows = []
    for k in L.LEADS:
        for b in ("M2_Persistence", "M3_PSA_only", "M4_NLP_only", "M5_Linear"):
            rows.append({"task": "quarterly provincial risk score", "lead": k, "model": "M1_LightGBM", "baseline": b,
                         "identical_rows": 0, "mae_model": np.nan, "mae_baseline": np.nan, "rmse_model": np.nan,
                         "rmse_baseline": np.nan, "abs_improvement_mae": np.nan, "rel_improvement_mae": np.nan,
                         "p_cluster_bootstrap": np.nan, "lightgbm_better": "not established", "status": BLOCKED})
    scores = json.load(open(OUT / "seal_scores.json")) if (OUT / "seal_scores.json").exists() else None
    for b in ("S2_two_round_mean", "S3_eb_shrunk_2023"):
        rec = {"task": "survey-year provincial PFDR", "lead": "next round", "model": b, "baseline": "S1_persistence",
               "identical_rows": 5, "status": "unscored (no provincial subsistence round after 2023 published)"}
        if scores:
            a, p = scores["models"][b], scores["models"]["S1_persistence"]
            rec.update(mae_model=a["mae"], mae_baseline=p["mae"], rmse_model=a["rmse"], rmse_baseline=p["rmse"],
                       abs_improvement_mae=p["mae"] - a["mae"], rel_improvement_mae=1 - a["mae"] / p["mae"] if p["mae"] else np.nan,
                       status="scored; five provinces, descriptive only")
        rows.append(rec)
    df = pd.DataFrame(rows)
    _save(df, ROOT / "E130_BASELINE_COMPARISON.csv")
    return df


def ablation(fa: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for arm in ["all five groups"] + [f"without {g}" for g in GROUPS]:
        g = arm.replace("without ", "")
        sub = fa[fa.trigger_group.str.startswith(g[:1])] if arm != "all five groups" else fa
        prov = sub[sub.resolution.astype(str).str.startswith("province")]
        for k in L.LEADS:
            rows.append({"arm": arm, "lead": k, "status": BLOCKED, "delta_mae": np.nan, "delta_within_tolerance": np.nan,
                         "group_features_removed": 0 if arm == "all five groups" else int(len(sub)),
                         "group_provincial_features": "" if arm == "all five groups" else int(len(prov)),
                         "group_median_province_specific_share": "" if arm == "all five groups" else
                         round(float(1 - pd.to_numeric(prov.share_common_quarter_effect, errors="coerce").median()), 3)
                         if len(prov) else ""})
    df = pd.DataFrame(rows)
    _save(df, ROOT / "E130_FEATURE_GROUP_ABLATION.csv")
    return df


def horizon_comparison() -> pd.DataFrame:
    rows = [{"model": m, "max_reliable_lead": "none (not evaluable)", "lead1": "not evaluable", "lead2": "not evaluable",
             "lead3": "not evaluable", "lead4": "not evaluable", "exceeds_every_baseline": "not established",
             "lead2_operational_status": "failed (not evaluable: no provincial quarterly reference)"} for m in MODELS]
    df = pd.DataFrame(rows)
    _save(df, ROOT / "E130_RELIABLE_HORIZON_COMPARISON.csv")
    return df


if __name__ == "__main__":
    mp = pd.read_csv(ROOT / "E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv")
    fa = pd.read_csv(ROOT / "E130_PROVINCIAL_FEATURE_AVAILABILITY.csv")
    for name, df in (("splits", splits()), ("training", training_results()), ("predictions", predictions()),
                     ("leads", lead_comparison(mp)), ("baselines", baseline_comparison()), ("ablation", ablation(fa)),
                     ("horizons", horizon_comparison())):
        print(name, df.shape)

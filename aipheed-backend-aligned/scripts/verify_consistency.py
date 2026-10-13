"""
scripts/verify_consistency.py
------------------------------
End-to-end consistency check across the pipeline, the API and the PDF report.

Every figure the system shows a reviewer should trace back to one computation.
This script asserts that it does: that the metrics in `training_results.json`
are the ones the dashboard serves and the ones the PDF prints, that the label
and feature matrix agree on the approved window, and that the model bundle,
the SHAP explainer and the disaggregator all operate on the same feature set.

It reads; it never writes and never retrains. Run it after a pipeline cycle.

    python -m scripts.verify_consistency
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROC = Path("data/processed")
CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(ok), detail))


def main() -> int:
    # ── 1. Approved window and grid ──────────────────────────────────────
    from app.ml.features.feature_matrix import MODEL_QUARTERS

    feats = pd.read_parquet(PROC / "features_fused.parquet")
    check("Window is 2020-Q1 .. 2025-Q4 (24 quarters)",
          (MODEL_QUARTERS[0], MODEL_QUARTERS[-1], len(MODEL_QUARTERS))
          == ("2020-Q1", "2025-Q4", 24),
          f"{MODEL_QUARTERS[0]}..{MODEL_QUARTERS[-1]} ({len(MODEL_QUARTERS)})")
    check("Feature matrix is the 120-row backbone",
          len(feats) == 120 and feats["province_code"].nunique() == 5,
          f"{len(feats)} rows, {feats['province_code'].nunique()} provinces")
    # Section 3.3.2.6's 45 candidates plus cpi_dev, Equation 5's CPI_dev built
    # as its legend defines it (deviation from the province's rolling mean).
    check("Feature matrix has 45 candidate columns + cpi_dev",
          len(feats.columns) - 2 == 46 and "cpi_dev" in feats.columns,
          f"{len(feats.columns) - 2} columns")

    # Rule 3: CPI_dev's rolling mean may use only earlier quarters. Recompute it
    # from food_cpi_yoy with the current and later quarters excluded and compare.
    from app.ml.features.feature_matrix import CPI_DEV_WINDOW
    fm = feats.sort_values(["province_code", "quarter"])
    prior = fm.groupby("province_code")["food_cpi_yoy"].transform(
        lambda x: x.shift(1).rolling(CPI_DEV_WINDOW, min_periods=2).mean())
    expect = (fm["food_cpi_yoy"] - prior).fillna(0.0)
    check("CPI_dev uses only earlier quarters of the same province (Rule 3)",
          bool(((fm["cpi_dev"] - expect).abs() < 1e-9).all()),
          f"window {CPI_DEV_WINDOW} prior quarters")
    # Every feature column, not just the numeric ones: an all-None column of
    # dtype object escapes select_dtypes("number") and reads as clean.
    feat_cols = [c for c in feats.columns if c not in ("province_code", "quarter")]
    nan_cols = {c: int(feats[c].isna().sum())
                for c in feat_cols if feats[c].isna().any()}
    check("No NaN left in any feature column (Section 3.3.2.6 fill rule)",
          not nan_cols, ", ".join(f"{c}={n}" for c, n in nan_cols.items()) or "none")
    non_numeric = {c: str(feats[c].dtype) for c in feat_cols
                   if not pd.api.types.is_numeric_dtype(feats[c])}
    check("Every feature column is numeric",
          not non_numeric,
          ", ".join(f"{c}:{t}" for c, t in non_numeric.items()) or "all numeric")
    dead = [c for c in feat_cols
            if pd.api.types.is_numeric_dtype(feats[c]) and feats[c].nunique() <= 1]

    # A constant column usually means a broken source -- that is how the empty
    # `rainfall_anomaly_pct` was caught. A trigger proportion is different: it
    # can be constant because the corpus contains no evidence of that driver,
    # which is a finding rather than a fault. The two are separated by asking
    # the corpus directly whether any article matches the category's keywords.
    unevidenced: list[str] = []
    try:
        from app.ml.nlp.trigger_classifier import TRIGGER_KEYWORDS, classify_triggers

        corpus = pd.read_parquet(PROC / "corpus_geocoded.parquet")
        corpus = corpus[corpus["province_code"].notna()]
        blob = (corpus["title"].fillna("") + " " + corpus["summary"].fillna("")).astype(str)
        fired = set()
        for t in blob:
            fired.update(classify_triggers(t))
        for col in list(dead):
            cat = col[len("trigger_"):] if col.startswith("trigger_") else None
            if cat in TRIGGER_KEYWORDS and cat not in fired:
                dead.remove(col)
                unevidenced.append(col)
    except Exception as exc:  # the corpus may be absent in a fresh clone
        logger_note = f" (trigger provenance not checked: {exc})"
    else:
        logger_note = ""

    check("No feature column is constant because its source is broken",
          not dead, (", ".join(dead) or "none") + logger_note)
    if unevidenced:
        check("Constant trigger columns are unevidenced in the corpus, not broken",
              True,
              ", ".join(unevidenced) + " — no article matches these keywords, so "
              "the driver is absent from the corpus rather than mis-extracted")

    # ── 2. Label ─────────────────────────────────────────────────────────
    labels = pd.read_parquet(PROC / "labels.parquet")
    pos = labels["label_stress"].mean()
    check("Label is balanced by the median threshold",
          0.45 <= pos <= 0.55, f"positive rate {pos:.3f} over {len(labels)} rows")
    check("Every labelled row is inside the approved window",
          labels["quarter"].isin(MODEL_QUARTERS).all())
    check("SWS hunger is not a feature (would be label leakage)",
          "pct_total_hunger" not in feats.columns)

    # ── 3. Selected feature set ──────────────────────────────────────────
    from app.ml.features.feature_selector import (
        EQUATION5_FEATURES, MAX_FEATURES, MIN_FEATURES, load_selected,
        model_features,
    )  # noqa: F401

    # Two different lists, deliberately. `selected` is what the Section 3.3.2.7
    # process retained on this data — the audit trail. `selected` is NOT what
    # the model trains on; Equation 5's vector is. See feature_selector.
    selected = load_selected()
    model_cols = model_features()

    check("Process retained a set within the approved floor/ceiling",
          MIN_FEATURES <= len(selected) <= MAX_FEATURES,
          f"{len(selected)} features (floor {MIN_FEATURES}, ceiling {MAX_FEATURES})")
    check("Model trains on Equation 5's vector",
          sorted(model_cols) == sorted(EQUATION5_FEATURES),
          f"{len(model_cols)} features")
    check("Every model feature exists in the matrix",
          all(c in feats.columns for c in model_cols),
          ", ".join(c for c in model_cols if c not in feats.columns) or "all present")

    # ── 3b. Rule 3 — No Look-Ahead Bias ──────────────────────────────────
    # "All features will derive exclusively from data available before the
    # forecast period." Two things can break this: a value back-filled from a
    # later quarter, and a feature built from the target's own future.
    prov_path = PROC / "feature_provenance.json"
    if prov_path.exists():
        prov = json.loads(prov_path.read_text()).get("imputed", {})
        backfilled = {c: v for c, v in prov.items()
                      if v.get("back_filled") or v.get("bfill")}
        check("No feature cell was back-filled from a later quarter",
              not backfilled, ", ".join(backfilled) or "none")

    lagged_label = [c for c in model_cols
                    if c.startswith("label_") or "quarters_since" in c]
    check("No lagged-label feature is in the model",
          not lagged_label, ", ".join(lagged_label) or "none")
    check("The label's SWS term is not a feature",
          not any(c in model_cols for c in
                  ("pct_total_hunger", "sws_hunger_pct", "stress_score")))

    # A feature that is constant within every quarter carries no cross-province
    # information; that is a known property of this label's design, not a fault,
    # but it is worth surfacing rather than leaving implicit.
    const_in_quarter = [
        c for c in model_cols
        if feats.groupby("quarter")[c].nunique(dropna=False).max() == 1
    ]
    check("Cross-province variation exists in at least one feature",
          len(const_in_quarter) < len(model_cols),
          f"{len(const_in_quarter)}/{len(model_cols)} are quarter-constant")

    # ── 4. Model bundle ──────────────────────────────────────────────────
    model_path = Path("models/lgbm_best.pkl")
    if not model_path.exists():
        check("Production model exists", False,
              "models/lgbm_best.pkl absent — run trainer.train_model()")
        return report()

    import joblib

    bundle = joblib.load(model_path)
    check("Model bundle carries its feature list and horizon",
          isinstance(bundle, dict)
          and "feature_cols" in bundle and "max_reliable_lead_time" in bundle)
    bundle_cols = list(bundle.get("feature_cols", []))
    check("Model bundle matches Equation 5's vector",
          sorted(bundle_cols) == sorted(model_cols),
          f"bundle {len(bundle_cols)} vs Equation 5 {len(model_cols)}")

    # A fit that found no split is not a model: it returns a constant 0.5 for
    # every row, and on a holdout whose majority class is 90% that scores an
    # accuracy of 0.9000 and a weighted F1 of 0.8526 while AUC-ROC is exactly
    # 0.5000. Algorithm 4's objective rewards it, so it has to be checked for
    # rather than assumed against. See PROPOSAL_CONFORMANCE 1.30.
    splits = int(bundle["model"].booster_.feature_importance("split").sum())
    check("Production model actually learned (has splits, is not constant)",
          splits > 0,
          f"{splits} splits across {bundle['model'].booster_.num_trees()} trees")

    # ── 5. Training results ↔ dashboard ↔ PDF ────────────────────────────
    results_path = PROC / "training_results.json"
    if not results_path.exists():
        check("training_results.json exists", False, "run the pipeline")
        return report()
    results = json.loads(results_path.read_text())

    # The API and the PDF both read training_results.json, so comparing them
    # only to each other passes even when that file describes a previous run.
    # Anchor it to the model actually on disk: the bundle and the results file
    # are written by the same call, so a mismatch means one of them is stale.
    check("training_results.json describes the model on disk (feature list)",
          list(results.get("feature_cols", [])) == bundle_cols,
          f"results {len(results.get('feature_cols', []))} vs bundle {len(bundle_cols)}")
    check("training_results.json describes the model on disk (hyperparameters)",
          results.get("best_params") == bundle.get("best_params"),
          "match" if results.get("best_params") == bundle.get("best_params")
          else "STALE — rerun training or the pipeline")
    check("training_results.json describes the model on disk (horizon)",
          results.get("max_reliable_lead_time") == bundle.get("max_reliable_lead_time"),
          f"{results.get('max_reliable_lead_time')} vs {bundle.get('max_reliable_lead_time')}")

    from app.services import dashboard as svc

    svc.model_performance.cache_clear()
    perf = svc.model_performance()

    pairs = [
        ("accuracy", "holdout_accuracy"),
        ("precision", "holdout_precision"),
        ("recall", "holdout_recall"),
        ("f1", "holdout_f1"),
        ("rocAuc", "holdout_roc_auc"),
    ]
    for api_key, res_key in pairs:
        a, b = perf.get(api_key), results.get(res_key)
        same = (a is None and b is None) or (
            a is not None and b is not None and abs(a - b) < 1e-9)
        check(f"API {api_key} == training_results {res_key}", same, f"{a} vs {b}")

    check("API horizon == the model bundle's horizon",
          perf.get("maxReliableLeadTime") == bundle.get("max_reliable_lead_time"),
          f"{perf.get('maxReliableLeadTime')} vs {bundle.get('max_reliable_lead_time')}")

    # The PDF reads the same function, so it cannot diverge; assert the path.
    import inspect

    from app.services import report as rep

    src = inspect.getsource(rep)
    check("PDF report reads model_performance() rather than its own copy",
          "svc.model_performance()" in src)

    # ── 6. Serving layer ─────────────────────────────────────────────────
    from app.ml.inference.predictor import Predictor

    pred = Predictor()
    quarters = pred.available_quarters()
    fc = pred.forecast_quarter(quarters[-1])
    check("Predictor returns the five CALABARZON provinces",
          len(fc) == 5, f"{len(fc)} rows for {quarters[-1]}")
    check("Every forecast carries Rule 6 labelling",
          all(f.get("horizon_label") and f.get("confidence_statement")
              and f.get("verification_date") for f in fc))
    check("Every forecast carries a data sufficiency flag (Rule 5)",
          all(f.get("data_sufficiency_flag") in ("OK", "LIMITED_SIGNAL") for f in fc))

    from app.ml.inference.disaggregator import Disaggregator

    mun = Disaggregator().disaggregate(fc, quarters[-1])
    check("Disaggregation covers 142 LGUs", len(mun) == 142, f"{len(mun)} rows")
    check("Every municipal row is labelled (Rule 8)",
          mun["disaggregation_label"].notna().all())

    from app.ml.inference.explainer import Explainer

    ex = Explainer()
    recs = ex.explain_province_quarter(fc[0]["province_code"], quarters[-1])
    check("SHAP explains exactly the model's feature set",
          sorted({r["feature_name"] for r in recs}) == sorted(model_cols),
          f"{len(recs)} records")
    if recs:
        served = fc[0]["risk_probability"]
        rebuilt = recs[0]["final_rfii"]
        check("Equation 7 reproduces the served probability",
              abs(served - rebuilt) < 0.02, f"served {served} vs phi0+sum {rebuilt}")

    # Section 1.2 ranking: the served order is the model's probability order.
    from app.services import dashboard as svc
    rank_ok, n_q = True, 0
    for q in quarters:
        rows = [r for r in svc.province_summary(q) if r.get("rank") is not None]
        rows.sort(key=lambda r: r["rank"])
        probs = [r["riskScore"] for r in rows]
        rank_ok &= all(a >= b for a, b in zip(probs, probs[1:]))
        n_q += 1
    check("Served rank follows the model probability in every quarter", rank_ok,
          f"{n_q} quarters")

    return report()


def report() -> int:
    width = max(len(n) for n, _, _ in CHECKS) + 2
    print("\n" + "=" * (width + 30))
    print("CONSISTENCY CHECK")
    print("=" * (width + 30))
    failed = 0
    for name, ok, detail in CHECKS:
        if not ok:
            failed += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<{width}} {detail}")
    print("=" * (width + 30))
    print(f"{len(CHECKS) - failed}/{len(CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

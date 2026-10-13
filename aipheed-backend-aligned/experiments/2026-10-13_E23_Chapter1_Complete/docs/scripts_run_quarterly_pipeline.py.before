"""
scripts/run_quarterly_pipeline.py
----------------------------------
The aiPHeed quarterly pipeline, in the order Figure 3.6.2 lays out.

Two independent data tracks are collected and converge into one predictive
pipeline:

  Government Data Track
      PSA, BSP, DOE, PAGASA, PhilRice and SWS are read; indicators are cleaned,
      aligned to a common quarterly reference period, and structured into a
      province-quarter feature set (Sections 3.3.1.2 and 3.3.2.5).

  News Data Track
      Filipino-English articles are fetched from RSS feeds, Google News RSS and
      GDELT; HTML is stripped, the title and summary concatenated and truncated
      to 512 characters; a language filter retains only Filipino and English
      articles; each is geocoded to a CALABARZON province by three-stage PSGC
      matching; unmatched articles are discarded; spatial bias weights are
      computed and province-quarters below five articles are flagged
      LIMITED_SIGNAL; articles are scored by XLM-RoBERTa against the ten
      bilingual HungerGist hypotheses and those below 0.30 are excluded; the
      FSSI is computed with its lags and acceleration; and each article is
      classified into the five trigger categories
      (Sections 3.3.2.1 through 3.3.2.4, Algorithms 1 and 2).

  Combined Pipeline
      The two feature sets fuse into one matrix; the composite stress label is
      generated; the Section 3.3.2.7 selection reduces the candidate pool;
      LightGBM is retrained and the Maximum Reliable Lead Time rediscovered
      (Algorithms 3 and 4); province probabilities are produced at that
      horizon; SHAP values are computed (Equation 7); province estimates are
      disaggregated to the 142 cities and municipalities (Algorithm 5); and any
      province breaching its rolling alert threshold is staged (Rule 7).

Nothing here publishes. Every forecast and alert is STAGED for mandatory review
by a DA IV-A or DEPDev IV-A administrator, per Figure 3.6.3.

Usage:
    python -m scripts.run_quarterly_pipeline                # full cycle
    python -m scripts.run_quarterly_pipeline --skip-collect # reuse raw data
    python -m scripts.run_quarterly_pipeline --skip-train   # reuse the model
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("aipheed.pipeline")

SUMMARY_PATH = Path("data/processed/pipeline_run.json")
TRAINING_RESULTS_PATH = Path("data/processed/training_results.json")


def _stage(n: int, title: str) -> None:
    logger.info("=" * 70)
    logger.info("STAGE %d — %s", n, title)
    logger.info("=" * 70)


def run_pipeline(
    skip_collect: bool = False,
    skip_train: bool = False,
    quarter: str | None = None,
) -> dict:
    """Run one quarterly cycle and return a summary dict."""
    started = datetime.now(timezone.utc)
    summary: dict = {"started_at": started.isoformat()}

    # ── Stage 1: collection ──────────────────────────────────────────────
    if skip_collect:
        logger.info("Stage 1 skipped (--skip-collect): reusing collected data.")
    else:
        _stage(1, "Data collection — news track and government track")
        from scripts.refresh_all_sources import main as refresh_sources

        refresh_sources()

    # ── Stage 2: NLP track ───────────────────────────────────────────────
    _stage(2, "NLP track — geocoding, bias weights, scoring, FSSI, triggers")
    import pandas as pd

    from app.ml.corpus.bias_weighter import compute_bias_weights
    from app.ml.corpus.language_filter import filter_in_scope
    from app.ml.features.fssi_builder import compute_fssi
    from app.ml.nlp.sentiment import score_articles_df
    from app.ml.nlp.trigger_classifier import classify_triggers_df, compute_trigger_proportions

    # The NLP track reads the curated corpus when one has been built, and the
    # full collection otherwise. Algorithm 1 scores every collected article, but
    # its 0.30 retention admits items with no bearing on food insecurity, and
    # the Index built from the full retention correlates -0.339 with SWS hunger
    # -- against the quantity it tracks. Built from the curated subset it
    # correlates +0.347. The cost is coverage: 21 of 120 province-quarters carry
    # a value and Rule 5 flags 119 of 120. See PROPOSAL_CONFORMANCE.md 1.36 and
    # scripts/build_curated_corpus.py.
    curated_path = Path("data/processed/corpus_curated.parquet")
    corpus_path = (curated_path if curated_path.exists()
                   else Path("data/processed/corpus_geocoded.parquet"))
    logger.info("NLP track corpus: %s", corpus_path)
    corpus = pd.read_parquet(corpus_path)
    summary["articles_collected"] = int(len(corpus))

    # Figure 3.6.2: retain only Filipino and English articles. The collection
    # queries already constrain language (GDELT sourcelang, Philippine outlets,
    # English and Tagalog query sets), so this is a backstop; what it removes is
    # recorded rather than assumed to be nothing.
    corpus, out_of_scope = filter_in_scope(corpus)
    summary["articles_out_of_scope_language"] = int(len(out_of_scope))

    summary["articles_geocoded"] = int(corpus["province_code"].notna().sum())

    # Figure 3.6.2: articles that match no province are discarded, and matched
    # articles are scored. Only matched articles still lacking a score are sent
    # through XLM-RoBERTa; re-scoring the whole collection whenever one score
    # was missing cost hours and changed nothing the FSSI uses.
    if "food_insecurity_score" not in corpus.columns:
        corpus["food_insecurity_score"] = pd.NA
    todo = corpus["province_code"].notna() & corpus["food_insecurity_score"].isna()
    summary["articles_scored_this_run"] = int(todo.sum())
    if todo.any():
        scored = score_articles_df(corpus.loc[todo].copy())
        for col in scored.columns:
            if col not in corpus.columns:
                corpus[col] = pd.NA
            corpus.loc[todo, col] = scored[col].values
        corpus.to_parquet(corpus_path, index=False)

    weights = compute_bias_weights(corpus)
    summary["limited_signal_cells"] = int(
        (weights["data_sufficiency"] == "LIMITED_SIGNAL").sum()
    )

    fssi = compute_fssi(corpus, weights)
    summary["fssi_rows"] = int(len(fssi))

    # Algorithm 2: every geocoded article is matched against the bilingual
    # regex patterns before proportions are taken. This call was missing, so
    # compute_trigger_proportions found no trigger columns, filled them with
    # zeros, and all five trigger features reached the model as constants.
    triggers = compute_trigger_proportions(classify_triggers_df(corpus))
    summary["trigger_rows"] = int(len(triggers))

    # ── Stage 3: fusion and labelling ────────────────────────────────────
    _stage(3, "Feature matrix fusion and composite stress label")
    from app.ml.features.feature_matrix import build_feature_matrix
    from app.ml.features.label_generator import generate_labels

    features = build_feature_matrix()
    summary["feature_matrix_shape"] = list(features.shape)

    labels = generate_labels()
    summary["labelled_rows"] = int(len(labels))
    summary["labelled_quarters"] = sorted(labels["quarter"].unique().tolist())

    # ── Stage 4: feature selection (Section 3.3.2.7) ─────────────────────
    _stage(4, "Two-stage feature selection")
    from app.ml.features.feature_selector import select_features

    try:
        selection = select_features()
        summary["n_candidates"] = selection["n_candidates"]
        summary["n_selected"] = selection["n_selected"]
        summary["selected_features"] = selection["selected_features"]
    except Exception as exc:
        logger.error(
            "Feature selection could not run on the current data (%s). Training "
            "will fall back to the feature set the proposal reports.", exc,
        )
        summary["feature_selection_error"] = str(exc)

    # ── Stage 5: training (Algorithms 3 and 4) ───────────────────────────
    if skip_train:
        logger.info("Stage 5 skipped (--skip-train): reusing models/lgbm_best.pkl.")
        results = (
            json.loads(TRAINING_RESULTS_PATH.read_text())
            if TRAINING_RESULTS_PATH.exists() else {}
        )
    else:
        _stage(5, "LightGBM training — lead time discovery and Optuna TPE")
        from app.ml.training.trainer import train_model

        results = train_model()
        TRAINING_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        TRAINING_RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str))

    summary["max_reliable_lead_time"] = results.get("max_reliable_lead_time")
    summary["holdout_f1"] = results.get("holdout_f1")
    summary["holdout_roc_auc"] = results.get("holdout_roc_auc")

    # ── Stage 6: baselines (RQ3 / Objective 4) ───────────────────────────
    if not skip_train and results:
        _stage(6, "Baseline comparison")
        from app.ml.training.evaluator import run_baseline_evaluation

        try:
            summary["baselines"] = run_baseline_evaluation(
                forecast_gap=results.get("max_reliable_lead_time", 0),
                best_params=results.get("best_params"),
            )
        except Exception as exc:
            logger.error("Baseline evaluation could not run (%s).", exc)
            summary["baseline_error"] = str(exc)

    # ── Stage 7: inference, SHAP, disaggregation, alerts ─────────────────
    _stage(7, "Forecast, SHAP attribution, spatial disaggregation, alerts")
    from app.ml.inference.disaggregator import Disaggregator
    from app.ml.inference.explainer import Explainer
    from app.ml.inference.predictor import Predictor

    predictor = Predictor()
    target_quarter = quarter or predictor.available_quarters()[-1]
    summary["quarter"] = target_quarter

    forecasts = predictor.forecast_quarter(target_quarter)
    summary["forecasts_staged"] = len(forecasts)
    summary["forecast_horizon_quarters"] = predictor.lead_time

    shap_records = Explainer().explain_quarter(target_quarter)
    summary["shap_records"] = len(shap_records)

    municipal = Disaggregator().disaggregate(forecasts, target_quarter)
    summary["municipal_rows"] = int(len(municipal))

    prev_quarters = [q for q in predictor.available_quarters() if q < target_quarter]
    prev = predictor.forecast_quarter(prev_quarters[-1]) if prev_quarters else []
    alerts = predictor.detect_alerts(forecasts, prev_forecasts=prev)
    summary["alerts_staged"] = len(alerts)

    # ── Done ─────────────────────────────────────────────────────────────
    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    summary["duration_seconds"] = round(
        (datetime.now(timezone.utc) - started).total_seconds(), 1
    )
    summary["published"] = False
    summary["review_note"] = (
        "All outputs are STAGED. A DA IV-A or DEPDev IV-A administrator must "
        "confirm each forecast and each alert before it appears publicly."
    )

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    logger.info("Pipeline summary written -> %s", SUMMARY_PATH)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the aiPHeed quarterly pipeline.")
    ap.add_argument("--skip-collect", action="store_true",
                    help="Reuse already-collected raw data.")
    ap.add_argument("--skip-train", action="store_true",
                    help="Reuse models/lgbm_best.pkl instead of retraining.")
    ap.add_argument("--quarter", default=None,
                    help="Quarter to forecast (default: the latest scoreable).")
    args = ap.parse_args()

    summary = run_pipeline(
        skip_collect=args.skip_collect,
        skip_train=args.skip_train,
        quarter=args.quarter,
    )
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

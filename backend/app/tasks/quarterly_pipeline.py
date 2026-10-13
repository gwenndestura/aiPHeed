"""
app/tasks/quarterly_pipeline.py
--------------------------------
The quarterly self-update (Chapter III, Rule 1), as one unattended run.

Stages, in order:

  1. government    PSA OpenStat food CPI + unemployment, PSA wholesale rice.
                   Upserted into the existing parquets, so a failed or partial
                   pull can never delete quarters that were already stored.
  2. news          Google News RSS + Philippine RSS for the last completed
                   quarter. New articles are deduplicated, geocoded, scored
                   with XLM-RoBERTa (Algorithm 1) and appended to the corpus.
                   Relevant CALABARZON articles not yet in the audited dataset
                   are written to an awaiting-review list. They do NOT enter the
                   FSSI until a reviewer has read them: the audited dataset's
                   rule is "nothing enters without having been read".
  3. nlp_features  Bias weights, trigger proportions and FSSI rebuilt from the
                   audited dataset (scripts/rebuild_fssi_chain.py).
  4. panel         Province-quarter panel through the last completed quarter
                   (scripts/build_thesis_panel.py).
  5. retrain       Three-way blend retrained into a CANDIDATE file
                   (scripts/train_thesis_blend.py), validated, and promoted to
                   the served path only if it is structurally sound and meets
                   the Algorithm 4 targets (Section 3.4.4: a configuration that
                   misses them is not published). The previous model is
                   archived before it is replaced.

Stages 1-3 are "soft": a source outage logs a warning and the run continues on
the data already stored. Stages 4-5 are "hard": if the panel cannot be built,
nothing is retrained, and the served model is never touched by a failed run.

Publishing (reloading the served model and staging the new quarter for DA
review) happens in the API process, in app/tasks/scheduler.py, because only
that process holds the caches to reload.

Every run writes data/pipeline_runs/<run_id>.json and latest.json.

CLI (what the scheduler calls):
    python -m app.tasks.quarterly_pipeline --trigger scheduled
    python -m app.tasks.quarterly_pipeline --skip news --no-promote
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]          # backend/
PROCESSED = ROOT / "data" / "processed"
RUNS_DIR = ROOT / "data" / "pipeline_runs"
LOCK_PATH = RUNS_DIR / ".lock"
SERVED_MODEL = ROOT / "models" / "thesis_food_insecurity_model.joblib"
CANDIDATE_DIR = ROOT / "models" / "candidates"
ARCHIVE_DIR = ROOT / "models" / "archive"
PANEL_PATH = ROOT / "data" / "thesis" / "panel.parquet"
AWAITING_REVIEW = PROCESSED / "audit_review" / "_awaiting_review_pipeline.csv"
AUDITED_DATASET = PROCESSED / "calabarzon_food_insecurity_dataset.parquet"
CORPUS = PROCESSED / "corpus_geocoded.parquet"

STAGES = ("government", "news", "nlp_features", "panel", "retrain")
HARD_STAGES = {"panel", "retrain"}

REQUIRED_BUNDLE_KEYS = (
    "lgbm_model", "lr_model", "lr_scaler", "weak_model", "weak_scaler",
    "lgbm_feature_cols", "lr_feature_cols", "weak_feature_cols",
    "blend_weight_lgbm", "blend_weight_lr", "blend_weight_weak",
    "threshold", "holdout_metrics", "walk_forward_metrics", "trained_through",
)

log = logging.getLogger("quarterly_pipeline")


class PipelineBusy(Exception):
    """Another run holds the lock."""


class StageFailed(Exception):
    pass


# ---------------------------------------------------------------------------
# Run record
# ---------------------------------------------------------------------------

@dataclass
class StageResult:
    name: str
    status: str               # ok | warning | failed | skipped
    detail: str = ""
    seconds: float = 0.0


@dataclass
class RunRecord:
    run_id: str
    trigger: str
    started_at: str
    finished_at: str | None = None
    status: str = "running"   # running | succeeded | completed_with_warnings | failed
    stages: list[StageResult] = field(default_factory=list)
    model_promoted: bool = False
    trained_through: str | None = None

    def save(self) -> None:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(asdict(self), indent=2, default=str)
        (RUNS_DIR / f"{self.run_id}.json").write_text(payload, encoding="utf-8")
        (RUNS_DIR / "latest.json").write_text(payload, encoding="utf-8")


def load_latest_run() -> dict | None:
    path = RUNS_DIR / "latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------------------
# Lock: one run at a time, across processes (uvicorn workers, a manual CLI run)
# ---------------------------------------------------------------------------

def _acquire_lock(stale_after: float) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists() and time.time() - LOCK_PATH.stat().st_mtime > stale_after:
        log.warning("removing stale pipeline lock (older than %.0fs)", stale_after)
        LOCK_PATH.unlink(missing_ok=True)
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise PipelineBusy("A quarterly pipeline run is already in progress.") from exc
    with os.fdopen(fd, "w") as fh:
        fh.write(str(os.getpid()))


def _release_lock() -> None:
    LOCK_PATH.unlink(missing_ok=True)


def is_running() -> bool:
    return LOCK_PATH.exists()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_completed_quarter_bounds(today: date | None = None) -> tuple[str, str, str]:
    from app.ml.features.feature_matrix import last_completed_quarter
    q = last_completed_quarter(today)
    year, n = int(q[:4]), int(q[-1])
    start = date(year, 3 * (n - 1) + 1, 1)
    end = (date(year + 1, 1, 1) if n == 4 else date(year, 3 * n + 1, 1))
    end = date.fromordinal(end.toordinal() - 1)
    return q, start.isoformat(), end.isoformat()


def _upsert_parquet(path: Path, new: pd.DataFrame, keys: list[str]) -> str:
    """
    Merge a fresh pull into a stored table.

    A fresh non-missing value wins (PSA revises figures), but a value missing
    from the fresh pull never erases a stored one (a table that 404s returns an
    empty column), and stored rows the pull did not return are kept.
    """
    if new is None or new.empty:
        raise StageFailed(f"{path.name}: source returned no rows")
    if path.exists():
        old = pd.read_parquet(path)
        shutil.copy2(path, path.with_suffix(".pre_pipeline.parquet"))
        new = new.drop_duplicates(subset=keys, keep="last").set_index(keys)
        merged = new.combine_first(old.drop_duplicates(subset=keys, keep="last").set_index(keys))
        merged = merged.reset_index()[list(old.columns)]
    else:
        merged = new
    merged = merged.sort_values(keys).reset_index(drop=True)
    merged.to_parquet(path, index=False)
    return f"{path.name}: {len(merged)} rows, through {merged['quarter'].max()}"


def _run_script(args: list[str], timeout: float) -> str:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    proc = subprocess.run([sys.executable, *args], cwd=ROOT, env=env, timeout=timeout,
                          capture_output=True, text=True)
    tail = (proc.stdout or "").strip().splitlines()[-3:]
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()[-3:]
        raise StageFailed(f"{args[0]} exited {proc.returncode}: {' | '.join(err or tail)}")
    return " | ".join(tail)


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

def stage_government(ctx: dict) -> str:
    from app.ml.corpus.openstat_fetcher import fetch_openstat_indicators
    from app.ml.corpus.psa_rice_fetcher import fetch_psa_rice_prices

    today = date.today().isoformat()
    psa = fetch_openstat_indicators("2020-01-01", today, save_path=None)
    a = _upsert_parquet(PROCESSED / "psa_indicators.parquet", psa,
                        ["province_code", "quarter"])
    rice = fetch_psa_rice_prices(start_year=2021)
    b = _upsert_parquet(PROCESSED / "psa_rice_prices.parquet", rice,
                        ["province_code", "quarter", "rice_class"])
    return f"{a}; {b}"


def stage_news(ctx: dict) -> str:
    """
    Runs collect_news() in its own process under a time budget.

    Google News answers sustained querying with 429/503 and the fetcher backs
    off for up to ten minutes at a time, so an unbounded fetch could consume
    the whole run and starve the retrain. On timeout the stage warns and the
    run continues on the corpus already stored.
    """
    from app.config import settings
    try:
        return _run_script(["-m", "app.tasks.quarterly_pipeline", "--news-only"],
                           settings.PIPELINE_NEWS_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise StageFailed(f"news collection exceeded its {exc.timeout:.0f}s budget "
                          "(source throttling); continuing on the stored corpus") from exc


def collect_news() -> str:
    from app.ml.corpus.geocoder import PROVINCE_PSGC, geocode_to_province
    from app.ml.corpus.gnews_rss_fetcher import fetch_gnews_rss_articles
    from app.ml.corpus.rss_fetcher import FEED_URLS, fetch_rss_articles
    from app.ml.nlp.classifier import load_classifier, score_article

    quarter, start, end = _last_completed_quarter_bounds()
    fetched: list[dict] = []
    errors: list[str] = []
    for name, fn in (("gnews", lambda: fetch_gnews_rss_articles(start, end)),
                     ("rss", lambda: fetch_rss_articles(FEED_URLS, start, end))):
        try:
            fetched.extend(fn())
        except Exception as exc:  # one source down must not cancel the other
            errors.append(f"{name}: {exc}")
    if not fetched:
        raise StageFailed(f"no articles fetched for {quarter} ({'; '.join(errors) or 'empty'})")

    corpus = pd.read_parquet(CORPUS)
    seen_ids = set(corpus["article_id"].dropna())
    seen_links = set(corpus["link"].dropna())
    new = pd.DataFrame(fetched).drop_duplicates(subset=["article_id"])
    new = new[~new["article_id"].isin(seen_ids) & ~new["link"].isin(seen_links)]
    if new.empty:
        return f"{quarter}: {len(fetched)} fetched, 0 new"

    names = {code: name for name, code in PROVINCE_PSGC.items()}
    clf = load_classifier()
    rows = []
    for rec in new.to_dict("records"):
        title, summary = rec.get("title") or "", rec.get("summary") or ""
        scored = score_article(clf, title, summary)
        code = geocode_to_province(f"{title} {summary}")
        published = pd.to_datetime(rec.get("published"), errors="coerce", utc=True)
        rows.append({
            **{k: rec.get(k) for k in ("title", "link", "article_id", "summary",
                                         "source_domain", "fetcher_source")},
            "published": published.strftime("%Y-%m-%d") if pd.notna(published) else None,
            "quarter": (f"{published.year}-Q{(published.month - 1) // 3 + 1}"
                        if pd.notna(published) else None),
            "food_insecurity_score": scored.get("food_insecurity_score"),
            "is_relevant": bool(scored.get("is_relevant")),
            "top_hypothesis": scored.get("top_hypothesis"),
            "top_topic_name": scored.get("top_topic_name"),
            "noncore_max": scored.get("noncore_max"),
            "relevance_margin": scored.get("relevance_margin"),
            "province_code": code,
            "province_name": names.get(code),
            "match_level": "province" if code else "none",
        })
    added = pd.DataFrame(rows)

    shutil.copy2(CORPUS, CORPUS.with_suffix(".pre_pipeline.parquet"))
    combined = pd.concat([corpus, added.reindex(columns=corpus.columns)], ignore_index=True)
    combined.to_parquet(CORPUS, index=False)

    audited = (set(pd.read_parquet(AUDITED_DATASET, columns=["article_id"])["article_id"])
               if AUDITED_DATASET.exists() else set())
    queue = added[added["is_relevant"] & added["province_code"].notna()
                  & ~added["article_id"].isin(audited)]
    AWAITING_REVIEW.parent.mkdir(parents=True, exist_ok=True)
    if AWAITING_REVIEW.exists():
        queue = pd.concat([pd.read_csv(AWAITING_REVIEW), queue], ignore_index=True)
        queue = queue.drop_duplicates(subset=["article_id"], keep="first")
    queue.to_csv(AWAITING_REVIEW, index=False)

    note = f"; source errors: {'; '.join(errors)}" if errors else ""
    return (f"{quarter}: {len(added)} new articles, "
            f"{int(added['is_relevant'].sum())} relevant, "
            f"{len(queue)} awaiting review{note}")


def stage_nlp_features(ctx: dict) -> str:
    return _run_script(["scripts/rebuild_fssi_chain.py"], ctx["timeout"])


def stage_panel(ctx: dict) -> str:
    out = _run_script(["scripts/build_thesis_panel.py"], ctx["timeout"])
    panel = pd.read_parquet(PANEL_PATH)
    ctx["panel_through"] = panel["quarter"].max()
    return f"{len(panel)} rows through {ctx['panel_through']} ({out})"


def validate_bundle(path: Path, panel_path: Path = PANEL_PATH) -> dict:
    """Load a candidate exactly the way ThesisPredictor will and score the panel."""
    import joblib
    import numpy as np

    bundle = joblib.load(path)
    missing = [k for k in REQUIRED_BUNDLE_KEYS if k not in bundle]
    if missing:
        raise StageFailed(f"candidate is missing {missing}")
    thr = float(bundle["threshold"])
    if not 0.0 < thr < 1.0:
        raise StageFailed(f"candidate threshold {thr} outside (0, 1)")
    booster = bundle["lgbm_model"].booster_
    n_splits = sum(t["num_leaves"] - 1 for t in booster.dump_model()["tree_info"])
    if n_splits == 0:
        raise StageFailed("candidate LightGBM has zero splits (a constant predictor)")

    panel = pd.read_parquet(panel_path)
    p = bundle["blend_weight_lgbm"] * bundle["lgbm_model"].predict_proba(
        panel[bundle["lgbm_feature_cols"]])[:, 1]
    p += bundle["blend_weight_lr"] * bundle["lr_model"].predict_proba(
        bundle["lr_scaler"].transform(panel[bundle["lr_feature_cols"]].fillna(0.0)))[:, 1]
    p += bundle["blend_weight_weak"] * bundle["weak_model"].predict_proba(
        bundle["weak_scaler"].transform(panel[bundle["weak_feature_cols"]].fillna(0.0)))[:, 1]
    if not np.all(np.isfinite(p)) or p.min() < 0 or p.max() > 1:
        raise StageFailed("candidate produced non-finite or out-of-range scores")
    return bundle


def promote(candidate: Path, served: Path = SERVED_MODEL,
            archive_dir: Path = ARCHIVE_DIR) -> Path | None:
    """Archive the served model, then atomically swap the candidate in."""
    archived = None
    if served.exists():
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archived = archive_dir / f"{served.stem}.{stamp}{served.suffix}"
        shutil.copy2(served, archived)
    tmp = served.with_suffix(".incoming")
    shutil.copy2(candidate, tmp)
    os.replace(tmp, served)
    return archived


def stage_retrain(ctx: dict) -> str:
    candidate = CANDIDATE_DIR / f"thesis_food_insecurity_model.{ctx['run_id']}.joblib"
    _run_script(["scripts/train_thesis_blend.py", "--out", str(candidate),
                 "--trials", str(ctx["trials"])], ctx["timeout"])
    bundle = validate_bundle(candidate)
    ctx["trained_through"] = bundle["trained_through"]
    hm = bundle["holdout_metrics"]
    summary = (f"candidate through {bundle['trained_through']}: holdout F1 "
               f"{hm['f1']:.3f}, AUC {hm['roc_auc'] if hm['roc_auc'] is None else round(hm['roc_auc'], 3)}, "
               f"cutoff {bundle['threshold']:.3f}")

    if not ctx["promote"]:
        ctx["warning"] = True
        return summary + "; NOT promoted (--no-promote)"
    if ctx["require_targets"] and not bundle.get("meets_thesis_targets"):
        ctx["warning"] = True
        return (summary + "; NOT promoted: misses the Algorithm 4 targets "
                "(Section 3.4.4), the current model stays in service")
    archived = promote(candidate)
    ctx["promoted"] = True
    return summary + f"; promoted (previous model archived to {archived.name if archived else 'none'})"


STAGE_FUNCS: dict[str, Callable[[dict], str]] = {
    "government": stage_government,
    "news": stage_news,
    "nlp_features": stage_nlp_features,
    "panel": stage_panel,
    "retrain": stage_retrain,
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(trigger: str = "cli", run_id: str | None = None, skip: set[str] | None = None,
        promote_model: bool = True, require_targets: bool = True, trials: int = 100,
        timeout: float = 6 * 3600) -> RunRecord:
    skip = skip or set()
    record = RunRecord(run_id=run_id or new_run_id(), trigger=trigger,
                       started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    _acquire_lock(stale_after=timeout)
    ctx = {"run_id": record.run_id, "timeout": timeout, "trials": trials,
           "promote": promote_model, "require_targets": require_targets}
    try:
        record.save()
        hard_failed = False
        for name in STAGES:
            if name in skip or (hard_failed and name in HARD_STAGES):
                reason = "skipped by request" if name in skip else "skipped: earlier stage failed"
                record.stages.append(StageResult(name, "skipped", reason))
                continue
            t0 = time.monotonic()
            ctx.pop("warning", None)
            try:
                detail = STAGE_FUNCS[name](ctx)
                status = "warning" if ctx.get("warning") else "ok"
            except Exception as exc:
                log.error("stage %s failed: %s", name, exc)
                log.debug(traceback.format_exc())
                detail, status = str(exc)[:500], ("failed" if name in HARD_STAGES else "warning")
                if name in HARD_STAGES:
                    hard_failed = True
            record.stages.append(StageResult(name, status, detail, round(time.monotonic() - t0, 1)))
            log.info("stage %-12s %-8s %s", name, status, detail)
            record.save()

        statuses = {s.status for s in record.stages}
        record.status = ("failed" if "failed" in statuses
                         else "completed_with_warnings" if "warning" in statuses
                         else "succeeded")
        record.model_promoted = bool(ctx.get("promoted"))
        record.trained_through = ctx.get("trained_through")
    finally:
        record.finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if record.status == "running":
            record.status = "failed"
        record.save()
        _release_lock()
    return record


def main() -> None:
    from app.config import settings

    ap = argparse.ArgumentParser(description="Run the aiPHeed quarterly pipeline once")
    ap.add_argument("--trigger", default="cli")
    ap.add_argument("--run-id")
    ap.add_argument("--skip", nargs="*", default=[], choices=STAGES)
    ap.add_argument("--no-promote", action="store_true",
                    help="train and validate a candidate but leave the served model alone")
    ap.add_argument("--trials", type=int, default=settings.PIPELINE_OPTUNA_TRIALS)
    ap.add_argument("--news-only", action="store_true",
                    help="internal: run the news collection step alone (used by stage_news)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.news_only:
        print(collect_news())
        return
    try:
        record = run(trigger=args.trigger, run_id=args.run_id, skip=set(args.skip),
                     promote_model=not args.no_promote, trials=args.trials,
                     timeout=settings.PIPELINE_TIMEOUT_SECONDS)
    except PipelineBusy as exc:
        print(exc)
        sys.exit(75)
    print(json.dumps(asdict(record), indent=2, default=str))
    sys.exit(0 if record.status != "failed" else 1)


if __name__ == "__main__":
    main()

"""
Mirror the forecast history, the run log and the source-update log into the database (tables of migration f6a7b8c9d0e1).

The files under data/final/ are the record of truth (committed with the code, so they survive a host whose disk is reset on
redeploy); the tables are a queryable copy. The sync only INSERTS rows it does not have yet (keyed by the ledger hash, the run id
or the source attempt); it never updates or deletes, so a database row can never overwrite an issued forecast.

    python -m app.final.dbsync          (also run by app.final.cycle after every run and at start-up)
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, text

from app.final import cycle as CY
from app.final import history as HI
from app.final import sources as SR


def _sync_url(url: str) -> str:
    return url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2") if url else url


def sync(url: str | None = None, ledger: Path | None = None, runs: Path | None = None, source_log: Path | None = None) -> dict:
    if url is None:
        from app.config import settings
        url = settings.DATABASE_URL
    eng = create_engine(_sync_url(url))
    n = {"forecasts": 0, "outcomes": 0, "supersessions": 0, "runs": 0, "sources": 0}
    with eng.begin() as c:
        have = {r[0] for r in c.execute(text("SELECT ledger_hash FROM final_forecast_history UNION SELECT ledger_hash FROM final_forecast_outcomes "
                                             "UNION SELECT ledger_hash FROM final_forecast_supersessions"))}
        for r in HI.read(ledger):
            if r["hash"] in have:
                continue
            if r.get("type") == "forecast":
                c.execute(text(
                    "INSERT INTO final_forecast_history (ledger_hash, model_id, model_version, issue_quarter, information_cutoff, target_quarter, lead, "
                    "province, province_code, p_high, risk_class, share_pct, range90_low, range90_high, generated_utc, data_version, issue_dir) VALUES "
                    "(:h, :model_id, :model_version, :issue_quarter, :information_cutoff, :target_quarter, :lead, :province, :province_code, :p_high, "
                    ":risk_class, :share_pct, :lo, :hi, :generated_utc, :data_version, :issue_dir)"),
                    {**r, "h": r["hash"], "lo": r["range90_pct"][0], "hi": r["range90_pct"][1]})
                n["forecasts"] += 1
            elif r.get("type") == "outcome":
                c.execute(text(
                    "INSERT INTO final_forecast_outcomes (ledger_hash, province, reference_quarter, observed_share_pct, observed_class, source, "
                    "source_sha256, authorized_by, recorded_utc) VALUES (:h, :province, :reference_quarter, :observed_share_pct, :observed_class, "
                    ":source, :source_sha256, :authorized_by, :recorded_utc)"), {**r, "h": r["hash"]})
                n["outcomes"] += 1
            elif r.get("type") == "superseded":                  # a corrected re-issue replaced this issue (forecasts stay as they were)
                c.execute(text(
                    "INSERT INTO final_forecast_supersessions (ledger_hash, model_id, issue_quarter, superseded_by, reason, decided_by, "
                    "evidence, recorded_utc) VALUES (:h, :model_id, :issue_quarter, :superseded_by, :reason, :by, :evidence, :recorded_utc)"),
                    {**r, "h": r["hash"]})
                n["supersessions"] += 1
        have_runs = {r[0] for r in c.execute(text("SELECT run_id FROM final_forecast_runs"))}
        for r in CY.runs_log(runs or CY.RUNS):
            if r.get("run_id") in have_runs or "run_id" not in r:
                continue
            c.execute(text("INSERT INTO final_forecast_runs (run_id, started_utc, finished_utc, now_ph, current_quarter, issue_quarter, status, error) "
                           "VALUES (:run_id, :started_utc, :finished_utc, :now_ph, :current_quarter, :issue_quarter, :status, :error)"),
                      {k: r.get(k) for k in ("run_id", "started_utc", "finished_utc", "now_ph", "current_quarter", "issue_quarter", "status", "error")})
            n["runs"] += 1
        log = source_log or SR.LOG
        have_src = {(a, b) for a, b in c.execute(text("SELECT source, attempt_utc FROM final_source_updates"))}
        if log.exists():
            for line in log.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                if (r["source"], r["attempt_utc"]) in have_src:
                    continue
                c.execute(text("INSERT INTO final_source_updates (source, attempt_utc, status, detail) VALUES (:s, :a, :st, :d)"),
                          {"s": r["source"], "a": r["attempt_utc"], "st": r["status"], "d": json.dumps(r.get("detail") or r.get("error"))})
                n["sources"] += 1
    return n


if __name__ == "__main__":
    print(json.dumps(sync(), indent=1))

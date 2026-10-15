"""E29 recurring-collection verification (QUARTERLY_COLLECTION_VERIFICATION.md). Run from the E29 folder:

    python -B runner/e29_collection_verification.py A|B|C|D|all   ->  runs/e29_collection_verification_<stage>.json

A  REAL scheduler execution: APScheduler BackgroundScheduler fires the real app.tasks.scheduler.run_news_incremental
   (DateTrigger, a few seconds ahead) on today's clock. Expected today: the active quarter 2026-Q4 (and 2026-Q3 in its
   45-day overlap) are refused (not authorized), nothing is retryable, nothing to score; the run is logged.
B  ACTIVE-QUARTER workflow with LIVE, AUTHORIZED data and a SIMULATED clock: 2026-Q2 replayed as if it were the active
   quarter (clock 2026-05-15, 2026-06-20, 2026-07-05 PHT; cutoff = the simulated clock so nothing published "after now"
   can enter). Live Google News RSS; separate store data/news_e29_active_quarter_sim.
C  FAILURE visibility and recovery: an unreachable proxy makes every request fail -> the run stops
   STOPPED_SOURCE_UNAVAILABLE, the status view shows failed windows; the next normal run retries and completes them.
D  NO ALTERATION of earlier records: article-store prefix, E28 FSSI panel, E25 seal and the dev ledgers hashed before
   and after a quarterly cycle and the stages above.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard29  # noqa: E402

guard29.install()
EXP = guard29.EXP
BD = EXP / "backend_dev"
sys.path.insert(0, str(BD))
os.chdir(BD)
PH = timezone(timedelta(hours=8))
SIM = BD / "data" / "news_e29_active_quarter_sim"


def sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def stage_a() -> dict:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.date import DateTrigger

    import app.tasks.scheduler as S
    from app.news.store import NewsStore

    before = len(NewsStore(BD / "data" / "news_e28").read("runs"))
    done: dict = {}

    def job():
        t0 = datetime.now(timezone.utc).isoformat()
        try:
            done["result"] = S.run_news_incremental()
        except Exception as exc:          # recorded, not hidden
            done["error"] = f"{type(exc).__name__}: {exc}"
        done["fired_at"], done["ended_at"] = t0, datetime.now(timezone.utc).isoformat()

    sch = BackgroundScheduler(timezone="Asia/Manila")
    run_at = datetime.now(timezone.utc) + timedelta(seconds=3)
    sch.add_job(job, trigger=DateTrigger(run_date=run_at), id=S.NEWS_JOB_ID, max_instances=1, coalesce=True)
    sch.start()
    for _ in range(600):
        if "ended_at" in done:
            break
        time.sleep(1)
    sch.shutdown(wait=True)
    runs = NewsStore(BD / "data" / "news_e28").read("runs")
    new = runs[before:]
    return {"scheduled_for_utc": run_at.isoformat(), **done, "new_run_records": new,
            "verdict": ("FIRED_AND_EXECUTED" if "ended_at" in done and "error" not in done else "FAILED"),
            "note": "real APScheduler BackgroundScheduler + DateTrigger + the real job function; not mocked"}


def _cli(args):
    from scripts.news_collect import main

    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(args)
    try:
        out = json.loads(buf.getvalue())
    except Exception:
        out = buf.getvalue()[-500:]
    return code, out


def stage_b() -> dict:
    from app.news.audit import status_view
    from app.news.store import NewsStore

    res = []
    for clock in ("2026-05-15T09:00:00+08:00", "2026-06-20T09:00:00+08:00", "2026-07-05T09:00:00+08:00"):
        code, out = _cli(["incremental", "--store", str(SIM), "--now", clock, "--cutoff", clock])
        st = NewsStore(SIM)
        w = {}
        for x in st.windows.values():
            w[x["status"]] = w.get(x["status"], 0) + 1
        sights = st.read("sightings")
        res.append({"clock": clock, "exit": code, "run": out, "articles": len(st.articles),
                    "sightings": len(sights), "window_status": w,
                    "articles_published_after_clock": sum(1 for a in st.articles.values()
                                                          if datetime.fromisoformat(a["published_ph"]) > datetime.fromisoformat(clock))})
    st = NewsStore(SIM)
    keys = [a["article_key"] for a in st.read("articles")]
    return {"steps": res, "duplicate_article_records": len(keys) - len(set(keys)),
            "rejected": {r: sum(1 for x in st.read("rejected") if x["reason"] == r)
                         for r in {x["reason"] for x in st.read("rejected")}},
            "status_view": status_view(st, "2026-Q2"),
            "note": "LIVE Google News RSS, authorized period; the clock is SIMULATED (--now/--cutoff)"}


def stage_c() -> dict:
    from app.news.audit import status_view
    from app.news.collector import Collector
    from app.news.sources import GoogleNewsRSS
    from app.news.store import NewsStore

    store_dir = BD / "data" / "news_e29_failure_sim"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9"          # nothing listens: every request fails
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:9"
    try:
        col = Collector(NewsStore(store_dir), [GoogleNewsRSS(max_attempts=2, backoff=(1.0,), delay=0.5)],
                        authorized_until="2026-Q2", now=datetime(2026, 7, 5, tzinfo=PH), max_consecutive_failures=4)
        r1 = col.run("incremental", ["2026-Q2"], provinces=["Batangas"])
    finally:
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("HTTP_PROXY", None)
    sv1 = status_view(NewsStore(store_dir), "2026-Q2")
    col2 = Collector(NewsStore(store_dir), [GoogleNewsRSS()], authorized_until="2026-Q2",
                     now=datetime(2026, 7, 5, tzinfo=PH), cutoff_ph=datetime(2026, 7, 5, tzinfo=PH))
    r2 = col2.run("incremental", ["2026-Q2"], provinces=["Batangas"])
    sv2 = status_view(NewsStore(store_dir), "2026-Q2")
    return {"failed_run": r1, "status_after_failure": {k: sv1[k] for k in ("window_status_counts", "failed_or_open_windows",
                                                                            "last_completed_run_utc", "stale")},
            "recovery_run": r2, "status_after_recovery": {k: sv2[k] for k in ("window_status_counts", "failed_or_open_windows",
                                                                               "last_completed_run_utc", "stale")}}


FILES_D = ["data/news_e28/articles.jsonl", "data/news_e28/scores.jsonl", "data/news_e28/fssi_panel.csv",
           "data/ledger/T1_A.jsonl", "data/ledger/T2.jsonl"]


def stage_d(before: dict | None = None) -> dict:
    seal = guard29.E25 / "runs" / "SEAL_E25_20261014T002548Z" / "prospective_forecasts.csv"
    now = {f: sha(BD / f) for f in FILES_D}
    now["E25 seal"] = sha(seal)
    from scripts.quarterly_update import main as q

    code = q(["cycle"])
    after = {f: sha(BD / f) for f in FILES_D}
    after["E25 seal"] = sha(seal)
    e28 = {f: sha(guard29.E28 / "backend_dev" / f) for f in FILES_D}
    return {"cycle_exit": code, "unchanged_by_cycle": {k: now[k] == after[k] for k in now},
            "equal_to_E28_originals": {f: after[f] == e28[f] for f in FILES_D},
            "seal_matches_SEAL_json": after["E25 seal"] == json.loads((seal.parent / "SEAL.json").read_text())["sha256_forecasts"]}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = {"A": stage_a, "B": stage_b, "C": stage_c, "D": stage_d}
    for k in (fns if which == "all" else [which]):
        out = fns[k]()
        (EXP / "runs" / f"e29_collection_verification_{k}.json").write_text(json.dumps(out, indent=1, default=str),
                                                                          encoding="utf-8")
        print(k, json.dumps(out, indent=1, default=str)[:3000])

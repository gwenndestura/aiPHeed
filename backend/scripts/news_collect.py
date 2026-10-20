"""
Quarterly news collection CLI (E28). Run from backend_dev/:

    python -m scripts.news_collect backfill [--from 2021-Q1] [--to <authorized_until>] [--provinces Batangas ...]
    python -m scripts.news_collect incremental [--now 2026-05-15T10:00:00+08:00]
    python -m scripts.news_collect missing          # province-quarter windows not yet COMPLETE
    python -m scripts.news_collect score            # XLM-RoBERTa scores for unscored province-attributed articles
    python -m scripts.news_collect fssi             # province-quarter FSSI + sufficiency
    python -m scripts.news_collect topics           # BERTopic patterns per province-quarter (descriptive only)
    python -m scripts.news_collect audit            # machine-readable coverage audit
    python -m scripts.news_collect status           # last runs, failures, open windows

Every command is idempotent and resumable: an interrupted backfill is continued by running it again.
The authorized limit is read from config/authorization.json; quarters after it are refused, not collected.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BD = Path(__file__).resolve().parents[1]
if str(BD) not in sys.path:
    sys.path.insert(0, str(BD))

DEFAULT_STORE = BD / "data" / "news_e28"


def authorized_until() -> str:
    return json.loads((BD / "config" / "authorization.json").read_text(encoding="utf-8"))["authorized_until"]


def authorized_through() -> str | None:
    """E31: optional date-level limit (YYYY-MM-DD) inside the last authorized quarter."""
    return json.loads((BD / "config" / "authorization.json").read_text(encoding="utf-8")).get("authorized_through")


def _sources(names: list[str]):
    from app.news.sources import GDELTDoc, GoogleNewsRSS

    reg = {"google_news_rss": GoogleNewsRSS, "gdelt_doc": GDELTDoc}
    return [reg[n]() for n in names]


def main(argv: list[str] | None = None) -> int:
    from app.news.collector import Collector, all_quarters
    from app.news.store import NewsStore
    from app.news.timeutil import quarter_of_date, quarters_between

    ap = argparse.ArgumentParser(prog="news_collect")
    ap.add_argument("command", choices=["backfill", "incremental", "missing", "score", "fssi", "topics", "audit", "status"])
    ap.add_argument("--store", default=str(DEFAULT_STORE))
    ap.add_argument("--from", dest="q_from", default="2021-Q1")
    ap.add_argument("--to", dest="q_to", default=None)
    ap.add_argument("--provinces", nargs="*", default=None)
    ap.add_argument("--sources", nargs="*", default=["google_news_rss"])
    ap.add_argument("--max-requests", type=int, default=None)
    ap.add_argument("--now", default=None, help="ISO clock override (tests and dry runs)")
    ap.add_argument("--cutoff", default=None, help="forecast information cutoff (ISO); later articles are refused")
    ap.add_argument("--out", default=None)
    ap.add_argument("--policy", default=None, help="source policy version (config/source_policy.json); default: active")
    ap.add_argument("--model-key", default=None,
                    help="topics: scoring model key of the stored XLM-R scores (default: the current classifier's key)")
    a = ap.parse_args(argv)
    store = NewsStore(a.store)
    au = authorized_until()
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc)
    cutoff = datetime.fromisoformat(a.cutoff) if a.cutoff else None

    if a.command in ("backfill", "incremental"):
        from app.news.policy import credible_fn

        col = Collector(store, _sources(a.sources), authorized_until=au, cutoff_ph=cutoff, now=now,
                        credible=credible_fn(a.policy), authorized_through=authorized_through())
        if a.command == "backfill":
            qs = quarters_between(a.q_from, a.q_to or au)
        else:
            from app.news.timeutil import PH, quarter_start

            today = now.astimezone(PH).date()
            cur = quarter_of_date(today)
            qs = [cur]
            # the just-closed quarter is re-queried for 45 days: search indexes add articles late
            if (today - quarter_start(cur)).days < 45:
                y, n = int(cur[:4]), int(cur[-1])
                qs.insert(0, f"{y - 1}-Q4" if n == 1 else f"{y}-Q{n - 1}")
        res = col.run(a.command, qs, provinces=a.provinces, max_requests=a.max_requests)
        print(json.dumps(res, indent=1))
        return 0 if res["status"] == "COMPLETED" else 2

    if a.command == "missing":
        from app.news.audit import missing_windows

        miss = missing_windows(store, all_quarters(au))
        print(json.dumps(miss, indent=1))
        return 0

    if a.command == "score":
        from app.news.scoring import score_pending

        print(json.dumps(score_pending(store), indent=1))
        return 0

    if a.command == "fssi":
        from app.news.fssi import build_fssi

        out = build_fssi(store, all_quarters(au))
        print(json.dumps(out["summary"], indent=1))
        return 0

    if a.command == "topics":
        from app.news.scoring import current_model_key
        from app.news.topics import build_topic_files

        # descriptive BERTopic patterns -> <store>/topics/ (manifest always; proportions only if the gate passes)
        out = build_topic_files(store, all_quarters(au), a.model_key or current_model_key(),
                                out_dir=Path(a.out) if a.out else None)
        print(json.dumps(out, indent=1, default=str))
        return 0

    if a.command == "audit":
        from app.news.audit import coverage_audit

        rows = coverage_audit(store, all_quarters(au))
        out = Path(a.out) if a.out else Path(a.store) / "coverage_audit.json"
        out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print(json.dumps({"rows": len(rows), "written": str(out)}, indent=1))
        return 0

    if a.command == "status":
        from app.news.audit import status_view

        print(json.dumps(status_view(store, au), indent=1))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

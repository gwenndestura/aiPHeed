"""
scripts/cb6_quarterly.py
------------------------
Operator commands for the automatic C-B6 update (the scheduler normally does all of this by itself).

    python -m scripts.cb6_quarterly status
    python -m scripts.cb6_quarterly run [--now 2027-01-01T05:00:00+08:00]   # the quarterly step, as the scheduler runs it
    python -m scripts.cb6_quarterly score-news                               # XLM-RoBERTa on new articles (needs the memory)

Needs AIPHEED_FI_DATA_DIR and AIPHEED_CB6_STATE_DIR. Nothing here trains a model.
"""
from __future__ import annotations

import argparse
import json


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "run", "score-news"])
    ap.add_argument("--now", default=None)
    a = ap.parse_args(argv)
    from app.cb6_auto import job, news

    if a.command == "status":
        out = job.status()
    elif a.command == "run":
        out = job.run_due(a.now)
    else:
        out = news.score_new()
    print(json.dumps(out, indent=1, default=str, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Manual SWS entry and SWS-release re-issue of Lead-2+ forecasts (app.ml.inference.sws_reissue).

    python scripts/sws_reissue.py enter --area BL --quarter 2026-Q4 --H 18.2 --published 2027-01-20 --fw-end 2026-12-15 --moe 4
    python scripts/sws_reissue.py run [--now 2027-01-21]     # record served quarter-start rows, re-issue what is due
    python scripts/sws_reissue.py status [--now 2027-01-21]  # forecasts in force
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.inference import sws_reissue as RI  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enter")
    for a in ("--area", "--quarter", "--H", "--published", "--fw-end", "--moe"):
        e.add_argument(a, required=True)
    for name in ("run", "status"):
        sub.add_parser(name).add_argument("--now")
    a = ap.parse_args(argv)
    if a.cmd == "enter":
        print(RI.enter_sws_reading(a.area, a.quarter, float(a.H), a.published, a.fw_end, float(a.moe)))
    elif a.cmd == "run":
        print(json.dumps(RI.run_daily(a.now), indent=1, default=str))
    else:
        print(RI.current(a.now).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Temporal-validity correction of the first FINAL issue (owner instructions 2026-11-14).

  original   2026-Q4   cut-off 1 Nov 2026 00:00 PHT (quarterly rule), generated 2026-11-13T15:20:58Z. It used October 2026 CPI
                       (PSA release 5 Nov 2026) and September 2026 LFS (PSA release 6 Nov 2026): both after its cut-off.
  corrected  2026-11   cut-off 10 Nov 2026 00:00 PHT (monthly rule: data update and forecast on the 10th of every month). Built
                       with the same frozen FINAL model, the same input schema, preprocessing and missing-value handling, from
                       panels rebuilt with the strict rule (only figures online before 10 Nov 2026).

The original issue folder and its ledger records are never changed. The ledger gets the corrected issue's records and one
append-only "superseded" record naming the replacement, the reason, who decided and the evidence. The original inputs are kept in
data/final/corrections/2026-Q4/ (the seven input files, hash-checked against the original manifest, and the exact inference rows).

News: the corrected issue's news inputs are those of the original (stories published 1 Aug - 31 Oct 2026, all before 10 Nov).
News collection was not re-run for 1-9 Nov 2026 (the raw news archive is not in this checkout), so no story after 31 Oct is used;
nothing is filled in for those days.

    python -m app.final.correction run --by "<owner>"
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.final import history as HI
from app.final import issue as IS
from app.final import period as PD

ORIGINAL, CORRECTED = "2026-Q4", "2026-11"
CORR = IS.ROOT / "corrections" / ORIGINAL
REASON = ("Temporal data availability correction: the 2026-Q4 forecast (cut-off 1 Nov 2026) used October 2026 CPI (released by "
          "PSA on 5 Nov 2026) and September 2026 LFS unemployment (released 6 Nov 2026), published after its cut-off. Replaced by "
          "the 10 November 2026 forecast under the monthly rule (data update and forecast on the 10th), built only from figures "
          "published before 10 Nov 2026.")
EVIDENCE = ("Q4_2026_FORECAST_CORRECTION_REPORT.md; data/final/corrections/2026-Q4/ (original inputs, hash-checked); PSA releases: "
            "CPI Oct 2026 on 5 Nov 2026, CPI Sep 2026 on 6 Oct 2026, LFS Sep 2026 on 6 Nov 2026, LFS Aug 2026 on 7 Oct 2026")


def run(by: str, ledger: Path | None = None) -> dict:
    model = PD.serving()["model_id"]
    if PD.issue_datetime(CORRECTED).date().isoformat() != "2026-11-10":
        raise IS.IssueError("serving.json must carry the monthly rule (day 10) before the correction is issued")
    if not (CORR / "original_inputs.csv").exists():
        raise IS.IssueError("the original inputs snapshot is missing; take it before the panels are rebuilt")
    os.environ["AIPHEED_LIVE_ASOF"] = PD.issue_datetime(CORRECTED).date().isoformat()
    os.environ.pop("AIPHEED_LIVE_PUBLISHED", None)
    out = {}
    d = IS.ISSUES / CORRECTED
    if not d.exists():
        news = json.loads((IS.ISSUES / ORIGINAL / "news_used.json").read_text(encoding="utf-8"))
        news["note"] = ("The news inputs of this forecast are those of the 1 November 2026 forecast: stories published 1 August - 31 "
                        "October 2026. Stories from 1-9 November 2026 were not collected for this re-issue.")
        d = IS.build(CORRECTED, news_used=news,
                     live_extra={"supersedes": ORIGINAL, "correction_reason": REASON, "news_window": "2026-08-01 to 2026-10-31"})
    out["issue_dir"] = str(d)
    out["history"] = HI.record_issue(IS.ledger_rows(d), ledger)
    out["supersession"] = HI.record_supersession(model, ORIGINAL, CORRECTED, REASON, by, EVIDENCE, ledger)
    out["verify"] = HI.verify(ledger)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--by", required=True)
    a = ap.parse_args()
    print(json.dumps(run(a.by), indent=1, default=str))

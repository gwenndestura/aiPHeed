"""
E174: one-time evaluation runner for frozen E168 vs frozen SIMPLE on genuinely independent provincial HFIAS rows.

It refuses to run until the independent set qualifies (protocol, docs/e173/PROTOCOL.md section 4 and E174 PROVENANCE.md):
  - every row HFIAS, province level, status 'eligible independent', never used in E151-E173;
  - a published standard error for every row (C2 and the Brier score need the class probability q_true, which needs the SE;
    nothing is imputed);
  - at least 40 rows (C6) and at least two survey rounds;
  - the runner has not run before (data/e174/out/evaluation.json absent).
Forecasts of both frozen models are written and hashed before any label is read; scoring uses app.e156.leads.evaluate unchanged.

    python -m app.e174.evaluate_future check      report readiness only (never reads label values)
    python -m app.e174.evaluate_future run        the one-time evaluation (refuses unless ready)
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from app.paths import BACKEND_DIR

ROWS = BACKEND_DIR / "data" / "e174" / "independent_rows" / "independent_rows.csv"
OUT = BACKEND_DIR / "data" / "e174" / "out"
MIN_ROWS, MIN_ROUNDS = 40, 2
REQUIRED = ["source_record_id", "survey_round", "year", "key", "level", "instrument", "status", "prior_use", "se_published"]


class NotReady(RuntimeError):
    pass


def readiness(rows: pd.DataFrame) -> dict:
    """Checks that use only provenance columns (no label values)."""
    miss = [c for c in REQUIRED if c not in rows]
    if miss:
        return {"ready": False, "reasons": [f"missing columns: {miss}"]}
    r = []
    if (rows["instrument"] != "HFIAS").any():
        r.append("non-HFIAS rows present (FIES / Radimer-Cornell cannot replace the HFIAS target)")
    if (rows["level"] != "province").any():
        r.append("non-province rows present")
    if (rows["status"] != "eligible independent").any() or (rows["prior_use"] != "not used").any():
        r.append("rows previously used or not eligible")
    if not rows["se_published"].astype(bool).all():
        r.append(f"{int((~rows['se_published'].astype(bool)).sum())} rows without a published standard error (q_true / Brier / C2 need it)")
    if len(rows) < MIN_ROWS:
        r.append(f"{len(rows)} rows < {MIN_ROWS} required by C6")
    if rows["survey_round"].nunique() < MIN_ROUNDS:
        r.append(f"{rows['survey_round'].nunique()} survey round(s) < {MIN_ROUNDS}")
    if (OUT / "evaluation.json").exists():
        r.append("already evaluated once")
    return {"ready": not r, "rows": int(len(rows)), "provinces": int(rows["key"].nunique()), "rounds": int(rows["survey_round"].nunique()), "reasons": r}


def score(F: pd.DataFrame) -> dict:
    """Score already-written forecasts of both frozen models (columns E168, mu_E168, half_E168, SIMPLE, ..., PERS, y_true, y_high,
    q_true, region, survey, lead) with the unchanged C1-C6 implementation."""
    from app.e156 import leads as LD
    return {a: LD.evaluate(F, a, a) for a in ("E168", "SIMPLE")}


def run():
    rows = pd.read_csv(ROWS) if ROWS.exists() else pd.DataFrame()
    st = readiness(rows)
    if not st["ready"]:
        raise NotReady("independent evaluation not possible: " + "; ".join(st["reasons"]))
    # When ready: (1) for each row, issue dates at Leads 1-3 before its round's reference quarter; (2) run frozen E168
    # (app.e168.lgbm.forecast) and frozen SIMPLE (app.e173.freeze rule, config hash checked) with data published before each
    # issue date; (3) write and hash the forecasts; (4) only then load the labels and call score(); (5) write evaluation.json once.
    raise NotReady("ready set detected: implement steps 1-5 against the new round's reference quarter before running (not needed today)")


if __name__ == "__main__":
    rows = pd.read_csv(ROWS) if ROWS.exists() else pd.DataFrame()
    if sys.argv[1] == "check":
        print(json.dumps(readiness(rows), indent=1))
    else:
        run()

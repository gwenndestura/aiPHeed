"""
Forecast generation from a frozen artifact. Never re-estimates parameters: it filters the data known at the issue date
(as_of) with the artifact's parameters and forecasts Leads 1-4 (Lead k = dashboard quarter - 1 + k; issue = first day
of the dashboard quarter, app.quarterly.target). Fails loudly when the artifact, the data or the issue date is invalid.

Each record carries issue date, dashboard quarter, target quarter, lead, area, score, 80 % interval, model version and
artifact hash, data vintage, feature cutoff, preprocessing version, evidence status and reliability status.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.forecasting import artifact as A
from app.forecasting import models as M
from app.forecasting import sws as T
from app.forecasting.as_of import issue_instant
from app.forecasting.evidence import AREAS, CALABARZON_SWS_AREA, EvidenceStatus, ReliabilityStatus

LEADS = (1, 2, 3, 4)
# Mechanical verdict of docs/aipheed/MODEL_REPORT.md (phase 6): no lead passes N1-N7; Lead 2 not yet testable on
# unseen quarters. Kept here so every served record states it; tests pin it to results/reliability_verdict.csv.
RELIABILITY = {k: ReliabilityStatus.NOT_RELIABLE for k in LEADS}


class InferenceError(RuntimeError):
    pass


def forecast(issue: date, artifact_path: Path, rounds_path: Path = T.SWS_ROUNDS) -> list[dict]:
    if issue.day != 1 or issue.month not in (1, 4, 7, 10):
        raise InferenceError(f"{issue} is not a quarter start: forecasts are issued on the first day of a quarter")
    body, params = A.load(artifact_path, rounds_path)
    if issue < date.fromisoformat(body["training_cutoff"]):
        raise InferenceError("issue date precedes the artifact's training cutoff: the artifact would carry future data")
    qt = T.known_at(T.load_rounds(rounds_path), issue)
    if qt.empty:
        raise InferenceError(f"no SWS round published before {issue}")
    D = T.qi(f"{issue.year}-Q{(issue.month - 1) // 3 + 1}")
    vintage = max(qt["published"]).isoformat()
    out = []
    for k in LEADS:
        target = D - 1 + k
        fc = M.forecast_seas(qt, params, target)
        missing = [a for a in AREAS if a not in fc]
        if missing:
            raise InferenceError(f"no forecast for {missing}")
        for a in AREAS:
            r = fc[a]
            if not (0.0 <= r["f"] <= 100.0) or r["sd"] <= 0:
                raise InferenceError(f"{a} {T.qs(target)}: forecast {r['f']:.2f} or sd {r['sd']:.2f} outside the valid range")
            out.append({"issue_date": issue.isoformat(), "feature_cutoff": issue_instant(issue).isoformat() + " (exclusive)",
                        "dashboard_quarter": T.qs(D), "target_quarter": T.qs(target), "lead": k, "area": a,
                        "score": round(r["f"], 4), "lo80": round(r["lo80"], 4), "hi80": round(r["hi80"], 4),
                        "unit": "% of families, SWS involuntary hunger",
                        "components": {"level": round(r["level"], 4), "design_effect": round(r["design_effect"], 4)},
                        "horizon_quarters_from_latest_data": r["h"],
                        "latest_data_quarter": T.qs(int(qt["qi"].max())), "data_vintage_published": vintage,
                        "model": body["model"], "model_version": body["training_cutoff"],
                        "artifact_sha256": body["artifact_sha256"], "preprocessing_version": body["preprocessing_version"],
                        "evidence_status": EvidenceStatus.AWAITING_GROUND_TRUTH.value,
                        "geography_note": ("SWS area value; CALABARZON lies in this area" if a == CALABARZON_SWS_AREA
                                           else "SWS area value"),
                        "reliability_status": RELIABILITY[k].value})
    return out

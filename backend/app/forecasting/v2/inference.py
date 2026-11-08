"""
v2 forecast generation from a frozen artifact. Never re-estimates: it filters the SWS history known at the issue
(as_of) with the artifact's parameters, adds the artifact's conformal half-width, and stores the provenance of every
number. Fails loudly on an invalid artifact, data file or issue date.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.forecasting import sws as T
from app.forecasting.as_of import issue_instant
from app.forecasting.evidence import AREAS, CALABARZON_SWS_AREA, EvidenceStatus
from app.forecasting.v2 import artifact as A
from app.forecasting.v2 import models as V
from app.forecasting.v2.select import LEADS, dashboard_quarter, interval


class InferenceError(RuntimeError):
    pass


def limitation(model: str, status: str, lead: int) -> str:
    what = ("This is the latest published SWS hunger reading carried forward (persistence): no change is predicted."
            if model == "PERSIST" else
            "This is the latest SWS hunger reading with part of its survey sampling noise filtered out; no further "
            "change is predicted.")
    return (f"{what} It is an SWS area value, not a provincial or LGU measurement. Lead {lead} status: {status}. On the "
            "2021-2026 development data no model reached 75 % within tolerance at Lead 2 (best history-only bound about "
            "43 %); confirmation needs at least 10 unseen SWS quarters (earliest about mid-2029).")


def forecast(issue: date, artifact_path: Path, rounds_path: Path = T.SWS_ROUNDS) -> list[dict]:
    if issue.day != 1 or issue.month not in (1, 4, 7, 10):
        raise InferenceError(f"{issue} is not a quarter start: forecasts are issued on the first day of a quarter")
    body, p = A.load(artifact_path)
    if issue < date.fromisoformat(body["training_cutoff"]):
        raise InferenceError("issue date precedes the artifact's training cutoff: the artifact would carry future data")
    known = T.known_at(T.load_rounds(rounds_path), issue)
    if known.empty:
        raise InferenceError(f"no SWS round published before {issue}")
    D = dashboard_quarter(issue)
    vintage = max(known["published"]).isoformat()
    out = []
    for k in LEADS:
        target = D - 1 + k
        fc = V.forecast(known, p, target)
        missing = [a for a in AREAS if a not in fc]
        if missing:
            raise InferenceError(f"no forecast for {missing}")
        conf = body["conformal"][str(k)]
        status = body["reliability_status_by_lead"][str(k)]
        for a in AREAS:
            r = fc[a]
            lo, hi, how = interval(r["f"], r["sd"], conf["halfwidth80"])
            if not (0.0 <= r["f"] <= 100.0) or not (lo < r["f"] < hi):
                raise InferenceError(f"{a} {T.qs(target)}: forecast {r['f']:.2f} or interval outside the valid range")
            out.append({"issue_date": issue.isoformat(), "feature_cutoff": issue_instant(issue).isoformat() + " (exclusive)",
                        "dashboard_quarter": T.qs(D), "target_quarter": T.qs(target), "lead": k, "area": a,
                        "score": round(r["f"], 4), "lo80": round(max(lo, 0.0), 4), "hi80": round(min(hi, 100.0), 4),
                        "interval_method": how, "interval_residuals": conf["n_residuals"],
                        "unit": "% of families, SWS involuntary hunger",
                        "components": {"latest_reading": round(r["latest"], 4),
                                       "noise_filter_adjustment": round(r["noise_adjustment"], 4),
                                       "predicted_change_beyond_anchor": 0.0},
                        "horizon_quarters_from_latest_data": r["h"], "latest_data_quarter": T.qs(r["latest_qi"]),
                        "data_vintage_published": vintage, "method": body["method"], "model": body["model"],
                        "model_version": body["training_cutoff"], "artifact_sha256": body["artifact_sha256"],
                        "preprocessing_version": body["preprocessing_version"],
                        "evidence_status": EvidenceStatus.AWAITING_GROUND_TRUTH.value,
                        "geography_note": ("SWS area value; CALABARZON lies in this area" if a == CALABARZON_SWS_AREA
                                           else "SWS area value"),
                        "reliability_status": status, "limitation": limitation(body["model"], status, k)})
    return out

"""
app/quarterly/config.py
-----------------------
The forecast period is configuration, not code. One JSON file names the current
reference quarter and the information cutoff; everything else (target quarter,
supporting-news window) is derived, so the quarter labels cannot drift apart.

    {
      "reference_quarter": "2026-Q4",
      "cutoff": "2026-12-31T23:59:59+08:00",      // or null = end of the reference quarter
      "timezone": "Asia/Manila",
      "model_version": "...",
      "feature_version": "...",
      "requirements": [ {...}, ... ]               // see app.quarterly.update.REQUIREMENT_KINDS
    }
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from app.quarterly.periods import PH_TZ, Quarter, to_ph


@dataclass
class ForecastPeriod:
    reference_quarter: Quarter
    cutoff: pd.Timestamp
    model_version: str = "unversioned"
    feature_version: str = "unversioned"
    requirements: list[dict] = field(default_factory=list)
    timezone: str = PH_TZ

    # ---- derived -----------------------------------------------------------------
    @property
    def target_quarter(self) -> Quarter:
        return self.reference_quarter.next()

    @property
    def news_window_start(self) -> pd.Timestamp:
        return self.reference_quarter.start()

    @property
    def news_window_end(self) -> pd.Timestamp:
        """Eligible news ends at the cutoff or the end of the reference quarter, whichever is earlier."""
        return min(self.cutoff, self.reference_quarter.end())

    @property
    def quarter_complete(self) -> bool:
        """True only when the cutoff is at or after the last second of the reference quarter (23:59:59 PHT)."""
        return self.cutoff >= self.reference_quarter.end().floor("s")

    def validate(self) -> None:
        if self.timezone != PH_TZ:
            raise ValueError("aiPHeed periods are defined in Asia/Manila")
        if self.cutoff < self.reference_quarter.start():
            raise ValueError("cutoff precedes the reference quarter: no supporting news is possible")
        if self.cutoff >= self.target_quarter.start():
            raise ValueError("cutoff falls inside the target quarter: target-quarter news would leak")

    def to_dict(self) -> dict:
        return {"reference_quarter": str(self.reference_quarter), "target_quarter": str(self.target_quarter),
                "cutoff": self.cutoff.isoformat(), "timezone": self.timezone,
                "news_window_start": self.news_window_start.isoformat(),
                "news_window_end": self.news_window_end.isoformat(),
                "quarter_complete": self.quarter_complete,
                "target_display": self.target_quarter.display(),
                "news_display": self.reference_quarter.display(),
                "model_version": self.model_version, "feature_version": self.feature_version,
                "requirements": self.requirements}

    def advanced(self) -> "ForecastPeriod":
        """The next cycle: reference quarter +1, cutoff at its end (re-declare explicitly if different)."""
        ref = self.reference_quarter.next()
        reqs = [advance_requirement(r) for r in self.requirements]
        return ForecastPeriod(ref, ref.end().floor("s"), self.model_version, self.feature_version, reqs, self.timezone)


def advance_requirement(req: dict) -> dict:
    r = dict(req)
    for k in ("quarter",):
        if k in r and r[k]:
            r[k] = str(Quarter.parse(r[k]).next())
    return r


def load_period(path: str | Path) -> ForecastPeriod:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    ref = Quarter.parse(d["reference_quarter"])
    cutoff = to_ph(d["cutoff"]) if d.get("cutoff") else ref.end().floor("s")
    if "target_quarter" in d and d["target_quarter"] and str(ref.next()) != d["target_quarter"]:
        raise ValueError(f"config target_quarter {d['target_quarter']} != reference+1 {ref.next()}")
    p = ForecastPeriod(ref, cutoff, d.get("model_version", "unversioned"), d.get("feature_version", "unversioned"),
                       d.get("requirements", []), d.get("timezone", PH_TZ))
    p.validate()
    return p


def save_period(p: ForecastPeriod, path: str | Path) -> None:
    d = {"reference_quarter": str(p.reference_quarter), "target_quarter": str(p.target_quarter),
         "cutoff": p.cutoff.isoformat(), "timezone": p.timezone, "model_version": p.model_version,
         "feature_version": p.feature_version, "requirements": p.requirements}
    Path(path).write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")

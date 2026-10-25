"""
app/services/final_engine.py
----------------------------
The final aiPHeed forecasting engine as served (branch aiPHeed/final-system-completion).

What it serves, and at which geographic level:
  * regional hunger (SWS involuntary hunger, 4 SWS areas; Balance Luzon contains CALABARZON): the latest published
    observation with its survey and publication dates and age, a latest-reading outlook with empirical 80% ranges,
    and the FIL-OA LightGBM research forecast (12 indicator families) with its walk-forward evaluation;
  * province food-price squeeze (PSA CPI): an economic-access indicator, never a hunger label;
  * 142 LGUs: the existing indicator-based priority ordering (FIRI v2 re-weighted by poverty and density), labelled as a
    priority score with the reason no local hunger figure is shown;
  * news: dated, de-duplicated food-event headlines published before the as-of date, marked as reported events or
    possible future risks; context only (news did not improve forecasts);
  * archive: retrospective walk-forward predictions with outcomes, and the sealed prospective forecasts.

Every number is read from backend/data/final_engine/, exported unchanged from the frozen experiment outputs by
aipheed-backend-aligned/experiments/FINAL_OBJECTIVE_ACHIEVEMENT/runner/export_engine.py. Nothing is refitted on request.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data" / "final_engine"
REQUIRED = ("engine.json", "archive.csv", "news_events.csv")
NO_LOCAL_OUTCOME = ("No measured hunger or food-insecurity figure exists for individual provinces, cities or "
                    "municipalities in 2021-2026 (SWS reports regions only; CBMS 2024 LGU results are not public). "
                    "The map shows an indicator-based priority score, not a food-insecurity rate or probability.")
PRIORITY_LABEL = "Priority score (indicator-based; not a measured or forecast hunger rate)"
NEWS_STATUS = ("Context only: news indicators did not improve the hunger forecasts in controlled tests "
               "(with vs without news, Holm p = 1 at every lead; real vs shuffled news).")


# The forward-looking wording used by the FINAL news pipeline (experiments/FINAL_FOOD_INSECURITY_LIGHTGBM/runner/
# news_features.py ANTICIPATORY): a headline that uses it is a possible future risk, otherwise a reported event.
import re  # noqa: E402

ANTICIPATORY = re.compile(
    r"\b(expect(s|ed|ing)?|could|might|likely|loom(s|ing)?|threat(s|en|ens|ened)?|warn(s|ed|ing|ings)?|alerts?|"
    r"brac(e|es|ed|ing)|forecast(s|ed)?|project(ed|ion|ions)|outlook|fears?|feared|risks?|seen to|set to|"
    r"to (rise|increase|hit|soar|spike|climb|go up|worsen)|possible|possibly|potential|anticipat\w*|"
    r"inaasahan|asahan|posibleng?|nagbabala|babala|banta|maaaring|nakaamba)\b", re.I)
REPORTED, FUTURE = "Reported event", "Possible future risk"


def news_kind(title: str) -> str:
    return FUTURE if ANTICIPATORY.search(str(title)) else REPORTED


def news_context_note(title: str) -> str:
    """The pop-up text for a headline that has no lead text."""
    k = news_kind(title)
    what = ("The headline warns of something that may happen; it is not a report that it happened."
            if k == FUTURE else "The headline reports something that has already happened.")
    return (f"{k}. {what} News is shown as context for DA staff: in tests it did not improve the hunger forecasts, "
            "so a headline is not evidence that hunger will rise.")


class EngineMissing(RuntimeError):
    pass


def _path(name: str) -> Path:
    p = DATA / name
    if not p.exists():
        raise EngineMissing(f"{name} has not been exported (run export_engine.py)")
    return p


@functools.lru_cache(maxsize=1)
def engine() -> dict:
    return json.loads(_path("engine.json").read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def _archive() -> pd.DataFrame:
    return pd.read_csv(_path("archive.csv"))


@functools.lru_cache(maxsize=1)
def _news() -> pd.DataFrame:
    return pd.read_csv(_path("news_events.csv"), keep_default_na=False)


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


def overview() -> dict:
    e = engine()
    ev = e["evaluation"]
    return {
        "asOf": e["asOf"],
        "regionalHunger": {"measure": e["sws"]["measure"], "geography": e["sws"]["geography"],
                           "latest": e["sws"]["latest"], "notes": e["sws"]["notes"]},
        "outlook": {
            "target": "SWS involuntary hunger, Balance Luzon and the other SWS areas (regional, % of families)",
            "latestReadingOutlook": e["outlook"]["persistence"],
            "lightgbmForecast": e["outlook"]["lightgbm"],
            "status": e["outlook"]["status"], "elevatedScoreNote": e["outlook"]["elevatedScoreNote"],
            "reliableHorizon": ev["maxReliableLead"], "accuracyTarget": ev["accuracyTarget"],
            "accuracyTargetReached": ev["accuracyTargetReached"]},
        "foodPrices": {k: e["cpi"][k] for k in ("definition", "latestMonth", "latest", "linkToHunger")},
        "localEvidence": NO_LOCAL_OUTCOME,
        "dataFreshness": data_freshness(),
    }


def data_freshness() -> list[dict]:
    e = engine()
    latest = e["sws"]["latest"]
    news = _news()
    return [
        {"source": "SWS hunger (regional)", "latest": latest["quarter"], "published": latest["published"],
         "ageDays": latest["ageDaysAtAsOf"], "note": "Survey ended " + latest["fieldworkEnd"]},
        {"source": "PSA provincial CPI", "latest": e["cpi"]["latestMonth"], "published": None, "ageDays": None,
         "note": "PSA releases a month's CPI about the 5th of the following month"},
        {"source": "News corpus (CALABARZON headlines)", "latest": news["published"].max() if len(news) else None,
         "published": None, "ageDays": None, "note": "Food-event headlines, de-duplicated"},
    ]


def evaluation() -> dict:
    return engine()["evaluation"]


def families() -> dict:
    return engine()["families"]


def contributions() -> dict:
    """Mean |SHAP| share of each driver group in the FIL-OA forecasts, per lead. Groups with no share are reported
    as such (not filled in)."""
    e = engine()
    groups = e["families"]["driverGroups"]
    out = {}
    for lead, shares in e["evaluation"]["shapShare"].items():
        out[lead] = {g: round(sum(shares.get(f, 0.0) for f in fams), 4) for g, fams in groups.items()}
        out[lead]["Model structure (area, lead, survey break)"] = round(
            shares.get("design (area, lead, post_break)", 0.0), 4)
    return {"model": "FIL-OA (regional SWS hunger)", "method": "mean absolute SHAP value share per driver group",
            "byLead": out,
            "reading": "A share says how much the model leaned on a group, not that the group causes hunger; news "
                       "and most indicator groups added no measurable accuracy (see evaluation)."}


def archive(kind: str | None = None, area: str | None = None) -> dict:
    a = _archive()
    if kind == "retrospective":
        a = a[a["kind"].str.startswith("retrospective")]
    elif kind == "prospective":
        a = a[a["kind"].str.startswith("prospective")]
    if area:
        a = a[a["area"] == area]
    return {"rows": _records(a), "seals": engine()["seals"],
            "note": "Retrospective rows are walk-forward predictions made with data published before each issue date "
                    "and scored against SWS (development evidence). Prospective rows are sealed and not yet scored."}


def news(limit: int = 100, category: str | None = None, kind: str | None = None, before: str | None = None) -> dict:
    n = _news()
    if before:
        n = n[n["published"] < before]
    if category:
        n = n[n["categories"].str.contains(category, regex=False)]
    if kind == "future":
        n = n[n["kind"].str.startswith("possible")]
    elif kind == "reported":
        n = n[n["kind"] == "reported event"]
    return {"status": NEWS_STATUS, "total": int(len(n)), "rows": _records(n.head(limit))}


def cpi() -> dict:
    return engine()["cpi"]


def lgus(municipalities: list[dict]) -> dict:
    """The 142 LGU records the dashboard already serves, with their priority label and the local-evidence note."""
    e = engine()
    sq = {r["province"].lower(): r for r in e["cpi"]["latest"]}
    rows = []
    for m in municipalities:
        p = sq.get(str(m.get("provinceId", "")).lower())
        rows.append({"id": m["id"], "name": m["name"], "province": m.get("provinceId"), "lguCode": m.get("lguCode"),
                     "classification": m.get("classification"), "priorityScore": m.get("riskIndex"),
                     "priorityLevel": m.get("riskLevel"), "rankInProvince": m.get("rankInProvince"),
                     "povertyRate": m.get("povertyRate"), "povertyLimitation": m.get("povertyLimitation"),
                     "densityPerKm2": m.get("densityPerKm2"),
                     "provinceFoodPriceSqueeze": p["fpd"] if p else None,
                     "localHungerEvidence": "insufficient local outcome evidence"})
    return {"count": len(rows), "label": PRIORITY_LABEL, "note": NO_LOCAL_OUTCOME, "rows": rows}

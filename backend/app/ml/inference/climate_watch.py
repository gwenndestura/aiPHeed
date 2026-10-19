"""
E66: Climate Food-Stress Watch (CFSW) -- a transparent, rule-based EL NINO HAZARD WATCH served beside the Lead-2
forecast. It is NOT a food-insecurity probability, NOT a model input, and it never changes P(HIGH), the decision or
the map colour.

Rule (E66 PROTOCOL.md section 4, frozen before it was computed), at issue date O, using only items dated before O:
  hazard  H : a PAGASA El Nino Alert, El Nino Advisory or El Nino-related Climate Advisory is in force (the latest
              El Nino item before O is not a Watch or a Final Advisory)
  stress  S : the latest SWS regional hunger posted before O is above 11.3%
  exposure E: the latest provincial palay or corn production YoY known at O is <= -10% (unknown if both missing)
  CLIMATE WATCH + LOCAL EXPOSURE = H and S and E;  CLIMATE WATCH = H and S;  NO CLIMATE WATCH otherwise;
  INSUFFICIENT DATA when S cannot be determined (missing hunger is never read as "no stress").

Why it exists (E65/E66): the served E56/E58 model has no forward-looking climate channel (ENSO has 0 price-tree splits
and the price part projects flat prices), and its target T43 equals the provincial food-price condition whenever
regional hunger is above 11.3%, so a LOW score cannot show El Nino risk. Only one El Nino episode (2023-24) is in the
2021-2026 window, so this watch is unvalidated; E66 r5 reports its history descriptively.
"""
from __future__ import annotations

import csv
import functools
import os
from pathlib import Path

from app.ml.inference.enso_context import PAGASA_ENSO

HUNGER_LINE = 11.3
PRODUCTION_DROP = -10.0
LEVELS = ("CLIMATE WATCH + LOCAL EXPOSURE", "CLIMATE WATCH", "NO CLIMATE WATCH", "INSUFFICIENT DATA")


def _el_nino_item(text: str) -> bool:
    return text.startswith(("El Nino", "Climate Advisory"))


def _active(text: str) -> bool:
    return text.startswith(("El Nino Alert", "El Nino Advisory", "Climate Advisory"))


def hazard(issue_date: str) -> tuple[bool, str]:
    """(in force, status text) from the PAGASA El Nino items issued strictly before the issue date. Before the first
    item (2023-03-24) PAGASA's status was La Nina-related (2021-22) or none: no El Nino hazard."""
    items = [(d, s) for d, s in PAGASA_ENSO if d < issue_date and _el_nino_item(s)]
    if not items:
        return False, "no PAGASA El Nino Alert or Advisory in force"
    d, s = items[-1]
    return _active(s), f"PAGASA {d}: {s}"


def watch(issue_date: str, latest_hunger: float | None, palay_yoy: float | None, corn_yoy: float | None) -> dict:
    h, status = hazard(issue_date)
    if latest_hunger is None:
        stress = None
    else:
        stress = latest_hunger > HUNGER_LINE
    prod = [v for v in (palay_yoy, corn_yoy) if v is not None]
    exposure = None if not prod else min(prod) <= PRODUCTION_DROP
    if stress is None:
        level = "INSUFFICIENT DATA"
    elif h and stress and exposure:
        level = "CLIMATE WATCH + LOCAL EXPOSURE"
    elif h and stress:
        level = "CLIMATE WATCH"
    else:
        level = "NO CLIMATE WATCH"
    return {"level": level, "hazard": h, "hazardStatus": status, "householdStress": stress,
            "latestHunger": latest_hunger, "localExposure": exposure,
            "exposureNote": ("production data unknown" if exposure is None else
                             f"palay {_fmt(palay_yoy)}, corn {_fmt(corn_yoy)} year on year")}


def _fmt(v):
    return "n/a" if v is None else f"{v:+.1f}%"


def sentence(w: dict, issue_date: str) -> str | None:
    """Text appended to the forecast summary when a watch is in force (None otherwise)."""
    if not w["level"].startswith("CLIMATE WATCH"):
        return None
    expo = (" Local exposure: the latest provincial production fell by 10% or more year on year ("
            + w["exposureNote"] + ")." if w["localExposure"] else
            " Local exposure: no provincial production drop of 10% or more is recorded (" + w["exposureNote"] + ").")
    return (f"Climate food-stress watch ({w['level']}): at the issue date ({issue_date}) {w['hazardStatus']} was in "
            f"force and regional hunger was {w['latestHunger']:.1f}%, above 11.3%.{expo} This watch is a separate, "
            "rule-based hazard flag, not a model input and not a food-insecurity probability; it has not been "
            "validated (one El Nino episode in 2021-2026). It means the low food-price score above should not be read "
            "as low El Nino risk.")


# ---------------------------------------------------------------------------------------------- serving lookup
# Inputs known at each issue date (latest posted SWS hunger, provincial palay/corn YoY), exported by E66 r5 from the
# E56 feature table (the same values the model saw); the current record's own observations are used first.
INPUTS = Path(os.getenv("AIPHEED_E66_CFSW_INPUTS", "data/e66/cfsw_inputs.csv"))


@functools.lru_cache(maxsize=2)
def _inputs(path: str, mtime_ns: int) -> dict:
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            num = {k: (float(r[k]) if r[k] not in ("", "nan", "None") else None)
                   for k in ("latest_hunger", "palay_yoy_known", "corn_yoy_known")}
            out[(r["target"], r["province_code"])] = {"issue": r["issue_date"], **num}
    return out


def for_quarter(rec: dict, quarter: str, code: str) -> dict | None:
    """CFSW for a province's issued (record target) or earlier Lead-2 forecast; None when the inputs are unknown."""
    p = rec.get("provinces", {}).get(code)
    if p is None:
        return None
    if quarter == rec.get("targetQuarter"):
        obs = p.get("observed", {})
        cl = obs.get("climate", {})
        w = watch(rec["origin"], (obs.get("hungerRegional") or {}).get("value"), cl.get("palayProductionYoY"),
                  cl.get("cornProductionYoY"))
        return {**w, "issueDate": rec["origin"], "targetQuarter": quarter}
    if not INPUTS.exists():
        return None
    row = _inputs(str(INPUTS), INPUTS.stat().st_mtime_ns).get((quarter, code))
    if row is None:
        return None
    w = watch(row["issue"], row["latest_hunger"], row["palay_yoy_known"], row["corn_yoy_known"])
    return {**w, "issueDate": row["issue"], "targetQuarter": quarter}

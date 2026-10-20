"""
E67 (AIPHEED_LEAD2_MODEL=e67 only): serving disclosure beside the E66 layered Lead-2 system.

Numbers are unchanged: e67 serves the E58 record (E56-TUNED LightGBM, Lead-2, E58-EW warning) with the E66 Climate
Food-Stress Watch and exact LGU ranks. E67 adds three things, all read from data/e67/e67_disclosure.json, which is
built only from the E67 experiment tables (aipheed-backend-aligned/experiments/E67_Lead2_Best_Model_Objectives_1_4,
runner/r5_build_disclosure.py):
  * modelIdentity: which model, mode, issue date and target produced the number, and its measured Lead-2 evidence;
  * triggerCoverage: per trigger group, what the model receives, how current and complete it is at the issue date, and
    its measured Lead-2 effect (E67 R1 ablation), so missing or thin data is never read as absence of risk;
  * a plain explanation when the score is LOW while a climate watch is in force: the projected food inflation against
    the province's HIGH line, and that the score stays LOW with any trigger group removed.
No probability, decision, colour or rank is changed.
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
from pathlib import Path

DISCLOSURE = Path(os.getenv("AIPHEED_E67_DISCLOSURE", "data/e67/e67_disclosure.json"))


class DisclosureError(RuntimeError):
    pass


@functools.lru_cache(maxsize=2)
def _load(path: str, mtime_ns: int) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    body = {k: v for k, v in d.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != d.get("content_sha256"):
        raise DisclosureError("E67 disclosure failed its integrity check")
    return d


def disclosure() -> dict | None:
    if not DISCLOSURE.exists():
        return None
    return _load(str(DISCLOSURE), DISCLOSURE.stat().st_mtime_ns)


def model_identity(rec: dict, quarter: str, issued: str, config: int | None = None) -> dict:
    d = disclosure() or {}
    p = next(iter(rec.get("provinces", {}).values()), {})
    if quarter == rec.get("targetQuarter") or config is None:
        served = (p.get("forecast") or {}).get("servedModel") or rec.get("modelFamily") or "E56 LightGBM"
    else:                                 # an earlier issue selected its own configuration (E56 nested selection)
        served = f"E56 LightGBM food-insecurity model (E56-TUNED, configuration {config})"
    return {"servingMode": "e67", "modelVersion": str(rec.get("modelVersion", "")), "servedModel": served,
            "lead": int(rec.get("lead", 2)), "issued": issued, "targetQuarter": quarter,
            "evidenceStatus": d.get("evidenceStatus", "not validated"),
            "lead2Accuracy": d.get("lead2Accuracy", "not available")}


def _low_text(quarter: str, name: str, row: dict) -> str:
    return (f"Why the score is LOW although a climate watch is in force: the model expects {name}'s food inflation in "
            f"{quarter} at about {row['foodProjection']:.1f}%, below its HIGH line of {row['foodThreshold']:.1f}%, and food "
            f"prices rising {abs(row['gapProjection']):.1f} points {'slower' if row['gapProjection'] < 0 else 'faster'} than "
            f"all prices (HIGH line {row['gapThreshold']:+.1f}). The price part stays at or below "
            f"{row['maxPricePartAnyAblation']:.0%} even with any one trigger group removed (E67). The model sees El Nino only "
            "through observed conditions, so possible El Nino effects on rice and vegetable prices are not in this score.")


def for_summary(rec: dict, quarter: str, province_code: str | None, kind: str, result: str,
                cfsw: dict | None) -> dict | None:
    """E67 additions to the plain summary of an issued or earlier Lead-2 forecast; None for back-tests."""
    if kind not in ("forecast", "earlier_forecast"):
        return None
    d = disclosure()
    if d is None:
        return None
    low = d.get("lowUnderWatch", {}).get(quarter, {})
    issued, config = None, None
    parts = []
    if province_code:
        name = rec.get("provinces", {}).get(province_code, {}).get("name")
        row = low.get(name)
        issued, config = (row["issueDate"], row.get("config")) if row else (None, None)
        watch_on = bool(cfsw and str(cfsw.get("level", "")).startswith("CLIMATE WATCH"))
        if row and result == "LOW" and watch_on:
            parts.append(_low_text(quarter, name, row))
    else:
        rows = list(low.values())
        issued, config = (rows[0]["issueDate"], rows[0].get("config")) if rows else (None, None)
        if rows and result == "LOW" and cfsw and cfsw.get("sentence"):
            parts.append("Why the scores are LOW although a climate watch is in force: projected food inflation is below "
                         "every province's HIGH line, and the price part stays low with any one trigger group removed (E67); "
                         "the model sees El Nino only through observed conditions.")
    cov = d["triggerCoverage"]
    gaps = [g["label"] for g in cov if g["missingAtIssue"]]
    parts.append("Data limits: Fish Kill uses fisheries production (no fish-kill event series); Employment and OFW "
                 "figures are national" + (f"; {', '.join(gaps)} inputs are missing at the issue date and are treated "
                                           "as unknown, not as no risk" if gaps else "") +
                 "; in the Lead-2 back-test, removing any one trigger group made no measurable difference (E67).")
    if issued is None:
        issued = rec.get("origin") if quarter == rec.get("targetQuarter") else ""
    ident = model_identity(rec, quarter, issued or "", config)
    parts.append(f"Model: {ident['servedModel']}, Lead-2, issued {ident['issued']}; {ident['lead2Accuracy']}")
    return {"sentence": " ".join(parts), "modelIdentity": ident, "triggerCoverage": cov}

"""
app/quarterly/preview.py
------------------------
The lead-2 (two-quarter-ahead) row as a labelled experimental preview, behind AIPHEED_LEAD2_PREVIEW (default on since
the final integration; =0 turns it off).

Algorithm 3 returns a Maximum Reliable Lead Time of 1 quarter, so the lead-2 row is below the 75% target. With the
flag on it is served and selectable, and the dashboard opens on it (defaultQuarter in /quarters and /config, by the
researchers' decision), but it is never an alert and never the other defaults (current quarter, forecast target,
quarter resolution, PDF, LGU ranking; app/quarterly/target.default_lead). Every response about its quarter carries
isPreview / belowAccuracyTarget / previewNote. The note is composed from the record's own lead-2 evaluation
(validation.next_quarter_evaluation), never typed in.
"""
from __future__ import annotations

from app.quarterly.target import lead2_preview
from app.quarterly.verdicts import TARGET

LEAD2_KEYS = ("E55", "E38-LGBM")            # the served lead-2 model of the E53 / E49 records (verdicts.py)


def _evaluation(rec: dict) -> dict | None:
    rows = {r.get("key"): r for r in ((rec.get("validation") or {}).get("next_quarter_evaluation") or {}).get("rows", [])}
    m = next((rows[k] for k in LEAD2_KEYS if k in rows), None)
    if m is None:
        return None
    pers = (rows.get("B1_PERSISTENCE") or {}).get("accuracy")
    return {"accuracy": m["accuracy"], "correct": m.get("correct"), "n": m.get("n"), "persistence": pers}


def compose_note(rec: dict) -> tuple[str, bool | None]:
    """(previewNote, belowAccuracyTarget) from the record's lead-2 numbers."""
    ev = _evaluation(rec)
    if ev is None:
        return ("Experimental two-quarter-ahead preview; no development accuracy is recorded for it. Not a validated "
                "forecast."), None
    acc, pers = ev["accuracy"], ev["persistence"]
    below = acc < TARGET
    parts = [f"Development accuracy {acc:.3f}", f"{'below' if below else 'at or above'} the 75% target"]
    if pers is not None:
        parts.append(f"{'below' if acc < pers else 'not below'} persistence ({pers:.3f})")
    body = ", ".join(parts[:2]) + (f" and {parts[2]}" if len(parts) > 2 else "")
    return f"Experimental two-quarter-ahead preview. {body}; not a validated forecast.", below


def preview_row(quarter: str) -> dict | None:
    """The served lead-2 row of `quarter`, with the flag on; otherwise None."""
    if not lead2_preview():
        return None
    from app.ml.inference import e31_engine as E31

    return next((q for q in E31.served_rows() if q["quarter"] == quarter and q.get("lead", 1) >= 2), None)


def default_quarter() -> str | None:
    """The quarter the dashboard opens on with the flag on: the newest served lead-2 (preview) quarter. None with the
    flag off or when the record has no lead-2 row."""
    if not lead2_preview():
        return None
    from app.ml.inference import e31_engine as E31

    rows = [q["quarter"] for q in E31.served_rows() if q.get("lead", 1) >= 2]
    return max(rows) if rows else None


def fields(quarter: str | None) -> dict:
    """Response fields for a quarter. Flag off: {} (responses unchanged). Flag on: isPreview for every quarter;
    belowAccuracyTarget and previewNote for the preview quarter."""
    if not lead2_preview() or quarter is None:
        return {}
    if preview_row(quarter) is None:
        return {"isPreview": False}
    from app.ml.inference import e31_engine as E31

    note, below = compose_note(E31.record())
    return {"isPreview": True, "belowAccuracyTarget": below, "previewNote": note}

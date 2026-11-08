"""
app/quarterly/self_description.py
---------------------------------
The served engine's name and "why served" text, composed from the active record at serving time. Each record's
stored text dates from when it was built: the E49 record calls itself a preview ("the official system serves E36"),
and the E53 record says "the default system serves E49", which stopped being true when E53 became the default (final
integration). The record files are protected and are not changed: like the 75% verdict (app.quarterly.verdicts), the
text is composed from the record's own numbers when it is served, and names the record actually served.

On by default; AIPHEED_COMPOSED_SELF_DESCRIPTION=0 serves the stored text unchanged.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from app.quarterly.verdicts import verdict_from_record

DEFAULT_RECORD = "e53"                     # app.ml.inference.e31_engine.DEFAULT_RECORD
INPUT_GROUPS = [("SWS hunger inputs", lambda f: f.startswith("H_")),
                ("the last published label", lambda f: f == "y_last"),
                ("provincial food and rice price inputs (PSA CPI)", lambda f: f in ("D_last", "Dnow", "rice_rel")),
                ("news inputs (validated titles and the food-stress score)", lambda f: f.startswith(("news_", "fssi"))),
                ("the five trigger proportions", lambda f: f.startswith("trig_")),
                ("measured driver conditions", lambda f: f.startswith("cond_"))]


def enabled() -> bool:
    return os.getenv("AIPHEED_COMPOSED_SELF_DESCRIPTION", "1").strip() != "0"


def _listed(items: list[str]) -> str:
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else "".join(items)


def _significantly_better(rec: dict) -> list[str]:
    pv = ((rec.get("validation") or {}).get("model_evaluation") or {}).get("paired_vs_baselines") or {}
    return sorted(k for k, v in pv.items() if (v.get("holm") is not None and v["holm"] < 0.05
                                               and (v.get("mean_brier_gain_vs_ref") or 0) > 0))


def compose(rec: dict, record_key: str) -> dict:
    """The served_engine block with name, why_served and evidence_status composed from the record. Other keys
    (version, file, sha256, config) are the record's own."""
    se = dict(rec.get("served_engine") or {})
    is_default = record_key == DEFAULT_RECORD
    name = re.sub(r"\s*-\s*PREVIEW\s*$", "", se.get("name", "")) if is_default else se.get("name", "")
    feats = (se.get("config") or {}).get("features") or []
    groups = [g for g, test in INPUT_GROUPS if any(test(f) for f in feats)]
    calibrated = is_calibrated(record_key)

    parts = ["Served by default." if is_default else
             f"Preview, served only when AIPHEED_RECORD={record_key}; the default serves the "
             f"{DEFAULT_RECORD.upper()} record."]
    parts.append(f"LightGBM with {len(feats)} inputs: {_listed(groups)}." if groups else "LightGBM.")
    if calibrated:
        parts.append("Probabilities are calibrated by shrinkage toward the training base rate; driver shares come "
                     "from the LightGBM before calibration.")
    v = verdict_from_record(rec.get("validation") or {})
    me = {r.get("key"): r for r in ((rec.get("validation") or {}).get("model_evaluation") or {}).get("rows", [])}
    m = me.get("E36-LGBM")
    better = _significantly_better(rec)
    if m and v:
        lo, hi = m["accuracy_ci95"]
        parts.append(f"One-quarter-ahead accuracy {m['accuracy_lead1']:.3f} ({m['correct']}/{m['n']}) on development "
                     f"dates; the 75% target is {'demonstrated' if v['demonstrated'] else 'not demonstrated'} "
                     f"(95% date-bootstrap interval {lo:.3f} to {hi:.3f}).")
    parts.append("No baseline is beaten significantly." if not better else
                 f"Significantly better than: {', '.join(better)} (Holm p < 0.05).")
    se["name"] = name
    se["why_served"] = " ".join(parts)
    se["evidence_status"] = (("EXPERIMENTAL" if is_default else "EXPERIMENTAL / PREVIEW")
                             + (" (not validated: no baseline is beaten significantly; development dates only)"
                                if not better else " (development dates only)"))
    return se


def is_calibrated(record_key: str) -> bool:
    """True when the record's model folder holds a shrinkage (C2) calibration file (E49, E53; not E36, E48)."""
    folder = Path(f"data/{record_key}/model")
    return folder.exists() and any(folder.glob("*_C2_*.json"))


def served_engine(rec: dict, record_key: str) -> dict:
    """What the serving layer shows: the composed block (default), the stored one with the flag set to 0."""
    return compose(rec, record_key) if enabled() else (rec.get("served_engine") or {})


def active_record_key() -> str:
    from app.ml.inference import e31_engine as E31

    return Path(E31.RECORD_PATH).parent.name

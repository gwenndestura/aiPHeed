"""
app/api/v1/fpp.py
-----------------
Label v2, "Food Price Pressure (exploratory)", served only when LABEL_VERSION=v2. The default (v1) dashboard is not
changed. Every response carries the note that the index measures food price pressure, not food insecurity, and
that its rule is a tool-adopted default, not adviser-endorsed or validated.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

router = APIRouter()
RECORD = Path(os.getenv("AIPHEED_FPP_RECORD", "data/fpp/fpp_record.json"))
PDF = Path(os.getenv("AIPHEED_FPP_PDF", "data/fpp/aiPHeed_Food_Price_Pressure_exploratory.pdf"))


def label_version() -> str:
    return os.getenv("LABEL_VERSION", "v1").lower()


def _record() -> dict:
    if label_version() != "v2":
        raise HTTPException(status_code=404, detail="Label v2 (Food Price Pressure, exploratory) is not enabled. "
                                                    "The default label is v1; set LABEL_VERSION=v2 to serve it.")
    if not RECORD.exists():
        raise HTTPException(status_code=404, detail="no Food Price Pressure record has been generated")
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != rec.get("content_sha256"):
        raise HTTPException(status_code=500, detail="Food Price Pressure record failed its integrity check")
    return rec


@router.get("/fpp/record")
def fpp_record():
    return _record()


@router.get("/fpp/summary")
def fpp_summary():
    rec = _record()
    return {k: rec[k] for k in ("name", "label_version", "note", "status", "forecast_origin", "forecasts",
                                "evaluation", "limitations", "content_sha256")}


@router.get("/fpp/report.pdf")
def fpp_report():
    rec = _record()
    if not PDF.exists():
        raise HTTPException(status_code=404, detail="no Food Price Pressure PDF has been rendered")
    b = PDF.read_bytes()
    m = re.search(rb"/Subject \(([0-9a-f]{64})\)", b)
    if not m or m.group(1).decode() != rec["content_sha256"]:
        raise HTTPException(status_code=409, detail="PDF does not match the current Food Price Pressure record")
    return Response(content=b, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="aiPHeed_Food_Price_Pressure_exploratory.pdf"',
                             "X-Record-SHA256": rec["content_sha256"], "X-Label-Note": "food price pressure, not food "
                             "insecurity; tool-adopted default rule; not adviser-endorsed or validated"})

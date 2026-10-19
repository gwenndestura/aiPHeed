"""E62 r7 helper: serve the backend on a port, either as it is ("after") or with the HEAD (pre-E61) record loader
restored at runtime ("before": re-read and re-hash the record on every call). Used only for measurement.

    cd backend && venv/Scripts/python.exe -B <this file> after|before <port>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, ".")
from app.ml.inference import e41_lead2 as L2  # noqa: E402


def head_record() -> dict:
    path = {"e42": L2.RECORD_E42, "e43": L2.RECORD_E43, "e44": L2.RECORD_E44, "e46": L2.RECORD_E46, "e52": L2.RECORD_E52,
            "e53": L2.RECORD_E53, "e55": L2.RECORD_E55, "e56": L2.RECORD_E56, "e58": L2.RECORD_E58}.get(L2.mode(), L2.RECORD)
    if not path.exists():
        raise L2.RecordError(f"no {L2.mode().upper()} record")
    rec = json.loads(Path(path).read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != rec.get("content_sha256"):
        raise L2.RecordError("record failed its integrity check")
    return rec


if __name__ == "__main__":
    variant, port = sys.argv[1], int(sys.argv[2])
    if variant == "before":
        L2.record = head_record
    from app.main import app  # noqa: E402
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

"""
Write-once forecast store. One JSON file per (artifact hash, data vintage, issue date), the only cache key: a
different model, data release or issue date can never be served from another's file. The API only reads these files.

    python -m app.forecasting.store run 2026-10-01 data/forecasting/artifacts/seas_llm_2026-10-01.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from app.forecasting import inference as I
from app.forecasting import sws as T

STORE = Path(__file__).resolve().parents[2] / "data" / "forecasting" / "forecasts"


def key(records: list[dict]) -> str:
    r = records[0]
    return f"{r['artifact_sha256'][:16]}_{r['data_vintage_published']}_{r['issue_date']}"


def save(records: list[dict]) -> Path:
    STORE.mkdir(parents=True, exist_ok=True)
    out = STORE / f"{key(records)}.json"
    body = {"key": key(records), "records": records}
    text = json.dumps(body, indent=1, sort_keys=True) + "\n"
    if out.exists():
        if out.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"{out.name} exists with different content: the store is write-once")
        return out
    out.write_text(text, encoding="utf-8", newline="\n")
    return out


def latest(issue: date | None = None) -> dict | None:
    """The stored forecast for an issue date (or the most recent issue), or None."""
    files = sorted(STORE.glob("*.json")) if STORE.exists() else []
    bodies = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    if issue is not None:
        bodies = [b for b in bodies if b["records"][0]["issue_date"] == issue.isoformat()]
    if not bodies:
        return None
    return max(bodies, key=lambda b: (b["records"][0]["issue_date"], b["records"][0]["data_vintage_published"]))


def digest(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "run":
        recs = I.forecast(date.fromisoformat(sys.argv[2]), Path(sys.argv[3]), T.SWS_ROUNDS)
        print(save(recs))
    else:
        sys.exit("usage: python -m app.forecasting.store run YYYY-MM-DD <artifact.json>")

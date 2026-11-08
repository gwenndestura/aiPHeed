"""
Write-once v2 forecast store: one JSON file per (artifact hash, data vintage, issue date), the only cache key. The API
only reads these files.

    python -m app.forecasting.v2.store run 2026-10-01 data/forecasting/artifacts/v2_2026-10-01.json
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from app.forecasting import sws as T
from app.forecasting.store import key
from app.forecasting.v2 import inference as I

STORE = Path(__file__).resolve().parents[3] / "data" / "forecasting" / "forecasts_v2"


def save(records: list[dict], store: Path = STORE) -> Path:
    store.mkdir(parents=True, exist_ok=True)
    out = store / f"{key(records)}.json"
    text = json.dumps({"key": key(records), "records": records}, indent=1, sort_keys=True) + "\n"
    if out.exists():
        if out.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"{out.name} exists with different content: the store is write-once")
        return out
    out.write_text(text, encoding="utf-8", newline="\n")
    return out


def latest(issue: date | None = None, store: Path = STORE) -> dict | None:
    bodies = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(store.glob("*.json"))] if store.exists() else []
    if issue is not None:
        bodies = [b for b in bodies if b["records"][0]["issue_date"] == issue.isoformat()]
    if not bodies:
        return None
    return max(bodies, key=lambda b: (b["records"][0]["issue_date"], b["records"][0]["data_vintage_published"]))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "run":
        print(save(I.forecast(date.fromisoformat(sys.argv[2]), Path(sys.argv[3]), T.SWS_ROUNDS)))
    else:
        sys.exit("usage: python -m app.forecasting.v2.store run YYYY-MM-DD <artifact.json>")

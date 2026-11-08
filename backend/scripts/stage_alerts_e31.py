"""Stage the E31 early-warning alert candidates (app/quarterly/alerts_e31.py) for DA administrator review.

    python scripts/stage_alerts_e31.py [--dry-run]

Idempotent. Nothing is published: a staged alert becomes public only after an administrator confirms it."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.database import AsyncSessionLocal  # noqa: E402
from app.ml.inference.e31_engine import record  # noqa: E402
from app.quarterly.alerts_e31 import candidates, stage  # noqa: E402


async def main(dry: bool):
    rec = record()
    if dry:
        print(json.dumps([{k: c[k] for k in ("quarter", "province_code", "alert_reason")} for c in candidates(rec)], indent=1))
        return
    async with AsyncSessionLocal() as db:
        res = await stage(db, rec)
    print(json.dumps({"staged": len(res["staged"]), "already_present": len(res["existing"]),
                      "items": [{k: c[k] for k in ("quarter", "province_code", "alert_reason")} for c in res["staged"]]},
                     indent=1))


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))

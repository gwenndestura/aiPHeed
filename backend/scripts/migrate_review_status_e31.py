"""Map review_records.status from the pre-E31 main-backend vocabulary to the E31 one (Figure 3.6.3).

    Approved -> Published          Rejected -> Pending (rejection_reason kept, so the row stays withheld)
    Staged   -> Staged             Pending / Published / Archived -> unchanged

    python scripts/migrate_review_status_e31.py            # dry run: counts only
    python scripts/migrate_review_status_e31.py --apply    # writes (back up the database first)

Uses DATABASE_URL (app.config). Idempotent. Never run it against a database you have not backed up.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402

from app.db.database import AsyncSessionLocal  # noqa: E402

MAP = {"Approved": "Published", "Rejected": "Pending"}


async def main(apply: bool):
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text("SELECT status, COUNT(*) FROM review_records GROUP BY status"))).all()
        print("before:", dict(rows))
        todo = {k: v for k, v in dict(rows).items() if k in MAP}
        if not todo:
            print("nothing to migrate")
            return
        if not apply:
            print("dry run; would map", {f"{k}->{MAP[k]}": v for k, v in todo.items()})
            return
        for old, new in MAP.items():
            await db.execute(text("UPDATE review_records SET status = :n WHERE status = :o"), {"n": new, "o": old})
        await db.commit()
        print("after:", dict((await db.execute(text("SELECT status, COUNT(*) FROM review_records GROUP BY status"))).all()))


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))

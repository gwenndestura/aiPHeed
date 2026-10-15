"""
app/services/review.py
-----------------------
The publication pipeline, implementing the forecast state diagram of
Figure 3.6.3.

    PENDING  --forecast complete-->  STAGED  --admin accepts-->  PUBLISHED
       ^                                |                            |
       +--------- admin rejects --------+         next quarter       v
                                                              ARCHIVED

A record enters PENDING when the pipeline starts and moves to STAGED once its
forecast exists. An administrator's acceptance moves it to PUBLISHED, making it
visible on the dashboard; a rejection returns it to PENDING. A PUBLISHED record
becomes ARCHIVED when a later quarter publishes, and stays reachable through the
historical forecasts endpoint.

A rejection has a public effect -- that province greys out on the map and its
forecast stops resolving -- so the transition is recorded with an actor, a
reason and a timestamp, and the reason stays on the PENDING row. A pending row
carrying a rejection reason is what "withheld" means publicly; a pending row
without one is simply awaiting its forecast.

This two-step review is what guarantees no forecast reaches the public
dashboard without human decision-making (Section 3.6).

Rows are seeded lazily from real model output the first time a quarter is
opened, rather than generated from a seed like the mock console did. The score
is snapshotted onto the row so the queue keeps showing what the reviewer
actually acted on even if the model is later retrained.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminUser, AuditRecord, ReviewRecord
from app.services import dashboard as svc
from app.services import reference as ref

logger = logging.getLogger(__name__)

PENDING, STAGED, PUBLISHED, ARCHIVED = "Pending", "Staged", "Published", "Archived"
STATUSES = (PENDING, STAGED, PUBLISHED, ARCHIVED)

REJECTION_REASONS = (
    "Data quality issue",
    "Insufficient signal / limited articles",
    "Conflicts with field intelligence",
    "Model anomaly / outlier prediction",
    "Sensitive context - withhold publication",
    "Other",
)


class ReviewError(Exception):
    """400 — the requested transition is not valid."""

    def __init__(self, message: str, code: str = "invalid_transition"):
        super().__init__(message)
        self.code = code


class ReviewNotFound(Exception):
    """404 — no such review item."""


def review_id(province_id: str, quarter: str) -> str:
    """Deterministic, so seeding a quarter twice is a no-op."""
    return f"rv_{quarter.replace('-', '')}_{province_id}"


async def ensure_rows(db: AsyncSession, quarter: str) -> None:
    """
    Seed the quarter's records and advance them to STAGED once scored.

    A row is created PENDING -- the state Figure 3.6.3 enters on the pipeline
    start command -- and moves to STAGED as soon as a forecast exists for it,
    which for a lazily seeded quarter is immediately.

    Existing rows are left alone: re-seeding must never reset a decision an
    admin already made, nor lift a rejection.
    """
    quarter = svc.resolve_quarter(quarter)
    existing = set(
        (await db.scalars(
            select(ReviewRecord.province_id).where(ReviewRecord.quarter == quarter)
        )).all()
    )
    missing = [p for p in svc.province_summary(quarter) if p["id"] not in existing]
    if not missing:
        return

    for province in missing:
        db.add(ReviewRecord(
            id=review_id(province["id"], quarter),
            province_code=province["provinceCode"],
            province_id=province["id"],
            province_name=province["name"],
            quarter=quarter,
            risk_score=province["riskScore"],
            risk_level=province["riskLevel"],
            # PENDING on creation, STAGED once the forecast is attached.
            status=STAGED if province["riskScore"] is not None else PENDING,
        ))
    await db.commit()
    logger.info("review: seeded %d rows for %s", len(missing), quarter)


async def list_items(
    db: AsyncSession,
    quarter: str | None = None,
    status: str | None = None,
) -> list[ReviewRecord]:
    """The review queue, newest quarter first then by risk descending."""
    if quarter:
        await ensure_rows(db, quarter)

    query = select(ReviewRecord)
    if quarter:
        query = query.where(ReviewRecord.quarter == quarter)
    if status:
        if status not in STATUSES:
            raise ReviewError(
                f"Unknown status '{status}'. Expected one of {', '.join(STATUSES)}.",
                code="unknown_status",
            )
        query = query.where(ReviewRecord.status == status)

    rows = list((await db.scalars(query)).all())
    rows.sort(key=lambda r: (ref.quarter_index(r.quarter), r.risk_score), reverse=True)
    return rows


async def get_item(db: AsyncSession, item_id: str) -> ReviewRecord:
    row = await db.scalar(select(ReviewRecord).where(ReviewRecord.id == item_id))
    if row is None:
        raise ReviewNotFound(f"No review item '{item_id}'.")
    return row


async def _audit(
    db: AsyncSession,
    user: AdminUser,
    action: str,
    row: ReviewRecord,
    reason: str | None = None,
    notes: str | None = None,
) -> None:
    """Written in the same transaction as the change, so the two cannot drift."""
    db.add(AuditRecord(
        actor_id=user.id,
        actor_email=user.email,
        action=action,
        subject_type="review",
        subject_id=row.id,
        province_id=row.province_id,
        quarter=row.quarter,
        reason=reason,
        notes=notes,
    ))


async def approve(db: AsyncSession, item_id: str, user: AdminUser) -> ReviewRecord:
    """Accept a staged forecast: STAGED -> PUBLISHED, and archive what it supersedes."""
    row = await get_item(db, item_id)
    row.status = PUBLISHED
    row.rejection_reason = None
    row.rejection_notes = None
    row.updated_by = user.id
    row.updated_by_name = user.full_name
    await _audit(db, user, "approve", row)
    await _archive_superseded(db, row)
    await db.commit()
    await db.refresh(row)
    return row


async def _archive_superseded(db: AsyncSession, row: ReviewRecord) -> None:
    """
    A PUBLISHED record moves to ARCHIVED when a later quarter publishes for the
    same province. Archived rows stay in the table and stay reachable through
    the historical forecasts endpoint -- the previous version is replaced on the
    dashboard, not deleted.
    """
    published = list((await db.scalars(
        select(ReviewRecord).where(
            ReviewRecord.province_id == row.province_id,
            ReviewRecord.status == PUBLISHED,
        )
    )).all())
    now = ref.quarter_index(row.quarter)
    for other in published:
        if other.id != row.id and ref.quarter_index(other.quarter) < now:
            other.status = ARCHIVED


async def reject(
    db: AsyncSession,
    item_id: str,
    user: AdminUser,
    reason: str,
    notes: str | None = None,
) -> ReviewRecord:
    """
    Withhold a forecast from publication.

    The reason is required and constrained: a rejection removes a number the
    public would otherwise see, and "why" has to survive the person who did it.
    """
    if reason not in REJECTION_REASONS:
        raise ReviewError(
            f"'{reason}' is not a recognised rejection reason.",
            code="unknown_reason",
        )
    row = await get_item(db, item_id)
    # Figure 3.6.3: rejection returns the record to PENDING. The reason stays on
    # the row, which is what marks it withheld rather than merely unscored.
    row.status = PENDING
    row.rejection_reason = reason
    row.rejection_notes = notes
    row.updated_by = user.id
    row.updated_by_name = user.full_name
    await _audit(db, user, "reject", row, reason=reason, notes=notes)
    await db.commit()
    await db.refresh(row)
    return row


async def undo(db: AsyncSession, item_id: str, user: AdminUser) -> ReviewRecord:
    """Return a published or rejected record to STAGED, clearing any rejection."""
    row = await get_item(db, item_id)
    if row.status == STAGED:
        raise ReviewError(
            f"{row.province_name} {row.quarter} is already Staged; nothing to undo.",
            code="already_staged",
        )
    previous = f"{row.status} (rejected)" if row.rejection_reason else row.status
    row.status = STAGED
    row.rejection_reason = None
    row.rejection_notes = None
    row.updated_by = user.id
    row.updated_by_name = user.full_name
    await _audit(db, user, "undo", row, notes=f"was {previous}")
    await db.commit()
    await db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Rejections — the public view of the same rows
# ---------------------------------------------------------------------------

async def list_rejections(db: AsyncSession, quarter: str | None = None) -> list[ReviewRecord]:
    """
    Records an administrator has withheld: PENDING rows carrying a rejection
    reason. A PENDING row without one is merely awaiting its forecast and is
    not a rejection.
    """
    query = select(ReviewRecord).where(
        ReviewRecord.status == PENDING,
        ReviewRecord.rejection_reason.is_not(None),
    )
    if quarter:
        query = query.where(ReviewRecord.quarter == quarter)
    rows = list((await db.scalars(query)).all())
    rows.sort(key=lambda r: ref.quarter_index(r.quarter), reverse=True)
    return rows


async def rejected_pairs(db: AsyncSession, quarter: str | None = None) -> set[tuple[str, str]]:
    """(province_id, quarter) pairs currently withheld."""
    return {(r.province_id, r.quarter) for r in await list_rejections(db, quarter)}


async def is_rejected(db: AsyncSession, province_id: str, quarter: str) -> ReviewRecord | None:
    return await db.scalar(
        select(ReviewRecord).where(
            ReviewRecord.province_id == province_id,
            ReviewRecord.quarter == quarter,
            ReviewRecord.status == PENDING,
            ReviewRecord.rejection_reason.is_not(None),
        )
    )


async def restore(
    db: AsyncSession,
    province_id: str,
    quarter: str,
    user: AdminUser,
) -> ReviewRecord:
    """Lift a rejection so the forecast publishes again."""
    row = await is_rejected(db, province_id, quarter)
    if row is None:
        raise ReviewNotFound(
            f"No active rejection for {province_id} in {quarter}."
        )
    row.status = STAGED
    row.rejection_reason = None
    row.rejection_notes = None
    row.updated_by = user.id
    row.updated_by_name = user.full_name
    await _audit(db, user, "restore", row)
    await db.commit()
    await db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

async def list_audit(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AuditRecord], int]:
    total = len(list((await db.scalars(select(AuditRecord.id))).all()))
    rows = list((await db.scalars(
        select(AuditRecord)
        .order_by(AuditRecord.timestamp.desc(), AuditRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).all())
    return rows, total

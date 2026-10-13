"""
app/api/v1/alerts.py
---------------------
Early warning alerts and the review they require.

Rule 7: "An alert will fire when a province's forecast exceeds the rolling
historical threshold. Human confirmation will be required before DA IV-A is
notified." Figure 3.6.3 gives alerts their own path — a detected alert enters
STAGED, and the administrator either confirms it for display or dismisses it,
"in which case it will remain in the records for audit but will not be shown
publicly."

admin_router  (auth: admin)   mounted at /api/v1/admin
    GET  /alerts?status=staged|confirmed|dismissed
    POST /alerts/{id}/confirm
    POST /alerts/{id}/dismiss

public_router (no auth)       mounted at /api/v1
    GET  /alerts        — confirmed alerts only

The public route returns confirmed alerts and nothing else. A staged alert has
not been reviewed and a dismissed one was rejected; neither may reach the
dashboard, which is what makes this a two-step review rather than an automatic
notification.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminUser, AlertRecord, AuditRecord
from app.db.repository.alert_repo import AlertRepository
from app.dependencies import get_db
from app.schemas.alerts import AlertResponse
from app.services.review import ReviewError, ReviewNotFound
from app.services.security import require_admin

logger = logging.getLogger(__name__)

admin_router = APIRouter(dependencies=[Depends(require_admin)])
public_router = APIRouter()

STATUSES = ("staged", "confirmed", "dismissed")


def _state(row: AlertRecord) -> str:
    if row.confirmed:
        return "confirmed"
    return "dismissed" if row.dismissed else "staged"


def _row(record: AlertRecord) -> dict:
    return {
        "id": record.id,
        "quarter": record.quarter,
        "province_code": record.province_code,
        "threshold_exceeded": record.threshold_exceeded,
        "confirmed": record.confirmed,
        "created_at": record.created_at,
    }


async def _get(db: AsyncSession, alert_id: int) -> AlertRecord:
    row = await db.scalar(select(AlertRecord).where(AlertRecord.id == alert_id))
    if row is None:
        raise ReviewNotFound(f"No alert '{alert_id}'.")
    return row


async def _audit(db: AsyncSession, user: AdminUser, action: str,
                 row: AlertRecord, notes: str | None = None) -> None:
    """Written with the change, so the decision and its record cannot drift."""
    db.add(AuditRecord(
        actor_id=user.id,
        actor_email=user.email,
        action=action,
        subject_type="alert",
        subject_id=str(row.id),
        province_id=row.province_code,
        quarter=row.quarter,
        notes=notes,
    ))
    await db.commit()


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@admin_router.get("/alerts", response_model=AlertResponse)
async def list_alerts(
    status: str = Query("staged", pattern="^(staged|confirmed|dismissed)$"),
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """The alert queue, by state. Defaults to what is awaiting review."""
    repo = AlertRepository(db)
    if status == "staged":
        rows = await repo.get_staged()
    elif status == "confirmed":
        rows = await repo.get_confirmed()
    else:
        rows = list((await db.scalars(
            select(AlertRecord).where(AlertRecord.dismissed.is_(True))
        )).all())
    data = [_row(r) for r in rows]
    return AlertResponse(data=data, total=len(data))


@admin_router.post("/alerts/{alert_id}/confirm", response_model=AlertResponse)
async def confirm_alert(
    alert_id: int,
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """
    STAGED → CONFIRMED. The alert becomes visible on the dashboard, and only
    now may the partner agencies be notified (Rule 7).
    """
    row = await _get(db, alert_id)
    if row.dismissed:
        raise ReviewError(
            f"Alert {alert_id} was dismissed; it cannot be confirmed.",
            code="alert_dismissed",
        )
    updated = await AlertRepository(db).confirm(alert_id)
    await _audit(db, user, "confirm_alert", updated)
    logger.info("alert %s confirmed by %s", alert_id, user.email)
    return AlertResponse(data=[_row(updated)], total=1)


@admin_router.post("/alerts/{alert_id}/dismiss", response_model=AlertResponse)
async def dismiss_alert(
    alert_id: int,
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """
    STAGED → DISMISSED. The record stays for audit and is never shown publicly.
    """
    row = await _get(db, alert_id)
    if row.confirmed:
        raise ReviewError(
            f"Alert {alert_id} is already confirmed; it cannot be dismissed.",
            code="alert_confirmed",
        )
    updated = await AlertRepository(db).dismiss(alert_id)
    await _audit(db, user, "dismiss_alert", updated)
    logger.info("alert %s dismissed by %s", alert_id, user.email)
    return AlertResponse(data=[_row(updated)], total=1)


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

@public_router.get("/alerts", response_model=AlertResponse)
async def active_alerts(db: AsyncSession = Depends(get_db)) -> AlertResponse:
    """
    Alerts that have passed administrative review.

    Staged and dismissed alerts are absent by design: no warning reaches the
    public dashboard without a human decision (Section 3.6).
    """
    rows = await AlertRepository(db).get_confirmed()
    data = [_row(r) for r in rows]
    return AlertResponse(data=data, total=len(data))

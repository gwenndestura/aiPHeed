"""
app/api/v1/admin.py
--------------------
The review pipeline and its public face.

admin_router  (auth: admin)   mounted at /api/v1/admin
    GET    /review?quarter=&status=
    POST   /review/{id}/approve
    POST   /review/{id}/reject
    POST   /review/{id}/undo
    DELETE /rejections/{province_id}/{quarter}
    GET    /audit
    GET    /feedback
    GET    /accounts                      pending requests and active admins
    POST   /accounts/{id}/approve         pending_approval -> active (emails the person)
    POST   /accounts/{id}/reject          pending_* -> rejected
    POST   /accounts/{id}/deactivate      active -> deactivated, every session ended
    POST   /pipeline/run
    GET    /pipeline/status

public_router (no auth)       mounted at /api/v1
    GET    /rejections?quarter=
    POST   /feedback

Rejections are public because the map needs them to grey provinces out.
Everything that *changes* one is admin-only.
"""

from __future__ import annotations

import logging

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminUser, AuditRecord, FeedbackRecord, ReviewRecord
from app.dependencies import get_db
from app.schemas.admin import (
    AccountRow,
    AccountsResponse,
    AuditResponse,
    AuditRow,
    Demographics,
    FeedbackCreated,
    FeedbackListResponse,
    FeedbackRow,
    FeedbackSubmit,
    FeedbackSummary,
    RejectionRow,
    RejectionsResponse,
    PipelineRunRequest,
    PipelineRunStatus,
    RejectRequest,
    ReviewItem,
    ReviewListResponse,
)
from app.services import accounts
from app.services import dashboard as svc
from app.services import feedback as fb
from app.services import mailer
from app.services import pipeline_runs as runs
from app.services import reference as ref
from app.services import review as rv
from app.services import security
from app.services.ratelimit import feedback_guard
from app.services.security import forbid_demo, forbid_demo_writes, require_admin
from app.services.review import ReviewError

logger = logging.getLogger(__name__)

# require_admin: 401/403 for anyone who is not a signed-in admin.
# forbid_demo_writes: the demo account is view-only on every route here,
# present and future (403 on anything but GET/HEAD/OPTIONS).
admin_router = APIRouter(dependencies=[Depends(require_admin), Depends(forbid_demo_writes)])
public_router = APIRouter()


# ---------------------------------------------------------------------------
# Serialisers
# ---------------------------------------------------------------------------

def _item(row: ReviewRecord) -> ReviewItem:
    return ReviewItem(
        id=row.id,
        provinceId=row.province_id,
        provinceCode=row.province_code,
        province=row.province_name,
        quarter=row.quarter,
        riskScore=row.risk_score,
        riskLevel=row.risk_level,
        status=rv.api_status(row),
        rejectionReason=row.rejection_reason,
        rejectionNotes=row.rejection_notes,
        updatedAt=row.updated_at,
        updatedBy=row.updated_by,
        updatedByName=row.updated_by_name,
    )


def _rejection(row: ReviewRecord) -> RejectionRow:
    return RejectionRow(
        provinceId=row.province_id,
        province=row.province_name,
        quarter=row.quarter,
        reason=row.rejection_reason,
        notes=row.rejection_notes,
        timestamp=row.updated_at,
    )


DEMO_HIDDEN = "Hidden in the demo account"


def _feedback_row(row: FeedbackRecord, mask_personal: bool = False) -> FeedbackRow:
    """`mask_personal`: the demo account sees no respondent's name, email, agency or designation."""
    hide = (lambda v: DEMO_HIDDEN if v else v) if mask_personal else (lambda v: v)
    return FeedbackRow(
        id=row.id,
        date=row.submitted_at,
        score=row.score,
        susVersion=row.sus_version,
        answers=row.answers,
        demographics=Demographics(
            fullName=hide(row.full_name),
            email=hide(row.email),
            agency=hide(row.agency),
            designation=hide(row.designation),
            age=row.age_band,
            sex=row.sex,
            clientType=row.client_type,
            province=row.province,
            municipality=row.municipality,
        ),
        liked=row.liked,
        improvements=row.improvements,
    )


def _audit_row(row: AuditRecord) -> AuditRow:
    return AuditRow(
        id=row.id,
        actorEmail=row.actor_email,
        actorId=row.actor_id,
        action=row.action,
        subjectType=row.subject_type,
        subjectId=row.subject_id,
        provinceId=row.province_id,
        quarter=row.quarter,
        reason=row.reason,
        notes=row.notes,
        timestamp=row.timestamp,
    )


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

@admin_router.get("/review", response_model=ReviewListResponse)
async def list_review(
    quarter: str | None = Query(None, description="Defaults to the latest scorable quarter"),
    status: str | None = Query(None, description="Staged | Approved | Rejected"),
    db: AsyncSession = Depends(get_db),
) -> ReviewListResponse:
    """
    The review queue.

    Rows are seeded from real model output the first time a quarter is opened,
    and an existing decision is never reset by re-seeding. Omit `quarter` to
    see every quarter at once.
    """
    resolved = svc.resolve_quarter(quarter) if quarter else None
    rows = await rv.list_items(db, quarter=resolved, status=status)
    return ReviewListResponse(
        quarter=resolved,
        status=status,
        statuses=list(rv.API_STATUSES),
        rejectionReasons=list(rv.REJECTION_REASONS),
        data=[_item(r) for r in rows],
    )


@admin_router.post("/review/{item_id}/approve", response_model=ReviewItem)
async def approve(
    item_id: str,
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ReviewItem:
    """Publish this province-quarter."""
    return _item(await rv.approve(db, item_id, user))


@admin_router.post("/review/{item_id}/reject", response_model=ReviewItem)
async def reject(
    item_id: str,
    body: RejectRequest,
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ReviewItem:
    """
    Withhold this province-quarter from the public map.

    Takes effect immediately: /forecast stops resolving for the pair and
    /rejections lists it.
    """
    return _item(await rv.reject(db, item_id, user, body.reason, body.notes))


@admin_router.post("/review/{item_id}/undo", response_model=ReviewItem)
async def undo(
    item_id: str,
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ReviewItem:
    """Return an Approved or Rejected item to Staged."""
    return _item(await rv.undo(db, item_id, user))


@admin_router.delete("/rejections/{province_id}/{quarter}", response_model=ReviewItem)
async def restore(
    province_id: str,
    quarter: str,
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ReviewItem:
    """Lift a rejection so the forecast publishes again."""
    return _item(await rv.restore(db, province_id.lower(), quarter, user))


def _run_status(payload: dict) -> PipelineRunStatus:
    return PipelineRunStatus(
        status=payload["status"],
        running=payload["running"],
        startedAt=payload.get("started_at"),
        startedBy=payload.get("started_by"),
        finishedAt=payload.get("finished_at"),
        error=payload.get("error"),
        lastRun=payload.get("last_run"),
    )


@admin_router.post("/pipeline/run", response_model=PipelineRunStatus, status_code=202)
async def run_pipeline(
    body: PipelineRunRequest,
    user: AdminUser = Depends(require_admin),
) -> PipelineRunStatus:
    """
    Trigger the quarterly cycle (Figure 3.6.1, Run Quarterly Pipeline).

    Collecting that quarter's news and government data is included in the run,
    since no forecast can be produced without it. The cycle takes far longer
    than a request, so this returns 202 immediately and the work continues on a
    worker thread; poll `GET /pipeline/status`.

    Every forecast and alert the run produces is STAGED. Nothing reaches the
    public dashboard until an administrator approves it.
    """
    try:
        payload = runs.start(
            actor_email=user.email,
            skip_collect=body.skipCollect,
            skip_train=body.skipTrain,
            quarter=body.quarter,
        )
    except RuntimeError as exc:
        raise ReviewError(str(exc), code="pipeline_already_running") from exc
    return _run_status(payload)


@admin_router.get("/pipeline/status", response_model=PipelineRunStatus)
async def pipeline_status(
    user: AdminUser = Depends(require_admin),
) -> PipelineRunStatus:
    """State of the current or most recent quarterly cycle."""
    return _run_status(runs.status())


@admin_router.get("/audit", response_model=AuditResponse)
async def audit(
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> AuditResponse:
    """Who changed what, when, and why. Append-only."""
    rows, total = await rv.list_audit(db, page, pageSize)
    return AuditResponse(
        data=[_audit_row(r) for r in rows],
        page=page,
        pageSize=pageSize,
        total=total,
    )


@admin_router.get("/feedback", response_model=FeedbackListResponse)
async def list_feedback(
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FeedbackListResponse:
    """
    Every SUS submission, with aggregates over the whole set.

    Previously each admin saw only what had been submitted from their own
    browser; this is the first view across all respondents.
    """
    rows, total, summary = await fb.listing(db, page, pageSize)
    return FeedbackListResponse(
        summary=FeedbackSummary(**summary),
        questions=list(fb.SUS_QUESTIONS),
        # Respondents' personal details are masked for the demo account here,
        # on the server -- not merely hidden in the page.
        data=[_feedback_row(r, mask_personal=bool(user.is_demo)) for r in rows],
        page=page,
        pageSize=pageSize,
        total=total,
    )


# ---------------------------------------------------------------------------
# Accounts (ACCT-1)
# ---------------------------------------------------------------------------

def _account_row(row: AdminUser, me: AdminUser) -> AccountRow:
    return AccountRow(
        id=row.id,
        email=row.email,
        name=row.full_name,
        office=row.office_unit,
        status=row.status,
        createdAt=row.created_at,
        emailVerifiedAt=row.email_verified_at,
        approvedAt=row.approved_at,
        lastLoginAt=row.last_login_at,
        isDemo=bool(row.is_demo),
        isSelf=row.id == me.id,
    )


async def _account(db: AsyncSession, account_id: int) -> AdminUser:
    row = await db.scalar(select(AdminUser).where(AdminUser.id == account_id))
    if row is None:
        raise accounts.AccountNotFound(f"No account {account_id}.")
    return row


@admin_router.get("/accounts", response_model=AccountsResponse, dependencies=[Depends(forbid_demo)])
async def list_accounts(
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AccountsResponse:
    """Requests waiting for a decision (email verified) and the admins with access."""
    rows = list((await db.scalars(select(AdminUser).order_by(AdminUser.created_at, AdminUser.id))).all())
    # The demo account is listed only while it is enabled.
    rows = [r for r in rows if not security.demo_blocked(r)]
    pending = [_account_row(r, user) for r in rows if r.status == accounts.PENDING_APPROVAL]
    active = [_account_row(r, user) for r in rows if r.status == accounts.ACTIVE]
    return AccountsResponse(pending=pending, active=active, pendingCount=len(pending))


@admin_router.post("/accounts/{account_id}/approve", response_model=AccountRow, dependencies=[Depends(forbid_demo)])
async def approve_account(
    account_id: int,
    background: BackgroundTasks,
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AccountRow:
    """Give a verified request admin access, and tell the person by email."""
    target = await _account(db, account_id)
    if target.status != accounts.PENDING_APPROVAL:
        raise accounts.AccountError("Only accounts waiting for approval can be approved.", "not_pending_approval")
    accounts.set_status(target, accounts.ACTIVE)
    target.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    target.approved_by_id = user.id
    accounts.audit(db, action="account_approved", subject=target, actor=user)
    await db.commit()
    background.add_task(mailer.send_email, *accounts.approved_email(target))
    return _account_row(target, user)


@admin_router.post("/accounts/{account_id}/reject", response_model=AccountRow, dependencies=[Depends(forbid_demo)])
async def reject_account(
    account_id: int,
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AccountRow:
    """Turn down a request. The row is kept for the audit trail; it cannot sign in."""
    target = await _account(db, account_id)
    if target.status not in (accounts.PENDING_APPROVAL, accounts.PENDING_VERIFICATION):
        raise accounts.AccountError("Only pending requests can be rejected.", "not_pending")
    accounts.set_status(target, accounts.REJECTED)
    accounts.audit(db, action="account_rejected", subject=target, actor=user)
    await db.commit()
    return _account_row(target, user)


@admin_router.post("/accounts/{account_id}/deactivate", response_model=AccountRow, dependencies=[Depends(forbid_demo)])
async def deactivate_account(
    account_id: int,
    user: AdminUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AccountRow:
    """
    Remove an admin's access and end every session they have, at once. Not
    your own account: that would lock you out mid-task (and could leave no
    admin at all).
    """
    target = await _account(db, account_id)
    if target.id == user.id:
        raise accounts.AccountError("You cannot deactivate your own account.", "cannot_deactivate_self")
    if target.status != accounts.ACTIVE:
        raise accounts.AccountError("Only active accounts can be deactivated.", "not_active")
    accounts.set_status(target, accounts.DEACTIVATED)
    await security.end_all_sessions(db, target)
    accounts.audit(db, action="account_deactivated", subject=target, actor=user)
    await db.commit()
    return _account_row(target, user)


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

@public_router.get("/rejections", response_model=RejectionsResponse)
async def rejections(
    quarter: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> RejectionsResponse:
    """
    Province-quarters an admin has withheld. No auth: the public map needs it.

    Distinct from a missing forecast -- these were generated and then held
    back, which is why they carry a reason and an actor.
    """
    rows = await rv.list_rejections(db, quarter)
    data = [_rejection(r) for r in rows]
    # AIPHEED_REQUIRE_APPROVAL=1 (default off): province-quarters not yet approved are withheld like rejections.
    rejected = {(r.province_id, r.quarter) for r in rows}
    for slug, q in sorted(await rv.unapproved_pairs(db, quarter) - rejected,
                          key=lambda x: (ref.quarter_index(x[1]), x[0]), reverse=True):
        data.append(RejectionRow(provinceId=slug, province=ref.province_name(slug) or slug, quarter=q,
                                 reason=rv.AWAITING_APPROVAL))
    return RejectionsResponse(quarter=quarter, data=data)


@public_router.post("/feedback", response_model=FeedbackCreated, status_code=201,
                    dependencies=[Depends(feedback_guard)])
async def submit_feedback(
    body: FeedbackSubmit,
    db: AsyncSession = Depends(get_db),
) -> FeedbackCreated:
    """
    Record a SUS response. No auth -- the survey is open to any dashboard user.

    The score returned is the server's own calculation from `answers`.
    """
    record = await fb.create(db, body.model_dump())
    return FeedbackCreated(
        id=record.id,
        date=record.submitted_at,
        score=record.score,
        susVersion=record.sus_version,
    )

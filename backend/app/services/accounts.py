"""
app/services/accounts.py
-------------------------
Admin account lifecycle (QA_REPORT ACCT-1).

    sign-up -> pending_verification --(email link)--> pending_approval
            --(an admin approves)--> active --(an admin deactivates)--> deactivated
    pending_* --(an admin rejects)--> rejected

Only `active` accounts may sign in. `AdminUser.is_active` predates the status
column and is what sign-in, refresh and every request already check, so
set_status() keeps it equal to (status == "active"); nothing else writes either.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import AccountToken, AdminUser, AuditRecord

PENDING_VERIFICATION = "pending_verification"
PENDING_APPROVAL = "pending_approval"
ACTIVE = "active"
REJECTED = "rejected"
DEACTIVATED = "deactivated"
STATUSES = (PENDING_VERIFICATION, PENDING_APPROVAL, ACTIVE, REJECTED, DEACTIVATED)

# Sign-in with the RIGHT password while pending gets a specific message (the
# person already proved they own the account, so this reveals nothing new).
# Rejected and deactivated accounts get the generic error like a wrong password.
PENDING_MESSAGES: dict[str, tuple[str, str]] = {
    PENDING_VERIFICATION: ("email_not_verified", "Verify your email to continue."),
    PENDING_APPROVAL: ("account_pending_approval", "Your account is waiting for approval."),
}


def set_status(user: AdminUser, status: str) -> None:
    """The only way to change an account's status; keeps is_active in step."""
    if status not in STATUSES:
        raise ValueError(f"unknown account status {status!r}")
    user.status = status
    user.is_active = status == ACTIVE


# ---------------------------------------------------------------------------
# Errors the person can act on (400, see app/main.py)
# ---------------------------------------------------------------------------

class AccountError(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


class AccountNotFound(Exception):
    """404: no account with that id."""


# ---------------------------------------------------------------------------
# Single-use link tokens (verification 24 h, password reset 1 h)
# ---------------------------------------------------------------------------

VERIFY_EMAIL = "verify_email"
RESET_PASSWORD = "reset_password"
TOKEN_TTL = {VERIFY_EMAIL: timedelta(hours=24), RESET_PASSWORD: timedelta(hours=1)}

LINK_ERRORS = {
    "link_invalid": "This link is not valid. Request a new one.",
    "link_expired": "This link has expired. Request a new one.",
    "link_used": "This link has already been used. Request a new one if you still need it.",
}


def link_error(code: str) -> AccountError:
    return AccountError(LINK_ERRORS[code], code)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_link_token(db: AsyncSession, user: AdminUser, purpose: str) -> str:
    """
    A new link token for `user`. Any earlier unused token of the same purpose
    stops working, so only the newest emailed link is valid. Only the hash is
    stored; the caller puts the token in the email and commits.
    """
    now = _now()
    await db.execute(
        update(AccountToken)
        .where(AccountToken.user_id == user.id, AccountToken.purpose == purpose, AccountToken.used_at.is_(None))
        .values(used_at=now)
    )
    token = secrets.token_urlsafe(32)  # 256 bits
    db.add(AccountToken(user_id=user.id, purpose=purpose, token_hash=_hash(token),
                        created_at=now, expires_at=now + TOKEN_TTL[purpose]))
    return token


async def redeem_link_token(db: AsyncSession, token: str, purpose: str) -> AdminUser:
    """
    Mark the token used and return its account, or raise link_invalid /
    link_expired / link_used (AccountError). The caller commits.
    """
    row = await db.scalar(
        select(AccountToken).where(AccountToken.token_hash == _hash(token), AccountToken.purpose == purpose)
    )
    if row is None:
        raise link_error("link_invalid")
    if row.used_at is not None:
        raise link_error("link_used")
    if _now() >= row.expires_at:
        raise link_error("link_expired")
    user = await db.scalar(select(AdminUser).where(AdminUser.id == row.user_id))
    if user is None:
        raise link_error("link_invalid")
    row.used_at = _now()
    return user


def link_url(path: str, token: str) -> str:
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}{path}?token={token}"


# ---------------------------------------------------------------------------
# Emails: (to, subject, body) for mailer.send_email
# ---------------------------------------------------------------------------

def verification_email(user: AdminUser, token: str) -> tuple[str, str, str]:
    return (
        user.email,
        "Verify your aiPHeed account email",
        f"Hello {user.full_name},\n\n"
        "Someone (hopefully you) created an aiPHeed administrator account with this "
        "address. To verify the address, open this link within 24 hours:\n\n"
        f"{link_url('/verify-email', token)}\n\n"
        "After you verify it, an administrator will review the request. You will get "
        "another email when the account is approved.\n\n"
        "If you did not sign up, ignore this email; the account will not be activated.\n",
    )


def already_registered_email(user: AdminUser) -> tuple[str, str, str]:
    return (
        user.email,
        "aiPHeed sign-up attempt",
        f"Hello {user.full_name},\n\n"
        "Someone tried to create an aiPHeed administrator account with this address, "
        "but an account for it already exists. No new account was created.\n\n"
        f"If you have forgotten your password, use \"Forgot password?\" on the sign-in "
        f"page: {settings.FRONTEND_BASE_URL.rstrip('/')}/login\n\n"
        "If this was not you, no action is needed.\n",
    )


def reset_email(user: AdminUser, token: str) -> tuple[str, str, str]:
    return (
        user.email,
        "Reset your aiPHeed password",
        f"Hello {user.full_name},\n\n"
        "Someone (hopefully you) asked to reset the password of your aiPHeed "
        "administrator account. To choose a new password, open this link within 1 hour:\n\n"
        f"{link_url('/reset-password', token)}\n\n"
        "Choosing a new password signs you out on every device.\n\n"
        "If you did not ask for this, ignore this email; your password stays the same.\n",
    )


def approved_email(user: AdminUser) -> tuple[str, str, str]:
    return (
        user.email,
        "Your aiPHeed administrator account is approved",
        f"Hello {user.full_name},\n\n"
        "Your aiPHeed administrator account has been approved. You can now sign in:\n\n"
        f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login\n",
    )


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def audit(db: AsyncSession, *, action: str, subject: AdminUser, actor: AdminUser | None = None,
          reason: str | None = None) -> None:
    """
    One audit row for an account event: who (actor; the account itself when
    None), whom (subject_id) and when (the row's timestamp). Never a password
    or a token.
    """
    who = actor or subject
    db.add(AuditRecord(
        actor_id=who.id,
        actor_email=who.email,
        action=action,
        subject_type="account",
        subject_id=str(subject.id),
        reason=reason,
        notes=subject.email if actor is not None else None,
    ))

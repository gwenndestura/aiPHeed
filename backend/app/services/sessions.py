"""
app/services/sessions.py
-------------------------
Refresh tokens: what keeps an admin signed in across a reload, a new tab or a
typed URL, while the access token itself stays in browser memory only.

How it fits together
--------------------
* Sign-in starts a session ("family") and sets a refresh token in an
  httpOnly cookie scoped to POST /api/v1/auth/refresh -- the browser sends it
  nowhere else, and page scripts cannot read it.
* On page load (and when the 1-hour access token expires) the frontend calls
  /auth/refresh. The presented token is ROTATED: it is marked used and a new
  one is set. Only a SHA-256 of each token is stored.
* Idle limit: each refresh extends the session by REFRESH_TOKEN_IDLE_TTL_SECONDS,
  never past REFRESH_TOKEN_MAX_TTL_SECONDS from sign-in.
* Replay: a token that was already rotated and is presented again after
  REUSE_GRACE_SECONDS means it was copied, so the whole family is revoked. The
  grace window covers two tabs loading at the same moment and sending the same
  cookie; the second gets its own new token instead of signing both out.

CSRF
----
Every other state-changing endpoint is authorised by the Authorization header,
which a browser never attaches on its own, so a forged cross-site request
carries no credentials. /auth/refresh is the one endpoint the cookie
authorises, and it is defended three ways: SameSite (Strict by default) keeps
the cookie off cross-site requests; a required custom header
(X-CSRF-Protection) forces a CORS preflight that only allow-listed origins
pass; and a present Origin header must be allow-listed. Even then, the new
access token is in the response body, which a foreign page cannot read.
"""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import AdminUser, RefreshToken
from app.services.security import ForbiddenError

logger = logging.getLogger(__name__)

COOKIE_NAME = "aipheed_refresh"
COOKIE_PATH = "/api/v1/auth/refresh"
CSRF_HEADER = "X-CSRF-Protection"
REUSE_GRACE_SECONDS = 30
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})


class RefreshError(Exception):
    """The refresh token is missing, unknown, expired, revoked or replayed."""

    def __init__(self, message: str, code: str = "session_expired"):
        super().__init__(message)
        self.code = code


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_row(user_id: int, family_id: str, absolute: datetime) -> tuple[str, RefreshToken]:
    token = secrets.token_urlsafe(32)  # 256 bits
    now = _now()
    row = RefreshToken(
        user_id=user_id,
        family_id=family_id,
        token_hash=_hash(token),
        created_at=now,
        expires_at=min(now + timedelta(seconds=settings.REFRESH_TOKEN_IDLE_TTL_SECONDS), absolute),
        absolute_expires_at=absolute,
    )
    return token, row


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

async def start_session(db: AsyncSession, user: AdminUser) -> tuple[str, RefreshToken]:
    """
    New sign-in: a new family and its first refresh token. The caller commits.
    Also drops rows past their maximum lifetime, so the table does not grow.
    """
    await db.execute(
        RefreshToken.__table__.delete().where(RefreshToken.absolute_expires_at < _now())
    )
    absolute = _now() + timedelta(seconds=settings.REFRESH_TOKEN_MAX_TTL_SECONDS)
    token, row = _new_row(user.id, uuid.uuid4().hex, absolute)
    db.add(row)
    return token, row


async def rotate(db: AsyncSession, presented: str) -> tuple[AdminUser, str, RefreshToken]:
    """
    Exchange a refresh token for a new one in the same family. The caller
    commits on success; on failure anything worth keeping (a revoked family)
    is committed here before RefreshError is raised.
    """
    now = _now()
    row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash(presented)))
    if row is None:
        raise RefreshError("Session not found. Sign in again.")
    if row.revoked_at is not None:
        raise RefreshError("Session has been signed out. Sign in again.", code="session_revoked")
    if now >= row.expires_at or now >= row.absolute_expires_at:
        raise RefreshError("Session expired. Sign in again.")
    if row.rotated_at is not None and (now - row.rotated_at).total_seconds() > REUSE_GRACE_SECONDS:
        # Already exchanged, and not a near-simultaneous second tab: someone
        # else holds a copy. End the whole session for everyone holding it.
        await revoke_family(db, row.family_id)
        await db.commit()
        logger.warning("refresh token replayed for user %s; session %s revoked", row.user_id, row.family_id)
        raise RefreshError("Session has been signed out. Sign in again.", code="session_revoked")

    user = await db.scalar(select(AdminUser).where(AdminUser.id == row.user_id))
    if user is None or not user.is_active or (user.is_demo and not settings.ENABLE_DEMO_ACCOUNT):
        await revoke_family(db, row.family_id)
        await db.commit()
        raise RefreshError("Account is no longer active.", code="account_inactive")

    if row.rotated_at is None:
        row.rotated_at = now
    token, new_row = _new_row(user.id, row.family_id, row.absolute_expires_at)
    db.add(new_row)
    return user, token, new_row


async def revoke_family(db: AsyncSession, family_id: str) -> None:
    """End one sign-in session (sign-out). The caller commits."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


async def revoke_all_for_user(db: AsyncSession, user_id: int) -> None:
    """End every session the account has, on every device. The caller commits."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


# ---------------------------------------------------------------------------
# Cookie
# ---------------------------------------------------------------------------

def _secure(request: Request) -> bool:
    """Secure, except over plain http to this machine, where browsers would drop it."""
    if request.url.scheme == "http" and (request.url.hostname or "") in LOCAL_HOSTS:
        return False
    # SameSite=None is only accepted on a Secure cookie.
    return settings.REFRESH_COOKIE_SECURE or settings.REFRESH_COOKIE_SAMESITE == "none"


def set_refresh_cookie(response: Response, request: Request, token: str, row: RefreshToken) -> None:
    max_age = max(0, int((row.expires_at - _now()).total_seconds()))
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=max_age,
        path=COOKIE_PATH,
        httponly=True,
        secure=_secure(request),
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


def clear_refresh_cookie(response: Response, request: Request) -> None:
    # A Set-Cookie applies whatever path the request was for, so this clears
    # the refresh-path cookie from the logout response too.
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        secure=_secure(request),
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------

def _origin_allowed(origin: str, request: Request) -> bool:
    own = f"{request.url.scheme}://{request.url.netloc}"
    if origin == own or origin in settings.cors_origins:
        return True
    return bool(settings.CORS_PREVIEW_REGEX and re.fullmatch(settings.CORS_PREVIEW_REGEX, origin))


def check_refresh_csrf(request: Request) -> None:
    """403 unless the request carries the custom header and, if sent, an allowed Origin."""
    if not request.headers.get(CSRF_HEADER):
        raise ForbiddenError(f"Missing {CSRF_HEADER} header.", code="csrf_failed")
    origin = request.headers.get("Origin")
    if origin and not _origin_allowed(origin, request):
        raise ForbiddenError("Origin not allowed.", code="csrf_failed")

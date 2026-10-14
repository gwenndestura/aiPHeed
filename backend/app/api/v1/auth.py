"""
app/api/v1/auth.py
-------------------
POST /api/v1/auth/login     sign in: access token in the body, refresh cookie set
POST /api/v1/auth/refresh   new access token from the refresh cookie (rotated)
GET  /api/v1/auth/me
POST /api/v1/auth/logout    revoke the access token and the session; clear the cookie

Replaces both client-side login paths. Neither talked to a server: one ignored
the password field entirely, the other compared against a credential compiled
into the JS bundle and printed in the UI. `/admin` was gated by a
sessionStorage flag anyone could set from devtools.

The frontend should call /auth/me on mount rather than trusting its own stored
copy of the session.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import AdminUser, AuditRecord
from app.dependencies import get_db
from app.schemas.admin import LoginRequest, LoginResponse, LogoutResponse, UserOut
from app.services import accounts, security, sessions
from app.services.ratelimit import (
    account_locked,
    clear_login_failures,
    login_guard,
    record_login_failure,
    refresh_guard,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _audit_failed_login(db: AsyncSession, request: Request, email: str, reason: str) -> None:
    """
    Record a refused sign-in. The attempted address and the client IP only --
    never the password. No account id either: the row must not say whether
    the address belongs to a real account.
    """
    db.add(AuditRecord(
        actor_id=None,
        actor_email=email,
        action="login_failed",
        subject_type="session",
        subject_id=None,
        reason=reason,
        notes=f"from {request.client.host}" if request.client else None,
    ))
    await db.commit()


@router.post("/login", response_model=LoginResponse,
             dependencies=[Depends(login_guard)])
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Exchange credentials for a short-lived bearer token.

    Every failure returns the same message. Saying "no such account" would let
    anyone enumerate which DA addresses are registered.
    """
    email = body.email.strip().lower()

    # Too many recent failures for this address: refuse without checking the
    # password, but still pay the hashing cost and give the same answer, so a
    # locked address looks exactly like a wrong password.
    if account_locked(email):
        security.verify_password(body.password, None)
        logger.warning("login refused for %s from %s: account failure limit reached",
                       email, request.client.host if request.client else "?")
        await _audit_failed_login(db, request, email, "account_failure_limit")
        raise security.AuthError("Email or password is incorrect.")

    user = await db.scalar(select(AdminUser).where(AdminUser.email == email))
    password_ok = security.verify_password(body.password, user.password_hash if user else None)

    # Domain is checked at account creation; re-checked here so a row that
    # predates the rule cannot sign in.
    credentials_ok = bool(user and password_ok and security.email_domain_allowed(email))

    # Right password, but the account is not approved yet: say why. Only after
    # the password checks out, so this cannot be used to probe addresses.
    if credentials_ok and user.status in accounts.PENDING_MESSAGES:
        code, message = accounts.PENDING_MESSAGES[user.status]
        await _audit_failed_login(db, request, email, user.status)
        raise security.AuthError(message, code=code)

    # Rejected and deactivated accounts fail exactly like a wrong password.
    if not (credentials_ok and user.is_active):
        record_login_failure(email)
        logger.warning("failed login for %s from %s", email, request.client.host if request.client else "?")
        await _audit_failed_login(db, request, email, "invalid_credentials")
        raise security.AuthError("Email or password is incorrect.")

    clear_login_failures(email)

    if security.needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(body.password)

    refresh_token, refresh_row = await sessions.start_session(db, user)
    token, expires_in, expires_at = security.create_access_token(user, session_id=refresh_row.family_id)
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(AuditRecord(
        actor_id=user.id,
        actor_email=user.email,
        action="login",
        subject_type="session",
        subject_id=None,
    ))
    await db.commit()
    sessions.set_refresh_cookie(response, request, refresh_token, refresh_row)

    return LoginResponse(
        token=token,
        expiresIn=expires_in,
        expiresAt=expires_at,
        user=UserOut(id=user.id, email=user.email, name=user.full_name, role=user.role),
    )


@router.post("/refresh", response_model=LoginResponse,
             responses={204: {"description": "No session to restore"}},
             dependencies=[Depends(refresh_guard)])
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    A new access token from the refresh cookie, which is rotated.

    Called on page load and when the access token expires, so a reload or a
    new tab does not sign the admin out. Requires the X-CSRF-Protection header
    (see app/services/sessions.py).

    No cookie at all is the normal case for a public visitor, so it is 204
    "nothing to restore", not an error (every page load calls this). A cookie
    that is invalid, expired or revoked is 401, and the cookie is cleared.
    """
    sessions.check_refresh_csrf(request)
    presented = request.cookies.get(sessions.COOKIE_NAME)
    if not presented:
        return Response(status_code=204)
    try:
        user, refresh_token, refresh_row = await sessions.rotate(db, presented)
    except sessions.RefreshError as exc:
        failed = JSONResponse(
            status_code=401,
            content={"error": {"code": exc.code, "message": str(exc), "details": {}}},
            headers={"WWW-Authenticate": "Bearer"},
        )
        sessions.clear_refresh_cookie(failed, request)
        return failed

    token, expires_in, expires_at = security.create_access_token(user, session_id=refresh_row.family_id)
    await db.commit()
    sessions.set_refresh_cookie(response, request, refresh_token, refresh_row)
    return LoginResponse(
        token=token,
        expiresIn=expires_in,
        expiresAt=expires_at,
        user=UserOut(id=user.id, email=user.email, name=user.full_name, role=user.role),
    )


@router.get("/me", response_model=UserOut)
async def me(user: AdminUser = Depends(security.current_user)) -> UserOut:
    """Who the bearer token belongs to. 401 if it is missing, expired or revoked."""
    return UserOut(id=user.id, email=user.email, name=user.full_name, role=user.role)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    user: AdminUser = Depends(security.current_user),
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    """
    Revoke the presented token and end its session.

    A JWT stays valid until it expires, so this records the token id in the
    revocation table. Without it, logout would only clear the browser's copy
    while the token itself kept working for the rest of its hour. The
    session's refresh tokens are revoked and the cookie cleared, so a reload
    afterwards stays signed out. Other devices' sessions are unaffected.
    """
    # Added before revoke(), which commits: the sign-out and its audit row
    # land together.
    db.add(AuditRecord(
        actor_id=user.id,
        actor_email=user.email,
        action="logout",
        subject_type="session",
        subject_id=None,
    ))
    session_id = request.state.token_payload.get("sid")
    if session_id:
        await sessions.revoke_family(db, session_id)
    await security.revoke(db, request.state.token_payload)
    sessions.clear_refresh_cookie(response, request)
    return LogoutResponse(
        revoked=True,
        message="Signed out. This token will no longer be accepted.",
    )

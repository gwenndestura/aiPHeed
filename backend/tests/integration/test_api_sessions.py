"""
Integration tests for sessions: the refresh cookie that keeps an admin
signed in across a reload (QA_REPORT AUTH-01), and what ends it.

Throwaway SQLite database per test, as in test_api_admin.py. The client talks
to http://localhost so the cookie is not marked Secure and the client sends
it back, as a browser would in local development.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.database import Base
from app.db.models import AdminUser, RefreshToken
from app.dependencies import get_db
from app.main import app
from app.services import security, sessions

EMAIL = "analyst@calabarzon.da.gov.ph"
PASSWORD = "correct-horse-battery-staple"
REFRESH = "/api/v1/auth/refresh"
CSRF = {"X-CSRF-Protection": "1"}


def _client(tmp_path, monkeypatch, base_url: str):
    db_file = tmp_path / "test.db"
    sync_engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", poolclass=NullPool)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with Session() as session:
            yield session

    monkeypatch.setattr(settings, "SECRET_KEY", "test-signing-key-not-for-production")
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, base_url=base_url), Session


@pytest.fixture
def api(tmp_path, monkeypatch):
    client, Session = _client(tmp_path, monkeypatch, "http://localhost")
    with client:
        client.session_factory = Session
        yield client
    app.dependency_overrides.clear()


def run(api, fn):
    async def _go():
        async with api.session_factory() as db:
            result = await fn(db)
            await db.commit()
            return result
    return asyncio.run(_go())


def make_user(api, email=EMAIL, password=PASSWORD):
    async def _create(db):
        db.add(AdminUser(email=email, full_name="J. Dela Cruz",
                         password_hash=security.hash_password(password), role="admin", is_active=True))
    run(api, _create)


def login(api, email=EMAIL, password=PASSWORD):
    r = api.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def refresh_cookie(response) -> str:
    return next(h for h in response.headers.get_list("set-cookie") if h.startswith(sessions.COOKIE_NAME + "="))


def present(api, token):
    """Send exactly this refresh token, as another browser holding a copy would."""
    api.cookies.clear()
    return api.post(REFRESH, headers={**CSRF, "Cookie": f"{sessions.COOKIE_NAME}={token}"})


def age_rows(api, **fields):
    """Move every refresh token's timestamps (expiry tests)."""
    async def _age(db):
        await db.execute(update(RefreshToken).values(**fields))
    run(api, _age)


def past(**delta):
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(**delta)


# ---------------------------------------------------------------------------
# The cookie
# ---------------------------------------------------------------------------

class TestCookie:

    def test_sign_in_sets_an_httponly_strict_cookie_scoped_to_refresh(self, api):
        make_user(api)
        header = refresh_cookie(login(api)).lower()
        assert "httponly" in header
        assert "samesite=strict" in header
        assert "path=/api/v1/auth/refresh" in header
        max_age = int(header.split("max-age=")[1].split(";")[0])
        assert settings.REFRESH_TOKEN_IDLE_TTL_SECONDS - 5 <= max_age <= settings.REFRESH_TOKEN_IDLE_TTL_SECONDS

    def test_cookie_is_secure_except_on_plain_http_localhost(self, tmp_path, monkeypatch):
        client, Session = _client(tmp_path, monkeypatch, "http://aipheed.example")
        with client:
            client.session_factory = Session
            make_user(client)
            secure = refresh_cookie(login(client)).lower()
        app.dependency_overrides.clear()
        assert "; secure" in secure

    def test_samesite_follows_the_setting(self, api, monkeypatch):
        make_user(api)
        monkeypatch.setattr(settings, "REFRESH_COOKIE_SAMESITE", "lax")
        assert "samesite=lax" in refresh_cookie(login(api)).lower()

    def test_the_token_is_stored_only_as_a_hash(self, api):
        make_user(api)
        login(api)
        raw = api.cookies.get(sessions.COOKIE_NAME)
        rows = run(api, lambda db: _all_rows(db))
        assert len(rows) == 1
        assert rows[0].token_hash != raw and len(rows[0].token_hash) == 64

    def test_access_token_never_set_as_a_cookie(self, api):
        make_user(api)
        r = login(api)
        assert all(not h.startswith(("token=", "access")) for h in r.headers.get_list("set-cookie"))
        assert r.json()["token"] not in " ".join(r.headers.get_list("set-cookie"))


async def _all_rows(db):
    return list((await db.scalars(select(RefreshToken).order_by(RefreshToken.id))).all())


# ---------------------------------------------------------------------------
# Refresh and rotation
# ---------------------------------------------------------------------------

class TestRefresh:

    def test_refresh_gives_a_working_access_token(self, api):
        make_user(api)
        login(api)
        r = api.post(REFRESH, headers=CSRF)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user"]["email"] == EMAIL
        assert api.get("/api/v1/admin/review", headers=bearer(body["token"])).status_code == 200

    def test_refresh_rotates_the_cookie(self, api):
        make_user(api)
        login(api)
        first = api.cookies.get(sessions.COOKIE_NAME)
        api.post(REFRESH, headers=CSRF)
        second = api.cookies.get(sessions.COOKIE_NAME)
        assert second and second != first
        api.post(REFRESH, headers=CSRF)
        assert api.cookies.get(sessions.COOKIE_NAME) not in (first, second)

    def test_a_rotated_token_is_rejected_and_ends_the_session(self, api, monkeypatch):
        make_user(api)
        login(api)
        old = api.cookies.get(sessions.COOKIE_NAME)
        assert api.post(REFRESH, headers=CSRF).status_code == 200
        new = api.cookies.get(sessions.COOKIE_NAME)
        monkeypatch.setattr(sessions, "REUSE_GRACE_SECONDS", -1)
        # The old token again: someone kept a copy.
        replay = present(api, old)
        assert replay.status_code == 401
        assert replay.json()["error"]["code"] == "session_revoked"
        # ...so the session is ended for the legitimate holder too.
        assert present(api, new).status_code == 401

    def test_two_tabs_refreshing_at_once_both_succeed(self, api):
        make_user(api)
        login(api)
        shared = api.cookies.get(sessions.COOKIE_NAME)
        # Both tabs loaded before either response came back: same cookie twice.
        assert present(api, shared).status_code == 200
        assert present(api, shared).status_code == 200

    def test_refresh_without_a_cookie_is_204_not_an_error(self, api):
        # Every public page load asks; "nothing to restore" must not log an error.
        r = api.post(REFRESH, headers=CSRF)
        assert r.status_code == 204
        assert not r.content

    def test_an_unknown_token_is_401_and_the_cookie_is_cleared(self, api):
        r = present(api, "not-a-real-token")
        assert r.status_code == 401
        assert 'max-age=0' in refresh_cookie(r).lower() or "expires=" in refresh_cookie(r).lower()


class TestExpiry:

    def test_idle_expiry(self, api):
        make_user(api)
        login(api)
        age_rows(api, expires_at=past(seconds=1))
        r = api.post(REFRESH, headers=CSRF)
        assert r.status_code == 401 and r.json()["error"]["code"] == "session_expired"

    def test_maximum_lifetime(self, api):
        make_user(api)
        login(api)
        age_rows(api, absolute_expires_at=past(seconds=1))
        assert api.post(REFRESH, headers=CSRF).status_code == 401

    def test_refresh_extends_the_idle_limit_but_not_past_the_maximum(self, api):
        make_user(api)
        login(api)
        # Session started long ago: 10 minutes of lifetime left.
        soon = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
        age_rows(api, absolute_expires_at=soon)
        assert api.post(REFRESH, headers=CSRF).status_code == 200
        newest = run(api, _all_rows)[-1]
        assert newest.expires_at <= newest.absolute_expires_at == soon


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------

class TestCsrf:

    def test_refresh_requires_the_custom_header(self, api):
        make_user(api)
        login(api)
        r = api.post(REFRESH)
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "csrf_failed"

    def test_a_foreign_origin_is_refused(self, api):
        make_user(api)
        login(api)
        r = api.post(REFRESH, headers={**CSRF, "Origin": "https://evil.example"})
        assert r.status_code == 403

    def test_an_allowed_origin_is_accepted(self, api):
        make_user(api)
        login(api)
        origin = settings.cors_origins[0]
        assert api.post(REFRESH, headers={**CSRF, "Origin": origin}).status_code == 200


# ---------------------------------------------------------------------------
# What ends a session
# ---------------------------------------------------------------------------

class TestEndingSessions:

    def test_logout_revokes_the_session_and_clears_the_cookie(self, api):
        make_user(api)
        token = login(api).json()["token"]
        kept = api.cookies.get(sessions.COOKIE_NAME)
        r = api.post("/api/v1/auth/logout", headers=bearer(token))
        assert r.status_code == 200
        assert 'max-age=0' in refresh_cookie(r).lower() or "expires=" in refresh_cookie(r).lower()
        assert api.cookies.get(sessions.COOKIE_NAME) is None
        # A copy of the cookie kept from before sign-out no longer works.
        assert present(api, kept).status_code == 401

    def test_logout_leaves_other_devices_signed_in(self, api):
        make_user(api)
        login(api)
        other_device = api.cookies.get(sessions.COOKIE_NAME)
        api.cookies.clear()
        token = login(api).json()["token"]
        api.post("/api/v1/auth/logout", headers=bearer(token))
        assert present(api, other_device).status_code == 200

    def test_deactivation_ends_every_session(self, api):
        make_user(api)
        login(api)
        cookie = api.cookies.get(sessions.COOKIE_NAME)

        async def _deactivate(db):
            user = await db.scalar(select(AdminUser).where(AdminUser.email == EMAIL))
            user.is_active = False
            await sessions.revoke_all_for_user(db, user.id)
        run(api, _deactivate)

        r = present(api, cookie)
        assert r.status_code == 401
        assert all(row.revoked_at is not None for row in run(api, _all_rows))

    def test_an_inactive_account_cannot_refresh_even_if_rows_survive(self, api):
        make_user(api)
        login(api)
        cookie = api.cookies.get(sessions.COOKIE_NAME)

        async def _deactivate_only(db):
            await db.execute(update(AdminUser).values(is_active=False))
        run(api, _deactivate_only)

        r = present(api, cookie)
        assert r.status_code == 401 and r.json()["error"]["code"] == "account_inactive"

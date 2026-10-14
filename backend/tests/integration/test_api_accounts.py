"""
Integration tests for admin accounts (QA_REPORT ACCT-1): account states at
sign-in, sign-up and email verification, approval, forgot/reset password and
the view-only demo account.

Same throwaway-database client as test_api_sessions.py (http://localhost, so
the refresh cookie round-trips).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, update

from app.config import settings
from app.db.models import AccountToken, AdminUser, AuditRecord
from app.services import accounts, mailer, security
from tests.integration.test_api_sessions import (  # noqa: F401  (api is a fixture)
    EMAIL,
    PASSWORD,
    api,
    run,
)

GENERIC = "Email or password is incorrect."


def add_user(api, email=EMAIL, password=PASSWORD, status=accounts.ACTIVE, **extra):
    async def _create(db):
        user = AdminUser(email=email, full_name="J. Dela Cruz", password_hash=security.hash_password(password),
                         role="admin", **extra)
        accounts.set_status(user, status)
        db.add(user)
    run(api, _create)


def sign_in(api, email=EMAIL, password=PASSWORD):
    return api.post("/api/v1/auth/login", json={"email": email, "password": password})


def error(r):
    return r.json()["error"]


# ---------------------------------------------------------------------------
# Account states at sign-in
# ---------------------------------------------------------------------------

class TestStatesAtSignIn:

    def test_active_account_signs_in(self, api):
        add_user(api)
        assert sign_in(api).status_code == 200

    def test_unverified_account_is_told_to_verify(self, api):
        add_user(api, status=accounts.PENDING_VERIFICATION)
        r = sign_in(api)
        assert r.status_code == 401
        assert error(r) == {**error(r), "code": "email_not_verified", "message": "Verify your email to continue."}

    def test_unapproved_account_is_told_it_is_waiting(self, api):
        add_user(api, status=accounts.PENDING_APPROVAL)
        r = sign_in(api)
        assert r.status_code == 401
        assert error(r)["code"] == "account_pending_approval"
        assert error(r)["message"] == "Your account is waiting for approval."

    @pytest.mark.parametrize("status", [accounts.REJECTED, accounts.DEACTIVATED])
    def test_rejected_and_deactivated_get_the_generic_error(self, api, status):
        add_user(api, status=status)
        r = sign_in(api)
        assert r.status_code == 401 and error(r)["message"] == GENERIC

    @pytest.mark.parametrize("status", [accounts.PENDING_VERIFICATION, accounts.PENDING_APPROVAL])
    def test_a_wrong_password_never_reveals_the_status(self, api, status):
        add_user(api, status=status)
        r = sign_in(api, password="wrong-password-xyz")
        assert error(r)["message"] == GENERIC

    def test_status_and_is_active_move_together(self):
        user = AdminUser(email=EMAIL, full_name="x", password_hash="x")
        for status in accounts.STATUSES:
            accounts.set_status(user, status)
            assert user.is_active == (status == accounts.ACTIVE)
        with pytest.raises(ValueError):
            accounts.set_status(user, "superuser")

    def test_an_account_made_without_a_status_is_active(self, api):
        # Rows made the pre-ACCT-1 way (and by the migration) default to active.
        async def _create(db):
            db.add(AdminUser(email=EMAIL, full_name="x", password_hash=security.hash_password(PASSWORD),
                             role="admin", is_active=True))
        run(api, _create)
        assert sign_in(api).status_code == 200
        user = run(api, lambda db: db.scalar(select(AdminUser)))
        assert user.status == accounts.ACTIVE


# ---------------------------------------------------------------------------
# Sign-up and email verification
# ---------------------------------------------------------------------------

NEW_EMAIL = "maria.santos@calabarzon.da.gov.ph"
GOOD_PASSWORD = "lambanog-tricycle-sampaguita-77"


@pytest.fixture
def outbox(monkeypatch):
    """Emails 'sent' during the test, as (to, subject, body)."""
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(mailer, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


def link_token(mail) -> str:
    return re.search(r"token=([A-Za-z0-9_-]+)", mail[2]).group(1)


def signup(api, email=NEW_EMAIL, password=GOOD_PASSWORD, **over):
    body = {"fullName": "Maria Santos", "email": email, "office": "Regional Field Office IV-A", "password": password}
    return api.post("/api/v1/auth/signup", json={**body, **over})


def find(api, email=NEW_EMAIL):
    return run(api, lambda db: db.scalar(select(AdminUser).where(AdminUser.email == email)))


async def _scalars(db, stmt):
    return list((await db.scalars(stmt)).all())


class TestSignUp:

    def test_new_account_is_pending_verification_with_no_access(self, api, outbox):
        r = signup(api)
        assert r.status_code == 202
        user = find(api)
        assert user.status == accounts.PENDING_VERIFICATION and not user.is_active
        assert user.office_unit == "Regional Field Office IV-A"
        assert outbox and outbox[0][0] == NEW_EMAIL and "/verify-email?token=" in outbox[0][2]
        assert error(sign_in(api, NEW_EMAIL, GOOD_PASSWORD))["code"] == "email_not_verified"

    @pytest.mark.parametrize("email", [
        "name@da.gov.ph", "name@fakecalabarzon.da.gov.ph", "name@calabarzon.da.gov.ph.evil.com",
        "name@sub.calabarzon.da.gov.ph", "name@gmail.com",
    ])
    def test_only_the_admin_domain_can_sign_up(self, api, outbox, email):
        r = signup(api, email=email)
        assert r.status_code == 400 and error(r)["code"] == "domain_not_allowed"
        assert "calabarzon.da.gov.ph" in error(r)["message"]
        assert find(api, email) is None and not outbox

    def test_uppercase_address_is_stored_lowercase(self, api, outbox):
        assert signup(api, email=NEW_EMAIL.upper()).status_code == 202
        assert find(api).email == NEW_EMAIL

    @pytest.mark.parametrize("password", ["short", "password1234", "Password1234"])
    def test_weak_passwords_are_refused(self, api, outbox, password):
        r = signup(api, password=password)
        assert r.status_code == 400 and error(r)["code"] == "weak_password"
        assert find(api) is None

    @pytest.mark.parametrize("field,value", [
        ("fullName", "x" * 201), ("office", "x" * 201), ("password", "x" * 1025), ("fullName", ""), ("office", ""),
    ])
    def test_length_caps_match_the_rest_of_the_api(self, api, outbox, field, value):
        assert signup(api, **{field: value}).status_code == 422

    def test_a_registered_address_gets_the_same_reply_and_no_second_account(self, api, outbox):
        add_user(api)  # analyst@..., active
        new = signup(api, email="other.person@calabarzon.da.gov.ph")
        taken = signup(api, email=EMAIL, password="a-completely-different-pass-99")
        assert taken.status_code == new.status_code == 202
        assert taken.json() == new.json()
        # The owner is told by email; the account and its password are untouched.
        assert outbox[-1][0] == EMAIL and "already exists" in outbox[-1][2]
        assert sign_in(api).status_code == 200
        count = run(api, lambda db: db.scalar(select(func.count()).select_from(AdminUser).where(AdminUser.email == EMAIL)))
        assert count == 1

    def test_signing_up_again_while_unverified_resends_but_keeps_the_password(self, api, outbox):
        signup(api)
        first = link_token(outbox[-1])
        assert signup(api, password="another-strong-passphrase-42").status_code == 202
        second = link_token(outbox[-1])
        # Only the newest link works...
        assert error(api.post("/api/v1/auth/verify-email", json={"token": first}))["code"] == "link_used"
        assert api.post("/api/v1/auth/verify-email", json={"token": second}).status_code == 200
        # ...and the second sign-up did not change the password.
        assert error(sign_in(api, NEW_EMAIL, GOOD_PASSWORD))["code"] == "account_pending_approval"

    def test_sign_up_is_rate_limited_per_ip(self, api, outbox, monkeypatch):
        from app.services import ratelimit
        ratelimit.reset()
        monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
        monkeypatch.setattr(settings, "RATE_LIMIT_SIGNUP_PER_HOUR", 2)
        codes = [signup(api, email=f"user{i}@calabarzon.da.gov.ph").status_code for i in range(3)]
        ratelimit.reset()
        assert codes == [202, 202, 429]


class TestVerification:

    def test_valid_link_verifies_and_moves_to_pending_approval(self, api, outbox):
        signup(api)
        r = api.post("/api/v1/auth/verify-email", json={"token": link_token(outbox[-1])})
        assert r.status_code == 200 and r.json()["status"] == accounts.PENDING_APPROVAL
        user = find(api)
        assert user.email_verified_at is not None and not user.is_active
        assert error(sign_in(api, NEW_EMAIL, GOOD_PASSWORD))["message"] == "Your account is waiting for approval."

    def test_a_link_works_once(self, api, outbox):
        signup(api)
        token = link_token(outbox[-1])
        assert api.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200
        again = api.post("/api/v1/auth/verify-email", json={"token": token})
        assert again.status_code == 400 and error(again)["code"] == "link_used"

    def test_an_expired_link_is_refused(self, api, outbox):
        signup(api)
        token = link_token(outbox[-1])
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
        run(api, lambda db: db.execute(update(AccountToken).values(expires_at=past)))
        r = api.post("/api/v1/auth/verify-email", json={"token": token})
        assert r.status_code == 400 and error(r)["code"] == "link_expired"
        assert find(api).status == accounts.PENDING_VERIFICATION

    def test_a_made_up_link_is_refused(self, api):
        r = api.post("/api/v1/auth/verify-email", json={"token": "not-a-real-token"})
        assert r.status_code == 400 and error(r)["code"] == "link_invalid"

    def test_links_are_stored_only_as_hashes(self, api, outbox):
        signup(api)
        token = link_token(outbox[-1])
        rows = run(api, lambda db: _scalars(db, select(AccountToken)))
        assert rows and all(row.token_hash != token and len(row.token_hash) == 64 for row in rows)
        assert rows[0].expires_at - rows[0].created_at == timedelta(hours=24)

    def test_resend_gives_the_same_reply_for_any_address(self, api, outbox):
        signup(api)
        replies = [api.post("/api/v1/auth/resend-verification", json={"email": e})
                   for e in (NEW_EMAIL, "nobody@calabarzon.da.gov.ph")]
        assert [r.status_code for r in replies] == [202, 202]
        assert replies[0].json() == replies[1].json()
        assert len(outbox) == 2  # sign-up + one resend to the real pending address

    def test_resend_issues_a_new_link_and_retires_the_old_one(self, api, outbox):
        signup(api)
        old = link_token(outbox[-1])
        api.post("/api/v1/auth/resend-verification", json={"email": NEW_EMAIL})
        assert error(api.post("/api/v1/auth/verify-email", json={"token": old}))["code"] == "link_used"
        assert api.post("/api/v1/auth/verify-email", json={"token": link_token(outbox[-1])}).status_code == 200

    def test_sign_up_and_verification_are_audited_without_secrets(self, api, outbox):
        signup(api)
        token = link_token(outbox[-1])
        api.post("/api/v1/auth/verify-email", json={"token": token})
        rows = run(api, lambda db: _scalars(db, select(AuditRecord)))
        assert [r.action for r in rows] == ["signup", "email_verified"]
        assert all(r.actor_email == NEW_EMAIL and r.subject_type == "account" for r in rows)
        dump = str([(r.reason, r.notes, r.subject_id) for r in rows])
        assert token not in dump and GOOD_PASSWORD not in dump

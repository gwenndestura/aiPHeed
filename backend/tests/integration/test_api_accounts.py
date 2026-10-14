"""
Integration tests for admin accounts (QA_REPORT ACCT-1): account states at
sign-in, sign-up and email verification, approval, forgot/reset password and
the view-only demo account.

Same throwaway-database client as test_api_sessions.py (http://localhost, so
the refresh cookie round-trips).
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.models import AdminUser
from app.services import accounts, security
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

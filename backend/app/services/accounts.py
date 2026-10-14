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

from app.db.models import AdminUser

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

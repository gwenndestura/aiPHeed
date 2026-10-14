"""
scripts/create_admin.py
------------------------
Create or update a DA CALABARZON admin account.

There is deliberately no seeded default account. The old console shipped a
hardcoded demo credential (removed), compiled into the JS bundle and printed
in the UI; anything comparable committed here would be the same mistake in a
new place.

Usage
-----
    python scripts/create_admin.py --email analyst@calabarzon.da.gov.ph \
                                   --name "J. Dela Cruz"

The password is read from a hidden prompt, or from the AIPHEED_ADMIN_PASSWORD
environment variable for non-interactive setup. It is never taken from a
command-line flag, where it would land in shell history and the process list.

    --deactivate    disable an existing account without deleting its audit trail
    --list          show existing accounts
    --demo          create or update the one view-only demo account from
                    DEMO_ADMIN_EMAIL and DEMO_ADMIN_PASSWORD in .env (it can
                    sign in only while ENABLE_DEMO_ACCOUNT=true)
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.config import settings  # noqa: E402
from app.db.database import AsyncSessionLocal  # noqa: E402
from app.db.models import AdminUser  # noqa: E402
from app.services import accounts, security  # noqa: E402
from app.services.passwords import password_problem  # noqa: E402


def read_password() -> str:
    """Hidden prompt with confirmation, or the env var when non-interactive."""
    from_env = os.environ.get("AIPHEED_ADMIN_PASSWORD")
    if from_env:
        return from_env

    first = getpass.getpass("Password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        sys.exit("Passwords do not match.")
    return first


def check_password(password: str) -> None:
    """The shared policy in app/services/passwords.py: length and common-password list."""
    problem = password_problem(password)
    if problem:
        sys.exit(problem)


async def list_accounts() -> None:
    async with AsyncSessionLocal() as db:
        rows = list((await db.scalars(select(AdminUser).order_by(AdminUser.email))).all())
    if not rows:
        print("No admin accounts exist yet.")
        return
    print(f"{'EMAIL':<40} {'NAME':<24} {'STATUS':<21} LAST LOGIN")
    for u in rows:
        last = u.last_login_at.strftime("%Y-%m-%d %H:%M") if u.last_login_at else "never"
        print(f"{u.email:<40} {u.full_name:<24} {u.status:<21} {last}")


async def deactivate(email: str) -> None:
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(AdminUser).where(AdminUser.email == email))
        if user is None:
            sys.exit(f"No account for {email}.")
        accounts.set_status(user, accounts.DEACTIVATED)
        # Every access token is refused and no browser can renew its session.
        await security.end_all_sessions(db, user)
        await db.commit()
    # The row is kept so the audit trail still resolves who did what.
    print(f"Deactivated {email}. Their audit history is retained; all sessions ended.")


async def upsert(email: str, name: str, password: str) -> None:
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(AdminUser).where(AdminUser.email == email))
        if user is None:
            # Created by someone with server access: verified and approved
            # already (this is how the first admin is made).
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            user = AdminUser(
                email=email,
                full_name=name,
                password_hash=security.hash_password(password),
                role="admin",
                email_verified_at=now,
                approved_at=now,
            )
            accounts.set_status(user, accounts.ACTIVE)
            db.add(user)
            action = "Created"
        else:
            user.full_name = name or user.full_name
            # Ends every existing session of the account (tokens and refresh
            # cookies) -- whoever knew the old password is signed out.
            await security.set_password(db, user, password)
            # The script is run by someone with server access: whatever state
            # the account was in, it is now verified, approved and active.
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            user.email_verified_at = user.email_verified_at or now
            user.approved_at = user.approved_at or now
            accounts.set_status(user, accounts.ACTIVE)
            action = "Updated (all existing sessions ended)"
        await db.commit()
    print(f"{action} admin account {email}.")


async def upsert_demo(email: str, password: str) -> str:
    """
    The one demo account: verified, approved, active, is_demo. Any other
    account still marked as the demo is un-marked AND deactivated -- simply
    un-marking it would turn a shared presentation login into a full admin.
    A regular admin's address is refused rather than demoted.
    """
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        others = (await db.scalars(
            select(AdminUser).where(AdminUser.is_demo.is_(True), AdminUser.email != email)
        )).all()
        for old in others:
            old.is_demo = False
            accounts.set_status(old, accounts.DEACTIVATED)
            await security.end_all_sessions(db, old)
            print(f"Previous demo account {old.email} un-marked and deactivated.")

        user = await db.scalar(select(AdminUser).where(AdminUser.email == email))
        if user is None:
            user = AdminUser(
                email=email,
                full_name="Demo account",
                password_hash=security.hash_password(password),
                role="admin",
                email_verified_at=now,
                approved_at=now,
                is_demo=True,
            )
            accounts.set_status(user, accounts.ACTIVE)
            db.add(user)
            action = "Created"
        elif not user.is_demo:
            sys.exit(
                f"{email} is a regular admin account. Choose a different DEMO_ADMIN_EMAIL; "
                "a real admin is never turned into the view-only demo account."
            )
        else:
            # Ends the demo account's existing sessions (e.g. a laptop left
            # signed in after the last presentation).
            await security.set_password(db, user, password)
            user.email_verified_at = user.email_verified_at or now
            user.approved_at = user.approved_at or now
            accounts.set_status(user, accounts.ACTIVE)
            action = "Updated (its existing sessions ended)"
        await db.commit()
    return action


def demo_from_env() -> None:
    email = settings.DEMO_ADMIN_EMAIL.strip().lower()
    password = settings.DEMO_ADMIN_PASSWORD
    if not email or not password:
        sys.exit("Set DEMO_ADMIN_EMAIL and DEMO_ADMIN_PASSWORD in backend/.env first.")
    if not security.email_domain_allowed(email):
        sys.exit(f"DEMO_ADMIN_EMAIL must be an @{settings.ADMIN_EMAIL_DOMAIN} address.")
    if settings.secret_is_default:
        sys.exit("SECRET_KEY is still 'changeme'. Set a strong random SECRET_KEY in backend/.env first.")
    check_password(password)
    action = asyncio.run(upsert_demo(email, password))
    print(f"{action} the view-only demo account {email}.")
    state = "ON: it can sign in now" if settings.ENABLE_DEMO_ACCOUNT else \
        "OFF: set ENABLE_DEMO_ACCOUNT=true in backend/.env and restart the API to let it sign in"
    print(f"ENABLE_DEMO_ACCOUNT is {state}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("Usage")[0].strip())
    parser.add_argument("--email")
    parser.add_argument("--name", default="")
    parser.add_argument("--list", action="store_true", help="show existing accounts")
    parser.add_argument("--deactivate", action="store_true", help="disable the account")
    parser.add_argument("--demo", action="store_true",
                        help="create/update the view-only demo account from DEMO_ADMIN_EMAIL / DEMO_ADMIN_PASSWORD")
    args = parser.parse_args()

    if args.demo:
        demo_from_env()
        return

    if args.list:
        asyncio.run(list_accounts())
        return

    if not args.email:
        sys.exit("--email is required (or pass --list).")

    email = args.email.strip().lower()
    if not security.email_domain_allowed(email):
        sys.exit(
            f"{email} is outside the permitted domain "
            f"@{settings.ADMIN_EMAIL_DOMAIN}. Change ADMIN_EMAIL_DOMAIN if that "
            "is wrong."
        )

    if args.deactivate:
        asyncio.run(deactivate(email))
        return

    if settings.secret_is_default:
        # Accounts would work, but every token minted against them would be
        # forgeable, so fix the key before creating the first one.
        sys.exit(
            "SECRET_KEY is still 'changeme'. Set a strong random SECRET_KEY in "
            "backend/.env first -- otherwise anyone can forge an admin token "
            "and the account you are about to create is meaningless.\n\n"
            "  python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )

    if not args.name:
        sys.exit("--name is required when creating or updating an account.")

    password = read_password()
    check_password(password)
    asyncio.run(upsert(email, args.name.strip(), password))


if __name__ == "__main__":
    main()

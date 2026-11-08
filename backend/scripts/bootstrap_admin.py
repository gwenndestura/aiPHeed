"""
scripts/bootstrap_admin.py
---------------------------
One-time way to create the first DA CALABARZON account on the deployed server when nobody with server access can run
create_admin.py.

    python scripts/bootstrap_admin.py prepare --email someone@calabarzon.da.gov.ph --name "Full Name"

asks for a password at a hidden prompt on the owner's own computer and writes data/bootstrap_admin.json: the address, the
name and the Argon2 hash. The password itself is never stored. Commit that file and push to main; on start-up the server
runs

    python scripts/bootstrap_admin.py apply

which creates the account if that address has none. It never changes an existing account, so a restart cannot undo a
later password change or take over someone else's account. With no file it does nothing.

The repository is public, so the hash can be read by anyone and guessed at offline: `prepare` requires a longer password
than the usual policy. Delete data/bootstrap_admin.json once the account signs in.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
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

DEFAULT_FILE = Path(__file__).resolve().parents[1] / "data" / "bootstrap_admin.json"
MIN_LENGTH = 16  # above the usual 12, because the hash is public


def prepare(email: str, name: str, path: Path) -> None:
    email = email.strip().lower()
    if not security.email_domain_allowed(email):
        sys.exit(f"The address must end in {' or '.join('@' + d for d in settings.admin_email_domains)}.")
    first = getpass.getpass(f"Password for {email} (at least {MIN_LENGTH} characters, typing stays hidden): ")
    second = getpass.getpass("Type it again: ")
    if first != second:
        sys.exit("The two passwords do not match. Nothing was saved.")
    if len(first) < MIN_LENGTH:
        sys.exit(f"Use at least {MIN_LENGTH} characters. Nothing was saved.")
    problem = password_problem(first)
    if problem:
        sys.exit(f"{problem} Nothing was saved.")
    doc = {"email": email, "name": name.strip(), "password_hash": security.hash_password(first)}
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"Saved. Sign in later as {email}. The password itself was not stored.")


async def _create_if_missing(doc: dict) -> str:
    async with AsyncSessionLocal() as db:
        if await db.scalar(select(AdminUser).where(AdminUser.email == doc["email"])):
            return "already exists; left unchanged"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        user = AdminUser(email=doc["email"], full_name=doc["name"], password_hash=doc["password_hash"], role="admin",
                         email_verified_at=now, approved_at=now)
        accounts.set_status(user, accounts.ACTIVE)
        db.add(user)
        await db.commit()
    return "created"


def apply(path: Path) -> None:
    if not path.exists():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not security.email_domain_allowed(doc["email"]) or not doc["password_hash"].startswith("$argon2"):
        sys.exit("bootstrap_admin: file refused (address outside the allowed domain, or not an Argon2 hash).")
    print(f"bootstrap_admin: {doc['email']} {asyncio.run(_create_if_missing(doc))}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("prepare")
    make.add_argument("--email", required=True)
    make.add_argument("--name", required=True)
    sub.add_parser("apply")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.email, args.name, args.file)
    else:
        apply(args.file)


if __name__ == "__main__":
    main()

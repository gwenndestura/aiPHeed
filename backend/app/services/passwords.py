"""
app/services/passwords.py
--------------------------
The one password policy. Every place that sets a password -- today
scripts/create_admin.py, later the sign-up and reset forms -- calls
`password_problem()` so the rules cannot drift apart.

Rules:

* At least 12 characters. Length is what makes a password hard to guess; a
  passphrase of a few words clears this easily.
* Not on the bundled list of common passwords
  (app/resources/common_passwords.txt, from public breach corpora). The check
  is case-insensitive and ignores surrounding spaces, so "Password1234" is
  refused along with "password1234".

No composition rules (a digit, a symbol, ...): they push people toward
predictable patterns without adding much strength.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

MIN_PASSWORD_LENGTH = 12

COMMON_PASSWORDS_FILE = Path(__file__).resolve().parents[1] / "resources" / "common_passwords.txt"


@lru_cache(maxsize=1)
def _common_passwords() -> frozenset[str]:
    with COMMON_PASSWORDS_FILE.open(encoding="utf-8") as f:
        return frozenset(
            line.rstrip("\n").lower()
            for line in f
            if line.strip() and not line.startswith("#")
        )


def is_common_password(password: str) -> bool:
    return password.strip().lower() in _common_passwords()


def password_problem(password: str) -> str | None:
    """
    Why `password` is not acceptable, as a sentence to show the person
    choosing it -- or None when it is fine.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return (
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters. "
            "A passphrase of a few words is easier to remember and stronger "
            "than a short complex string."
        )
    if is_common_password(password):
        return (
            "That password appears on a list of commonly used passwords. "
            "Choose a different one."
        )
    return None

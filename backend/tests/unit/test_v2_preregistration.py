"""
tests/unit/test_v2_preregistration.py
-------------------------------------
docs/aipheed/v2/PREREGISTRATION.md was committed before any v2 model was fitted. Its SHA-256 (line endings
normalised to LF, so a CRLF checkout does not change it) is frozen here: any edit fails this test. Deviations go to
docs/aipheed/v2/DEVIATIONS.md instead.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

PREREG = Path(__file__).resolve().parents[3] / "docs" / "aipheed" / "v2" / "PREREGISTRATION.md"
PREREG_SHA256 = "90ad51a99a90b3a06597c02f8d6a6515b1034388953afe7e37c24506220a691b"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def test_preregistration_unchanged():
    assert _sha(PREREG.read_bytes()) == PREREG_SHA256


def test_preregistration_check_detects_an_edit():
    edited = PREREG.read_bytes().replace(b"2 000 draws", b"1 000 draws")
    assert edited != PREREG.read_bytes() and _sha(edited) != PREREG_SHA256

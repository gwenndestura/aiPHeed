"""
tests/unit/test_v6_preregistration.py
-------------------------------------
docs/aipheed/v6/PREREGISTRATION.md was committed before any v6 model was fitted. Its SHA-256 (line endings
normalised to LF, so a CRLF checkout does not change it) is frozen here: any edit fails this test. Deviations go to
docs/aipheed/v6/DEVIATIONS.md instead.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

PREREG = Path(__file__).resolve().parents[3] / "docs" / "aipheed" / "v6" / "PREREGISTRATION.md"
PREREG_SHA256 = "f82237d6558dd660db53b4754eac3bde8d428138e17b352ca68255226e961309"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def test_preregistration_unchanged():
    assert _sha(PREREG.read_bytes()) == PREREG_SHA256


def test_preregistration_check_detects_an_edit():
    edited = PREREG.read_bytes().replace(b"seed 2026", b"seed 2027")
    assert edited != PREREG.read_bytes() and _sha(edited) != PREREG_SHA256

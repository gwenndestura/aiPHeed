"""
tests/unit/test_v4_preregistration.py
-------------------------------------
docs/aipheed/v4/PREREGISTRATION.md was committed before any v4 model was fitted. Its SHA-256 (line endings
normalised to LF, so a CRLF checkout does not change it) is frozen here: any edit fails this test. Deviations go to
docs/aipheed/v4/DEVIATIONS.md instead.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

PREREG = Path(__file__).resolve().parents[3] / "docs" / "aipheed" / "v4" / "PREREGISTRATION.md"
PREREG_SHA256 = "eaff4f63c0a483bda6bcfd77538634e2e27b6d220515806fdf1bba15c75d3d22"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def test_preregistration_unchanged():
    assert _sha(PREREG.read_bytes()) == PREREG_SHA256


def test_preregistration_check_detects_an_edit():
    edited = PREREG.read_bytes().replace(b"seed 2026", b"seed 2027")
    assert edited != PREREG.read_bytes() and _sha(edited) != PREREG_SHA256

"""Test helper: put runner/ and backend_dev/ on the path and install the E29 guard (every test runs under it)."""
import os
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
# The backend under test: E31 backend_dev by default; AIPHEED_TEST_BACKEND=<dir> runs the same suite against another
# copy, e.g. the main backend/ after the E34 promotion.
BD = Path(os.environ.get("AIPHEED_TEST_BACKEND") or EXP / "backend_dev").resolve()
for p in (EXP / "runner", BD, EXP / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import guard29  # noqa: E402

guard29.install()

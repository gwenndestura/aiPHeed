"""Test helper: put runner/ and backend_dev/ on the path and install the E26 guard (every test runs under it)."""
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
for p in (EXP / "runner", EXP / "backend_dev", EXP / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import guard  # noqa: E402

guard.install()

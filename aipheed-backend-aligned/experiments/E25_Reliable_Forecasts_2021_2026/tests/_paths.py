"""Test helper: put runner/ and backend_dev/ on the path and install the E25 guard (every test runs under it)."""
import json
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
for p in (EXP / "runner", EXP / "backend_dev", EXP / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import guard  # noqa: E402

guard.install()


def primary_run() -> str:
    """The primary frozen run recorded in runs/reproducibility.json."""
    return json.loads((EXP / "runs" / "reproducibility.json").read_text(encoding="utf-8"))["run_1"]

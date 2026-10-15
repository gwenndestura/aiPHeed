"""Record the validity-test outcome for gate G0 (PROTOCOL section 7)."""
import json
from datetime import datetime, timezone
from pathlib import Path


def pytest_sessionfinish(session, exitstatus):
    out = Path(__file__).resolve().parents[1] / "runs" / "leakage_tests.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"passed": exitstatus == 0, "tests_collected": session.testscollected,
                               "failed": session.testsfailed,
                               "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, indent=1))

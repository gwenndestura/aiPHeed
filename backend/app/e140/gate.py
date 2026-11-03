"""Record E140's gate (PROTOCOL.md section 4) in the model registry: python -m app.e140.gate"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app import registry as R
from app.paths import BACKEND_DIR

MODEL_ID = "e140-lgbm-native-1.0"
ARTIFACT = "data/e140/out/results.json"


def record() -> dict:
    from app.registry.catalog import sync
    r = json.loads((BACKEND_DIR / ARTIFACT).read_text())
    checks = [{"id": k, "status": "pass" if v else "fail", "evidence": ARTIFACT} for k, v in r["gate"]["checks"].items()]
    sync()
    return R.record_gate(MODEL_ID, {"gate_version": "risk-gate E140-P1", "decision": r["gate"]["decision"],
                                    "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "artifact_file_sha256": R.file_sha256(BACKEND_DIR / ARTIFACT),
                                    "passed": r["gate"]["decision"] == "A", "checks": checks})


if __name__ == "__main__":
    m = record()
    print(m["model_id"], m["status"], m["gate"]["decision"], [c["id"] for c in m["gate"]["checks"] if c["status"] != "pass"])

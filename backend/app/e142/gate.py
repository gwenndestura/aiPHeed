"""Record E142's pre-registered gate in the model registry: python -m app.e142.gate"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app import registry as R
from app.e142 import OUT, PROTOCOL_VERSION
from app.paths import BACKEND_DIR

MODEL_ID = "e142-state-lgbm-1.0"
ARTIFACT = "data/e142/out/results.json"


def record() -> dict:
    from app.registry.catalog import sync
    g = json.loads((OUT / "results.json").read_text())["gate"]
    checks = [{"id": k, "status": "pass" if v else "fail", "evidence": ARTIFACT} for k, v in g["checks"].items()]
    sync()
    return R.record_gate(MODEL_ID, {"gate_version": f"risk-gate {PROTOCOL_VERSION}", "checks": checks, "passed": bool(g["passed"]),
                                    "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "artifact_file_sha256": R.file_sha256(BACKEND_DIR / ARTIFACT)})


if __name__ == "__main__":
    m = record()
    print(m["model_id"], m["status"], [c["id"] for c in m["gate"]["checks"] if c["status"] != "pass"])

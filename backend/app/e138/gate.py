"""Record the E138 selected WHERE model's gate result (PROTOCOL.md section 6) in the model registry.

    python -m app.e138.gate
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app import registry as R
from app.e138 import OUT, PROTOCOL_VERSION
from app.paths import BACKEND_DIR

MODEL_ID = "e138-where-lrp-1.0"
ARTIFACT = "data/e138/out/results.json"


def result() -> dict:
    res = json.loads((OUT / "results.json").read_text())
    checks = [{"id": k, "status": "pass" if v else "fail", "evidence": ARTIFACT} for k, v in res["gate"]["checks"].items()]
    checks.append({"id": "G12_confirmatory", "status": "not_evaluable",
                   "evidence": "sealed prediction data/e138/out/sealed_prediction.json awaits the next provincial round"})
    return {"gate_version": f"risk-gate {PROTOCOL_VERSION}", "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "artifact_file_sha256": R.file_sha256(BACKEND_DIR / ARTIFACT), "selected": res["selection"]["selected"],
            "passed": all(c["status"] == "pass" for c in checks if c["id"] != "G12_confirmatory"), "checks": checks}


def record() -> dict:
    from app.registry.catalog import sync
    sync()
    return R.record_gate(MODEL_ID, result())


if __name__ == "__main__":
    m = record()
    print(m["model_id"], m["status"], [c["id"] for c in m["gate"]["checks"] if c["status"] != "pass"])

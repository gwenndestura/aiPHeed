"""Record E144's pre-registered decisions in the model registry: python -m app.e144.gate"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app import registry as R
from app.e144 import OUT, PROTOCOL_VERSION
from app.paths import BACKEND_DIR

MODEL_ID = "e144-lbf-1.0"
ARTIFACT = "data/e144/out/results.json"


def record() -> dict:
    from app.registry.catalog import sync
    dec = json.loads((OUT / "results.json").read_text())["decisions"]
    checks = [{"id": k, "status": "pass" if v else "fail", "evidence": ARTIFACT}
              for k, v in dec.items() if isinstance(v, bool) and k != "validated_forecast"]
    sync()
    return R.record_gate(MODEL_ID, {"gate_version": f"E144 decisions {PROTOCOL_VERSION}", "checks": checks,
                                    "passed": bool(dec["validated_forecast"]),
                                    "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "artifact_file_sha256": R.file_sha256(BACKEND_DIR / ARTIFACT)})


if __name__ == "__main__":
    m = record()
    print(m["model_id"], m["status"], [c["id"] for c in m["gate"]["checks"] if c["status"] == "fail"])

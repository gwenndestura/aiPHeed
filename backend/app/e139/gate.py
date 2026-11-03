"""Record E139's acceptance gate (PROTOCOL.md section 7) in the model registry: python -m app.e139.gate"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app import registry as R
from app.e139 import OUT, PROTOCOL_VERSION
from app.paths import BACKEND_DIR

MODEL_ID = "e139-lgbm-1.0"
ARTIFACT = "data/e139/out/model_artifact.json"


def result() -> dict:
    r = json.loads((OUT / "results.json").read_text())
    checks = [{"id": k, "status": "pass" if v else "fail", "evidence": "lead 0, data/e139/out/results.json"}
              for k, v in r["leads"]["0"]["checks"].items()]
    checks += [{"id": k, "status": "pass" if v else "fail", "evidence": "data/e139/out/results.json"}
               for k, v in r["global_checks"].items() if k.startswith("G")]
    checks.append({"id": "G12_confirmatory", "status": "not_evaluable",
                   "evidence": "sealed_prediction.json awaits the next provincial food-insecurity round"})
    return {"gate_version": f"risk-gate {PROTOCOL_VERSION}", "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "artifact_file_sha256": R.file_sha256(BACKEND_DIR / ARTIFACT), "max_reliable_lead": r["max_reliable_lead"],
            "passed": all(c["status"] == "pass" for c in checks if c["id"] != "G12_confirmatory"), "checks": checks}


def record() -> dict:
    from app.registry.catalog import sync
    sync()
    return R.record_gate(MODEL_ID, result())


if __name__ == "__main__":
    m = record()
    print(m["model_id"], m["status"], [c["id"] for c in m["gate"]["checks"] if c["status"] != "pass"])

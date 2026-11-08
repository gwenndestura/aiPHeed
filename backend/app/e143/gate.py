"""Record E143's pre-registered gate in the model registry: python -m app.e143.gate"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app import registry as R
from app.e143 import OUT, PROTOCOL_VERSION
from app.paths import BACKEND_DIR

IDS = {"e143-re-lgbm-1.0": "C2 RE-LGBM-X", "e143-hre-lgbm-1.0": "C4 HRE-LGBM-X"}
ARTIFACT = "data/e143/out/results.json"


def record() -> list[dict]:
    from app.registry.catalog import sync
    g = json.loads((OUT / "results.json").read_text())["gate"]["per_candidate"]
    sync()
    out = []
    for mid, c in IDS.items():
        checks = [{"id": k, "status": "n/a" if v is None else "pass" if v else "fail", "evidence": ARTIFACT}
                  for k, v in g[c]["checks"].items()]
        out.append(R.record_gate(mid, {"gate_version": f"risk-gate {PROTOCOL_VERSION}", "checks": checks,
                                       "passed": bool(g[c]["passed"]),
                                       "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                       "artifact_file_sha256": R.file_sha256(BACKEND_DIR / ARTIFACT)}))
    return out


if __name__ == "__main__":
    for m in record():
        print(m["model_id"], m["status"], [c["id"] for c in m["gate"]["checks"] if c["status"] == "fail"])

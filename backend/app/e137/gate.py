"""
Record E137's revised risk-gate result (PROTOCOL.md section 8) in the model registry.

    python -m app.e137.gate        registers e137-sarf-1.0 (catalog) and records its gate result

Overall result = the checks at Lead 0 (the shortest horizon). The candidate passes only if S1-S11 pass there. Each
lead's checks are kept in `per_lead`. S12 (confirmatory test on unseen measurements) is always pending for now.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app import registry as R
from app.e137 import OUT, PROTOCOL_VERSION
from app.paths import BACKEND_DIR

MODEL_ID = "e137-sarf-1.0"
ARTIFACT = "data/e137/out/results.json"


def result() -> dict:
    res = json.loads((OUT / "results.json").read_text())
    ext = json.loads((OUT / "external_s11.json").read_text())
    per_lead = {}
    for lead, r in res["leads"].items():
        c = dict(r["gate"]["checks"])
        c["S11_external"] = ext["passed"]
        per_lead[lead] = c
    checks = [{"id": k, "status": "pass" if v else "fail", "evidence": f"lead 0; per-lead values in {ARTIFACT}"}
              for k, v in per_lead["0"].items()]
    checks.append({"id": "S12_confirmatory", "status": "not_evaluable",
                   "evidence": "no unseen provincial HFIAS/FIES round yet; ENNS rows are development evidence (D-3)"})
    return {"gate_version": f"risk-gate {PROTOCOL_VERSION}", "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "artifact_file_sha256": R.file_sha256(BACKEND_DIR / ARTIFACT),
            "passed": all(c["status"] == "pass" for c in checks if c["id"] != "S12_confirmatory"),
            "max_reliable_lead": res["max_reliable_lead_development"], "checks": checks, "per_lead": per_lead,
            "note": "A pass would mean APPROVED-PROVISIONAL (S12 pending) and still need owner approval to promote."}


def record() -> dict:
    from app.registry.catalog import sync
    sync()
    return R.record_gate(MODEL_ID, result())


if __name__ == "__main__":
    m = record()
    print(m["model_id"], m["status"], [c["id"] for c in m["gate"]["checks"] if c["status"] != "pass"])

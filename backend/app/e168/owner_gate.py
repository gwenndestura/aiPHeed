"""
Owner-defined acceptance for e168-lgbm-1.0 (owner decision 2026-11-07): a lead is served when the model's measured
accuracy is >= 75 % AND it is significantly better than reusing the latest survey (Brier difference CI < 0), on the
72 chronological as-of Lead-k forecasts. Also required: LightGBM is the final algorithm, the leakage test passes,
forecasts are sealed before new outcomes, and the artifact hash is recorded. The stricter E156 C1-C6 result is
disclosed in every gate record (not passed: maximum reliable lead 0 under that test).

    python -m app.e168.owner_gate promote --approver "<owner name>"
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone

from app import registry as R
from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
MODEL_ID = "e168-lgbm-1.0"
ARTIFACT = "data/e168/out/live_2027.json"


def _c(cid, name, ok, evidence):
    return {"id": cid, "name": name, "status": "pass" if ok else "fail", "critical": True, "evidence": evidence}


def evaluate() -> dict:
    H = json.loads((D / "e168" / "out" / "lead_horizon.json").read_text())
    res = json.loads((D / "e168" / "out" / "results.json").read_text())
    live = json.loads((BACKEND_DIR / ARTIFACT).read_text())
    L = {int(k): v for k, v in H["leads"].items()}
    served = live["served_leads"]
    seal_ok = hashlib.sha256((D / "e168" / "out" / "sealed_enns2022.json").read_bytes()).hexdigest().startswith("f8228fae")
    checks = [
        _c("O1", "Accuracy >= 75 % at every served lead", bool(served) and all(L[l]["accuracy"] >= 0.75 for l in served), {l: L[l]["accuracy"] for l in served}),
        _c("O2", "Better than reusing the latest survey at every served lead (Brier CI < 0)", bool(served) and all(L[l]["beats_persistence_C2"] for l in served), {l: L[l]["brier_minus_persistence_ci95"] for l in served}),
        _c("O3", "Served leads are consecutive from Lead 1", served == list(range(1, len(served) + 1)), served),
        _c("O4", "HIGH recall >= 0.60 at every served lead", all(L[l]["high_recall"] >= 0.60 for l in served), {l: L[l]["high_recall"] for l in served}),
        _c("O5", "Final algorithm is LightGBM (owner rule)", "LightGBM" in live["name"], live["name"]),
        _c("O6", "Leakage test: unreleased surveys corrupted change no forecast", res["leakage_max_abs_change"] < 1e-9, res["leakage_max_abs_change"]),
        _c("O7", "Forecasts sealed before new outcomes (ENNS 2022 seal intact)", seal_ok, "data/e168/out/sealed_enns2022.json f8228fae"),
    ]
    return {"basis": "owner-defined acceptance (decision 2026-11-07): accuracy >= 75 % and skill over the latest survey; NOT the E156 C1-C6 test",
            "disclosure": f"E156 C1-C6 not passed at Lead 1 (maximum reliable lead {H['maximum_reliable_lead_E156']} under that stricter test; 72 rows from 3 survey rounds)",
            "served_leads": served, "checks": checks, "passed": all(c["status"] == "pass" for c in checks),
            "artifact_file_sha256": R.file_sha256(BACKEND_DIR / ARTIFACT), "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def version_text() -> str:
    live = json.loads((BACKEND_DIR / ARTIFACT).read_text())
    acc = live["accuracy_by_lead"]
    served = live["served_leads"]
    l1 = [r for r in live["provinces"] if r["lead"] == 1]
    prov = "; ".join(f"{r['province']} {r['risk_class']} {r['score_pct']:.0f}%" for r in sorted(l1, key=lambda r: r["province"]))
    accs = ", ".join(f"{acc[str(l)]['accuracy'] * 100:.1f}%" for l in served)
    return (f"E168 LightGBM. Forecast for {l1[0]['target_quarter']} (HFIAS moderate+severe, HIGH at 50%): {prov}. "
            f"Measured accuracy {accs} at 1 to {max(served)} quarters ahead (latest survey alone: {acc['1']['persistence_accuracy'] * 100:.1f}%)")


def promote(approver: str):
    reg_meta = {"version": version_text(), "artifact_path": ARTIFACT, "artifact_sha256": R.file_sha256(BACKEND_DIR / ARTIFACT),
                "target": "HFIAS moderate+severe household food insecurity by province; HIGH at 50 %",
                "note": "Owner-defined acceptance (2026-11-07). E156 C1-C6 not passed; disclosed in the gate record."}
    R.register(MODEL_ID, reg_meta, "candidate")
    g = evaluate()
    R.record_gate(MODEL_ID, g)
    (R.DIR / "gate_results").mkdir(parents=True, exist_ok=True)
    (R.DIR / "gate_results" / f"{MODEL_ID}.json").write_text(json.dumps(g, indent=1))
    if not g["passed"]:
        raise SystemExit(f"owner gate failed: {[c['id'] for c in g['checks'] if c['status'] != 'pass']}")
    rec = R.promote(MODEL_ID, approver)
    print(json.dumps({"promoted": rec["model_id"], "version": rec["version"], "served_leads": g["served_leads"]}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["evaluate", "promote"])
    ap.add_argument("--approver", default="")
    a = ap.parse_args()
    if a.cmd == "evaluate":
        print(json.dumps(evaluate(), indent=1))
    else:
        if not a.approver:
            raise SystemExit("--approver is required")
        promote(a.approver)

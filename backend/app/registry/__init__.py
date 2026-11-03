"""
app.registry
------------
Model registry and release gate. The official dashboard and the production API may only use a model that this
registry marks as approved for production; nothing selects "the latest artifact".

    data/registry/registry.json        models, gate results, the production pointer and the promotion history
    data/registry/approvals/<id>.json  approval record written only by a successful promotion

Statuses: candidate -> rejected | approved. The incumbent dashboard engine that predates this gate is recorded as
`legacy_incumbent` (served, never gate-approved). `promote` refuses unless every gate check passed for the exact
artifact hash on disk; it never relaxes a threshold.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from app.paths import BACKEND_DIR

DIR = BACKEND_DIR / "data" / "registry"
REGISTRY = DIR / "registry.json"
APPROVALS = DIR / "approvals"


class NoApprovedModel(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path: Path | None = None) -> dict:
    p = path or REGISTRY
    if not p.exists():
        return {"production": None, "models": {}, "history": []}
    return json.loads(p.read_text())


def save(reg: dict, path: Path | None = None) -> None:
    p = path or REGISTRY
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg, indent=1))


def register(model_id: str, meta: dict, status: str = "candidate", path: Path | None = None) -> dict:
    """Add or refresh a model entry. The same artifact keeps its status; a different artifact starts again as `status`
    (an approval belongs to one artifact hash, so a changed approved model also leaves production)."""
    reg = load(path)
    old = reg["models"].get(model_id)
    same = bool(old) and old.get("artifact_sha256") == meta.get("artifact_sha256")
    entry = {**(old if same else {}), **meta, "model_id": model_id,
             "status": old["status"] if same else status,
             "registered_utc": old["registered_utc"] if same else _now()}
    if old and not same and (reg.get("production") or {}).get("model_id") == model_id:
        reg["production"] = None
        reg["history"].append({"utc": _now(), "event": "production_cleared", "model_id": model_id,
                               "reason": "artifact changed after approval"})
    reg["models"][model_id] = entry
    reg["history"].append({"utc": _now(), "event": "registered", "model_id": model_id, "status": entry["status"]})
    save(reg, path)
    return entry


def record_gate(model_id: str, result: dict, path: Path | None = None) -> dict:
    reg = load(path)
    m = reg["models"][model_id]
    m["gate"] = result
    if m["status"] != "legacy_incumbent":
        m["status"] = "candidate" if result["passed"] else "rejected"
    reg["history"].append({"utc": _now(), "event": "gate_evaluated", "model_id": model_id, "passed": result["passed"],
                           "failed_checks": [c["id"] for c in result["checks"] if c["status"] != "pass"]})
    save(reg, path)
    return m


def promote(model_id: str, approver: str, path: Path | None = None, approvals: Path | None = None) -> dict:
    """Point production at `model_id`. Refused unless its latest gate result passed every check for the artifact hash
    that is on disk now."""
    reg = load(path)
    m = reg["models"].get(model_id)
    if m is None:
        raise ValueError(f"{model_id} is not registered")
    g = m.get("gate")
    if not g or not g.get("passed"):
        failed = [c["id"] for c in (g or {}).get("checks", []) if c["status"] != "pass"]
        raise PermissionError(f"{model_id} has not passed the release gate (failed or not evaluable: {failed or 'not evaluated'})")
    art = BACKEND_DIR / m["artifact_path"]
    if file_sha256(art) != g["artifact_file_sha256"]:
        raise PermissionError(f"{model_id}: the artifact on disk differs from the one the gate evaluated")
    rec = {"model_id": model_id, "version": m.get("version"), "artifact_path": m["artifact_path"],
           "artifact_file_sha256": g["artifact_file_sha256"], "approved_utc": _now(), "approver": approver,
           "gate": g}
    ap = (approvals or APPROVALS)
    ap.mkdir(parents=True, exist_ok=True)
    (ap / f"{model_id}.json").write_text(json.dumps(rec, indent=1))
    m["status"] = "approved"
    reg["production"] = {k: rec[k] for k in ("model_id", "version", "artifact_path", "artifact_file_sha256", "approved_utc")}
    reg["history"].append({"utc": rec["approved_utc"], "event": "promoted", "model_id": model_id, "approver": approver})
    save(reg, path)
    return rec


def production(path: Path | None = None) -> dict:
    """The approved production entry, verified against the artifact on disk. Raises NoApprovedModel otherwise."""
    reg = load(path)
    p = reg.get("production")
    if not p:
        raise NoApprovedModel("no model has passed the release gate; the food-insecurity forecast is validation-pending")
    art = BACKEND_DIR / p["artifact_path"]
    if not art.exists() or file_sha256(art) != p["artifact_file_sha256"]:
        raise NoApprovedModel(f"approved artifact for {p['model_id']} is missing or was modified; refusing to serve it")
    return p


def summary(path: Path | None = None) -> dict:
    reg = load(path)
    return {"production": reg.get("production"),
            "models": [{"model_id": k, "version": v.get("version"), "status": v["status"], "target": v.get("target"),
                        "gate_passed": (v.get("gate") or {}).get("passed"),
                        "failed_checks": [c["id"] for c in (v.get("gate") or {}).get("checks", []) if c["status"] != "pass"],
                        "gate_evaluated_utc": (v.get("gate") or {}).get("evaluated_utc")}
                       for k, v in reg["models"].items()],
            "history": reg["history"][-50:]}

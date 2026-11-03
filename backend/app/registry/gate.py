"""
Release gate. Every check reads evidence computed by the candidate's own evaluation code (its `evidence_builder`) and
runs the candidate's tests; nothing is taken from a hand-written claim. A candidate passes only if every check passes.
A check that cannot be evaluated because the data do not exist is "not_evaluable", which is not a pass, except where
the directive makes the check conditional on data ("independent validation where data permit").

    python -m app.registry.gate evaluate <model_id>
    python -m app.registry.gate promote <model_id> --approver "<name>"
    python -m app.registry.gate status

THRESHOLDS are fixed constants (digest recorded in every result). They follow the project's locked class rule (FI9-Z)
and the directive: accuracy >= 0.75 together with balanced accuracy, HIGH recall, calibration and skill over the best
simple baseline, on at least 20 chronologically held-out targets with at least 10 HIGH cases.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone

from app import registry as R
from app.paths import BACKEND_DIR

THRESHOLDS = {
    "accuracy_min": 0.75, "balanced_accuracy_min": 0.70, "high_recall_min": 0.60, "high_precision_min": 0.50,
    "ece_max": 0.10, "interval_coverage_tolerance": 0.05, "chronological_targets_min": 20, "chronological_high_min": 10,
    "required_groups": ["market", "climate", "employment", "poverty", "news"],
    "required_families": ["A1", "A2", "A3", "C1", "C2", "C3", "C4", "E1", "E2", "V1", "N1", "H1"],
    "required_n1": "improved",
}
THRESHOLDS_SHA256 = hashlib.sha256(json.dumps(THRESHOLDS, sort_keys=True).encode()).hexdigest()


def _c(cid: str, name: str, status: str, evidence, critical: bool = True) -> dict:
    return {"id": cid, "name": name, "status": status, "critical": critical, "evidence": evidence}


def _run_tests(nodes: list[str]) -> dict:
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *nodes]
    p = subprocess.run(cmd, cwd=BACKEND_DIR, capture_output=True, text=True)
    tail = [line for line in p.stdout.splitlines() if line.strip()][-1:] or [p.stderr[-300:]]
    return {"command": " ".join(["python", *cmd[1:]]), "returncode": p.returncode, "summary": tail[0]}


def checks(ev: dict, tests: dict) -> list[dict]:
    T = THRESHOLDS
    out = []
    tgt = ev["target"]
    out.append(_c("B1", "Model training completed (sealed artifact loads, hash verified)",
                  "pass" if ev["artifact_loads"] else "fail", {"artifact": ev["artifact_path"]}))
    missing_f = [f for f in T["required_families"] if f not in ev["families_used"]]
    missing_g = [g for g in T["required_groups"] if g not in ev["groups_used"]]
    out.append(_c("B2", "All required features verified (five groups, twelve families in the model)",
                  "pass" if not (missing_f or missing_g) else "fail",
                  {"families_used": ev["families_used"], "missing_families": missing_f, "missing_groups": missing_g}))
    out.append(_c("B3", "Improved N1 integrated in the predictive pipeline",
                  "pass" if ev.get("n1_version") == T["required_n1"] else "fail", {"n1_version": ev.get("n1_version")}))
    out.append(_c("B4", "Data and release-date audits", "pass" if tests["release"]["returncode"] == 0 else "fail",
                  {**tests["release"], "notes": ev.get("release_notes")}))
    out.append(_c("B5", "Leakage checks", "pass" if tests["leakage"]["returncode"] == 0 else "fail", tests["leakage"]))
    ch = ev.get("chronological")
    if not ch:
        out.append(_c("B6", "Chronological evaluation on the food-insecurity target", "not_evaluable",
                      ev.get("chronological_note")))
    else:
        ok = ch["n_targets"] >= T["chronological_targets_min"] and ch["n_high"] >= T["chronological_high_min"]
        out.append(_c("B6", "Chronological evaluation on the food-insecurity target", "pass" if ok else "fail", ch))
    ind = ev.get("independent") or {}
    out.append(_c("B7", "Independent validation where data permit",
                  "pass" if ind.get("passed") else ("fail" if ind.get("applicable") else "pass"), ind, critical=False))
    bl = (ch or {}).get("baselines")
    out.append(_c("B8", "Beats the best simple baseline on the target", "not_evaluable" if not bl else
                  ("pass" if bl["model_brier"] < min(bl["baseline_brier"].values()) else "fail"), bl))
    m = (ch or {}).get("metrics")
    if not m:
        out.append(_c("B9", "Accuracy and class-sensitive metrics on the target", "not_evaluable", None))
    else:
        ok = (m["accuracy"] >= T["accuracy_min"] and m["balanced_accuracy"] >= T["balanced_accuracy_min"]
              and m["high_recall"] >= T["high_recall_min"] and m["high_precision"] >= T["high_precision_min"])
        out.append(_c("B9", "Accuracy and class-sensitive metrics on the target", "pass" if ok else "fail", m))
    cal = ev.get("calibration") or {}
    cov_ok = cal.get("interval_coverage") is not None and \
        cal["interval_coverage"] >= cal["interval_nominal"] - T["interval_coverage_tolerance"]
    ece_ok = cal.get("ece") is not None and cal["ece"] <= T["ece_max"]
    out.append(_c("B10", "Calibration and uncertainty", "pass" if (cov_ok and ece_ok) else "fail", cal))
    geo = ev.get("geographic") or {}
    out.append(_c("B11", "Geographic generalization at the served resolution",
                  {True: "pass", False: "fail", None: "not_evaluable"}[geo.get("passed_at_served_resolution")], geo))
    hz = ev.get("horizon") or {}
    out.append(_c("B12", "Forecast horizon justified on the target", "pass" if hz.get("validated_leads") else "not_evaluable", hz))
    gc = ev.get("group_contribution") or {}
    untested = [g for g in T["required_groups"] if not (gc.get(g) or {}).get("tested_out_of_sample")]
    out.append(_c("B13", "Five-group contribution analysis (out-of-sample ablation)", "pass" if not untested else "fail",
                  {"untested_groups": untested, "groups": gc}))
    out.append(_c("B14", "All automated tests pass", "pass" if tests["all"]["returncode"] == 0 else "fail", tests["all"]))
    docs = [d for d in ev.get("documents", []) if (BACKEND_DIR.parent / d).exists()]
    out.append(_c("B15", "Model card and methodology report", "pass" if len(docs) == len(ev.get("documents", [])) and docs else "fail",
                  {"documents": ev.get("documents"), "found": docs}))
    out.append(_c("A1", "Valid food-insecurity target (not a proxy)",
                  "pass" if tgt.get("is_food_insecurity_measurement") else "fail", tgt))
    return out


def evaluate(model_id: str, path=None) -> dict:
    reg = R.load(path)
    m = reg["models"][model_id]
    mod, fn = m["evidence_builder"].split(":")
    ev = getattr(importlib.import_module(mod), fn)()
    t = m["tests"]
    tests = {k: _run_tests(t[k]) for k in ("release", "leakage", "all")}
    cs = checks(ev, tests)
    passed = all(c["status"] == "pass" for c in cs)
    res = {"model_id": model_id, "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "thresholds": THRESHOLDS, "thresholds_sha256": THRESHOLDS_SHA256,
           "artifact_file_sha256": R.file_sha256(BACKEND_DIR / m["artifact_path"]), "passed": passed,
           "decision": "eligible for promotion" if passed else "REJECTED: not eligible for the dashboard",
           "checks": cs, "evidence": ev}
    R.record_gate(model_id, res, path)
    out = R.DIR / "gate_results"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{model_id}.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m app.registry.gate")
    ap.add_argument("cmd", choices=["evaluate", "promote", "status"])
    ap.add_argument("model_id", nargs="?")
    ap.add_argument("--approver", default=None)
    a = ap.parse_args()
    if a.cmd == "status":
        print(json.dumps(R.summary(), indent=1))
    elif a.cmd == "evaluate":
        r = evaluate(a.model_id)
        print(json.dumps({"model_id": r["model_id"], "passed": r["passed"], "decision": r["decision"],
                          "checks": [(c["id"], c["status"]) for c in r["checks"]]}, indent=1))
    else:
        if not a.approver:
            raise SystemExit("--approver is required")
        print(json.dumps(R.promote(a.model_id, a.approver), indent=1, default=str))


if __name__ == "__main__":
    main()

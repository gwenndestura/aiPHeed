"""
Quarterly regeneration of the approved E168 forecast (Part 11 of the 2026-11-07 completion brief).

stage   (scheduler, or by hand) Issue at the start of the current quarter, Asia/Manila (app.quarterly.target): runs the
        frozen E168 procedure (app.e168.serve._forecast, the same path as validation) for Leads 1-3, records each trigger
        group's contribution (app.e168.dashboard_export), validates the result and writes it atomically to
        data/e168/issues/<issue>/ (live.json, dashboard_rows.csv, manifest.json). It never changes what is served.
promote (owner only) Re-checks the staged issue, registers it as the e168-lgbm-1.0 artifact and promotes it through the
        registry (app.registry.promote, approver recorded). Only then do the outlook, map, LGU ranking, explanations and
        alerts move to it. Earlier issues stay on disk for reproducibility.

Safeguards: a lock file against duplicate runs; an existing issue is never regenerated; stale inputs, missing provinces,
wrong target quarters, probabilities outside 0-1, class/probability mismatches and model-version mismatches stop the run;
files are written to a temporary folder and renamed only when complete.

    python -m app.e168.regenerate stage [--issue 2027-Q1]
    python -m app.e168.regenerate promote --issue 2027-Q1 --approver "<name>"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone

import pandas as pd

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
ISSUES = D / "e168" / "issues"
MODEL_ID = "e168-lgbm-1.0"
PROVINCES = {"Batangas", "Cavite", "Laguna", "Quezon", "Rizal"}
LEADS = (1, 2, 3)
INPUTS = ["e152/out/local_panel.parquet", "e151/out/news_panel.parquet", "hfias/clean/enns_hfias.csv"]


class RegenerationError(RuntimeError):
    pass


def current_issue() -> str:
    from app.quarterly.target import forecast_target
    o = forecast_target()["origin"]                      # e.g. 2026-10-01: the first day of the issue quarter
    return f"{o[:4]}-Q{(int(o[5:7]) - 1) // 3 + 1}"


def _sha(path) -> str | None:
    p = D / path
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _check_fresh(issue: str) -> dict:
    from app.fi5.target import qindex, qlabel
    i = qindex(issue)
    lp = pd.read_parquet(D / "e152" / "out" / "local_panel.parquet", columns=["qi"])
    newest = int(lp["qi"].max())
    if newest < i - 2:
        raise RegenerationError(f"stale inputs: provincial panel ends {qlabel(newest)}, issue {issue} needs {qlabel(i - 2)} or later")
    return {"provincial_panel_newest_quarter": qlabel(newest)}


def validate(issue: str, rows: list[dict], dash: pd.DataFrame) -> None:
    from app.fi5.target import qindex, qlabel
    i = qindex(issue)
    problems = []
    for lead in LEADS:
        got = {r["province"] for r in rows if r["lead"] == lead}
        if got != PROVINCES:
            problems.append(f"lead {lead}: provinces {sorted(got)}")
    for r in rows:
        if r["target_quarter"] != qlabel(i + r["lead"]):
            problems.append(f"{r['province']} lead {r['lead']}: target {r['target_quarter']}")
        if not (0.0 <= r["p_high"] <= 1.0) or r["risk_class"] != ("HIGH" if r["p_high"] >= 0.5 else "LOW"):
            problems.append(f"{r['province']} lead {r['lead']}: probability/class {r['p_high']}/{r['risk_class']}")
        if not (0 < r["score_pct"] < 100) or "leaves=" not in r["config"]:
            problems.append(f"{r['province']} lead {r['lead']}: score or LightGBM configuration missing")
    if len(dash) != len(rows) or dash[["probability", "score_pct"]].isna().any().any() or set(dash["model"]) != {MODEL_ID}:
        problems.append("dashboard rows incomplete or model version mismatch")
    if problems:
        raise RegenerationError("; ".join(problems))


def stage(issue: str | None = None) -> dict:
    from app.e168 import dashboard_export as X
    from app.e168 import serve as SV
    issue = issue or current_issue()
    final = ISSUES / issue
    if (final / "live.json").exists():
        return {"issue": issue, "status": "exists", "path": str(final)}
    ISSUES.mkdir(parents=True, exist_ok=True)
    lock = ISSUES / ".lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return {"issue": issue, "status": "already running", "lock": str(lock)}
    tmp = ISSUES / f".{issue}.tmp"
    try:
        os.write(fd, issue.encode())
        fresh = _check_fresh(issue)
        dash = pd.concat([X._lead(l, issue) for l in LEADS], ignore_index=True)
        H = json.loads((D / "e168" / "out" / "lead_horizon.json").read_text())
        acc = {int(k): {"accuracy": v["accuracy"], "high_recall": v["high_recall"], "persistence_accuracy": v["persistence_accuracy"],
                        "beats_persistence": v["beats_persistence_C2"]} for k, v in H["leads"].items()}
        rows = [{"province": r["province"], "lead": int(r["lead"]), "target_quarter": r["quarter"], "score_pct": float(r["score_pct"]),
                 "range90_pct": [float(r["range90_low"]), float(r["range90_high"])], "p_high": float(r["probability"]),
                 "risk_class": r["class"], "config": r["config"]} for _, r in dash.iterrows()]
        validate(issue, rows, dash)
        doc = {"model": MODEL_ID, "name": "E168 LightGBM-only (survey baseline + constrained LightGBM change + calibration layer)",
               "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "issue_quarter": issue,
               "target": "HFIAS moderate+severe household food insecurity, HIGH at 50 %", "provinces": rows, "accuracy_by_lead": acc,
               "acceptance_basis": "owner-defined (2026-11-07): accuracy >= 75 % and significantly better than reusing the latest survey (Brier CI < 0) at each served lead",
               "served_leads": [l for l in LEADS if acc[l]["accuracy"] >= 0.75 and acc[l]["beats_persistence"]],
               "statistical_reliability": "E156 C1-C6 not passed at Lead 1 (maximum reliable lead 0 under that stricter test; 72 validation rows from 3 survey rounds)",
               "seals": {"ENNS2022": "f8228fae"}}
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        (tmp / "live.json").write_text(json.dumps(doc, indent=1), newline="\n")
        dash.to_csv(tmp / "dashboard_rows.csv", index=False, lineterminator="\n")
        man = {"issue": issue, "status": "staged", "model": MODEL_ID, "procedure": "app.e168.serve._forecast (frozen E168, validation feature path)",
               "created_utc": doc["created_utc"], "inputs_sha256": {p: _sha(p) for p in INPUTS}, "freshness": fresh,
               "live_sha256": hashlib.sha256((tmp / "live.json").read_bytes()).hexdigest(),
               "promote": f"python -m app.e168.regenerate promote --issue {issue} --approver \"<name>\""}
        (tmp / "manifest.json").write_text(json.dumps(man, indent=1), newline="\n")
        os.replace(tmp, final)
        return {"issue": issue, "status": "staged", "path": str(final)}
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)
        shutil.rmtree(tmp, ignore_errors=True)


def promote(issue: str, approver: str) -> dict:
    from app import registry as R
    from app.e168 import owner_gate as OG
    d = ISSUES / issue
    man = json.loads((d / "manifest.json").read_text())
    live = json.loads((d / "live.json").read_text())
    if hashlib.sha256((d / "live.json").read_bytes()).hexdigest() != man["live_sha256"]:
        raise RegenerationError("staged artifact changed after staging")
    validate(issue, live["provinces"], pd.read_csv(d / "dashboard_rows.csv"))
    art = str((d / "live.json").relative_to(BACKEND_DIR)).replace("\\", "/")
    g = OG.evaluate()                                    # O1-O7 on the frozen evaluation (unchanged procedure)
    if not g["passed"]:
        raise RegenerationError(f"owner gate failed: {[c['id'] for c in g['checks'] if c['status'] != 'pass']}")
    g["artifact_file_sha256"] = R.file_sha256(d / "live.json")
    R.register(MODEL_ID, {"version": f"E168 LightGBM, issue {issue}", "artifact_path": art, "artifact_sha256": g["artifact_file_sha256"],
                          "target": "HFIAS moderate+severe household food insecurity by province; HIGH at 50 %",
                          "note": f"Quarterly issue {issue} of the frozen E168 procedure."}, "candidate")
    R.record_gate(MODEL_ID, g)
    rec = R.promote(MODEL_ID, approver)
    man["status"], man["promoted_utc"], man["approver"] = "promoted", rec.get("approved_utc"), approver
    (d / "manifest.json").write_text(json.dumps(man, indent=1), newline="\n")
    return {"issue": issue, "status": "promoted", "artifact": art}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stage", "promote"])
    ap.add_argument("--issue")
    ap.add_argument("--approver", default="")
    a = ap.parse_args()
    if a.cmd == "stage":
        print(json.dumps(stage(a.issue), indent=1))
    else:
        if not (a.issue and a.approver):
            raise SystemExit("--issue and --approver are required")
        print(json.dumps(promote(a.issue, a.approver), indent=1))

"""E53 prospective evaluation (PROTOCOL 7): score every frozen 2027 forecast against the published PS outcome and the
predeclared baselines (persistence, always HIGH, always LOW). Frozen files are only read and hash-checked, never
edited. Until an outcome is published the quarter is reported as pending.

    backend/venv/Scripts/python.exe -B runner/e53_prospective.py [labels_csv]
      labels_csv: PS labels with columns province_code,q,PS (default: E51 data/labels_cpi.csv, re-exported when the
      2027 CPI is published); persistence from E51 data/persistence_cpi.csv (PS_last at the origin)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

E53 = Path(__file__).resolve().parents[1]
EXP = E53.parent
FROZEN = sorted((EXP / "E52_Objectives_Acceptance" / "frozen").glob("*.json")) + sorted((E53 / "frozen").glob("*.json"))
NAMES = {"034100000": "Batangas", "042100000": "Cavite", "043400000": "Laguna", "045600000": "Quezon", "045800000": "Rizal"}


def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def check(f: Path) -> dict:
    sha = (f.parent / (f.stem + ".sha256")).read_text().split()[0]
    if hashlib.sha256(f.read_bytes()).hexdigest() != sha:
        raise SystemExit(f"{f.name} was modified after freezing")
    return json.loads(f.read_text())


def main():
    import csv
    lab_path = Path(sys.argv[1]) if len(sys.argv) > 1 else EXP / "E51_Target_Definition" / "data" / "labels_cpi.csv"
    with lab_path.open() as fh:
        lab = {(r["province_code"], int(r["q"])): int(r["PS"]) for r in csv.DictReader(fh) if r["PS"] != ""}
    pers_path = EXP / "E51_Target_Definition" / "data" / "persistence_cpi.csv"
    with pers_path.open() as fh:
        pers = {(int(r["t"]), r["province_code"]): r["PS_last"] for r in csv.DictReader(fh)}
    code = {v: k for k, v in NAMES.items()}
    report = {}
    for f in FROZEN:
        fz = check(f)
        q = qi(fz["target_quarter"])
        rows = []
        for name, v in fz["provinces"].items():
            p = v.get("p", v.get("p_price_pressure"))
            y = lab.get((code[name], q))
            pl = pers.get((q - 2, code[name]))
            rows.append({"province": name, "p": p, "decision": v["decision"], "observed": y,
                         "persistence": None if pl in (None, "") else int(float(pl))})
        known = [r for r in rows if r["observed"] is not None]
        if len(known) < len(rows):
            report[f.name] = {"target_quarter": fz["target_quarter"], "status": "pending (outcome not yet published)",
                              "frozen_sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "forecasts": rows}
            continue
        y = [r["observed"] for r in known]
        dec = [int(r["decision"] == "HIGH") for r in known]
        brier = sum((r["p"] - r["observed"]) ** 2 for r in known) / len(known)
        report[f.name] = {"target_quarter": fz["target_quarter"], "status": "scored",
                          "accuracy": sum(int(a == b) for a, b in zip(dec, y)) / len(y), "brier": brier,
                          "persistence_accuracy": (sum(int(r["persistence"] == r["observed"]) for r in known
                                                       if r["persistence"] is not None) / len(known)),
                          "always_HIGH_brier": sum((1 - v) ** 2 for v in y) / len(y),
                          "always_LOW_brier": sum(v ** 2 for v in y) / len(y), "forecasts": rows}
    out = E53 / "prospective_status.json"
    out.write_text(json.dumps(report, indent=1))
    for k, v in report.items():
        print(k, v["target_quarter"], v["status"], {kk: v[kk] for kk in ("accuracy", "brier") if kk in v})


if __name__ == "__main__":
    main()

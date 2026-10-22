"""E99-F Q9: version identity. SHA-256 of the served model artifacts and serving code on this branch, compared with the
E98 commit (a42de8c) and with production (origin/final-system-v2), using LF-normalised content (git autocrlf).
Run from backend/:  py -3.13 .../manifest.py [out.json]"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ARTIFACTS = ["data/thesis/firi2_history.csv", "data/thesis/firi2_evaluation.json", "data/thesis/firi2_reference.json",
             "data/thesis/firi_anchors.json", "data/thesis/final_evaluation.json", "data/e58/e58_record.json",
             "data/inputs/sws_rounds.csv", "data/inputs/lgu_vulnerability.csv"]
CODE = ["app/ml/inference/thesis_system.py", "app/ml/inference/firi.py", "app/ml/inference/e41_lead2.py",
        "app/services/dashboard.py", "app/quarterly/target.py", "app/quarterly/lgu_poverty.py", "app/quarterly/lgu_audit.py"]
REFS = {"e98": "a42de8c", "production": "origin/final-system-v2"}


def norm_sha(b: bytes | None) -> str | None:
    return None if b is None else hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def at(ref: str, path: str) -> bytes | None:
    r = subprocess.run(["git", "show", f"{ref}:backend/{path}"], capture_output=True, cwd="..")
    return r.stdout if r.returncode == 0 else None


def main(out: str | None = None) -> dict:
    res = {"refs": {k: subprocess.run(["git", "rev-parse", v], capture_output=True, text=True, cwd="..").stdout.strip()
                    for k, v in REFS.items()}, "files": {}}
    for p in ARTIFACTS + CODE:
        here = norm_sha(Path(p).read_bytes())
        row = {"kind": "artifact" if p in ARTIFACTS else "code", "sha256_lf": here}
        for k, ref in REFS.items():
            row[f"same_as_{k}"] = norm_sha(at(ref, p)) == here
        res["files"][p] = row
    res["artifacts_identical_to_production"] = all(v["same_as_production"] for p, v in res["files"].items() if v["kind"] == "artifact")
    res["artifacts_identical_to_e98"] = all(v["same_as_e98"] for p, v in res["files"].items() if v["kind"] == "artifact")
    res["code_changed_vs_e98"] = [p for p, v in res["files"].items() if v["kind"] == "code" and not v["same_as_e98"]]
    res["code_differs_from_production"] = [p for p, v in res["files"].items() if v["kind"] == "code" and not v["same_as_production"]]
    if out:
        Path(out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    r = main(sys.argv[1] if len(sys.argv) > 1 else None)
    print(json.dumps({k: v for k, v in r.items() if k != "files"}, indent=1))
    for p, v in r["files"].items():
        print(f"  {p:42s} e98={v['same_as_e98']} prod={v['same_as_production']}")

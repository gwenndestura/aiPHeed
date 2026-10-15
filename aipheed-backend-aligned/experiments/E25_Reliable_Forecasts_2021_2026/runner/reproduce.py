"""E25 reproducibility (C8): compare two runs byte for byte (prediction seals, details, fold metadata, results).
Usage: python -B runner/reproduce.py <run_id_1> <run_id_2> [<monthly_1> <monthly_2>]  -> runs/reproducibility.json"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(a: str, b: str, ma: str | None = None, mb: str | None = None):
    A, B = EXP / "runs" / a, EXP / "runs" / b
    out = {"run_1": a, "run_2": b, "files": {}}
    for f in sorted(p.name for p in A.iterdir() if p.is_file() and p.name != "manifest.json"):
        out["files"][f] = {"sha256_run1": sha(A / f), "sha256_run2": sha(B / f) if (B / f).exists() else None}
        out["files"][f]["identical"] = out["files"][f]["sha256_run1"] == out["files"][f]["sha256_run2"]
    s1 = json.loads((A / "SEALS.json").read_text())
    s2 = json.loads((B / "SEALS.json").read_text())
    out["prediction_seals_identical"] = s1 == s2
    m1 = json.loads((A / "manifest.json").read_text())
    m2 = json.loads((B / "manifest.json").read_text())
    core = ("run_e25.py", "score_e25.py", "e25lib.py", "e23_lib.py", "pcf.py", "guard.py")   # modules the run imports
    out["run_code_identical"] = all(m1["runner_sha256"].get(f) == m2["runner_sha256"].get(f) for f in core)
    out["run_code_sha256"] = {f: m1["runner_sha256"].get(f) for f in core}
    out["other_runner_files_added_between_runs"] = sorted(set(m2["runner_sha256"]) - set(m1["runner_sha256"]))
    out["all_files_identical"] = all(v["identical"] for v in out["files"].values())
    if ma and mb:
        x = json.loads((EXP / "runs" / ma / "results_monthly.json").read_text())["seal"]
        y = json.loads((EXP / "runs" / mb / "results_monthly.json").read_text())["seal"]
        out["monthly"] = {"run_1": ma, "run_2": mb, "seal_1": x, "seal_2": y, "identical": x == y,
                          "results_identical": sha(EXP / "runs" / ma / "results_monthly.json") ==
                                               sha(EXP / "runs" / mb / "results_monthly.json")}
    (EXP / "runs" / "reproducibility.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "files"}, indent=1))
    for f, v in out["files"].items():
        print(("OK   " if v["identical"] else "DIFF ") + f)


if __name__ == "__main__":
    main(*sys.argv[1:])

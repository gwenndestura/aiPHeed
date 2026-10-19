"""E62 r8: every frozen / sealed artifact of E56-E61 still matches its own freeze record; E56-E58 tracked files are
unchanged against HEAD; the served E56 model files match their manifest.

    backend/venv/Scripts/python.exe -B runner/r8_frozen_check.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

E62 = Path(__file__).resolve().parents[1]
EXP = E62.parent
ROOT = EXP.parents[1]


def sha(p: Path, lf: bool = False) -> str:
    b = p.read_bytes()
    return hashlib.sha256(b.replace(b"\r\n", b"\n") if lf else b).hexdigest()


def main():
    out = []
    for f in sorted(EXP.glob("E5[6-9]*/**/*.sha256")) + sorted(EXP.glob("E6[01]*/**/*.sha256")):
        target = f.with_suffix("")
        want = f.read_text().split()[0]
        if target.exists():
            out.append({"file": str(target.relative_to(EXP)), "ok": sha(target) == want or sha(target, True) == want})
    for f in sorted(EXP.glob("E5[6-9]*/runner/*SHA256.txt")) + sorted(EXP.glob("E6[01]*/runner/*SHA256.txt")):
        want = f.read_text().split()[0]
        name = {"PROTOCOL_SHA256.txt": "PROTOCOL.md", "ADDENDUM_1_SHA256.txt": "PROTOCOL_ADDENDUM_1.md",
                "CLASSIFIER_V2_SHA256.txt": "runner/n4_classifier.py"}.get(f.name)
        if name is None:
            continue
        target = f.parents[1] / name
        if target.exists():
            out.append({"file": str(target.relative_to(EXP)), "ok": sha(target) == want or sha(target, True) == want})
    man = json.loads((ROOT / "backend/data/e56/model/manifest.json").read_text())
    for name, want in man.items():
        p = ROOT / "backend/data/e56/model" / name
        out.append({"file": f"backend/data/e56/model/{name}", "ok": sha(p) == want or sha(p, True) == want})
    diff = subprocess.run(["git", "status", "--porcelain", "--", "aipheed-backend-aligned/experiments/E56_LightGBM_Optimization",
                           "aipheed-backend-aligned/experiments/E57_E56_Rolling_Origin_Test",
                           "aipheed-backend-aligned/experiments/E58_Rising_Stress_Early_Warning", "backend/data/e56",
                           "backend/data/e58"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    res = {"checked": len(out), "failed": [o["file"] for o in out if not o["ok"]], "files": out,
           "git_status_E56_E58_and_served_data": diff or "clean"}
    (E62 / "out" / "r8_frozen_check.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "files"}, indent=1))


if __name__ == "__main__":
    main()

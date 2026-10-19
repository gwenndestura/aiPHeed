"""E63 write guard: SHA-256 manifest of the frozen folders E56-E62 and backend/data (main checkout).

    python -B runner/e63_guard.py snapshot before   -> out/guard_before.json
    python -B runner/e63_guard.py snapshot after    -> out/guard_after.json, then compares with before
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e63_lib as H  # noqa: E402

ROOTS = [H.EXP / n for n in ("E56_LightGBM_Optimization", "E57_E56_Rolling_Origin_Test", "E58_Rising_Stress_Early_Warning",
                             "E59_E58_Validation_Audit", "E60_E58_Accuracy_Optimization",
                             "E61_E58_Low_Forecast_Investigation", "E62_Final_System_Audit")]
ROOTS.append(H.L.ROOT / "backend" / "data")


def manifest() -> dict:
    out = {}
    for r in ROOTS:
        for f in sorted(r.rglob("*")):
            if f.is_file():
                out[str(f.relative_to(H.L.ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def main():
    tag = sys.argv[2]
    m = manifest()
    (H.E63 / "out" / f"guard_{tag}.json").write_text(json.dumps(m, indent=0))
    print(tag, len(m), "files hashed")
    if tag == "after":
        b = json.loads((H.E63 / "out" / "guard_before.json").read_text())
        changed = sorted(k for k in set(b) | set(m) if b.get(k) != m.get(k))
        res = {"files_before": len(b), "files_after": len(m), "changed_added_or_removed": changed}
        (H.E63 / "out" / "guard_check.json").write_text(json.dumps(res, indent=1))
        print("changed/added/removed:", changed if changed else "none")


if __name__ == "__main__":
    main()

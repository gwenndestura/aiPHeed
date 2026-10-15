"""E26: confirm that E25 (including the sealed prospective forecasts) is unchanged. Hash-only: every file listed in
E25's own E25_FILES_SHA256.txt is re-hashed and compared; no file content is parsed except the list itself. Nothing is
typed. Run without the data guard because it reads bytes for hashing only.
Usage: python -B runner/verify_e25_unchanged.py   -> runs/e25_unchanged.json"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
E25 = EXP.parent / "E25_Reliable_Forecasts_2021_2026"
SEAL = "runs/SEAL_E25_20261014T002548Z/"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    listing = (E25 / "E25_FILES_SHA256.txt").read_text(encoding="utf-8").splitlines()
    rows, bad = [], []
    for ln in listing:
        if not ln.strip():
            continue
        want, rel = ln.split(None, 1)
        p = E25 / rel
        got = sha(p) if p.exists() else None
        rows.append({"file": rel, "match": got == want})
        if got != want:
            bad.append({"file": rel, "expected": want, "actual": got})
    seal = [r for r in rows if r["file"].replace("\\", "/").startswith(SEAL)]
    out = {"checked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "e25_list_sha256": sha(E25 / "E25_FILES_SHA256.txt"), "files": len(rows),
           "mismatches": bad, "seal_files": [r["file"] for r in seal],
           "seal_unchanged": bool(seal) and all(r["match"] for r in seal), "all_unchanged": not bad}
    (EXP / "runs" / "e25_unchanged.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "seal_files"}, indent=1), "\nseal files:", out["seal_files"])
    if bad:
        raise SystemExit("E25 differs from its hash list")


if __name__ == "__main__":
    main()

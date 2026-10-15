"""Record (or check) the SHA-256 of every preserved artifact.

    python -B runner/e35_preserve.py record   -> preservation/BASELINE_MANIFEST.json (once, before any E35 fit)
    python -B runner/e35_preserve.py check    -> exit 1 if any preserved file changed, appeared or disappeared
"""
from __future__ import annotations

import json
import sys

import e35_common as E

OUT = E.E35 / "preservation" / "BASELINE_MANIFEST.json"


def main(mode: str) -> int:
    now = E.preserved_manifest()
    if mode == "record":
        if OUT.exists():
            raise SystemExit("baseline already recorded; it is never overwritten")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(json.dumps({"files": now, "n_files": len(now)}, indent=1).encode())
        print(f"recorded {len(now)} files")
        return 0
    base = json.loads(OUT.read_text(encoding="utf-8"))["files"]
    changed = sorted(k for k in base if k in now and now[k] != base[k])
    missing = sorted(set(base) - set(now))
    added = sorted(set(now) - set(base))
    print(f"preserved files: {len(base)}; changed {len(changed)}, missing {len(missing)}, added {len(added)}")
    for k in changed + missing + added:
        print("  ", k)
    return 1 if (changed or missing or added) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "check"))

"""E26 reproducibility: rerun sections A-C (root_cause.py), D (horizon.py) and the local power design (local_power.py) in this process and compare the bytes of
every output with the bytes before the rerun. All three are deterministic (fixed seeds, no clock in their outputs).
Usage: python -B runner/reproduce.py   -> runs/reproducibility.json"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import horizon  # noqa: E402
import local_power  # noqa: E402
import root_cause  # noqa: E402

EXP = guard.EXP
OUTPUTS = ["runs/root_cause.json", "runs/voi_predictions.csv", "runs/horizon.json", "docs/HORIZON.md",
           "runs/local_power.json"]


def hashes() -> dict:
    return {f: hashlib.sha256((EXP / f).read_bytes()).hexdigest() for f in OUTPUTS}


def main():
    before = hashes()
    root_cause.main()
    horizon.main()
    local_power.main()
    after = hashes()
    out = {"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "outputs": {f: {"before": before[f], "after": after[f], "identical": before[f] == after[f]} for f in OUTPUTS}}
    out["all_identical"] = all(v["identical"] for v in out["outputs"].values())
    (EXP / "runs" / "reproducibility.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    if not out["all_identical"]:
        raise SystemExit("E26 outputs are not reproducible")


if __name__ == "__main__":
    main()

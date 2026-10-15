"""E26: register the EXISTING E25 seal (SEAL_E25_20261014T002548Z, sealed 2026-10-14T00:25:48Z, before the logged
exposure) in prospective ledgers, one per target (T1_A and T2 have different outcomes for the same quarter). No new
forecast is made: the forecasts file is hash-verified against the seal and every entry keeps the original seal time.
Development ledgers only (the operational ledger location needs the researcher's decision).
Usage: python -B runner/import_e25_seal.py   -> runs/ledger/T1_A.jsonl, runs/ledger/T2.jsonl, runs/ledger/status.json"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
sys.path.insert(0, str(guard.EXP / "backend_dev"))
from app.quarterly import ledger as LG  # noqa: E402

SEAL = guard.E25_RUNS / "SEAL_E25_20261014T002548Z"
OUT = guard.EXP / "runs" / "ledger"
BASE = {"B1_naive_persistence": "baseline_persistence", "B1p_calibrated_persistence": "baseline_calibrated_persistence",
        "CLIM_training_rate": "reference_climatology"}           # amendment A3


def main():
    import pandas as pd
    OUT.mkdir(parents=True, exist_ok=True)
    arms = pd.read_csv(SEAL / "prospective_forecasts.csv", usecols=["target", "arm"]).drop_duplicates()
    status = {"seal": str(SEAL), "ledgers": {}}
    for target in ("T1_A", "T2"):
        path = OUT / f"{target}.jsonl"
        if not path.exists():                                  # append-only: the import is done once
            roles = {a: BASE.get(a, "candidate") for a in arms.loc[arms["target"] == target, "arm"]}
            LG.Ledger(path).import_sealed_file(seal_json=SEAL / "SEAL.json",
                                               forecasts_csv=SEAL / "prospective_forecasts.csv",
                                               arm_roles=roles, target=target)
        L2 = LG.Ledger(path)                                   # reload: verifies the hash chain from disk
        status["ledgers"][target] = {
            "entries": len(L2.entries), "chain_verified": L2.verify(),
            "arms": sorted({e["payload"]["arm"] for e in L2.seals()}),
            "targets": sorted({e["payload"]["target_quarter"] for e in L2.seals()}),
            "outcomes_recorded": sorted(L2.outcomes()),
            "a1_first_eligible_year_final_arm": L2.a1_first_eligible_year("PCF21:lead1") if target == "T1_A" else None,
            "note": ("FINAL_T1 = PCF21" if target == "T1_A" else
                     "FINAL_T2 (M4_21) was not sealed in E25: it needs July-August 2026 CPI, which is not authorized")}
    (OUT / "status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    print(json.dumps(status, indent=1))


if __name__ == "__main__":
    main()

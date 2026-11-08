"""
E132 prospective seal (protocol section 7): E132 models' forecasts for 2026-Q4 .. 2027-Q3 for the 4 SWS areas, issued
2026-11-01 with all information published by then, plus labelled model-based provincial estimates from the E132
candidate (SEAS-LLM, frozen selection rule). Write-once.

    python -I runner/e132_seal.py
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e132_run as E  # noqa: E402

sys.path.insert(0, str(E.EXP / "E131_Objectives_Resolution" / "runner"))
import e131_provincial as PV  # noqa: E402

SEALED = HERE.parent / "sealed"
AREA = SEALED / "E132_PROSPECTIVE_SEAL.csv"
PROV = SEALED / "E132_PROVINCIAL_MODEL_BASED_SEAL.csv"


def main():
    if AREA.exists() or PROV.exists():
        sys.exit("refusing to overwrite an existing E132 seal")
    X = E.X
    rr = X.rounds()
    qt = X.quarter_table(rr)
    cpi, reg, pov = X.cpi_quarterly(), X.regional_covariates(), X.poverty_area()
    E.INCOME, E.RICE = E.income_area(), E.rice_affordability()
    X.features = E.features132
    E.GROUPS132.update({k: list(v) for k, v in X.GROUPS.items()})
    E.GROUPS132["A"] = E.GROUPS132["A"] + ["riceaff_chg4"]
    E.GROUPS132["E"] = E.GROUPS132["E"] + E.INC
    X.feat_cols = E.feat_cols132
    S = E.seal(rr, qt, cpi, reg, pov)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    S.insert(0, "sealed_utc", stamp)
    S.insert(1, "candidate", "SEAS-LLM (frozen selection rule: highest Lead-2 within-tolerance share, P-DASH, shared rows)")
    SEALED.mkdir(exist_ok=True)
    AREA.write_bytes(S.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    bl = S[S.area == "balance_luzon"].rename(columns={"SEAS-LLM": "f", "SEAS-LLM_lo80": "lo80", "SEAS-LLM_hi80": "hi80"})
    rr_tab = pd.read_csv(E.EXP / "E131_Objectives_Resolution" / "out" / "x3c_relative_risk.csv")
    prov = PV.provincial_estimates(bl[["target", "lead", "f", "lo80", "hi80"]], rr_tab)
    prov["label"] = prov["label"].str.replace("Balance Luzon hunger forecast", "Balance Luzon SEAS-LLM hunger forecast")
    prov.insert(0, "sealed_utc", stamp)
    PROV.write_bytes(prov.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    (SEALED / "E132_SEAL_SHA256.txt").write_text(
        "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in (AREA, PROV)), encoding="utf-8")
    print(S[["area", "lead", "target", "y_latest", "PERSIST", "LLM", "SEAS-LLM", "SEAS-LLM_lo80", "SEAS-LLM_hi80", "ENS", "HYB-LGBM"]].round(2).to_string(index=False))
    print(prov[["province", "target", "estimate", "lo80", "hi80"]].round(2).to_string(index=False))
    print((SEALED / "E132_SEAL_SHA256.txt").read_text())


if __name__ == "__main__":
    main()

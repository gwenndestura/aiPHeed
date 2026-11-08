"""
E131 prospective seal (protocol section 9): every model's forecast for 2026-Q4 .. 2027-Q3 for the 4 SWS areas, issued
2026-10-31 with all information published by then, plus the X3c model-based provincial estimates from the E131
candidate (LLM, by the frozen selection rule). Write-once: refuses to overwrite.

    python -I runner/e131_seal.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e131_x1 as X  # noqa: E402
import e131_provincial as P  # noqa: E402

SEALED = HERE.parent / "sealed"
AREA_SEAL = SEALED / "E131_PROSPECTIVE_SEAL.csv"
PROV_SEAL = SEALED / "E131_PROVINCIAL_MODEL_BASED_SEAL.csv"


def main():
    if AREA_SEAL.exists() or PROV_SEAL.exists():
        sys.exit("refusing to overwrite an existing E131 seal")
    rr = X.rounds()
    qt = X.quarter_table(rr)
    S = X.seal(rr, qt, X.cpi_quarterly(), X.regional_covariates(), X.poverty_area())
    S.insert(0, "sealed_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    S.insert(1, "candidate", "LLM (frozen selection rule: highest Lead-2 within-tolerance share, P-DASH)")
    SEALED.mkdir(exist_ok=True)
    AREA_SEAL.write_bytes(S.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    bl = S[S.area == "balance_luzon"].rename(columns={"LLM": "f", "LLM_lo80": "lo80", "LLM_hi80": "hi80"})[["target", "lead", "f", "lo80", "hi80"]]
    rr_tab = pd.read_csv(HERE.parent / "out" / "x3c_relative_risk.csv")
    prov = P.provincial_estimates(bl, rr_tab)
    prov.insert(0, "sealed_utc", S["sealed_utc"].iloc[0])
    PROV_SEAL.write_bytes(prov.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    import hashlib
    (SEALED / "E131_SEAL_SHA256.txt").write_text(
        "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in (AREA_SEAL, PROV_SEAL)), encoding="utf-8")
    print(S[["area", "lead", "target", "y_latest", "PERSIST", "LLM", "LLM_lo80", "LLM_hi80", "DLLM", "LGBM-ALL"]].round(2).to_string(index=False))
    print(prov[["province", "target", "estimate", "lo80", "hi80", "estimate_poverty_rr_sensitivity"]].round(2).to_string(index=False))
    print((SEALED / "E131_SEAL_SHA256.txt").read_text())


if __name__ == "__main__":
    main()

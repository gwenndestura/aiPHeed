"""
E134 prospective seal (protocol section 7): E134 candidates' forecasts for 2026-Q4 .. 2027-Q3 for the 4 SWS areas, issued
2026-11-01 with all information published by then. The selected candidate HFM-X equals E133's (asserted against the
E133 seal), so E133's provincial model-based seal (76c2388a) remains the provincial seal; no new provincial file.
Write-once.

    python -I runner/e134_seal.py
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e134_run as E  # noqa: E402

R, X, L = E.R, E.X, E.L
SEALED = HERE.parent / "sealed"
AREA = SEALED / "E134_PROSPECTIVE_SEAL.csv"
ISSUE = date(2026, 11, 1)


def main():
    if AREA.exists():
        sys.exit("refusing to overwrite an existing E134 seal")
    rr = X.rounds()
    qa = X.asof(rr, ISSUE)
    assert L.qs(int(qa["qi"].max())) == "2026-Q3"
    drv = {"rice": R.Drivers("rice"), "b30": R.Drivers("b30"), "oni": R.Drivers("rice", "oni_quarter_mean")}
    adrv = E.AreaDrivers()
    e133 = pd.read_csv(E.EXP / "E133_Forecasting_Breakthrough" / "sealed" / "E133_PROSPECTIVE_SEAL.csv")
    e132 = pd.read_csv(E.EXP / "E132_Final_Methodology" / "sealed" / "E132_PROSPECTIVE_SEAL.csv")
    rows = []
    for k in L.LEADS:
        T = L.qs(L.qi("2026-Q4") - 1 + k)
        r133 = R.predict(qa, ISSUE, L.qi(T), drv)
        r134 = E.predict(qa, ISSUE, L.qi(T), drv, adrv, {m: E.VARIANTS[m] for m in ("E134-AREA-T", "E134-AREA-O")})
        for j, a in enumerate(X.AREAS):
            s = qa[qa.area == a].sort_values("qi")
            rec = {"area": a, "issue": ISSUE.isoformat(), "lead": k, "target": T, "y_latest": float(s["y"].iloc[-1]),
                   "latest_quarter": L.qs(int(s["qi"].iloc[-1])), "PERSIST": float(s["y"].iloc[-1])}
            for m, src in (("HFM-X", r133["HFM-X"]), ("E134-ONI", r133["HFM-X-PH2"]),
                           ("E134-AREA-T", r134["E134-AREA-T"]), ("E134-AREA-O", r134["E134-AREA-O"])):
                f, sd = float(src[0][j]), float(src[1][j])
                rec[m], rec[f"{m}_lo80"], rec[f"{m}_hi80"] = f, f - X.Z80 * sd, f + X.Z80 * sd
            old = e133[(e133.area == a) & (e133.target == T)].iloc[0]
            assert abs(old["HFM-X"] - rec["HFM-X"]) < 1e-9 and abs(old["HFM-X-PH2"] - rec["E134-ONI"]) < 1e-9
            seas = e132[(e132.area == a) & (e132.target == T)].iloc[0]
            sd_seas = (seas["SEAS-LLM_hi80"] - seas["SEAS-LLM_lo80"]) / (2 * X.Z80)
            sd_hfmx = (rec["HFM-X_hi80"] - rec["HFM-X_lo80"]) / (2 * X.Z80)
            rec["E134-ENS"] = (rec["HFM-X"] + float(seas["SEAS-LLM"])) / 2
            half = X.Z80 * (sd_seas + sd_hfmx) / 2
            rec["E134-ENS_lo80"], rec["E134-ENS_hi80"] = rec["E134-ENS"] - half, rec["E134-ENS"] + half
            rows.append(rec)
    S = pd.DataFrame(rows)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    S.insert(0, "sealed_utc", stamp)
    S.insert(1, "candidate", "HFM-X (E134 frozen selection rule: S-U, P-DASH, Lead-2 within, ties lower MAE); identical to E133")
    SEALED.mkdir(exist_ok=True)
    AREA.write_bytes(S.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    (SEALED / "E134_SEAL_SHA256.txt").write_text(f"{hashlib.sha256(AREA.read_bytes()).hexdigest()}  {AREA.name}\n", encoding="utf-8")
    print(S[["area", "lead", "target", "HFM-X", "E134-AREA-T", "E134-AREA-O", "E134-ONI", "E134-ENS"]].round(2).to_string(index=False))
    print((SEALED / "E134_SEAL_SHA256.txt").read_text())


if __name__ == "__main__":
    main()

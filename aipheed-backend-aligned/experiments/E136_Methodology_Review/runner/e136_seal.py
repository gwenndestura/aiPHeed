"""
E136 prospective seal: SIMPLE (challenger) and X-RED (separate prospective hypothesis, per the E136 directive) for
2026-Q4 .. 2027-Q3, 4 SWS areas, issued 2026-11-01 with information published by then. SEAS-LLM (the E136
recommendation) and HFM-X are already sealed (E132 cea5a2ec; E133 efba3235 / E134 e4f844dd). Write-once.

    python -I runner/e136_seal.py
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e136_run as T  # noqa: E402

S, E, R, X, L = T.S, T.E, T.R, T.X, T.L
SEALED = HERE.parent / "sealed"
AREA = SEALED / "E136_PROSPECTIVE_SEAL.csv"
ISSUE = date(2026, 11, 1)


def main():
    if AREA.exists():
        sys.exit("refusing to overwrite an existing E136 seal")
    rr = X.rounds()
    qa = X.asof(rr, ISSUE)
    assert L.qs(int(qa["qi"].max())) == "2026-Q3"
    drv, adrv = {"rice": R.Drivers("rice")}, E.AreaDrivers()
    rows = []
    for k in L.LEADS:
        tgt = L.qs(L.qi("2026-Q4") - 1 + k)
        out = {"SIMPLE": S.predict_cfg(qa, ISSUE, L.qi(tgt), drv, adrv, T.SIMPLE, {x: T.SIMPLE_SD for x in T.SIMPLE}),
               "X-RED": S.predict_cfg(qa, ISSUE, L.qi(tgt), drv, adrv, S.HFMX, {x: 0.5 for x in S.HFMX})}
        for j, a in enumerate(X.AREAS):
            rec = {"area": a, "issue": ISSUE.isoformat(), "lead": k, "target": tgt}
            for m, (mean, sd, _) in out.items():
                rec[m], rec[f"{m}_lo80"], rec[f"{m}_hi80"] = float(mean[j]), float(mean[j] - X.Z80 * sd[j]), float(mean[j] + X.Z80 * sd[j])
            rows.append(rec)
    D = pd.DataFrame(rows)
    D.insert(0, "sealed_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    SEALED.mkdir(exist_ok=True)
    AREA.write_bytes(D.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    (SEALED / "E136_SEAL_SHA256.txt").write_text(f"{hashlib.sha256(AREA.read_bytes()).hexdigest()}  {AREA.name}\n", encoding="utf-8")
    print(D.round(2).to_string(index=False))
    print((SEALED / "E136_SEAL_SHA256.txt").read_text())


if __name__ == "__main__":
    main()

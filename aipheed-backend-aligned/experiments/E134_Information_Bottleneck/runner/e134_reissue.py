"""
E134 prospective re-issue (E134_PROSPECTIVE_VALIDATION_PROTOCOL.md item 6): on the first day of a quarter, refit the
frozen candidate and the registered hypotheses on rounds published before that day and forecast Leads 1-4.
Write-once: sealed/E134_REISSUE_<quarter>.csv plus a line in sealed/E134_REISSUE_SHA256.txt.

    python -I runner/e134_reissue.py 2027-01-01
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e134_run as E  # noqa: E402

R, X, L = E.R, E.X, E.L
SEALED = HERE.parent / "sealed"


def reissue(issue: date) -> pd.DataFrame:
    assert issue > date(2026, 11, 1) and issue == L.qstart(L.quarter_of(issue)), "re-issue only on a quarter start after the first seal"
    rr = X.rounds()
    new = E.ROOT.parent / "E131_Objectives_Resolution" / "data" / "sws_rounds_after_2026Q3.csv"
    if new.exists():
        rr = pd.concat([rr, X.rounds(new)], ignore_index=True)
    qa = X.asof(rr, issue)
    drv = {"rice": R.Drivers("rice"), "b30": R.Drivers("b30"), "oni": R.Drivers("rice", "oni_quarter_mean")}
    adrv = E.AreaDrivers()
    D, rows = L.quarter_of(issue), []
    for k in L.LEADS:
        T = L.qs(L.qi(D) - 1 + k)
        r133 = R.predict(qa, issue, L.qi(T), drv)
        r134 = E.predict(qa, issue, L.qi(T), drv, adrv, {m: E.VARIANTS[m] for m in ("E134-AREA-T", "E134-AREA-O")})
        for j, a in enumerate(X.AREAS):
            rec = {"area": a, "issue": issue.isoformat(), "lead": k, "target": T}
            for m, src in (("HFM-X", r133["HFM-X"]), ("E134-ONI", r133["HFM-X-PH2"]),
                           ("E134-AREA-T", r134["E134-AREA-T"]), ("E134-AREA-O", r134["E134-AREA-O"])):
                rec[m], rec[f"{m}_lo80"], rec[f"{m}_hi80"] = float(src[0][j]), float(src[0][j] - X.Z80 * src[1][j]), float(src[0][j] + X.Z80 * src[1][j])
            rows.append(rec)
    return pd.DataFrame(rows)


def main(arg: str):
    issue = date.fromisoformat(arg)
    out = SEALED / f"E134_REISSUE_{L.quarter_of(issue)}.csv"
    if out.exists():
        sys.exit("refusing to overwrite an existing re-issue")
    S = reissue(issue)
    S.insert(0, "sealed_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    out.write_bytes(S.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    with open(SEALED / "E134_REISSUE_SHA256.txt", "a", encoding="utf-8") as f:
        f.write(f"{hashlib.sha256(out.read_bytes()).hexdigest()}  {out.name}\n")
    print(out.name)


if __name__ == "__main__":
    main(sys.argv[1])

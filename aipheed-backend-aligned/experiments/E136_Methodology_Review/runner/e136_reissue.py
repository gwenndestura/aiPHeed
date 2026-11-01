"""
E134 Addendum 2 quarterly re-issue: on the first day of a quarter after 2026-11-01, refit the amended primary
(SEAS-LLM) and the challengers (SIMPLE, HFM-X) on rounds published before that day, forecast Leads 1-4 for the 4 SWS
areas, and write sealed/E136_REISSUE_<quarter>.csv once, with its sha256 appended to sealed/E136_REISSUE_SHA256.txt.
Refresh the driver data (E131 CPI, E119 drivers) with releases published before the issue first; a driver that
cannot be refreshed is held at its last value by the frozen rule (log it).

    python -I runner/e136_reissue.py 2027-01-01
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
NEW_ROUNDS = T.EXP / "E131_Objectives_Resolution" / "data" / "sws_rounds_after_2026Q3.csv"
MODELS = ("SEAS-LLM", "SIMPLE", "HFM-X")


def rounds() -> pd.DataFrame:
    rr = X.rounds()
    if NEW_ROUNDS.exists():
        new = X.rounds(NEW_ROUNDS)
        assert (new["quarter"].map(L.qi) > L.qi("2026-Q3")).all()
        rr = pd.concat([rr, new], ignore_index=True)
    return rr


def reissue(issue: date) -> pd.DataFrame:
    assert issue > date(2026, 11, 1) and issue == L.qstart(L.quarter_of(issue)), "re-issue only on a quarter start after 2026-11-01"
    rr = rounds()
    qa = X.asof(rr, issue)
    upto = int(qa["qi"].max())
    drv = {"rice": R.Drivers("rice"), "b30": R.Drivers("b30"), "oni": R.Drivers("rice", "oni_quarter_mean")}
    adrv = E.AreaDrivers()
    D, rows = L.quarter_of(issue), []
    for k in L.LEADS:
        tq = L.qi(D) - 1 + k
        seas = R.S.seas_forecast(qa, upto, tq)
        simple = S.predict_cfg(qa, issue, tq, drv, adrv, T.SIMPLE, {x: T.SIMPLE_SD for x in T.SIMPLE})
        hfmx = R.predict(qa, issue, tq, drv)["HFM-X"]
        for j, a in enumerate(X.AREAS):
            s = qa[qa.area == a].sort_values("qi")
            rec = {"area": a, "issue": issue.isoformat(), "lead": k, "target": L.qs(tq),
                   "y_latest": float(s["y"].iloc[-1]), "latest_quarter": L.qs(int(s["qi"].iloc[-1]))}
            for m, f, sd in (("SEAS-LLM", seas[a]["f"], seas[a]["sd"]), ("SIMPLE", simple[0][j], simple[1][j]),
                             ("HFM-X", hfmx[0][j], hfmx[1][j])):
                rec[m], rec[f"{m}_lo80"], rec[f"{m}_hi80"] = float(f), float(f - X.Z80 * sd), float(f + X.Z80 * sd)
            rows.append(rec)
    return pd.DataFrame(rows)


def main(arg: str):
    issue = date.fromisoformat(arg)
    out = SEALED / f"E136_REISSUE_{L.quarter_of(issue)}.csv"
    if out.exists():
        sys.exit("refusing to overwrite an existing re-issue")
    D = reissue(issue)
    D.insert(0, "sealed_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    out.write_bytes(D.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    with open(SEALED / "E136_REISSUE_SHA256.txt", "a", encoding="utf-8") as f:
        f.write(f"{hashlib.sha256(out.read_bytes()).hexdigest()}  {out.name}\n")
    print(out.name)


if __name__ == "__main__":
    main(sys.argv[1])

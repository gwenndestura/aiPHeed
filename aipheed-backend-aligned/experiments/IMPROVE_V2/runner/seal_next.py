"""Issue later IMPROVE_V2 forecasts (PLAN.md section 10) into NEW sealed files; never edits an existing one.

    python seal_next.py 2027-01-01 [--data DIR]

The issue date must be the first day of a quarter and must not be in the future. Origin t = the quarter before it;
forecasts are made for leads 1 and 2 with targets >= 2027-Q1, by the carried-forward arm of each lead (results.json),
using only data published before the issue date (the same code and cut-off rules as run_iv2.py).

Data: by default the files HISTORY_RETRAIN read. With --data DIR, every file hr_lib reads from its data/ and long/
folders is read from DIR instead (place refreshed copies there: same names, same columns). News comes from backend/app
read-only. The SHA-256 of every input file used is written into the new file's ledger entry."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import iv2_lib as V

H = V.H
LEDGER = V.IV / "SEAL_LEDGER.md"
FIRST_TARGET = H.qi("2027-Q1")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("issue_date")
    ap.add_argument("--data")
    a = ap.parse_args()
    D = dt.date.fromisoformat(a.issue_date)
    if D.day != 1 or D.month not in (1, 4, 7, 10):
        raise SystemExit("the issue date must be the first day of a quarter")
    if D > dt.date.today():
        raise SystemExit("refusing: the issue date is in the future")
    out = V.IV / f"sealed_IMPROVE_V2_{D.isoformat()}.csv"
    if out.exists():
        raise SystemExit(f"refusing: {out.name} exists and is never overwritten")
    if f"| {D.isoformat()} |" in LEDGER.read_text(encoding="utf-8"):
        raise SystemExit(f"refusing: issue date {D.isoformat()} is already sealed in the ledger")
    t = (D.year * 4 + (D.month - 1) // 3) - 1
    assert H.issue(t) == D.isoformat()
    leads = [k for k in (1, 2) if t + k >= FIRST_TARGET]
    if not leads:
        raise SystemExit("no target >= 2027-Q1 at this issue date")
    if a.data:
        H.DATA = H.LONG = Path(a.data)
    used = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(list(H.DATA.glob("*.csv")) + list(H.LONG.glob("*.csv")))}
    res = json.loads((V.OUT / "results.json").read_text())
    plan = res["plan"]
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    origins = list(range(H.FIRST_ORIGIN, t + 1))
    T = V.table(d, origins)
    rows = []
    for k in leads:
        name = res["leads"][f"L{k}"]["selection"]["carried_forward"]
        arm, news = name.replace("+news", ""), name.endswith("+news")
        pooled, regression, platt = V.ARMS[arm]
        need = origins if (regression or platt) else [t]          # sigma and Platt need the arm's own history
        fs = []
        for o in need:
            kb = V.known_labels(d, o, lab)
            kb = kb[kb["area"] == "BL"]
            fs.append(V.fit_base(T, o, lab, pooled, regression, news, float(kb["y"].mean()) if len(kb) else 0.0, d))
        F = pd.concat(fs, ignore_index=True)
        if regression:
            F = V.sigma_pass(F, d, lab_bl)
        if platt:
            F = V.platt_pass(F, d, lab_bl)
            F["p_raw"] = F["p_cal"]
        f = F[(F["t"] == t) & (F["lead"] == k)].iloc[0]
        ps = H.persist_t2(d, t)
        p = float(f["p_raw"])
        rows.append({"issue_date": D.isoformat(), "origin": H.qs(t), "lead": k, "target_quarter": H.qs(t + k),
                     "arm": name, "p_high": round(p, 6), "class": "HIGH" if p >= .5 else "LOW",
                     "persist_p": ps, "newest_sws_published": f["sws_newest_published"],
                     "newest_sws_reading": float(f["h_last"]), "threshold": H.H_LINE,
                     "target": "SWS Balance Luzon involuntary hunger > 11.3% (quarter mean of non-commissioned rounds)",
                     "plan_sha256": plan, "sealed_on": dt.date.today().isoformat(), "label": "EXPLORATORY"})
    S = pd.DataFrame(rows)
    S.to_csv(out, index=False, lineterminator="\n")
    h = hashlib.sha256(out.read_bytes()).hexdigest()
    (V.OUT / f"seal_inputs_{D.isoformat()}.json").write_text(json.dumps(used, indent=1))
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"| `{out.name}` | `{h}` | {D.isoformat()} | {', '.join(map(str, S['lead']))} | "
                 f"{', '.join(S['target_quarter'])} | {dt.date.today().isoformat()} |\n")
    print(S.T.to_string())
    print("sha256", h)


if __name__ == "__main__":
    main()

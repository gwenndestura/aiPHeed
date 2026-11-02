"""IMPROVE_V2 seal (PLAN.md section 10). Run once, after RESULTS: python seal.py

Writes sealed_prospective_IMPROVE_V2.csv (every carried-forward forecast with target >= 2027-Q1 whose issue date has
passed: on 2026-11-03 only Lead 2 for 2027-Q1, origin 2026-Q3, issue date 2026-10-01), its SHA-256 in SEAL_LEDGER.md,
and the Objective-3 rankings out/lgu_rankings.csv. Refuses to overwrite an existing seal."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import datetime as dt
import hashlib
import json

import numpy as np
import pandas as pd

import iv2_lib as V
import run_iv2 as RUN

H = V.H
SEALED = V.IV / "sealed_prospective_IMPROVE_V2.csv"
LEDGER = V.IV / "SEAL_LEDGER.md"
FIRST_TARGET = H.qi("2027-Q1")
RANK_LABEL = "priority ranking, not a measured food-insecurity rate"


def sha(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def lgu_rankings(prob: float, target: str, arm: str) -> pd.DataFrame:
    """Objective 3: the backend's approved ranking (forecaster_v2.lgu_table -> lgu_poverty.rank_lgus), imported
    read-only. The forecast is regional: the same probability for all five provinces (PLAN 5)."""
    if str(V.BACKEND) not in sys.path:
        sys.path.insert(0, str(V.BACKEND))
    from app.quarterly.forecaster_v2 import lgu_table
    lg = pd.read_csv(V.BACKEND / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    r = lgu_table(lg, {p: prob for p in H.PROVS}, exact_ranks=True)
    return r.assign(target_quarter=target, arm=arm, regional_probability=prob, label=RANK_LABEL,
                    note="regional forecast: every province has the same probability, so the order inside a province "
                         "is set by poverty (60%) and density (40%) alone; most LGUs carry a province-mean poverty "
                         "substitute (backend known limitation)")


def main():
    if SEALED.exists():
        raise SystemExit("already sealed: the sealed file is never edited or rewritten")
    plan = RUN.plan_sha()
    res = json.loads((V.OUT / "results.json").read_text())
    sel = {k: res["leads"][f"L{k}"]["selection"]["carried_forward"] for k in RUN.LEADS}
    F = pd.read_csv(V.OUT / "forecasts.csv")
    T = RUN._table()
    today = dt.date.today().isoformat()
    rows = []
    for k in RUN.LEADS:
        for t in sorted(F["t"].unique()):
            q = int(t) + k
            if q < FIRST_TARGET or H.issue(int(t)) > today:
                continue
            f = F[(F["name"] == sel[k]) & (F["t"] == t) & (F["lead"] == k)]
            ps = F[(F["name"] == "PERSIST") & (F["t"] == t) & (F["lead"] == k)]
            b = T[(T["t"] == t) & (T["lead"] == k) & (T["area"] == "BL")].iloc[0]
            assert len(f) == 1 and len(ps) == 1
            p = float(f["p"].iloc[0])
            rows.append({"issue_date": H.issue(int(t)), "origin": H.qs(int(t)), "lead": k, "target_quarter": H.qs(q),
                         "arm": sel[k], "p_high": round(p, 6), "class": "HIGH" if p >= .5 else "LOW",
                         "persist_p": float(ps["p"].iloc[0]), "newest_sws_published": b["sws_newest_published"],
                         "newest_sws_reading": float(b["h_last"]), "threshold": H.H_LINE,
                         "target": "SWS Balance Luzon involuntary hunger > 11.3% (quarter mean of non-commissioned rounds)",
                         "plan_sha256": plan, "sealed_on": today, "label": "EXPLORATORY"})
    S = pd.DataFrame(rows)
    assert len(S), "nothing issuable"
    S.to_csv(SEALED, index=False, lineterminator="\n")
    h = sha(SEALED)
    R = pd.concat([lgu_rankings(r["p_high"], r["target_quarter"], r["arm"]) for r in rows], ignore_index=True)
    R.to_csv(V.OUT / "lgu_rankings.csv", index=False, lineterminator="\n")
    LEDGER.write_text(
        "# IMPROVE_V2 seal ledger (EXPLORATORY)\n\n"
        f"Plan: `PLAN.md` sha `{plan}`. Carried-forward arms (PLAN 4): Lead 1 **{sel[1]}**, Lead 2 **{sel[2]}**.\n\n"
        "Sealed files are never edited. Later forecasts are issued by `runner/seal_next.py` into new files, each "
        "appended below with its SHA-256. `runner/score_seal.py` checks every hash before scoring.\n\n"
        "| File | SHA-256 | Issue date(s) | Lead(s) | Target(s) | Sealed on |\n|---|---|---|---|---|---|\n"
        f"| `{SEALED.name}` | `{h}` | {', '.join(S['issue_date'])} | {', '.join(map(str, S['lead']))} | "
        f"{', '.join(S['target_quarter'])} | {today} |\n", encoding="utf-8", newline="\n")
    print(S.T.to_string())
    print("sha256", h)


if __name__ == "__main__":
    main()

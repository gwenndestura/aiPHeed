"""E53 trigger coverage audit (no model fitted): for each issue date 2023-Q4..2026-Q3 (targets 2024-Q2..2027-Q1) and
each trigger group (D-1 mapping), the share of the group's model inputs that have a value at the issue date, and whether
the inputs differ between provinces (provincial) or are identical (national).

    backend/venv/Scripts/python.exe -B runner/e53_coverage.py   -> tables/trigger_coverage.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e53_lib as E  # noqa: E402

L, P2, np, pd = E.L, E.P2, E.np, E.pd


def main():
    d, X, B = E.load()
    cols = E.pcols()
    groups = {g: [c for c in cols if E.group_of(c) == g] for g in E.FIVE + ["other"]}
    rows = []
    for t in range(L.qi("2023-Q4"), L.qi("2026-Q3") + 1):
        x = X[X["t"] == t].set_index("province_code").loc[L.PROVS]
        for g, cs in groups.items():
            v = x[cs].astype(float)
            prov = [c for c in cs if v[c].notna().all() and v[c].nunique() > 1]
            rows.append({"origin_quarter": L.qs(t), "target_quarter": L.qs(t + 2), "group": g, "inputs": len(cs),
                         "share_present": round(float(v.notna().to_numpy().mean()), 3),
                         "missing_inputs": ";".join(c for c in cs if v[c].isna().all()),
                         "provincial_inputs": ";".join(prov), "national_inputs": len(cs) - len(prov)})
    T = pd.DataFrame(rows)
    out = E.E53 / "tables"
    out.mkdir(exist_ok=True)
    T.to_csv(out / "trigger_coverage.csv", index=False)
    S = T.groupby("group").agg(inputs=("inputs", "first"), mean_share_present=("share_present", "mean"),
                               min_share_present=("share_present", "min"))
    print(S.round(3).to_string())
    print(T[T["missing_inputs"] != ""][["target_quarter", "group", "missing_inputs"]].to_string())
    print(T[T["target_quarter"] == "2027-Q1"][["group", "provincial_inputs", "national_inputs"]].to_string())


if __name__ == "__main__":
    main()

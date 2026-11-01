"""Y12 step 1c (data audit, before the plan is frozen; no forecasting): does the 2012-based provincial CPI reproduce the
official 2018-based price condition where they overlap (2021), and what is the price-condition prevalence by province
and period? Uses only CPI and the frozen E40 thresholds (no supply data, no model). Writes out/audit_checks.json.

    python -B audit_checks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ACQ = HERE.parent / "data_acquired"
OUT = HERE.parent / "out"
EXP = HERE.parents[2]
sys.path.insert(0, str(EXP / "E41_Lead2_Audit" / "runner"))


def qmeans(cp: pd.DataFrame) -> pd.DataFrame:
    cp = cp.assign(q=cp["ym"] // 3)
    g = cp.groupby(["geo", "commodity", "q"])["value"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] == 3].pivot_table(index=["geo", "q"], columns="commodity", values="mean").reset_index()
    return g


def main():
    import e41_lib as E
    th = E.e40_spec()
    cp = pd.read_csv(ACQ / "tidy_cpi2012_yoy.csv")
    q12 = qmeans(cp)
    off = E.load().yoy.rename(columns={"province_code": "geo", "yoy": "value"})
    q18 = qmeans(off)
    res = {}
    j = q12.merge(q18, on=["geo", "q"], suffixes=("_12", "_18"))
    for g, d in j.groupby("geo"):
        c12 = (d["food_12"] > th["food"][g]) | ((d["food_12"] - d["all_items_12"]) > th["gap"][g])
        c18 = (d["food_18"] > th["food"][g]) | ((d["food_18"] - d["all_items_18"]) > th["gap"][g])
        res[g] = {"overlapQuarters": [f"{q // 4}-Q{q % 4 + 1}" for q in d["q"]],
                  "foodYoY_meanAbsDiff": round(float((d["food_12"] - d["food_18"]).abs().mean()), 3),
                  "gap_meanAbsDiff": round(float(((d["food_12"] - d["all_items_12"]) - (d["food_18"] - d["all_items_18"])).abs().mean()), 3),
                  "conditionAgreement": f"{int((c12 == c18).sum())}/{len(d)}"}
    prev = {}
    for g in th["food"]:
        d = q12[q12["geo"] == g]
        c = (d["food"] > th["food"][g]) | ((d["food"] - d["all_items"]) > th["gap"][g])
        for lab, lo, hi in (("1995-2001", 1995, 2001), ("2002-2011 (backcast)", 2002, 2011), ("2012-2020", 2012, 2020)):
            m = (d["q"] // 4 >= lo) & (d["q"] // 4 <= hi)
            prev.setdefault(g, {})[lab] = f"{c[m].mean():.2f} of {int(m.sum())}"
    out = {"overlap2012vs2018": res, "prevalenceByPeriod": prev, "thresholds": {"food": th["food"], "gap": th["gap"]}}
    OUT.mkdir(exist_ok=True)
    (OUT / "audit_checks.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

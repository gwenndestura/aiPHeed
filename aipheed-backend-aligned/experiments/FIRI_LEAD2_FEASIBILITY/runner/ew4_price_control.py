"""Price-path positive control for ew4_issue_audit.py: the first control moved only the hunger values, so this one
perturbs CPI published BEFORE the issue (every 2026 month <= m0, index x1.15 and YoY +6) and requires the P4/P0 price
values to change. In memory only; writes out/ew4_price_control.json.

    python ew4_price_control.py
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import dataclasses  # noqa: E402
import json  # noqa: E402

import ew4_issue_audit as A  # noqa: E402

X, U, E, L = A.X, A.U, A.E, A.L


def main():
    A.frozen_ok()
    U.setup()
    K = int(json.loads((U.OUT / "testability_unified.json").read_text())["K"])
    t = L.qi(A.ISSUE_T)
    m0 = L.m0_of(t)
    d, x = E.data()

    def prices(dd):
        A.clear_all()
        S = X.add_fe(U.stack(K, dd, x, t, U.pinksheet()), dd, X.rice_cpi())
        f = X.forecast_origin(S, t, A.ARMS, True, dd)
        return {(r["province_code"], int(r["lead"]), c): round(float(r[c]), 10)
                for _, r in f[f["lead"].isin([1, 2])].iterrows() for c in [f"{p}_price" for p in A.ARMS]}

    base = prices(d)
    yo, ix = d.yoy.copy(), d.idx.copy()
    lo = (t - 2) // 4 * 12                                           # January of the issue year
    yo.loc[(yo["ym"] >= lo) & (yo["ym"] <= m0), "yoy"] += 6.0
    ix.loc[(ix["ym"] >= lo) & (ix["ym"] <= m0), "index"] *= 1.15
    ctrl = prices(dataclasses.replace(d, yoy=yo, idx=ix))
    A.clear_all()
    changed = [str(k) for k in base if base[k] != ctrl[k]]
    res = {"origin": A.ISSUE_T, "perturbed": f"CPI {L.ym_s(lo)}..{L.ym_s(m0)}: index x1.15, YoY +6 (published before issue)",
           "priceValues": len(base), "changed": len(changed), "passed": bool(changed)}
    (A.HERE.parent / "out" / "ew4_price_control.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()

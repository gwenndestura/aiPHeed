"""LEAD2_IMPROVE feature builder (no outcome is read): adds to the served model's stack, for every origin and lead
1..15, only information published before the issue date:

- A1_food_anc, A1_gap_anc: the food and gap projections of the target quarter with the monthly log index grown at the
  BSP 2-4% target midpoint (ln 1.03 / 12) instead of held flat, minus the province's frozen thresholds;
- trigger dynamics (origin level): dC3, dC4, dE1, dE2 = change since the previous origin; C2_2q = typhoons in the last
  two quarters; C1_run = consecutive origins with an El Nino alert in force.

    python features_v2.py       # ../data/stack_v2.csv, ../out/features_v2_audit.json
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np
import pandas as pd

import lt_lib as T

sys.path.insert(0, str(T.EXP / "FORECAST_RESEARCH_II" / "runner"))
import ii_lib as II  # noqa: E402

F = T.F
G_ANCHOR = math.log(1.03) / 12


def anchored(S: pd.DataFrame, g: float) -> tuple[np.ndarray, np.ndarray]:
    W = II.index_wide()
    lf, la = np.log(W["food"]), np.log(W["all"])
    out_f, out_g = [], []
    for t, k, p in zip(S["t"], S["lead"], S["province_code"]):
        m0 = II.m0_of(int(t))
        q = int(t) + int(k)
        months = [q // 4 * 12 + (q % 4) * 3 + j for j in range(3)]

        def L(series, m):
            if m <= m0:
                return series[p].get(m, np.nan)
            base = series[p].get(m0, np.nan)
            return base + g * (m - m0)
        try:
            yf = [100 * (math.exp(L(lf, m) - L(lf, m - 12)) - 1) for m in months]
            ya = [100 * (math.exp(L(la, m) - L(la, m - 12)) - 1) for m in months]
            if any(np.isnan(yf + ya)) or min(m - 12 for m in months) < II.FIRST_YM:
                raise ValueError
            fq, aq = float(np.mean(yf)), float(np.mean(ya))
            out_f.append(fq - F.TH_F[p])
            out_g.append(fq - aq - F.TH_G[p])
        except (ValueError, KeyError):
            out_f.append(np.nan)
            out_g.append(np.nan)
    return np.array(out_f), np.array(out_g)


def main():
    S = T.stack().copy()
    S["A1_food_anc"], S["A1_gap_anc"] = anchored(S, G_ANCHOR)
    flat_f, flat_g = anchored(S, 0.0)
    o = S.drop_duplicates(["t", "province_code"]).set_index(["t", "province_code"])
    prev = lambda c, t, p: o[c].get((t - 1, p), np.nan)  # noqa: E731
    for c in ("C3", "C4", "E1", "E2"):
        S[f"d{c}"] = [o[c].get((t, p), np.nan) - prev(c, t, p) for t, p in zip(S["t"], S["province_code"])]
    S["C2_2q"] = [o["C2"].get((t, p), np.nan) + prev("C2", t, p) for t, p in zip(S["t"], S["province_code"])]
    run = {}
    for p in sorted(S["province_code"].unique()):
        r = 0
        for t in sorted(S["t"].unique()):
            v = o["C1"].get((t, p), np.nan)
            r = r + 1 if v == 1 else 0
            run[(t, p)] = r
    S["C1_run"] = [run[(t, p)] for t, p in zip(S["t"], S["province_code"])]
    S.to_csv(T.DATA / "stack_v2.csv", index=False, lineterminator="\n", float_format="%.10g")
    m = S["A1_food"].notna() & np.isfinite(flat_f)
    audit = {"rows": len(S), "flat_recompute_vs_A1_food_max_abs": float(np.nanmax(np.abs(flat_f[m] - S.loc[m, "A1_food"]))),
             "flat_recompute_vs_A1_gap_max_abs": float(np.nanmax(np.abs(flat_g[m] - S.loc[m, "A1_gap"]))),
             "coverage": {c: float(S[c].notna().mean()) for c in ("A1_food_anc", "A1_gap_anc", "dC3", "dC4", "dE1", "dE2", "C2_2q", "C1_run")},
             "A1_coverage": float(S["A1_food"].notna().mean())}
    (T.OUT / "features_v2_audit.json").write_text(json.dumps(audit, indent=1))
    print(audit)


if __name__ == "__main__":
    main()

"""PROTOCOL_LEAD2_CAUSES_SCREEN: does the NASA POWER provincial rainfall anomaly of the origin quarter predict the
Lead-2 price-projection error on development rows only (targets <= 2024-Q4)?

    python rain_screen.py       # ../out/rain_screen.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T

F, KEY = T.F, T.KEY
RAIN = T.EXP.parent.parent / "backend" / "data" / "processed" / "province_rainfall.parquet"
SEED, DRAWS = 2031, 2000


def spearman(a, b) -> float:
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def main():
    proto = T.LT / "PROTOCOL_LEAD2_CAUSES_SCREEN.md"
    assert T.sha256(proto) == (T.HERE / "CAUSES_SHA256.txt").read_text().strip(), "protocol changed after freezing"
    S = T.stack()
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    D = C[(C["lead"] == 2) & (C["q"] <= F.DEV_LAST)][KEY + ["q"]].copy()
    assert D["q"].max() <= F.DEV_LAST
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv", dtype={"province_code": str})
    D = D.merge(lab[["province_code", "q", "m_food", "m_gap"]], on=["province_code", "q"]).merge(S[KEY + ["A1_food", "A1_gap"]], on=KEY)
    D["e"] = D[["m_food", "m_gap"]].max(axis=1) - D[["A1_food", "A1_gap"]].max(axis=1)
    r = pd.read_parquet(RAIN)
    r["t"] = r["year"].astype(int) * 4 + r["quarter"].str[-1].astype(int) - 1
    r = r[r["year"] >= 2021][["province_code", "t", "rainfall_anomaly_pct"]]
    r["rain_dev"] = r["rainfall_anomaly_pct"] - r.groupby("t")["rainfall_anomaly_pct"].transform("mean")
    r["rain_abs"] = r["rainfall_anomaly_pct"].abs()
    D = D.merge(r, on=["province_code", "t"], how="left")
    rng = np.random.default_rng(SEED)
    qs = np.array(sorted(D["q"].unique()))
    res = {"protocol_sha256": T.sha256(proto), "rows": int(len(D)), "quarters": int(len(qs)),
           "targets": [F.qs(int(qs[0])), F.qs(int(qs[-1]))], "signals": {}}
    for c in ("rainfall_anomaly_pct", "rain_dev", "rain_abs"):
        m = D[c].notna() & D["e"].notna()
        rho = spearman(D.loc[m, c], D.loc[m, "e"])
        boot = []
        for _ in range(DRAWS):
            pick = rng.choice(qs, len(qs), replace=True)
            B = pd.concat([D[m & (D["q"] == q)] for q in pick])
            if B[c].nunique() > 2:
                boot.append(spearman(B[c], B["e"]))
        lo, hi = np.percentile(boot, [5, 95])
        res["signals"][c] = {"n": int(m.sum()), "rho": rho, "ci90": [float(lo), float(hi)],
                             "passes": bool(abs(rho) >= .30 and (lo > 0 or hi < 0))}
    res["proceed_to_candidate"] = any(v["passes"] for v in res["signals"].values())
    (T.OUT / "rain_screen.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()

"""LEAD2_FINAL feature builder (no outcome is read): food-price composition and breadth at the cut-off.

Source: PSA OpenStat 0012M4ACP22 provincial CPI by food subgroup (acquired in E84,
E84_Objective_Continuation/data_acquired/psa_cpi_subgroups_2021_2026.csv), 2018 PSA weights (psa_cpi_weights_2018.csv).
It is released together with the food CPI already in the model, so for each row only months <= psa_newest_month are
read (the same month the A1 columns use).

Subgroups: fresh = fish and seafood, fruits and nuts, vegetables (the fresh-food exclusion used in "core excluding fresh
food" indices); non-fresh = rice, corn, meat, oils and fats, sugar. For the newest 3 published months:

- K_core      weighted non-fresh food y/y (%) minus the province's frozen food threshold TH_F (persistent pressure margin)
- K_fresh_gap weighted fresh y/y minus weighted non-fresh y/y (pressure concentrated in items that revert)
- K_diff      weight share of the 8 subgroups whose y/y in the newest month exceeds their y/y 3 months earlier
              (breadth of acceleration; a diffusion index)

    python features_v4.py       # ../data/stack_v4.csv, ../out/features_v4_audit.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T

F = T.F
SUB = T.EXP / "E84_Objective_Continuation" / "data_acquired"
FRESH = {"01.1.3": "fish", "01.1.6": "fruits", "01.1.7": "vegetables"}
CORE = {"01.1.1.12": "rice", "01.1.1.16": "corn", "01.1.2": "meat", "01.1.5": "oils", "01.1.8": "sugar"}
K_COLS = ["K_core", "K_fresh_gap", "K_diff"]
NAMES = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000",
         "Batangas": "PH040500000"}


def code(desc: str) -> str:
    return desc.split(" - ")[0].strip()


def load():
    a = pd.read_csv(SUB / "psa_cpi_subgroups_2021_2026.csv")
    a["code"] = a["Commodity Description"].map(code)
    a = a[a["code"].isin({**FRESH, **CORE})].copy()
    d = pd.to_datetime(a["ym"], format="%Y %b")
    a["m"] = d.dt.year * 12 + d.dt.month - 1
    a["province_code"] = a["Geolocation"].map(NAMES)
    I = {(p, c): g.set_index("m")["index"].astype(float) for (p, c), g in a.groupby(["province_code", "code"])}
    w = pd.read_csv(SUB / "psa_cpi_weights_2018.csv")
    w["province_code"] = w["Geolocation"].str.strip(". ").map(NAMES)
    w["code"] = w["Commodity Description"].map(code)
    W = {(p, c): float(v) for p, c, v in zip(w["province_code"], w["code"], w["Weights"]) if c in {**FRESH, **CORE}}
    return I, W, int(a["m"].min()), int(a["m"].max())


def yoy(s: pd.Series, m: int) -> float:
    a, b = s.get(m, np.nan), s.get(m - 12, np.nan)
    return 100 * (a / b - 1) if pd.notna(a) and pd.notna(b) else np.nan


def features(p: str, m0: int, I, W) -> tuple[float, float, float]:
    def group(codes, months):
        vals = [(W[(p, c)], np.mean([yoy(I[(p, c)], m) for m in months])) for c in codes]
        if any(np.isnan(v) for _, v in vals):
            return np.nan
        return sum(w * v for w, v in vals) / sum(w for w, _ in vals)
    months = [m0 - 2, m0 - 1, m0]
    core, fresh = group(CORE, months), group(FRESH, months)
    num = den = 0.0
    for c in {**FRESH, **CORE}:
        a, b = yoy(I[(p, c)], m0), yoy(I[(p, c)], m0 - 3)
        if np.isnan(a) or np.isnan(b):
            return core - F.TH_F[p] if pd.notna(core) else np.nan, fresh - core, np.nan
        num += W[(p, c)] * (a > b)
        den += W[(p, c)]
    return core - F.TH_F[p], fresh - core, num / den


def main():
    I, W, m_first, m_last = load()
    S = pd.read_csv(T.DATA / "stack_v2.csv", dtype={"province_code": str})
    pm = pd.to_datetime(S["psa_newest_month"], format="%Y-%m")
    S["m0"] = pm.dt.year * 12 + pm.dt.month - 1
    assert (S["m0"] == (S["t"] // 4) * 12 + (S["t"] % 4) * 3 + 1).all(), "psa_newest_month must equal the A1 cut-off month"
    assert S["m0"].max() <= m_last
    cache = {}
    for t, p, m0 in zip(S["t"], S["province_code"], S["m0"]):
        if (p, m0) not in cache:
            cache[(p, m0)] = features(p, int(m0), I, W)
    vals = np.array([cache[(p, m0)] for p, m0 in zip(S["province_code"], S["m0"])])
    for j, c in enumerate(K_COLS):
        S[c] = vals[:, j]
    S = S.drop(columns="m0")
    S.to_csv(T.DATA / "stack_v4.csv", index=False, lineterminator="\n", float_format="%.10g")
    o = S.drop_duplicates(["t", "province_code"])
    ev = o[o["t"] >= 8091]
    audit = {"source_months": [f"{m_first // 12}-{m_first % 12 + 1:02d}", f"{m_last // 12}-{m_last % 12 + 1:02d}"],
             "newest_month_read_max": str(S["psa_newest_month"].max()),
             "weights_used": {f"{p}|{c}": W[(p, c)] for p, c in sorted(W)},
             "coverage_all_origins": {c: float(o[c].notna().mean()) for c in K_COLS},
             "coverage_eval_origins": {c: float(ev[c].notna().mean()) for c in K_COLS},
             "first_origin_with_value": {c: int(o.loc[o[c].notna(), "t"].min()) for c in K_COLS},
             "describe_eval_origins": ev[K_COLS].describe().round(3).to_dict(),
             "corr_with_A1_food_eval": {c: float(ev[[c, "A1_food"]].corr().iloc[0, 1]) for c in K_COLS},
             "corr_with_accel_eval": {c: float(ev[[c, "accel"]].corr().iloc[0, 1]) for c in K_COLS}}
    (T.OUT / "features_v4_audit.json").write_text(json.dumps(audit, indent=1, default=float))
    print(json.dumps({k: v for k, v in audit.items() if k != "weights_used"}, indent=1, default=float))


if __name__ == "__main__":
    main()

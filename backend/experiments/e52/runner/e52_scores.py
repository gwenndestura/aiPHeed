"""E52: measured five-driver CONDITION scores from official / measured data (separate from the model's SHAP).

    python -B backend/experiments/e52/runner/e52_scores.py  -> backend/experiments/e52/E52_scores.csv, E52_results.json

Nothing here touches the served model, records, API or frontend; inputs are read only.

TIMING. For forecast quarter F (origin = first day of F), each series uses its DATA QUARTER Q = F-2, the latest
complete quarter published before the origin. This is the model's timing: for F = 2026-Q4 (origin 2026-10-01) the
model's D_last is the food CPI of 2026-Q2, and E43 used 2026-Q2 for every driver.

SCORE. 0-100 percent rank of the quarter-Q value against that series' OWN history 2021-Q1..Q (expanding, Q included,
nothing after Q): score = 100 * #{history values < x} / (n - 1) (ties take the lowest rank, so a zero in a series of
zeros scores 0). Province series rank against the province's own history; national series against the national one.

  Market      mean of rank(D) and rank(rice CPI YoY); D = province food CPI YoY - five-province mean
              (psa_indicators.parquet, PSA provincial CPI; equals the model's D), rice = PSA OpenStat provincial
              rice CPI YoY, quarter mean of its 3 months (E32 data_acquired file used by the model)       province
  Climate     max(rank |rainfall anomaly %| (NASA POWER daily, e43), rank tc_max_signal (NOAA IBTrACS, storms
              within 300 km of the province centroid, mapped to PAGASA wind-signal bands))           province
  Fish Kill   rank of max(0, -ln(V_Q / V_Q-4)), V = PSA OpenStat total fisheries production of the province
              (0132E4GVFP1, subsector FISHERIES) -- PROXY: supply decline, not fish-kill incidents       province
  Employment  mean of rank(u) and rank(u_Q - u_Q-4), u = PSA LFS national unemployment, quarter mean of the
              released months, observed quarters only (e43). Provincial annual adjustment NOT applied: the PSA
              RSSO IV-A releases (rsso04a.psa.gov.ph) return HTTP 403 and no release date is verifiable  national
  OFW         rank of max(0, -g_real), g_real = (1 + remittance USD YoY)(1 + USD/PHP YoY)/(1 + province food
              CPI YoY) - 1 (e43 real_peso_inputs). 2026 remittances are BSP figures reported by secondary
              sources -> PROVISIONAL; the curated 2022-2025 quarterly split is 3.6% off BSP's own 2025
              totals -> flagged UNVERIFIED                                       national, varies only via food CPI
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
E52 = Path(__file__).resolve().parents[1]
B = E52.parents[1]
ROOT = B.parent
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
PROVS = list(NAMES)
qk = lambda s: int(s[:4]) * 4 + int(s[-1]) - 1
qs = lambda k: f"{k // 4}-Q{k % 4 + 1}"
START = qk("2021-Q1")
FORECASTS = [qs(k) for k in range(qk("2023-Q1"), qk("2026-Q4") + 1)]
DRIVERS = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]


def pct_rank(hist: list[float], x: float) -> float:
    h = [v for v in hist if v == v]
    if x != x or len(h) < 2:
        return float("nan")
    return 100.0 * sum(v < x for v in h) / (len(h) - 1)


def series_score(s: dict[int, float], q: int) -> tuple[float, float, int]:
    """score of s[q] against s over START..q; returns (score, raw value, n history)."""
    hist = [s[k] for k in range(START, q + 1) if k in s]
    x = s.get(q, float("nan"))
    return pct_rank(hist, x), x, len([v for v in hist if v == v])


def load():
    psa = pd.read_parquet(B / "data/processed/psa_indicators.parquet")
    psa["D"] = psa["food_cpi_yoy"] - psa.groupby("quarter")["food_cpi_yoy"].transform("mean")
    D = {p: {qk(q): v for q, v in g.set_index("quarter")["D"].items() if v == v} for p, g in psa.groupby("province_code")}
    r = pd.read_csv(ROOT / "aipheed-backend-aligned/experiments/E32_New_Model/data_acquired/provincial_rice_cpi_yoy_2021_2026.csv",
                    dtype={"province_code": str})
    r["tq"] = r["reference_month"].str[:4].astype(int) * 4 + (r["reference_month"].str[5:7].astype(int) - 1) // 3
    rq = r.groupby(["province_code", "tq"]).agg(v=("rice_cpi_yoy_pct", "mean"), n=("rice_cpi_yoy_pct", "size")).reset_index()
    rq = rq[rq["n"] == 3]
    RICE = {p: dict(zip(g["tq"], g["v"])) for p, g in rq.groupby("province_code")}
    rain = pd.read_parquet(B / "experiments/e43/data/rainfall_daily_province.parquet")
    RAIN = {p: {qk(q): abs(v) for q, v in zip(g["quarter"], g["value"]) if v == v}
            for p, g in rain[rain["observed"] == 1].groupby("province_code")}
    RAIN_SIGNED = {p: {qk(q): v for q, v in zip(g["quarter"], g["value"])} for p, g in rain.groupby("province_code")}
    pc = pd.read_parquet(B / "data/processed/pagasa_climate.parquet")
    TC = {p: {qk(q): float(v) for q, v in zip(g["quarter"], g["tc_max_signal"])} for p, g in pc.groupby("province_code")}
    f = pd.read_parquet(B / "experiments/e43/data/fisheries_production.parquet")
    f = f[(f["subsector"] == "FISHERIES") & (f["observed"] == 1) & f["province_code"].isin(PROVS)]
    V = {p: {qk(q): v for q, v in zip(g["quarter"], g["value"])} for p, g in f.groupby("province_code")}
    FISH = {p: {k: max(0.0, -math.log(v[k] / v[k - 4])) for k in v if k - 4 in v and v[k] > 0 and v[k - 4] > 0}
            for p, v in V.items()}
    FISH_YOY = {p: {k: v[k] / v[k - 4] - 1 for k in v if k - 4 in v} for p, v in V.items()}
    u = pd.read_parquet(B / "experiments/e43/data/unemployment_quarterly.parquet")
    u = u[u["observed"] == 1]
    U = {qk(q): v for q, v in zip(u["quarter"], u["value"])}
    DU = {k: U[k] - U[k - 4] for k in U if k - 4 in U}
    rp = pd.read_parquet(B / "experiments/e43/data/real_peso_inputs.parquet")
    rp = rp[rp["g_real_pct"].notna()]
    OFW = {p: {qk(q): max(0.0, -v) for q, v in zip(g["quarter"], g["g_real_pct"])} for p, g in rp.groupby("province_code")}
    GREAL = {p: {qk(q): v for q, v in zip(g["quarter"], g["g_real_pct"])} for p, g in rp.groupby("province_code")}
    rem = pd.read_parquet(B / "experiments/e43/data/remittance_quarterly.parquet")
    REM_PRIMARY = {qk(q): int(v) for q, v in zip(rem["quarter"], rem["verified_primary"])}
    return dict(D=D, RICE=RICE, RAIN=RAIN, RAIN_SIGNED=RAIN_SIGNED, TC=TC, FISH=FISH, FISH_YOY=FISH_YOY, U=U, DU=DU,
                OFW=OFW, GREAL=GREAL, REM_PRIMARY=REM_PRIMARY)


def nanmean(*xs):
    v = [x for x in xs if x == x]
    return float(np.mean(v)) if v else float("nan")


def nanmax(*xs):
    v = [x for x in xs if x == x]
    return float(max(v)) if v else float("nan")


def main():
    d = load()
    rows = []
    for F in FORECASTS:
        q = qk(F) - 2
        for p in PROVS:
            sD, vD, nD = series_score(d["D"][p], q)
            sR, vR, nR = series_score(d["RICE"][p], q)
            sRa, vRa, nRa = series_score(d["RAIN"][p], q)
            sT, vT, nT = series_score(d["TC"][p], q)
            sF, vF, nF = series_score(d["FISH"][p], q)
            sU, vU, nU = series_score(d["U"], q)
            sDU, vDU, nDU = series_score(d["DU"], q)
            sO, vO, nO = series_score(d["OFW"][p], q)
            base = {"forecast_quarter": F, "data_quarter": qs(q), "province": NAMES[p], "province_code": p}
            rows += [
                {**base, "driver": "market", "score": nanmean(sD, sR), "level": "province",
                 "inputs": {"D_pp": vD, "rank_D": sD, "rice_cpi_yoy": vR, "rank_rice": sR}, "n_history": min(nD, nR),
                 "source": "PSA provincial CPI (food, rice; OpenStat)", "flag": ""},
                {**base, "driver": "climate", "score": nanmax(sRa, sT), "level": "province",
                 "inputs": {"rain_anomaly_pct": d["RAIN_SIGNED"][p].get(q, float("nan")), "rank_abs_rain": sRa,
                            "tc_max_signal": vT, "rank_storm": sT}, "n_history": min(nRa, nT),
                 "source": "NASA POWER daily rainfall; NOAA IBTrACS storms", "flag": "not Philippine-government data"},
                {**base, "driver": "fish_kill", "score": sF, "level": "province",
                 "inputs": {"production_yoy": d["FISH_YOY"][p].get(q, float("nan")), "decline_log": vF}, "n_history": nF,
                 "source": "PSA OpenStat 0132E4GVFP1 fisheries production", "flag": "PROXY (supply decline, not incidents)"},
                {**base, "driver": "employment", "score": nanmean(sU, sDU), "level": "national",
                 "inputs": {"unemployment_pct": vU, "rank_u": sU, "yoy_change_pp": vDU, "rank_change": sDU},
                 "n_history": nU, "source": "PSA LFS national (OpenStat 0021B3FKEI2), quarter mean",
                 "flag": "national; provincial adjustment not verifiable (RSSO IV-A HTTP 403)"},
                {**base, "driver": "ofw_remittance", "score": sO, "level": "national (varies only via food CPI)",
                 "inputs": {"g_real_pct": d["GREAL"][p].get(q, float("nan")), "fall_pct": vO}, "n_history": nO,
                 "source": "BSP cash remittances (curated / reported), ECB FX, PSA food CPI",
                 "flag": ("PROVISIONAL (2026 BSP values from secondary reports)" if q >= qk("2026-Q1")
                          else "UNVERIFIED curated quarterly split")},
            ]
    df = pd.DataFrame(rows)
    flat = df.drop(columns="inputs").join(pd.json_normalize(df["inputs"]).add_prefix("in_"))
    flat.to_csv(E52 / "E52_scores.csv", index=False, float_format="%.4f")

    piv = df.pivot_table(index=["forecast_quarter", "province"], columns="driver", values="score")[DRIVERS]
    region = df.groupby(["forecast_quarter", "driver"])["score"].mean().unstack()[DRIVERS]
    spread = df.groupby(["forecast_quarter", "driver"])["score"].agg(lambda s: float(s.max() - s.min())).unstack()[DRIVERS]
    q4 = df[df["forecast_quarter"] == "2026-Q4"]
    res = {"timing": "forecast quarter F uses data quarter F-2 (latest complete quarter before the origin)",
           "q4_2026": {r.province: {} for r in q4.itertuples()},
           "calabarzon_mean": {F: {k: round(v, 1) for k, v in row.items()} for F, row in region.round(1).iterrows()},
           "province_spread_max_minus_min": {F: {k: round(v, 1) for k, v in row.items()} for F, row in spread.iterrows()},
           "by_province": {f"{F} {p}": {k: (None if v != v else round(v, 1)) for k, v in row.items()} for (F, p), row in piv.iterrows()}}
    for r in q4.itertuples():
        res["q4_2026"][r.province][r.driver] = {"score": None if r.score != r.score else round(r.score, 1),
                                                "data_quarter": r.data_quarter, "level": r.level, "source": r.source,
                                                "flag": r.flag, "inputs": {k: (None if v != v else round(v, 3)) for k, v in r.inputs.items()},
                                                "n_history": r.n_history}
    (E52 / "E52_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    pd.set_option("display.width", 200)
    print("Q4 2026 (data 2026-Q2):\n", piv.loc["2026-Q4"].round(1))
    print("\nCALABARZON mean:\n", region.round(1))
    print("\nprovince spread (max-min):\n", spread.round(1))


if __name__ == "__main__":
    main()

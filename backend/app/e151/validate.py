"""
E151 validation forms B to D that do not need the forecast gates: instrument compatibility, construct checks on the news, and contextual agreement. Labelled as such; none of this is direct validation.

    python -m app.e151.validate -> data/e151/out/validation.json
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.e144 import data as D
from app.e147 import features as Fe
from app.e147 import labels as Lb
from app.e148 import panel as Pn
from app.e150 import response as R150
from app.e151 import OUT
from app.fi5.target import qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
DATA = BACKEND_DIR / "data"
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
REG = {"Region I": "Ilocos", "Region II": "Cagayan Valley", "Region III": "Central Luzon", "Region IV-A": "CALABARZON", "MIMAROPA": "MIMAROPA", "Region V": "Bicol", "Region VI": "Western Visayas", "Region VII": "Central Visayas", "Region VIII": "Eastern Visayas", "Region IX": "Zamboanga", "Region X": "Northern Mindanao", "Region XI": "Davao", "Region XII": "SOCCSKSARGEN", "Region XIII": "Caraga", "CAR": "CAR", "Cordillera": "CAR", "BARMM": "BARMM", "NCR": "NCR", "National Capital": "NCR"}


def _norm_region(s: str) -> str | None:
    t = str(s)
    for k in sorted(REG, key=len, reverse=True):
        if k.lower() in t.lower():
            if k == "Region I" and any(x in t for x in ("II", "IV", "IX", "V", "X")):
                continue
            return REG[k]
    return None


def measures() -> dict:
    """Any-level against moderate-or-severe, round by round: how often each crosses 50."""
    h = pd.read_csv(DATA / "hfias" / "clean" / "enns_hfias.csv")
    h["any"] = 100 - h["food_secure_pct"]
    h["modsev"] = h["moderate_pct"] + h["severe_pct"]
    L = pd.read_csv(Lb.SEALED)
    w = L.pivot_table(index=["key", "province_name"], columns="fs_survey_category", values="pct").reset_index()
    w["any"] = w["Food Insecure Households"]
    w["modsev"] = w["Moderately Food Insecure Households"] + w["Severely Food Insecure Households"]
    w["year"], w["area"] = 2021, w["province_name"]
    A = pd.concat([h[["area", "year", "any", "modsev"]], w[["area", "year", "any", "modsev"]]]).dropna()
    r = {}
    for y, g in A.groupby("year"):
        r[str(int(y))] = {"n": int(len(g)), "share_any_ge50": float((g["any"] >= 50).mean()), "share_modsev_ge50": float((g["modsev"] >= 50).mean()), "mean_any": float(g["any"].mean()), "mean_modsev": float(g["modsev"].mean()), "spearman_any_modsev": float(spearmanr(g["any"], g["modsev"]).statistic)}
    five = A[A["area"].str.title().isin(CAL)].sort_values(["area", "year"]).round(1)
    return {"by_round": r, "calabarzon_rows": five.to_dict(orient="records"), "note": "ENNS 2018-2019 and 2021 sources only. Moderate-or-severe here is HFIAS moderate plus severe, not FIES."}


def hfias_vs_sws() -> dict:
    """Do HFIAS round-to-round changes move with SWS in the same area? Compatibility of two instruments, not validation of the model."""
    Fe.LT = 0.0
    b = Fe.base_rows()
    a = b.groupby(["sws_area", "survey", "year"])["y"].mean().reset_index().sort_values(["sws_area", "year"])
    s = D.sws_quarterly()
    s["year"] = (s["qi"] // 4).astype(int)
    sy = s.groupby(["area", "year"])["hunger"].mean().reset_index()
    rows = []
    for ar, g in a.groupby("sws_area"):
        g = g.reset_index(drop=True)
        z = sy[sy["area"] == ar].set_index("year")["hunger"]
        for j in range(1, len(g)):
            y0, y1 = int(g["year"].iloc[j - 1]), int(g["year"].iloc[j])
            if y0 in z.index and y1 in z.index:
                rows.append({"area": ar, "from": y0, "to": y1, "d_hfias_logit": float(g["y"].iloc[j] - g["y"].iloc[j - 1]), "d_sws_logit": float(Fe._logit(z[y1]) - Fe._logit(z[y0]))})
    R = pd.DataFrame(rows)
    return {"n": int(len(R)), "spearman": float(spearmanr(R["d_hfias_logit"], R["d_sws_logit"]).statistic) if len(R) > 3 else None, "same_direction": float(((R["d_hfias_logit"] > 0) == (R["d_sws_logit"] > 0)).mean()) if len(R) else None, "rows": R.round(3).to_dict(orient="records"), "note": "Rounds through 2019 in Fe.base_rows; few pairs."}


def construct() -> dict:
    """Do news streams move with the thing they are named after, as of the same quarter? Uses no food-insecurity outcome."""
    P = pd.read_parquet(OUT / "news_panel.parquet")
    n = P[(P["stream"] == "nat") & (P["lag_m"] == 0)].set_index("qi")
    G = R150.province_inputs().groupby("qi")[["cpi_food_yoy", "cpi_rice_yoy", "c_tc_4q", "c_rain_anom_6m", "oni", "unemp_rate", "remit_yoy"]].mean()
    pairs = [("e_market", "cpi_food_yoy"), ("e_market", "cpi_rice_yoy"), ("e_climate", "c_tc_4q"), ("e_climate", "oni"), ("e_employment", "unemp_rate"), ("e_remittance", "remit_yoy"), ("e_net", "cpi_food_yoy"), ("e_net", "unemp_rate")]
    out = {}
    for a, b in pairs:
        z = pd.concat([n[a], G[b]], axis=1).dropna()
        c = spearmanr(z[a], z[b]).statistic if len(z) > 8 else np.nan
        # a block shuffle reference: is the correlation larger than rotating one series in time?
        r = np.random.default_rng(151)
        v = z[b].values
        nul = [spearmanr(z[a].values, np.roll(v, r.integers(4, max(5, len(v) - 4)))).statistic for _ in range(1000)]
        out[f"{a}~{b}"] = {"n": int(len(z)), "spearman": float(c), "share_rotations_as_large": float(np.mean(np.abs(nul) >= abs(c)))}
    top = {}
    for c in ("e_market", "e_climate", "e_employment", "e_remittance", "e_hunger", "e_response"):
        top[c] = [qlabel(int(i)) for i in n[c].sort_values(ascending=False).head(5).index]
    return {"correlations": out, "top_quarters": top, "shocks_for_reading": "Yolanda 2013-Q4; rice crisis 2018-Q2 to Q4; COVID 2020-Q2; rice 2023-Q3 and El Nino 2024-Q1 to Q2. A window ending before the issue date reads the previous quarter."}


def fies_context() -> dict:
    """Contextual only: 2021 forecast of HFIAS any-level by region against FIES 2023 moderate-or-severe by region. Different instruments, different years."""
    f = pd.read_csv(DATA / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv")
    f = f[(f["level"] == "region") & (f["year"] == 2023)].copy()
    f["reg"] = f["geography"].map(_norm_region)
    p = OUT / "prov_oof.csv"
    if not p.exists():
        return {"status": "no forecasts yet"}
    o = pd.read_csv(p)
    o = o[(o["survey"] == "ENNS2021") & (o["lead"] == 1)].copy()
    o["reg"] = o["region"].map(lambda s: _norm_region(s) or s)
    m = o.groupby("reg").agg(mu=("mu_GNT", "mean"), y=("y_true", "mean"), n=("key", "size"))
    z = f.set_index("reg")[["percent"]].join(m, how="inner")
    return {"n_regions": int(len(z)), "spearman_forecast_vs_fies2023": float(spearmanr(z["mu"], z["percent"]).statistic) if len(z) > 3 else None, "spearman_hfias2021_vs_fies2023": float(spearmanr(z["y"], z["percent"]).statistic) if len(z) > 3 else None, "calabarzon_fies2023": float(f[f["reg"] == "CALABARZON"]["percent"].iloc[0]) if (f["reg"] == "CALABARZON").any() else None, "note": "Different instruments and years; agreement is contextual, not validation."}


def main():
    res = {"measures": measures(), "hfias_vs_sws": hfias_vs_sws(), "construct": construct(), "fies_context": fies_context()}
    (OUT / "validation.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps({k: (v if k != "hfias_vs_sws" else {x: y for x, y in v.items() if x != "rows"}) for k, v in res.items()}, indent=0, default=float)[:6000])


if __name__ == "__main__":
    main()

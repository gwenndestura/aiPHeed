"""
app/cb6_auto/features.py
------------------------
The C-B6 input row of one origin, ported without change of rule from the experiment code that built the development table:
HISTORY_RETRAIN/runner/hr_lib.py (rows_t2 and helpers), SENIOR_REVIEW/runner/prospective_lib.py (add_news_anomaly),
OBJECTIVES_AUDIT/runner/cb6_model.py (st_values). tests/unit/test_cb6_auto.py checks every origin against the stored table.

Time index: month ym = year*12 + month-1; quarter q = year*4 + quarter-1. O(t), the issue date of origin t, is the first day
of quarter t+1. Only values published before O(t) enter: CPI/ONI/Pink Sheet to month 2 of quarter t, production to quarter
t-1, typhoons to quarter t, rice stocks to issue month - 4, SWS rounds with published < O(t). A missing value stays NaN.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
REGION = "PH040000000"
AREAS = {"NCR": "metro_manila", "BL": "balance_luzon", "VIS": "visayas", "MIN": "mindanao"}
H_LINE, SIGMA_H_FALLBACK, POOL_MIN = 11.3, 4.0, 8
WORLD = ["W_rice_yoy", "W_rice_mom", "W_cereal_yoy", "W_crude_yoy", "W_urea_yoy"]
NEWS_WIN, NEWS_MINP = 8, 4
STOCK_LAG_MONTHS = 4
GROUPS = {"market": ["R_food_yoy", "R_head_yoy", "R_food_mom", "R_rice_yoy"] + WORLD,
          "climate": ["ONI_last", "ONI_max12", "tc_mean", "R_C3"], "fish_kill": ["R_C4"],
          "hunger": ["h_last", "h_change", "h_mean4", "true_h", "pi_H4L"], "news": ["z_N1R"], "lead": ["lead"],
          "employment": [], "ofw_remittance": [], "supply": ["ST1", "ST2"]}


def qs(i: int) -> str:
    return f"{int(i) // 4}-Q{int(i) % 4 + 1}"


def qi(s: str) -> int:
    return int(s[:4]) * 4 + int(s[-1]) - 1


def m0_of(t: int) -> int:
    """Newest CPI / ONI / Pink Sheet month usable at O(t): month 2 of quarter t."""
    return (t // 4) * 12 + (t % 4) * 3 + 1


def issue(t: int) -> str:
    n = t + 1
    return f"{n // 4}-{(n % 4) * 3 + 1:02d}-01"


def origin_of_issue(date_str: str) -> int:
    y, m = int(date_str[:4]), int(date_str[5:7])
    assert date_str[8:10] == "01" and m in (1, 4, 7, 10), f"{date_str} is not the first day of a quarter"
    return y * 4 + (m - 1) // 3 - 1


@dataclass
class Data:
    idx: dict            # "food" | "all_items" | "rice" -> Series by ym (Region IV-A CPI)
    sws: pd.DataFrame    # area, q, H, published
    oni: pd.Series       # by end-month ym
    pink: pd.DataFrame   # index ym
    prod: dict           # "Palay" | "Corn" | "FISHERIES" -> Series by q (Region IV-A)
    tc: dict             # province -> Series by q
    stocks: pd.DataFrame  # index ym: total, nfa, household, commercial
    n1r: pd.Series       # by origin t


def _value_series(df: pd.DataFrame, kcol: str) -> pd.Series:
    return df.dropna(subset=["value"]).set_index(kcol)["value"].astype(float).sort_index()


def load(src: Path) -> Data:
    item = {"0 - ALL ITEMS": "all_items", "01.1 - FOOD": "food"}
    cpi = pd.concat([pd.read_csv(src / f, dtype={"geo_code": str}) for f in ("cpi_backcast_ACP28.csv", "cpi_ACP22.csv")])
    cpi["commodity"] = cpi["item"].map(item)
    assert not cpi.dropna(subset=["value"]).duplicated(["commodity", "ym"]).any(), "duplicate CPI months"
    idx = {c: _value_series(g, "ym") for c, g in cpi.groupby("commodity")}
    idx["rice"] = _value_series(pd.read_csv(src / "cpi_rice_region.csv"), "ym")
    s = pd.read_csv(src / "sws_area_rounds_full.csv")
    s = s[~s["commissioned"].astype(bool)]
    rows = [{"area": a, "q": qi(x["quarter"]), "H": float(x[col]), "published": str(x["published"])[:10]}
            for _, x in s.iterrows() for a, col in AREAS.items() if pd.notna(x[col])]
    o = pd.read_csv(src / "cov_oni.csv")
    oni = pd.Series(o["oni"].to_numpy(float), index=(o["end_year"] * 12 + o["end_month"] - 1).to_numpy()).sort_index()
    pink = pd.read_csv(src / "pinksheet_monthly_1960.csv").set_index("ym").sort_index()
    prod = {}
    for f in ("palay_corn_EVCP0.csv", "fisheries_GVFP1.csv"):
        d = pd.read_csv(src / f, dtype={"geo_code": str})
        prod.update({k: _value_series(g, "q") for k, g in d.groupby("item")})
    ty = pd.read_csv(src / "typhoons_province_quarter.csv", dtype={"province_code": str})
    tc = {p: g.set_index("q")["tc_count"].astype(float).sort_index() for p, g in ty.groupby("province_code")}
    stocks = pd.read_csv(src / "tidy_stocks_national.csv").set_index("ym").sort_index()
    n = pd.read_csv(src / "n1r_history.csv")
    n1r = pd.Series(n["N1R"].to_numpy(float), index=n["t"].to_numpy()).sort_index()
    return Data(idx, pd.DataFrame(rows), oni, pink, prod, tc, stocks, n1r)


def known(d: Data, t: int, area: str) -> list[tuple[int, float, str]]:
    r = d.sws[(d.sws["area"] == area) & (d.sws["published"] < issue(t))]
    return [(int(q), float(g["H"].mean()), g["published"].max()) for q, g in sorted(r.groupby("q"), key=lambda x: x[0])]


def pi_h4l(d: Data, t: int, k: int) -> dict:
    kn = known(d, t, "BL")
    if not kn:
        return {"pi": np.nan, "h_last": np.nan, "true_h": np.nan, "published": None, "kn": []}
    q_last, h_last = kn[-1][0], kn[-1][1]
    h = (t + k) - q_last
    errs = []
    for a in AREAS:
        dd = {x[0]: x[1] for x in known(d, t, a)}
        errs += [dd[q + h] - dd[q] for q in dd if q + h in dd]
    if len(errs) < POOL_MIN:
        dd = {x[0]: x[1] for x in kn}
        e0 = [dd[q + h] - dd[q] for q in dd if q + h in dd]
        sig = math.sqrt(np.mean(np.square(e0))) if len(e0) >= 4 else SIGMA_H_FALLBACK
    else:
        sig = math.sqrt(float(np.mean(np.square(errs))))
    return {"pi": float(norm.cdf((h_last - H_LINE) / max(sig, 0.5))), "h_last": h_last, "true_h": h,
            "published": kn[-1][2], "kn": kn}


def _at(s: pd.Series | None, k) -> float:
    return float(s[k]) if s is not None and k in s.index else np.nan


def _yoy_q(s: pd.Series | None, q: int) -> float:
    a, b = _at(s, q), _at(s, q - 4)
    return 100 * (a / b - 1) if np.isfinite(a) and np.isfinite(b) and b != 0 else np.nan


def _ry(s: pd.Series | None, m: int) -> float:
    return 100 * (s[m] / s[m - 12] - 1) if s is not None and m in s.index and m - 12 in s.index else np.nan


def _mom3(s: pd.Series | None, m0: int) -> float:
    return 100 * (math.log(s[m0]) - math.log(s[m0 - 3])) if s is not None and m0 in s.index and m0 - 3 in s.index else np.nan


def _cut(s: pd.Series | None, limit: int) -> pd.Series | None:
    return None if s is None else s[s.index <= limit]


def world(d: Data, t: int) -> dict:
    m0 = m0_of(t)
    w = d.pink[d.pink.index <= m0]

    def yoy(c):
        return float(100 * (w.loc[m0, c] / w.loc[m0 - 12, c] - 1)) if m0 in w.index and m0 - 12 in w.index else np.nan
    mom = (float(100 * (math.log(w.loc[m0, "rice_thai5"]) - math.log(w.loc[m0 - 3, "rice_thai5"])))
           if m0 in w.index and m0 - 3 in w.index else np.nan)
    cer = np.array([yoy("rice_thai5"), yoy("wheat_hrw"), yoy("maize")])
    cer_m = float(np.nanmean(cer)) if np.isfinite(cer).any() else np.nan
    return {"W_rice_yoy": yoy("rice_thai5"), "W_rice_mom": mom, "W_cereal_yoy": cer_m, "W_crude_yoy": yoy("crude_avg"),
            "W_urea_yoy": yoy("urea")}


def st_values(S: pd.DataFrame, t: int) -> tuple[float, float]:
    iss = issue(t)
    m = int(iss[:4]) * 12 + int(iss[5:7]) - 1 - STOCK_LAG_MONTHS
    if m not in S.index or m - 12 not in S.index:
        return np.nan, np.nan
    a, b = S.loc[m], S.loc[m - 12]
    if not (b["total"] > 0 and a["total"] > 0):
        return np.nan, np.nan
    return float((a["total"] / b["total"] - 1) * 100), float(100 * a["nfa"] / a["total"] - 100 * b["nfa"] / b["total"])


def z_n1r(n1r: pd.Series, t: int) -> float:
    """(N1R(t) - mean(N1R over origins t-8..t-1)) / sd (ddof 1); NaN below 4 past values, at sd 0, or without N1R(t)."""
    x = n1r.get(t, np.nan)
    past = n1r.reindex([i for i in range(t - NEWS_WIN, t) if i in n1r.index]).dropna()
    sd = float(past.std(ddof=1)) if len(past) >= 2 else float("nan")
    return float((x - past.mean()) / sd) if pd.notna(x) and len(past) >= NEWS_MINP and sd > 0 else np.nan


def rows_origin(d: Data, t: int, leads=(1, 2)) -> list[dict]:
    m0 = m0_of(t)
    fy, hy, rice = (_cut(d.idx.get(c), m0) for c in ("food", "all_items", "rice"))
    both = lambda s: (float(np.nanmean([_ry(s, m0 - 1), _ry(s, m0)]))  # noqa: E731
                      if np.isfinite([_ry(s, m0 - 1), _ry(s, m0)]).all() else np.nan)
    o = d.oni[d.oni.index <= m0]
    w12 = o[o.index > m0 - 12]
    tcs = [_at(d.tc[p][d.tc[p].index <= t], t) if p in d.tc else np.nan for p in PROVS]
    crops = [_yoy_q(_cut(d.prod.get(c), t - 1), t - 1) for c in ("Palay", "Corn")]
    crops = [v for v in crops if np.isfinite(v)]
    st1, st2 = st_values(d.stocks, t)
    base = {"t": t, "R_food_yoy": both(fy), "R_head_yoy": both(hy), "R_rice_yoy": _ry(rice, m0), "R_food_mom": _mom3(fy, m0),
            "ONI_last": _at(o, m0), "ONI_max12": float(w12.max()) if len(w12) else np.nan,
            "tc_mean": float(np.mean(tcs)) if np.isfinite(tcs).all() else np.nan,
            "R_C3": -min(crops) if crops else np.nan, "R_C4": -_yoy_q(_cut(d.prod.get("FISHERIES"), t - 1), t - 1),
            **world(d, t), "z_N1R": z_n1r(d.n1r, t), "ST1": st1, "ST2": st2}
    kn = pi_h4l(d, t, 1)["kn"]
    hs = [x[1] for x in kn]
    out = []
    for k in leads:
        hz = pi_h4l(d, t, k)
        out.append({**base, "lead": k, "q": t + k, "pi_H4L": hz["pi"], "h_last": hz["h_last"], "true_h": hz["true_h"],
                    "h_change": hs[-1] - hs[-2] if len(hs) >= 2 else np.nan,
                    "h_mean4": float(np.mean(hs[-4:])) if hs else np.nan, "sws_newest_published": hz["published"],
                    "sws_newest_q": qs(kn[-1][0]) if kn else None})
    return out


def freshness(d: Data, t: int) -> dict:
    """True when each source reaches the newest period the release rules allow at O(t). False = stale: its inputs are NaN
    (news, typhoons, CPI...) and the forecast records that. SWS is listed separately: a quarter's round being unpublished at
    O(t) is normal, and the forecast then starts from the newest published round."""
    m0 = m0_of(t)
    iss = issue(t)
    stock_m = int(iss[:4]) * 12 + int(iss[5:7]) - 1 - STOCK_LAG_MONTHS
    return {"cpi_food_month2": m0 in d.idx.get("food", pd.Series(dtype=float)).index,
            "cpi_headline_month2": m0 in d.idx.get("all_items", pd.Series(dtype=float)).index,
            "cpi_rice_month2": m0 in d.idx.get("rice", pd.Series(dtype=float)).index,
            "oni_month2": m0 in d.oni.index, "pinksheet_month2": m0 in d.pink.index,
            "palay_corn_quarter_t-1": (t - 1) in d.prod.get("Palay", pd.Series(dtype=float)).index,
            "fisheries_quarter_t-1": (t - 1) in d.prod.get("FISHERIES", pd.Series(dtype=float)).index,
            "typhoons_quarter_t": all(p in d.tc and t in d.tc[p].index for p in PROVS),
            "rice_stocks_issue-4": stock_m in d.stocks.index,
            "news_n1r_quarter_t": pd.notna(d.n1r.get(t, np.nan))}


def cutoffs(d: Data, t: int) -> dict:
    """The newest period of each source actually used at O(t), for the forecast record."""
    m0 = m0_of(t)

    def ym(ix, lim=m0):
        ix = [int(x) for x in ix if int(x) <= lim]
        return f"{max(ix) // 12}-{max(ix) % 12 + 1:02d}" if ix else None
    kn = known(d, t, "BL")
    return {"cpi_food_month": ym(d.idx["food"].index), "cpi_rice_month": ym(d.idx["rice"].index), "oni_month": ym(d.oni.index),
            "pinksheet_month": ym(d.pink.index), "stocks_month": ym(d.stocks.index, m0 - 2),
            "sws_newest_quarter": qs(kn[-1][0]) if kn else None, "sws_newest_published": kn[-1][2] if kn else None,
            "n1r_quarter": qs(t) if pd.notna(d.n1r.get(t, np.nan)) else None}


def load_centroids(path: Path) -> dict:
    return {k: tuple(v) for k, v in json.loads(path.read_text(encoding="utf-8")).items()}

"""HISTORY_RETRAIN library (PLAN.md 6b9f17fb, PLAN_AMENDMENT_1.md 319ae4d2): long-history data, labels T1/T2, the
hunger term pi_H4L, feature rows F_b / F_c for T1 and T2, models PERSIST / LOGIT / LGBM, and the frozen R1-R7 scorer.

Every input is read through one Data object so that the leakage audit (PLAN section 8.2) can randomize everything
published on or after an issue date and rebuild the same rows.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True        # read-only imports from other experiment folders must leave nothing behind

import copy
import hashlib
import importlib.util
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
HR = HERE.parent
EXP = HR.parent
DATA = HR / "data"
OUT = HR / "out"
LONG = EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "data" / "long"
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
REGION = "PH040000000"
AREAS = {"NCR": "metro_manila", "BL": "balance_luzon", "VIS": "visayas", "MIN": "mindanao"}
H_LINE, SIGMA_H_FALLBACK, POOL_MIN = 11.3, 4.0, 8
FIRST_ORIGIN = 1998 * 4 + 2                          # 1998-Q3: first origin with a published SWS reading
FIRST_ORIGIN_C = 2011 * 4 + 1                        # 2011-Q2: option (c) (PLAN section 4)
FIRST_YM_PUBLISHED_YOY = 2021 * 12                   # 2021-01: label YoY as PSA published (E40 file)
KMAX = 15                                            # leads stacked in the LightGBM, as served
EVAL_FIRST, EVAL_LAST = 2010 * 4, 2026 * 4 + 2       # targets 2010-Q1..2026-Q3
ORIGINS_EVAL = list(range(EVAL_FIRST - 2, EVAL_LAST))  # 2009-Q3..2026-Q2
HEADLINE_P60 = {"PH040100000": 5.013333, "PH040200000": 4.653333, "PH040300000": 5.060000,
                "PH040400000": 6.073333, "PH040500000": 5.546667}   # E68 e68_lib.HEADLINE_P60 (as served)
SEED_LGBM = 2027
GRID = [dict(id=i, depth=d, leaves=2 ** d, trees=n, cw=w)              # B.GRID (E108), as served
        for i, (d, n, w) in enumerate([(d, n, w) for d in (1, 2) for n in (50, 150) for w in (None, "balanced")])]
MONO_UP = ["A1_food", "A1_gap", "A_mom"]
WORLD = ["W_rice_yoy", "W_rice_mom", "W_cereal_yoy", "W_crude_yoy", "W_urea_yoy"]
T1_B = ["A1_food", "A1_gap", "A_mom", "A2", "R_rice_yoy", "V1", "ONI_last", "ONI_max12", "C2", "C3", "C4"] + WORLD + ["H1"]
T1_C_EXTRA = ["E1", "A3", "N1", "G_pri_yoy", "NG_gap_price"]
T2_B = ["h_last", "h_change", "h_mean4", "true_h", "pi_H4L", "R_food_yoy", "R_head_yoy", "R_rice_yoy", "R_food_mom",
        "ONI_last", "ONI_max12", "tc_mean", "R_C3", "R_C4"] + WORLD
T2_C_EXTRA = ["E1", "R_A3", "N1", "G_pri_yoy"]


def qs(i: int) -> str:
    return f"{int(i) // 4}-Q{int(i) % 4 + 1}"


def qi(s: str) -> int:
    return int(s[:4]) * 4 + int(s[-1]) - 1


def m0_of(t: int) -> int:
    """Newest CPI / ONI / Pink Sheet month usable at O(t): month 2 of quarter t."""
    return (t // 4) * 12 + (t % 4) * 3 + 1


def issue(t: int) -> str:
    """O(t) = first day of quarter t+1."""
    n = t + 1
    return f"{n // 4}-{(n % 4) * 3 + 1:02d}-01"


def q_of_ym(ym: int) -> int:
    return (ym // 12) * 4 + (ym % 12) // 3


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ================================================================================================ data
@dataclass
class Data:
    idx: dict            # (geo, commodity) -> Series by ym   commodity in {all_items, food, rice}
    yoy: dict            # (prov, commodity) -> Series by ym  (label YoY: recomputed < 2021-01, published >= 2021-01)
    sws: pd.DataFrame    # area, q, H, published
    oni: pd.Series       # by end-month ym
    pink: pd.DataFrame   # index ym
    prod: dict           # (geo, crop) -> Series by q   crop in {Palay, Corn, FISHERIES}
    rice_w: dict         # geo -> Series by ym (wholesale RMR)
    tc: dict             # prov -> Series by q
    lfs: pd.Series       # national unemployment rate by ym (survey months only)
    news: pd.DataFrame   # origin q, province_code, N1, G_pri_yoy, NG_gap_price (2021-Q1+)
    v1: dict             # prov -> static V1


def _series(df, key_cols, kcol, vcol="value"):
    out = {}
    for k, g in df.dropna(subset=[vcol]).groupby(key_cols):
        out[k] = g.set_index(kcol)[vcol].astype(float).sort_index()
    return out


def load() -> Data:
    item = {"0 - ALL ITEMS": "all_items", "01.1 - FOOD": "food"}
    cpi = pd.concat([pd.read_csv(DATA / f, dtype={"geo_code": str}) for f in ("cpi_backcast_ACP28.csv", "cpi_ACP22.csv")])
    cpi["commodity"] = cpi["item"].map(item)
    assert not cpi.dropna(subset=["value"]).duplicated(["geo_code", "commodity", "ym"]).any()
    idx = _series(cpi, ["geo_code", "commodity"], "ym")
    c = pd.read_csv(LONG / "cov_cpi.csv")
    r = c[(c["geolocation"] == "Region IV-A (CALABARZON)") & c["commodity_description"].str.contains("Rice")]
    idx[(REGION, "rice")] = r.dropna(subset=["value"]).set_index("ym")["value"].astype(float).sort_index()
    pub = pd.read_csv(EXP / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv",
                      dtype={"province_code": str})
    pub["ym"] = pub["reference_month"].str[:4].astype(int) * 12 + pub["reference_month"].str[5:7].astype(int) - 1
    yoy = {}
    for p in PROVS:
        for com in ("all_items", "food"):
            s = idx[(p, com)]
            vals = {m: 100 * (s[m] / s[m - 12] - 1) for m in s.index if m - 12 in s.index and m < FIRST_YM_PUBLISHED_YOY}
            pp = pub[(pub["province_code"] == p) & (pub["commodity"] == com)].set_index("ym")["yoy_pct"].astype(float)
            vals.update({int(m): float(v) for m, v in pp.items()})
            yoy[(p, com)] = pd.Series(vals).sort_index()
    s = pd.read_csv(LONG / "sws_area_rounds_full.csv")
    s = s[~s["commissioned"].astype(bool)]
    rows = [{"area": a, "q": qi(x["quarter"]), "H": float(x[col]), "published": str(x["published"])[:10],
             "mode": x["mode"], "base": x["respondent_base"]}
            for _, x in s.iterrows() for a, col in AREAS.items() if pd.notna(x[col])]
    sws = pd.DataFrame(rows)
    o = pd.read_csv(LONG / "cov_oni.csv")
    oni = pd.Series(o["oni"].to_numpy(float), index=(o["end_year"] * 12 + o["end_month"] - 1).to_numpy()).sort_index()
    pink = pd.read_csv(DATA / "pinksheet_monthly_1960.csv").set_index("ym").sort_index()
    pc = pd.read_csv(DATA / "palay_corn_EVCP0.csv", dtype={"geo_code": str})
    fi = pd.read_csv(DATA / "fisheries_GVFP1.csv", dtype={"geo_code": str})
    prod = {**_series(pc, ["geo_code", "item"], "q"), **_series(fi, ["geo_code", "item"], "q")}
    rw = pd.read_csv(DATA / "rice_wholesale_AWB01.csv", dtype={"geo_code": str})
    rice_w = {g: x.dropna(subset=["value"]).set_index("ym")["value"].astype(float).sort_index()
              for g, x in rw.groupby("geo_code")}
    ty = pd.read_csv(DATA / "typhoons_province_quarter.csv", dtype={"province_code": str})
    tc = {p: d.set_index("q")["tc_count"].astype(float).sort_index() for p, d in ty.groupby("province_code")}
    lf = pd.read_csv(LONG / "cov_lfs.csv")
    months = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                          "September", "October", "November", "December"])}
    lf = lf[lf["Month"].isin(months)].copy()
    lf["v"] = pd.to_numeric(lf["Unemployment Rate Both sexes"], errors="coerce")
    lf = lf.dropna(subset=["v"])
    lfs = pd.Series(lf["v"].to_numpy(float), index=(lf["Year"].astype(int) * 12 + lf["Month"].map(months)).to_numpy())
    tt = pd.read_csv(EXP / "FIRI_V2_DATA_AUDIT" / "out" / "training_table_lead1.csv", dtype={"province_code": str})
    news = tt[["origin", "province_code", "N1", "G_pri_yoy", "NG_gap_price"]].copy()
    news["t"] = news["origin"].map(qi)
    v1 = tt.groupby("province_code")["V1"].first().to_dict()
    assert tt.groupby("province_code")["V1"].nunique().eq(1).all()
    return Data(idx, yoy, sws, oni, pink, prod, rice_w, tc, lfs.sort_index(), news.drop(columns="origin"), v1)


def perturb(d: Data, t: int, seed: int) -> Data:
    """Every value published on or after O(t) randomized (PLAN 8.2); values usable at O(t) untouched."""
    rng = np.random.default_rng(seed)
    m0, O = m0_of(t), issue(t)
    e = copy.deepcopy(d)

    def scr(s: pd.Series, mask) -> pd.Series:
        s = s.copy()
        s[mask] = rng.normal(0, 50, int(mask.sum())) + 100
        return s
    e.idx = {k: scr(s, s.index > m0) for k, s in e.idx.items()}
    e.yoy = {k: scr(s, s.index > m0) for k, s in e.yoy.items()}
    late = e.sws["published"] >= O
    e.sws.loc[late, "H"] = rng.uniform(0, 40, int(late.sum()))
    e.oni = scr(e.oni, e.oni.index > m0)
    e.pink = e.pink.copy()
    num = [c for c in e.pink.columns if c != "month"]
    e.pink.loc[e.pink.index > m0, num] = rng.uniform(1, 500, (int((e.pink.index > m0).sum()), len(num)))
    e.prod = {k: scr(s, s.index > t - 1) for k, s in e.prod.items()}
    lm = (t - 1) // 4 * 12 + ((t - 1) % 4) * 3 + 2                    # last month of quarter t-1
    e.rice_w = {k: scr(s, s.index > lm) for k, s in e.rice_w.items()}
    e.tc = {k: scr(s, s.index > t) for k, s in e.tc.items()}
    e.lfs = scr(e.lfs, e.lfs.index > lm)
    e.news = e.news.copy()
    nl = e.news["t"] > t
    e.news.loc[nl, ["N1", "G_pri_yoy", "NG_gap_price"]] = rng.normal(0, 9, (int(nl.sum()), 3))
    return e


# ================================================================================================ labels
def bl_quarters(d: Data) -> pd.Series:
    r = d.sws[d.sws["area"] == "BL"]
    return r.groupby("q")["H"].mean().sort_index()


def price_frame(d: Data) -> pd.DataFrame:
    """Price condition per complete CPI quarter (quarter mean of the three monthly YoY; E40 thresholds)."""
    th = frozen_thresholds()
    rows = []
    for p in PROVS:
        f, h = d.yoy[(p, "food")], d.yoy[(p, "all_items")]
        for q in sorted({q_of_ym(m) for m in f.index}):
            ms = [q // 4 * 12 + (q % 4) * 3 + i for i in range(3)]
            if all(m in f.index for m in ms) and all(m in h.index for m in ms):
                F, HL = float(np.mean([f[m] for m in ms])), float(np.mean([h[m] for m in ms]))
                rows.append({"province_code": p, "q": q, "F": F, "HL": HL,
                             "price": int(F > th["food"][p] or (F - HL) > th["gap"][p])})
    return pd.DataFrame(rows)


_TH: dict = {}


def frozen_thresholds() -> dict:
    if not _TH:
        import json
        s = json.loads((EXP / "E40_SWS_CPI_Tiers" / "label_spec.json").read_text())["thresholds"]
        _TH.update({"food": s["food"], "gap": s["gap"], "H": s["H"]})
        assert _TH["H"] == H_LINE
    return _TH


def t1_labels(d: Data) -> pd.DataFrame:
    """T1 (T43c) for every province-quarter with a non-commissioned BL round and a complete CPI quarter."""
    h = bl_quarters(d)
    ps = price_frame(d)
    o = ps[ps["q"].isin(h.index)].copy()
    o["H"] = o["q"].map(h)
    o["hunger"] = (o["H"] > H_LINE).astype(int)
    o["y"] = (o["hunger"] & o["price"]).astype(int)
    return o.reset_index(drop=True)


def t2_labels(d: Data) -> pd.DataFrame:
    h = bl_quarters(d)
    return pd.DataFrame({"q": h.index.astype(int), "H": h.values, "y": (h.values > H_LINE).astype(int)})


def complete_bl(d: Data, t: int) -> set:
    """BL quarters q <= t-1 whose every round was published before O(t)."""
    r = d.sws[d.sws["area"] == "BL"]
    O = issue(t)
    return {int(q) for q, g in r.groupby("q") if (g["published"] < O).all() and q <= t - 1}


# ================================================================================================ hunger term
def known(d: Data, t: int, area: str, min_q: int | None = None) -> list[tuple[int, float, str]]:
    r = d.sws[(d.sws["area"] == area) & (d.sws["published"] < issue(t))]
    if min_q is not None:
        r = r[r["q"] >= min_q]
    return [(int(q), float(g["H"].mean()), g["published"].max()) for q, g in sorted(r.groupby("q"), key=lambda x: x[0])]


def pi_h4l(d: Data, t: int, k: int, min_q: int | None = None) -> dict:
    """H4 on the long record: sigma = RMSE of latest-reading errors pooled over the four areas at the true horizon;
    < 8 pooled errors -> H0 (BL errors, >= 4, else 4.0). min_q=2021-Q1 reproduces the served 2021+ H4."""
    kn = known(d, t, "BL", min_q)
    if not kn:
        return {"pi": np.nan, "h_last": np.nan, "true_h": np.nan, "sws_newest_published": None, "fallback": None}
    q_last, h_last = kn[-1][0], kn[-1][1]
    h = (t + k) - q_last
    errs = []
    for a in AREAS:
        dd = {x[0]: x[1] for x in known(d, t, a, min_q)}
        errs += [dd[q + h] - dd[q] for q in dd if q + h in dd]
    fb = len(errs) < POOL_MIN
    if fb:
        dd = {x[0]: x[1] for x in kn}
        e0 = [dd[q + h] - dd[q] for q in dd if q + h in dd]
        sig = math.sqrt(np.mean(np.square(e0))) if len(e0) >= 4 else SIGMA_H_FALLBACK
    else:
        sig = math.sqrt(float(np.mean(np.square(errs))))
    return {"pi": float(norm.cdf((h_last - H_LINE) / max(sig, 0.5))), "h_last": h_last, "true_h": h,
            "sws_newest_published": kn[-1][2], "fallback": fb, "kn": kn}


# ================================================================================================ features
def _at(s: pd.Series | None, k) -> float:
    return float(s[k]) if s is not None and k in s.index else np.nan


def _yoy_q(s: pd.Series | None, q: int) -> float:
    a, b = _at(s, q), _at(s, q - 4)
    return 100 * (a / b - 1) if np.isfinite(a) and np.isfinite(b) and b != 0 else np.nan


def _qmean_month(s: pd.Series | None, q: int) -> float:
    if s is None:
        return np.nan
    ms = [q // 4 * 12 + (q % 4) * 3 + i for i in range(3)]
    v = [s[m] for m in ms if m in s.index]
    return float(np.mean(v)) if v else np.nan


def world(d: Data, t: int) -> dict:
    w = d.pink[d.pink.index <= m0_of(t)]
    m0 = m0_of(t)

    def yoy(c):
        return float(100 * (w.loc[m0, c] / w.loc[m0 - 12, c] - 1)) if m0 in w.index and m0 - 12 in w.index else np.nan
    mom = (float(100 * (math.log(w.loc[m0, "rice_thai5"]) - math.log(w.loc[m0 - 3, "rice_thai5"])))
           if m0 in w.index and m0 - 3 in w.index else np.nan)
    with np.errstate(all="ignore"):
        cer = np.array([yoy("rice_thai5"), yoy("wheat_hrw"), yoy("maize")])
        cer_m = float(np.nanmean(cer)) if np.isfinite(cer).any() else np.nan
    return {"W_rice_yoy": yoy("rice_thai5"), "W_rice_mom": mom, "W_cereal_yoy": cer_m, "W_crude_yoy": yoy("crude_avg"),
            "W_urea_yoy": yoy("urea")}


def _cut_idx(d: Data, key, m0):
    s = d.idx.get(key)
    return None if s is None else s[s.index <= m0]


def _projection(s: pd.Series | None, t: int, k: int) -> float:
    """Mean YoY of the target months of t+k with the newest index (m0) held flat (E107 projection, base >= 1994-01)."""
    m0 = m0_of(t)
    if s is None or m0 not in s.index:
        return np.nan
    first = (t + k) // 4 * 12 + ((t + k) % 4) * 3
    vals = [100 * (s[m0] / s[b] - 1) for b in (first - 12, first - 11, first - 10) if b <= m0 and b in s.index]
    return float(np.mean(vals)) if len(vals) >= 2 else np.nan


def _mom3(s: pd.Series | None, m0: int) -> float:
    return 100 * (math.log(s[m0]) - math.log(s[m0 - 3])) if s is not None and m0 in s.index and m0 - 3 in s.index else np.nan


def _crop_drop(d: Data, geo: str, t: int) -> float:
    ys = [_yoy_q(_cut_q(d.prod.get((geo, c)), t), t - 1) for c in ("Palay", "Corn")]
    ys = [v for v in ys if np.isfinite(v)]
    return -min(ys) if ys else np.nan


def _cut_q(s, t):
    return None if s is None else s[s.index <= t - 1]


def _e1(d: Data, t: int) -> float:
    lm = (t - 1) // 4 * 12 + ((t - 1) % 4) * 3 + 2
    s = d.lfs[d.lfs.index <= lm]
    a, b = _qmean_month(s, t - 1), _qmean_month(s, t - 5)
    return a - b if np.isfinite(a) and np.isfinite(b) else np.nan


def _a3(d: Data, geo: str, t: int) -> float:
    lm = (t - 1) // 4 * 12 + ((t - 1) % 4) * 3 + 2
    s = d.rice_w.get(geo)
    s = None if s is None else s[s.index <= lm]
    a, b = _qmean_month(s, t - 1), _qmean_month(s, t - 5)
    return 100 * (a / b - 1) if np.isfinite(a) and np.isfinite(b) else np.nan


def _oni(d: Data, t: int) -> dict:
    m0 = m0_of(t)
    o = d.oni[d.oni.index <= m0]
    w = o[o.index > m0 - 12]
    return {"ONI_last": _at(o, m0), "ONI_max12": float(w.max()) if len(w) else np.nan}


def _news(d: Data, t: int) -> pd.DataFrame:
    return d.news[d.news["t"] == t].set_index("province_code")


def rows_t1(d: Data, t: int) -> list[dict]:
    """F_b(T1) + F_c extras for every province and lead 1..KMAX at origin t."""
    th = frozen_thresholds()
    m0 = m0_of(t)
    wf, on = world(d, t), _oni(d, t)
    rice = _cut_idx(d, (REGION, "rice"), m0)
    nw = _news(d, t)
    hz = {k: pi_h4l(d, t, k) for k in range(1, KMAX + 1)}
    e1 = _e1(d, t)
    out = []
    for p in PROVS:
        sf, sa = _cut_idx(d, (p, "food"), m0), _cut_idx(d, (p, "all_items"), m0)
        hy = d.yoy[(p, "all_items")]
        hy = hy[hy.index <= m0]
        a2 = (np.mean([hy[m] for m in (m0 - 1, m0)]) - HEADLINE_P60[p]) if all(m in hy.index for m in (m0 - 1, m0)) else np.nan
        tcs = d.tc.get(p)
        base = {"t": t, "province_code": p, "A_mom": _mom3(sf, m0), "A2": a2,
                "R_rice_yoy": 100 * (rice[m0] / rice[m0 - 12] - 1) if rice is not None and m0 in rice.index and m0 - 12 in rice.index else np.nan,
                "V1": d.v1[p], **on, "C2": _at(None if tcs is None else tcs[tcs.index <= t], t),
                "C3": _crop_drop(d, p, t),
                "C4": -_yoy_q(_cut_q(d.prod.get((p, "FISHERIES")), t), t - 1),
                **wf, "E1": e1, "A3": _a3(d, p, t),
                "N1": float(nw.loc[p, "N1"]) if p in nw.index else np.nan,
                "G_pri_yoy": float(nw.loc[p, "G_pri_yoy"]) if p in nw.index else np.nan,
                "NG_gap_price": float(nw.loc[p, "NG_gap_price"]) if p in nw.index else np.nan}
        for k in range(1, KMAX + 1):
            pf, pa = _projection(sf, t, k), _projection(sa, t, k)
            out.append({**base, "lead": k, "q": t + k, "A1_food": pf - th["food"][p], "A1_gap": (pf - pa) - th["gap"][p],
                        "H1": hz[k]["pi"], "h_last": hz[k]["h_last"], "true_h": hz[k]["true_h"],
                        "sws_newest_published": hz[k]["sws_newest_published"], "H_fallback": hz[k]["fallback"]})
    return out


def rows_t2(d: Data, t: int) -> list[dict]:
    m0 = m0_of(t)
    wf, on = world(d, t), _oni(d, t)
    fy, hy = _cut_idx(d, (REGION, "food"), m0), _cut_idx(d, (REGION, "all_items"), m0)
    rice = _cut_idx(d, (REGION, "rice"), m0)

    def ry(s, m):
        return 100 * (s[m] / s[m - 12] - 1) if s is not None and m in s.index and m - 12 in s.index else np.nan
    nw = _news(d, t)
    tcs = [_at(d.tc[p][d.tc[p].index <= t], t) for p in PROVS]
    base = {"t": t, "R_food_yoy": np.nanmean([ry(fy, m0 - 1), ry(fy, m0)]) if np.isfinite([ry(fy, m0 - 1), ry(fy, m0)]).all() else np.nan,
            "R_head_yoy": np.nanmean([ry(hy, m0 - 1), ry(hy, m0)]) if np.isfinite([ry(hy, m0 - 1), ry(hy, m0)]).all() else np.nan,
            "R_rice_yoy": ry(rice, m0), "R_food_mom": _mom3(fy, m0), **on,
            "tc_mean": float(np.mean(tcs)) if np.isfinite(tcs).all() else np.nan,
            "R_C3": _crop_drop(d, REGION, t), "R_C4": -_yoy_q(_cut_q(d.prod.get((REGION, "FISHERIES")), t), t - 1),
            **wf, "E1": _e1(d, t), "R_A3": _a3(d, REGION, t),
            "N1": float(nw["N1"].mean()) if len(nw) and nw["N1"].notna().any() else np.nan,
            "G_pri_yoy": float(nw["G_pri_yoy"].mean()) if len(nw) and nw["G_pri_yoy"].notna().any() else np.nan}
    hz1 = pi_h4l(d, t, 1)
    kn = hz1.get("kn") or []
    hs = [x[1] for x in kn]
    out = []
    for k in range(1, KMAX + 1):
        hz = pi_h4l(d, t, k)
        out.append({**base, "lead": k, "q": t + k, "pi_H4L": hz["pi"], "h_last": hz["h_last"], "true_h": hz["true_h"],
                    "h_change": hs[-1] - hs[-2] if len(hs) >= 2 else np.nan,
                    "h_mean4": float(np.mean(hs[-4:])) if hs else np.nan,
                    "sws_newest_published": hz["sws_newest_published"], "H_fallback": hz["fallback"]})
    return out


def table(d: Data, which: str, origins) -> pd.DataFrame:
    f = rows_t1 if which == "T1" else rows_t2
    return pd.DataFrame([r for t in origins for r in f(d, t)])


# ================================================================================================ persistence and CLIM
def persist_t1(d: Data, t: int) -> dict:
    """PERSIST-SI (ch1_lib.persist_si): hunger on the newest BL reading AND price on the newest three CPI months."""
    th = frozen_thresholds()
    kn = known(d, t, "BL")
    hung = bool(kn) and kn[-1][1] > H_LINE
    m0 = m0_of(t)
    out = {}
    for p in PROVS:
        f, a = d.yoy[(p, "food")], d.yoy[(p, "all_items")]
        ms = [m0 - 2, m0 - 1, m0]
        if not all(m in f.index for m in ms) or not all(m in a.index for m in ms):
            out[p] = np.nan
            continue
        fm, am = np.mean([f[m] for m in ms]), np.mean([a[m] for m in ms])
        out[p] = float(hung and (fm > th["food"][p] or (fm - am) > th["gap"][p]))
    return out


def persist_t2(d: Data, t: int) -> float:
    kn = known(d, t, "BL")
    return float(kn[-1][1] > H_LINE) if kn else np.nan


def known_t1(d: Data, t: int, L1: pd.DataFrame) -> pd.DataFrame:
    done = complete_bl(d, t)
    return L1[L1["q"].isin(done)]


def known_price(d: Data, t: int, PF: pd.DataFrame) -> pd.DataFrame:
    """Price condition labels of complete CPI quarters q <= t-1 (all months <= m0)."""
    return PF[PF["q"] <= t - 1]


def known_t2(d: Data, t: int, L2: pd.DataFrame) -> pd.DataFrame:
    return L2[L2["q"].isin(complete_bl(d, t))]


# ================================================================================================ models
def eligible(tr: pd.DataFrame) -> bool:
    return tr["q"].nunique() >= 6 and int(tr["y"].sum()) >= 5 and int((1 - tr["y"]).sum()) >= 5


class LGBM:
    """uni_lib.UniPrice, unchanged settings."""

    def __init__(self, cfg: dict, cols: list[str], mono: bool):
        self.cfg, self.cols, self.mono = cfg, cols, mono
        self.m = self.const = None

    def fit(self, tr: pd.DataFrame):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        kw = {}
        if self.mono:
            kw["monotone_constraints"] = [1 if c in MONO_UP else 0 for c in self.cols]
            kw["monotone_constraints_method"] = "basic"
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, reg_lambda=5.0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=SEED_LGBM, n_jobs=1,
                                    verbose=-1, max_depth=self.cfg["depth"], num_leaves=self.cfg["leaves"],
                                    n_estimators=self.cfg["trees"], class_weight=self.cfg["cw"],
                                    min_child_samples=15, **kw)
        self.m.fit(tr[self.cols].astype(float), y)
        return self

    def predict(self, te: pd.DataFrame) -> np.ndarray:
        if self.m is None:
            return np.full(len(te), self.const)
        return self.m.predict_proba(te[self.cols].astype(float))[:, 1]


def inner_folds(tr: pd.DataFrame):
    """uni_lib.select folds: each of the last 4 training origins held out, fitted on rows whose target precedes it."""
    origins = sorted(tr["t"].unique())[-4:]
    f = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o]) for o in origins]
    return [(a, h) for a, h in f if a["q"].nunique() >= 3 and a["y"].nunique() == 2 and len(h)]


def lgbm_select(tr: pd.DataFrame, cols: list[str], mono: bool) -> dict:
    folds = inner_folds(tr)
    if not folds:
        return GRID[0]
    ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
    sc = {}
    for c in GRID:
        ps = np.concatenate([LGBM(c, cols, mono).fit(f).predict(h) for f, h in folds])
        p = np.clip(ps, 1e-6, 1 - 1e-6)
        sc[c["id"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return min(GRID, key=lambda c: (round(sc[c["id"]], 9), c["id"]))


def logit(tr: pd.DataFrame, te: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """LEAD2_FOODINSECURITY LOGIT: train-median imputation, standardization, L2 logistic C=1, no class weights."""
    from sklearn.linear_model import LogisticRegression
    X, Z = tr[cols].astype(float), te[cols].astype(float)
    med = X.median()
    keep = [c for c in cols if pd.notna(med[c])]
    X, Z = X[keep].fillna(med[keep]), Z[keep].fillna(med[keep])
    mu, sd = X.mean(), X.std(ddof=0)
    keep = [c for c in keep if sd[c] > 0]
    if not keep:
        return np.full(len(te), float(tr["y"].mean()))
    X, Z = (X[keep] - mu[keep]) / sd[keep], (Z[keep] - mu[keep]) / sd[keep]
    m = LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=5000).fit(X.to_numpy(), tr["y"].to_numpy(int))
    return m.predict_proba(Z.to_numpy())[:, 1]


# ================================================================================================ scoring
_RP = None


def rp():
    """The frozen R1-R7 implementation (P0H4_LEAD12_REVIEW/runner/reproduce.py rules()), imported unchanged."""
    global _RP
    if _RP is None:
        _RP = load_module("p0h4_reproduce", EXP / "P0H4_LEAD12_REVIEW" / "runner" / "reproduce.py")
        _RP.boot_quarters_original = _RP.boot_quarters
        _RP.boot_quarters = fast_boot_quarters
    return _RP


def fast_boot_quarters(g: pd.DataFrame, stat) -> list[float]:
    """Exact replacement for reproduce.boot_quarters for statistics that are a mean over rows (all of rules()'s are):
    the same generator, quarter order and draws; the mean of the concatenated quarters is computed from per-quarter
    means weighted by row counts instead of pd.concat. Checked against the original by run_hr.check_fast_boot."""
    R = _RP
    qv = g["q"].unique()
    by = {q: h for q, h in g.groupby("q")}
    m = np.array([stat(by[q]) for q in qv])
    n = np.array([len(by[q]) for q in qv], float)
    full = stat(g)
    assert abs(full - float((m * n).sum() / n.sum())) < 1e-12, "statistic is not a row mean"
    s = m * n
    rng = np.random.default_rng(R.SEED)
    pos = {x: i for i, x in enumerate(qv)}
    out = []
    for _ in range(R.B):
        pick = np.array([pos[x] for x in rng.choice(qv, len(qv))])
        out.append(float(s[pick].sum() / n[pick].sum()))
    return out


def boot_mean(q: np.ndarray, v: np.ndarray, R) -> np.ndarray:
    """R.boot_quarters for a per-row mean, vectorized: the same generator (seed R.SEED), the same quarter order
    (order of first appearance, as pandas unique) and the same R.B draws of rng.choice(qv, len(qv)); the mean of the
    concatenated rows is sum of the picked quarters' sums over the sum of their row counts."""
    rng = np.random.default_rng(R.SEED)
    qv = pd.unique(q)
    pos = {x: i for i, x in enumerate(qv)}
    qi_ = np.array([pos[x] for x in q])
    s, n = np.bincount(qi_, weights=v, minlength=len(qv)), np.bincount(qi_, minlength=len(qv)).astype(float)
    out = np.empty(R.B)
    for b in range(R.B):
        pick = np.array([pos[x] for x in rng.choice(qv, len(qv))])
        out[b] = s[pick].sum() / n[pick].sum()
    return out


def _rules_no_high(h: pd.DataFrame, R) -> dict:
    s = R.cm(h["y"].to_numpy(int), h[R.P].to_numpy(float))
    acc = lambda x: float(((x[R.P] >= .5).astype(int) == x["y"]).mean())  # noqa: E731
    base = {b: float(((h[c] >= .5).astype(int) == h["y"]).mean()) for b, c in (("ALWAYS-LOW", "ALWAYS-LOW_p"),
                                                                              ("PERSIST-SI", "PERSIST-SI_p"))}
    r5 = []
    for c in ("PERSIST-SI_p", "CLIM_p"):
        diff = float(np.mean((h[R.P] - h["y"]) ** 2 - (h[c] - h["y"]) ** 2))
        bs = R.boot_quarters(h, lambda x, c=c: float(np.mean((x[R.P] - x["y"]) ** 2 - (x[c] - x["y"]) ** 2)))
        r5.append(diff < 0 and float(np.mean(np.asarray(bs) >= 0)) < .10)
    qsorted = sorted(h["q"].unique())
    thirds = [list(x) for x in np.array_split(np.array(qsorted), 3)]
    loqo = min(acc(h[h["q"] != q]) for q in qsorted)
    out = {"R1 >=10 quarters and >=40 rows": (len(qsorted) >= 10 and len(h) >= 40, f"{len(qsorted)} q, {len(h)} rows"),
           "R2 accuracy >= 0.75": (s["accuracy"] >= .75, round(s["accuracy"], 4)),
           "R3 balanced accuracy >= 0.70": (s["balanced"] >= .70, round(s["balanced"], 4)),
           "R4 accuracy > always-LOW and > PERSIST-SI": (s["accuracy"] > base["ALWAYS-LOW"] and
                                                       s["accuracy"] > base["PERSIST-SI"], str(base)),
           "R5 Brier < PERSIST-SI and < CLIM, one-sided cluster p < 0.10": (all(r5), str(r5)),
           "R6 precision >= 0.60 and recall >= 0.60": (False, "never HIGH: precision undefined"),
           "R7 each third >= 0.60 and leave-one-quarter-out min >= 0.70": (
               min(acc(h[h["q"].isin(x)]) for x in thirds) >= .6 and loqo >= .7, f"LOQO min {loqo:.3f}")}
    return {k: {"pass": bool(v[0]), "value": v[1], "restated": True} for k, v in out.items()}


def evaluate(g: pd.DataFrame, col: str) -> dict:
    """R1-R7 via rules() (forecast placed in its column P0H4_p3), metrics, and the PLAN section 6 Brier criterion."""
    R = rp()
    h = g.copy()
    h[R.P] = h[col].astype(float)
    h["target"] = h["q"].map(qs)
    p, y = h[R.P].to_numpy(float), h["y"].to_numpy(int)
    const = bool(np.ptp(p) == 0)
    if const:                                       # AUC undefined for a constant forecast (PLAN 7)
        s = R.cm(y, p)
        s.update({"quarters": int(h["q"].nunique()), "auc": None, "brier": float(np.mean((p - y) ** 2))})
    else:
        s = R.scores(h)
    try:
        rules = R.rules(h)
    except TypeError:
        # rules() formats precision with :.3f, which fails when the forecast never says HIGH (precision undefined).
        # Same thresholds restated for that case only; R6 fails by definition (no precision), flagged in the output.
        rules = _rules_no_high(h, R)
    rules = {k: v for k, v in rules.items()}
    bc = {}
    for b, c in (("ALWAYS-HIGH", "ALWAYS-HIGH_p"), ("persistence", "PERSIST-SI_p")):
        dv = ((h[R.P] - h["y"]) ** 2 - (h[c] - h["y"]) ** 2).to_numpy(float)
        diff = float(np.mean(dv))
        bc[b] = {"brierDiff": diff, "p_one_sided": float(np.mean(boot_mean(h["q"].to_numpy(), dv, R) >= 0)),
                 "lower": diff < 0}
    allr = all(v["pass"] for v in rules.values())
    return {"metrics": s, "rules": rules, "brierVs": bc, "allR1R7": allr,
            "reliable": bool(allr and all(v["lower"] for v in bc.values()))}

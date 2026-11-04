"""
E147 inputs as of an issue date. Reads no 2021 label.

Release rules: PSA poverty and subsistence rounds usable 2 calendar years after the survey year (E137 rule); production quarters by
the E137 publication rule; SWS by its published date; national series by FI5 release rules; NASA soil with a 2-month delay; news
by publication date.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

import numpy as np
import pandas as pd

from app.e137 import features as F
from app.e141 import panel as P
from app.e144 import data as D
from app.e144 import link as L
from app.e146 import soil as S
from app.e147 import RAW
from app.paths import BACKEND_DIR

R137 = BACKEND_DIR / "data" / "e137" / "raw"
R138 = BACKEND_DIR / "data" / "e138" / "raw"
R139 = BACKEND_DIR / "data" / "e139" / "raw"
GOV = ["m_food_cpi_yoy", "m_rice_cpi_yoy", "m_food_threshold_rel", "c_soil_anom_3m", "c_rain_anom_6m", "c_tc_4q", "c_agri_yoy", "c_fish_yoy", "oni",
       "unemp_rate", "unemp_yoy", "remit_yoy", "p_poverty", "p_subsistence", "p_poverty_gap", "p_density"]
HIST = ["y_prev", "gap_q", "rtm", "rc2011", "d_sws", "sws_last"]
PSA = ["p_poverty", "p_subsistence", "p_poverty_gap"]
GROUPS = {"market": GOV[:3], "climate": GOV[3:9], "employment": GOV[9:11], "remittance": GOV[11:12], "poverty": GOV[12:]}
THRESHOLD = 60.0
LT = float(np.log(0.6 / 0.4))


def _logit(p):
    p = np.clip(np.asarray(p, float) / 100, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


@lru_cache(maxsize=None)
def _fy(path: str, pat: str) -> pd.DataFrame:
    d = pd.read_csv(path, encoding="utf-8-sig")
    d = d[d["Geolocation"].notna()].copy()
    d["k"] = d["Geolocation"].map(F.nospace)
    cols = {int(re.search(r"(20\d\d)", c).group(1)): c for c in d.columns if re.search(pat, c) and re.search(r"20\d\d", c) and "Coefficient" not in c and "Standard" not in c}
    return d.drop_duplicates("k").set_index("k")[list(cols.values())].rename(columns={v: k for k, v in cols.items()}).apply(pd.to_numeric, errors="coerce")


@lru_cache(maxsize=None)
def _quarterly_late(name: str) -> pd.DataFrame:
    """Province x quarter production 2020 onward; the E141 file ends in 2019."""
    file, col, labs = {"agri": ("palay_corn_q_2020_2023.csv", "Ecosystem/Croptype", ("Palay", "Corn")), "fish": ("fisheries_q_2020_2023.csv", "Subsector", ("FISHERIES",))}[name]
    d = pd.read_csv(R137 / "y2023" / "psa" / file, encoding="utf-8-sig")
    d = d[d[col].isin(labs)].copy()
    d["k"] = d["Geolocation"].map(F.nospace)
    qc = [c for c in d.columns if re.match(r"^\d{4} Quarter \d$", c)]
    d[qc] = d[qc].apply(pd.to_numeric, errors="coerce")
    return d.groupby("k")[qc].sum(min_count=1)


@lru_cache(maxsize=None)
def _rain_late() -> dict:
    out = {}
    for f in (R137 / "y2023" / "nasa").glob("power_*.json"):
        k = F.nospace(f.stem.replace("power_", ""))
        k = (F.GEO_ALIAS.get(k, k) or "").replace(" ", "")
        v = json.loads(f.read_text())["properties"]["parameter"]["PRECTOTCORR"]
        s = pd.Series({pd.Period(f"{x[:4]}-{x[4:]}", "M"): val for x, val in v.items() if x[4:] != "13"}, dtype=float)
        out[k] = s.where(s > -900)
    return out


def gov_row(k: str, d: pd.Timestamp) -> dict:
    P._use_long_history()
    r = F.row_features(k, d, None)
    out = {c: r.get(c, np.nan) for c in GOV}
    pov = _fy(str(R137 / "y2023" / "psa" / "poverty_pop_2018_2023.csv"), r"Poverty Incidence")
    gap = _fy(str(R137 / "y2023" / "psa" / "poverty_gap_2018_2023.csv"), r"Estimate|Poverty Gap")
    sub = _fy(str(R138 / "psa" / "subsistence_families_2018_2023.csv"), r"Subsistence Incidence")
    thr = _fy(str(R138 / "psa" / "subsistence_families_2018_2023.csv"), r"Food\s+Threshold")
    for y in (2018, 2021, 2023):
        if d >= pd.Timestamp(year=y + 2, month=1, day=1):
            if k in pov.index and y in pov.columns and pd.notna(pov.at[k, y]):
                out["p_poverty"] = float(_logit(pov.at[k, y]))
            if k in sub.index and y in sub.columns and pd.notna(sub.at[k, y]):
                out["p_subsistence"] = float(_logit(sub.at[k, y]))
            if k in gap.index and y in gap.columns and pd.notna(gap.at[k, y]):
                out["p_poverty_gap"] = float(gap.at[k, y])
            if k in thr.index and y in thr.columns and pd.notna(thr.at[k, y]) and "philippines" in thr.index:
                out["m_food_threshold_rel"] = float(np.log(thr.at[k, y] / thr.at["philippines", y]))
    if d >= pd.Timestamp("2020-07-01"):
        for name, fname, col, labs in (("agri", "palay_corn_quarterly.csv", "Ecosystem/Croptype", ("Palay", "Corn")), ("fish", "fisheries_quarterly.csv", "Subsector", ("FISHERIES",))):
            q0, q1 = F._quarterly(fname, col, labs), _quarterly_late(name)
            pub = F._published_quarters(list(q0.columns) + list(q1.columns), d)
            def get(c):
                t = q0 if c in q0.columns else q1
                return t.at[k, c] if k in t.index else np.nan
            if len(pub) >= 8:
                last, prev = np.nansum([get(c) for c in pub[-4:]]), np.nansum([get(c) for c in pub[-8:-4]])
                out[f"c_{name}_yoy"] = float(np.log(last / prev)) if last > 0 and prev > 0 else np.nan
    if pd.isna(out["c_rain_anom_6m"]):
        rain = _rain_late().get(k)
        if rain is not None:
            last_month = (d - pd.Timedelta(days=30)).to_period("M") - 1
            months = pd.period_range(last_month - 5, last_month, freq="M")
            if all(m in rain.index for m in months):
                clim = [rain.reindex([pd.Period(year=y, month=m.month, freq="M") for m in months]).mean() for y in range(2000, 2010)]
                out["c_rain_anom_6m"] = float((rain[months].mean() - np.mean(clim)) / np.std(clim, ddof=1))
    out["c_soil_anom_3m"] = S.anomaly(k, d)
    out.update({c: D.national(d).get(c, np.nan) for c in ("oni", "unemp_rate", "unemp_yoy", "remit_yoy")})
    return out


@lru_cache(maxsize=None)
def radimer_2011() -> dict:
    d = pd.read_csv(RAW / "dev_labels_2011_2019.csv")
    d = d[(d["actual_year"].astype(str) == "2011") & (d["fs_survey_category"] == "Food Insecure Households")].drop_duplicates("key")
    return dict(zip(d["key"], _logit(d["pct"])))


def base_rows() -> pd.DataFrame:
    o = P.outcomes("insecure")[["key", "province", "region", "sws_area", "island", "survey", "year", "ref_quarter", "p", "se_p"]].copy()
    o["y"] = _logit(o["p"])
    pp = o["p"] / 100
    o["se_y"] = (o["se_p"] / 100) / (pp * (1 - pp))
    o["q_high"] = _class_prob(o["y"], o["se_y"])
    return o


def _class_prob(y, se):
    from scipy.stats import norm
    return norm.cdf((np.asarray(y, float) - LT) / np.asarray(se, float))


def frame(targets: pd.DataFrame, history: pd.DataFrame, lead: int, issue_of=None) -> pd.DataFrame:
    """Inputs for `targets` (key, region, sws_area, year, ref_quarter); `history` holds only rounds usable as past values."""
    rows = []
    for _, t in targets.iterrows():
        d = issue_of(t) if issue_of else F.issue_date(int(t["year"]), lead)
        h = history[history["year"] < int(t["year"])]
        own = h[h["key"] == t["key"]].sort_values("year")
        row = {"key": t["key"], "survey": t["survey"], "issue": d}
        if len(own):
            last = own.iloc[-1]
            row.update(y_prev=float(last["y"]), se_prev=float(last["se_y"]), prev_year=int(last["year"]), gap_q=(int(t["year"]) - int(last["year"])) * 4)
            latest = h[h["region"] == t["region"]].sort_values("year").groupby("key").tail(1)
            row["rtm"] = float(last["y"] - latest["y"].mean())
            hp = L._area_hunger(t["sws_area"], last["ref_quarter"])
        else:
            row.update(y_prev=np.nan, se_prev=np.nan, prev_year=np.nan, gap_q=np.nan, rtm=np.nan)
            hp = np.nan
        s = D.sws_quarterly()
        s = s[(s["area"] == t["sws_area"]) & (s["published"] < d)].sort_values("qi")
        row["sws_last"] = float(_logit(s["hunger"].iloc[-1])) if len(s) else np.nan
        row["d_sws"] = row["sws_last"] - float(_logit(hp)) if hp == hp and len(s) else np.nan
        row["rc2011"] = radimer_2011().get(t["key"], np.nan)
        row.update(gov_row(t["key"].replace(" ", ""), d))
        rows.append(row)
    return pd.DataFrame(rows)

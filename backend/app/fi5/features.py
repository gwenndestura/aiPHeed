"""As-of five-domain feature rows.

A row is built for an issue date d (the last day of issue quarter t) and a target quarter T = t + lead. Every value
comes from a series row whose available_from <= d, and every standardisation (rainfall climatology, news z-scores)
uses only earlier values, so the same code serves the walk-forward evaluation and the live forecast.

Blocks (the outcome block is the target's own last reading; the five explanatory domains hold government
indicators and the news signals that describe the same domain):

    outcome     hunger_last, hunger_last_anom, hunger_age_q
    market      cpi_food_yoy, cpi_rice_yoy, cpi_food_rel, cpi_food_accel, palay_yoy | gdelt_shortage,
                gdelt_agri_supply, fssi_market, topic_market
    climate     rain_anom_3m, tmax_anom_3m, tc_exposure_q, tc_exposure_4q, oni | fssi_climate, topic_climate
    employment  unemp_rate, unemp_yoy | gdelt_jobs_income, fssi_employment, topic_employment
    remittance  remit_yoy | fssi_remittance, topic_remittance
    poverty     poverty_inc | gdelt_assistance, fssi_poverty, topic_poverty, hunger_news_share
"""
from __future__ import annotations

from functools import cached_property

import numpy as np
import pandas as pd

from app.fi5 import sources as S
from app.fi5.nlp import DOMAINS, FSSI
from app.fi5.target import AREA, BASELINE_Q, MIN_BASELINE_OBS, q_end, qindex, quarterly

OUTCOME = ["hunger_last", "hunger_last_anom", "hunger_age_q"]
GOV = ["cpi_food_yoy", "cpi_rice_yoy", "cpi_food_rel", "cpi_food_accel", "palay_yoy",
       "rain_anom_3m", "tmax_anom_3m", "tc_exposure_q", "tc_exposure_4q", "oni",
       "unemp_rate", "unemp_yoy", "remit_yoy", "poverty_inc"]
NEWS = ["gdelt_shortage", "gdelt_agri_supply", "gdelt_jobs_income", "gdelt_assistance",
        *[f"fssi_{d}" for d in DOMAINS], *[f"topic_{d}" for d in DOMAINS], "hunger_news_share"]
ALL = OUTCOME + GOV + NEWS
FEATURE_SETS = {
    "full": ALL,                       # proposed LightGBM: outcome history + five domains (government + news)
    "full_no_news": OUTCOME + GOV,     # ablation: does news add anything?
    "psa_only": GOV,                   # baseline 2: structured government indicators only
    "nlp_only": NEWS,                  # baseline 3: FSSI / BERTopic / GDELT news features only
}
MIN_Z_HISTORY = 4


def domain_of(feature: str) -> str:
    return S.REG[feature].domain


def kind_of(feature: str) -> str:
    return S.REG[feature].kind


def _asof(df: pd.DataFrame, d: pd.Timestamp) -> pd.DataFrame:
    return df[df["available_from"] <= d]


def _z_last(x: pd.Series) -> float:
    """z-score of the last value against all earlier values (NaN with fewer than 4 earlier values)."""
    x = x.dropna()
    if len(x) < MIN_Z_HISTORY + 1:
        return np.nan
    hist, last = x.iloc[:-1], x.iloc[-1]
    sd = hist.std(ddof=1)
    return float((last - hist.mean()) / sd) if sd > 0 else 0.0


class FeatureBuilder:
    def __init__(self, area: str = AREA, use_corpus: bool = True):
        self.area = area
        self.use_corpus = use_corpus

    # ------------------------------------------------------------------ cached series
    @cached_property
    def sws(self):
        return quarterly(self.area)

    @cached_property
    def cpi(self):
        return S.cpi()

    @cached_property
    def palay(self):
        return S.palay()

    @cached_property
    def lfs(self):
        return S.lfs()

    @cached_property
    def nasa(self):
        return S.nasa()

    @cached_property
    def tc(self):
        return S.typhoons()

    @cached_property
    def oni(self):
        return S.oni()

    @cached_property
    def gdelt(self):
        return S.gdelt()

    @cached_property
    def remit(self):
        return S.remittances()

    @cached_property
    def poverty(self):
        return S.poverty()

    @cached_property
    def fssi(self) -> pd.DataFrame:
        if not self.use_corpus or not FSSI.exists():
            return pd.DataFrame(columns=["period_end"])
        f = pd.read_csv(FSSI)
        f = f[f["geo"] == "CALABARZON"].copy()
        f["period_end"] = [q_end(qindex(q)) for q in f["quarter"]]
        f["available_from"] = f["period_end"]
        keep = {f"fssi_{d}": f"fssi_{d}" for d in DOMAINS} | {f"topic_share_{d}": f"topic_{d}" for d in DOMAINS} | \
               {"hunger_report_share": "hunger_news_share"}
        return f.rename(columns=keep)[["period_end", "available_from", *keep.values()]].sort_values("period_end")

    # ------------------------------------------------------------------ one row
    def row(self, issue_qi: int, target_qi: int, issue_date: pd.Timestamp | None = None) -> dict:
        """issue_date defaults to the last day of the issue quarter; FI7 passes an earlier date inside the quarter
        (release-aware operational issue), in which case quarterly news/GDELT come from the last complete quarter."""
        d = q_end(issue_qi) if issue_date is None else pd.Timestamp(issue_date)
        q_ref = q_end(issue_qi) if d >= q_end(issue_qi) else q_end(issue_qi - 1)
        r: dict = {"issue_quarter": f"{issue_qi // 4}-Q{issue_qi % 4 + 1}", "issue_date": d.date().isoformat(),
                   "target_quarter": f"{target_qi // 4}-Q{target_qi % 4 + 1}", "lead": target_qi - issue_qi}
        # outcome block -------------------------------------------------------------
        sws = self.sws[self.sws["published"] <= d]
        if len(sws):
            last = sws.iloc[-1]
            win = sws[(sws["qi"] >= target_qi - BASELINE_Q) & (sws["qi"] < target_qi)]["hunger"]
            base = win.mean() if len(win) >= MIN_BASELINE_OBS else np.nan
            r.update(hunger_last=float(last["hunger"]), hunger_last_anom=float(last["hunger"] - base),
                     hunger_age_q=int(target_qi - last["qi"]), baseline_known=float(base),
                     last_reading_quarter=last["quarter"])
        # market -----------------------------------------------------------------------
        c = _asof(self.cpi, d).dropna(subset=["yoy_food"])
        if len(c):
            r.update(cpi_food_yoy=c["yoy_food"].iloc[-1], cpi_rice_yoy=c["yoy_rice"].iloc[-1],
                     cpi_food_rel=c["yoy_food"].iloc[-1] - c["yoy_all"].iloc[-1],
                     cpi_food_accel=(c["yoy_food"].iloc[-1] - c["yoy_food"].iloc[-4]) if len(c) >= 4 else np.nan)
        p = _asof(self.palay, d)
        if len(p):
            r["palay_yoy"] = p["yoy_palay"].iloc[-1]
        # climate ----------------------------------------------------------------------
        n = _asof(self.nasa, d)
        if len(n) >= 3 * 12:
            n = n.reset_index(drop=True)
            last3 = n.iloc[-3:]
            hist_p, hist_t = [], []
            for pos in n.index[(n["month"] == last3["month"].iloc[-1])][:-1]:
                if pos >= 2:                      # the same three calendar months in an earlier year
                    w = n.iloc[pos - 2:pos + 1]
                    hist_p.append(w["precip"].mean())
                    hist_t.append(w["tmax"].mean())
            if len(hist_p) >= 10:
                cur_p, cur_t = last3["precip"].mean(), last3["tmax"].mean()
                r["rain_anom_3m"] = float((cur_p - np.mean(hist_p)) / np.std(hist_p, ddof=1))
                r["tmax_anom_3m"] = float(cur_t - np.mean(hist_t))
        tc = self.tc[self.tc["t"] <= d]
        r["tc_exposure_q"] = int((tc["period_end"] == q_end(issue_qi)).sum())
        r["tc_exposure_4q"] = int((tc["t"] > d - pd.DateOffset(years=1)).sum())
        o = _asof(self.oni, d)
        if len(o):
            r["oni"] = o["oni"].iloc[-1]
        # employment -------------------------------------------------------------------
        e = _asof(self.lfs, d)
        if len(e):
            r["unemp_rate"], r["unemp_yoy"] = e["unemp_rate"].iloc[-1], e["unemp_yoy"].iloc[-1]
        # remittances ------------------------------------------------------------------
        m = _asof(self.remit, d)
        if len(m):
            r["remit_yoy"] = m["remit_yoy"].iloc[-1]
        # poverty ----------------------------------------------------------------------
        v = _asof(self.poverty, d)
        if len(v):
            r["poverty_inc"] = v["poverty_inc"].iloc[-1]
        # news inside the domains (z vs the series' own earlier quarters) ---------------
        g = _asof(self.gdelt, d)
        if len(g) and g["period_end"].iloc[-1] == q_ref:
            for k in ["gdelt_shortage", "gdelt_agri_supply", "gdelt_jobs_income", "gdelt_assistance"]:
                r[k] = _z_last(g[k])
        f = _asof(self.fssi, d) if len(self.fssi) else self.fssi
        if len(f) and f["period_end"].iloc[-1] == q_ref:
            for k in [f"fssi_{x}" for x in DOMAINS] + [f"topic_{x}" for x in DOMAINS] + ["hunger_news_share"]:
                r[k] = _z_last(f[k])
        return r

    def matrix(self, lead: int, first_issue_qi: int, last_issue_qi: int, with_labels: pd.DataFrame | None = None):
        rows = [self.row(t, t + lead) for t in range(first_issue_qi, last_issue_qi + 1)]
        X = pd.DataFrame(rows)
        for c in ALL:
            if c not in X:
                X[c] = np.nan
        if with_labels is not None:
            lab = with_labels.set_index("quarter")
            X["y"] = X["target_quarter"].map(lab["y"])
            X["hunger_target"] = X["target_quarter"].map(lab["hunger"])
        return X

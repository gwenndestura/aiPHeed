"""FI7 design rows: one row per (issue date, target quarter), every value as known at the issue date.

timing = "quarter_end"   issue on the last day of quarter t (the FI5/FI6 protocol); lead L targets t + L
timing = "operational"   issue on the last day of the 2nd month of quarter c (release-aware: by then the previous
                         quarter's SWS reading has normally been published); h targets c + h (h = 1: next quarter)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.fi5.features import FeatureBuilder
from app.fi5.target import q_end, qindex, qlabel
from app.fi6.features import NEWS_PARTS
from app.fi6.news_model import NEWSA, asof_news
from app.fi6.target import labels, quarterly
from app.fi7 import extra_sources as X
from app.fi7 import news_windows as NW

FIRST_ISSUE = "1999-Q1"
MIN_Z_HISTORY = 8
WINDOW_COLS = {f"w_{d}": f"risk_share_{d}" for d in ["market", "climate", "employment", "remittance", "poverty"]} | \
              {"w_climate_damage": "climate_damage_log", "w_displaced": "displaced_families_log"}
EW_COLS = {f"ew_esc_{d}": f"escalation_{d}" for d in ["market", "climate", "employment", "remittance", "poverty"]} | \
          {f"ew_per_{d}": f"persistence_{d}" for d in ["market", "climate", "employment", "remittance", "poverty"]}


def issue_date(qi: int, timing: str) -> pd.Timestamp:
    if timing == "quarter_end":
        return q_end(qi)
    start = pd.Timestamp(year=qi // 4, month=3 * (qi % 4) + 1, day=1)
    return start + pd.DateOffset(months=2) - pd.Timedelta(days=1)      # last day of the quarter's 2nd month


def _expanding_z(s: pd.Series) -> pd.Series:
    out = []
    for i in range(len(s)):
        h = s.iloc[:i].dropna()
        if pd.isna(s.iloc[i]) or len(h) < MIN_Z_HISTORY:
            out.append(np.nan)
            continue
        sd = h.std(ddof=1)
        out.append(float((s.iloc[i] - h.mean()) / sd) if sd > 0 else 0.0)
    return pd.Series(out, index=s.index)


class Designer:
    def __init__(self, timing: str, as_of: pd.Timestamp | None = None):
        """as_of: the live date. If the current quarter's scheduled issue date is later, the live date replaces it so
        that only data published by today are used (the forecast is refreshed on the scheduled date)."""
        self.timing = timing
        self.fb = FeatureBuilder()
        self.lab = labels()
        self.q = quarterly()
        self.extra = X.load_cache()
        live = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today()
        last_qi = max(qindex("2026-Q4"), live.year * 4 + (live.month - 1) // 3)     # never a hardcoded final quarter
        self.issue_qis = list(range(qindex(FIRST_ISSUE), last_qi + 1))
        self.dates = {qi: issue_date(qi, timing) for qi in self.issue_qis}
        if as_of is not None:
            as_of = pd.Timestamp(as_of).normalize()
            self.issue_qis = [qi for qi in self.issue_qis if q_end(qi - 1) < as_of]
            last = self.issue_qis[-1]
            self.dates = {qi: self.dates[qi] for qi in self.issue_qis}
            if self.dates[last] > as_of:
                self.dates[last] = as_of
        news_q = asof_news().set_index("issue_quarter")
        self.news_q = news_q
        nw = NW.OUT
        win = pd.read_csv(nw) if nw.exists() else NW.build(list(self.dates.values()))
        win["issue_date"] = pd.to_datetime(win["issue_date"])
        want = set(pd.to_datetime(list(self.dates.values())))
        if not want <= set(win["issue_date"]):
            win = NW.build(sorted(want | set(win["issue_date"])))
            win["issue_date"] = pd.to_datetime(win["issue_date"])
        win = win[win["issue_date"].isin(want)].sort_values("issue_date").reset_index(drop=True)
        z = pd.DataFrame({"issue_date": win["issue_date"]})
        for k, c in {**WINDOW_COLS, **EW_COLS}.items():
            z[k] = _expanding_z(win[c].astype(float)) if k.startswith("w_") else win[c].astype(float)
        self.win = z.set_index("issue_date")

    def row(self, issue_qi: int, target_qi: int) -> dict:
        d = self.dates[issue_qi]
        r = self.fb.row(issue_qi, target_qi, issue_date=d)
        r["issue_quarter"], r["issue_date"] = qlabel(issue_qi), d.date().isoformat()
        r["lead"] = target_qi - issue_qi
        for k, parts in NEWS_PARTS.items():
            vals = [r.get(p) for p in parts if pd.notna(r.get(p, np.nan))]
            r[k] = float(np.mean(vals)) if vals else np.nan
        r.update(X.asof_extra(d, pd.Timestamp(year=issue_qi // 4, month=3 * (issue_qi % 4) + 1, day=1), self.extra))
        ref_q = qlabel(issue_qi) if d >= q_end(issue_qi) else qlabel(issue_qi - 1)      # last complete news quarter
        for c in NEWSA:
            r[c] = float(self.news_q.loc[ref_q, c]) if ref_q in self.news_q.index and pd.notna(self.news_q.loc[ref_q, c]) else np.nan
        if d in self.win.index:
            r.update(self.win.loc[d].to_dict())
        pub = self.q[self.q["published"] <= d]
        r["moe_last"] = float(pub["moe"].iloc[-1]) if len(pub) else np.nan
        r["threshold_known"] = r.get("baseline_known", np.nan) + r["moe_last"]
        return r

    def frame(self, lead: int) -> pd.DataFrame:
        last_target = int(self.lab["qi"].max())
        rows = [self.row(t, t + lead) for t in self.issue_qis if t + lead <= last_target]
        X_ = pd.DataFrame(rows)
        L = self.lab.set_index("quarter")
        X_["tqi"] = X_["target_quarter"].map(qindex)
        X_["issue_ts"] = pd.to_datetime(X_["issue_date"])
        for c, src in [("y", "y"), ("hunger_target", "hunger"), ("p_flip", "p_flip"), ("target_published", "published")]:
            X_[c] = X_["target_quarter"].map(L[src])
        X_["delta_target"] = X_["hunger_target"] - X_["hunger_last"]
        return X_

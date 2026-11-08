"""
E148 rows and models. A training row = one measured outcome at one lead, with inputs as of that lead's issue date.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e137 import model as M137
from app.e140 import model as M140
from app.e144 import OUT as O144
from app.e144 import data as D
from app.e144 import link as L
from app.e147 import features as Fe
from app.e148 import OUT
from app.e148 import panel as Pn
from app.fi5.target import qindex

RQ = {"NNS2013": qindex("2013-Q3"), "FNRI2015": qindex("2015-Q3"), "ENNS2018": qindex("2018-Q3"), "ENNS2019": qindex("2019-Q3"), "ENNS2021": qindex("2021-Q3")}
NOW = [c for c in Fe.GOV] + ["remit_q_yoy", "unemp_region"]
SINCE = ["soil_since", "rain_since", "tc_rate_since", "agri_since", "unemp_chg_since", "remit_since"]
HIST = ["y_anchor", "gap_q", "rtm", "rc2011", "lead"]
SWS = ["sws_last", "d_sws", "sws_fc"]
NEWS_EXTRA = ["fssi_since", "fssi_chg"]
NEWS = ["nb_fssi", "nb_attention"] + [f"nb_topic_{i}" for i in range(6)] + NEWS_EXTRA
RAWN = ["nr_volume", "nr_count", "nr_mean"]
SETS = {"Q-G": HIST + NOW + SINCE + SWS, "Q-noSWS": HIST + NOW + SINCE, "Q-GN": HIST + NOW + SINCE + SWS + RAWN, "Q-GNB": HIST + NOW + SINCE + SWS + NEWS, "Q-frozen": HIST + NOW + SINCE + SWS}


class Store:
    def __init__(self):
        self.gov = pd.read_parquet(OUT / "gov_panel.parquet").set_index(["key", "qi"]).sort_index()
        self.news = pd.read_parquet(OUT / "news_panel.parquet").set_index(["origin", "key", "qi"]).sort_index()
        a = pd.read_csv(O144 / "stage_a_oof.csv")
        self.stage = a.set_index(["area", "issue_qi", "h"])["level_logit"].to_dict()
        self.sws = D.sws_quarterly()
        self.base = Fe.base_rows()

    def anchor(self, key, region, T, i, lag, extra=None):
        h = pd.concat([self.base, extra]) if extra is not None else self.base
        h = h.assign(rq=h["survey"].map(RQ))
        h = h[(h["rq"] < T) & (h["rq"] + lag <= i)]
        own = h[h["key"] == key].sort_values("rq")
        if own.empty:
            return None
        latest = h[h["region"] == region].sort_values("rq").groupby("key").tail(1)
        last = own.iloc[-1]
        return {"y_anchor": float(last["y"]), "se_anchor": float(last["se_y"]), "rq_anchor": int(last["rq"]), "gap_q": int(T - last["rq"]), "rtm": float(last["y"] - latest["y"].mean()), "ref_anchor": last["ref_quarter"]}


def _mean(g, col, a, b):
    v = [g.at[q, col] for q in range(a + 1, b + 1) if q in g.index]
    v = [x for x in v if x == x]
    return float(np.mean(v)) if v else np.nan


def row(S: Store, t: dict, lead: int, origin: str, lag=Pn.ANCHOR_LAG, extra=None, frozen=False) -> dict | None:
    """Inputs for target quarter T at this lead; issue quarter i = T - lead. frozen: quarterly inputs held at the anchor's release quarter."""
    T, key = int(t["T"]), t["key"]
    i = T - lead
    A = S.anchor(key, t["region"], T, i, lag, extra)
    if A is None or key not in S.gov.index.get_level_values(0):
        return None
    g = S.gov.loc[key]
    use = A["rq_anchor"] + lag if frozen else i
    if use not in g.index:
        return None
    r = {"key": key, "T": T, "lead": lead, "i": i, **A}
    for c in NOW:
        r[c] = float(g.at[use, c])
    a0 = A["rq_anchor"]
    r["soil_since"], r["rain_since"], r["agri_since"], r["remit_since"] = _mean(g, "c_soil_anom_3m", a0, use), _mean(g, "c_rain_anom_6m", a0, use), _mean(g, "c_agri_yoy", a0, use), _mean(g, "remit_yoy", a0, use)
    r["tc_rate_since"] = _mean(g, "c_tc_4q", a0, use)
    r["unemp_chg_since"] = float(g.at[use, "unemp_rate"] - g.at[a0, "unemp_rate"]) if a0 in g.index else np.nan
    r["rc2011"] = Fe.radimer_2011().get(key, np.nan)
    d = Pn.q_start(use)
    s = S.sws[(S.sws["area"] == t["sws_area"]) & (S.sws["published"] < d)].sort_values("qi")
    r["sws_last"] = float(Fe._logit(s["hunger"].iloc[-1])) if len(s) else np.nan
    hp = L._area_hunger(t["sws_area"], A["ref_anchor"])
    r["d_sws"] = r["sws_last"] - float(Fe._logit(hp)) if hp == hp and len(s) else np.nan
    r["sws_fc"] = S.stage.get((t["sws_area"], i - 1, lead), np.nan) if not frozen else np.nan
    nk = (origin, key, use)
    if nk in S.news.index:
        n = S.news.loc[nk]
        for c in ["nb_fssi", "nb_attention"] + [f"nb_topic_{j}" for j in range(6)] + RAWN:
            r[c] = float(n[c])
        vals = [S.news.at[(origin, key, q), "nb_fssi"] for q in range(a0 + 1, use + 1) if (origin, key, q) in S.news.index]
        vals = [v for v in vals if v == v]
        r["fssi_since"] = float(np.mean(vals)) if vals else np.nan
        pk = (origin, key, a0)
        r["fssi_chg"] = float(n["nb_fssi"] - S.news.at[pk, "nb_fssi"]) if pk in S.news.index else np.nan
    else:
        for c in NEWS + RAWN:
            r[c] = np.nan
    return r


def rows_for(S, targets: pd.DataFrame, leads, origin, **kw) -> pd.DataFrame:
    out = []
    for _, t in targets.iterrows():
        for h in leads:
            r = row(S, t, h, origin, **kw)
            if r is not None:
                r.update({"survey": t["survey"], "province": t["province"], "region": t["region"], "island": t["island"], "sws_area": t["sws_area"]})
                if "y" in t:
                    r.update({"y_true": t["y"], "se_true": t["se_y"], "q_true": t["q_high"], "p_true": t["p"]})
                out.append(r)
    return pd.DataFrame(out)


def targets(S, surveys):
    b = S.base[S.base["survey"].isin(surveys)].copy()
    b["T"] = b["survey"].map(RQ)
    return b


class QModel:
    """LightGBM on change from the anchor, pooled across leads; sigma per lead from out-of-fold residuals."""

    def __init__(self, cols):
        self.cols = list(cols)

    def fit(self, tr):
        d = tr.reset_index(drop=True).copy()
        d["y"] = d["y_true"] - d["y_anchor"]
        d["se_y"] = np.sqrt(d["se_true"] ** 2 + d["se_anchor"] ** 2)
        d["q"] = norm.cdf(d["y"] / d["se_y"])
        self.use_ = [c for c in self.cols if d[c].notna().any()]
        pred = np.full(len(d), np.nan)
        for a, b in GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]):
            pred[b] = M140.LGBNative("GBC", self.use_).fit(d.iloc[a]).predict_y(d.iloc[b])
        d["res"] = d["y"] - pred
        self.oof_ = d.assign(pred=pred)
        self.sigma_all_ = float(np.sqrt(np.mean(d["res"] ** 2)))
        self.sigma_ = d.groupby("lead")["res"].apply(lambda r: float(np.sqrt(np.mean(r ** 2)))).to_dict()
        self.m_ = M140.LGBNative("GBC", self.use_).fit(d)
        return self

    def mu(self, X):
        return X["y_anchor"].values + self.m_.predict_y(X)

    def sigma(self, X):
        return X["lead"].map(lambda h: self.sigma_.get(h, self.sigma_all_)).values

    def proba(self, X):
        return norm.cdf((self.mu(X) - Fe.LT) / self.sigma(X))


def logit(cols, tr, te):
    use = [c for c in cols if tr[c].notna().any()]
    return M137.SoftLogit(use).fit(tr.assign(q=tr["q_true"])).predict_proba(te)


def predict_all(tr, te, te_frozen=None, arms=None) -> dict:
    out = {}
    for a in [x for x in SETS if (arms is None or x in arms) and x != "Q-frozen"]:
        m = QModel(SETS[a]).fit(tr)
        out[a], out["mu_" + a], out["sigma_" + a] = m.proba(te), m.mu(te), m.sigma(te)
    if te_frozen is not None and (arms is None or "Q-frozen" in arms):
        m = QModel(SETS["Q-G"]).fit(tr)
        idx = te_frozen.set_index(["key", "T", "lead"]).reindex(pd.MultiIndex.from_frame(te[["key", "T", "lead"]])).reset_index()
        ok = idx["y_anchor"].notna().values
        p = np.full(len(te), np.nan)
        p[ok] = m.proba(idx[ok])
        out["Q-frozen"] = p
    if arms is None:
        t2 = tr.assign(y=tr["y_true"], se_y=tr["se_true"], q=tr["q_true"])
        use = [c for c in NEWS if t2[c].notna().any()]
        n = M140.LGBNative("GBC", use).fit(t2)
        out["N"] = norm.cdf((n.predict_y(te) - Fe.LT) / float(np.std(t2["y"].values - n.predict_y(t2))))
        dy = (tr["y_true"] - tr["y_anchor"]).values
        rate = float(np.sum(dy) / np.sum(tr["gap_q"]))
        out["mu_DRIFT"] = te["y_anchor"].values + rate * te["gap_q"].values
        out["DRIFT"] = norm.cdf((out["mu_DRIFT"] - Fe.LT) / float(np.std(dy)))
        out["mu_PERS"] = te["y_anchor"].values
        out["PERS"] = norm.cdf((te["y_anchor"].values - Fe.LT) / float(np.sqrt(np.mean(dy ** 2))))
        f = {c: 0.0 for c in NEWS}
        out["LR-PSA"] = logit(Fe.PSA, tr, te)
        out["LR-NLP"] = logit(NEWS, tr.fillna(f), te.fillna(f))
        out["LR-ALL"] = logit(SETS["Q-GNB"], tr.fillna(f), te.fillna(f))
    return out

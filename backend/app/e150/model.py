"""
E150 models (docs/e150/RISK_SCORE_METHODOLOGY.md).

Approach A, prevalence:  logit(p) = N_T + mu_p + w_p * d_p + loading * h_pT + LightGBM residual
    N_T       shared national level, composition-corrected by two-way fixed effects on released rounds, carried forward by its trend
    mu_p      province structural level from LightGBM, cross-fitted so a province's level comes from a model that never saw its region
    w_p d_p   the province's measured deviation from that level, shrunk by measurement error (Fay-Herriot logic)
    h_pT      quarterly response learned on SWS area-quarters, applied to the province's own inputs (0 if the survey rows give it no support)
    residual  LightGBM on survey-row errors, with theory-signed monotone constraints and a learned option of no residual

Approach B, risk score:  100 x P(p >= 50) from a LightGBM classifier on the five trigger groups, Platt-calibrated on grouped folds. An index of risk, not prevalence.
"""
from __future__ import annotations

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

from app.e137 import model as M137
from app.e140 import model as M140
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e148 import panel as Pn
from app.e150 import OUT
from app.e150.panel import CPI_COLS

warnings.filterwarnings("ignore")
LT = 0.0
LEVEL = ["p_poverty", "p_subsistence", "p_poverty_gap", "p_density", "m_food_threshold_rel", "rc2011"]
GROUPS = {"market": ["cpi_food_yoy", "cpi_rice_yoy", "cpi_food_3m", "cpi_food_accel", "cpi_food_rel_nat", "cpi_since"],
          "climate": ["c_soil_anom_3m", "c_rain_anom_6m", "c_tc_4q", "c_agri_yoy", "c_fish_yoy", "oni", "soil_since", "rain_since", "tc_rate_since", "agri_since"],
          "employment": ["unemp_rate", "unemp_yoy", "unemp_chg_since", "unemp_region"], "remittance": ["remit_yoy", "remit_since", "remit_q_yoy"], "poverty": ["p_poverty", "p_subsistence", "p_poverty_gap", "p_density"]}
RES = [c for g in GROUPS.values() for c in g] + ["h_signal", "gap_q", "lead"]
NEWS = ["fv2_fssi", "fv2_attention", "fv2_named_share", "fv2_market", "fv2_climate", "fv2_employment", "fv2_remittance", "fv2_poverty", "fv2_fssi_chg"] + [f"nb_topic_{i}" for i in range(6)]
SIGN = {"cpi_food_yoy": 1, "cpi_rice_yoy": 1, "cpi_food_3m": 1, "cpi_food_accel": 1, "cpi_since": 1, "c_tc_4q": 1, "tc_rate_since": 1, "c_agri_yoy": -1, "agri_since": -1, "c_fish_yoy": -1, "unemp_rate": 1, "unemp_yoy": 1, "unemp_chg_since": 1, "unemp_region": 1,
        "remit_yoy": -1, "remit_since": -1, "remit_q_yoy": -1, "p_poverty": 1, "p_subsistence": 1, "p_poverty_gap": 1, "h_signal": 1, "fv2_fssi": 1, "fv2_fssi_chg": 1}
PARAMS = dict(objective="regression", num_leaves=4, max_depth=2, min_child_samples=10, learning_rate=0.02, reg_lambda=5.0, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=150, n_jobs=1, verbose=-1)
GRID = [100, 300, 600]


class Store:
    def __init__(self, base: pd.DataFrame | None = None):
        self.s8 = M8.Store()
        if base is not None:
            self.s8.base = base
        self.cpi = pd.read_parquet(OUT / "cpi_panel.parquet").set_index(["key", "qi"]).sort_index()
        h = pd.read_parquet(OUT / "h_signal.parquet")
        self.h = {(k, i, l): v for k, i, l, v in zip(h["key"], h["i"], h["lead"], h["h_signal"])}
        self.hfull = {(k, i, l): v for k, i, l, v in zip(h["key"], h["i"], h["lead"], h["h_full"])}
        p = OUT / "news_v2_panel.parquet"
        self.news = pd.read_parquet(p).set_index(["key", "qi"]).sort_index() if p.exists() else None

    @property
    def base(self):
        return self.s8.base


def _cpi_since(S, key, a0, i):
    v = [S.cpi.at[(key, q), "cpi_food_yoy"] for q in range(a0 + 1, i + 1) if (key, q) in S.cpi.index]
    v = [x for x in v if x == x]
    return float(np.mean(v)) if v else np.nan


def row(S: Store, t: dict, lead: int, origin: str, frozen=False) -> dict | None:
    r = M8.row(S.s8, t, lead, origin, frozen=frozen)
    if r is None:
        return None
    use = r["rq_anchor"] + Pn.ANCHOR_LAG if frozen else r["i"]
    if (t["key"], use) in S.cpi.index:
        c = S.cpi.loc[(t["key"], use)]
        for k in CPI_COLS:
            r[k] = float(c[k])
    else:
        for k in CPI_COLS:
            r[k] = np.nan
    r["cpi_since"] = _cpi_since(S, t["key"], r["rq_anchor"], use)
    r["h_signal"] = 0.0 if frozen else S.h.get((t["key"], r["i"], lead), np.nan)
    r["h_full"] = np.nan if frozen else S.hfull.get((t["key"], r["i"], lead), np.nan)
    if S.news is not None and (t["key"], use) in S.news.index:
        n = S.news.loc[(t["key"], use)]
        for k in NEWS:
            if k in n.index:
                r[k] = float(n[k])
    return r


def rows_for(S, targets, leads, origin, **kw) -> pd.DataFrame:
    out = []
    for _, t in targets.iterrows():
        for h in leads:
            r = row(S, t, h, origin, **kw)
            if r is not None:
                r.update({"survey": t["survey"], "province": t["province"], "region": t["region"], "island": t["island"], "sws_area": t["sws_area"]})
                if "y" in t:
                    r.update({"y_true": t["y"], "se_true": t["se_y"], "q_true": t["q_high"], "p_true": t["p"]})
                out.append(r)
    d = pd.DataFrame(out)
    for c in NEWS:
        if c not in d:
            d[c] = np.nan
    return d


class Hier:
    """Shared level + cross-fitted structural level + measurement-error-shrunk province deviation, from released rounds only."""

    def fit(self, S: Store, rounds: list[str]):
        b = S.base[S.base["survey"].isin(rounds)].copy()
        b["rq"] = b["survey"].map(M8.RQ)
        g = S.s8.gov
        lv = []
        for _, r in b.iterrows():
            i = int(r["rq"]) - 1
            x = g.loc[(r["key"], i)] if (r["key"], i) in g.index else None
            lv.append({c: (float(x[c]) if x is not None and c in x.index else np.nan) for c in LEVEL if c != "rc2011"})
        L = pd.DataFrame(lv, index=b.index)
        b = pd.concat([b, L], axis=1)
        b["rc2011"] = b["key"].map(Fe.radimer_2011())
        # two-way fixed effects, weighted by measurement precision
        b["w"] = 1.0 / (b["se_y"] ** 2 + 0.02)
        N = {s: float(np.average(x["y"], weights=x["w"])) for s, x in b.groupby("survey")}
        A = {}
        for _ in range(30):
            res = b["y"] - b["survey"].map(N)
            A = {k: float(np.average(res[x.index], weights=x["w"])) for k, x in b.groupby("key")}
            res2 = b["y"] - b["key"].map(A)
            N = {s: float(np.average(res2[x.index], weights=x["w"])) for s, x in b.groupby("survey")}
        anchor = np.mean(list(A.values()))
        self.N = {s: v + anchor for s, v in N.items()}
        qs = np.array([M8.RQ[s] for s in self.N], float)
        ns = np.array([self.N[s] for s in self.N])
        self.slope = float(np.polyfit(qs, ns, 1)[0]) if len(qs) > 1 else 0.0
        self.last_q, self.last_n = int(qs.max()), float(ns[np.argmax(qs)])
        self.b = b.assign(rel=b["y"] - b["survey"].map(self.N)).reset_index(drop=True)
        d = self.b
        d["y_keep"] = d["y"]
        # structural level, cross-fitted by region
        self.folds = []
        oof = np.full(len(d), np.nan)
        for a, c in GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]):
            m = self._lv(d.iloc[a])
            oof[c] = m.predict_y(d.iloc[c])
            self.folds.append((set(d["region"].iloc[c]), m))
        self.full = self._lv(d)
        d["dev"] = d["rel"] - oof
        # moments: permanent province variance from pairs in different rounds; round-specific noise beyond sampling error
        pairs = [x * y for _, g_ in d.groupby("key") for ii, x in enumerate(g_["dev"].values) for y in g_["dev"].values[ii + 1:]]
        tot = float(np.mean(d["dev"] ** 2 - d["se_y"] ** 2))
        self.tau2 = max(0.005, float(np.mean(pairs))) if pairs else max(0.005, 0.5 * tot)
        self.sig2 = max(0.0, tot - self.tau2)
        return self

    def _lv(self, tr):
        t = tr.assign(y=tr["rel"], q=norm.cdf(tr["rel"] / tr["se_y"]))
        return M140.LGBNative("GBC", LEVEL).fit(t)

    def level(self, X):
        out = np.asarray(self.full.predict_y(X), float).copy()
        for regs, m in self.folds:
            idx = X["region"].isin(regs).values
            if idx.any():
                out[idx] = m.predict_y(X[idx])
        return out

    def shared(self, T):
        return self.last_n + self.slope * (np.asarray(T, float) - self.last_q)

    def province(self, X, T=None) -> pd.DataFrame:
        """Parts of the forecast: shared level, structural level, shrunk deviation, and the variance of the province part."""
        mu = self.level(X)
        dev, w, var = [], [], []
        for key in X["key"].values:
            own = self.b[self.b["key"] == key]
            if len(own):
                v = own["se_y"].values ** 2 + self.sig2
                pm = np.sum(own["dev"].values / v) / np.sum(1 / v)
                wi = self.tau2 / (self.tau2 + 1 / np.sum(1 / v))
            else:
                pm, wi = 0.0, 0.0
            dev.append(pm)
            w.append(wi)
            var.append(self.tau2 * (1 - wi) + self.sig2)
        T = X["T"].values if T is None else T
        return pd.DataFrame({"shared": self.shared(T), "level": mu, "weight_own": w, "deviation": dev, "adj": np.array(w) * np.array(dev), "var_prov": var}, index=X.index)

    def predict(self, X, T=None):
        p = self.province(X, T)
        return (p["shared"] + p["level"] + p["adj"]).values, p


def released(i, rounds, lag=Pn.ANCHOR_LAG):
    return [s for s in rounds if M8.RQ[s] + lag <= i]


class Residual:
    """LightGBM on as-of forecast errors of survey rows, with a learned option of no residual."""

    def __init__(self, cols):
        self.cols = list(cols)

    def fit(self, d):
        d = d.reset_index(drop=True)
        self.use_ = [c for c in self.cols if d[c].notna().any() and d[c].nunique() > 1]
        mono = [SIGN.get(c, 0) for c in self.use_]
        par = dict(PARAMS, monotone_constraints=mono, monotone_constraints_method="basic")
        w = 1.0 / (d["se_true"] ** 2 + 0.05)
        best = (float(np.sum(w * d["e"] ** 2)), 0)
        folds = list(GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]))
        self.oof_ = d["e"].values.copy()
        for n in GRID:
            pred = np.zeros(len(d))
            for a, b in folds:
                pred[b] = lgb.LGBMRegressor(n_estimators=n, **par).fit(d.iloc[a][self.use_], d.iloc[a]["e"], sample_weight=w.iloc[a]).predict(d.iloc[b][self.use_])
            sse = float(np.sum(w * (d["e"] - pred) ** 2))
            if sse < best[0]:
                best = (sse, n)
                self.oof_ = (d["e"] - pred).values
        self.n_ = best[1]
        self.m_ = lgb.LGBMRegressor(n_estimators=self.n_, **par).fit(d[self.use_], d["e"], sample_weight=w) if self.n_ else None
        return self

    def predict(self, X):
        return self.m_.predict(X[self.use_]) if self.m_ is not None else np.zeros(len(X))


class Pipeline:
    """Everything fitted from outcomes released at issue quarter i."""

    def __init__(self, S: Store, i: int, rounds: list[str], origin: str):
        self.S, self.i, self.origin = S, i, origin
        self.rel = released(i, rounds)
        self.hier = Hier().fit(S, self.rel)
        # as-of errors of each released outcome that had an earlier release
        rows = []
        for s in self.rel:
            tg = M8.targets(S.s8, [s])
            d = rows_for(S, tg, list(range(1, 9)), origin)
            if d.empty:
                continue
            for h, g in d.groupby("lead"):
                prior = released(M8.RQ[s] - h, rounds)
                if not prior:
                    continue
                hp = Hier().fit(S, prior)
                mu, _ = hp.predict(g, g["T"].values)
                g = g.assign(base=mu, e=g["y_true"].values - mu)
                rows.append(g)
        self.tr = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
        self.sigma_base = float(np.sqrt(np.mean(self.tr["e"] ** 2))) if len(self.tr) else None
        self.loading = 0.0
        if len(self.tr):
            t = self.tr.dropna(subset=["h_signal"])
            x, y = t["h_signal"].values, t["e"].values
            lam = 0.25 * len(x) * float(np.var(x)) if np.var(x) > 0 else 1.0     # ridge prior toward no loading
            self.loading = float(max(0.0, np.sum(x * (y - y.mean())) / (np.sum((x - x.mean()) ** 2) + lam)))
        self.res = {}

    def residual(self, name, cols):
        if name not in self.res:
            self.res[name] = Residual(cols).fit(self.tr) if len(self.tr) else None
        return self.res[name]


def sigma_of(e):
    return float(np.sqrt(np.mean(np.square(e))))


def q90(e):
    return float(np.quantile(np.abs(e), 0.90))


def classifier_b(P: Pipeline, te, cols):
    """Approach B. Soft labels, grouped Platt calibration; a risk probability, not prevalence."""
    d = P.tr.reset_index(drop=True)
    use = [c for c in cols if d[c].notna().any() and d[c].nunique() > 1]
    X2, y2, w2 = pd.concat([d[use], d[use]]), np.r_[np.ones(len(d)), np.zeros(len(d))], np.r_[d["q_true"].values, 1 - d["q_true"].values]
    par = dict(objective="binary", num_leaves=4, max_depth=2, min_child_samples=10, learning_rate=0.02, n_estimators=200, reg_lambda=5.0, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=150, n_jobs=1, verbose=-1)
    oof = np.zeros(len(d))
    for a, b in GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]):
        ia = np.r_[a, a + len(d)]
        m = lgb.LGBMClassifier(**par).fit(X2.iloc[ia], y2[ia], sample_weight=w2[ia] + 1e-6)
        oof[b] = m.predict_proba(d.iloc[b][use])[:, 1]
    lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
    pl = LogisticRegression(C=1.0).fit(np.r_[lg(oof), lg(oof)][:, None], y2, sample_weight=w2 + 1e-6)
    m = lgb.LGBMClassifier(**par).fit(X2, y2, sample_weight=w2 + 1e-6)
    raw = m.predict_proba(te[use])[:, 1]
    return pl.predict_proba(lg(raw)[:, None])[:, 1], raw


def logit_arm(cols, tr, te):
    use = [c for c in cols if tr[c].notna().any()]
    f = {c: 0.0 for c in NEWS}
    return M137.SoftLogit(use).fit(tr.assign(q=tr["q_true"]).fillna(f)).predict_proba(te.fillna(f))


def predict_all(P: Pipeline, te, te_frozen=None, news=True) -> dict:
    """All arms for the rows te, using information released at P.i."""
    base, parts = P.hier.predict(te, te["T"].values)
    out = {"mu_A-H": base, "part_shared": parts["shared"].values, "part_level": parts["level"].values, "part_adj": parts["adj"].values, "part_weight": parts["weight_own"].values}
    sig = P.sigma_base
    out["A-H"] = norm.cdf((base - LT) / sig)
    h = te["h_signal"].fillna(0.0).values
    mu_h = base + P.loading * h
    out["mu_A-Hh"], out["A-Hh"], out["part_h"] = mu_h, norm.cdf((mu_h - LT) / sig), P.loading * h
    gr = P.residual("G", RES)
    if gr is not None:
        r = gr.predict(te)
        mu_g = base + r
        sg = sigma_of(gr.oof_)
        out["mu_A-G"], out["A-G"], out["part_res"], out["q90_A-G"] = mu_g, norm.cdf((mu_g - LT) / sg), r, q90(gr.oof_)
        out["n_trees_A-G"] = np.full(len(te), gr.n_)
    if news and P.S.news is not None:
        nr = P.residual("GN", RES + NEWS)
        mu_n = base + nr.predict(te)
        out["mu_A-GN"], out["A-GN"] = mu_n, norm.cdf((mu_n - LT) / sigma_of(nr.oof_))
        out["n_trees_A-GN"] = np.full(len(te), nr.n_)
    grp = [c for g in GROUPS.values() for c in g] + ["h_signal", "y_anchor", "rtm", "gap_q", "lead", "rc2011"]
    pb, raw = classifier_b(P, te, grp)
    out["B-score"], out["B-raw"] = pb, raw
    tr = P.tr
    dy = (tr["y_true"] - tr["y_anchor"]).values
    rate = float(np.sum(dy) / np.sum(tr["gap_q"]))
    out["mu_DRIFT"], out["mu_PERS"] = te["y_anchor"].values + rate * te["gap_q"].values, te["y_anchor"].values
    out["DRIFT"] = norm.cdf((out["mu_DRIFT"] - LT) / float(np.std(dy)))
    out["PERS"] = norm.cdf((te["y_anchor"].values - LT) / float(np.sqrt(np.mean(dy ** 2))))
    out["LR-PSA"] = logit_arm(Fe.PSA, tr, te)
    out["LR-ALL"] = logit_arm(RES + ["y_anchor"], tr, te)
    if P.S.news is not None:
        out["LR-NLP"] = logit_arm([c for c in NEWS], tr, te)
    if te_frozen is not None and gr is not None:
        z = te_frozen.set_index(["key", "T", "lead"]).reindex(pd.MultiIndex.from_frame(te[["key", "T", "lead"]])).reset_index()
        ok = z["y_anchor"].notna().values
        v = np.full(len(te), np.nan)
        mf, _ = P.hier.predict(z[ok], z[ok]["T"].values)
        v[ok] = norm.cdf((mf + gr.predict(z[ok]) - LT) / sigma_of(gr.oof_))
        out["A-frozen"] = v
    return out

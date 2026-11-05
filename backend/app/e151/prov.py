"""
E151 Tier 2: province survey forecasts by rolling origin (docs/e151/PROTOCOL.md). 2018, 2019 and 2021 have been read by earlier work: retrospective evidence.

    python -m app.e151.prov run -> data/e151/out/prov_oof.csv, prov_results.json
"""
from __future__ import annotations

import json
import os
import sys
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm, spearmanr
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

from app.e141 import panel as P141
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e147 import labels as Lb
from app.e148 import model as M8
from app.e148 import panel as Pn
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e150.posthoc_relative import COLS as REL_COLS
from app.e151 import OUT

warnings.filterwarnings("ignore")
ROUNDS = ["NNS2013", "FNRI2015", "ENNS2018", "ENNS2019", "ENNS2021"]
ORIGIN = Ev.ORIGIN
LEADS = list(range(1, 9))
SEED = 151
G5 = ["market", "climate", "employment", "remittance", "poverty"]
GOV_COLS = [c for g in M.GROUPS.values() for c in g] + ["gap_q", "lead"]
N_P = [f"p_e_{g}" for g in G5 + ["response"]] + [f"p_tp_{g}" for g in G5 + ["response"]] + ["p_e_hunger", "p_e_net", "p_intensity", "p_net_since"]
N_A = ["a_e_net", "a_e_hunger", "a_net_since"] + [f"a_e_{g}" for g in G5]
N_N = ["n_e_net", "n_e_hunger", "n_net_since"] + [f"n_e_{g}" for g in G5]
N_R = ["r_e_net"]
NEWS_ALL = N_P + N_A + N_N + N_R + ["p_tg_hard", "p_tg_resp", "p_tg_net"]
NEWS_OVERALL = ["p_e_net", "p_e_hunger", "p_intensity", "p_net_since", "a_e_net", "a_net_since", "n_e_net", "n_net_since"]
GNT_COLS = GOV_COLS + NEWS_ALL + ["h2"]
SIGN = {**M.SIGN, "h2": 1, "p_tg_hard": 1, "p_tg_net": 1, "p_tg_resp": -1, "p_e_net": 1, "a_e_net": 1, "n_e_net": 1, "p_e_hunger": 1, "a_e_hunger": 1, "n_e_hunger": 1, "p_net_since": 1, "a_net_since": 1, "n_net_since": 1, "p_e_response": -1}
NEWS_LAG = 0
TARGET = os.environ.get("E151_TARGET", "mod_sev")                 # D4: the main target is HFIAS moderate plus severe; "insecure" is the any-level sensitivity run
SUFFIX = "" if TARGET == "mod_sev" else "_" + TARGET
CATS = {"mod_sev": ["Moderately Food Insecure Households", "Severely Food Insecure Households"], "insecure": ["Food Insecure Households"]}
N_T = ["p_tg_hard", "p_tg_resp", "p_tg_net"]
MIDAS = ["cpi_since", "soil_since", "rain_since", "tc_rate_since", "agri_since", "unemp_chg_since", "remit_since", "p_net_since", "a_net_since", "n_net_since", "gap_q"]


def target_rows(with_2021: bool = False) -> pd.DataFrame:
    """Survey rows for the chosen target, in the shape of Fe.base_rows. The HIGH line stays at 50 on this target; nothing is rescaled."""
    o = P141.outcomes(TARGET)[["key", "province", "region", "sws_area", "island", "survey", "year", "ref_quarter", "p", "se_p"]].copy()
    o = o[o["p"].notna() & o["se_p"].notna()].copy()
    if with_2021:
        k = o.drop_duplicates("key").set_index("key")
        e = _pct_2021()
        e = e[e["key"].isin(k.index)].copy()
        e["survey"], e["year"], e["ref_quarter"], e["p"], e["se_p"] = "ENNS2021", 2021, "2021-Q3", e["pct"], 3.0
        for c in ("province", "region", "sws_area", "island"):
            e[c] = e["key"].map(k[c])
        o = pd.concat([o, e[o.columns]], ignore_index=True)
    o["y"] = Fe._logit(o["p"])
    pp = o["p"] / 100
    o["se_y"] = (o["se_p"] / 100) / (pp * (1 - pp))
    o["q_high"] = norm.cdf(o["y"] / o["se_y"])
    return o.reset_index(drop=True)


def _pct_2021() -> pd.DataFrame:
    L = pd.read_csv(Lb.SEALED)
    w = L[L["fs_survey_category"].isin(CATS[TARGET])].drop_duplicates(["key", "fs_survey_category"]).groupby("key")["pct"].sum().reset_index()
    return w


class Hier2(M.Hier):
    """Fix 2: the shared level is carried flat from the last released round."""

    def shared(self, T):
        return np.full(len(np.asarray(T, float)), self.last_n)


class Store2(M.Store):
    """Fix 1: structural inputs relative to the all-province mean of the same issue quarter."""

    def __init__(self, base=None):
        super().__init__(target_rows() if base is None else base)
        g = self.s8.gov.copy()
        g[REL_COLS] = g[REL_COLS] - g[REL_COLS].groupby(level="qi").transform("mean")
        self.s8.gov = g
        self.news = None
        h2 = pd.read_parquet(OUT / "h2_signal.parquet")
        self.h2 = {(k, i, l): v for k, i, l, v in zip(h2["key"], h2["i"], h2["lead"], h2["h2"])}
        P = pd.read_parquet(OUT / "news_panel.parquet")
        self.P = P[P["lag_m"] == NEWS_LAG].set_index(["stream", "qi"]).sort_index()


def _stream_since(S, stream, a0, i):
    v = [S.P.at[(stream, q), "e_net"] for q in range(a0 + 1, i + 1) if (stream, q) in S.P.index]
    return float(np.mean(v)) if v else 0.0


def add_inputs(S, d: pd.DataFrame) -> pd.DataFrame:
    if d.empty:
        return d
    rows = []
    for r in d[["key", "i", "lead", "rq_anchor", "sws_area", "region"]].itertuples(index=False):
        o = {"h2": S.h2.get((r.key, r.i, r.lead), np.nan)}
        for pre, st in (("p", "prov:" + r.key), ("a", "area:" + r.sws_area), ("n", "nat")):
            k = (st, r.i)
            x = S.P.loc[k] if k in S.P.index else None
            for c in [f"e_{g}" for g in G5 + ["response"]] + [f"tp_{g}" for g in G5 + ["response"]] + ["e_hunger", "e_net"]:
                o[f"{pre}_{c}"] = float(x[c]) if x is not None and x[c] == x[c] else 0.0
            o[f"{pre}_intensity"] = float(x["intensity"]) if x is not None else np.nan
            o[f"{pre}_net_since"] = _stream_since(S, st, int(r.rq_anchor), int(r.i))
        k = ("prov:" + r.key, r.i)
        x = S.P.loc[k] if k in S.P.index else None
        for c in ("tg_hard", "tg_resp", "tg_net"):
            o["p_" + c] = float(x[c]) if x is not None and c in x.index and x[c] == x[c] else 0.0
        k = ("reg:iva", r.i)
        o["r_e_net"] = float(S.P.at[k, "e_net"]) if r.region == "CALABARZON" and k in S.P.index else np.nan
        rows.append(o)
    return pd.concat([d.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


class Res2:
    """Fix 3: LightGBM on as-of survey errors, always fitted. Trees chosen by weighted out-of-fold error within training rows."""

    GRID = [100, 300, 600]

    def __init__(self, cols):
        self.cols = list(cols)

    def fit(self, d):
        d = d.reset_index(drop=True)
        self.use_ = [c for c in self.cols if d[c].notna().any() and d[c].nunique() > 1]
        par = dict(M.PARAMS, monotone_constraints=[SIGN.get(c, 0) for c in self.use_], monotone_constraints_method="basic", random_state=SEED)
        w = 1.0 / (d["se_true"] ** 2 + 0.05)
        best = (np.inf, 100, None)
        folds = list(GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]))
        for n in self.GRID:
            pred = np.zeros(len(d))
            for a, b in folds:
                pred[b] = lgb.LGBMRegressor(n_estimators=n, **par).fit(d.iloc[a][self.use_], d.iloc[a]["e"], sample_weight=w.iloc[a]).predict(d.iloc[b][self.use_])
            sse = float(np.sum(w * (d["e"] - pred) ** 2))
            if sse < best[0]:
                best = (sse, n, (d["e"] - pred).values)
        self.n_, self.oof_ = best[1], best[2]
        self.gap_ = d["gap_q"].values.astype(float)
        self.m_ = lgb.LGBMRegressor(n_estimators=self.n_, **par).fit(d[self.use_], d["e"], sample_weight=w)
        return self

    def predict(self, X):
        return self.m_.predict(X[self.use_])

    def scale(self, gap):
        """Fix 6: squared error grows with quarters since the anchor; then a conformal multiplier for 90 % intervals."""
        Z = np.column_stack([np.ones(len(self.gap_)), self.gap_])
        b = np.linalg.lstsq(Z, self.oof_ ** 2, rcond=None)[0]
        b[1] = max(b[1], 0.0)
        s = np.sqrt(np.clip(b[0] + b[1] * self.gap_, 1e-3, None))
        q = float(np.quantile(np.abs(self.oof_) / s, 0.90))
        sd = np.sqrt(np.clip(b[0] + b[1] * np.asarray(gap, float), 1e-3, None))
        return sd, q * sd, {"var_intercept": float(b[0]), "var_per_quarter": float(b[1]), "conformal_q": q}


def _kalman(g, q, prior, prior_var, year):
    """Local-level filter over a province's released rounds. q is the variance added per year; q = 0 gives the Fay-Herriot style estimate. Returns the mean and variance at `year`."""
    m, v, t = prior, prior_var, None
    for r in g.sort_values("year").itertuples(index=False):
        if t is not None:
            v += q * (r.year - t)
        s = r.se_y ** 2
        k = v / (v + s)
        m, v, t = m + k * (r.y - m), (1 - k) * v, r.year
    return m, v + (q * max(0.0, year - t) if t is not None else 0.0)


def small_area(S, rel, te, tr):
    """Upgrade 3. Fay-Herriot: a poverty-covariate prior with between-area variance by moments, q = 0. State-space: the same with q chosen by predictive likelihood on released rounds only."""
    b = S.base[S.base["survey"].isin(rel)].copy()
    psa = pd.concat([tr[["key", "p_poverty"]], te[["key", "p_poverty"]]]).groupby("key")["p_poverty"].mean().dropna()
    b["x"] = b["key"].map(psa)
    b["x"] = b["x"].fillna(b["x"].mean()).fillna(0.0)
    X = np.column_stack([np.ones(len(b)), b["x"]])
    w = np.sqrt(1 / (b["se_y"].values ** 2 + 0.1))
    beta = np.linalg.lstsq(X * w[:, None], b["y"].values * w, rcond=None)[0]
    res = b["y"].values - X @ beta
    su2 = max(0.01, float(np.mean(res ** 2 - b["se_y"].values ** 2)))
    xbar = float(b["x"].mean())
    prior = lambda k: float(beta[0] + beta[1] * psa.get(k, xbar))
    best, bq = np.inf, 0.0
    groups = {k: g.sort_values("year") for k, g in b.groupby("key")}
    for q in (0.0, 0.005, 0.01, 0.02, 0.05, 0.1):
        ll = 0.0
        for k, g in groups.items():
            for j in range(1, len(g)):
                m, v = _kalman(g.iloc[:j], q, prior(k), su2, float(g["year"].iloc[j]))
                s = v + g["se_y"].iloc[j] ** 2
                ll += 0.5 * (np.log(s) + (g["y"].iloc[j] - m) ** 2 / s)
        if ll < best:
            best, bq = ll, q
    out = {}
    for name, q in (("FH", 0.0), ("SS", bq)):
        mu, var = [], []
        for k, t in zip(te["key"], te["T"].values):
            g = groups.get(k)
            m, v = _kalman(g, q, prior(k), su2, float(t) / 4.0) if g is not None else (prior(k), su2)
            mu.append(m)
            var.append(v)
        out[name] = (np.array(mu), np.array(var))
    return out, bq


def task(survey, lead, base=None, shuffle=None):
    Fe.LT = 0.0
    M.Hier = Hier2
    M.Store = Store2
    S = Store2(base)
    Tq, i = M8.RQ[survey], M8.RQ[survey] - lead
    if not M.released(i, ROUNDS):
        return None
    P = M.Pipeline(S, i, ROUNDS, ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = add_inputs(S, M.rows_for(S, tg, [lead], ORIGIN[survey]))
    if te.empty:
        return None
    tr = add_inputs(S, P.tr)
    if shuffle is not None:
        r = np.random.default_rng(shuffle)
        for fr in (tr, te):
            for _, g in fr.groupby(["survey", "lead"]):
                fr.loc[g.index, NEWS_ALL] = fr.loc[r.permutation(g.index.values), NEWS_ALL].values
    base_mu, parts = P.hier.predict(te, te["T"].values)
    keep = ["key", "province", "region", "island", "sws_area", "survey", "T", "lead", "i", "y_anchor", "gap_q", "rq_anchor", "h2"] + [c for c in ("y_true", "se_true", "q_true", "p_true") if c in te]
    o = te[keep].copy()
    o["mu_ANCHOR"], o["part_shared"], o["part_level"], o["part_adj"] = base_mu, parts["shared"].values, parts["level"].values, parts["adj"].values
    o["ANCHOR"] = norm.cdf(base_mu / P.sigma_base)
    for name, cols in (("GOV", GOV_COLS), ("NEWS", NEWS_ALL + ["gap_q", "lead"]), ("GN", GOV_COLS + NEWS_OVERALL), ("GNT", GNT_COLS)):
        m = Res2(cols).fit(tr)
        mu = base_mu + m.predict(te)
        sd, half, meta = m.scale(te["gap_q"].values)
        o[f"mu_{name}"], o[name], o[f"half_{name}"] = mu, norm.cdf(mu / sd), half
        if name == "GNT":
            o["n_trees"], o["var_slope"] = m.n_, meta["var_per_quarter"]
    dy = (tr["y_true"] - tr["y_anchor"]).values
    o["mu_PERS"] = te["y_anchor"].values
    o["PERS"] = norm.cdf(te["y_anchor"].values / float(np.sqrt(np.mean(dy ** 2))))
    o["half_PERS"] = float(np.quantile(np.abs(dy), 0.9))
    sa, bq = small_area(S, P.rel, te, tr)
    for name, (mu, var) in sa.items():
        sd = np.sqrt(var + 0.02)
        o[f"mu_{name}"], o[name], o[f"half_{name}"] = mu, norm.cdf(mu / sd), 1.645 * sd
    o["ss_q"] = bq
    # mixed-frequency baseline: change since the last survey on aggregates since that survey (U-MIDAS style, no Almon weights)
    use = [c for c in MIDAS if c in tr and tr[c].notna().any()]
    med, sd_ = tr[use].median(), tr[use].std().replace(0, 1)
    rg = Ridge(alpha=10.0).fit(((tr[use] - med) / sd_).fillna(0.0), dy)
    o["mu_MIDAS"] = te["y_anchor"].values + rg.predict(((te[use] - med) / sd_).fillna(0.0))
    e_ = dy - rg.predict(((tr[use] - med) / sd_).fillna(0.0))
    o["MIDAS"], o["half_MIDAS"] = norm.cdf(o["mu_MIDAS"] / float(np.sqrt(np.mean(e_ ** 2)))), float(np.quantile(np.abs(e_), 0.9))
    fill = lambda fr: fr.fillna({c: 0.0 for c in NEWS_ALL})
    def lr(cols):
        use = [c for c in cols if tr[c].notna().any()]
        return M.M137.SoftLogit(use).fit(fill(tr).assign(q=tr["q_true"])).predict_proba(fill(te))
    o["PSA"], o["LR"], o["LR_NEWS"] = lr(Fe.PSA), lr(GNT_COLS + ["y_anchor"]), lr(NEWS_ALL)
    o["sigma_base"], o["released"] = P.sigma_base, "+".join(P.rel)
    return o


def label_2021(F):
    w = _pct_2021()
    d21 = F["survey"] == "ENNS2021"
    F = F.drop(columns=[c for c in ("pct",) if c in F]).merge(w, on="key", how="left")
    F = F[~(F["survey"] == "ENNS2021") | F["pct"].notna()].copy()
    d21 = F["survey"] == "ENNS2021"
    F.loc[d21, "y_true"] = Fe._logit(F.loc[d21, "pct"])
    F.loc[d21, "se_true"] = 0.03 / (F.loc[d21, "pct"] / 100 * (1 - F.loc[d21, "pct"] / 100))
    F.loc[d21, "q_true"] = norm.cdf(F.loc[d21, "y_true"] / F.loc[d21, "se_true"])
    F["y_high"] = (F["y_true"] >= 0).astype(int)
    return F


ARMS = ["ANCHOR", "GOV", "NEWS", "GN", "GNT", "PERS", "PSA", "LR", "LR_NEWS", "FH", "SS", "MIDAS"]


def met(g, a):
    m = E7.metrics(g[a].values, g["y_high"].values, g["q_true"].values)
    c = m["confusion"]
    m["low_recall"] = c["tn"] / (c["tn"] + c["fp"]) if c["tn"] + c["fp"] else None
    m["balanced_accuracy"] = (m["recall"] + m["low_recall"]) / 2 if m["low_recall"] is not None else None
    if f"mu_{a}" in g:
        e = 100 / (1 + np.exp(-g[f"mu_{a}"])) - 100 / (1 + np.exp(-g["y_true"]))
        m["mae_points"], m["rmse_points"] = float(e.abs().mean()), float(np.sqrt((e ** 2).mean()))
        m["slope"] = float(np.polyfit(g[f"mu_{a}"], g["y_true"], 1)[0])
        m["mean_error_logit"] = float((g[f"mu_{a}"] - g["y_true"]).mean())
        chg = g["y_true"] - g["y_anchor"]
        pred = g[f"mu_{a}"] - g["y_anchor"]
        m["change_spearman"] = float(spearmanr(pred, chg).statistic) if pred.nunique() > 1 else None
        m["direction_accuracy"] = float(((pred > 0) == (chg > 0)).mean()) if pred.nunique() > 1 else None
        if f"half_{a}" in g:
            m["coverage_90"] = float((np.abs(g[f"mu_{a}"] - g["y_true"]) <= g[f"half_{a}"]).mean())
    return m


def calibrate(F):
    """Nested in time: a calibrator is fitted on as-of forecasts of rounds released before the target, and chosen on the previous round."""
    x = F[F["lead"] == 1]
    pre, r19, r21 = x[x["survey"] == "ENNS2018"], x[x["survey"] == "ENNS2019"], x[x["survey"] == "ENNS2021"]
    def fit(tr, kind):
        w = 1 / (tr["se_true"] ** 2 + 0.02)
        if kind == "none":
            return lambda z: z["mu_GNT"].values
        if kind == "linear":
            b = np.polyfit(tr["mu_GNT"], tr["y_true"], 1, w=np.sqrt(w))
            return lambda z: np.polyval(b, z["mu_GNT"].values)
        if kind == "isotonic":
            m = IsotonicRegression(out_of_bounds="clip").fit(tr["mu_GNT"], tr["y_true"], sample_weight=w)
            return lambda z: m.predict(z["mu_GNT"].values)
        res = tr["y_true"] - tr["mu_GNT"]
        eff = res.groupby(tr["region"]).agg(["sum", "size"])
        d = (eff["sum"] / (eff["size"] + 5.0)).to_dict()
        return lambda z: z["mu_GNT"].values + z["region"].map(d).fillna(0.0).values
    kinds = ["none", "linear", "isotonic", "region_pooling"]
    pick = {k: float(np.mean(np.abs(fit(pre, k)(r19) - r19["y_true"]))) for k in kinds}
    chosen = min(pick, key=pick.get)
    both = pd.concat([pre, r19])
    res = {"selection_error_on_2019_fit_on_2018": pick, "chosen": chosen, "by_kind_on_2021": {}}
    for k in kinds:
        mu = fit(both, k)(r21)
        p = norm.cdf(mu / float(np.std(both["y_true"] - fit(both, k)(both))))
        hi = (mu >= 0).astype(int)
        y = r21["y_high"].values
        res["by_kind_on_2021"][k] = {"mean_error_logit": float((mu - r21["y_true"]).mean()), "mae_points": float(np.mean(np.abs(100 / (1 + np.exp(-mu)) - 100 / (1 + np.exp(-r21["y_true"]))))), "slope": float(np.polyfit(mu, r21["y_true"], 1)[0]) if np.std(mu) > 0 else None, "accuracy": float((hi == y).mean()), "low_recall": float(((hi == 0) & (y == 0)).sum() / max(1, (y == 0).sum())), "high_recall": float(((hi == 1) & (y == 1)).sum() / max(1, (y == 1).sum())), "brier": float(np.mean((p - r21["q_true"]) ** 2))}
    return res


def scale_test(g, a, rng, n=5000):
    regs = list(g.groupby("region").indices.values())
    mu, y = g[f"mu_{a}"].values, g["y_true"].values
    sl, me = [], []
    for _ in range(n):
        i = np.concatenate([regs[j] for j in rng.integers(0, len(regs), len(regs))])
        if np.std(mu[i]) > 0:
            sl.append(np.polyfit(mu[i], y[i], 1)[0])
        me.append(np.mean(mu[i] - y[i]))
    cov = float((np.abs(mu - y) <= g[f"half_{a}"].values).mean())
    s, m = [np.percentile(sl, 2.5), np.percentile(sl, 97.5)], [np.percentile(me, 2.5), np.percentile(me, 97.5)]
    return {"slope_ci95": [float(x) for x in s], "mean_error_ci95": [float(x) for x in m], "coverage_90": cov, "may_be_called_prevalence": bool(s[0] <= 1 <= s[1] and m[0] <= 0 <= m[1] and 0.80 <= cov <= 0.98)}


def run():
    R = Parallel(n_jobs=20)(delayed(task)(s, h) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in LEADS)
    F = label_2021(pd.concat([x for x in R if x is not None], ignore_index=True))
    F.to_csv(OUT / f"prov_oof{SUFFIX}.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(SEED)
    res = {"evidence": "retrospective rolling origin; all rows read by earlier experiments", "by_lead": {}}
    for h, g in F.groupby("lead"):
        g = g.reset_index(drop=True)
        e = {"n": int(len(g)), "n_high": int(g["y_high"].sum()), "always_high": float(g["y_high"].mean()), "metrics": {a: met(g, a) for a in ARMS}}
        for a, b in (("GNT", "PERS"), ("GNT", "GOV"), ("GNT", "ANCHOR"), ("GOV", "ANCHOR"), ("NEWS", "ANCHOR"), ("GN", "GOV"), ("GOV", "PERS"), ("ANCHOR", "PERS")):
            e[f"{a}-{b}"] = E7.diff_ci(g, a, b, "q_true", rng, n=2000)
        res["by_lead"][f"L{h}"] = e
    x = F[F["lead"] == 1].reset_index(drop=True)
    # how the model compares with the old survey as it ages, which is the purpose of the study
    res["by_survey_age_L1"] = {}
    pct = lambda v: 100 / (1 + np.exp(-v))
    for lab, lo, hi in (("3_to_4_years", 12, 16), ("6_years", 24, 24)):
        g = x[(x["gap_q"] >= lo) & (x["gap_q"] <= hi)]
        if len(g) >= 5:
            res["by_survey_age_L1"][lab] = {"n": int(len(g)), "n_low": int((g["y_high"] == 0).sum()), "mae_GNT": float((pct(g["mu_GNT"]) - pct(g["y_true"])).abs().mean()), "mae_PERS": float((pct(g["mu_PERS"]) - pct(g["y_true"])).abs().mean()), "acc_GNT": float(((g["GNT"] >= .5) == (g["y_high"] == 1)).mean()), "acc_PERS": float(((g["PERS"] >= .5) == (g["y_high"] == 1)).mean()), "brier_GNT": float(np.mean((g["GNT"] - g["q_true"]) ** 2)), "brier_PERS": float(np.mean((g["PERS"] - g["q_true"]) ** 2))}
    # how often each arm says HIGH: a model that always says one thing shows up here
    res["share_forecast_high_L1"] = {a: float((x[a] >= .5).mean()) for a in ARMS}
    res["share_actual_high_L1"] = float(x["y_high"].mean())
    res["by_survey_L1"] = {s: {"n": int(len(g)), "n_high": int(g["y_high"].sum()), "metrics": {a: met(g, a) for a in ("ANCHOR", "GOV", "GNT", "PERS")}} for s, g in x.groupby("survey")}
    res["by_island_L1"] = {s: {"n": int(len(g)), "n_high": int(g["y_high"].sum()), "accuracy_GNT": float(((g["GNT"] >= .5) == (g["y_high"] == 1)).mean()), "accuracy_PERS": float(((g["PERS"] >= .5) == (g["y_high"] == 1)).mean())} for s, g in x.groupby("island")}
    x["t"] = pd.qcut(x["gap_q"], 3, labels=False, duplicates="drop")
    res["coverage_by_staleness_L1"] = {str(int(t)): {"gap_q_range": [int(g["gap_q"].min()), int(g["gap_q"].max())], "n": int(len(g)), "half_width_logit": float(g["half_GNT"].mean()), "coverage": float((np.abs(g["mu_GNT"] - g["y_true"]) <= g["half_GNT"]).mean()), "rmse": float(np.sqrt(((g["mu_GNT"] - g["y_true"]) ** 2).mean()))} for t, g in x.groupby("t")}
    res["scale_test_L1"] = {a: scale_test(x, a, rng) for a in ("GNT", "GOV")}
    res["calibration"] = calibrate(F)
    res["province_rows_L1"] = x[x["region"] == "CALABARZON"][["province", "survey", "y_true", "y_anchor", "mu_ANCHOR", "mu_GOV", "mu_NEWS", "mu_GNT", "GNT", "PERS", "half_GNT"]].round(3).to_dict(orient="records")
    # placebo: news shuffled within round and lead
    pl = Parallel(n_jobs=20)(delayed(task)(s, 1, None, 5000 + k) for k in range(30) for s in ("ENNS2018", "ENNS2019", "ENNS2021"))
    br = []
    for k in range(30):
        z = label_2021(pd.concat([p for p in pl[k * 3:k * 3 + 3] if p is not None], ignore_index=True))
        br.append(float(np.mean((z["GNT"] - z["q_true"]) ** 2)))
    real = float(np.mean((x["GNT"] - x["q_true"]) ** 2))                # the same soft Brier as the placebos; metrics()["brier"] is defined differently
    res["placebo_L1"] = {"real_brier_soft": real, "placebo_mean": float(np.mean(br)), "placebo_values": [float(v) for v in br], "share_placebo_better_or_equal": float(np.mean(np.array(br) <= real)), "note": "news columns shuffled within round and lead; 30 runs"}
    res["target"] = TARGET
    (OUT / f"prov_results{SUFFIX}.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    L1 = res["by_lead"]["L1"]
    print(json.dumps({a: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in L1["metrics"][a].items() if k in ("accuracy", "balanced_accuracy", "low_recall", "recall", "auc", "brier", "mae_points", "slope", "coverage_90", "change_spearman", "direction_accuracy")} for a in ARMS}, indent=0))
    print({k: L1[k] for k in L1 if "-" in k})
    print(res["scale_test_L1"], res["calibration"], res["coverage_by_staleness_L1"], res["placebo_L1"])


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()

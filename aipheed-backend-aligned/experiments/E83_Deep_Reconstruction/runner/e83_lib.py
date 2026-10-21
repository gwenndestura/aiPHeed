"""E83 library (PROTOCOL.md): one leakage-safe harness for Leads 0-3 on the approved T43 target.

Data, publication timing (origin O(t) = first day of quarter t+1; CPI to month 2 of quarter t; SWS rounds posted before
O(t)) and T43 labels come from the audited E41/E43 libraries. E83 adds: lead-general features and structural
simulation, the five-driver group map, lead-text news features (N-series), the model arms and the scoring loop.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E83 = Path(__file__).resolve().parents[1]
EXP = E83.parent
sys.path.insert(0, str(EXP / "E43_Five_Trigger_Risk" / "runner"))
sys.path.insert(0, str(EXP / "E46_Rice_Policy" / "runner"))
import e43_lib as K  # noqa: E402

L = K.L
np, pd = L.np, L.pd
BACKEND = L.ROOT / "backend"
PROC = BACKEND / "data" / "processed"                        # identical (sha256) to the aligned copies E43 used
K.EXTRA_FILES = {"climate": PROC / "pagasa_climate.parquet", "ofw": PROC / "bsp_macro.parquet",
                 "rice": PROC / "psa_rice_prices.parquet"}
LEADS = (0, 1, 2, 3)
EVAL_FROM = L.qi("2023-Q1")          # thresholds were frozen on 2021-22 data, so targets from 2023 are threshold-clean

# ------------------------------------------------------------------------------------------------ driver groups
# Five drivers of the directive (section 7). Hunger history is the approved target's own lagged outcome, kept apart.
DRIVERS = {
    "D1_prices": ["F_last", "F_now", "gap_now", "mom3", "F_hat_k", "G_hat_k", "D_now", "rice_whsl_yoy",
                  "tariff_yoy_regime", "import_suspension_share", "price_ceiling_share", "food_emergency_share"],
    "D2_climate": ["tc_count", "tc_max_signal", "tc_severe", "enso"],
    "D3_agri_supply": ["palay_yoy", "corn_yoy", "fish_yoy", "aqua_yoy"],
    "D4_household_economy": ["ur_last", "ur_yoy", "under_last", "remit_usd_yoy", "fx_yoy"],
    "D5_news_v0": ["news_market", "news_climate", "news_fish_kill", "news_employment", "news_ofw_remittance", "news_n",
                   "fssi_v2", "fssi_admitted"],
    "H_history": ["H_last", "H_chg", "H_age"],
}


def data():
    d = L.load()
    x = K.load_extra()
    return d, x


# ------------------------------------------------------------------------------------------------ projections
def proj(d_cut: L.Data, t: int, k: int, p: str, commodity: str) -> float:
    """Base-effect projection of the quarter-mean YoY at t+k (E41 M1 generalised to any lead and to headline)."""
    m0 = L.m0_of(t)
    I = L._series(d_cut, p, commodity)
    if m0 not in I.index:
        return np.nan
    lnI = np.log(I)
    g, _, n = L.drift_sigma(lnI, m0)
    ms = L.target_months(t, k)
    if any((m - 12) not in I.index or (m - 12) < L.FIRST_YM for m in ms) or not np.isfinite(g):
        return np.nan
    vals = [100 * ((I[m] if m <= m0 and m in I.index else math.exp(lnI[m0] + g * (m - m0))) / I[m - 12] - 1) for m in ms]
    return float(np.mean(vals))


def features(d: L.Data, x: dict, origins: list[int], k: int, events=None) -> pd.DataFrame:
    """E43 five-trigger features + E46 rice-policy features + lead-k projections, all as of O(t)."""
    import e46_lib as R
    X = K.features(d, x, origins)
    events = R.load_events() if events is None else events
    pf = []
    for t in origins:
        f = R.policy_features(events, t) if k == 2 else _policy_k(R, events, t, k)
        pf.append({"t": t, **f})
    X = X.merge(pd.DataFrame(pf), on="t", how="left")
    rows = []
    for t in origins:
        c = d.cut(t)
        for p in L.PROVS:
            F = proj(c, t, k, p, "food")
            H = proj(c, t, k, p, "all_items")
            rows.append({"t": t, "province_code": p, "F_hat_k": F, "G_hat_k": F - H if np.isfinite(F) and np.isfinite(H) else np.nan})
    return X.merge(pd.DataFrame(rows), on=["t", "province_code"], how="left")


def _policy_k(R, events, t, k):
    O = L.origin(t)
    known = events[events["announcement_date"] < O]
    months = L.target_months(t, k)
    out = {c: 0.0 for c in R.POLICY}
    for e in known.itertuples():
        a, b = R._ym(str(e.effective_start.date())), R._ym(str(e.effective_end.date()))
        if e.feature == "tariff_yoy_regime":
            out[e.feature] = max(out[e.feature], float(np.mean([(m >= a) and (m - 12 < a) for m in months])))
        else:
            out[e.feature] = max(out[e.feature], float(np.mean([a <= m <= b for m in months])))
    return out


# ------------------------------------------------------------------------------------------------ labels
def labels_all(d_full: L.Data) -> pd.DataFrame:
    return K.label_frame(d_full)


def available(d_full: L.Data, t: int) -> pd.DataFrame:
    return K.available_labels(d_full, t)


def pairs(X: pd.DataFrame, d_full: L.Data, t: int, k: int) -> pd.DataFrame:
    """Training pairs (X(t'), y(t'+k)) whose label was complete and posted before O(t)."""
    lab = available(d_full, t)
    tr = X[X["t"] + k <= t - 1].assign(q=lambda f: f["t"] + k)
    return tr.merge(lab[["province_code", "q", "y"]], on=["province_code", "q"], how="inner")


# ------------------------------------------------------------------------------------------------ structural
def simulate(d_cut: L.Data, t: int, k: int, n: int = 20000, seed: int = 83, seasonal: bool = False) -> dict:
    """P(T43 HIGH at t+k): regional H random walk from the latest posted round (step sd from posted history, scaled by
    sqrt(gap)); province food and headline log-index paths with the joint mean/covariance of the last 12 monthly
    changes; months already published are used as observed. Returns {province: (p, p_hunger, p_price)}."""
    th = L.e40_spec()
    rng = np.random.default_rng(seed + 10 * t + k)
    hq = L.h_quarters(d_cut).sort_values("q")
    if len(hq) < 5:
        return {}
    qq, hh = hq["q"].to_numpy(), hq["H"].to_numpy()
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    h = t + k - int(qq[-1])
    Hk = float(hh[-1]) + rng.normal(0, sig * math.sqrt(max(h, 0)), n) if h > 0 else np.full(n, float(hh[-1]))
    if h <= 0:                                           # the target round is already posted
        Hk = np.full(n, float(hq.set_index("q")["H"][t + k]))
    sws = Hk > th["H"]
    m0 = L.m0_of(t)
    ms = L.target_months(t, k)
    steps = max(ms) - m0
    out = {}
    for p in L.PROVS:
        lf, lh = np.log(L._series(d_cut, p, "food")), np.log(L._series(d_cut, p, "all_items"))
        win = lambda s: s.diff()[(s.index > m0 - 12) & (s.index <= m0) & (s.index - 1 >= L.FIRST_YM)].dropna()  # noqa: E731
        cf, ch = win(lf), win(lh)
        j = cf.index.intersection(ch.index)
        if len(j) < 6 or any((m - 12) not in lf.index for m in ms) or m0 not in lf.index:
            continue
        Z = np.column_stack([cf[j], ch[j]])
        if steps > 0 and not seasonal:
            inc = rng.multivariate_normal(Z.mean(axis=0), np.cov(Z.T, ddof=1), size=(n, steps))
            pf, ph = lf[m0] + np.cumsum(inc[:, :, 0], axis=1), lh[m0] + np.cumsum(inc[:, :, 1], axis=1)
        elif steps > 0:
            # R2-1 (DEVIATIONS D2): each future month's mean change = mean change of the same calendar month in earlier
            # in-window years (published by O(t)); noise = covariance of the last 12 deseasonalised changes.
            mf, mh = _seasonal_means(lf, m0), _seasonal_means(lh, m0)
            if mf is None or mh is None:
                continue
            res = Z - np.column_stack([[mf[(m % 12)] for m in j], [mh[(m % 12)] for m in j]])
            mu = np.array([[mf[(m0 + i) % 12], mh[(m0 + i) % 12]] for i in range(1, steps + 1)])
            inc = mu[None, :, :] + rng.multivariate_normal(np.zeros(2), np.cov(res.T, ddof=1), size=(n, steps))
            pf, ph = lf[m0] + np.cumsum(inc[:, :, 0], axis=1), lh[m0] + np.cumsum(inc[:, :, 1], axis=1)

        def val(path, s, m):
            return np.full(n, s[m]) if m <= m0 else path[:, m - m0 - 1]
        Fq = np.mean([100 * (np.exp(val(pf if steps > 0 else None, lf, m)) / np.exp(lf[m - 12]) - 1) for m in ms], axis=0)
        Gq = np.mean([100 * (np.exp(val(ph if steps > 0 else None, lh, m)) / np.exp(lh[m - 12]) - 1) for m in ms], axis=0)
        price = (Fq > th["food"][p]) | ((Fq - Gq) > th["gap"][p])
        out[p] = (float(np.mean(sws & price)), float(np.mean(sws)), float(np.mean(price)))
    return out


def _seasonal_means(lnI: pd.Series, m0: int) -> dict | None:
    """Mean monthly log change per calendar month over in-window months <= m0 (both ends inside 2021-01..m0)."""
    ch = lnI.diff()
    ch = ch[(ch.index <= m0) & (ch.index - 1 >= L.FIRST_YM)].dropna()
    g = ch.groupby(ch.index % 12).mean()
    if len(g) < 12:
        return None
    return g.to_dict()


# ------------------------------------------------------------------------------------------------ learners
LGBM = dict(objective="binary", num_leaves=4, max_depth=2, min_child_samples=5, n_estimators=100, learning_rate=0.05,
            reg_lambda=5.0, random_state=83, deterministic=True, n_jobs=1, force_row_wise=True, verbosity=-1)


class GB(K.GBModel):
    def fit(self, tr):
        from lightgbm import LGBMClassifier
        p = tr["y"].mean()
        self.m = LGBMClassifier(**LGBM, scale_pos_weight=(1 - p) / p).fit(tr[self.cols].astype(float), tr["y"].astype(int))
        return self


LR = K.LRModel


def eligible(tr: pd.DataFrame) -> bool:
    return K.eligible(tr)


# ------------------------------------------------------------------------------------------------ scoring
metrics = L.cls_metrics
sign_flip = L.sign_flip
holm = L.holm
date_bootstrap = L.date_bootstrap

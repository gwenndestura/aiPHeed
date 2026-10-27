"""LEAD2_OPTIMIZATION library (PROTOCOL_LEAD2.md): engineered price dynamics (P1), the wider tuning grid (P2), the
distributional price regressors (P3) and the direct-regression hunger terms (H1 on 2021+, H2 on 1998+ = sample b).

Reused unchanged from FINAL_UNIFIED_LGBM: the stacked table of every lead (12 families + lead + world prices), the
training-row rule, inner chronological validation by origin, labels (T43c), pi_H, baselines and the reliability rule.
"""
from __future__ import annotations

import functools
import itertools
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
L2 = HERE.parent
EXP = L2.parent
OUT = L2 / "out"
sys.path.insert(0, str(EXP / "FINAL_UNIFIED_LGBM" / "runner"))
import uni_lib as U  # noqa: E402

C, FM, B, E, L, np, pd = U.C, U.FM, U.B, U.E, U.L, U.np, U.pd
from scipy.stats import norm, t as student_t  # noqa: E402

SEED = 2028
H_LINE = U.H_LINE
LONG = EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "data" / "long"
FE_COLS = ["F_ex", "G_ex", "mom1", "mom6", "accel", "vol6", "A1_food_d", "A1_gap_d", "R_rice_yoy", "R_rice_mom3"]
MONO_UP = ["A1_food", "A1_gap", "A_mom", "A1_food_d", "A1_gap_d"]
MIN_PAIRS = 6
FAMILY_OF = {**U.FAMILY_OF, **{c: "A1" for c in ("F_ex", "G_ex", "mom1", "mom6", "accel", "vol6", "A1_food_d",
                                                  "A1_gap_d")}, "R_rice_yoy": "A3", "R_rice_mom3": "A3"}


def base_cols(news: bool = True) -> list[str]:
    return U.cols("U2", news)


def fe_cols(news: bool = True) -> list[str]:
    return base_cols(news) + FE_COLS


# ================================================================================================ inputs
@functools.lru_cache(maxsize=1)
def rice_cpi() -> pd.Series:
    """Region IV-A rice CPI (index) by month, 2021-01 onward only (study window)."""
    c = pd.read_csv(LONG / "cov_cpi.csv")
    c = c[c["geolocation"].str.startswith("Region IV-A") & c["commodity_description"].str.contains("Rice")]
    c = c[(c["ym"] >= L.FIRST_YM - 3) & c["value"].notna()]
    return c.set_index("ym")["value"].astype(float).sort_index()


def _origin_fe(d, t: int, rice: pd.Series) -> dict:
    """Lead-independent engineered values per province at origin t, from months <= m0 only."""
    th = L.e40_spec()
    m0 = L.m0_of(t)
    dc = d.cut(t)
    out = {}
    r = rice[rice.index <= m0]
    r_yoy = (100 * (r[m0] / r[m0 - 12] - 1)) if m0 in r.index and m0 - 12 in r.index else np.nan
    r_mom = (100 * (math.log(r[m0]) - math.log(r[m0 - 3]))) if m0 in r.index and m0 - 3 in r.index else np.nan
    for p in L.NAMES:
        y = dc.yoy[dc.yoy["province_code"] == p]
        f = y[y["commodity"] == "food"].set_index("ym")["yoy"]
        a = y[y["commodity"] == "all_items"].set_index("ym")["yoy"]
        last = [m for m in (m0 - 2, m0 - 1, m0) if m in f.index and m in a.index]
        s = L._series(dc, p, "food")
        s = s[s.index <= m0]
        lg = np.log(s)
        ch = lg.diff().dropna()
        ch6 = ch[(ch.index > m0 - 6) & (ch.index <= m0)]
        out[p] = {
            "F_ex": float(f[last].mean() - th["food"][p]) if len(last) == 3 else np.nan,
            "G_ex": float((f[last] - a[last]).mean() - th["gap"][p]) if len(last) == 3 else np.nan,
            "mom1": float(100 * (lg[m0] - lg[m0 - 1])) if m0 in lg.index and m0 - 1 in lg.index else np.nan,
            "mom6": float(100 * (lg[m0] - lg[m0 - 6])) if m0 in lg.index and m0 - 6 in lg.index else np.nan,
            "accel": float(f[m0] - f[m0 - 3]) if m0 in f.index and m0 - 3 in f.index else np.nan,
            "vol6": float(100 * ch6.std(ddof=1)) if len(ch6) >= 4 else np.nan,
            "R_rice_yoy": float(r_yoy), "R_rice_mom3": float(r_mom),
        }
    return out


def _drift_projection(dc, t: int, k: int, p: str, commodity: str) -> float:
    """Mean YoY of the target months of t+k with the index grown at its trailing 6-month mean monthly log change."""
    s = L._series(dc, p, commodity)
    m0 = L.m0_of(t)
    if m0 not in s.index or m0 - 6 not in s.index:
        return float("nan")
    g = (math.log(s[m0]) - math.log(s[m0 - 6])) / 6
    vals = [100 * (s[m0] * math.exp(g * (m - m0)) / s[m - 12] - 1)
            for m in L.target_months(t, k) if L.FIRST_YM <= m - 12 <= m0 and (m - 12) in s.index]
    return float(np.mean(vals)) if len(vals) >= 2 else float("nan")


def add_fe(S: pd.DataFrame, d=None, rice: pd.Series | None = None) -> pd.DataFrame:
    d = E.data()[0] if d is None else d
    rice = rice_cpi() if rice is None else rice
    th = L.e40_spec()
    S = S.copy()
    of = {int(t): _origin_fe(d, int(t), rice) for t in S["t"].unique()}
    for c in ("F_ex", "G_ex", "mom1", "mom6", "accel", "vol6", "R_rice_yoy", "R_rice_mom3"):
        S[c] = [of[int(t)][p][c] for t, p in zip(S["t"], S["province_code"])]
    cuts = {int(t): d.cut(int(t)) for t in S["t"].unique()}
    fd, gd = [], []
    for t, k, p in zip(S["t"], S["lead"], S["province_code"]):
        dc = cuts[int(t)]
        f = _drift_projection(dc, int(t), int(k), p, "food")
        h = _drift_projection(dc, int(t), int(k), p, "all_items")
        fd.append(f - th["food"][p])
        gd.append((f - h) - th["gap"][p])
    S["A1_food_d"], S["A1_gap_d"] = fd, gd
    return S


# ================================================================================================ price models
def uni_grid() -> list[dict]:
    return [dict(id=f"u{c['id']}", leaves=c["leaves"], depth=c["depth"], trees=c["trees"], cw=c["cw"], lr=0.05,
                 min_child=15, sub=1.0, col=1.0, l1=0.0, l2=5.0) for c in B.GRID]


def wide_grid() -> list[dict]:
    space = list(itertools.product((2, 3, 4, 7), (0.03, 0.05, 0.1), (50, 100, 200, 400), (10, 15, 25), (0.8, 1.0),
                                   (0.7, 1.0), (0.0, 1.0), (1.0, 5.0, 10.0), (None, "balanced")))
    rng = np.random.default_rng(SEED)
    pick = rng.choice(len(space), 24, replace=False)
    g = [dict(id=f"w{i}", leaves=s[0], depth=int(math.ceil(math.log2(s[0]))), lr=s[1], trees=s[2], min_child=s[3],
              sub=s[4], col=s[5], l1=s[6], l2=s[7], cw=s[8]) for i, s in enumerate(space[j] for j in sorted(pick))]
    return uni_grid() + g


class Model:
    """LightGBM classifier (or regressor) with the protocol's monotone terms."""

    def __init__(self, cfg: dict, cols: list[str], reg: bool = False):
        self.cfg, self.cols, self.reg = cfg, cols, reg
        self.m = self.const = None

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        import lightgbm as lgb
        if not self.reg and len(set(y.tolist())) < 2:
            self.const = float(np.mean(y)) if len(y) else 0.5
            return self
        c = self.cfg
        kw = dict(learning_rate=c["lr"], n_estimators=c["trees"], num_leaves=c["leaves"], max_depth=c["depth"],
                  min_child_samples=c["min_child"], subsample=c["sub"], subsample_freq=1 if c["sub"] < 1 else 0,
                  colsample_bytree=c["col"], reg_alpha=c["l1"], reg_lambda=c["l2"], deterministic=True,
                  force_row_wise=True, feature_pre_filter=False, random_state=SEED, n_jobs=1, verbose=-1,
                  monotone_constraints=[1 if x in MONO_UP else 0 for x in self.cols],
                  monotone_constraints_method="basic")
        if self.reg:
            self.m = lgb.LGBMRegressor(objective="regression", **kw)
        else:
            self.m = lgb.LGBMClassifier(objective="binary", class_weight=c["cw"], **kw)
        self.m.fit(X[self.cols].astype(float), y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.m is None:
            return np.full(len(X), self.const)
        if self.reg:
            return self.m.predict(X[self.cols].astype(float))
        return self.m.predict_proba(X[self.cols].astype(float))[:, 1]


def _folds(tr: pd.DataFrame):
    origins = sorted(tr["t"].unique())[-4:]
    f = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o]) for o in origins]
    return [(a, h) for a, h in f if a["q"].nunique() >= 3 and a["y"].nunique() == 2 and len(h)]


def select_clf(tr: pd.DataFrame, cols: list[str], grid: list[dict]) -> dict:
    folds = _folds(tr)
    if not folds:
        return grid[0]
    ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
    sc = {}
    for c in grid:
        ps = np.concatenate([Model(c, cols).fit(f, f["y"].to_numpy(int)).predict(h) for f, h in folds])
        p = np.clip(ps, 1e-6, 1 - 1e-6)
        sc[c["id"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return min(grid, key=lambda c: (round(sc[c["id"]], 9), grid.index(c)))


def _excess(tr: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    th = L.e40_spec()
    yf = tr["F"].to_numpy(float) - tr["province_code"].map(th["food"]).to_numpy(float)
    yg = (tr["F"] - tr["HL"]).to_numpy(float) - tr["province_code"].map(th["gap"]).to_numpy(float)
    return yf, yg


def select_reg(tr: pd.DataFrame, cols: list[str], target: int) -> tuple[dict, float]:
    """Regression config by inner-fold squared error; sigma = RMSE of the chosen config's inner-fold predictions."""
    grid = [c for c in uni_grid() if c["cw"] is None]
    folds = _folds(tr)
    if not folds:
        return grid[0], 2.0
    ys = np.concatenate([_excess(h)[target] for _, h in folds])
    best, best_se = None, None
    for c in grid:
        ps = np.concatenate([Model(c, cols, reg=True).fit(f, _excess(f)[target]).predict(h) for f, h in folds])
        se = float(np.mean((ps - ys) ** 2))
        if best_se is None or round(se, 9) < round(best_se, 9):
            best, best_se = c, se
    return best, max(math.sqrt(best_se), 0.25)


def price_prob(arm: str, tr: pd.DataFrame, te: pd.DataFrame, news: bool = True) -> tuple[np.ndarray, str]:
    """pi_P of one arm at one origin (tr: training rows with y, F, HL; te: rows of the origin, every lead)."""
    if arm == "P0":
        cc = base_cols(news)
        cfg, _ = U.select(tr, cc, True)
        return U.UniPrice(cfg, cc, True).fit(tr).predict(te), f"u{cfg['id']}"
    cc = fe_cols(news)
    if arm in ("P1", "P2"):
        cfg = select_clf(tr, cc, uni_grid() if arm == "P1" else wide_grid())
        return Model(cfg, cc).fit(tr, tr["y"].to_numpy(int)).predict(te), cfg["id"]
    if arm == "P3":
        yf, yg = _excess(tr)
        cf, sf = select_reg(tr, cc, 0)
        cg, sg = select_reg(tr, cc, 1)
        pf = norm.cdf(Model(cf, cc, reg=True).fit(tr, yf).predict(te) / sf)
        pg = norm.cdf(Model(cg, cc, reg=True).fit(tr, yg).predict(te) / sg)
        return 1 - (1 - pf) * (1 - pg), f"{cf['id']}/{cg['id']}|{sf:.2f}/{sg:.2f}"
    raise ValueError(arm)


# ================================================================================================ hunger terms
@functools.lru_cache(maxsize=1)
def long_bl() -> pd.DataFrame:
    """Pre-2021 non-commissioned Balance Luzon rounds (sample b), release date by the E114 rule."""
    r = pd.read_csv(LONG / "sws_area_rounds_full.csv")
    r = r[(r["era"] == "pre-2021") & (~r["commissioned"].astype(bool))]
    return pd.DataFrame({"q": [L.qi(q) for q in r["quarter"]], "H": r["balance_luzon"].astype(float),
                         "published": r["published"].astype(str).str[:10]})


def known_series(iss: str, sample: str) -> list[tuple[int, float]]:
    """(q, mean H) of BL quarters with a round published before iss: the 2021+ verified series (as pi_H uses), plus
    the pre-2021 quarters for sample b."""
    kn = [(q, h) for q, h, *_ in C.bl_known(iss)]
    if sample == "b":
        lb = long_bl()
        lb = lb[(lb["published"] < iss) & (lb["q"] < L.FIRST_Q)]
        pre = [(int(q), float(g["H"].mean())) for q, g in lb.groupby("q")]
        kn = pre + [x for x in kn if x[0] >= L.FIRST_Q]
    return sorted(kn)


def ar_hunger(t: int, k: int, sample: str) -> tuple[float, dict]:
    """P(BL hunger(t+k) > 11.3) by direct regression at the true horizon h on the known series."""
    kn = known_series(E.issue(t), sample)
    if not kn:
        return float("nan"), {}
    q_last, x0 = kn[-1]
    h = (t + k) - q_last
    d = dict(kn)
    pairs = [(d[q], d[q + h]) for q in d if q + h in d]
    if len(pairs) < MIN_PAIRS:
        return float("nan"), {"n_pairs": len(pairs)}
    x, y = np.array(pairs).T
    n = len(x)
    sxx = float(np.sum((x - x.mean()) ** 2))
    b = float(np.clip(np.sum((x - x.mean()) * (y - y.mean())) / sxx, 0.0, 1.0)) if sxx > 0 else 0.0
    a = float(y.mean() - b * x.mean())
    res = y - (a + b * x)
    s = math.sqrt(float(np.sum(res ** 2)) / (n - 2))
    se = s * math.sqrt(1 + 1 / n + ((x0 - x.mean()) ** 2 / sxx if sxx > 0 else 0))
    yhat = a + b * x0
    p = 1 - float(student_t.cdf((H_LINE - yhat) / max(se, 0.25), n - 2))
    return p, {"n_pairs": n, "a": a, "b": b, "yhat": yhat, "se": se, "h": h}


def hunger_terms(D: pd.DataFrame) -> pd.DataFrame:
    """Adds pi_H1 (AR21, fallback H0) and pi_H2 (AR98, sample b, fallback H0) per (origin, lead)."""
    cache = {}
    for t, k in D[["t", "lead"]].drop_duplicates().itertuples(index=False):
        a, ia = ar_hunger(int(t), int(k), "a")
        b, ib = ar_hunger(int(t), int(k), "b")
        cache[(int(t), int(k))] = (a, b, ia.get("yhat"), ib.get("yhat"))
    D = D.copy()
    v = [cache[(int(t), int(k))] for t, k in zip(D["t"], D["lead"])]
    D["pi_H1_raw"] = [x[0] for x in v]
    D["pi_H2_raw"] = [x[1] for x in v]
    D["H1_yhat"] = [x[2] for x in v]
    D["H2_yhat"] = [x[3] for x in v]
    D["pi_H1"] = np.where(np.isnan(D["pi_H1_raw"]), D["H1"], D["pi_H1_raw"])
    D["pi_H2"] = np.where(np.isnan(D["pi_H2_raw"]), D["H1"], D["pi_H2_raw"])
    return D


# ================================================================================================ forecasts
def forecast_origin(S: pd.DataFrame, t: int, arms=("P0", "P1", "P2", "P3"), news: bool = True, d=None):
    tr = U.train_rows(S, t, d)
    te = S[S["t"] == t]
    if not B.eligible(tr) or not len(te):
        return None
    out = te[["t", "lead", "province_code", "target_q", "H1", "h_last"]].copy()
    for a in arms:
        p, cfg = price_prob(a, tr, te, news)
        out[f"{a}_price"] = p
        out[f"{a}_cfg"] = cfg
    return out

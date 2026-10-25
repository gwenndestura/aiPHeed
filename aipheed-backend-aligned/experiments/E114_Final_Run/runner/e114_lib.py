"""E114 library (PROTOCOL_E114.md): two outcome samples (a: 2021+, b: full 1998+ history), dated long-history
covariates cut at issue dates, the shrinkage-to-persistence family, a panel model with area effects, a structural
state-space model (local level + quarterly seasonal + exogenous regressors), baselines, conformal bands and tests.
Self-contained (no E107 machinery); E111's Newey-West DM and E113's MCS are reimplemented identically."""
from __future__ import annotations

import functools
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
E114 = HERE.parent
EXP = E114.parent
DATA = E114 / "data"
OUT = E114 / "out"
SEED = 114
AREAS = {"NCR": "metro_manila", "BL": "balance_luzon", "VIS": "visayas", "MIN": "mindanao"}
LEADS = (1, 2, 3, 4, 5, 6)
BREAK = None                      # set below (needs qi)
ALPHAS = (1, 3, 10, 30, 100, 300, 1000)
LAGS = (0, 1)
PHIS = (0.0, 0.25, 0.5, 0.75)
MIN_PAIRS, MIN_ORIGINS, MIN_KNOWN_AREA = 12, 3, 2
FOOD_TARGET = 3.0
NEWS = ["N-DIS", "N-SUP", "N-PRI", "N-AST"]
PSA = ["P-FOOD", "P-DFOOD", "P-RICE", "P-PALAY", "P-UNEMP"]
CLIM = ["C-ONI", "C-TC"]
MRG = ["MR", "CROSS"]
SPECS = {"SH-MR": MRG, "SH-N": NEWS, "SH-P": PSA, "SH-C": CLIM, "SH-FULL": MRG + NEWS + PSA + CLIM,
         "SH-FULL-noN": MRG + PSA + CLIM, "SH-FULL-noP": MRG + NEWS + CLIM, "SH-FULL-noC": MRG + NEWS + PSA,
         "PANEL-AE": MRG + NEWS + PSA + CLIM + ["A-NCR", "A-BL", "A-VIS", "A-MIN"]}
CANDIDATES = ["SH-MR", "SH-N", "SH-P", "SH-C", "SH-FULL", "PANEL-AE", "SS-X"]
BASELINES = ["RW", "MA2", "DAMP", "AR1", "ETS", "LR"]
ABLATIONS = ["SH-FULL-noN", "SH-FULL-noP", "SH-FULL-noC"]
MODELS = BASELINES + CANDIDATES + ABLATIONS
EVAL_FROM = {"a": None, "b": "2003-Q1"}           # (a) as E113 (first eligible origin); (b) targets from 2003-Q1
_OVERRIDE: dict = {}
_SAMPLE = {"name": "b", "file": "sws_area_rounds_full.csv", "drop_phone": False, "adjust": False, "train_pre_only": False}


def qi(s: str) -> int:
    return int(s[:4]) * 4 + int(s[-1]) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def issue(t: int) -> str:
    n = t + 1
    return date(n // 4, (n % 4) * 3 + 1, 1).isoformat()


BREAK = qi("2025-Q2")
LAST_OUTCOME = qi("2026-Q3")
LAST_ORIGIN = qi("2026-Q3")


# ================================================================================================ sample selection
def set_sample(name: str, file: str | None = None, drop_phone: bool = False, adjust: bool = False,
               train_pre_only: bool = False) -> None:
    files = {"a": "../../E110_Hunger_Generalization/data/sws_area_rounds.csv", "b": "sws_area_rounds_full.csv"}
    _SAMPLE.update(name=name, file=file or files[name], drop_phone=drop_phone, adjust=adjust,
                   train_pre_only=train_pre_only)
    clear_caches()


@functools.lru_cache(maxsize=1)
def rounds() -> pd.DataFrame:
    if "rounds" in _OVERRIDE:
        return _OVERRIDE["rounds"]
    r = pd.read_csv((DATA / _SAMPLE["file"]).resolve())
    if "mode" in r and _SAMPLE["drop_phone"]:
        r = r[r["mode"] != "mobile phone"]
    rows = []
    for x in r.itertuples():
        for a, col in AREAS.items():
            h = getattr(x, col)
            if pd.isna(h):
                continue
            moe = float(x.area_moe_bl if a == "BL" else x.area_moe_other)
            rows.append({"area": a, "q": qi(x.quarter), "H": float(h), "published": str(x.published)[:10],
                         "R": (moe / 1.959964) ** 2})
    return pd.DataFrame(rows)


@functools.lru_cache(maxsize=200000)
def known(iss: str, area: str) -> tuple:
    r = rounds()
    r = r[(r["area"] == area) & (r["published"] < iss)]
    s = tuple(sorted((int(q), float(g["H"].mean()), float(g["R"].mean() / len(g))) for q, g in r.groupby("q")))
    if _SAMPLE["adjust"]:
        s = _adjusted(s)
    return s


def _adjusted(s: tuple) -> tuple:
    """Break-adjusted series (Phase 2b): post-break readings minus delta = post-break mean - mean of the last 4
    pre-break readings (assumes the whole mean change at the break is design). Applied once >= 2 post-break known."""
    post = [h for q, h, _ in s if q >= BREAK]
    pre = [h for q, h, _ in s if q < BREAK][-4:]
    if len(post) < 2 or not pre:
        return s
    d = float(np.mean(post) - np.mean(pre))
    return tuple((q, h - d if q >= BREAK else h, r) for q, h, r in s)


def adj_delta(iss: str, area: str) -> float:
    if not _SAMPLE["adjust"]:
        return 0.0
    r = rounds()
    r = r[(r["area"] == area) & (r["published"] < iss)]
    s = sorted((int(q), float(g["H"].mean())) for q, g in r.groupby("q"))
    post = [h for q, h in s if q >= BREAK]
    pre = [h for q, h in s if q < BREAK][-4:]
    return float(np.mean(post) - np.mean(pre)) if len(post) >= 2 and pre else 0.0


def outcome(q: int, area: str) -> float | None:
    r = rounds()
    g = r[(r["area"] == area) & (r["q"] == q)]
    return float(g["H"].mean()) if len(g) else None


def outcome_var(q: int, area: str) -> float | None:
    r = rounds()
    g = r[(r["area"] == area) & (r["q"] == q)]
    return float(g["R"].mean() / len(g)) if len(g) else None


@functools.lru_cache(maxsize=8)
def scale(area: str) -> float:
    r = rounds()
    s = r[r["area"] == area].groupby("q")["H"].mean()
    d = [abs(s[q] - s[q - 1]) for q in s.index if q - 1 in s.index]
    return float(np.mean(d))


def anchor(series, target_q: int) -> float:
    if target_q >= BREAK:
        post = [h for q, h, _ in series if q >= BREAK]
        if len(post) >= 2:
            return float(np.mean(post))
        pre = [h for q, h, _ in series if q < BREAK]
        return float(np.mean(pre)) if pre else float(np.mean([h for _, h, _ in series]))
    return float(np.mean([h for _, h, _ in series]))


# ================================================================================================ covariates (§2)
def _avail_month(ym: int, iss: str, day: int = 10) -> bool:
    n = ym + 1
    return date(n // 12, n % 12 + 1, day).isoformat() <= iss


@functools.lru_cache(maxsize=1)
def cpi_series() -> dict:
    c = pd.read_csv(DATA / "cov_cpi.csv")
    c = c[c["geolocation"] == "PHILIPPINES"]
    out = {}
    for key, com in (("food", "01.1 - FOOD"), ("rice", "01.1.1.12 - Rice")):
        s = c[c["commodity_description"] == com].set_index("ym")["yoy"].dropna().sort_index()
        out[key] = s
    return out


def cpi_feats(iss: str) -> dict:
    out = {}
    for key, s in cpi_series().items():
        s = _OVERRIDE.get(("cpi", key), s)
        av = [m for m in s.index if _avail_month(int(m), iss)]
        if len(av) < 2:
            out[key] = (np.nan, np.nan)
            continue
        m = max(av)
        now = float(s.loc[[x for x in (m - 1, m) if x in s.index]].mean())
        prev = [x for x in (m - 4, m - 3) if x in s.index]
        out[key] = (now, now - float(s.loc[prev].mean()) if prev else np.nan)
    return {"P-FOOD": out["food"][0] - FOOD_TARGET, "P-DFOOD": out["food"][1], "P-RICE": out["rice"][0]}


@functools.lru_cache(maxsize=1)
def palay_series() -> pd.Series:
    p = pd.read_csv(DATA / "cov_palay.csv")
    return p.set_index("q")["yoy"]


@functools.lru_cache(maxsize=1)
def unemp_series() -> pd.Series:
    l = pd.read_csv(DATA / "cov_lfs.csv", encoding="latin-1")
    months = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                          "September", "October", "November", "December"])}
    l = l[l["Month"].isin(months)].copy()
    l["ym"] = l["Year"].astype(int) * 12 + l["Month"].map(months)
    l["ur"] = pd.to_numeric(l["Unemployment Rate Both sexes"], errors="coerce")
    return l.dropna(subset=["ur"]).set_index("ym")["ur"].sort_index()


def unemp_feat(iss: str) -> float:
    s = _OVERRIDE.get("unemp", unemp_series())
    av = [m for m in s.index if date((int(m) + 3) // 12, (int(m) + 3) % 12 + 1, 1).isoformat() <= iss]
    if not av:
        return np.nan
    m = max(av)
    prev = [x for x in s.index if m - 13 <= x <= m - 11]
    return float(s.loc[m] - s.loc[prev].mean()) if prev else np.nan


@functools.lru_cache(maxsize=1)
def oni_series() -> pd.Series:
    o = pd.read_csv(DATA / "cov_oni.csv")
    o["ym"] = o["end_year"] * 12 + o["end_month"] - 1
    return o.set_index("ym")["oni"].sort_index()


def oni_feat(iss: str) -> float:
    s = _OVERRIDE.get("oni", oni_series())
    av = [m for m in s.index if _avail_month(int(m), iss)]
    return float(s.loc[max(av)]) if av else np.nan


@functools.lru_cache(maxsize=1)
def tc_series() -> pd.Series:
    t = pd.read_csv(DATA / "cov_ibtracs_par.csv").set_index("q")["tc_par"]
    full = pd.Series(0, index=range(int(t.index.min()), LAST_ORIGIN + 1))
    full.loc[t.index[t.index <= LAST_ORIGIN]] = t[t.index <= LAST_ORIGIN]
    return full


def tc_feat(t: int) -> float:
    s = _OVERRIDE.get("tc", tc_series())
    return float(s.get(t, np.nan) - s.get(t - 4, np.nan))


@functools.lru_cache(maxsize=1)
def news_table() -> pd.DataFrame:
    """GDELT DOC 2.0 coverage shares (2017+), quarterly mean of monthly values, then YoY change; composites as E113."""
    f = DATA / "cov_gdelt_doc.csv"
    if not f.exists():
        return pd.DataFrame()
    g = pd.read_csv(f)
    dcol = [c for c in g.columns if c.lower().startswith("date")][0]
    vcol = [c for c in g.columns if c.lower() == "value"][0]
    g["d"] = pd.to_datetime(g[dcol], errors="coerce")
    g = g.dropna(subset=["d"])
    g["q"] = g["d"].dt.year * 4 + (g["d"].dt.month - 1) // 3
    g["last"] = g["d"]
    w = g.pivot_table(index="q", columns="category", values=vcol, aggfunc="mean").sort_index()
    last = g.groupby("q")["last"].max()
    comp = pd.DataFrame({"dis": w.get("disaster"), "sup": w.get("agri_supply", 0) + w.get("shortage", 0),
                         "pri": w.get("price"), "ast": w.get("assistance")})
    for c in list(comp.columns):
        comp[f"{c}_yoy"] = comp[c] - comp[c].reindex(comp.index - 4).to_numpy()
    comp["last_published"] = last
    return comp


def news_row(q: int, iss: str) -> dict:
    tab = _OVERRIDE.get("news", news_table())
    cols = {"N-DIS": "dis_yoy", "N-SUP": "sup_yoy", "N-PRI": "pri_yoy", "N-AST": "ast_yoy"}
    # quarter q's months are usable from day 1 of the following month: the whole quarter at O(q) and after
    if not len(tab) or q not in tab.index or issue(q) > iss:
        return {k: np.nan for k in cols}
    return {k: float(tab.loc[q, v]) for k, v in cols.items()}


def palay_feat(t: int) -> float:
    s = _OVERRIDE.get("palay", palay_series())
    v = s.get(t - 1, np.nan)
    return -float(v) if pd.notna(v) else np.nan


# ================================================================================================ features
def features(t: int, k: int, area: str, iss: str | None = None) -> dict | None:
    iss = iss or issue(t)
    s = known(iss, area)
    if not s:
        return None
    hl, ql = s[-1][1], s[-1][0]
    x = {"h_last": hl, "q_last": ql, "MR": hl - anchor(s, t + k), "CROSS": float(t + k >= BREAK and ql < BREAK)}
    for L in LAGS:
        x.update({f"{c}@{L}": v for c, v in news_row(t - L, iss).items()})
    x.update(cpi_feats(iss))
    x.update({"P-PALAY": palay_feat(t), "P-UNEMP": unemp_feat(iss), "C-ONI": oni_feat(iss), "C-TC": tc_feat(t)})
    for a in AREAS:
        x[f"A-{a}"] = float(a == area)
    return x


@functools.lru_cache(maxsize=400000)
def _feat(t: int, k: int, area: str) -> tuple:
    f = features(t, k, area)
    return tuple(sorted(f.items())) if f is not None else ()


def feat(t: int, k: int, area: str) -> dict | None:
    f = _feat(t, k, area)
    return dict(f) if f else None


@functools.lru_cache(maxsize=8192)
def pairs(t: int, k: int, iss: str | None = None) -> pd.DataFrame:
    iss = iss or issue(t)
    rows = []
    for a in AREAS:
        kn = {q: h for q, h, _ in known(iss, a)}
        for tp in range(qi("1998-Q3"), t):
            q = tp + k
            if q not in kn or (_SAMPLE["train_pre_only"] and q >= BREAK):
                continue
            x = feat(tp, k, a)
            if x is None:
                continue
            rows.append({"area": a, "t": tp, "q": q, "y": kn[q], "dy": kn[q] - x["h_last"], **x})
    return pd.DataFrame(rows)


def eligible(t: int, k: int, iss: str | None = None) -> bool:
    iss = iss or issue(t)
    tr = pairs(t, k, iss)
    return (len(tr) >= MIN_PAIRS and tr["t"].nunique() >= MIN_ORIGINS
            and all(len(known(iss, a)) >= MIN_KNOWN_AREA for a in AREAS))


# ================================================================================================ fitting
def _cols(model: str, L: int) -> list[str]:
    return [f"{c}@{L}" if c in NEWS else c for c in SPECS[model]]


def _matrix(tr: pd.DataFrame, cols) -> np.ndarray:
    return np.nan_to_num(tr[cols].to_numpy(float), nan=0.0)


def _ridge_fit(X: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    s = np.sqrt(np.mean(X ** 2, axis=0))
    s[s == 0] = 1.0
    Z = X / s
    return np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ y) / s


@functools.lru_cache(maxsize=40000)
def fit_sh(model: str, t: int, k: int, iss: str | None = None) -> dict | None:
    if not eligible(t, k, iss):
        return None
    tr = pairs(t, k, iss or issue(t))
    lags = LAGS if any(c in NEWS for c in SPECS[model]) else (0,)
    y, groups = tr["dy"].to_numpy(float), tr["t"].to_numpy()
    ug = np.unique(groups)
    best = None
    for L in lags:
        X = _matrix(tr, _cols(model, L))
        for a in ALPHAS:
            err = 0.0
            for g in ug:
                m = groups == g
                err += float(np.abs(X[m] @ _ridge_fit(X[~m], y[~m], a) - y[m]).sum())
            key = (round(err, 9), -a, L)
            if best is None or key < best[0]:
                best = (key, a, L)
    _, a, L = best
    cols = _cols(model, L)
    return {"alpha": a, "lag": L, "cols": cols, "beta": _ridge_fit(_matrix(tr, cols), y, a)}


@functools.lru_cache(maxsize=40000)
def fit_lr(t: int, k: int, iss: str | None = None) -> dict:
    tr = pairs(t, k, iss or issue(t))
    cols = _cols("SH-FULL", 0)
    if len(tr) < len(cols) + 2:
        return {"beta": None, "cols": cols}
    X = np.column_stack([np.ones(len(tr)), _matrix(tr, cols)])
    b, *_ = np.linalg.lstsq(X, tr["dy"].to_numpy(float), rcond=None)
    return {"beta": b, "cols": cols}


def _damp(s, target_q: int, phi: float) -> float:
    hl, ql = s[-1][1], s[-1][0]
    if len(s) < 2 or phi == 0:
        return hl
    slope = (hl - s[-2][1]) / (ql - s[-2][0])
    g = target_q - ql
    return hl + slope * phi * (1 - phi ** g) / (1 - phi)


@functools.lru_cache(maxsize=40000)
def fit_damp(t: int, k: int, iss: str | None = None) -> float:
    tr = pairs(t, k, iss or issue(t))
    best = None
    for phi in PHIS:
        e = [abs(_damp(known(issue(int(r.t)), r.area), int(r.q), phi) - r.y) for r in tr.itertuples()]
        key = (round(float(np.mean(e)), 9), phi)
        if best is None or key < best:
            best = key
    return best[1]


@functools.lru_cache(maxsize=40000)
def fit_ar1(iss: str) -> float:
    xs, ys = [], []
    for a in AREAS:
        s = known(iss, a)
        if not s:
            continue
        m = float(np.mean([h for _, h, _ in s]))
        for (q0, h0, _), (q1, h1, _) in zip(s, s[1:]):
            if q1 - q0 == 1:
                xs.append(h0 - m)
                ys.append(h1 - m)
    if len(xs) < 4:
        return 1.0
    x, y = np.array(xs), np.array(ys)
    return float(np.clip((x @ y) / (x @ x), 0.0, 1.0)) if x @ x > 0 else 1.0


@functools.lru_cache(maxsize=8192)
def pooled_q(iss: str) -> float:
    vals = []
    for a in AREAS:
        s = known(iss, a)
        for (q0, h0, r0), (q1, h1, r1) in zip(s, s[1:]):
            vals.append(((h1 - h0) ** 2 - r0 - r1) / (q1 - q0))
    return max(float(np.mean(vals)) if vals else 0.25, 0.25)


def llr(series, Q: float) -> float:
    q0, a, P = series[0][0], series[0][1], series[0][2]
    for q, h, r in series[1:]:
        P = P + Q * (q - q0)
        K = P / (P + r)
        a, P, q0 = a + K * (h - a), (1 - K) * P, q
    return a


# ------------------------------------------------------------------ structural state space (SS-X)
def _season_row(q: int) -> list[float]:
    s = q % 4
    return [1.0, 0.0, 0.0] if s == 0 else [0.0, 1.0, 0.0] if s == 1 else [0.0, 0.0, 1.0] if s == 2 else [-1.0, -1.0, -1.0]


def _ss_exog_hist(q: int, iss: str) -> list[float]:
    """Exogenous values contemporaneous with outcome quarter q, using only the months released before the issue."""
    ms = [m for m in (q // 4 * 12 + (q % 4) * 3 + i for i in range(3)) if _avail_month(m, iss)]
    o = oni_series().reindex(ms).mean() if ms else np.nan
    f = cpi_series()["food"].reindex(ms).mean() if ms else np.nan
    return [0.0 if pd.isna(o) else float(o), 0.0 if pd.isna(f) else float(f) - FOOD_TARGET]


@functools.lru_cache(maxsize=40000)
def fit_ss(t: int, area: str, iss: str | None = None) -> dict | None:
    """Kalman filter: state [level, g1, g2, g3, b_oni, b_food]; level random walk (pooled Q), seasonal and
    regression coefficients static (diffuse 1e3 prior). Observation variance = published margins."""
    iss = iss or issue(t)
    s = known(iss, area)
    if len(s) < 8:
        return None
    Q = pooled_q(iss)
    a = np.array([s[0][1], 0, 0, 0, 0, 0], float)
    P = np.diag([s[0][2] + 1.0, 1e3, 1e3, 1e3, 1e3, 1e3])
    q_prev = s[0][0] - 1
    for q, h, r in s:
        P = P.copy()
        P[0, 0] += Q * (q - q_prev)
        Z = np.array([1.0] + _season_row(q) + _ss_exog_hist(q, iss))
        f = Z @ P @ Z + r
        K = P @ Z / f
        a = a + K * (h - Z @ a)
        P = P - np.outer(K, Z @ P)
        q_prev = q
    return {"a": a, "P": P, "Q": Q, "q_last": s[-1][0]}


def ss_forecast(t: int, k: int, area: str, iss: str | None = None) -> float | None:
    iss = iss or issue(t)
    m = fit_ss(t, area, iss)
    if m is None:
        return None
    zf = [oni_feat(iss), cpi_feats(iss)["P-FOOD"]]
    zf = [0.0 if pd.isna(v) else v for v in zf]
    Z = np.array([1.0] + _season_row(t + k) + zf)
    return float(Z @ m["a"])


# ================================================================================================ forecasts
def _forecast(model: str, t: int, k: int, area: str, iss: str | None = None) -> dict | None:
    iss_ = iss or issue(t)
    if not eligible(t, k, iss):
        return None
    x = features(t, k, area, iss_) if iss else feat(t, k, area)
    if x is None:
        return None
    s = known(iss_, area)
    hl, ql = x["h_last"], x["q_last"]
    out = {"h_last": hl, "q_last": ql, "true_horizon": t + k - ql}
    if model == "RW":
        f = hl
    elif model == "MA2":
        f = float(np.mean([h for _, h, _ in s[-2:]]))
    elif model == "DAMP":
        f = _damp(s, t + k, fit_damp(t, k, iss))
    elif model == "AR1":
        an = anchor(s, t + k)
        f = an + fit_ar1(iss_) ** (t + k - ql) * (hl - an)
    elif model == "ETS":
        f = llr(s, pooled_q(iss_))
    elif model == "LR":
        m = fit_lr(t, k, iss)
        f = hl if m["beta"] is None else hl + float(m["beta"][0] + np.nan_to_num(np.array([x[c] for c in m["cols"]], float)) @ m["beta"][1:])
    elif model == "SS-X":
        f = ss_forecast(t, k, area, iss)
        if f is None:
            return None
    elif model in SPECS:
        m = fit_sh(model, t, k, iss)
        xv = np.nan_to_num(np.array([x[c] for c in m["cols"]], float), nan=0.0)
        contrib = xv * m["beta"]
        f = hl + float(contrib.sum())
        out.update(alpha=m["alpha"], lag=m["lag"], contrib=dict(zip(m["cols"], map(float, contrib))))
    else:
        raise ValueError(model)
    if _SAMPLE["adjust"]:                       # Phase 2b: back to the published scale
        d = adj_delta(iss_, area)
        if t + k >= BREAK:
            f += d
        if ql >= BREAK:
            out["h_last"] = hl + d
    out["forecast"] = float(f)
    return out


@functools.lru_cache(maxsize=800000)
def forecast(model: str, t: int, k: int, area: str) -> dict | None:
    return _forecast(model, t, k, area)


def band(model: str, t: int, k: int, iss: str | None = None) -> dict:
    """80% half-width: conformal quantile of the model's earlier out-of-sample |errors| (same lead, all areas)."""
    iss = iss or issue(t)
    errs = []
    for a in AREAS:
        kn = {q: h for q, h, _ in known(iss, a)}
        for tp in range(qi("1998-Q3"), t - k + 1):
            if tp + k in kn:
                f = forecast(model, tp, k, a)
                if f is not None:
                    errs.append(abs(outcome(tp + k, a) - f["forecast"]))
    if len(errs) >= 8:
        e = np.sort(errs)
        return {"half": float(e[min(int(math.ceil(0.8 * (len(e) + 1))) - 1, len(e) - 1)]), "n_errors": len(e),
                "method": "conformal"}
    tr = pairs(t, k, iss)
    return {"half": float(1.2816 * np.sqrt(np.mean(tr["dy"] ** 2))) if len(tr) else 8.0, "n_errors": len(errs),
            "method": "fallback"}


@functools.lru_cache(maxsize=80000)
def _band(model: str, t: int, k: int) -> tuple:
    b = band(model, t, k)
    return b["half"], b["n_errors"]


def surge_threshold(area: str, q_last: int, q_target: int) -> float:
    return 1.959964 * math.sqrt(outcome_var(q_last, area) + outcome_var(q_target, area))


def p_surge(f: float, hl: float, thr: float, half: float) -> float:
    sd = max(half / 1.2816, 1e-6)
    return float(1 - 0.5 * (1 + math.erf((thr - (f - hl)) / (sd * math.sqrt(2)))))


def clim_surge_rate(t: int, k: int) -> float:
    tr = pairs(t, k)
    ev = [r.dy > surge_threshold(r.area, int(r.q_last), int(r.q)) for r in tr.itertuples()
          if outcome_var(int(r.q_last), r.area) is not None]
    return float(np.mean(ev)) if ev else 0.0


# ================================================================================================ evaluation
def evaluate(k: int, models=MODELS, with_band: bool = True) -> pd.DataFrame:
    start = EVAL_FROM.get(_SAMPLE["name"])
    rows = []
    for a in AREAS:
        r = rounds()
        for q in sorted(r[r["area"] == a]["q"].unique()):
            q = int(q)
            t = q - k
            if q > LAST_OUTCOME or t < qi("1998-Q3") or (start and q < qi(start)):
                continue
            fs = {m: forecast(m, t, k, a) for m in models}
            if any(v is None for v in fs.values()):
                continue
            y = outcome(q, a)
            hl, ql = fs["RW"]["h_last"], fs["RW"]["q_last"]
            thr = surge_threshold(a, ql, q)
            row = {"area": a, "q": q, "quarter": qs(q), "t": t, "origin": qs(t), "lead": k, "y": y, "h_last": hl,
                   "q_last": qs(ql), "true_horizon": q - ql, "scale": scale(a), "surge_thr": thr,
                   "surge": int(y - hl > thr), "falling": int(y < hl), "post_break": int(q >= BREAK)}
            for m in models:
                row[m] = fs[m]["forecast"]
                if with_band:
                    h, n = _band(m, t, k)
                    row[f"{m}_half"], row[f"{m}_nerr"] = h, n
                    row[f"{m}_psurge"] = p_surge(fs[m]["forecast"], hl, thr, h)
                if m in SPECS:
                    row[f"{m}_lag"] = fs[m]["lag"]
            if with_band:
                row["clim_psurge"] = clim_surge_rate(t, k)
            rows.append(row)
    return pd.DataFrame(rows).sort_values(["q", "area"]).reset_index(drop=True) if rows else pd.DataFrame()


def sloss(df, m):
    return (df[m] - df["y"]).abs() / df["scale"]


def qdiff(df, m, base="RW"):
    return (sloss(df, m) - sloss(df, base)).groupby(df["q"]).mean()


def dm_nw(d, h: int) -> dict:
    """E111 ADDENDUM_1: one-sided HLN-corrected DM, Bartlett (Newey-West) variance, lag h-1."""
    from scipy.stats import t as tdist
    d = np.asarray(d, float)
    n = len(d)
    if n < 3:
        return {"n": n, "p": None}
    dbar = float(d.mean())
    dc = d - dbar
    lag = min(max(h - 1, 0), n - 1)
    v = float(np.dot(dc, dc) / n) + 2 * sum((1 - j / (lag + 1)) * float(np.dot(dc[j:], dc[:-j]) / n) for j in range(1, lag + 1))
    if v <= 0:
        return {"n": n, "mean": dbar, "p": None}
    stat = dbar / math.sqrt(v / n) * math.sqrt(max((n + 1 - 2 * h + h * (h - 1) / n) / n, 1e-9))
    return {"n": n, "mean": dbar, "stat": stat, "p": float(tdist.cdf(stat, df=n - 1))}


def dm(df, m, base, k) -> dict:
    d = qdiff(df, m, base)
    return {**dm_nw(d.to_numpy(), k), "mean_diff": float(d.mean()), "quarters": int(len(d))}


def holm(ps: dict) -> dict:
    items = sorted((p, f) for f, p in ps.items() if p is not None)
    n, out, run = len(items), {}, 0.0
    for i, (p, f) in enumerate(items):
        run = max(run, min(1.0, (n - i) * p))
        out[f] = run
    return out


def metrics(df, m) -> dict:
    e = df[m] - df["y"]
    out = {"rows": len(df), "quarters": int(df["q"].nunique()), "mae": float(e.abs().mean()),
           "rmse": float(np.sqrt((e ** 2).mean())), "mase": float(sloss(df, m).mean()), "bias": float(e.mean())}
    if m != "RW":
        mv = (df[m] - df["h_last"]).abs() >= 0.5
        out["directional_n"] = int(mv.sum())
        out["directional_acc"] = float((np.sign(df.loc[mv, m] - df.loc[mv, "h_last"]) ==
                                        np.sign(df.loc[mv, "y"] - df.loc[mv, "h_last"])).mean()) if mv.any() else None
    if f"{m}_half" in df:
        lo, hi, y = df[m] - df[f"{m}_half"], df[m] + df[f"{m}_half"], df["y"]
        out["coverage80"] = float(((y >= lo) & (y <= hi)).mean())
        out["coverage_n"] = int(len(df))
        out["band_conformal_share"] = float((df[f"{m}_nerr"] >= 8).mean())
        out["interval_score80"] = float(((hi - lo) + 10 * ((lo - y).clip(lower=0) + (y - hi).clip(lower=0))).mean())
    return out


def regime_diffs(df, m) -> dict:
    d = sloss(df, m) - sloss(df, "RW")
    out = {}
    for name, mask in (("surge", df["surge"] == 1), ("falling", df["falling"] == 1), ("post_break", df["post_break"] == 1)):
        out[name] = {"rows": int(mask.sum()), "mean_scaled_diff": float(d[mask].mean()) if mask.any() else None}
    bl = df[df["area"] == "BL"]
    out["BL"] = {"rows": len(bl), "mae": float((bl[m] - bl["y"]).abs().mean()), "mae_rw": float((bl["RW"] - bl["y"]).abs().mean())}
    return out


def decide(df, m, k, holm_p) -> dict:
    mt, mr, rg = metrics(df, m), metrics(df, "RW"), regime_diffs(df, m)
    c = {"R1": mt["quarters"] >= 8,
         "R2": mt["mase"] < mr["mase"] and holm_p is not None and holm_p < 0.10,
         "R3": mt.get("coverage80") is not None and 0.70 <= mt["coverage80"] <= 0.90,
         "R4": all(rg[x]["mean_scaled_diff"] is None or rg[x]["mean_scaled_diff"] <= 0 for x in ("surge", "falling", "post_break"))
               and rg["BL"]["mae"] <= rg["BL"]["mae_rw"]}
    return {"criteria": c, "failed": [x for x, v in c.items() if not v], "reliable": all(c.values()), "regimes": rg}


def surge_metrics(df, m) -> dict:
    y = df["surge"].to_numpy(int)
    p = df[f"{m}_psurge"].to_numpy(float)
    c = p >= 0.5
    tp, fp, fn = int((c & (y == 1)).sum()), int((c & (y == 0)).sum()), int((~c & (y == 1)).sum())
    return {"events": int(y.sum()), "rows": len(y), "alerts": int(c.sum()), "hits": tp, "false_alarms": fp,
            "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
            "brier": float(np.mean((p - y) ** 2)), "brier_clim": float(np.mean((df["clim_psurge"] - y) ** 2)),
            "brier_rw": float(np.mean((df["RW_psurge"] - y) ** 2))}


def brier_boot_p(df, m, ref, B: int = 2000) -> float:
    y = df["surge"].to_numpy(float)
    d = ((df[f"{m}_psurge"] - y) ** 2 - (df[ref] - y) ** 2).groupby(df["q"]).mean().to_numpy()
    rng = np.random.default_rng(SEED)
    return float((np.array([rng.choice(d, len(d)).mean() for _ in range(B)]) >= 0).mean())


def mcs(L: pd.DataFrame, k: int, alpha: float = 0.10, B: int = 2000) -> dict:
    rng = np.random.default_rng(SEED)
    X = L.to_numpy(float)
    n = len(X)
    b = min(max(k, 2), n)
    starts = np.arange(n - b + 1)
    idx = [np.concatenate([np.arange(s, s + b) for s in rng.choice(starts, int(math.ceil(n / b)))])[:n] for _ in range(B)]
    models, alive, pvals, running = list(L.columns), list(range(L.shape[1])), {}, 0.0
    while len(alive) > 1:
        S = X[:, alive]
        dbar = S.mean(0) - S.mean()
        boots = np.array([(S[i].mean(0) - S[i].mean()) - dbar for i in idx])
        sd = boots.std(0)
        sd[sd == 0] = 1e-12
        tstat = dbar / sd
        p = float(((boots / sd).max(1) >= tstat.max()).mean())
        running = max(running, p)
        worst = alive[int(np.argmax(tstat))]
        pvals[models[worst]] = running
        if p >= alpha:
            break
        alive.remove(worst)
    for i in alive:
        pvals.setdefault(models[i], 1.0)
    return {"included": [models[i] for i in alive], "mcs_p": pvals, "block": b}


def block_boot_spearman(x, y, block: int = 4, B: int = 2000) -> dict:
    """Spearman rho with a moving-block bootstrap one-sided p (share of resampled rho <= 0)."""
    from scipy.stats import spearmanr
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    n = len(x)
    if n < 8:
        return {"n": n, "rho": None, "p_block": None}
    rho = float(spearmanr(x, y).statistic)
    rng = np.random.default_rng(SEED)
    starts = np.arange(n - block + 1)
    rs = []
    for _ in range(B):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.choice(starts, int(math.ceil(n / block)))])[:n]
        rs.append(spearmanr(x[idx], y[idx]).statistic)
    rs = np.nan_to_num(np.array(rs))
    return {"n": n, "rho": rho, "p_block": float((rs <= 0).mean())}


def clear_caches() -> None:
    for f in (rounds, known, scale, cpi_series, palay_series, unemp_series, oni_series, tc_series, news_table, _feat,
              pairs, fit_sh, fit_lr, fit_damp, fit_ar1, pooled_q, fit_ss, forecast, _band):
        f.cache_clear()


def sha256(p) -> str:
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(p, o) -> None:
    import json

    def plain(v):
        if isinstance(v, dict):
            return {str(a): plain(b) for a, b in v.items()}
        if isinstance(v, (list, tuple)):
            return [plain(b) for b in v]
        if isinstance(v, (np.bool_,)):
            return bool(v)
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return None if np.isnan(v) else float(v)
        if isinstance(v, float) and math.isnan(v):
            return None
        return v
    Path(p).write_text(json.dumps(plain(o), indent=1), encoding="utf-8", newline="\n")

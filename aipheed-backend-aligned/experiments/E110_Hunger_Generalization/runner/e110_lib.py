"""E110 library (PROTOCOL.md): SWS hunger forecasts for Balance Luzon and the 4-area generalization panel.

Vintages: an area-quarter value known at issue date O(t) is the mean of its rounds published before O(t).
Round precision R = (published area margin / 1.96)^2; a quarter with several rounds has variance mean(R)/n.
"""
from __future__ import annotations

import functools
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E110 = HERE.parent
E109R = E110.parent / "E109_Hunger_Forecasting" / "runner"
sys.path.insert(0, str(E109R))
import e109_lib as H9  # noqa: E402

E, np, pd = H9.E, H9.np, H9.pd
OUT = E110 / "out"
AREA_FILE = E110 / "data" / "sws_area_rounds.csv"
EXTRA_FILE = E110 / "data" / "sws_area_rounds_excluded.csv"
AREAS = {"NCR": "metro_manila", "BL": "balance_luzon", "VIS": "visayas", "MIN": "mindanao"}
PANEL_LEADS = (1, 2, 3, 4, 5, 6)
BL_LEADS = (1, 2, 3, 4)
MIN_KNOWN, MIN_PAIRS, MIN_QUARTERS = 6, 8, 8
Q_FLOOR = 0.25
MOE_BL = 4.0
SEED = 110
BASE = ["RW", "MA2", "MEAN"]
STRUCT = ["LLR", "COMB"]
PANEL_METHODS = BASE + STRUCT + ["NAT-R"]
BL_METHODS = PANEL_METHODS + ["LGBM-R", "RIDGE-R"]
NATIONAL = ["C1", "E1", "E2"]
_OPTS = {"voters": False, "const_r": None}


def set_options(voters: bool = False, const_r: float | None = None) -> None:
    """Sensitivities S-VOTERS / S-R4; clears every cache."""
    _OPTS.update(voters=voters, const_r=const_r)
    for f in (rounds, known, forecast, residual_pairs, _pooled_q):
        f.cache_clear()


# ================================================================================================ data
@functools.lru_cache(maxsize=1)
def rounds() -> pd.DataFrame:
    """Long table: one row per (round, area) with H, published date and observation variance R."""
    r = pd.read_csv(AREA_FILE)
    if _OPTS["voters"]:
        x = pd.read_csv(EXTRA_FILE)
        x = x[x["commissioned"].astype(str) == "unclear"].assign(area_moe_bl=6.0, area_moe_other=6.0)
        r = pd.concat([r, x], ignore_index=True)
    rows = []
    for x in r.itertuples():
        for a, col in AREAS.items():
            h = getattr(x, col)
            if pd.isna(h):
                continue
            moe = float(x.area_moe_bl if a == "BL" else x.area_moe_other)
            if _OPTS["const_r"] is not None:
                moe = _OPTS["const_r"]
            rows.append({"area": a, "q": E.qi(x.quarter), "H": float(h), "published": str(x.published)[:10],
                         "R": (moe / 1.959964) ** 2})
    return pd.DataFrame(rows)


@functools.lru_cache(maxsize=20000)
def known(issue: str, area: str) -> tuple[tuple[int, float, float], ...]:
    """(quarter, vintage mean H, variance of that mean) for the area's rounds published before the issue date."""
    r = rounds()
    r = r[(r["area"] == area) & (r["published"] < issue)]
    return tuple(sorted((int(q), float(g["H"].mean()), float(g["R"].mean() / len(g))) for q, g in r.groupby("q")))


def outcome(q: int, area: str) -> float | None:
    r = rounds()
    g = r[(r["area"] == area) & (r["q"] == q)]
    return float(g["H"].mean()) if len(g) else None


def outcome_quarters(area: str = "BL") -> list[int]:
    return sorted(int(q) for q in rounds().query("area == @area")["q"].unique())


# ================================================================================================ structural
@functools.lru_cache(maxsize=4096)
def _pooled_q(issue: str) -> float:
    """Q per quarter by moments over consecutive known pairs of all 4 areas: (dH^2 - R_i - R_j)/gap, floor."""
    vals = []
    for a in AREAS:
        s = known(issue, a)
        for (q0, h0, r0), (q1, h1, r1) in zip(s, s[1:]):
            vals.append(((h1 - h0) ** 2 - r0 - r1) / (q1 - q0))
    return max(float(np.mean(vals)) if vals else Q_FLOOR, Q_FLOOR)


def llr(series, Q: float) -> tuple[float, float]:
    """Kalman local level with per-observation variance; returns (filtered level, its variance) at the last quarter."""
    q0, a, P = series[0][0], series[0][1], series[0][2]
    for q, h, r in series[1:]:
        P = P + Q * (q - q0)
        K = P / (P + r)
        a, P, q0 = a + K * (h - a), (1 - K) * P, q
    return a, P


# ================================================================================================ indicator residual pairs
def _ridge(tr: pd.DataFrame, cols, x: pd.Series) -> float:
    from sklearn.linear_model import Ridge
    A = tr[cols].astype(float)
    med = A.median().fillna(0.0)
    A = A.fillna(med)
    keep = [c for c in cols if A[c].nunique() > 1]
    if not keep:
        return float(tr["res"].mean())
    mu, sd = A[keep].mean(), A[keep].std().replace(0, 1.0)
    m = Ridge(alpha=10.0).fit(((A[keep] - mu) / sd).to_numpy(), tr["res"].to_numpy())
    z = ((x[keep].astype(float).fillna(med[keep]) - mu) / sd).to_numpy().reshape(1, -1)
    return float(m.predict(z)[0])


def _lgbm(trees: int):
    import lightgbm as lgb
    return lgb.LGBMRegressor(objective="regression", n_estimators=trees, learning_rate=0.05, max_depth=1, num_leaves=2,
                             min_child_samples=3, reg_lambda=5.0, deterministic=True, force_row_wise=True,
                             feature_pre_filter=False, random_state=SEED, n_jobs=1, verbose=-1, boost_from_average=False)


def _lgbm_trees(tr: pd.DataFrame, k: int) -> int:
    qv = sorted(tr["q"].unique())[-4:]
    sc = {}
    for n in (25, 75):
        errs = []
        for q in qv:
            fit, hold = tr[tr["q"] <= q - k - 1], tr[tr["q"] == q]
            if len(fit) < 4 or not len(hold):
                continue
            m = _lgbm(n).fit(fit[E.COLUMNS].astype(float), fit["res"].to_numpy())
            errs += list(np.abs(m.predict(hold[E.COLUMNS].astype(float)) - hold["res"].to_numpy()))
        sc[n] = float(np.mean(errs)) if errs else float("inf")
    return min((25, 75), key=lambda n: (round(sc[n], 9), n))


@functools.lru_cache(maxsize=256)
def residual_pairs(t: int, k: int, areas: tuple[str, ...]) -> pd.DataFrame:
    """(origin t' < t, area, target t'+k) with the target vintage known at O(t); res = target - LLR forecast at t'."""
    X = H9.regional_features(k)
    rows = []
    for a in areas:
        kn = {q: h for q, h, _ in known(E.issue(t), a)}
        for tp in range(E.FIRST_ORIGIN, t):
            q = tp + k
            if q not in kn:
                continue
            f = forecast("LLR", tp, k, a)
            if f is None:
                continue
            rows.append({"area": a, "t": tp, "q": q, "res": kn[q] - f["forecast"],
                         **{c: X.loc[tp, c] if tp in X.index else np.nan for c in E.COLUMNS}})
    return pd.DataFrame(rows)


# ================================================================================================ forecasts
@functools.lru_cache(maxsize=50000)
def forecast(method: str, t: int, k: int, area: str = "BL") -> dict | None:
    """Point forecast of the area's hunger in quarter t+k issued at O(t); None when the origin is not eligible."""
    issue = E.issue(t)
    if any(len(known(issue, a)) < MIN_KNOWN for a in AREAS):
        return None
    s = known(issue, area)
    hl = s[-1][1]
    out = {"h_last": hl, "h_last_quarter": E.qs(s[-1][0])}
    if method == "RW":
        f = hl
    elif method == "MA2":
        f = float(np.mean([h for _, h, _ in s[-2:]]))
    elif method == "MEAN":
        f = float(np.mean([h for _, h, _ in s]))
    elif method in ("LLR", "COMB"):
        Q = _pooled_q(issue)
        lev, P = llr(s, Q)
        f = lev if method == "LLR" else (lev + hl) / 2
        out.update(Q=Q, P=P)
    elif method in ("NAT-R", "LGBM-R", "RIDGE-R"):
        base = forecast("LLR", t, k, area)
        areas = tuple(AREAS) if method == "NAT-R" else ("BL",)
        if method != "NAT-R" and area != "BL":
            return None
        tr = residual_pairs(t, k, areas)
        if len(tr) < MIN_PAIRS:
            return None
        x = H9.regional_features(k).loc[t]
        if method == "NAT-R":
            d = _ridge(tr, NATIONAL, x)
        elif method == "RIDGE-R":
            d = _ridge(tr, E.COLUMNS, x)
        else:
            n = _lgbm_trees(tr, k)
            m = _lgbm(n).fit(tr[E.COLUMNS].astype(float), tr["res"].to_numpy())
            xx = pd.DataFrame([x[E.COLUMNS].astype(float)])
            d = float(m.predict(xx)[0])
            out.update(trees=n, gain=dict(zip(E.COLUMNS, m.booster_.feature_importance("gain").astype(float))),
                       shap=dict(zip(E.COLUMNS + ["_base"], map(float, m.booster_.predict(xx, pred_contrib=True)[0]))))
        f = base["forecast"] + d
        out.update(n_pairs=len(tr), residual_pred=d)
    else:
        raise ValueError(method)
    out["forecast"] = float(f)
    return out


def sigma(method: str, t: int, k: int, area: str) -> float:
    kn = {q: h for q, h, _ in known(E.issue(t), area)}
    errs = []
    for tp in range(E.FIRST_ORIGIN, t - k + 1):
        if tp + k in kn:
            f = forecast(method, tp, k, area)
            if f is not None:
                errs.append(kn[tp + k] - f["forecast"])
    if len(errs) >= 4:
        return float(math.sqrt(np.mean(np.square(errs))))
    s = [h for _, h, _ in known(E.issue(t), area)]
    return float(np.std(np.diff(s), ddof=1)) if len(s) > 2 else 4.0


def p_above(f: float, c: float, s: float) -> float:
    return float(1 - 0.5 * (1 + math.erf((c - f) / (max(s, 1e-6) * math.sqrt(2)))))


# ================================================================================================ evaluation
def evaluate(k: int, methods, areas=tuple(AREAS)) -> pd.DataFrame:
    """One row per (target quarter, area) where every listed method has a forecast."""
    rows = []
    for a in areas:
        for q in outcome_quarters(a):
            t = q - k
            if t < E.FIRST_ORIGIN or q > E.LAST_OUTCOME:
                continue
            fs = {m: forecast(m, t, k, a) for m in methods}
            if any(v is None for v in fs.values()):
                continue
            y = outcome(q, a)
            rr = rounds()
            r = {"area": a, "q": q, "quarter": E.qs(q), "t": t, "origin": E.qs(t), "lead": k, "y": y,
                 "h_last": fs["RW"]["h_last"], "h_last_quarter": fs["RW"]["h_last_quarter"],
                 "rising": int(y > fs["RW"]["h_last"])}
            last_q = E.qi(fs["RW"]["h_last_quarter"])
            last_r = rr[(rr["area"] == a) & (rr["q"] == last_q)]["R"].mean()
            r["moe_last"] = float(np.sqrt(last_r) * 1.959964)
            for m in methods:
                f = fs[m]["forecast"]
                s = sigma(m, t, k, a)
                r[m] = f
                r[f"{m}_pB3"] = p_above(f, 20.0, s)
                r[f"{m}_pB4"] = p_above(f, fs["RW"]["h_last"] + r["moe_last"], s)
            kn = [h for _, h, _ in known(E.issue(t), a)]
            r["PERSIST_pB3"] = float(fs["RW"]["h_last"] > 20.0)
            r["CLIM_pB3"] = float(np.mean([h > 20.0 for h in kn]))
            r["PERSIST_pB4"] = 0.0
            ch = np.diff(kn)
            r["CLIM_pB4"] = float(np.mean(ch > r["moe_last"])) if len(ch) else 0.0
            r["yB3"] = int(y > 20.0)
            r["yB4"] = int(y - fs["RW"]["h_last"] > r["moe_last"])
            rows.append(r)
    df = pd.DataFrame(rows)
    return df.sort_values(["q", "area"]).reset_index(drop=True) if len(df) else df


def quarter_diff(df: pd.DataFrame, m: str, base: str = "RW") -> pd.Series:
    d = df.assign(d=(df[m] - df["y"]).abs() - (df[base] - df["y"]).abs())
    return d.groupby("q")["d"].mean()


def decide(df: pd.DataFrame, m: str, k: int, bl: pd.DataFrame) -> dict:
    """PROTOCOL section 3 for method m at lead k. df: rows used for P1/P3-P5 (panel, or BL for BL-only methods)."""
    dq = quarter_diff(df, m)
    nq = len(dq)
    dm = _dm_signed(dq.to_numpy(), k)
    c = {}
    c["P1"] = nq >= MIN_QUARTERS and dq.mean() < 0 and dm["p"] is not None and dm["p"] < 0.10
    mae_bl = float(np.abs(bl[m] - bl["y"]).mean()) if len(bl) else None
    mae_rw = float(np.abs(bl["RW"] - bl["y"]).mean()) if len(bl) else None
    c["P2"] = len(bl) >= MIN_QUARTERS and mae_bl <= mae_rw and mae_bl <= MOE_BL
    qs_ = sorted(dq.index)
    thirds = [qs_[i * len(qs_) // 3:(i + 1) * len(qs_) // 3] for i in range(3)]
    p3a = all(len(x) and dq.loc[x].mean() < 0 for x in thirds)
    rows = df.assign(d=(df[m] - df["y"]).abs() - (df["RW"] - df["y"]).abs())
    p3b = all(len(rows[rows["rising"] == v]) and rows.loc[rows["rising"] == v, "d"].mean() < 0 for v in (0, 1))
    post = dq[dq.index >= E.qi("2025-Q2")]
    p3c = len(post) > 0 and post.mean() < 0
    c["P3"] = bool(p3a and p3b and p3c)
    loo = max(float(dq.drop(q).mean()) for q in qs_) if nq > 1 else float("inf")
    c["P4"] = loo < 0
    last = dq[dq.index.isin(sorted(qs_)[-4:])]
    c["P5"] = len(last) == 4 and last.mean() <= 0
    c["P6"] = False
    if nq < MIN_QUARTERS or len(bl) < MIN_QUARTERS:
        st = "insufficient evidence"
    elif all(c[x] for x in ("P1", "P2", "P3", "P4", "P5")):
        st = "provisional"
    else:
        st = "not reliable"
    return {"status": st, "criteria": c, "failed": [x for x, v in c.items() if not v], "n_quarters": nq,
            "n_bl_quarters": len(bl), "mean_quarter_diff_vs_rw": float(dq.mean()) if nq else None, "dm": dm,
            "mae_bl": mae_bl, "mae_bl_rw": mae_rw, "loo_max_diff": loo,
            "parts": {"thirds": [float(dq.loc[x].mean()) if len(x) else None for x in thirds],
                      "falling": float(rows.loc[rows["rising"] == 0, "d"].mean()) if (rows["rising"] == 0).any() else None,
                      "rising": float(rows.loc[rows["rising"] == 1, "d"].mean()) if (rows["rising"] == 1).any() else None,
                      "post_2025": float(post.mean()) if len(post) else None,
                      "last4": float(last.mean()) if len(last) else None}}


def _dm_signed(d, h: int) -> dict:
    """One-sided HLN-corrected DM test that the mean loss differential d (model minus RW) is below 0."""
    from scipy.stats import t as tdist
    d = np.asarray(d, float)
    n = len(d)
    if n < 3:
        return {"n": n, "p": None}
    dbar = float(d.mean())
    dc = d - dbar
    lag = max(h - 1, 0)
    v = float(np.dot(dc, dc) / n) + 2 * sum(float(np.dot(dc[j:], dc[:-j]) / n) for j in range(1, min(lag, n - 1) + 1))
    if v <= 0:
        return {"n": n, "mean": dbar, "p": 0.0 if dbar < 0 else 1.0}
    stat = dbar / math.sqrt(v / n) * math.sqrt(max((n + 1 - 2 * h + h * (h - 1) / n) / n, 1e-9))
    return {"n": n, "mean": dbar, "stat": stat, "p": float(tdist.cdf(stat, df=n - 1))}


def cont(df: pd.DataFrame, m: str, k: int) -> dict:
    e = df[m] - df["y"]
    dq = (e.abs()).groupby(df["q"]).mean()
    return {"rows": len(df), "quarters": int(df["q"].nunique()), "mae": float(e.abs().mean()),
            "rmse": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean()),
            "mae_block95": H9.block_ci(dq.to_numpy(), k)}


def binary(df: pd.DataFrame, m: str, b: str) -> dict:
    return H9.bin_metrics(df, f"{m}_p{b}", f"y{b}")


def write_json(p, o):
    E.write_json(p, o)


def sha256(p):
    return E.sha256(p)

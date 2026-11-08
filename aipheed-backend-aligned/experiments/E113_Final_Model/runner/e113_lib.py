"""E113 library (PROTOCOL_E113.md + ADDENDUM_1.md): the 4-area SWS hunger panel, dated news composites and CPI features,
the shrinkage-to-persistence ridge family, the baselines, conformal-style bands, surge probabilities and the tests.
SWS vintages and the local-level filter come unchanged from E110; the news corpus and GDELT tags from E112."""
from __future__ import annotations

import functools
import math
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
E113 = HERE.parent
EXP = E113.parent
sys.path.insert(0, str(EXP / "E111_Hunger_Forecast_Audit" / "runner"))
sys.path.insert(0, str(EXP / "E112_Food_Insecurity_Forecasting" / "runner"))
import e111_lib as G  # noqa: E402

E, F, H9, np, pd = G.E, G.F, G.H9, G.np, G.pd
OUT = E113 / "out"
SEED = 113
AREAS = list(F.AREAS)                                        # NCR, BL, VIS, MIN
BREAK_Q = E.qi("2025-Q2")
LEADS = (1, 2, 3, 4, 5, 6)
MIN_PAIRS, MIN_ORIGINS, MIN_KNOWN_AREA = 12, 3, 2
ALPHAS = (1, 3, 10, 30, 100, 300, 1000)
LAGS = (0, 1)
PHIS = (0.0, 0.25, 0.5, 0.75)
FOOD_TARGET = 3.0
NEWS = ["N-DIS", "N-SUP", "N-PRI", "N-AST"]
PSA = ["P-FOOD", "P-DFOOD", "P-RICE"]
SPECS = {"SH-MR": ["MR"], "SH-N": NEWS, "SH-P": PSA, "SH-MRN": ["MR"] + NEWS, "SH-MRP": ["MR"] + PSA,
         "SH-FULL": ["MR"] + NEWS + PSA, "REP-C": ["AGRI-C"], "REP-G": ["AGRI-G"]}
CANDIDATES = ["SH-MR", "SH-N", "SH-P", "SH-MRN", "SH-MRP", "SH-FULL"]
BASELINES = ["RW", "MA2", "DAMP", "AR1", "ETS", "LR"]
REPLICATION = ["REP-C", "REP-G"]
MODELS = BASELINES + CANDIDATES + REPLICATION
SEVERE = re.compile(r"state of calamity|super ?typhoon|signal (no\.? ?|#)?[345]|death toll|dead|killed|patay|nasawi|"
                    r"missing|evacuat|lumikas|damage|pinsala|destroy|wiped out|billion", re.I)
_OVERRIDE: dict = {}                                         # leakage audit / placebo hooks (never used in scoring)


# ================================================================================================ news composites (§2, §3)
def build_composites() -> dict[str, pd.DataFrame]:
    """Quarterly composite shares from the E112 de-duplicated corpus (with severity) and GDELT; no hunger data."""
    import news_indicators as NI
    c = NI.corpus_frame()
    c["severe"] = c["disaster"] & c["title"].astype(str).map(lambda s: bool(SEVERE.search(s)))
    g = NI.gdelt_frame()
    g["severe"] = False
    out = {}
    for src, d in (("C", c), ("G", g)):
        grp = d.groupby("q")
        t = pd.DataFrame({"n": grp.size(), "last_published": grp["published"].max(),
                          "dis": grp["disaster"].mean() + grp["severe"].mean(),
                          "dis_plain": grp["disaster"].mean(), "severe": grp["severe"].mean(),
                          "sup": grp["agri_supply"].mean() + grp["shortage"].mean(), "pri": grp["price"].mean(),
                          "ast": grp["assistance"].mean(), "agri": grp["agri_supply"].mean()}).sort_index()
        for col in ("dis", "dis_plain", "sup", "pri", "ast", "agri"):
            t[f"{col}_yoy"] = t[col].to_numpy() - t[col].reindex(t.index - 4).to_numpy()
        t.index.name = "q"
        t["quarter"] = [E.qs(int(q)) for q in t.index]
        out[src] = t.reset_index()
    return out


@functools.lru_cache(maxsize=4)
def composites(src: str) -> pd.DataFrame:
    t = pd.read_csv(OUT / f"news_composites_{src}.csv")
    t["last_published"] = pd.to_datetime(t["last_published"])
    return t.set_index("q")


def news_row(q: int, issue: str, src: str = "C") -> dict:
    """YoY composites of quarter q if every counted headline was published before the issue date, else NaN."""
    tab = _OVERRIDE.get(("news", src), composites(src))
    cols = {"N-DIS": "dis_yoy", "N-SUP": "sup_yoy", "N-PRI": "pri_yoy", "N-AST": "ast_yoy", "AGRI": "agri_yoy"}
    if q not in tab.index or not tab.loc[q, "last_published"] < pd.Timestamp(issue):
        return {k: np.nan for k in cols}
    return {k: float(tab.loc[q, v]) for k, v in cols.items()}


# ================================================================================================ CPI (§2; day-10 release rule)
@functools.lru_cache(maxsize=1)
def cpi_monthly() -> pd.Series:
    """Calabarzon food CPI YoY (5-province mean) by month index ym = year*12 + month-1 (PSA OpenStat, E40/E41 files)."""
    d = E.data()[0]
    y = d.yoy[d.yoy["commodity"] == "food"]
    return y.groupby("ym")["yoy"].mean().sort_index()


def cpi_available(ym: int, issue: str) -> bool:
    """Month ym is published by day 10 of the following month (PSA releases in the first week)."""
    n = ym + 1
    return date(n // 12, n % 12 + 1, 10).isoformat() <= issue


def cpi_features(issue: str) -> dict:
    s = _OVERRIDE.get("cpi", cpi_monthly())
    av = [m for m in s.index if cpi_available(int(m), issue)]
    if len(av) < 2:
        return {"P-FOOD": np.nan, "P-DFOOD": np.nan, "cpi_last_month": None}
    m = max(av)
    now = float(s.loc[[m - 1, m]].mean()) if m - 1 in s.index else np.nan
    before = float(s.loc[[m - 4, m - 3]].mean()) if (m - 4 in s.index and m - 3 in s.index) else np.nan
    return {"P-FOOD": now - FOOD_TARGET, "P-DFOOD": now - before, "cpi_last_month": f"{m // 12}-{m % 12 + 1:02d}"}


@functools.lru_cache(maxsize=1)
def rice_table() -> pd.Series:
    return H9.regional_features(1)["A3"]


def rice_at(t: int) -> float:
    s = _OVERRIDE.get("rice", rice_table())
    return float(s.loc[t]) if t in s.index else np.nan


def cpi_quarterly() -> pd.Series:
    """Quarter mean of the three monthly food YoY values (complete quarters only); for validation and regimes."""
    s = cpi_monthly()
    q = pd.Series(s.values, index=[int(m) // 12 * 4 + (int(m) % 12) // 3 for m in s.index])
    g = q.groupby(level=0)
    return g.mean()[g.size() == 3]


# ================================================================================================ SWS panel (§1)
def rounds() -> pd.DataFrame:
    return _OVERRIDE.get("rounds", F.rounds())


@functools.lru_cache(maxsize=50000)
def known(issue: str, area: str) -> tuple:
    r = rounds()
    r = r[(r["area"] == area) & (r["published"] < issue)]
    return tuple(sorted((int(q), float(g["H"].mean()), float(g["R"].mean() / len(g))) for q, g in r.groupby("q")))


def outcome(q: int, area: str) -> float | None:
    return F.outcome(q, area)


@functools.lru_cache(maxsize=8)
def scale(area: str) -> float:
    s = dict((q, h) for q, h, _ in known("9999-12-31", area))
    d = [abs(s[q] - s[q - 1]) for q in s if q - 1 in s]
    return float(np.mean(d))


def anchor(series, target_q: int) -> float:
    if target_q >= BREAK_Q:
        post = [h for q, h, _ in series if q >= BREAK_Q]
        if len(post) >= 2:
            return float(np.mean(post))
        pre = [h for q, h, _ in series if q < BREAK_Q]
        return float(np.mean(pre)) if pre else float(np.mean([h for _, h, _ in series]))
    return float(np.mean([h for _, h, _ in series]))


# ================================================================================================ features at one origin
def features(t: int, k: int, area: str, issue: str | None = None) -> dict | None:
    """Every feature of (origin t, lead k, area) as known at the issue date (default O(t)); None if no reading known."""
    issue = issue or E.issue(t)
    s = known(issue, area)
    if not s:
        return None
    hl, ql = s[-1][1], s[-1][0]
    x = {"h_last": hl, "q_last": ql, "MR": hl - anchor(s, t + k)}
    for L in LAGS:
        for src in ("C", "G"):
            nr = news_row(t - L, issue, src)
            if src == "C":
                x.update({f"{c}@{L}": nr[c] for c in NEWS})
                x[f"AGRI-C@{L}"] = nr["AGRI"]
            else:
                x[f"AGRI-G@{L}"] = nr["AGRI"]
    c = cpi_features(issue)
    x.update({"P-FOOD": c["P-FOOD"], "P-DFOOD": c["P-DFOOD"], "P-RICE": rice_at(t)})
    return x


@functools.lru_cache(maxsize=200000)
def _feat(t: int, k: int, area: str) -> tuple:
    f = features(t, k, area)
    return tuple(sorted(f.items())) if f is not None else ()


def feat(t: int, k: int, area: str) -> dict | None:
    f = _feat(t, k, area)
    return dict(f) if f else None


@functools.lru_cache(maxsize=4096)
def pairs(t: int, k: int, issue: str | None = None) -> pd.DataFrame:
    """Pooled training pairs (§4): every area, origin t' < t, target t'+k published before the issue date."""
    issue = issue or E.issue(t)
    rows = []
    for a in AREAS:
        kn = {q: h for q, h, _ in known(issue, a)}
        for tp in range(E.FIRST_ORIGIN, t):
            q = tp + k
            if q not in kn:
                continue
            x = feat(tp, k, a)
            if x is None:
                continue
            rows.append({"area": a, "t": tp, "q": q, "y": kn[q], "dy": kn[q] - x["h_last"], **x})
    return pd.DataFrame(rows)


def eligible(t: int, k: int, issue: str | None = None) -> bool:
    issue = issue or E.issue(t)
    tr = pairs(t, k, issue)
    return (len(tr) >= MIN_PAIRS and tr["t"].nunique() >= MIN_ORIGINS
            and all(len(known(issue, a)) >= MIN_KNOWN_AREA for a in AREAS))


# ================================================================================================ fitting
def _cols(model: str, L: int) -> list[str]:
    out = []
    for c in SPECS[model]:
        out.append(f"{c}@{L}" if c in NEWS else (f"AGRI-C@0" if c == "AGRI-C" else f"AGRI-G@0" if c == "AGRI-G" else c))
    return out


def _ridge_fit(X: np.ndarray, y: np.ndarray, alpha: float):
    s = np.sqrt(np.mean(X ** 2, axis=0))
    s[s == 0] = 1.0
    Z = X / s
    beta = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ y)
    return beta / s


def _matrix(tr: pd.DataFrame, cols) -> np.ndarray:
    return np.nan_to_num(tr[cols].to_numpy(float), nan=0.0)                          # ADDENDUM_1 item 1


@functools.lru_cache(maxsize=20000)
def fit_sh(model: str, t: int, k: int, issue: str | None = None) -> dict | None:
    """Ridge without intercept on dy; alpha and news lag by leave-one-origin-out inside the training pairs."""
    tr = pairs(t, k, issue or E.issue(t))
    if not eligible(t, k, issue):
        return None
    lags = LAGS if any(c in NEWS for c in SPECS[model]) else (0,)
    y, groups = tr["dy"].to_numpy(float), tr["t"].to_numpy()
    best = None
    for L in lags:
        X = _matrix(tr, _cols(model, L))
        for a in ALPHAS:
            err = 0.0
            for g in np.unique(groups):
                m = groups == g
                b = _ridge_fit(X[~m], y[~m], a)
                err += float(np.abs(X[m] @ b - y[m]).sum())
            key = (round(err, 9), -a, L)
            if best is None or key < best[0]:
                best = (key, a, L)
    _, a, L = best
    cols = _cols(model, L)
    return {"alpha": a, "lag": L, "cols": cols, "beta": _ridge_fit(_matrix(tr, cols), y, a), "n_pairs": len(tr)}


@functools.lru_cache(maxsize=20000)
def fit_lr(t: int, k: int, issue: str | None = None) -> dict | None:
    tr = pairs(t, k, issue or E.issue(t))
    cols = _cols("SH-FULL", 0)
    if len(tr) < len(cols) + 2:
        return {"beta": None, "cols": cols}
    X = np.column_stack([np.ones(len(tr)), _matrix(tr, cols)])
    b, *_ = np.linalg.lstsq(X, tr["dy"].to_numpy(float), rcond=None)
    return {"beta": b, "cols": cols}


@functools.lru_cache(maxsize=20000)
def fit_damp(t: int, k: int, issue: str | None = None) -> float:
    tr = pairs(t, k, issue or E.issue(t))
    best = None
    for phi in PHIS:
        e = []
        for r in tr.itertuples():
            s = known(E.issue(int(r.t)), r.area)
            e.append(abs(_damp(s, int(r.q), phi) - r.y))
        key = (round(float(np.mean(e)), 9), phi)
        if best is None or key < best:
            best = key
    return best[1]


def _damp(s, target_q: int, phi: float) -> float:
    hl, ql = s[-1][1], s[-1][0]
    if len(s) < 2 or phi == 0:
        return hl
    slope = (hl - s[-2][1]) / (ql - s[-2][0])
    g = target_q - ql
    return hl + slope * phi * (1 - phi ** g) / (1 - phi)


@functools.lru_cache(maxsize=20000)
def fit_ar1(issue: str) -> float:
    xs, ys = [], []
    for a in AREAS:
        s = known(issue, a)
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


# ================================================================================================ forecasts
def _forecast(model: str, t: int, k: int, area: str, issue: str | None = None) -> dict | None:
    issue_ = issue or E.issue(t)
    if not eligible(t, k, issue):
        return None
    x = features(t, k, area, issue_) if issue else feat(t, k, area)
    if x is None:
        return None
    s = known(issue_, area)
    hl, ql = x["h_last"], x["q_last"]
    out = {"h_last": hl, "q_last": ql, "true_horizon": t + k - ql}
    if model == "RW":
        f = hl
    elif model == "MA2":
        f = float(np.mean([h for _, h, _ in s[-2:]]))
    elif model == "DAMP":
        phi = fit_damp(t, k, issue)
        f = _damp(s, t + k, phi)
        out["phi"] = phi
    elif model == "AR1":
        rho = fit_ar1(issue_)
        g = t + k - ql
        an = anchor(s, t + k)
        f = an + rho ** g * (hl - an)
        out["rho"] = rho
    elif model == "ETS":
        lev, _ = F.llr(s, _pooled_q(issue_))
        f = lev
    elif model == "LR":
        m = fit_lr(t, k, issue)
        if m["beta"] is None:
            f = hl
        else:
            xv = np.nan_to_num(np.array([x[c] for c in m["cols"]], float), nan=0.0)
            f = hl + float(m["beta"][0] + xv @ m["beta"][1:])
    elif model in SPECS:
        m = fit_sh(model, t, k, issue)
        xv = np.nan_to_num(np.array([x[c] for c in m["cols"]], float), nan=0.0)
        contrib = xv * m["beta"]
        f = hl + float(contrib.sum())
        out.update(alpha=m["alpha"], lag=m["lag"], contrib=dict(zip(m["cols"], map(float, contrib))))
    else:
        raise ValueError(model)
    out["forecast"] = float(f)
    return out


@functools.lru_cache(maxsize=4096)
def _pooled_q(issue: str) -> float:
    vals = []
    for a in AREAS:
        s = known(issue, a)
        for (q0, h0, r0), (q1, h1, r1) in zip(s, s[1:]):
            vals.append(((h1 - h0) ** 2 - r0 - r1) / (q1 - q0))
    return max(float(np.mean(vals)) if vals else F.Q_FLOOR, F.Q_FLOOR)


@functools.lru_cache(maxsize=400000)
def forecast(model: str, t: int, k: int, area: str) -> dict | None:
    return _forecast(model, t, k, area)


def band(model: str, t: int, k: int, issue: str | None = None) -> dict:
    """80% half-width (§5): conformal quantile of earlier out-of-sample |errors| (same model, lead; all areas)."""
    issue = issue or E.issue(t)
    errs = []
    for a in AREAS:
        kn = {q: h for q, h, _ in known(issue, a)}
        for tp in range(E.FIRST_ORIGIN, t - k + 1):
            if tp + k in kn:
                f = forecast(model, tp, k, a)
                if f is not None:
                    errs.append(abs(kn[tp + k] - f["forecast"]))
    if len(errs) >= 8:
        e = np.sort(errs)
        return {"half": float(e[min(int(math.ceil(0.8 * (len(e) + 1))) - 1, len(e) - 1)]), "n_errors": len(e),
                "method": "conformal"}
    tr = pairs(t, k, issue)
    return {"half": float(1.2816 * np.sqrt(np.mean(tr["dy"] ** 2))), "n_errors": len(errs), "method": "fallback"}


@functools.lru_cache(maxsize=40000)
def _band(model: str, t: int, k: int) -> float:
    return band(model, t, k)["half"]


def surge_threshold(area: str, q_last: int, q_target: int) -> float:
    full = {q: r for q, _, r in known("9999-12-31", area)}
    return 1.959964 * math.sqrt(full[q_last] + full[q_target])


def p_surge(f: float, hl: float, thr: float, half: float) -> float:
    sd = max(half / 1.2816, 1e-6)
    return float(1 - 0.5 * (1 + math.erf((thr - (f - hl)) / (sd * math.sqrt(2)))))


def clim_surge_rate(t: int, k: int) -> float:
    tr = pairs(t, k)
    ev = [r.dy > surge_threshold(r.area, int(r.q_last), int(r.q)) for r in tr.itertuples()]
    return float(np.mean(ev)) if ev else 0.0


# ================================================================================================ evaluation
def evaluate(k: int, models=MODELS, with_band: bool = True) -> pd.DataFrame:
    rows = []
    for a in AREAS:
        for q in sorted({q for q, _, _ in known("9999-12-31", a)}):
            t = q - k
            if t < E.FIRST_ORIGIN or q > E.LAST_OUTCOME:
                continue
            fs = {m: forecast(m, t, k, a) for m in models}
            if any(v is None for v in fs.values()):
                continue
            y = outcome(q, a)
            hl, ql = fs["RW"]["h_last"], fs["RW"]["q_last"]
            thr = surge_threshold(a, ql, q)
            r = {"area": a, "q": q, "quarter": E.qs(q), "t": t, "origin": E.qs(t), "lead": k, "y": y, "h_last": hl,
                 "q_last": E.qs(ql), "true_horizon": q - ql, "scale": scale(a), "surge_thr": thr,
                 "surge": int(y - hl > thr), "falling": int(y < hl), "post_break": int(q >= BREAK_Q)}
            for m in models:
                r[m] = fs[m]["forecast"]
                if with_band:
                    h = _band(m, t, k)
                    r[f"{m}_half"] = h
                    r[f"{m}_psurge"] = p_surge(fs[m]["forecast"], hl, thr, h)
                if m in SPECS:
                    r[f"{m}_alpha"], r[f"{m}_lag"] = fs[m]["alpha"], fs[m]["lag"]
            if with_band:
                r["clim_psurge"] = clim_surge_rate(t, k)
            rows.append(r)
    return pd.DataFrame(rows).sort_values(["q", "area"]).reset_index(drop=True) if rows else pd.DataFrame()


# ================================================================================================ metrics
def sloss(df: pd.DataFrame, m: str) -> pd.Series:
    return (df[m] - df["y"]).abs() / df["scale"]


def qdiff(df: pd.DataFrame, m: str, base: str = "RW") -> pd.Series:
    return (sloss(df, m) - sloss(df, base)).groupby(df["q"]).mean()


def dm(df: pd.DataFrame, m: str, base: str, k: int) -> dict:
    d = qdiff(df, m, base)
    return {**G.dm_nw(d.to_numpy(), k), "mean_diff": float(d.mean()), "quarters": int(len(d))}


def metrics(df: pd.DataFrame, m: str) -> dict:
    e = df[m] - df["y"]
    out = {"rows": len(df), "quarters": int(df["q"].nunique()), "mae": float(e.abs().mean()),
           "rmse": float(np.sqrt((e ** 2).mean())), "mase": float(sloss(df, m).mean()), "bias": float(e.mean())}
    if m != "RW":
        mv = (df[m] - df["h_last"]).abs() >= 0.5
        out["directional_n"] = int(mv.sum())
        out["directional_acc"] = float((np.sign(df.loc[mv, m] - df.loc[mv, "h_last"]) ==
                                        np.sign(df.loc[mv, "y"] - df.loc[mv, "h_last"])).mean()) if mv.any() else None
    if f"{m}_half" in df:
        lo, hi = df[m] - df[f"{m}_half"], df[m] + df[f"{m}_half"]
        y = df["y"]
        out["coverage80"] = float(((y >= lo) & (y <= hi)).mean())
        out["interval_score80"] = float(((hi - lo) + (2 / 0.2) * ((lo - y).clip(lower=0) + (y - hi).clip(lower=0))).mean())
    return out


def regime_diffs(df: pd.DataFrame, m: str) -> dict:
    d = sloss(df, m) - sloss(df, "RW")
    out = {}
    for name, mask in (("surge", df["surge"] == 1), ("falling", df["falling"] == 1), ("post_break", df["post_break"] == 1),
                       ("pre_break", df["post_break"] == 0)):
        out[name] = {"rows": int(mask.sum()), "mean_scaled_diff": float(d[mask].mean()) if mask.any() else None}
    bl = df[df["area"] == "BL"]
    out["BL"] = {"rows": len(bl), "mae": float((bl[m] - bl["y"]).abs().mean()), "mae_rw": float((bl["RW"] - bl["y"]).abs().mean())}
    return out


def surge_metrics(df: pd.DataFrame, m: str) -> dict:
    y = df["surge"].to_numpy(int)
    p = df[f"{m}_psurge"].to_numpy(float)
    c = p >= 0.5
    tp, fp, fn = int((c & (y == 1)).sum()), int((c & (y == 0)).sum()), int((~c & (y == 1)).sum())
    return {"events": int(y.sum()), "rows": len(y), "alerts": int(c.sum()), "hits": tp, "false_alarms": fp,
            "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
            "brier": float(np.mean((p - y) ** 2)), "brier_clim": float(np.mean((df["clim_psurge"] - y) ** 2)),
            "brier_rw": float(np.mean((df["RW_psurge"] - y) ** 2))}


def brier_boot_p(df: pd.DataFrame, m: str, ref_col: str, B: int = 2000) -> float:
    """Paired quarter-bootstrap p that the model's Brier is not below the reference's."""
    y = df["surge"].to_numpy(float)
    d = ((df[f"{m}_psurge"] - y) ** 2 - (df[ref_col] - y) ** 2).groupby(df["q"]).mean().to_numpy()
    rng = np.random.default_rng(SEED)
    bs = np.array([rng.choice(d, len(d)).mean() for _ in range(B)])
    return float((bs >= 0).mean())


def decide(df: pd.DataFrame, m: str, k: int, holm_p: float | None) -> dict:
    mt, mr = metrics(df, m), metrics(df, "RW")
    rg = regime_diffs(df, m)
    c = {"R1": mt["quarters"] >= 8,
         "R2": mt["mase"] < mr["mase"] and holm_p is not None and holm_p < 0.10,
         "R3": mt.get("coverage80") is not None and 0.70 <= mt["coverage80"] <= 0.90,
         "R4": all(rg[x]["mean_scaled_diff"] is None or rg[x]["mean_scaled_diff"] <= 0 for x in ("surge", "falling", "post_break"))
               and rg["BL"]["mae"] <= rg["BL"]["mae_rw"]}
    return {"criteria": c, "failed": [x for x, v in c.items() if not v], "reliable": all(c.values()), "regimes": rg}


def holm(ps: dict) -> dict:
    return G.holm(ps)


def mcs(L: pd.DataFrame, k: int, alpha: float = 0.10, B: int = 2000) -> dict:
    """Hansen Model Confidence Set (T_max) on per-quarter losses (rows = quarters, columns = models)."""
    rng = np.random.default_rng(SEED)
    X = L.to_numpy(float)
    n = len(X)
    b = min(max(k, 2), n)
    starts = np.arange(n - b + 1)
    idx = [np.concatenate([np.arange(s, s + b) for s in rng.choice(starts, int(math.ceil(n / b)))])[:n] for _ in range(B)]
    models = list(L.columns)
    alive = list(range(len(models)))
    pvals, running = {}, 0.0
    while len(alive) > 1:
        S = X[:, alive]
        dbar = S.mean(0) - S.mean()
        boots = np.array([(S[i].mean(0) - S[i].mean()) - dbar for i in idx])
        sd = boots.std(0)
        sd[sd == 0] = 1e-12
        tstat = dbar / sd
        tmax = tstat.max()
        p = float(((boots / sd).max(1) >= tmax).mean())
        running = max(running, p)
        worst = alive[int(np.argmax(tstat))]
        pvals[models[worst]] = running
        if p >= alpha:
            break
        alive.remove(worst)
    for i in alive:
        pvals.setdefault(models[i], 1.0)
    return {"included": [models[i] for i in alive], "mcs_p": pvals, "block": b}


def clear_caches() -> None:
    for f in (known, _feat, pairs, fit_sh, fit_lr, fit_damp, fit_ar1, forecast, _band, _pooled_q, composites,
              cpi_monthly, rice_table, scale):
        f.cache_clear()


def write_json(p, o):
    G.write_json(p, o)


def sha256(p):
    return G.sha256(p)

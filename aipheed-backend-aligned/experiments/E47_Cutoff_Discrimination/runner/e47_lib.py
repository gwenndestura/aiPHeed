"""E47 library (PROTOCOL.md): energy-price inputs, the I7-E component model, the structural logistic models SL-P and
SL-5T, the regularized LightGBM classifier LGBM-C, and training-only threshold selection.

Issue convention: E41/E46 I7 (00:00 on day 1 of quarter t+1; CPI through month 2 of t), cutoff-audited in
runs/cutoff_audit_i7.json. Brent enters only through the 30 days ending 10 days before the issue date.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
E47 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E47.parent / "E46_Rice_Policy" / "runner"))
import e46_i7 as I7  # noqa: E402

M, C, K, L, P2, np, pd = I7.M, I7.C, I7.K, I7.L, I7.P2, I7.np, I7.pd
BRENT_FILE = E47 / "data" / "brent_daily_fred_raw.csv"
ENERGY = ["brent_yoy", "brent_mom3"]
MARGINS = ["mF1", "mF0", "mG1", "mG0", "mH"]
TRIGGERS_SL = {"market": ["rice_whsl_yoy", "brent_yoy"], "climate": ["tc_count", "enso", "palay_yoy"],
               "fish_kill": ["fish_yoy"], "employment": ["ur_yoy"], "ofw_remittance": ["remit_php_yoy", "fx_yoy"]}
SL5_COLS = MARGINS + [c for g in TRIGGERS_SL.values() for c in g]
THRESHOLDS = [0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]
WINDOW_DAYS, LAG_DAYS = 30, 10


# ------------------------------------------------------------------------------------------------ energy
def load_brent() -> pd.Series:
    b = pd.read_csv(BRENT_FILE)
    b["date"] = pd.to_datetime(b["observation_date"])
    s = pd.to_numeric(b["DCOILBRENTEU"], errors="coerce")
    assert b["date"].min() >= pd.Timestamp("2021-01-01"), "study window: no pre-2021 observation"
    return pd.Series(s.to_numpy(), index=b["date"]).dropna()


def _avg(s: pd.Series, end: pd.Timestamp) -> float:
    w = s[(s.index >= end - pd.Timedelta(days=WINDOW_DAYS)) & (s.index < end)]
    return float(w.mean()) if len(w) >= 10 else np.nan


def energy_features(t: int, brent: pd.Series) -> dict:
    """Window = the 30 days ending 10 days before O(t); compared with the same window 1 year and 3 months earlier."""
    end = L.origin(t) - pd.Timedelta(days=LAG_DAYS)
    now, yr, q3 = _avg(brent, end), _avg(brent, end - pd.Timedelta(days=365)), _avg(brent, end - pd.Timedelta(days=91))
    return {"brent_yoy": 100 * (now / yr - 1) if np.isfinite(now) and np.isfinite(yr) else np.nan,
            "brent_mom3": 100 * (now / q3 - 1) if np.isfinite(now) and np.isfinite(q3) else np.nan,
            "brent_window_end": str(end.date())}


def features(d, x, origins, ev=None, brent=None) -> pd.DataFrame:
    ev = M.load_events() if ev is None else ev
    brent = load_brent() if brent is None else brent
    X = M.features(d, x, origins, ev)
    E = pd.DataFrame([{"t": t, **energy_features(t, brent)} for t in origins]).drop(columns=["brent_window_end"])
    return X.merge(E, on="t", how="left")


# ------------------------------------------------------------------------------------------------ I7-E
def forecast_i7e(d, X, B, t, n_jobs=8):
    """E46 I7 with the energy inputs added to both price residuals (everything else identical)."""
    pcols = [c for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g]] + M.POLICY + ENERGY
    hcols = [c for g in P2.ALL_GROUPS if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]
    c = d.cut(t)
    F = L.quarter_F(c).rename(columns={"F": "F_true"})
    HL = L.quarter_F(c, "all_items").rename(columns={"F": "HL_true"})
    FG = F.merge(HL, on=["province_code", "q"]).assign(G_true=lambda f: f["F_true"] - f["HL_true"])
    XB = X.merge(B, on=["t", "province_code"])
    for m in P2.MULTS:
        XB[f"gbase_{m}"] = XB[f"base_{m}"] - XB[f"hl_{m}"]
    tr = XB[XB["t"] + 2 <= t - 1].assign(q=lambda f: f["t"] + 2).merge(FG, on=["province_code", "q"])
    te = XB[XB["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    htr, hte = P2.hunger_frame(X, P2.h_series(d, t, False), t, hcols)
    if (tr["q"].nunique() < P2.MIN_PRICE_Q or len(htr) < P2.MIN_H_PAIRS or not len(hte)
            or te[[f"base_{m}" for m in P2.MULTS]].isna().all().all()):
        return None
    fc = I7.component(tr, te, pcols, "F_true", "base_{}", False, "forward", False, n_jobs)
    gc = I7.component(tr, te, pcols, "G_true", "gbase_{}", False, "forward", False, n_jobs)
    if not (np.isfinite(fc["rmse"]) and np.isfinite(gc["rmse"])):
        return None
    j = fc["oof"].merge(gc["oof"], on=["q", "province_code"], suffixes=("_F", "_G"))
    rho = float(np.corrcoef(j["y_hat_F"] - j["y_true_F"], j["y_hat_G"] - j["y_true_G"])[0, 1]) if len(j) > 2 else 0.0
    rho = 0.0 if not np.isfinite(rho) else rho
    hc = P2.hunger_component(htr, hte, hcols)
    ps = P2.p_price_biv(fc["hat"], gc["hat"], fc["rmse"], gc["rmse"], rho, te["province_code"])
    return {"p": np.asarray(hc["p"] * ps), "threshold": 0.5, "p_price": ps, "p_hunger": hc["p"], "F_hat": fc["hat"],
            "G_hat": gc["hat"], "food_cfg": fc["cfg"], "gap_cfg": gc["cfg"], "food_model": fc["model"],
            "gap_model": gc["model"], "pcols": pcols, "te": te}


# ------------------------------------------------------------------------------------------------ structural frame
def margin_frame(X: pd.DataFrame, B: pd.DataFrame) -> pd.DataFrame:
    """As-of price and hunger margins against the T43 thresholds (points), one row per origin x province."""
    th = L.e40_spec()
    D = X.merge(B, on=["t", "province_code"])
    cf, cg = D["province_code"].map(th["food"]), D["province_code"].map(th["gap"])
    D["mF1"], D["mF0"] = D["base_1.0"] - cf, D["base_0.0"] - cf
    D["mG1"], D["mG0"] = (D["base_1.0"] - D["hl_1.0"]) - cg, (D["base_0.0"] - D["hl_0.0"]) - cg
    D["mH"] = D["H_last"] - th["H"]
    return D


class Std:
    """Median imputation + missing flags + standardisation, fitted on training rows only."""

    def __init__(self, cols):
        self.cols = cols

    def fit(self, X):
        Z = X[self.cols].astype(float)
        self.med = Z.median()
        self.miss = [c for c in self.cols if Z[c].isna().any()]
        D = self._d(Z)
        self.mu, self.sd = D.mean(), D.std(ddof=0).replace(0, 1)
        self.keep = [c for c in D if D[c].std(ddof=0) > 0]
        return self

    def _d(self, Z):
        D = Z.fillna(self.med).fillna(0.0)
        for c in self.miss:
            D[f"{c}__missing"] = Z[c].isna().astype(float)
        return D

    def transform(self, X):
        D = self._d(X[self.cols].astype(float))
        for c in self.keep:
            if c not in D:
                D[c] = 0.0
        return ((D - self.mu) / self.sd)[self.keep]


def make_model(kind: str):
    if kind in ("SL-P", "SL-5T"):
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(C=1.0 if kind == "SL-P" else 0.1, max_iter=5000)
    from lightgbm import LGBMClassifier
    return LGBMClassifier(objective="binary", num_leaves=3, max_depth=2, min_child_samples=8, n_estimators=150,
                          learning_rate=0.03, reg_lambda=10.0, random_state=47, deterministic=True, n_jobs=1,
                          force_row_wise=True, verbosity=-1)


def cols_of(kind: str):
    return MARGINS if kind == "SL-P" else SL5_COLS


def fit_predict(kind, tr, te):
    cols = cols_of(kind)
    s = Std(cols).fit(tr)
    Ztr, Zte = s.transform(tr), s.transform(te)
    m = make_model(kind)
    if kind == "LGBM-C":
        mono = [1 if c in MARGINS else 0 for c in Ztr.columns]
        m.set_params(monotone_constraints=mono)
    m.fit(Ztr, tr["y"].astype(int))
    return m.predict_proba(Zte)[:, 1], m, s


def eligible(tr) -> bool:
    return tr["y"].nunique() == 2 and tr["y"].sum() >= 3 and tr["q"].nunique() >= 6


def inner_threshold(kind, tr) -> tuple[float, int]:
    """Embargoed forward-chaining inside the training pairs: fold q is fitted on targets <= q-3; pooled OOF predictions
    of the last 6 folds choose the cut maximising balanced accuracy (ties: closest to 0.5); 0.5 if the pooled OOF has
    fewer than 3 HIGH or 3 LOW rows."""
    oof = []
    for q, fq in I7.folds(tr["q"].unique(), "forward"):
        fit, hold = tr[tr["q"].isin(fq)], tr[tr["q"] == q]
        if not eligible(fit):
            continue
        p, _, _ = fit_predict(kind, fit, hold)
        oof.append(hold[["y"]].assign(p=p))
    if not oof:
        return 0.5, 0
    o = pd.concat(oof)
    if o["y"].sum() < 3 or (o["y"] == 0).sum() < 3:
        return 0.5, len(o)
    best = max(THRESHOLDS, key=lambda th: (round(C.balanced(o["y"], o["p"] >= th), 10), -abs(th - 0.5)))
    return float(best), len(o)


def forecast_sl(kind, D, d, t):
    lab = K.available_labels(d, t)[["province_code", "q", "y"]]
    tr = D[D["t"] + 2 <= t - 1].assign(q=lambda f: f["t"] + 2).merge(lab, on=["province_code", "q"])
    te = D[D["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    if not eligible(tr):
        return None
    p, m, s = fit_predict(kind, tr, te)
    thr, n_oof = inner_threshold(kind, tr)
    return {"p": p, "threshold": thr, "n_oof": n_oof, "model": m, "std": s, "n_train": int(len(tr)),
            "n_train_HIGH": int(tr["y"].sum()), "te": te}

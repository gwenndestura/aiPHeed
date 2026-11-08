"""LEAD2_ONE_MODEL library (PROTOCOL_ONE_MODEL.md): ONE LightGBM on the combined target T43c across every lead, with
hunger information only as inputs (S0-S3), plus the in-window decision threshold and Platt calibration.

Reused unchanged: the stacked table and features of LEAD2_OPTIMIZATION (l2_lib, a3, a4), labels, baselines, metrics.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ONE = HERE.parent
EXP = ONE.parent
OUT = ONE / "out"
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))
import l2_lib as X  # noqa: E402
import a3 as A3  # noqa: E402
import a4 as A4  # noqa: E402

U, C, FM, B, E, L, np, pd = X.U, X.C, X.FM, X.B, X.E, X.L, X.np, X.pd
SEED = 2030
OTHER = ("NCR", "VIS", "MIN")
DYN = ["h_change", "h_mean4", "h_max4", "h_margin", "h_run"] + [f"{a}_{s}" for a in OTHER for s in ("last", "change")]
MONO = {"A1_food", "A1_gap", "A_mom", "H1", "h_last"}
CANDS = {"S0": dict(dyn=False, offset=False, balanced=False), "S1": dict(dyn=True, offset=False, balanced=False),
         "S2": dict(dyn=True, offset=True, balanced=False), "S3": dict(dyn=True, offset=True, balanced=True)}
TAUS = [round(x, 2) for x in np.arange(0.20, 0.501, 0.05)]


def cols(cand: str) -> list[str]:
    return A4.cols() + (DYN if CANDS[cand]["dyn"] else [])


def grid(cand: str) -> list[dict]:
    g = X.uni_grid() + X.reg_grid()
    if CANDS[cand]["balanced"]:
        g = [dict(c, cw="balanced", id=c["id"] + "b") for c in g]
        g = list({c["id"]: c for c in g}.values())
    return g


# ================================================================================================ inputs
def dynamics(t: int) -> dict:
    """Issue-time SWS dynamics: BL readings and the other three areas' latest readings, published before O(t)."""
    iss = E.issue(t)
    bl = [h for _, h, *_ in C.bl_known(iss)]
    out = {c: np.nan for c in DYN}
    if bl:
        out["h_margin"] = bl[-1] - X.H_LINE
        out["h_mean4"], out["h_max4"] = float(np.mean(bl[-4:])), float(np.max(bl[-4:]))
        side = bl[-1] > X.H_LINE
        run = 0
        for h in reversed(bl):
            if (h > X.H_LINE) != side:
                break
            run += 1
        out["h_run"] = float(run if side else -run)
    if len(bl) >= 2:
        out["h_change"] = bl[-1] - bl[-2]
    for a in OTHER:
        k = [h for _, h, *_ in FM.known(iss, a, "primary")]
        if k:
            out[f"{a}_last"] = k[-1]
        if len(k) >= 2:
            out[f"{a}_change"] = k[-1] - k[-2]
    return out


def build(K: int, d=None, x=None, last_origin=None, w=None, cpi=None, rice=None) -> pd.DataFrame:
    S = U.stack(K) if d is None else U.stack(K, d, x, last_origin, w)
    S = A4.add_onset(X.add_fe(S, d, rice), cpi, None)
    dy = {int(t): dynamics(int(t)) for t in S["t"].unique()}
    for c in DYN:
        S[c] = [dy[int(t)][c] for t in S["t"]]
    return S


# ================================================================================================ model
class One:
    def __init__(self, cfg: dict, cand: str):
        self.cfg, self.cand = cfg, cand
        self.cols, self.use_offset = cols(cand), CANDS[cand]["offset"]
        self.m = self.price_fit = self.const = None

    def _offset(self, rows):
        return B.logit(np.clip(X.struct_prior(rows, self.price_fit), 0.01, 0.99))

    def fit(self, tr: pd.DataFrame, price_fit: pd.DataFrame):
        import lightgbm as lgb
        self.price_fit = price_fit
        y = tr["y"].to_numpy(int)
        if len(set(y.tolist())) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        c = self.cfg
        self.m = lgb.LGBMClassifier(objective="binary", class_weight=c["cw"], learning_rate=c["lr"],
                                    n_estimators=c["trees"], num_leaves=c["leaves"], max_depth=c["depth"],
                                    min_child_samples=c["min_child"], reg_lambda=c["l2"], reg_alpha=c["l1"],
                                    colsample_bytree=c["col"], subsample=c["sub"],
                                    subsample_freq=1 if c["sub"] < 1 else 0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=SEED, n_jobs=1,
                                    verbose=-1, monotone_constraints=[1 if v in MONO else 0 for v in self.cols],
                                    monotone_constraints_method="basic")
        kw = {"init_score": self._offset(tr)} if self.use_offset else {}
        self.m.fit(tr[self.cols].astype(float), y, **kw)
        return self

    def predict(self, te: pd.DataFrame) -> np.ndarray:
        if self.m is None:
            return np.full(len(te), self.const)
        raw = self.m.predict(te[self.cols].astype(float), raw_score=True)
        if self.use_offset:
            raw = raw + self._offset(te)
        return 1 / (1 + np.exp(-raw))


def _ll(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def forecast(S: pd.DataFrame, t: int, cand: str, d=None) -> pd.DataFrame:
    """The candidate at origin t: probability (0.50 rule), in-window tau and Platt-calibrated probability."""
    from sklearn.linear_model import LogisticRegression
    lab = C.known_t43c(t, d)[["province_code", "q", "y"]]
    tr = S[(S["t"] < t) & (S["target_q"] <= t - 1)].rename(columns={"target_q": "q"}).merge(
        lab, on=["province_code", "q"], how="inner")
    pr = U.train_rows(S, t, d)
    te = S[S["t"] == t]
    out = te[["t", "lead", "province_code", "target_q"]].copy()
    if not B.eligible(tr):
        base = float(tr["y"].mean()) if len(tr) else 0.0
        out[f"{cand}_p"], out[f"{cand}_cfg"], out[f"{cand}_tau"], out[f"{cand}_pc"] = base, "base-rate", 0.5, base
        return out
    origins = sorted(tr["t"].unique())[-4:]
    folds = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o], pr[pr["q"] <= o - 1]) for o in origins]
    folds = [f for f in folds if f[0]["q"].nunique() >= 3 and f[0]["y"].nunique() == 2 and len(f[1])]
    G = grid(cand)
    best, inner = G[0], None
    if folds:
        ys = np.concatenate([h["y"].to_numpy(int) for _, h, _ in folds])
        sc, preds = {}, {}
        for c in G:
            ps = np.concatenate([One(c, cand).fit(f, p).predict(h) for f, h, p in folds])
            sc[c["id"]], preds[c["id"]] = _ll(ys, ps), ps
        best = min(G, key=lambda c: (round(sc[c["id"]], 9), G.index(c)))
        inner = (ys, preds[best["id"]])
    p = One(best, cand).fit(tr, pr).predict(te)
    tau, pc = 0.5, p
    if inner is not None and len(set(inner[0].tolist())) == 2:
        ys, ps = inner
        ba = {}
        for tt in TAUS:
            yh = (ps >= tt).astype(int)
            rec = ((yh == 1) & (ys == 1)).sum() / max((ys == 1).sum(), 1)
            spec = ((yh == 0) & (ys == 0)).sum() / max((ys == 0).sum(), 1)
            ba[tt] = (rec + spec) / 2
        tau = max(TAUS, key=lambda tt: (round(ba[tt], 9), tt))
        lr = LogisticRegression(C=1e6).fit(B.logit(ps).reshape(-1, 1), ys)
        pc = lr.predict_proba(B.logit(p).reshape(-1, 1))[:, 1]
    out[f"{cand}_p"], out[f"{cand}_cfg"], out[f"{cand}_tau"], out[f"{cand}_pc"] = p, best["id"], tau, pc
    return out

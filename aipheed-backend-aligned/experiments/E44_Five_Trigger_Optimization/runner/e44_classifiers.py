"""E44 iteration I1 (PROTOCOL.md section 3): five-trigger feature sets, the 132-configuration grid, and nested selection
(blocked leave-one-target-quarter-out inside the training window, cross-fitted Platt, threshold choice).
Data, timing, labels and baselines come unchanged from E43 (e43_lib) and E41 (e41_lib)."""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E44 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E44.parent / "E43_Five_Trigger_Risk" / "runner"))
import e43_lib as K  # noqa: E402

L, np, pd = K.L, K.np, K.pd
TRIGGERS = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
F5_GROUPS = {
    "market": ["F_hat_M1", "F_now", "D_now", "gap_now", "rice_whsl_yoy"],
    "climate": ["tc_count", "tc_count_l1", "enso", "enso_l2", "palay_yoy", "corn_yoy"],
    "fish_kill": ["fish_yoy", "aqua_yoy"],
    "employment": ["ur_yoy", "under_yoy"],
    "ofw_remittance": ["remit_usd_yoy", "remit_php_yoy", "fx_yoy"],
    "hunger_history": ["H_last", "H_age"],
    "news": ["news_market", "news_climate", "news_fish_kill", "news_employment", "news_ofw_remittance", "news_n"],
}
NEWS_OF = {"market": "news_market", "climate": "news_climate", "fish_kill": "news_fish_kill",
           "employment": "news_employment", "ofw_remittance": "news_ofw_remittance"}
F5 = [c for g in F5_GROUPS.values() for c in g]
F5_GOV = [c for g, cs in F5_GROUPS.items() if g != "news" for c in cs]
F5_COMPACT = ["F_hat_M1", "enso", "fish_yoy", "ur_yoy", "remit_php_yoy", "H_last", "news_climate"]
FEATURE_SETS = {"F5": F5, "F5-GOV": F5_GOV, "F5-COMPACT": F5_COMPACT}
THRESHOLDS = [0.2, 0.3, 0.4, 0.5]
MIN_Q, MIN_HIGH = 6, 3


def trigger_of(col: str) -> str | None:
    for g, cs in F5_GROUPS.items():
        if col in cs:
            if g == "news":
                return next((k for k, v in NEWS_OF.items() if v == col), "news_total")
            return g
    return None


def covers_five(cols: list[str]) -> bool:
    return set(TRIGGERS) <= {trigger_of(c) for c in cols}


# ================================================================================================ features
def features(d_full, x_full, origins: list[int]) -> pd.DataFrame:
    X = K.features(d_full, x_full, origins)
    rows = []
    for t in origins:
        cx = K.cut_extra(x_full, t)
        tc = cx["tc"].set_index(["province_code", "q"])["tc_count"]
        en = cx["enso"].set_index(["province_code", "q"])["enso_phase"]
        of = cx["ofw"].drop_duplicates("q").set_index("q")
        php = of["ofw_cash_remit_usd_bn"] * of["fx_usd_php_avg"]
        lf = d_full.cut(t).lfs.set_index(["series", "ym"])["value"]

        def qm(s, q):
            v = [lf.get((s, q // 4 * 12 + (q % 4) * 3 + j), np.nan) for j in range(3)]
            v = [z for z in v if pd.notna(z)]
            return float(np.mean(v)) if v else np.nan

        under_yoy = qm("under", t - 1) - qm("under", t - 5) if t - 5 >= L.FIRST_Q else np.nan
        a, b = php.get(t - 1, np.nan), php.get(t - 5, np.nan)
        remit_php = float(100 * (a / b - 1)) if t - 5 >= L.FIRST_Q and pd.notna(a) and pd.notna(b) and b else np.nan
        for p in L.PROVS:
            rows.append({"t": t, "province_code": p, "tc_count_l1": float(tc.get((p, t - 1), np.nan)),
                         "enso_l2": K.ENSO.get(en.get((p, t - 2)), np.nan), "under_yoy": under_yoy,
                         "remit_php_yoy": remit_php})
    return X.merge(pd.DataFrame(rows), on=["t", "province_code"], how="left")


# ================================================================================================ grid
def grid(feature_sets: dict[str, list[str]]) -> list[dict]:
    out = []
    for fs, (nl, mcs, ne, lam, cw, win) in itertools.product(
            feature_sets, itertools.product([2, 4], [3, 8], [50, 150], [1.0, 10.0], ["none", "balanced"],
                                            ["expanding", "last8"])):
        out.append({"model": "LGBM", "features": fs, "num_leaves": nl, "min_child_samples": mcs, "n_estimators": ne,
                    "reg_lambda": lam, "class_weight": cw, "window": win})
    for fs, (C, cw, win) in itertools.product(feature_sets, itertools.product([0.05, 0.3, 1.0], ["none", "balanced"],
                                                                              ["expanding", "last8"])):
        out.append({"model": "LR", "features": fs, "C": C, "class_weight": cw, "window": win})
    return out


def complexity(c: dict) -> tuple:
    if c["model"] == "LR":
        return (0, c["C"], c["features"] != "F5-COMPACT")
    return (1, c["num_leaves"], c["n_estimators"], -c["min_child_samples"], -c["reg_lambda"])


class LR:
    def __init__(self, cols, C, cw):
        self.cols, self.C, self.cw = cols, C, cw

    def fit(self, tr):
        from sklearn.linear_model import LogisticRegression
        X = tr[self.cols].astype(float)
        self.med = X.median()
        self.miss = [c for c in self.cols if X[c].isna().any()]
        Z = self._design(X)
        self.mu, self.sd = Z.mean(), Z.std(ddof=0).replace(0, 1)
        self.keep = [c for c in Z if Z[c].std(ddof=0) > 0]
        self.m = LogisticRegression(C=self.C, class_weight=None if self.cw == "none" else "balanced", max_iter=5000)
        self.m.fit(((Z - self.mu) / self.sd)[self.keep], tr["y"].astype(int))
        return self

    def _design(self, X):
        Z = X.fillna(self.med).fillna(0.0)
        for c in self.miss:
            Z[f"{c}__missing"] = X[c].isna().astype(float)
        return Z

    def predict(self, te):
        Z = self._design(te[self.cols].astype(float))
        return self.m.predict_proba(((Z - self.mu) / self.sd)[self.keep])[:, 1]

    def contributions(self, te) -> pd.DataFrame:
        Z = ((self._design(te[self.cols].astype(float)) - self.mu) / self.sd)[self.keep]
        c = Z * self.m.coef_[0]
        c.columns = [k.replace("__missing", "") for k in c.columns]
        return c.T.groupby(level=0).sum().T


class GB:
    def __init__(self, cols, cfg):
        self.cols, self.cfg = cols, cfg

    def fit(self, tr):
        from lightgbm import LGBMClassifier
        p = tr["y"].mean()
        spw = (1 - p) / p if self.cfg["class_weight"] == "balanced" else 1.0
        self.m = LGBMClassifier(objective="binary", num_leaves=self.cfg["num_leaves"], max_depth=-1,
                                min_child_samples=self.cfg["min_child_samples"], n_estimators=self.cfg["n_estimators"],
                                learning_rate=0.05, reg_lambda=self.cfg["reg_lambda"], scale_pos_weight=spw,
                                random_state=42, deterministic=True, n_jobs=1, force_row_wise=True, verbosity=-1)
        self.m.fit(tr[self.cols].astype(float), tr["y"].astype(int))
        return self

    def predict(self, te):
        return self.m.predict_proba(te[self.cols].astype(float))[:, 1]

    def contributions(self, te) -> pd.DataFrame:
        c = self.m.booster_.predict(te[self.cols].astype(float), pred_contrib=True)[:, :-1]
        return pd.DataFrame(c, columns=self.cols, index=te.index)


def build(cfg: dict, cols: list[str]):
    return LR(cols, cfg["C"], cfg["class_weight"]) if cfg["model"] == "LR" else GB(cols, cfg)


def windowed(tr: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    if cfg["window"] == "last8":
        qs = sorted(tr["q"].unique())[-8:]
        return tr[tr["q"].isin(qs)]
    return tr


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def platt_fit(p, y):
    from sklearn.linear_model import LogisticRegression
    y = np.asarray(y, int)
    if len(np.unique(y)) < 2:
        return None
    return LogisticRegression(C=1.0, max_iter=2000).fit(_logit(p).reshape(-1, 1), y)


def platt_apply(m, p):
    return np.asarray(p, float) if m is None else m.predict_proba(_logit(p).reshape(-1, 1))[:, 1]


def oof(tr: pd.DataFrame, cfg: dict, cols: list[str]) -> pd.DataFrame:
    """Blocked leave-one-target-quarter-out predictions inside the training window, then cross-fitted Platt."""
    tw = windowed(tr, cfg)
    out = []
    for q in sorted(tw["q"].unique()):
        fit, hold = tw[tw["q"] != q], tw[tw["q"] == q]
        p = build(cfg, cols).fit(fit).predict(hold) if fit["y"].nunique() == 2 else np.full(len(hold), fit["y"].mean())
        out.append(hold[["q", "province_code", "y"]].assign(p_raw=p))
    o = pd.concat(out, ignore_index=True)
    o["p_cal"] = np.nan
    for q in o["q"].unique():
        m = platt_fit(o.loc[o["q"] != q, "p_raw"], o.loc[o["q"] != q, "y"])
        o.loc[o["q"] == q, "p_cal"] = platt_apply(m, o.loc[o["q"] == q, "p_raw"])
    return o


def balanced(y, yh):
    y, yh = np.asarray(y, int), np.asarray(yh, int)
    r1 = ((yh == 1) & (y == 1)).sum() / max((y == 1).sum(), 1)
    r0 = ((yh == 0) & (y == 0)).sum() / max((y == 0).sum(), 1)
    return (r1 + r0) / 2


def evaluate_config(args):
    tr, cfg, cols = args
    o = oof(tr, cfg, cols)
    return float(np.mean((o["p_cal"] - o["y"]) ** 2)), o


def select_and_predict(tr: pd.DataFrame, te: pd.DataFrame, configs: list[dict], sets: dict, n_jobs: int = 8) -> dict:
    """Nested selection (PROTOCOL 3) and the outer prediction for one origin."""
    from joblib import Parallel, delayed
    res = Parallel(n_jobs=n_jobs, backend="loky")(delayed(evaluate_config)((tr, c, sets[c["features"]]))
                                                  for c in configs)
    scores = [r[0] for r in res]
    order = sorted(range(len(configs)), key=lambda i: (round(scores[i], 10), complexity(configs[i])))
    best = order[0]
    cfg, o = configs[best], res[best][1]
    cols = sets[cfg["features"]]
    model = build(cfg, cols).fit(windowed(tr, cfg))
    cal = platt_fit(o["p_raw"], o["y"])
    thr = max(THRESHOLDS, key=lambda th: (round(balanced(o["y"], o["p_cal"] >= th), 10), th == 0.5, th))
    p_raw = model.predict(te)
    return {"config": cfg, "inner_brier": scores[best], "threshold": thr, "p_raw": p_raw,
            "p": platt_apply(cal, p_raw), "model": model, "cols": cols, "platt": cal,
            "inner_top5": [(configs[i], scores[i]) for i in order[:5]]}


def eligible(tr: pd.DataFrame) -> bool:
    return tr["q"].nunique() >= MIN_Q and tr["y"].sum() >= MIN_HIGH and tr["y"].nunique() == 2

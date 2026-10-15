"""E42 library (PROTOCOL.md): drift-variant projections, prequential selection + Platt (PS), GOV/NLP/COMB models,
trigger diagnostics. Data loading, timing, features and scoring are reused unchanged from E41 (e41_lib)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E42 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E42.parent / "E41_Lead2_Audit" / "runner"))
import e41_lib as L  # noqa: E402

np, pd = L.np, L.pd
norm = L.norm
NEWS = L.ROOT / "backend" / "data" / "news_e31" / "fssi_v2_panel.csv"
ARMS = {"M1": 1.0, "M1z": 0.0, "M1h": 0.5}             # drift multiplier; order = tie-break order
GROUPS = {
    "market": ["F_last", "F_now", "HL_now", "gap_now", "mom3", "F_hat_M1", "F_hat_M1z", "D_now"],
    "hunger_sws": ["H_last", "H_chg", "H_age"],
    "climate_supply": ["palay_yoy", "corn_yoy"],
    "fish_supply": ["fish_yoy", "aqua_yoy"],
    "employment": ["ur_last", "ur_yoy", "under_last"],
    "ofw_remittance": [],
    "news": ["news_n"] + [f"news_{k}" for k in L.TRIGGERS] + ["fssi_v2", "fssi_admitted", "fssi_sufficient"],
}
GOV = [f for g in ("market", "hunger_sws", "climate_supply", "fish_supply", "employment") for f in GROUPS[g]]
NLP = GROUPS["news"]
COMB = GOV + NLP
SETS = {"GOV": GOV, "NLP": NLP, "COMB": COMB}
LGBM = dict(objective="binary", num_leaves=4, max_depth=2, min_child_samples=10, n_estimators=100,
            learning_rate=0.05, reg_lambda=5.0, random_state=42, deterministic=True, n_jobs=1, force_row_wise=True,
            verbosity=-1)
MIN_PS_DATES, MIN_PLATT_DATES = 4, 8


# ------------------------------------------------------------------------------------------ projections
def m_point(d: L.Data, t: int, k: int, p: str, mult: float) -> dict:
    """E41 M1 with the trailing drift multiplied by `mult` (1 = M1, 0 = M1z, 0.5 = M1h)."""
    m0 = L.m0_of(t)
    I = L._series(d, p, "food")
    if m0 not in I.index:
        return {"F_hat": np.nan}
    lnI = np.log(I)
    g, sd, n = L.drift_sigma(lnI, m0)
    ms = L.target_months(t, k)
    if n < 6 or any((m - 12) not in I.index or (m - 12) < L.FIRST_YM for m in ms):
        return {"F_hat": np.nan, "n_drift": n}
    g = g * mult
    yo = [100 * (math.exp(lnI[m0] + g * (m - m0)) / I[m - 12] - 1) for m in ms]
    return {"F_hat": float(np.mean(yo)), "sigma": sd, "n_drift": n,
            "s_theory": float(100 * sd * math.sqrt(L.var_factor([m - m0 for m in ms])))}


def m_forecasts(d_full: L.Data, origins: list[int], k: int, mult: float) -> pd.DataFrame:
    """As e41_lib.m1_forecasts, for any drift multiplier (s = max(s_theory, s_track of the arm's own errors))."""
    rows = [{"t": t, "target_q": t + k, "province_code": p, **m_point(d_full.cut(t), t, k, p, mult)}
            for t in origins for p in L.PROVS]
    P = pd.DataFrame(rows)
    out = []
    for t in origins:
        F = L.quarter_F(d_full.cut(t)).set_index(["province_code", "q"])["F"]
        prior = P[P["target_q"] <= t - 1].copy()
        prior["F"] = [F.get((p, q), np.nan) for p, q in zip(prior["province_code"], prior["target_q"])]
        prior = prior.dropna(subset=["F", "F_hat"])
        s_track = float(np.sqrt(np.mean((prior["F"] - prior["F_hat"]) ** 2))) if prior["target_q"].nunique() >= 4 else np.nan
        cur = P[P["t"] == t].copy()
        cur["s"] = np.fmax(cur["s_theory"], np.nan_to_num(s_track, nan=-np.inf))
        cur["p"] = 1 - norm.cdf((L.FPP_THRESHOLD - cur["F_hat"]) / cur["s"])
        out.append(cur)
    return pd.concat(out, ignore_index=True)


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def prequential(d_full: L.Data, arms: dict[str, pd.DataFrame], origins: list[int]) -> pd.DataFrame:
    """PS (PROTOCOL 3): choose the arm with the lowest past mean per-date Brier, then walk-forward Platt."""
    from sklearn.linear_model import LogisticRegression
    out = []
    for t in origins:
        lab = L.fpp_labels(d_full.cut(t))
        lab = lab[lab["q"] <= t - 1].rename(columns={"q": "target_q"})[["province_code", "target_q", "y"]]
        past = {}
        for name, A in arms.items():
            h = A[(A["target_q"] <= t - 1)].merge(lab, on=["province_code", "target_q"]).dropna(subset=["p"])
            past[name] = h
        n_dates = min(h["target_q"].nunique() for h in past.values())
        if n_dates >= MIN_PS_DATES:
            scores = {n: float(h.assign(b=(h["p"] - h["y"]) ** 2).groupby("target_q")["b"].mean().mean())
                      for n, h in past.items()}
            chosen = min(ARMS, key=lambda n: (scores[n], list(ARMS).index(n)))
        else:
            scores, chosen = {}, "M1"
        cur = arms[chosen][arms[chosen]["t"] == t][["t", "target_q", "province_code", "F_hat", "p"]].copy()
        h = past[chosen]
        platt = False
        if h["target_q"].nunique() >= MIN_PLATT_DATES and h["y"].nunique() == 2 and cur["p"].notna().all():
            lr = LogisticRegression(C=1.0, max_iter=2000).fit(_logit(h["p"]).reshape(-1, 1), h["y"].to_numpy(int))
            cur["p"] = lr.predict_proba(_logit(cur["p"]).reshape(-1, 1))[:, 1]
            platt = True
        cur["chosen"], cur["platt"] = chosen, platt
        cur["past_scores"] = [scores] * len(cur)
        out.append(cur)
    return pd.concat(out, ignore_index=True)


# ------------------------------------------------------------------------------------------ features
def nlp_panel() -> pd.DataFrame:
    f = pd.read_csv(NEWS, dtype={"province_code": str})
    f["q"] = f["quarter"].map(L.qi)
    L._assert_window("FSSI-v2", q=f["q"])
    return f


def features(d_full: L.Data, origins: list[int]) -> pd.DataFrame:
    X = L.feature_table(d_full, origins)
    X["F_hat_M1z"] = [m_point(d_full.cut(t), t, 2, p, 0.0)["F_hat"] for t, p in zip(X["t"], X["province_code"])]
    f = nlp_panel().set_index(["province_code", "q"])
    X["fssi_v2"] = [f["FSSI_v2"].get((p, t), np.nan) for p, t in zip(X["province_code"], X["t"])]
    X["fssi_admitted"] = [float(f["n_admitted"].get((p, t), 0) or 0) for p, t in zip(X["province_code"], X["t"])]
    X["fssi_sufficient"] = [float(f["evidence_status"].get((p, t), "") == "SUFFICIENT")
                            for p, t in zip(X["province_code"], X["t"])]
    return X


# ------------------------------------------------------------------------------------------ models
class LRModel:
    """Standardized L2 logistic regression; training-median imputation + missing indicators (PROTOCOL 3)."""

    def __init__(self, cols):
        self.cols = cols

    def fit(self, tr):
        from sklearn.linear_model import LogisticRegression
        X = tr[self.cols].astype(float)
        self.med = X.median()
        self.miss = [c for c in self.cols if X[c].isna().any()]
        Z = self._design(X)
        self.mu, self.sd = Z.mean(), Z.std(ddof=0).replace(0, 1)
        self.keep = [c for c in Z if Z[c].std(ddof=0) > 0]
        self.m = LogisticRegression(C=0.5, max_iter=5000).fit(((Z - self.mu) / self.sd)[self.keep], tr["y"].astype(int))
        return self

    def _design(self, X):
        Z = X.fillna(self.med).fillna(0.0)
        for c in self.miss:
            Z[f"{c}__missing"] = X[c].isna().astype(float)
        return Z

    def predict(self, te):
        Z = self._design(te[self.cols].astype(float))
        return self.m.predict_proba(((Z - self.mu) / self.sd)[self.keep])[:, 1]


class GBModel:
    def __init__(self, cols):
        self.cols = cols

    def fit(self, tr):
        from lightgbm import LGBMClassifier
        self.m = LGBMClassifier(**LGBM).fit(tr[self.cols].astype(float), tr["y"].astype(int))
        return self

    def predict(self, te):
        return self.m.predict_proba(te[self.cols].astype(float))[:, 1]


def eligible(tr: pd.DataFrame) -> bool:
    return tr["q"].nunique() >= L.MIN_TRAIN_QUARTERS and tr["y"].nunique() == 2


def grouped_shap(model: GBModel, te: pd.DataFrame) -> dict:
    c = model.m.booster_.predict(te[model.cols].astype(float), pred_contrib=True)[:, :-1]
    out = {}
    for g, fs in GROUPS.items():
        j = [model.cols.index(f) for f in fs if f in model.cols]
        out[g] = float(np.abs(c[:, j].sum(axis=1)).mean()) if j else None
    return out

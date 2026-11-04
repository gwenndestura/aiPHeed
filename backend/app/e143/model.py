"""
E143 cross-fitted survey-anchored provincial risk models (PROTOCOL.md section 4).

    Level      cross-fitted structural level: a province's level comes from the fold model whose training excluded its
               region (GroupKFold(5) by region); training deviations are out-of-fold
    Anchored   one class, three anchor forms:
               "ar1"   E142 form: mu + phi^h x shrunk last-survey deviation (phi from adjacent measured transitions)
               "re"    permanent province component + independent round shocks; BLUP from all earlier rounds
               "hre"   region + province permanent components; BLUP from own and same-region earlier rounds
Every anchor uses only rows whose survey reference quarter precedes the target's; with no identifying training pair
the anchor is off (structural level only).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e142 import model as M142

RQ = M142.ROUND_QUARTER


class Level:
    def __init__(self, kind: str = "lgbm"):
        self.kind = kind

    def fit(self, tr: pd.DataFrame):
        tr = tr.reset_index(drop=True)
        k = min(5, tr["region"].nunique())
        self.oof_ = np.full(len(tr), np.nan)
        self.folds_ = []
        for a, b in GroupKFold(k).split(tr, groups=tr["region"]):
            m = M142._Mu(self.kind).make().fit(tr.iloc[a])
            self.oof_[b] = m.predict_y(tr.iloc[b])
            self.folds_.append((set(tr["region"].iloc[b]), m))
        self.full_ = M142._Mu(self.kind).make().fit(tr)
        return self

    def predict_y(self, X: pd.DataFrame) -> np.ndarray:
        out = np.asarray(self.full_.predict_y(X), float).copy()
        for regs, m in self.folds_:
            idx = X["region"].isin(regs).values
            if idx.any():
                out[idx] = m.predict_y(X[idx])
        return out


class Anchored:
    def __init__(self, form: str = "re", level: str = "lgbm"):
        self.form, self.level = form, level

    def fit(self, tr: pd.DataFrame, level: Level | None = None):
        tr = tr.reset_index(drop=True)
        self.lv_ = level if level is not None else Level(self.level).fit(tr)
        d = tr["y"].values - self.lv_.oof_
        self.tr_ = tr.assign(d=d, rq=tr["survey"].map(RQ))
        self.tau2_ = float(max(0.01, np.mean(d ** 2 - tr["se_y"].values ** 2)))
        T = self.tr_
        # pair moments (different rounds only)
        own, reg = [], []
        for i in range(len(T)):
            for j in range(i + 1, len(T)):
                if T.at[i, "survey"] == T.at[j, "survey"] or T.at[i, "region"] != T.at[j, "region"]:
                    continue
                (own if T.at[i, "key"] == T.at[j, "key"] else reg).append(T.at[i, "d"] * T.at[j, "d"])
        self.n_own_pairs_, self.n_reg_pairs_ = len(own), len(reg)
        self.c_ = float(np.clip(np.mean(own) / self.tau2_, 0, 1)) if own else 0.0
        self.sA_ = self.c_ * self.tau2_
        self.sG_ = float(np.clip(np.mean(reg), 0, self.sA_)) if (reg and own) else 0.0
        # AR(1) persistence, exactly E142's estimator but on these out-of-fold deviations
        key_d = {(k, s): v for k, s, v in zip(T["key"], T["survey"], T["d"])}
        prods, hs = [], []
        for k, ps, v, h in zip(T["key"], T["prev_survey"], T["d"], M142.gap_quarters(T)):
            if isinstance(ps, str) and (k, ps) in key_d:
                prods.append(v * key_d[(k, ps)])
                hs.append(h)
        self.n_transitions_ = len(prods)
        if prods:
            prods, hs = np.asarray(prods), np.asarray(hs, float)
            self.phi_ = float(M142.PHI_GRID[int(np.argmin([np.sum((prods - self.tau2_ * p ** hs) ** 2) for p in M142.PHI_GRID]))])
        else:
            self.phi_ = 0.0
        return self

    # ------------------------------------------------------------------------------------------------------------
    def _past(self, key, region, tq):
        P = self.tr_[self.tr_["rq"] < tq]
        return P[P["key"] == key], P[(P["region"] == region) & (P["key"] != key)]

    def _one(self, key, region, tq):
        """Returns (anchor mean, anchor-explained variance, weight on own last survey, n own rounds used)."""
        t2 = self.tau2_
        own, oth = self._past(key, region, tq)
        if self.form == "ar1":
            if not len(own) or self.phi_ == 0:
                return 0.0, 0.0, 0.0, 0
            last = own.sort_values("rq").iloc[-1]
            h = tq - last["rq"]
            w = self.phi_ ** h
            k = t2 / (t2 + last["se_y"] ** 2)
            p0 = t2 * last["se_y"] ** 2 / (t2 + last["se_y"] ** 2)
            return w * k * last["d"], t2 - (w ** 2 * p0 + t2 * (1 - w ** 2)), w * k, 1
        sA, sG = self.sA_, (self.sG_ if self.form == "hre" else 0.0)
        rows = [own] + ([oth] if sG > 0 else [])
        R = pd.concat(rows) if rows else own
        if not len(R) or (sA == 0 and sG == 0):
            return 0.0, 0.0, 0.0, 0
        kk, rr, dd, se = R["key"].values, R["rq"].values, R["d"].values, R["se_y"].values
        same_p = kk[:, None] == kk[None, :]
        S = np.where(same_p, sA, sG).astype(float)
        S[np.diag_indices_from(S)] = t2 + se ** 2
        s = np.where(kk == key, sA, sG).astype(float)
        a = np.linalg.solve(S, s)
        own_w = float(a[kk == key].sum())
        return float(a @ dd), float(s @ a), own_w, int((kk == key).sum())

    def predict(self, X: pd.DataFrame, target_q=None):
        mu = self.lv_.predict_y(X)
        tq = (X["survey"].map(RQ).values if target_q is None else np.broadcast_to(np.asarray(target_q, float), (len(X),)))
        res = [self._one(k, r, q) for k, r, q in zip(X["key"], X["region"], tq)]
        anc = np.array([r[0] for r in res])
        expl = np.array([r[1] for r in res])
        self.last_detail_ = pd.DataFrame(res, columns=["anchor", "explained_var", "weight_on_own_surveys", "own_rounds_used"],
                                         index=X.index).assign(level=mu)
        V = np.maximum(self.tau2_ - expl, 1e-4)
        return mu + anc, V

    def predict_proba(self, X, target_q=None):
        yhat, V = self.predict(X, target_q)
        return norm.cdf(yhat / np.sqrt(V))


CANDIDATES = {"C1 STATE-LGBM-X": ("ar1", "lgbm"), "C2 RE-LGBM-X": ("re", "lgbm"),
              "C3 RE-RIDGE-X": ("re", "ridge"), "C4 HRE-LGBM-X": ("hre", "lgbm")}
N_VAR_PARAMS = {"C1 STATE-LGBM-X": 2, "C2 RE-LGBM-X": 2, "C3 RE-RIDGE-X": 2, "C4 HRE-LGBM-X": 3}

"""C-B6P3 (../PREREGISTRATION_P3.md, owner directive): C-B6P2 with a linear base on the five driver groups, so every
driver contributes to every forecast. LightGBM boosts on top of the logistic log-odds (init_score).

    python cb6p3_model.py fit     # -> ../out/cb6p3_fits.csv
    python cb6p3_model.py score   # -> ../out/cb6p3_results.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cb6p2_model as P2  # noqa: E402

M, H, V = P2.M, P2.H, P2.V
PLAN = M.HERE / "PREREGISTRATION_P3.md"
OUT = M.OUT
NAME = "C-B6P3"
COLS = P2.M.COLS["C-B6P2"]
DRV_GROUPS = {"market": ["R_food_yoy", "R_head_yoy", "R_food_mom", "R_rice_yoy"] + H.WORLD,
              "climate": ["ONI_last", "ONI_max12", "tc_mean", "R_C3"], "fish_kill": ["R_C4"],
              "employment": ["E1"], "ofw_remittance": ["E2"]}
DRV = [c for cs in DRV_GROUPS.values() for c in cs]


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "C-B6P3 pre-registration changed"
    return h


class Hybrid:
    """L2 logistic on the driver inputs (log-odds) + LightGBM boosting from that init_score."""

    def __init__(self, cfg: dict, cols: list[str]):
        self.cfg, self.cols = cfg, cols
        self.m = self.lr = None
        self.const = None

    def _z(self, df):
        X = df[self.keep].astype(float).fillna(self.med)
        return ((X - self.mu) / self.sd).to_numpy()

    def fit(self, tr: pd.DataFrame):
        import lightgbm as lgb
        from sklearn.linear_model import LogisticRegression
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        X = tr[DRV].astype(float)
        self.med = X.median()
        self.keep = [c for c in DRV if pd.notna(self.med[c])]
        X = X[self.keep].fillna(self.med[self.keep])
        self.mu, sd = X.mean(), X.std(ddof=0)
        self.keep = [c for c in self.keep if sd[c] > 0]
        self.med, self.mu, self.sd = self.med[self.keep], self.mu[self.keep], sd[self.keep]
        self.lr = LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=5000).fit(self._z(tr), y)
        off = self.lr.decision_function(self._z(tr))
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, reg_lambda=5.0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=H.SEED_LGBM, n_jobs=1,
                                    verbose=-1, max_depth=self.cfg["depth"], num_leaves=self.cfg["leaves"],
                                    n_estimators=self.cfg["trees"], class_weight=self.cfg["cw"], min_child_samples=15)
        self.m.fit(tr[self.cols].astype(float), y, init_score=off)
        return self

    def predict(self, te: pd.DataFrame) -> np.ndarray:
        if self.m is None:
            return np.full(len(te), self.const)
        raw = self.m.booster_.predict(te[self.cols].astype(float), raw_score=True) + self.lr.decision_function(self._z(te))
        return 1 / (1 + np.exp(-raw))

    def shap(self, te: pd.DataFrame) -> pd.DataFrame:
        S = pd.DataFrame(np.asarray(self.m.booster_.predict(te[self.cols].astype(float), pred_contrib=True))[:, :-1],
                         columns=self.cols, index=te.index)
        lin = self._z(te) * self.lr.coef_[0]
        for j, c in enumerate(self.keep):
            S[c] = S[c] + lin[:, j]
        return S


def select(tr: pd.DataFrame) -> dict:
    folds = H.inner_folds(tr)
    if not folds:
        return H.GRID[0]
    ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
    sc = {}
    for c in H.GRID:
        p = np.clip(np.concatenate([Hybrid(c, COLS).fit(f).predict(h) for f, h in folds]), 1e-6, 1 - 1e-6)
        sc[c["id"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return min(H.GRID, key=lambda c: (round(sc[c["id"]], 9), c["id"]))


def _origin(t: int) -> pd.DataFrame:
    S, Dm = M._G["T"], M._G["Dm"]
    te = M._prov_rows(S[(S["area"] == "BL") & (S["t"] == t) & S["lead"].isin(M.LEADS)].copy(), Dm).reset_index(drop=True)
    tr = M.train_rows(t)
    o = te[["t", "lead", "q", "province"]].copy()
    o["name"], o["fallback"], o["cfg"] = NAME, False, None
    sh = pd.DataFrame(0.0, index=o.index, columns=COLS)
    if H.eligible(tr):
        cfg = select(tr)
        m = Hybrid(cfg, COLS).fit(tr)
        o["p"], o["cfg"] = m.predict(te), cfg["id"]
        if m.m is not None:
            sh = m.shap(te)
    else:
        o["p"], o["fallback"] = float(tr["y"].mean()) if len(tr) else 0.5, True
    return pd.concat([o, sh.add_prefix("shap_")], axis=1)


def fit():
    pre = check()
    with Pool(8, initializer=P2._init) as pool:
        F = pd.concat(pool.map(_origin, list(range(M.FIRST, H.qi("2026-Q3") + 1))), ignore_index=True)
    F.to_csv(OUT / "cb6p3_fits.csv", index=False)
    print({"prereg_sha256": pre, "rows": len(F), "origins": int(F["t"].nunique())})


def score():
    pre = check()
    L = pd.read_csv(OUT / "cb6p_labels.csv")
    F = pd.concat([pd.read_csv(OUT / "cb6p_fits.csv"), pd.read_csv(OUT / "cb6p2_fits.csv"),
                   pd.read_csv(OUT / "cb6p3_fits.csv")], ignore_index=True)
    W0 = F.pivot_table(index=["t", "lead", "q", "province"], columns="name", values="p").reset_index()
    W0 = W0.merge(L[["province", "q", "y"]], on=["province", "q"])
    W0 = W0[W0["q"] >= M.Q0]
    arms = [NAME, "C-B6P2", "C-B6P", "PERSIST"]
    groups = {**M.GROUPS, "province_history": P2.EXTRA}
    res = {"prereg_sha256": pre, "leads": {}, "algorithm3": {}}
    for k in M.LEADS:
        W = W0[W0["lead"] == k].dropna(subset=arms)
        Lk = {a: M.metrics(W["y"], W[a]) for a in arms}
        if k <= 2:
            Lk["vs_C-B6P2"] = M.paired(W, NAME, "C-B6P2")
            Lk["vs_PERSIST"] = M.paired(W, NAME, "PERSIST")
            s = F[(F["name"] == NAME) & (F["lead"] == k) & (F["q"] >= M.Q0)]
            g = pd.DataFrame({n: sum(s[f"shap_{c}"].fillna(0) for c in cs) for n, cs in groups.items()})
            Lk["driver_nonzero_share"] = {n: float((g[n].abs() > 0).mean()) for n in DRV_GROUPS}
            sh = g.abs().div(g.abs().sum(axis=1).replace(0, np.nan), axis=0) * 100
            Lk["shap_share_pct_mean"] = {n: float(sh[n].mean()) for n in groups}
        res["leads"][str(k)] = Lk
    for a in arms:
        mx = 0
        for k in M.LEADS:
            if res["leads"][str(k)][a]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][a] = mx
    l1, l2 = res["leads"]["1"], res["leads"]["2"]
    res["acceptance"] = {
        "every_driver_nonzero_ge_99pct": all(v >= .99 for x in (l1, l2) for v in x["driver_nonzero_share"].values()),
        "accuracy_ge_0.75_both": all(x[NAME]["accuracy"] >= .75 for x in (l1, l2)),
        "brier_not_worse_than_C-B6P2_by_0.01": all(x["vs_C-B6P2"]["diff"] <= .01 for x in (l1, l2))}
    res["acceptance"]["passes"] = all(res["acceptance"].values())
    (OUT / "cb6p3_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for a in arms:
            m = res["leads"][k][a]
            print(f"L{k} {a:8s} acc {m['accuracy']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} F1 {m['f1']:.3f} "
                  f"AUC {m['auc']:.3f} Brier {m['brier']:.4f}")
        print("   vs C-B6P2", {x: round(y, 4) if isinstance(y, float) else y for x, y in res["leads"][k]["vs_C-B6P2"].items()})
        print("   drivers nonzero:", {x: round(y, 3) for x, y in res["leads"][k]["driver_nonzero_share"].items()})
        print("   SHAP %:", {x: round(y, 1) for x, y in res["leads"][k]["shap_share_pct_mean"].items()})
    print("Algorithm 3:", res["algorithm3"])
    print("Acceptance:", res["acceptance"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()

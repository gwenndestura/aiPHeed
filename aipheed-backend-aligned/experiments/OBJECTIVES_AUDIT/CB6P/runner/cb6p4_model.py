"""C-B6P4 (../PREREGISTRATION_P4.md, owner directive): C-B6P3 with the logistic C chosen on the inner folds.

    python cb6p4_model.py fit     # -> ../out/cb6p4_fits.csv
    python cb6p4_model.py score   # -> ../out/cb6p4_results.json
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
import cb6p3_model as P3  # noqa: E402

P2, M, H = P3.P2, P3.M, P3.H
PLAN = M.HERE / "PREREGISTRATION_P4.md"
OUT = M.OUT
NAME = "C-B6P4"
CS = [0.001, 0.01, 0.1, 1.0]
COLS, DRV_GROUPS = P3.COLS, P3.DRV_GROUPS


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "C-B6P4 pre-registration changed"
    return h


class Hybrid4(P3.Hybrid):
    def __init__(self, cfg, cols, C):
        super().__init__(cfg, cols)
        self.C = C

    def fit(self, tr):
        from sklearn import linear_model
        orig = linear_model.LogisticRegression
        C = self.C

        def LR(**kw):
            kw["C"] = C
            return orig(**kw)
        import sklearn.linear_model as slm
        slm.LogisticRegression = LR
        try:
            return super().fit(tr)
        finally:
            slm.LogisticRegression = orig


def select(tr):
    folds = H.inner_folds(tr)
    if not folds:
        return H.GRID[0], CS[0]
    ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
    best = None
    for C in CS:
        for c in H.GRID:
            p = np.clip(np.concatenate([Hybrid4(c, COLS, C).fit(f).predict(h) for f, h in folds]), 1e-6, 1 - 1e-6)
            s = round(float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p))), 9)
            key = (s, C, c["id"])
            if best is None or key < best[0]:
                best = (key, c, C)
    return best[1], best[2]


def _origin(t):
    S, Dm = M._G["T"], M._G["Dm"]
    te = M._prov_rows(S[(S["area"] == "BL") & (S["t"] == t) & S["lead"].isin(M.LEADS)].copy(), Dm).reset_index(drop=True)
    tr = M.train_rows(t)
    o = te[["t", "lead", "q", "province"]].copy()
    o["name"], o["fallback"], o["cfg"], o["C"] = NAME, False, None, np.nan
    sh = pd.DataFrame(0.0, index=o.index, columns=COLS)
    if H.eligible(tr):
        cfg, C = select(tr)
        m = Hybrid4(cfg, COLS, C).fit(tr)
        o["p"], o["cfg"], o["C"] = m.predict(te), cfg["id"], C
        if m.m is not None:
            sh = m.shap(te)
    else:
        o["p"], o["fallback"] = float(tr["y"].mean()) if len(tr) else 0.5, True
    return pd.concat([o, sh.add_prefix("shap_")], axis=1)


def fit():
    pre = check()
    with Pool(8, initializer=P2._init) as pool:
        F = pd.concat(pool.map(_origin, list(range(M.FIRST, H.qi("2026-Q3") + 1))), ignore_index=True)
    F.to_csv(OUT / "cb6p4_fits.csv", index=False)
    print({"prereg_sha256": pre, "rows": len(F), "chosen_C": F.groupby("t")["C"].first().value_counts().to_dict()})


def score():
    pre = check()
    L = pd.read_csv(OUT / "cb6p_labels.csv")
    F = pd.concat([pd.read_csv(OUT / f) for f in ("cb6p_fits.csv", "cb6p2_fits.csv", "cb6p3_fits.csv", "cb6p4_fits.csv")],
                  ignore_index=True)
    W0 = F.pivot_table(index=["t", "lead", "q", "province"], columns="name", values="p").reset_index()
    W0 = W0.merge(L[["province", "q", "y"]], on=["province", "q"])
    W0 = W0[W0["q"] >= M.Q0]
    arms = [NAME, "C-B6P3", "C-B6P2", "PERSIST"]
    groups = {**M.GROUPS, "province_history": P2.EXTRA}
    res = {"prereg_sha256": pre, "leads": {}, "algorithm3": {},
           "chosen_C": {str(k): int(v) for k, v in F[F["name"] == NAME].groupby("t")["C"].first().value_counts().items()}}
    for k in M.LEADS:
        W = W0[W0["lead"] == k].dropna(subset=arms)
        Lk = {a: M.metrics(W["y"], W[a]) for a in arms}
        if k <= 2:
            Lk["vs_C-B6P2"] = M.paired(W, NAME, "C-B6P2")
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
    (OUT / "cb6p4_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("chosen C:", res["chosen_C"])
    for k in ("1", "2"):
        for a in arms:
            m = res["leads"][k][a]
            print(f"L{k} {a:8s} acc {m['accuracy']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} F1 {m['f1']:.3f} "
                  f"AUC {m['auc']:.3f} Brier {m['brier']:.4f}")
        v = res["leads"][k]["vs_C-B6P2"]
        print(f"   vs C-B6P2 dBrier {v['diff']:+.4f} p {v['p_one_sided']:.3f}")
        print("   drivers nonzero:", {x: round(y, 3) for x, y in res["leads"][k]["driver_nonzero_share"].items()})
        print("   SHAP %:", {x: round(y, 1) for x, y in res["leads"][k]["shap_share_pct_mean"].items()})
    print("Algorithm 3:", res["algorithm3"])
    print("Acceptance:", res["acceptance"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()

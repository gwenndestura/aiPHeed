"""Y8 development (EXPERIMENT_PLAN_PHASE2_ADDENDUM_A.md): can the regional price condition be forecast at Lead 2 (target
months m0+5..m0+7) better than persistence? Region IV-A CPI 1994+, targets 2000-Q1..2020-Q4, expanding-window refits with
in-fold standardisation and penalty choice. Writes out/y8_dev.json, out/y8_dev_rows.csv.

    python -B run_dev.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import warnings
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402
from sklearn.linear_model import LogisticRegression, Ridge  # noqa: E402
from sklearn.metrics import log_loss  # noqa: E402

import cov  # noqa: E402
import p2lib as P  # noqa: E402

warnings.filterwarnings("ignore")
R = P.R
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TF, TG = 6.25, 0.48
C_GRID = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
A_GRID = (0.3, 1.0, 3.0, 10.0, 30.0, 100.0)
T_FIRST, T_LAST = R.qi("2000-Q1") - 2, R.qi("2020-Q4") - 2


def plan_ok():
    want = (P.RES / "common" / "PLAN2A_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((P.RES / "EXPERIMENT_PLAN_PHASE2_ADDENDUM_A.md").read_bytes()).hexdigest() == want


def region() -> tuple[pd.Series, pd.Series]:
    c = pd.read_csv(R.LONG / "cov_cpi.csv")
    c = c[c["geolocation"].str.startswith("Region IV-A") & c["yoy"].notna()]
    f = c[c["commodity_description"] == "01.1 - FOOD"].set_index("ym")["yoy"].astype(float)
    a = c[c["commodity_description"] == "0 - ALL ITEMS"].set_index("ym")["yoy"].astype(float)
    return f, f - a


F, G = region()


def tmonths(q: int) -> list[int]:
    return [(q // 4) * 12 + 3 * (q % 4) + i for i in range(3)]


def row(t: int) -> dict | None:
    m = R.m0(t)
    need = [m - i for i in range(13)] + [x - 12 for x in tmonths(t + 2)]
    if not all(x in F.index for x in need):
        return None
    f3, g3 = float(F[[m, m - 1, m - 2]].mean()), float(G[[m, m - 1, m - 2]].mean())
    cv = dict(zip(cov.FEATS, cov.feats(t)))
    r = {"t": t, "q": t + 2, "F_last": float(F[m]), "F3": f3, "dF3": float(F[m] - F[m - 3]), "dF6": float(F[m] - F[m - 6]),
         "F_base": float(F[[x - 12 for x in tmonths(t + 2)]].mean()), "G_last": float(G[m]), "G3": g3,
         "dG3": float(G[m] - G[m - 3]), "G_base": float(G[[x - 12 for x in tmonths(t + 2)]].mean()),
         "pers_bin": float(f3 > TF or g3 > TG), "xF": f3 - TF, "xG": g3 - TG, **{k: cv[k] for k in
                                                                               ("rice_yoy", "rice_d3", "oni_last", "oni_max6", "tc_prev", "palay_yoy")}}
    tm = tmonths(t + 2)
    if all(x in F.index for x in tm):
        r.update(F_tgt=float(F[tm].mean()), G_tgt=float(G[tm].mean()))
        r["y"] = int(r["F_tgt"] > TF or r["G_tgt"] > TG)
    return r


AR_X = ["F_last", "F3", "dF3", "dF6", "F_base", "G_last", "G3", "dG3", "G_base", "rice_yoy"]
LX = ["F_last", "F3", "dF3", "dF6", "G3", "rice_yoy", "rice_d3", "oni_last", "oni_max6", "tc_prev", "palay_yoy"]


def _std(tr, x0, cols):
    X = tr[cols].to_numpy(float)
    mu = np.nanmean(X, 0)
    X = np.where(np.isnan(X), mu, X)
    sd = X.std(0)
    sd[sd == 0] = 1
    z = np.array([x0[c] for c in cols], float)
    z = np.where(np.isnan(z), mu, z)
    return (X - mu) / sd, ((z - mu) / sd).reshape(1, -1)


def _split(tr):
    cut = tr["t"].quantile(0.75)
    return (tr["t"] <= cut).to_numpy(), (tr["t"] > cut).to_numpy()


def fit_predict(tr: pd.DataFrame, x0: dict) -> dict:
    y = tr["y"].to_numpy(int)
    out = {}
    ok = len(tr) >= 20 and y.sum() >= 3 and (1 - y).sum() >= 3
    if not ok:
        return {"PERS_PROB": np.nan, "AR": np.nan, "LOGX": np.nan}
    X, z = _std(tr, x0, ["xF", "xG"])
    out["PERS_PROB"] = float(LogisticRegression(C=100.0, max_iter=2000).fit(X, y).predict_proba(z)[0, 1])
    a, b = _split(tr)
    # AR: ridge for F and G target-quarter means
    X, z = _std(tr, x0, AR_X)
    pr = []
    for tgt, th in (("F_tgt", TF), ("G_tgt", TG)):
        yy = tr[tgt].to_numpy(float)
        best, ba = np.inf, A_GRID[0]
        for al in A_GRID:
            e = Ridge(alpha=al).fit(X[a], yy[a]).predict(X[b]) - yy[b]
            if np.mean(e ** 2) < best:
                best, ba = float(np.mean(e ** 2)), al
        mdl = Ridge(alpha=ba).fit(X, yy)
        sig = math.sqrt(float(np.mean((yy - mdl.predict(X)) ** 2)))
        pr.append(float(norm.cdf((float(mdl.predict(z)[0]) - th) / max(sig, 0.1))))
    out["AR"] = 1 - (1 - pr[0]) * (1 - pr[1])
    # LOGX
    X, z = _std(tr, x0, LX)
    best, bc = np.inf, C_GRID[0]
    if len(set(y[a])) == 2:
        for c in C_GRID:
            mdl = LogisticRegression(C=c, max_iter=2000).fit(X[a], y[a])
            ll = log_loss(y[b], mdl.predict_proba(X[b])[:, 1], labels=[0, 1])
            if ll < best:
                best, bc = ll, c
    out["LOGX"] = float(LogisticRegression(C=bc, max_iter=2000).fit(X, y).predict_proba(z)[0, 1])
    return out


def boot(d, a, b, block=1):
    l = ((d[a] - d["y"]) ** 2 - (d[b] - d["y"]) ** 2).to_numpy()
    n = len(l)
    rng = np.random.default_rng(P.SEED)
    nb = math.ceil(n / block)
    bs = np.empty(P.B)
    for i in range(P.B):
        st = rng.integers(0, n - block + 1, nb)
        bs[i] = np.concatenate([l[s:s + block] for s in st])[:n].mean()
    return {"diff": float(l.mean()), "p_one_sided": float(np.mean(bs >= 0))}


def main():
    plan_ok()
    allr = {t: row(t) for t in range(R.qi("1995-Q1"), T_LAST + 1)}
    allr = {t: r for t, r in allr.items() if r is not None}
    rows = []
    for t in range(T_FIRST, T_LAST + 1):
        if t not in allr or "y" not in allr[t]:
            continue
        tr = pd.DataFrame([r for tt, r in allr.items() if tt <= t - 3 and "y" in r])
        p = fit_predict(tr, allr[t])
        rows.append({**{k: allr[t][k] for k in ("t", "q", "y", "pers_bin", "F3", "G3", "F_tgt", "G_tgt")}, **p,
                     "target": R.qs(t + 2), "trainRows": len(tr)})
    d = pd.DataFrame(rows).dropna(subset=["PERS_PROB", "AR", "LOGX"])
    res = {"rows": len(d), "prevalence": float(d["y"].mean()), "period": f"{d['target'].min()}..{d['target'].max()}"}
    for c in ("pers_bin", "PERS_PROB", "AR", "LOGX"):
        res[c] = R.metrics(d["y"], d[c])
    for c in ("AR", "LOGX"):
        res[f"{c}_vs_PERS_PROB"] = {"iid": boot(d, c, "PERS_PROB"), "block4": boot(d, c, "PERS_PROB", 4)}
        res[f"{c}_gate"] = {"G1": res[f"{c}_vs_PERS_PROB"]["iid"]["diff"] < 0 and res[f"{c}_vs_PERS_PROB"]["iid"]["p_one_sided"] < .10,
                            "G2": (res[c]["balanced"] or 0) >= (res["PERS_PROB"]["balanced"] or 0)}
    passed = [c for c in ("AR", "LOGX") if all(res[f"{c}_gate"].values())]
    res["passedGate"] = passed
    OUT.mkdir(exist_ok=True)
    (OUT / "y8_dev.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    d.to_csv(OUT / "y8_dev_rows.csv", index=False, lineterminator="\n", float_format="%.5f")
    print({k: res[k] for k in ("rows", "prevalence", "period")})
    for c in ("pers_bin", "PERS_PROB", "AR", "LOGX"):
        m = res[c]
        print(f"{c:10s} acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} "
              f"spec {m['specificity'] or 0:.2f} AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f}")
    for c in ("AR", "LOGX"):
        print(c, res[f"{c}_vs_PERS_PROB"], res[f"{c}_gate"])
    print("passed gate:", passed)


if __name__ == "__main__":
    main()

"""E60 step C1 (PROTOCOL section 5): rolling-origin forecasts of candidates A, B, C, D at the 10 evaluation origins and the
2 operational origins, SEALED before any outcome is read. Same E56 nested procedure (72 configurations) for A/C/D with
different input sets; B is an L2 logistic regression on news features only. P(HIGH) = P_hunger (I7) x P_price.

    backend/venv/Scripts/python.exe -B runner/c1_candidates.py  -> sealed/candidates.csv (+ .sha256), sealed/selections.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E60 = Path(__file__).resolve().parents[1]
EXP = E60.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402
from n5_features import HIST_COLS, NEWS_COLS, TRIG  # noqa: E402

E, F, I7, L, np, pd = G.E, G.F, G.I7, G.L, G.np, G.pd
ORIGINS = list(range(L.qi("2023-Q4"), L.qi("2026-Q3") + 1))
SEALED = E60 / "sealed" / "candidates.csv"


def verify():
    want = (E60 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E60 / "MODEL_SELECTION_AND_VALIDATION_PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("protocol changed after freezing")
    want = (E60 / "runner" / "CLASSIFIER_V2_SHA256.txt").read_text().split()[0]
    if hashlib.sha256((E60 / "runner" / "n4_classifier.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest() != want:
        raise SystemExit("classifier v2 changed after freezing")


def colfn(cand):
    def cols(c):
        base = F.feature_cols(c["feat"], "AS" if c["pov"] == "AS" else None, drop=("news",))   # government only
        if cand == "A":
            return base
        news = [f"nz_market_share", "nz_market_chg", "nz_reg_market"] if c["feat"] == "market" else NEWS_COLS
        return base + news + (HIST_COLS if cand == "D" else [])
    return cols


def tuned(d, X, B, t, space, cols):
    from joblib import Parallel, delayed
    tr, te = F.frame(d, X, B, t, "AS")
    hc = F.hunger(d, X, t)

    def inner(c):
        cc = cols(c)
        ll, n = 0.0, 0
        for q, fq in I7.folds(tr["q"].unique(), "forward"):
            fit = tr[tr["q"].isin(fq)].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
            hold = tr[tr["q"] == q].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}"])
            if not len(hold) or not len(fit):
                continue
            p = np.clip(G.PriceLGB2(cc, c).fit(fit).predict(hold), 1e-6, 1 - 1e-6)
            y = hold["PS"].to_numpy(float)
            ll += float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
            n += len(y)
        return ll / n if n else float("inf")
    scores = Parallel(n_jobs=8, backend="loky")(delayed(inner)(c) for c in space)
    best = min(range(len(space)), key=lambda i: (round(scores[i], 10), G.simplicity(space[i])))
    c = space[best]
    fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
    mdl = G.PriceLGB2(cols(c), c).fit(fit)
    pp = mdl.predict(te)
    imp = dict(zip(mdl.feat, mdl.model.booster_.feature_importance("split"))) if mdl.const is None else {}
    return {"p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "cfg": c,
            "news_splits": int(sum(v for k, v in imp.items() if k.startswith("nz_"))),
            "hist_splits": int(sum(v for k, v in imp.items() if k.startswith("hist_"))),
            "split_importance": {k: int(v) for k, v in imp.items() if v}}


def news_only(d, X, B, t):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    tr, te = F.frame(d, X, B, t, None)
    hc = F.hunger(d, X, t)
    fit = tr.dropna(subset=["F_true", "G_true"])
    Xf, Xt = fit[NEWS_COLS].astype(float).fillna(0.0), te[NEWS_COLS].astype(float).fillna(0.0)
    y = fit["PS"].astype(int).to_numpy()
    if len(set(y)) < 2:
        pp = np.full(len(te), float(y.mean()))
    else:
        sc = StandardScaler().fit(Xf)
        m = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(Xf), y)
        pp = m.predict_proba(sc.transform(Xt))[:, 1]
    return {"p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"]}


def main():
    verify()
    if SEALED.exists():
        raise SystemExit("already sealed")
    d, X0, B = E.load()
    nf = pd.read_csv(E60 / "data" / "news_features.csv", dtype={"province_code": str})
    X = X0.merge(nf, on=["t", "province_code"], how="left")
    space = G.search_space()
    rows, sel = [], {}
    for t in ORIGINS:
        out = {"A": tuned(d, X, B, t, space, colfn("A")), "C": tuned(d, X, B, t, space, colfn("C")),
               "D": tuned(d, X, B, t, space, colfn("D")), "B": news_only(d, X, B, t)}
        sel[L.qs(t)] = {k: {kk: v[kk] for kk in ("cfg", "news_splits", "hist_splits", "split_importance") if kk in v}
                        for k, v in out.items()}
        for i, p in enumerate(L.PROVS):
            r = {"t": t, "origin_quarter": L.qs(t), "target": L.qs(t + 2), "province_code": p}
            for k, v in out.items():
                r[f"{k}_p"], r[f"{k}_p_price"], r[f"{k}_p_hunger"] = float(v["p"][i]), float(v["p_price"][i]), float(v["p_hunger"])
            rows.append(r)
        print("origin", L.qs(t), {k: (v["cfg"]["id"], v["news_splits"]) for k, v in out.items() if "cfg" in v}, flush=True)
    SEALED.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(SEALED, index=False, float_format="%.12g")
    (SEALED.parent / "candidates.csv.sha256").write_text(hashlib.sha256(SEALED.read_bytes()).hexdigest() + "  candidates.csv\n")
    (SEALED.parent / "selections.json").write_text(json.dumps(sel, indent=1, default=str))
    print("sealed", len(rows))


if __name__ == "__main__":
    main()

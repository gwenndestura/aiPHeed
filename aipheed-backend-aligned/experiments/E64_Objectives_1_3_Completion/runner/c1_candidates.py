"""E64 step C1 (PROTOCOL section 5): rolling-origin forecasts of A, C, D, E, A-S, D-S and B at the 10 evaluation origins
and the 2 operational origins, SEALED before any outcome is read. Inner selection uses training targets only.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E64_Objectives_1_3_Completion/runner/c1_candidates.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e64_lib as K  # noqa: E402

G, E, F, I7, L, np, pd = K.G, K.E, K.F, K.I7, K.L, K.np, K.pd
SEALED = K.E64 / "sealed" / "candidates.csv"
N3 = None


def cols_for(cand):
    from app.news.pipeline_v3 import N3_COLS

    def cols(c):
        gov = F.feature_cols(c["feat"], "AS" if c["pov"] == "AS" else None, drop=("news",))
        if cand in ("A", "A-S"):
            return gov
        if cand == "C":
            return G.cols_for(c)
        if cand in ("D", "D-S"):
            return gov + list(N3_COLS)
        if cand == "E":
            return gov + list(N3_COLS) + K.HIST_COLS
        raise ValueError(cand)
    return cols


def inner_scores(tr, space, cols):
    from joblib import Parallel, delayed

    def one(c):
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
    return np.array(Parallel(n_jobs=8, backend="loky")(delayed(one)(c) for c in space))


def fit_with(tr, te, hc, c, cols):
    fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
    mdl = G.PriceLGB2(cols(c), c).fit(fit)
    pp = mdl.predict(te)
    imp = dict(zip(mdl.feat, mdl.model.booster_.feature_importance("split"))) if mdl.const is None else {}
    return {"p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "cfg": c["id"],
            "n3_splits": int(sum(v for k, v in imp.items() if k.startswith("n3_"))),
            "news_old_splits": int(sum(v for k, v in imp.items() if k.startswith("news_"))),
            "hist_splits": int(sum(v for k, v in imp.items() if k.startswith("hist_"))),
            "split_importance": {k: int(v) for k, v in imp.items() if v}}


def news_only(tr, te, hc):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from app.news.pipeline_v3 import N3_COLS
    fit = tr.dropna(subset=["F_true", "G_true"])
    Xf, Xt = fit[list(N3_COLS)].astype(float), te[list(N3_COLS)].astype(float)
    med = Xf.median()
    Xf2 = Xf.fillna(med).assign(fssi_missing=Xf["n3_fssi"].isna().astype(float))
    Xt2 = Xt.fillna(med).assign(fssi_missing=Xt["n3_fssi"].isna().astype(float))
    Xf2, Xt2 = Xf2.fillna(0.0), Xt2.fillna(0.0)            # columns entirely missing in training only
    y = fit["PS"].astype(int).to_numpy()
    if len(set(y)) < 2:
        pp = np.full(len(te), float(y.mean()))
    else:
        sc = StandardScaler().fit(Xf2)
        pp = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(Xf2), y).predict_proba(sc.transform(Xt2))[:, 1]
    return {"p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"]}


def main():
    K.verify_protocol()
    if SEALED.exists():
        raise SystemExit("already sealed")
    d, X0, B = E.load()
    n3 = K.n3_table()
    n3.to_csv(K.E64 / "data" / "n3_features.csv", index=False, float_format="%.10g", lineterminator="\n")
    hist = pd.read_csv(K.E60_FEAT, dtype={"province_code": str})[["t", "province_code"] + K.HIST_COLS]
    X = X0.merge(n3.drop(columns=["fssi_status", "n_admitted"]), on=["t", "province_code"], how="left")
    X = X.merge(hist, on=["t", "province_code"], how="left")
    space = G.search_space()
    acc = {"A": [], "D": []}                     # inner-score vectors per origin, for the stable rule
    rows, sel = [], {}
    for t in K.ORIGINS_EVAL + K.ORIGINS_OP:
        tr, te = F.frame(d, X, B, t, "AS")
        hc = F.hunger(d, X, t)
        out = {}
        for cand in ("A", "C", "D", "E"):
            cols = cols_for(cand)
            s = inner_scores(tr, space, cols)
            if cand in acc:
                acc[cand].append(s)
            best = min(range(len(space)), key=lambda i: (round(s[i], 10), G.simplicity(space[i])))
            out[cand] = fit_with(tr, te, hc, space[best], cols)
            out[cand]["inner_logloss"] = float(s[best])
        for cand, base in (("A-S", "A"), ("D-S", "D")):
            m = np.mean(np.vstack(acc[base]), axis=0)
            best = min(range(len(space)), key=lambda i: (round(m[i], 10), G.simplicity(space[i])))
            out[cand] = fit_with(tr, te, hc, space[best], cols_for(cand))
        out["B"] = news_only(tr, te, hc)
        sel[L.qs(t)] = {k: {kk: v[kk] for kk in ("cfg", "n3_splits", "news_old_splits", "hist_splits", "split_importance",
                                                  "inner_logloss") if kk in v} for k, v in out.items()}
        for i, p in enumerate(L.PROVS):
            assert te["province_code"].iloc[i] == p
            r = {"t": t, "origin_quarter": L.qs(t), "target": L.qs(t + 2), "province_code": p}
            for k, v in out.items():
                r[f"{k}_p"], r[f"{k}_p_price"], r[f"{k}_p_hunger"] = float(v["p"][i]), float(v["p_price"][i]), float(v["p_hunger"])
            rows.append(r)
        print("origin", L.qs(t), {k: (v.get("cfg"), v.get("n3_splits")) for k, v in out.items()}, flush=True)
    K.write_sealed(pd.DataFrame(rows), SEALED)
    (K.E64 / "sealed" / "selections.json").write_text(json.dumps(sel, indent=1, default=str))
    print("sealed", len(rows))


if __name__ == "__main__":
    main()

"""E89 run (PROTOCOL.md): coverage fix (COV), price-condition calibration (PCAL, PCAL-GB), Leads 1 and 2, on the
E84 rows. Run from backend/:  python .../run_e89.py"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
for p in ("E84_Objective_Continuation", "E83_Deep_Reconstruction"):
    sys.path.insert(0, str(EXP / p / "runner"))
import e84_lib as C  # noqa: E402
import run_e83 as R  # noqa: E402

E, L, np, pd = C.E, C.L, C.np, C.pd
E84_RUN = EXP / "E84_Objective_Continuation" / "runs" / "20261021T093234Z"
TH = L.e40_spec()
GB_PARAMS = dict(objective="binary", num_leaves=4, max_depth=2, n_estimators=60, learning_rate=0.05, min_child_samples=5,
                 reg_lambda=5.0, random_state=89, deterministic=True, n_jobs=1, force_row_wise=True, verbosity=-1)


def lg(p):
    p = np.clip(np.asarray(p, float), 1e-3, 1 - 1e-3)
    return np.log(p / (1 - p))


def price_labels(d) -> pd.DataFrame:
    F = L.quarter_F(d, "food").merge(L.quarter_F(d, "all_items").rename(columns={"F": "HL"}), on=["province_code", "q"])
    F["y_price"] = ((F["F"] > F["province_code"].map(TH["food"])) |
                    ((F["F"] - F["HL"]) > F["province_code"].map(TH["gap"]))).astype(int)
    return F[["province_code", "q", "y_price"]]


def coverage_fill(X, d, x, sub, W, w, k, origins):
    """COV: re-simulate S-COMP with min_h = 3 at origins where it was unissued."""
    X = X.copy()
    for t in origins:
        m = (X["t"] == t) & X["comp_p"].isna()
        if not m.any():
            continue
        fx = x["ofw"][x["ofw"]["q"] <= t - 1].drop_duplicates("q").set_index("q")["fx_usd_php_avg"]
        o = C.simulate_comp(d.cut(t), sub, W, C.world_cut(w, t), fx, t, k, passthrough=True, min_h=3)
        for p, v in o.items():
            mm = m & (X["province_code"] == p)
            X.loc[mm, ["comp_p", "comp_p_hunger", "comp_p_price", "comp_F_hat", "comp_G_hat"]] = \
                [v["p"], v["p_hunger"], v["p_price"], v["F_hat"], v["G_hat"]]
    return X


def design(D: pd.DataFrame, gb: bool) -> pd.DataFrame:
    Z = pd.DataFrame({"l_comp": lg(D["comp_p_price"]), "l_sim": lg(D["sim_p_price"].fillna(D["comp_p_price"]))}, index=D.index)
    for p in L.PROVS:
        Z[f"prov_{p}"] = (D["province_code"] == p).astype(float)
    if gb:
        Z["F_rel"] = D["F_now"] - D["province_code"].map(TH["food"])
        Z["G_rel"] = D["gap_now"] - D["province_code"].map(TH["gap"])
        Z["mom3"] = D["mom3"]
        Z["rice_mom3"] = D["rice_mom3"]
    return Z


def calibrate(X, d, t, k, te, gb: bool):
    """Calibrated P(price condition at t+k) for the test rows, trained on pairs whose price label is known at O(t)."""
    lab = price_labels(d.cut(t))
    lab = lab[lab["q"] <= t - 1]
    tr = X[X["t"] + k <= t - 1].assign(q=lambda f: f["t"] + k).merge(lab, on=["province_code", "q"])
    tr = tr[tr["comp_p_price"].notna()]
    if tr["q"].nunique() < 6 or tr["y_price"].sum() < 4 or (1 - tr["y_price"]).sum() < 4:
        return te["comp_p_price"].to_numpy(), False
    A, B = design(tr, gb), design(te, gb)
    if gb:
        from lightgbm import LGBMClassifier
        A = A.fillna(A.median()).fillna(0.0)
        B = B.fillna(A.median()).fillna(0.0)
        m = LGBMClassifier(**GB_PARAMS).fit(A, tr["y_price"], init_score=A["l_comp"].to_numpy())
        raw = m.predict_proba(B, raw_score=True) + B["l_comp"].to_numpy()
        return 1 / (1 + np.exp(-raw)), True
    from sklearn.linear_model import LogisticRegression
    mu, sd = A.mean(), A.std(ddof=0).replace(0, 1)
    m = LogisticRegression(C=0.5, max_iter=5000).fit((A - mu) / sd, tr["y_price"])
    return m.predict_proba((B - mu) / sd)[:, 1], True


def run(k, d, x, sub, W, w):
    P = pd.read_csv(E84_RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
    X = pd.read_csv(E84_RUN / f"features_k{k}.csv", dtype={"province_code": str})
    X = coverage_fill(X, d, x, sub, W, w, k, sorted(P["t"].unique()))
    P["HYB-GBA-SIM"] = P["NA-GB"].fillna(P["S-SIM"])
    add = []
    for t in sorted(P["t"].unique()):
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        pc, f1 = calibrate(X, d, t, k, te, gb=False)
        pg, f2 = calibrate(X, d, t, k, te, gb=True)
        for i, p in enumerate(L.PROVS):
            ph, pp = te["comp_p_hunger"].iloc[i], te["comp_p_price"].iloc[i]
            add.append({"t": t, "province_code": p, "S-COV": te["comp_p"].iloc[i], "S-PCAL": ph * pc[i], "S-PCAL-GB": ph * pg[i],
                        "p_hunger": ph, "p_price_raw": pp, "p_price_cal": pc[i], "p_price_gb": pg[i],
                        "cal_fitted": f1, "gb_fitted": f2})
    return P.merge(pd.DataFrame(add), on=["t", "province_code"], how="left"), X


def quarter_generalization(P, arm, ref="B-PERSIST"):
    """Pre-set Lead-1 generalization criteria (GENERALIZATION_CRITERIA.md), applied to any arm and lead."""
    yh = np.where(P[arm].notna(), (P[arm] >= 0.5).astype(int), 1 - P["y"])
    P = P.assign(c=(yh == P["y"]).astype(int), r=((P[ref] >= 0.5).astype(int) == P["y"]).astype(int))
    g = P.groupby("target_q").agg(c=("c", "sum"), r=("r", "sum"), n=("y", "size"))
    w, l = int((g.c > g.r).sum()), int((g.c < g.r).sum())
    p = sum(comb(w + l, i) for i in range(w, w + l + 1)) / 2 ** (w + l) if w + l else 1.0
    early = P["target_q"] < "2025"
    ch = (P[ref] >= 0.5).astype(int) != P["y"]
    yh_s = pd.Series(yh, index=P.index)
    rec = lambda m: ((yh_s[m] == 1) & (P.y[m] == 1)).sum() / max(P.y[m].sum(), 1)  # noqa: E731
    rng = np.random.default_rng(89)
    qs = g.index.to_numpy()
    boot = [g.loc[s, "c"].sum() / g.loc[s, "n"].sum() for s in (rng.choice(qs, len(qs)) for _ in range(2000))]
    out = {"majority_quarters": float((g.c >= 3).mean()), "early_acc": float(P.c[early].mean()),
           "late_acc": float(P.c[~early].mean()), "wins": w, "losses": l, "ties": int((g.c == g.r).sum()), "sign_p": p,
           "recall_pooled": float(rec(P.index == P.index)), "recall_early": float(rec(early)), "recall_late": float(rec(~early)),
           "changing_acc": float(P.c[ch].mean()), "changing_n": int(ch.sum()),
           "acc_ci95_quarter_block": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
           "per_quarter_correct": g["c"].astype(int).to_dict()}
    a = out["majority_quarters"] >= 0.8
    b = out["early_acc"] >= 0.75 and out["late_acc"] >= 0.75
    c = w > l and p < 0.10
    dd = out["recall_pooled"] >= 0.5
    e = out["changing_acc"] >= 0.5
    out["criteria"] = {"a": a, "b": b, "c": c, "d": dd, "e": e}
    out["verdict"] = ("Consistent across quarters" if all((a, b, c, dd, e)) else
                      "Partially generalized" if out["majority_quarters"] >= 0.6 else "Not demonstrated to generalize")
    return out


def price_scorecard(P, k, d):
    lab = price_labels(d)
    M = P.assign(q=P["target_q"].map(L.qi)).merge(lab, on=["province_code", "q"])
    out = {}
    for c in ("p_price_raw", "p_price_cal", "p_price_gb"):
        D = M[M[c].notna()]
        out[c] = E.metrics(D["y_price"], (D[c] >= 0.5).astype(int), D[c])
    return out


if __name__ == "__main__":
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = HERE.parent / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    d, x = E.data()
    sub, W = C.load_sub()
    w = C.load_world()
    arms = ["S-COV", "S-PCAL", "S-PCAL-GB", "S-SIM", "S-COMP", "HYB-GBA-SIM"]
    R.PRIMARY[:] = arms
    summ = {"stamp": stamp, "protocol_sha256": (HERE.parent / "PROTOCOL.sha256").read_text().split()[0], "leads": {}}
    for k in (1, 2):
        P, X = run(k, d, x, sub, W, w)
        P.to_csv(o / f"predictions_k{k}.csv", index=False)
        res, tests = R.evaluate(P)
        gen = {a: quarter_generalization(P, a) for a in arms}
        summ["leads"][k] = {"metrics": {a: res[a] for a in arms + R.BASELINES if a in res}, "tests": tests,
                            "pass": {a: R.passes(res, tests, a) for a in arms}, "generalization": gen,
                            "price_scorecard": price_scorecard(P, k, d)}
        print(f"k={k}")
        for a in ["B-PERSIST", "B-CLIM", "B-AL"] + arms:
            m = res[a]["all_rows_unissued_wrong"]
            ps = summ["leads"][k]["pass"].get(a, {})
            g = gen.get(a, {})
            th = {n.split(" vs ")[1]: round(v["p_holm"], 3) for n, v in tests.items() if n.startswith(a + " vs")}
            print(f"  {a:12s} acc={m['accuracy']:.3f} ({m['TP'] + m['TN']}/65) bal={m['balanced_accuracy'] or 0:.3f} "
                  f"recH={m['recall_HIGH'] or 0:.2f} prec={m['precision'] or 0:.2f} brier={m['brier']:.3f} PASS={ps.get('PASS')} "
                  f"holm={th} | quarters W/L/T={g.get('wins')}/{g.get('losses')}/{g.get('ties')} "
                  f"early/late={g.get('early_acc', 0):.2f}/{g.get('late_acc', 0):.2f} {g.get('verdict', '')}", flush=True)
        sc = summ["leads"][k]["price_scorecard"]
        print("  price scorecard:", {c: (sc[c]["n"], round(sc[c]["accuracy"], 3), round(sc[c].get("brier", float("nan")), 3))
                                      for c in sc}, flush=True)
    (o / "metrics.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8")
    print(o)

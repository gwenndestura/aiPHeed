"""E23-B improvement runner (IMPROVEMENT_PROTOCOL_E23B.md, frozen). Reuses E23 data/frame and the SEALED E23
baseline predictions (identical rows). Usage: python -B runner/run_e23b.py <E23 run id>"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import warnings  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e23_lib as L  # noqa: E402
import run_e23 as R  # noqa: E402

EXP = guard.EXP
qk, qs = L.qk, L.qs
LAG = ["S1_last", "margin_last", "y_last", "D_last", "D_mean4", "H_last_pub", "H_roll4", "H_trend"]
COMPACT_GOV = ["food_cpi_yoy", "cpi_dev", "unemployment_rate", "rice_price_regular_accel"]
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7]
GRID = [dict(min_child_samples=m, n_estimators=n, reg_lambda=r) for m in (5, 10) for n in (50, 150) for r in (1.0, 10.0)]
FIXED = dict(objective="binary", num_leaves=3, max_depth=2, learning_rate=0.05, colsample_bytree=0.8, subsample=1.0,
             random_state=42, n_jobs=1, deterministic=True, force_col_wise=True, verbosity=-1)


def check_frozen():
    for ln in (EXP / "runner" / "PROTOCOL_E23B_SHA256.txt").read_text(encoding="utf-8").splitlines():
        p = ln.split()
        if len(p) == 2 and len(p[0]) == 64 and hashlib.sha256((EXP / p[1]).read_bytes()).hexdigest() != p[0]:
            raise SystemExit(f"E23-B: {p[1]} differs from its frozen hash; stop.")


def lag_features(te_or_tr: pd.DataFrame, comp: pd.DataFrame, rounds, tau: float, t: int) -> pd.DataFrame:
    """Lag block for rows whose feature quarter is t' (column 't'); labels must be published before O(t')."""
    cq = comp[comp["S1"].notna()].copy()
    cq["tq"] = cq["quarter"].map(qk)
    cache = {}
    out = []
    for _, r in te_or_tr.iterrows():
        tt = int(r["t"])
        if (tt, r["province_code"]) not in cache:
            pubq = sorted({q for q in cq["quarter"].unique() if L.label_published(rounds, q, tt)}, key=qk)
            g = cq[(cq["province_code"] == r["province_code"]) & cq["quarter"].isin(pubq)].sort_values("tq")
            if g.empty:
                v = dict.fromkeys(LAG, np.nan)
            else:
                last = g.iloc[-1]
                v = {"S1_last": last["S1"], "D_last": last["D"], "D_mean4": g["D"].iloc[-4:].mean(),
                     "H_last_pub": last["H"], "H_roll4": g["H"].iloc[-4:].mean()}
            cache[(tt, r["province_code"])] = v
        v = dict(cache[(tt, r["province_code"])])
        v["margin_last"] = v["S1_last"] - tau if v.get("S1_last") == v.get("S1_last") else np.nan
        v["y_last"] = float(v["S1_last"] > tau) if v.get("S1_last") == v.get("S1_last") else np.nan
        v["H_trend"] = r["sws_hunger"] - v["H_last_pub"] if v.get("H_last_pub") == v.get("H_last_pub") else np.nan
        out.append(v)
    return pd.concat([te_or_tr.reset_index(drop=True), pd.DataFrame(out)[LAG]], axis=1)


def fit_predict(tr, cols, cfg, te):
    from lightgbm import LGBMClassifier
    y = tr["y"].to_numpy(int)
    cols = L.usable_cols(tr, cols)
    if y.mean() in (0.0, 1.0) or not cols:
        return np.full(len(te), float(y.mean()))
    p = y.mean()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = LGBMClassifier(**FIXED, **cfg, scale_pos_weight=(1 - p) / p).fit(tr[cols], y)
    return m.predict_proba(te[cols])[:, 1]


def best_threshold(y, p):
    accs = {th: float(((p >= th).astype(int) == y).mean()) for th in THRESHOLDS}
    top = max(accs.values())
    return min([th for th, a in accs.items() if a == top], key=lambda th: abs(th - 0.5)), top


def select(tr, sets, k):
    vq = sorted(tr["target_q"].unique())[-3:]
    cands = []
    for sname, cols in sets.items():
        for gi, cfg in enumerate(GRID):
            ys, ps = [], []
            for v in vq:
                a, b = tr[tr["target_q"] <= v - k - 1], tr[tr["target_q"] == v]
                if a["target_q"].nunique() < 4 or a["y"].nunique() < 2 or b.empty:
                    continue
                ys.append(b["y"].to_numpy(int)); ps.append(fit_predict(a, cols, cfg, b))
            if not ys:
                continue
            y, p = np.concatenate(ys), np.concatenate(ps)
            th, acc = best_threshold(y, p)
            cands.append((-acc, L.logloss(y, p), list(sets).index(sname), gi, sname, cfg, th, acc))
    if not cands:
        return {"set": "FA", "cfg": GRID[0], "threshold": 0.5, "inner_accuracy": None, "fallback": True}
    c = sorted(cands, key=lambda x: x[:4])[0]
    return {"set": c[4], "cfg": c[5], "threshold": c[6], "inner_accuracy": c[7], "fallback": False}


def main():
    R.check_frozen()
    check_frozen()
    e23run = sys.argv[1]
    runid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_E23B"
    rd = EXP / "runs" / runid
    rd.mkdir(parents=True)
    log = []
    allow = guard.verify_allowlist()
    comp, rounds, ff, gov_cols, S = R.load(log)
    comp = comp.copy()
    X = L.build_frame(ff, rounds, gov_cols)
    gov = gov_cols + ["sws_hunger"]
    sets = {"FA": LAG + gov + L.NLP, "FB": LAG + gov, "FC": LAG + COMPACT_GOV + ["FSSI", "FSSI_lag1"]}
    pairs = {k: L.pairs_for(X, S, k) for k in L.LEADS}
    allp = pd.concat(pairs.values(), ignore_index=True)
    out = {}
    for mode in ("origin", "fixed"):
        sealed = EXP / "runs" / e23run / f"predictions_{mode}.csv"
        seal = json.loads((EXP / "runs" / e23run / f"SEAL_{mode}.json").read_text(encoding="utf-8"))
        assert hashlib.sha256(sealed.read_bytes()).hexdigest() == seal["sha256"]
        B = pd.read_csv(sealed, dtype={"province_code": str})
        rows, meta = [], {}
        for (k, fq), g in B[B["model"] == L.PROPOSED].groupby(["lead", "feature_quarter"]):
            t = qk(fq)
            tau = float(g["threshold"].iloc[0])
            te = pairs[k][pairs[k]["t"] == t].sort_values("province_code").reset_index(drop=True)
            ok = {q: L.label_published(rounds, q, t) for q in allp["target_quarter"].unique()}
            tr = pairs[k][pairs[k]["target_quarter"].map(ok) & (pairs[k]["t"] >= qk(L.FIRST_Q))].copy()
            tr["y"] = (tr["S1"] > tau).astype(int)
            te["y"] = (te["S1"] > tau).astype(int)
            assert te["y"].tolist() == g.sort_values("province_code")["y"].tolist()
            tr = lag_features(tr, comp, rounds, tau, t)
            te = lag_features(te, comp, rounds, tau, t)
            sel = select(tr, sets, k)
            p = fit_predict(tr, sets[sel["set"]], sel["cfg"], te)
            meta[f"k{k}_{fq}"] = {**sel, "tau": tau}
            for i, r in te.iterrows():
                rows.append({"threshold_mode": mode, "lead": k, "feature_quarter": fq, "origin": g["origin"].iloc[0],
                             "target_quarter": r["target_quarter"], "province_code": r["province_code"],
                             "model": "IMP_lgbm_selected", "score": float(p[i]), "decision_threshold": sel["threshold"],
                             "pred": int(p[i] >= sel["threshold"]), "y": int(r["y"])})
        P = pd.DataFrame(rows)
        b = P.to_csv(index=False, lineterminator="\n").encode()
        (rd / f"predictions_imp_{mode}.csv").write_bytes(b)
        (rd / f"SEAL_imp_{mode}.json").write_text(json.dumps({"sha256": hashlib.sha256(b).hexdigest(),
                                                                "rows": len(P)}), encoding="utf-8")
        (rd / f"selection_{mode}.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
        out[mode] = score(P, B)
    (rd / "results_e23b.json").write_text(json.dumps(out, indent=1, default=R.jd), encoding="utf-8")
    (rd / "manifest.json").write_text(json.dumps({"run": runid, "e23_run": e23run, "allowlist": allow,
                                                  "access_log": guard.ACCESS_LOG, "integrity": log,
                                                  "protocol": (EXP / "runner" / "PROTOCOL_E23B_SHA256.txt").read_text()},
                                                 indent=1, default=R.jd), encoding="utf-8")
    print(runid)


def score(P, B):
    res = {}
    for k in sorted(P["lead"].unique()):
        imp = P[P["lead"] == k].sort_values(["origin", "province_code"])
        bl = B[B["lead"] == k]
        y = imp["y"].to_numpy()
        g = imp["origin"].to_numpy()
        accs = {"IMP_lgbm_selected": float((imp["pred"] == imp["y"]).mean()),
                "REF_always_HIGH": float(y.mean())}
        corr = {"IMP_lgbm_selected": (imp["pred"].to_numpy() == y).astype(float)}
        for m in L.BASELINES + [L.PROPOSED]:
            d = bl[bl["model"] == m].sort_values(["origin", "province_code"])
            assert (d["province_code"].to_numpy() == imp["province_code"].to_numpy()).all()
            c = ((d["score"].to_numpy() >= 0.5).astype(int) == y).astype(float)
            corr[m] = c
            accs[m] = float(c.mean())
        strongest = max(L.BASELINES, key=lambda m: accs[m])
        tests = {}
        for m in L.BASELINES:
            dO = pd.DataFrame({"o": g, "d": corr[m] - corr["IMP_lgbm_selected"]}).groupby("o")["d"].mean().to_numpy()
            sf = L.signflip_brier(dO)              # one-sided: mean(baseline - IMP) < 0  <=> IMP better
            b01 = int(((corr["IMP_lgbm_selected"] == 1) & (corr[m] == 0)).sum())
            b10 = int(((corr["IMP_lgbm_selected"] == 0) & (corr[m] == 1)).sum())
            from scipy.stats import binomtest
            mc = binomtest(b01, b01 + b10, 0.5, alternative="greater").pvalue if b01 + b10 else 1.0
            loo = [float(np.mean(corr["IMP_lgbm_selected"][g != o]) - np.mean(corr[m][g != o])) for o in np.unique(g)]
            tests[m] = {"acc_diff": accs["IMP_lgbm_selected"] - accs[m], "signflip_p": sf["p_one_sided"],
                        "origins_better": sf["origins_better"], "origins_worse": sf["origins_worse"],
                        "mcnemar_exact_p": float(mc), "imp_only_correct": b01, "baseline_only_correct": b10,
                        "loo_min": min(loo), "loo_max": max(loo)}
        t = tests[strongest]
        beats = bool(t["acc_diff"] > 0 and t["signflip_p"] < 0.05 and t["origins_better"] > t["origins_worse"])
        nH, nL = int(y.sum()), int((1 - y).sum())
        res[str(k)] = {"n_origins": int(len(np.unique(g))), "n_rows": int(len(y)), "HIGH": nH, "LOW": nL,
                       "evaluable_E23_rule": bool(len(np.unique(g)) >= 8 and nH >= 5 and nL >= 5),
                       "accuracy": accs, "imp_metrics": L.cls_metrics(y, imp["score"]) | {
                           "accuracy_at_selected_threshold": accs["IMP_lgbm_selected"]},
                       "exceeds_75": accs["IMP_lgbm_selected"] > 0.75, "strongest_baseline": strongest,
                       "beats_strongest": beats, "tests": tests,
                       "imp_confusion": {"TP": int(((imp["pred"] == 1) & (imp["y"] == 1)).sum()),
                                         "FP": int(((imp["pred"] == 1) & (imp["y"] == 0)).sum()),
                                         "FN": int(((imp["pred"] == 0) & (imp["y"] == 1)).sum()),
                                         "TN": int(((imp["pred"] == 0) & (imp["y"] == 0)).sum())}}
    return res


if __name__ == "__main__":
    main()

"""E24 runner (FROZEN_EVALUATION_PROTOCOL.md; hashes checked first).
Usage: python -B runner/run_e24.py"""
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
import platform  # noqa: E402
import warnings  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e23_lib as L  # noqa: E402
import run_e23 as R  # noqa: E402

EXP = guard.EXP
qk, qs = L.qk, L.qs
E23RUN = guard.E23_DIR / "runs" / "20261013T152113Z"
P_COLS = ["v_last", "margin_last", "y_last", "v_mean4", "v_diff"]
LRC_GRID = [0.01, 0.1, 1.0, 10.0]
REQUIRED = ["B1_naive_persistence", "B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only", "B5_lgbm_gov_only",
            "B6_lgbm_nlp_only", "PROPOSED_lgbm_combined"]
POOL = ["B1_naive_persistence", "PROPOSED_lgbm_combined", "ABL_lgbm_GNP", "ABL_lrc_GNP", "ABL_lgbm_GP", "ABL_lr_GP"]


def check_frozen():
    for ln in (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").splitlines():
        p = ln.split()
        if len(p) == 2 and len(p[0]) == 64 and hashlib.sha256((EXP / p[1]).read_bytes()).hexdigest() != p[0]:
            raise SystemExit(f"E24: {p[1]} differs from its frozen hash; stop.")


# ------------------------------------------------------------------------------------------ data
def load():
    log = []
    comp, rounds, ff, gov_cols, S = R.load(log)
    cpi26 = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.COLL / "provincial_food_cpi_yoy_2026H1_raw.csv")),
                        dtype={"province_code": str})
    cpi26["quarter"] = cpi26["reference_month"].map(lambda m: f"{m[:4]}-Q{(int(m[5:7]) - 1) // 3 + 1}")
    F = cpi26.groupby(["province_code", "quarter"])["food_cpi_yoy_pct_raw"].mean().reset_index(name="F")
    F["D"] = F["F"] - F.groupby("quarter")["F"].transform("mean")
    D = pd.concat([comp[comp["D"].notna()][["province_code", "quarter", "D"]], F[["province_code", "quarter", "D"]]],
                  ignore_index=True)
    assert D.groupby("quarter").size().eq(5).all()
    V = {"T1": S.rename(columns={"S1": "v"})[["province_code", "quarter", "v"]],
         "T2": D.rename(columns={"D": "v"})}
    for k in V:
        V[k] = V[k].assign(tq=V[k]["quarter"].map(qk)).reset_index(drop=True)
    return comp, rounds, ff, gov_cols, V, log


def make_pub(target, rounds):
    if target == "T1":
        return lambda q, t: L.label_published(rounds, q, t)
    return lambda q, t: qk(q) <= t - 1


def threshold(target, V, pub, t):
    if target == "T2":
        return 0.0
    ok = V[V["quarter"].map(lambda q: pub(q, t))]
    return float(ok["v"].median())


def pblock(V, pub, rows: pd.DataFrame, tau: float, cache: dict) -> pd.DataFrame:
    vals = []
    for t2, pc in zip(rows["t"], rows["province_code"]):
        key = (int(t2), pc)
        if key not in cache:
            g = V[(V["province_code"] == pc) & V["quarter"].map(lambda q: pub(q, int(t2)))].sort_values("tq")
            if g.empty:
                cache[key] = (np.nan, np.nan, np.nan)
            else:
                v = g["v"].to_numpy()
                cache[key] = (v[-1], v[-4:].mean(), v[-1] - v[-2] if len(v) > 1 else np.nan)
        last, m4, d = cache[key]
        vals.append([last, last - tau, float(last > tau) if last == last else np.nan, m4, d])
    return pd.concat([rows.reset_index(drop=True), pd.DataFrame(vals, columns=P_COLS)], axis=1)


def pairs(X, V, k):
    Lb = V.assign(t=V["tq"] - k)[["province_code", "t", "v", "quarter"]].rename(columns={"quarter": "target_quarter"})
    P = X.merge(Lb, on=["province_code", "t"], how="inner")
    P["lead"] = k
    P["target_q"] = P["target_quarter"].map(qk)
    return P


# ------------------------------------------------------------------------------------------ models
def fit_lrc(tr, cols, te, k):
    """Logistic regression with C chosen by nested chronological log loss (training rows only)."""
    vq = sorted(tr["target_q"].unique())[-3:]
    best, bs = 1.0, np.inf
    for C in LRC_GRID:
        lls = []
        for v in vq:
            a, b = tr[tr["target_q"] <= v - k - 1], tr[tr["target_q"] == v]
            if a["target_q"].nunique() < 4 or a["y"].nunique() < 2 or b.empty:
                continue
            lls.append(L.logloss(b["y"], lr_c(a, cols, b, C)))
        s = np.mean(lls) if lls else np.inf
        if s < bs - 1e-12:
            best, bs = C, s
    return lr_c(tr, cols, te, best), best


def lr_c(tr, cols, te, C):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    y = tr["y"].to_numpy(int)
    cols = L.usable_cols(tr, cols)
    if y.mean() in (0.0, 1.0) or not cols:
        return np.full(len(te), float(y.mean()))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=C, max_iter=5000))
        return m.fit(tr[cols], y).predict_proba(te[cols])[:, 1]


def nested_lgbm(tr_s, tr_p, cols, te, k):
    sel = L.inner_select(tr_s, tr_p, cols, k)
    p, mdl, use = L.lgbm_predict(tr_s, tr_p, cols, sel["config"], te, k)
    return p, mdl, use, sel


def inner_pool_accuracy(member, tr_s, cols_of, k, V, tau):
    vq = sorted(tr_s["target_q"].unique())[-3:]
    ys, ps = [], []
    for v in vq:
        a, b = tr_s[tr_s["target_q"] <= v - k - 1], tr_s[tr_s["target_q"] == v]
        if a["target_q"].nunique() < 4 or a["y"].nunique() < 2 or b.empty:
            continue
        if member == "B1_naive_persistence":
            known = V[V["tq"] <= v - k - 1]
            last = known.sort_values("tq").groupby("province_code")["v"].last()
            p = b["province_code"].map(lambda pc: float(last.get(pc, np.nan) > tau)).to_numpy()
        elif "lr" in member:
            p = lr_c(a, cols_of[member], b, 1.0)
        else:
            p, _, _ = L.lgbm_predict(a, a, cols_of[member], L.GRID[0], b, k)
        ys.append(b["y"].to_numpy()); ps.append((np.asarray(p) >= 0.5).astype(int))
    if not ys:
        return None
    y, p = np.concatenate(ys), np.concatenate(ps)
    return float((y == p).mean())


# ------------------------------------------------------------------------------------------ run one target
def run_target(target, X, V, rounds, gov_cols):
    pub = make_pub(target, rounds)
    G = gov_cols + ["sws_hunger"]
    N = L.NLP
    cols_of = {"B2_lr_combined": N + G, "B3_lr_gov_only": G, "B4_lr_nlp_only": N, "B5_lgbm_gov_only": G,
               "B6_lgbm_nlp_only": N, "PROPOSED_lgbm_combined": N + G,   # E23 column order (colsample is order-dependent)
               "ABL_lr_P": P_COLS, "ABL_lr_GP": G + P_COLS, "ABL_lr_NP": N + P_COLS, "ABL_lr_GNP": G + N + P_COLS,
               "ABL_lgbm_P": P_COLS, "ABL_lgbm_GP": G + P_COLS, "ABL_lgbm_NP": N + P_COLS, "ABL_lgbm_GNP": G + N + P_COLS,
               "ABL_lrc_GNP": G + N + P_COLS}
    PR = {k: pairs(X, V, k) for k in L.LEADS}
    allp = pd.concat(PR.values(), ignore_index=True)
    preds, meta = [], {}
    tmin, tmax = qk(L.FIRST_Q), qk(L.LAST_FEATURE_Q)
    for k in L.LEADS:
        for t in range(tmin, tmax + 1):
            te = PR[k][PR[k]["t"] == t].sort_values("province_code").reset_index(drop=True)
            if len(te) != 5:
                continue
            tau = threshold(target, V, pub, t)
            okq = {q: pub(q, t) for q in allp["target_quarter"].unique()}
            pubp = allp[allp["target_quarter"].map(okq) & (allp["t"] >= tmin)].copy()
            pubp["y"] = (pubp["v"] > tau).astype(int)
            tr_s = pubp[pubp["lead"] == k].copy()
            if tr_s["target_q"].nunique() < L.MIN_TRAIN_QUARTERS:
                continue
            assert pubp["target_q"].max() <= t - 1                       # C7: no training target at/after test
            assert all(pub(q, t) for q in pubp["target_quarter"].unique())  # C7: every training label published
            cache = {}
            tr_s = pblock(V, pub, tr_s, tau, cache)
            tr_p = pblock(V, pub, pubp, tau, cache)
            te = pblock(V, pub, te.assign(y=(te["v"] > tau).astype(int)), tau, cache)
            assert (te["t"] == t).all()
            s, m = {}, {"lead": k, "feature_quarter": qs(t), "target_quarter": te["target_quarter"].iloc[0],
                        "threshold": tau, "train_HIGH": int(tr_s["y"].sum()), "train_LOW": int((1 - tr_s["y"]).sum()),
                        "test_HIGH": int(te["y"].sum()), "test_LOW": int((1 - te["y"]).sum()),
                        "n_train_quarters": int(tr_s["target_q"].nunique())}
            s["B1_naive_persistence"] = te["y_last"].to_numpy(float)
            s["MAJ_training_majority"] = np.full(5, 1.0 if tr_s["y"].mean() >= 0.5 else 0.0)
            for name in ("B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only", "ABL_lr_P", "ABL_lr_GP", "ABL_lr_NP",
                         "ABL_lr_GNP"):
                s[name] = L.fit_lr(tr_s, cols_of[name], te)
            s["ABL_lrc_GNP"], m["lrc_C"] = fit_lrc(tr_s, cols_of["ABL_lrc_GNP"], te, k)
            for name in ("B5_lgbm_gov_only", "B6_lgbm_nlp_only", "PROPOSED_lgbm_combined", "ABL_lgbm_P", "ABL_lgbm_GP",
                         "ABL_lgbm_NP", "ABL_lgbm_GNP"):
                p, mdl, use, sel = nested_lgbm(tr_s, tr_p, cols_of[name], te, k)
                s[name] = p
                m[f"cfg_{name}"] = sel["config"]
                if name == "PROPOSED_lgbm_combined" and mdl is not None:
                    m["shap_mean_abs"] = L.shap_abs(mdl, te, use, k).abs().mean().to_dict()
            inner = {mb: inner_pool_accuracy(mb, tr_s, cols_of, k, V, tau) for mb in POOL}
            best = "B1_naive_persistence"
            for mb in POOL[1:]:
                if inner[mb] is not None and (inner[best] is None or inner[mb] > inner[best] + 1e-12):
                    best = mb
            s["FINAL_E24F"] = s[best]
            m["final_choice"], m["inner_accuracy"] = best, inner
            meta[f"k{k}_{qs(t)}"] = m
            for arm, v in s.items():
                for i, r in te.iterrows():
                    preds.append({"target": target, "lead": k, "feature_quarter": qs(t),
                                  "origin": L.origin_of(t).date().isoformat(), "target_quarter": r["target_quarter"],
                                  "province_code": r["province_code"], "model": arm, "score": float(v[i]),
                                  "y": int(r["y"]), "y_last": r["y_last"], "value": float(r["v"]), "threshold": tau})
    return pd.DataFrame(preds), meta


# ------------------------------------------------------------------------------------------ scoring
def metrics(y, s):
    m = L.cls_metrics(y, s)
    m["balanced_accuracy"] = (None if m["recall"] is None or m["specificity"] is None
                              else (m["recall"] + m["specificity"]) / 2)
    return m


def compare(d, a, b):
    da = d[d["model"] == a].sort_values(["origin", "province_code"])
    db = d[d["model"] == b].sort_values(["origin", "province_code"])
    assert (da["province_code"].to_numpy() == db["province_code"].to_numpy()).all()
    g, y = da["origin"].to_numpy(), da["y"].to_numpy()
    ca = ((da["score"].to_numpy() >= .5).astype(int) == y).astype(float)
    cb = ((db["score"].to_numpy() >= .5).astype(int) == y).astype(float)
    acc_o = pd.DataFrame({"o": g, "d": cb - ca}).groupby("o")["d"].mean().to_numpy()      # <0 => a better
    bri_o = pd.DataFrame({"o": g, "d": (da["score"].to_numpy() - y) ** 2 - (db["score"].to_numpy() - y) ** 2}
                         ).groupby("o")["d"].mean().to_numpy()
    sa, sb = L.signflip_brier(acc_o), L.signflip_brier(bri_o)
    loo = [float(ca[g != o].mean() - cb[g != o].mean()) for o in np.unique(g)]
    auc = L.paired_auc_perm(g, y, da["score"].to_numpy(), db["score"].to_numpy()) if y.min() != y.max() else {}
    return {"acc_diff": float(ca.mean() - cb.mean()), "acc_p_one_sided": sa["p_one_sided"],
            "origins_better": sa["origins_better"], "origins_worse": sa["origins_worse"],
            "brier_diff": float(bri_o.mean()), "brier_p_one_sided": sb["p_one_sided"],
            "auc_diff": auc.get("auc_diff"), "auc_p_one_sided": auc.get("p_one_sided"),
            "loo_acc_diff_min": min(loo), "loo_acc_diff_max": max(loo)}


def score_target(P, meta, target):
    rows, out = [], {}
    models = list(P["model"].unique())
    for k in sorted(P["lead"].unique()):
        d = P[P["lead"] == k]
        f = d[d["model"] == "FINAL_E24F"]
        nH, nL, no = int(f["y"].sum()), int((1 - f["y"]).sum()), int(f["origin"].nunique())
        ev = no >= L.MIN_ORIGINS and nH >= L.MIN_PER_CLASS and nL >= L.MIN_PER_CLASS
        mm = {}
        for m in models:
            dm = d[d["model"] == m].sort_values(["origin", "province_code"])
            mm[m] = metrics(dm["y"], dm["score"])
            rows.append({"target": target, "lead": int(k), "model": m, "n_rows": len(dm), "n_test_quarters": no,
                         "HIGH": nH, "LOW": nL, "evaluable": ev,
                         **{q: mm[m][q] for q in ("accuracy", "balanced_accuracy", "precision", "recall", "F1",
                                                  "specificity", "ROC_AUC", "Brier", "TP", "FP", "FN", "TN")}})
        strongest = max(REQUIRED[:-1], key=lambda m: (mm[m]["accuracy"], -mm[m]["Brier"]))
        tests = {a: {b: compare(d, a, b) for b in REQUIRED[:-1] + ["MAJ_training_majority"] + ([] if a == "PROPOSED_lgbm_combined" else ["PROPOSED_lgbm_combined"])}
                 for a in ("FINAL_E24F", "PROPOSED_lgbm_combined")}
        for a in tests:
            hp = L.holm({b: tests[a][b]["acc_p_one_sided"] for b in REQUIRED[:-1]})
            for b in REQUIRED[:-1]:
                tests[a][b]["acc_p_holm"] = hp[b]
        fin = d[d["model"] == "FINAL_E24F"].sort_values(["origin", "province_code"])
        changed = fin["y"].to_numpy() != fin["y_last"].to_numpy()
        corr = ((fin["score"].to_numpy() >= .5).astype(int) == fin["y"].to_numpy())
        g, y = fin["origin"].to_numpy(), fin["y"].to_numpy()
        ci = L.cluster_boot_auc(g, y, fin["score"].to_numpy()) if ev else {"ci_low": None}
        t_s = tests["FINAL_E24F"][strongest]
        t_p = tests["FINAL_E24F"]["B1_naive_persistence"]
        crit = {
            "C1_accuracy_gt_75": mm["FINAL_E24F"]["accuracy"] > 0.75,
            "C2_beats_strongest": bool(t_s["acc_diff"] > 0 and t_s["acc_p_one_sided"] < 0.05 and t_s["brier_diff"] <= 0),
            "C3_not_HIGH_dominance": bool((mm["FINAL_E24F"]["balanced_accuracy"] or 0) >= 0.60 and
                                          (mm["FINAL_E24F"]["balanced_accuracy"] or 0) >
                                          (mm[strongest]["balanced_accuracy"] or 0)),
            "C4_defensible_across_folds": bool(t_s["origins_better"] > t_s["origins_worse"] and t_s["loo_acc_diff_min"] >= 0),
            "C5_info_beyond_persistence": bool(int((corr & changed).sum()) > int((~corr & ~changed).sum())),
            "C6_reliability_rule": bool(ev and ci.get("ci_low") is not None and ci["ci_low"] > 0.5 and
                                        t_p["brier_p_one_sided"] < 0.05),
            "C9_generalizes_unseen": "NOT ASSESSABLE (no untouched authorized holdout)"}
        share = pd.Series([m["final_choice"] for kk, m in meta.items() if kk.startswith(f"k{k}_")]).value_counts().to_dict()
        fold = [{"origin": o, "target_quarter": gg["target_quarter"].iloc[0], "HIGH": int(gg["y"].sum()),
                 "LOW": int((1 - gg["y"]).sum()), "label_changes": int((gg["y"] != gg["y_last"]).sum()),
                 "acc_final": float(((gg["score"] >= .5).astype(int) == gg["y"]).mean())}
                for o, gg in fin.groupby("origin")]
        out[str(k)] = {"n_test_quarters": no, "HIGH": nH, "LOW": nL, "evaluable": ev, "strongest_baseline": strongest,
                       "metrics": mm, "tests": tests, "criteria": crit, "final_choice_share": share,
                       "label_change_rows": int(changed.sum()), "final_correct_on_changed": int((corr & changed).sum()),
                       "final_wrong_on_unchanged": int((~corr & ~changed).sum()), "auc_ci_final": ci, "folds": fold}
    return pd.DataFrame(rows), out


def main():
    check_frozen()
    runid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rd = EXP / "runs" / runid
    rd.mkdir(parents=True)
    allow = guard.verify_allowlist()
    comp, rounds, ff, gov_cols, V, log = load()
    X = L.build_frame(ff, rounds, gov_cols)
    allrows, results, seals = [], {}, {}
    for target in ("T1", "T2"):
        P, meta = run_target(target, X, V[target], rounds, gov_cols)
        b = P.to_csv(index=False, lineterminator="\n").encode()
        (rd / f"predictions_{target}.csv").write_bytes(b)
        seals[target] = hashlib.sha256(b).hexdigest()
        (rd / f"SEAL_{target}.json").write_text(json.dumps({"sha256": seals[target], "rows": len(P)}), encoding="utf-8")
        Pr = pd.read_csv(rd / f"predictions_{target}.csv", dtype={"province_code": str})
        rows, res = score_target(Pr, meta, target)
        allrows.append(rows)
        results[target] = res
        (rd / f"fold_meta_{target}.json").write_text(json.dumps(meta, indent=1, default=R.jd), encoding="utf-8")
        if target == "T1":   # reproducibility: required models must equal E23's sealed predictions
            E = pd.read_csv(E23RUN / "predictions_origin.csv", dtype={"province_code": str})
            assert hashlib.sha256((E23RUN / "predictions_origin.csv").read_bytes()).hexdigest() == \
                json.loads((E23RUN / "SEAL_origin.json").read_text())["sha256"]
            mx = 0.0
            for m in REQUIRED:
                a = Pr[Pr["model"] == m].sort_values(["lead", "origin", "province_code"])
                e = E[E["model"] == m].sort_values(["lead", "origin", "province_code"])
                assert len(a) == len(e) and (a["y"].to_numpy() == e["y"].to_numpy()).all()
                mx = max(mx, float(np.abs(a["score"].to_numpy() - e["score"].to_numpy()).max()))
            results["T1_matches_E23_required_models_max_abs_diff"] = mx
    pd.concat(allrows).to_csv(rd / "metrics_all.csv", index=False, lineterminator="\n")
    (rd / "results.json").write_text(json.dumps(results, indent=1, default=R.jd), encoding="utf-8")
    import lightgbm, sklearn, scipy
    man = {"run_id": runid, "seals": seals, "allowlist": allow, "integrity": log, "access_log": guard.ACCESS_LOG,
           "reference_reads": guard.REFERENCE_READS,
           "versions": {"python": platform.python_version(), "lightgbm": lightgbm.__version__,
                        "sklearn": sklearn.__version__, "scipy": scipy.__version__, "numpy": np.__version__,
                        "pandas": pd.__version__},
           "protocol": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8")}
    (rd / "manifest.json").write_text(json.dumps(man, indent=1, default=R.jd), encoding="utf-8")
    print(runid, seals)
    for t in ("T1", "T2"):
        for k, v in results[t].items():
            print(t, k, v["n_test_quarters"], v["HIGH"], v["LOW"], v["evaluable"], "FINAL acc",
                  round(v["metrics"]["FINAL_E24F"]["accuracy"], 3), "strongest", v["strongest_baseline"],
                  round(v["metrics"][v["strongest_baseline"]]["accuracy"], 3), {c: x for c, x in v["criteria"].items()})


if __name__ == "__main__":
    main()

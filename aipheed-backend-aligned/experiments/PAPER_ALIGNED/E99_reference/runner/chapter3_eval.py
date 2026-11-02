"""E99 (PROTOCOL.md): the thesis pipeline as written in Chapter III, on the authorized 2021-Q1..2026-Q3 window.
Eq. 3 label, Algorithm 3 lead-time discovery, Algorithm 4 Optuna TPE with holdout acceptance, the six Chapter I
comparators (plus prevalence, FIRI v2 and the Chapter III blend) on identical folds, SHAP for H1, hypothesis decisions,
prospective seal. Run from backend/:
    py -3.13 ../aipheed-backend-aligned/experiments/E99_Chapter3_Evaluation/runner/chapter3_eval.py
"""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
import warnings
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
E99 = HERE.parent
sys.path.insert(0, str(E99.parent / "E97_Validation_Completion" / "runner"))
import common as C  # noqa: E402

warnings.filterwarnings("ignore")
SEED = 99
NLP = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel", "trigger_market", "trigger_climate", "trigger_employment",
       "trigger_ofw_remittance", "trigger_fish_kill"]
GOV = ["food_cpi_dev", "unemployment_rate_prev", "rice_change_prev"]
ALL = NLP + GOV
BLEND_TRIG = ["trigger_climate", "trigger_fish_kill", "trigger_ofw_remittance"]
HOLDOUT = ["2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]
DEV_LAST = "2025-Q1"
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]


def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def issue(t: int) -> str:
    n = t + 1
    return date(n // 4, (n % 4) * 3 + 1, 15).isoformat()


# ------------------------------------------------------------------------------------------------ data
def labels(threshold_rows: str = "all") -> tuple[pd.DataFrame, float]:
    s = pd.read_csv("data/inputs/sws_rounds.csv")
    s = s[s["definition_A"].astype(str) == "True"]
    sw = s.groupby("quarter").agg(H=("H", "mean"), posted=("published", lambda x: max(v[:10] for v in x)))
    p = pd.read_parquet("data/processed/psa_indicators.parquet")[["province_code", "quarter", "food_cpi_yoy"]]
    p = p[(p["quarter"] >= "2021-Q1") & (p["quarter"] <= "2026-Q3")].dropna()
    p["dev"] = p["food_cpi_yoy"] - p.groupby("quarter")["food_cpi_yoy"].transform("mean")
    L = p.merge(sw, left_on="quarter", right_index=True, how="inner")
    L["stress"] = L["H"] + 2 * L["dev"]
    base = L if threshold_rows == "all" else L[L["quarter"] <= DEV_LAST]
    med = float(base["stress"].median())
    L["y"] = (L["stress"] > med).astype(int)
    L["q"] = L["quarter"].map(qi)
    return L, med


def features() -> pd.DataFrame:
    f = pd.read_parquet("data/processed/features_fused.parquet")
    p = pd.read_parquet("data/processed/psa_indicators.parquet")[["province_code", "quarter", "food_cpi_yoy"]]
    p["food_cpi_dev"] = p["food_cpi_yoy"] - p.groupby("quarter")["food_cpi_yoy"].transform("mean")
    f = f.merge(p[["province_code", "quarter", "food_cpi_dev"]], on=["province_code", "quarter"], how="left")
    f["t"] = f["quarter"].map(qi)
    f = f.sort_values(["province_code", "t"])
    g = f.groupby("province_code")
    assert (g["t"].diff().dropna() == 1).all(), "features_fused must have consecutive quarters per province"
    f["unemployment_rate_prev"] = g["unemployment_rate"].shift(1)
    f["rice_change_prev"] = 100 * (g["rice_price_regular"].shift(1) / g["rice_price_regular"].shift(2) - 1)
    return f[["province_code", "quarter", "t"] + ALL]


def pairs(X: pd.DataFrame, L: pd.DataFrame, k: int) -> pd.DataFrame:
    Y = L[["province_code", "q", "quarter", "y", "posted", "stress"]].rename(columns={"quarter": "target"})
    P = X.assign(q=X["t"] + k).merge(Y, on=["province_code", "q"], how="inner")
    return P.sort_values(["q", "province_code"]).reset_index(drop=True)


def firi_lookup() -> dict:
    h = pd.read_csv("data/thesis/firi2_history.csv", dtype={"province_code": str})
    return {(r.origin_quarter, r.province_code): r.FIRI for r in h.itertuples() if pd.notna(r.FIRI)}


# ------------------------------------------------------------------------------------------------ models
def lgbm(params=None):
    from lightgbm import LGBMClassifier
    base = dict(random_state=SEED, deterministic=True, n_jobs=1, verbosity=-1, force_row_wise=True)
    return LGBMClassifier(**base, **(params or {}))


def fit_lgbm(tr, te, cols, params=None):
    m = lgbm(params).fit(tr[cols].astype(float), tr["y"])
    return m.predict_proba(te[cols].astype(float))[:, 1], m


def fit_lr(tr, te, cols):
    from sklearn.linear_model import LogisticRegression
    A, B = tr[cols].astype(float), te[cols].astype(float)
    med = A.median()
    A, B = A.fillna(med).fillna(0.0), B.fillna(med).fillna(0.0)
    mu, sd = A.mean(), A.std(ddof=0).replace(0, 1.0)
    m = LogisticRegression(C=1.0, max_iter=5000).fit((A - mu) / sd, tr["y"])
    return m.predict_proba((B - mu) / sd)[:, 1]


def fold_rows(P: pd.DataFrame, q: int, k: int) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    t = q - k
    I = issue(t)
    tr = P[(P["q"] <= t) & (P["posted"] < I)]
    te = P[P["q"] == q]
    return tr, te, I


def predict_fold(tr, te, k, firi, tuned=None) -> dict:
    out = {}
    single = tr["y"].nunique() < 2
    rate = float(tr["y"].mean())

    def guard(fn):
        return np.full(len(te), rate) if single else fn()
    out["LGBM-default"] = guard(lambda: fit_lgbm(tr, te, ALL)[0])
    if tuned is not None:
        out["LGBM-tuned"] = guard(lambda: fit_lgbm(tr, te, ALL, tuned)[0])
    out["LR-combined"] = guard(lambda: fit_lr(tr, te, ALL))
    out["LR-gov"] = guard(lambda: fit_lr(tr, te, GOV))
    out["LR-nlp"] = guard(lambda: fit_lr(tr, te, NLP))
    out["LGBM-gov"] = guard(lambda: fit_lgbm(tr, te, GOV)[0])
    out["LGBM-nlp"] = guard(lambda: fit_lgbm(tr, te, NLP)[0])
    last = tr.sort_values("q").groupby("province_code")["y"].last()
    out["Persistence"] = te["province_code"].map(last).astype(float).to_numpy()
    out["Prevalence"] = np.full(len(te), rate)
    if k == 2:
        out["FIRI-v2"] = np.array([firi.get((qs(int(t)), p), np.nan) for t, p in zip(te["t"], te["province_code"])])
    if tuned is not None:
        trig = guard(lambda: fit_lr(tr, te, BLEND_TRIG))
        out["Blend-ChIII"] = 0.4 * out["LGBM-tuned"] + 0.4 * out["LR-gov"] + 0.2 * trig
    out["_single_class_training"] = single
    return out


def run_folds(P, k, targets, firi, tuned=None) -> pd.DataFrame:
    rows = []
    for q in targets:
        tr, te, I = fold_rows(P, q, k)
        if te.empty or tr["q"].nunique() < 8 or te[ALL].isna().all(axis=1).any():
            continue
        pr = predict_fold(tr, te, k, firi, tuned)
        df = te[["province_code", "t", "q", "target", "y"]].copy()
        df["issue"], df["train_rows"], df["train_quarters"] = I, len(tr), tr["q"].nunique()
        df["single_class_training"] = pr.pop("_single_class_training")
        for a, v in pr.items():
            df[a] = v
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


# ------------------------------------------------------------------------------------------------ metrics
def arm_metrics(D: pd.DataFrame, a: str) -> dict:
    from sklearn.metrics import f1_score
    E = D[D[a].notna()]
    m = C.metrics(E["y"], E[a].clip(0, 1))
    yh = (E[a] >= (0.712 if a == "Blend-ChIII" else 0.5)).astype(int)
    if a == "Blend-ChIII":
        m.update(C.metrics(E["y"], yh.astype(float)))      # classification at the document's cutoff
        m["auc_roc"] = C.auc(E["y"], E[a])
        m["brier"] = float(np.mean((E[a] - E["y"]) ** 2))
    m["weighted_f1"] = float(f1_score(E["y"], yh, average="weighted", zero_division=0))
    acc_q = (yh == E["y"]).groupby(E["target"]).mean()
    m["mean_fold_accuracy"] = float(acc_q.mean())
    m["folds"] = int(acc_q.size)
    m["per_fold_accuracy"] = acc_q.round(3).to_dict()
    corr = (yh == E["y"]).astype(float).to_numpy()
    m["accuracy_quarter_bootstrap95"] = C.boot_ci(E["target"].to_numpy(), lambda i: float(corr[i].mean()), seed=SEED)
    on = E[(E["y"] == 1) & (E["Persistence"] == 0)] if "Persistence" in E else E.iloc[0:0]
    m["onset_rows"], m["onset_hits"] = len(on), int((yh.loc[on.index] == 1).sum()) if len(on) else 0
    return m


def table(D: pd.DataFrame) -> dict:
    arms = [c for c in D.columns if c not in ("province_code", "t", "q", "target", "y", "issue", "train_rows",
                                               "train_quarters", "single_class_training")]
    return {a: arm_metrics(D, a) for a in arms}


def mcnemar(D, a, b) -> dict:
    from scipy.stats import binomtest
    ca = ((D[a] >= 0.5).astype(int) == D["y"])
    cb = ((D[b] >= 0.5).astype(int) == D["y"])
    n01, n10 = int((ca & ~cb).sum()), int((~ca & cb).sum())
    p = 1.0 if n01 + n10 == 0 else float(binomtest(min(n01, n10), n01 + n10, 0.5).pvalue)
    return {"proposed_only_correct": n01, "comparator_only_correct": n10, "exact_p": p}


# ------------------------------------------------------------------------------------------------ algorithms
def algorithm3(X, L, firi, dev_targets_fn, label=""):
    res, kstar = {}, 0
    for k in range(1, 9):
        P = pairs(X, L, k)
        D = run_folds(P, k, dev_targets_fn(P), firi)
        if D.empty:
            res[k] = {"folds": 0, "pass": False, "reason": "no fold with >= 8 training quarters"}
            break
        tab = table(D)
        acc = tab["LGBM-default"]["mean_fold_accuracy"]
        res[k] = {"folds": tab["LGBM-default"]["folds"], "mean_fold_accuracy": acc, "pass": acc >= 0.75, "arms": tab,
                  "class_counts": {"HIGH": int(D["y"].sum()), "LOW": int((1 - D["y"]).sum())}}
        print(f"{label} k={k} folds={res[k]['folds']} LGBM mean-fold acc={acc:.3f} pass={acc >= 0.75} "
              f"persist={tab['Persistence']['mean_fold_accuracy']:.3f} classes={res[k]['class_counts']}", flush=True)
        if acc >= 0.75:
            kstar = k
        else:
            break
    return res, kstar


def algorithm4(X, L, firi, k) -> dict:
    import optuna
    from sklearn.metrics import f1_score
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    P = pairs(X, L, k)
    dev = [q for q in sorted(P["q"].unique()) if qs(q) <= DEV_LAST]
    folds = []
    for q in dev:
        tr, te, _ = fold_rows(P, q, k)
        if not te.empty and tr["q"].nunique() >= 8 and tr["y"].nunique() == 2:
            folds.append((tr, te))

    def objective(trial):
        prm = {"num_leaves": trial.suggest_int("num_leaves", 4, 32), "max_depth": trial.suggest_int("max_depth", 2, 6),
               "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
               "n_estimators": trial.suggest_int("n_estimators", 50, 500),
               "min_child_samples": trial.suggest_int("min_child_samples", 3, 20),
               "subsample": trial.suggest_float("subsample", 0.5, 1.0), "subsample_freq": 1,
               "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
               "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10, log=True),
               "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 10, log=True)}
        f1s = []
        for tr, te in folds:
            p, _ = fit_lgbm(tr, te, ALL, prm)
            f1s.append(f1_score(te["y"], (p >= 0.5).astype(int), average="weighted", zero_division=0))
        return float(np.mean(f1s))

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=100)
    best = {**study.best_params, "subsample_freq": 1}
    Ddev = run_folds(P, k, dev, firi, best)
    Dho = run_folds(P, k, [qi(q) for q in HOLDOUT], firi, best)
    tab_dev, tab_ho = table(Ddev), table(Dho)
    ho = tab_ho["LGBM-tuned"]
    accept = ho["weighted_f1"] >= 0.75 and ho["auc_roc"] is not None and ho["auc_roc"] >= 0.80
    allP = P[P["y"].notna()]
    final_pred, final_model = fit_lgbm(allP, allP, ALL, best)
    return {"k": k, "optuna_folds": len(folds), "best_value_mean_weighted_f1": study.best_value, "best_params": best,
            "trials": study.trials_dataframe().drop(columns=["datetime_start", "datetime_complete", "duration"],
                                                    errors="ignore").to_dict(orient="records"), "dev": tab_dev, "holdout": tab_ho,
            "holdout_class_counts": {"HIGH": int(Dho["y"].sum()), "LOW": int((1 - Dho["y"]).sum())},
            "accepted": bool(accept), "_frames": (Ddev, Dho), "_final": (final_model, allP)}


def shap_ranks(model, Xtr: pd.DataFrame) -> dict:
    import shap
    sv = shap.TreeExplainer(model).shap_values(Xtr[ALL].astype(float))
    sv = sv[1] if isinstance(sv, list) else sv
    imp = pd.Series(np.abs(sv).mean(axis=0), index=ALL).sort_values(ascending=False)
    return {"mean_abs_shap": imp.round(6).to_dict(), "rank": {f: int(r) for r, f in enumerate(imp.index, 1)}}


def h1_decision(rk: dict) -> dict:
    fssi = min(rk[f] for f in ("FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel"))
    return {"best_fssi_rank": fssi, "food_cpi_dev_rank": rk["food_cpi_dev"], "rejected": fssi <= 3 and rk["food_cpi_dev"] <= 3}


# ------------------------------------------------------------------------------------------------ main
def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E99 / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    L, med = labels("all")
    X = features()
    firi = firi_lookup()
    print(f"Eq.3 label: rows={len(L)} quarters={L['quarter'].nunique()} median={med:.3f} HIGH={L['y'].mean():.3f}")
    L.to_csv(o / "eq3_labels.csv", index=False)
    dev_fn = lambda P: [q for q in sorted(P["q"].unique()) if qs(q) <= DEV_LAST]  # noqa: E731
    all_fn = lambda P: sorted(P["q"].unique())  # noqa: E731
    a3, kstar = algorithm3(X, L, firi, dev_fn, "A3")
    L1, med1 = labels("dev")
    s1, k_s1 = algorithm3(X, L1, firi, dev_fn, "S1")
    s2, k_s2 = algorithm3(X, L, firi, all_fn, "S2")
    print("k* =", kstar, "| S1 k* =", k_s1, "| S2 k* =", k_s2)
    runs = {}
    for k in dict.fromkeys([kk for kk in (kstar, 2) if kk >= 1]):
        r = algorithm4(X, L, firi, k)
        Ddev, Dho = r.pop("_frames")
        model, allP = r.pop("_final")
        Ddev.to_csv(o / f"predictions_dev_k{k}.csv", index=False)
        Dho.to_csv(o / f"predictions_holdout_k{k}.csv", index=False)
        with open(o / f"lgbm_best_k{k}.pkl", "wb") as fh:
            pickle.dump(model, fh)
        r["final_model_sha256"] = hashlib.sha256((o / f"lgbm_best_k{k}.pkl").read_bytes()).hexdigest()
        r["final_training_rows"] = len(allP)
        r["shap_final"] = shap_ranks(model, allP)
        fold_ranks = []
        P = pairs(X, L, k)
        for q in sorted(Ddev["q"].unique()):
            tr, te, _ = fold_rows(P, q, k)
            if tr["y"].nunique() == 2:
                fold_ranks.append(shap_ranks(fit_lgbm(tr, te, ALL, r["best_params"])[1], tr)["rank"])
        r["shap_fold_median_rank"] = {f: float(np.median([fr[f] for fr in fold_ranks])) for f in ALL} if fold_ranks else {}
        r["H1"] = h1_decision(r["shap_final"]["rank"])
        pooled = pd.concat([Ddev, Dho], ignore_index=True)
        r["mcnemar_vs_comparators"] = {c: mcnemar(pooled, "LGBM-tuned", c) for c in
                                       ("Persistence", "LR-combined", "LR-gov", "LR-nlp", "LGBM-gov", "LGBM-nlp")}
        six = ("Persistence", "LR-combined", "LR-gov", "LR-nlp", "LGBM-gov", "LGBM-nlp")
        better = lambda tab: all(tab["LGBM-tuned"]["accuracy"] > tab[c]["accuracy"] and  # noqa: E731
                                 tab["LGBM-tuned"]["weighted_f1"] > tab[c]["weighted_f1"] for c in six)
        r["H3"] = {"descriptive_dev": better(r["dev"]), "descriptive_holdout": better(r["holdout"])}
        r["H3"]["rejected_descriptive"] = r["H3"]["descriptive_dev"] and r["H3"]["descriptive_holdout"]
        r["H3"]["rejected_significant"] = r["H3"]["rejected_descriptive"] and all(v["exact_p"] < 0.05 for v in r["mcnemar_vs_comparators"].values())
        runs[k] = r
        ho = r["holdout"]["LGBM-tuned"]
        print(f"A4 k={k} optuna folds={r['optuna_folds']} best wF1(dev)={r['best_value_mean_weighted_f1']:.3f} "
              f"holdout acc={ho['accuracy']:.3f} wF1={ho['weighted_f1']:.3f} auc={ho['auc_roc']} accepted={r['accepted']} "
              f"classes={r['holdout_class_counts']}", flush=True)
        for part in ("dev", "holdout"):
            for a, m in r[part].items():
                print(f"   {part:7s} {a:13s} acc={m['accuracy']:.3f} mfold={m['mean_fold_accuracy']:.3f} bal={m['balanced_accuracy']} "
                      f"P={m['precision_HIGH']} R={m['recall_HIGH']} F1={m['f1_HIGH']:.2f} wF1={m['weighted_f1']:.3f} "
                      f"auc={m['auc_roc']} brier={m['brier']:.3f} {m['confusion']} folds={m['folds']}")
        print("   SHAP final rank:", r["shap_final"]["rank"], "H1:", r["H1"], "H3:", r["H3"])
        print("   McNemar:", r["mcnemar_vs_comparators"])
    # prospective seal: k = 2 tuned model, origin 2026-Q2 (issue 2026-07-15) -> 2026-Q4
    seal = None
    if 2 in runs:
        P2 = pairs(X, L, 2)
        t0 = qi("2026-Q2")
        tr = P2[(P2["q"] <= t0) & (P2["posted"] < issue(t0))]
        te = X[X["t"] == t0].set_index("province_code").loc[PROVS].reset_index()
        p, _ = fit_lgbm(tr, te, ALL, runs[2]["best_params"])
        S = te[["province_code", "quarter"] + ALL].rename(columns={"quarter": "origin"}).assign(
            target="2026-Q4", issue_date=issue(t0), p_high=p, class_high=(p >= 0.5).astype(int),
            model="E99 Algorithm 4 LightGBM k=2 (research seal, not published)", train_rows=len(tr),
            params=json.dumps(runs[2]["best_params"], sort_keys=True), label_threshold_median=med)
        S.to_csv(o / "sealed_prospective_2026Q4.csv", index=False)
        h = hashlib.sha256((o / "sealed_prospective_2026Q4.csv").read_bytes()).hexdigest()
        (o / "sealed_prospective_2026Q4.sha256").write_text(f"{h}  sealed_prospective_2026Q4.csv\n")
        seal = {"file": "sealed_prospective_2026Q4.csv", "sha256": h, "issue_date": issue(t0), "target": "2026-Q4",
                "p_high": dict(zip(S["province_code"], np.round(p, 4)))}
        print("SEAL", seal)
    hyp = {"H1": runs.get(kstar or 2, {}).get("H1"),
           "H2": {"k_star": kstar, "accepted_at_k_star": runs.get(kstar, {}).get("accepted") if kstar else None,
                  "rejected": bool(kstar >= 2 and runs[kstar]["accepted"])},
           "H3": {**runs.get(kstar or 2, {}).get("H3", {}), "evaluated_at_k": kstar or 2},
           "H4": "blocked: requires DA evaluator assessments", "H5": "blocked: requires ISO/IEC 25010 responses"}
    res = {"stamp": stamp, "protocol_sha256": (E99 / "PROTOCOL.sha256").read_text().split()[0],
           "label": {"definition": "Chapter III Eq. 3: SWS hunger + 2 x provincial food CPI YoY deviation > global median",
                     "rows": len(L), "quarters": int(L["quarter"].nunique()), "median": med, "high_share": float(L["y"].mean()),
                     "is_proxy": True, "sensitivity_S1_median_dev_only": med1},
           "algorithm3": {"k_star": kstar, "per_k": a3}, "S1": {"k_star": k_s1, "per_k": s1}, "S2": {"k_star": k_s2, "per_k": s2},
           "algorithm4": {str(k): v for k, v in runs.items()}, "hypotheses": hyp, "prospective_seal": seal,
           "evidence_status": "development evidence; holdout untouched by E99 selection but examined earlier in the E-series"}
    (o / "e99_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("HYPOTHESES", json.dumps(hyp, default=float))
    print(o)


if __name__ == "__main__":
    main()

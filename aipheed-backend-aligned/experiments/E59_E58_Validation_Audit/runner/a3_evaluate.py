"""E59 audit step 3: cross-quarter evaluation, baselines, rising-stress case review, generalization and significance.
Uses only the sealed predictions (E57/E58), the E55 baseline run and committed E38 predictions; no rule or threshold is
changed. Sensitivity analyses that alter inputs are labelled as such and never replace the frozen results.

    backend/venv/Scripts/python.exe -B runner/a3_evaluate.py
      -> E58_BASELINE_COMPARISON.csv, E58_RISING_STRESS_CASE_REVIEW.csv, out/evaluation.json, out/*.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
A = Path(__file__).resolve().parents[1]
EXP = A.parent
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
from scipy.stats import binomtest  # noqa: E402

P = pd.read_csv(A / "E58_QUARTERLY_PREDICTIONS.csv", dtype={"province_code": str})
BL = EXP / "E55_Food_Insecurity_LightGBM" / "runs" / "baselines_20261017T153459Z" / "rows_baselines.csv"
E38 = EXP / "E38_Lead2_Diagnosis_Tuning" / "runs" / "20261015T033922Z" / "predictions.csv"
E57ROWS = sorted((EXP / "E57_E56_Rolling_Origin_Test" / "runs").glob("2026*"))[0] / "rows.csv"
RNG = np.random.default_rng(59)


def metrics(y, yhat, p=None):
    y, yhat = np.asarray(y, int), np.asarray(yhat, int)
    tp, tn = int(((yhat == 1) & (y == 1)).sum()), int(((yhat == 0) & (y == 0)).sum())
    fp, fn = int(((yhat == 1) & (y == 0)).sum()), int(((yhat == 0) & (y == 1)).sum())
    dv = lambda a, b: a / b if b else None  # noqa: E731
    rh, rl, ph, pl = dv(tp, tp + fn), dv(tn, tn + fp), dv(tp, tp + fp), dv(tn, tn + fn)
    out = {"n": int(len(y)), "HIGH": int(y.sum()), "LOW": int((y == 0).sum()), "TP": tp, "TN": tn, "FP": fp, "FN": fn,
           "accuracy": (tp + tn) / len(y) if len(y) else None,
           "balanced_accuracy": None if rh is None or rl is None else (rh + rl) / 2,
           "recall_HIGH": rh, "precision_HIGH": ph, "recall_LOW": rl, "precision_LOW": pl,
           "f1_HIGH": (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else None}
    if p is not None:
        from sklearn.metrics import roc_auc_score
        p = np.asarray(p, float)
        out["brier"] = float(np.mean((p - y) ** 2))
        out["auc"] = float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(p)) > 1 else None
    return out


def qboot(D, fn, B=4000):
    qs = sorted(D["target"].unique())
    vals = []
    for _ in range(B):
        g = pd.concat([D[D["target"] == q] for q in RNG.choice(qs, len(qs))])
        v = fn(g)
        if v is not None and v == v:
            vals.append(v)
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))] if vals else None


def calib(y, p):
    from sklearn.linear_model import LogisticRegression
    y, p = np.asarray(y, int), np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    z = np.log(p / (1 - p)).reshape(-1, 1)
    lr = LogisticRegression(C=1e6).fit(z, y)
    bins = []
    for lo in np.arange(0, 1, 0.2):
        s = (p >= lo) & ((p < lo + 0.2) if lo < 0.8 else (p <= 1))
        bins.append({"bin": f"{lo:.1f}-{lo + 0.2:.1f}", "n": int(s.sum()), "mean_p": float(p[s].mean()) if s.any() else None,
                     "observed": float(y[s].mean()) if s.any() else None})
    return {"citl": float(y.mean() - p.mean()), "slope": float(lr.coef_[0][0]), "reliability": bins}


def mcnemar(a_ok, b_ok):
    b = int((a_ok & ~b_ok).sum())
    c = int((~a_ok & b_ok).sum())
    return {"A_right_B_wrong": b, "A_wrong_B_right": c, "exact_p": float(binomtest(b, b + c, 0.5).pvalue) if b + c else 1.0}


def main():
    D = P.copy()
    D["y"] = D["y_T43"]
    D["MAJ_pred"], D["MAJ_p"] = 0, 0.0
    e57 = pd.read_csv(E57ROWS, dtype={"province_code": str}).set_index(["t", "province_code"])
    D["t"] = D["origin_quarter"].map(L.qi)
    D["stress_direction"] = [e57.loc[(t, p), "stress_direction"] for t, p in zip(D["t"], D["province_code"])]
    D["CLIM_p"] = [e57.loc[(t, p), "CLIM_p"] for t, p in zip(D["t"], D["province_code"])]
    D["E55_p"] = [e57.loc[(t, p), "E55_p"] for t, p in zip(D["t"], D["province_code"])]
    D["E55_pred"] = (D["E55_p"] >= 0.5).astype(int)
    MODELS = {"E58-EW": ("EW_pred", "E56_p_price"), "E56": ("E56_pred", "E56_p"), "E55-LGBM": ("E55_pred", "E55_p"),
              "Price projection rule": ("PROJ_pred", "BPROJ_p"), "Persistence": ("PERSIST_pred", None),
              "Majority class (LOW)": ("MAJ_pred", "MAJ_p")}
    res = {"pooled_50": {}, "per_quarter": [], "per_province": [], "strata": {}, "ci": {}}
    for m, (c, pc) in MODELS.items():
        res["pooled_50"][m] = metrics(D["y"], D[c], None if pc is None else D[pc])
        res["pooled_50"][m]["onsets_detected"] = int(((D["onset"] == 1) & (D[c] == 1)).sum())
    res["calibration_EW_Pprice"] = calib(D["y"], D["E56_p_price"])
    res["calibration_E56"] = calib(D["y"], D["E56_p"])
    for q, g in D.groupby("target"):
        mm = metrics(g["y"], g["EW_pred"], g["E56_p_price"])
        res["per_quarter"].append({"target": q, "issue": g["origin_quarter"].iloc[0], **mm,
                                   "E56_accuracy": float((g["E56_pred"] == g["y"]).mean()),
                                   "PROJ_accuracy": float((g["PROJ_pred"] == g["y"]).mean()),
                                   "PERSIST_accuracy": float((g["PERSIST_pred"] == g["y"]).mean()),
                                   "MAJ_accuracy": float((g["MAJ_pred"] == g["y"]).mean()),
                                   "onsets": int(g["onset"].sum()), "onsets_warned_EW": int(((g["onset"] == 1) & (g["EW_pred"] == 1)).sum()),
                                   "stress_direction": g["stress_direction"].iloc[0], "EW_differs_from_E56": bool((g["EW_pred"] != g["E56_pred"]).any())})
    Q = pd.DataFrame(res["per_quarter"])
    res["quarter_summary_EW"] = {"quarters": int(len(Q)), "mean": float(Q["accuracy"].mean()), "median": float(Q["accuracy"].median()),
                                 "min": float(Q["accuracy"].min()), "max": float(Q["accuracy"].max()),
                                 "quarters_ge_0.75": int((Q["accuracy"] >= 0.75).sum()),
                                 "sd": float(Q["accuracy"].std(ddof=1))}
    for pv, g in D.groupby("province"):
        res["per_province"].append({"province": pv, **metrics(g["y"], g["EW_pred"], g["E56_p_price"]),
                                    "E56_accuracy": float((g["E56_pred"] == g["y"]).mean()), "onsets": int(g["onset"].sum()),
                                    "onsets_warned_EW": int(((g["onset"] == 1) & (g["EW_pred"] == 1)).sum())})
    for name, g in [("2024-Q2 only", D[D["target"] == "2024-Q2"]), ("excluding 2024-Q2", D[D["target"] != "2024-Q2"])] + \
                   [(f"stress {k}", g) for k, g in D.groupby("stress_direction")]:
        res["strata"][name] = {m: metrics(g["y"], g[c]) | {"onsets": int(g["onset"].sum()),
                                                            "onsets_detected": int(((g["onset"] == 1) & (g[c] == 1)).sum())}
                               for m, (c, _) in MODELS.items()}
    # uncertainty (quarter-cluster bootstrap) and episode-level view of onsets
    for m, (c, _) in MODELS.items():
        res["ci"][m] = {"accuracy": qboot(D, lambda g, c=c: float((g[c] == g["y"]).mean())),
                        "recall_HIGH": qboot(D, lambda g, c=c: float(g[g["y"] == 1][c].mean()) if (g["y"] == 1).any() else None),
                        "onset_recall": qboot(D, lambda g, c=c: float(g[g["onset"] == 1][c].mean()) if (g["onset"] == 1).any() else None)}
    ep = D[D["onset"] == 1].groupby("target")
    res["onset_episodes"] = [{"target": q, "onsets": int(len(g)), "EW_warned": int(g["EW_pred"].sum()),
                              "E56_warned": int(g["E56_pred"].sum()), "PROJ_warned": int(g["PROJ_pred"].sum())} for q, g in ep]
    # paired comparisons
    ok = {m: (D[c] == D["y"]).to_numpy() for m, (c, _) in MODELS.items()}
    res["paired"] = {
        "EW_vs_E56_rows_mcnemar": mcnemar(ok["E58-EW"], ok["E56"]),
        "EW_vs_PROJ_rows_mcnemar": mcnemar(ok["E58-EW"], ok["Price projection rule"]),
        "EW_vs_PERSIST_rows_mcnemar": mcnemar(ok["E58-EW"], ok["Persistence"])}
    qa = D.groupby("target").apply(lambda g: pd.Series({m: float((g[c] == g["y"]).mean()) for m, (c, _) in MODELS.items()}))
    for b in ("E56", "Price projection rule", "Persistence", "Majority class (LOW)"):
        w, l_ = int((qa["E58-EW"] > qa[b]).sum()), int((qa["E58-EW"] < qa[b]).sum())
        res["paired"][f"EW_vs_{b}_quarter_sign_test"] = {"EW_better_quarters": w, "EW_worse_quarters": l_,
                                                         "ties": int(len(qa) - w - l_),
                                                         "p": float(binomtest(w, w + l_, 0.5).pvalue) if w + l_ else 1.0}
    db = D.copy()
    for m, pc in (("EW", "E56_p_price"), ("E56", "E56_p"), ("PROJ", "BPROJ_p"), ("MAJ", "MAJ_p"), ("CLIM", "CLIM_p")):
        db[f"{m}_p"] = db[pc]
    for b in ("E56", "PROJ", "MAJ", "CLIM"):
        res["paired"][f"brier_EW_minus_{b}"] = E.paired_brier(db.rename(columns={"target": "target"}), "EW", b, seed=59, n=4000)
    # required baselines on the 45 rows where the E55 baseline run exists (2024-Q2 cannot be forecast by them)
    bl = pd.read_csv(BL, dtype={"province_code": str}).set_index(["target", "province_code"])
    D45 = D[[(q, p) in bl.index for q, p in zip(D["target"], D["province_code"])]].copy()
    rows = []
    for name, cp, thr in [("E58-EW", "E56_p_price", 0.5), ("E56", "E56_p", 0.5), ("E55-LGBM", "E55_p", 0.5),
                          ("Price projection rule", "BPROJ_p", 0.5)]:
        rows.append({"model": name, "rows": "45 (B1-B7 available)", **metrics(D45["y"], D45[cp] >= thr, D45[cp])})
    blmap = {"B1_PERSIST": "Naive persistence", "B6_LR_COMB": "Logistic regression (combined)",
             "B2_LR_GOV": "Logistic regression (government indicators only)", "B4_LR_NLP": "Logistic regression (NLP only)",
             "B3_LGBM_GOV": "LightGBM (government indicators only)", "B5_LGBM_NLP": "LightGBM (NLP only)",
             "B7_E38PROC": "E38 LightGBM procedure refitted on T43", "CLIM": "Climatology", "LOW": "Majority class (always LOW)",
             "HIGH": "Always HIGH"}
    keys = list(zip(D45["target"], D45["province_code"]))
    for b, name in blmap.items():
        p = np.array([float(bl.loc[k, f"{b}_p"]) for k in keys])
        thr = np.array([float(bl.loc[k, "B7_E38PROC_thr"]) for k in keys]) if b == "B7_E38PROC" else 0.5
        rows.append({"model": name, "rows": "45", **metrics(D45["y"], p >= thr, p)})
    e38 = pd.read_csv(E38, dtype={"province_code": str})
    e38 = e38[e38["arm"] == "E38-LGBM"].set_index(["target_quarter", "province_code"])
    D38 = D[[(q, p) in e38.index for q, p in zip(D["target"], D["province_code"])]]
    p38 = np.array([float(e38.loc[(q, p), "p"]) for q, p in zip(D38["target"], D38["province_code"])])
    t38 = np.array([float(e38.loc[(q, p), "threshold"]) for q, p in zip(D38["target"], D38["province_code"])])
    rows.append({"model": "E38 production default (thesis Eq.3 target; NON-EQUIVALENT)", "rows": f"{len(D38)} (no 2025-Q2/Q3)",
                 **metrics(D38["y"], p38 >= t38, p38)})
    for name, (c, pc) in MODELS.items():
        rows.append({"model": name, "rows": "50 (all eligible)", **metrics(D["y"], D[c], None if pc is None else D[pc])})
    BC = pd.DataFrame(rows)
    BC.round(4).to_csv(A / "E58_BASELINE_COMPARISON.csv", index=False)
    # rising-stress case review: every onset and every EW false alarm
    cases = D[(D["onset"] == 1) | ((D["EW_pred"] == 1) & (D["y"] == 0))].copy()
    cases["case_type"] = np.where(cases["onset"] == 1, "ONSET (LOW at latest known label -> HIGH at target)", "EW false alarm (warned, outcome LOW)")
    cases["EW_result"] = np.where(cases["onset"] == 1, np.where(cases["EW_pred"] == 1, "warned", "MISSED"), "false alarm")
    cases["E56_result"] = np.where(cases["onset"] == 1, np.where(cases["E56_pred"] == 1, "warned", "missed"),
                                   np.where(cases["E56_pred"] == 1, "false alarm", "no alarm"))
    cases["PROJ_result"] = np.where(cases["onset"] == 1, np.where(cases["PROJ_pred"] == 1, "warned", "missed"),
                                    np.where(cases["PROJ_pred"] == 1, "false alarm", "no alarm"))
    diag = pd.read_csv(EXP / "E58_Rising_Stress_Early_Warning" / "tables" / "diagnosis_rows.csv")
    diag = diag.set_index(["target", "province"])
    cases["miss_mechanism"] = [("stale hunger reading suppressed a correct price signal" if r.E56_p_hunger < 0.5 and r.E56_p_price >= 0.5
                                else "price part did not foresee the price rise" if r.E56_p_price < 0.5 and r.y == 1
                                else "price pressure forecast but did not occur" if r.y == 0 else "")
                               for r in cases.itertuples()]
    cases["F_target"] = [diag.loc[(q, p), "F_target"] for q, p in zip(cases["target"], cases["province"])]
    cases["food_threshold"] = [diag.loc[(q, p), "food_thr"] for q, p in zip(cases["target"], cases["province"])]
    cases["G_target"] = [diag.loc[(q, p), "G_target"] for q, p in zip(cases["target"], cases["province"])]
    cases["gap_threshold"] = [diag.loc[(q, p), "gap_thr"] for q, p in zip(cases["target"], cases["province"])]
    cases[["case_type", "issue" if "issue" in cases else "origin_quarter", "target", "province", "y_T43", "latest_known_T43",
           "E56_p", "E56_p_price", "E56_p_hunger", "H_last_known", "EW_level", "EW_result", "E56_result", "PROJ_result",
           "BPROJ_p", "miss_mechanism", "F_target", "food_threshold", "G_target", "gap_threshold"]] \
        .sort_values(["case_type", "target", "province"]).round(4).to_csv(A / "E58_RISING_STRESS_CASE_REVIEW.csv", index=False)
    pd.DataFrame(res["per_quarter"]).round(4).to_csv(A / "out" / "per_quarter_EW.csv", index=False)
    pd.DataFrame(res["per_province"]).round(4).to_csv(A / "out" / "per_province_EW.csv", index=False)
    (A / "out" / "evaluation.json").write_text(json.dumps(res, indent=1, default=float))
    f = lambda v: None if v is None else round(v, 3)  # noqa: E731
    for m, v in res["pooled_50"].items():
        print(f"{m:24s} acc {f(v['accuracy'])} bal {f(v['balanced_accuracy'])} recH {f(v['recall_HIGH'])} precH {f(v['precision_HIGH'])} "
              f"recL {f(v['recall_LOW'])} precL {f(v['precision_LOW'])} F1 {f(v['f1_HIGH'])} brier {f(v.get('brier'))} "
              f"auc {f(v.get('auc'))} {v['TP']}/{v['TN']}/{v['FP']}/{v['FN']} onsets {v['onsets_detected']}  CI {res['ci'][m]}")
    print("quarter summary", res["quarter_summary_EW"])
    print(Q[["target", "n", "HIGH", "accuracy", "balanced_accuracy", "E56_accuracy", "PROJ_accuracy", "PERSIST_accuracy",
             "MAJ_accuracy", "onsets", "onsets_warned_EW", "stress_direction"]].round(2).to_string())
    print(pd.DataFrame(res["per_province"])[["province", "HIGH", "accuracy", "recall_HIGH", "precision_HIGH", "FP", "FN", "E56_accuracy", "onsets", "onsets_warned_EW"]].round(2).to_string())
    print({k: {m: (f(v["accuracy"]), v["onsets_detected"], v["onsets"]) for m, v in s.items()} for k, s in res["strata"].items()})
    print("episodes", res["onset_episodes"])
    print("paired", json.dumps(res["paired"], default=float))
    print("calib EW", res["calibration_EW_Pprice"]["citl"], res["calibration_EW_Pprice"]["slope"], res["calibration_EW_Pprice"]["reliability"])
    print(BC[["model", "rows", "n", "accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "brier"]].round(3).to_string())


if __name__ == "__main__":
    main()

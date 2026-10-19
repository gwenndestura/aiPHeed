"""E60 step C2 (PROTOCOL sections 6-7): score the SEALED E60 candidates with E56, E58-EW, the projection rule, persistence,
majority class and the six SOP-Q3 baselines; DEV-only final-candidate choice; Q-news (C vs A); Q-improve (final vs EW).

    backend/venv/Scripts/python.exe -B runner/c2_score.py
      -> MODEL_CANDIDATE_COMPARISON.csv, NEWS_ABLATION_RESULTS.csv, QUARTERLY_AND_PROVINCE_RESULTS.csv, out/score.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E60 = Path(__file__).resolve().parents[1]
EXP = E60.parent
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
from scipy.stats import binomtest  # noqa: E402
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402

SEALED = E60 / "sealed" / "candidates.csv"
Q59 = EXP / "E59_E58_Validation_Audit" / "E58_QUARTERLY_PREDICTIONS.csv"
BL = EXP / "E55_Food_Insecurity_LightGBM" / "runs" / "baselines_20261017T153459Z" / "rows_baselines.csv"
DEV_Q = ["2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2", "2025-Q3"]
TEST_Q = ["2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]
RNG = np.random.default_rng(60)


def verify():
    if hashlib.sha256(SEALED.read_bytes()).hexdigest() != (SEALED.parent / "candidates.csv.sha256").read_text().split()[0]:
        raise SystemExit("sealed candidates changed")


def metr(y, w, p=None):
    y, w = np.asarray(y, int), np.asarray(w, int)
    tp, tn = int(((w == 1) & (y == 1)).sum()), int(((w == 0) & (y == 0)).sum())
    fp, fn = int(((w == 1) & (y == 0)).sum()), int(((w == 0) & (y == 1)).sum())
    dv = lambda a, b: a / b if b else None  # noqa: E731
    rh, rl = dv(tp, tp + fn), dv(tn, tn + fp)
    o = {"n": int(len(y)), "HIGH": int(y.sum()), "TP": tp, "TN": tn, "FP": fp, "FN": fn, "accuracy": (tp + tn) / len(y),
         "balanced_accuracy": None if rh is None or rl is None else (rh + rl) / 2, "recall_HIGH": rh,
         "precision_HIGH": dv(tp, tp + fp), "recall_LOW": rl, "precision_LOW": dv(tn, tn + fn),
         "f1_HIGH": dv(2 * tp, 2 * tp + fp + fn), "fp_rate": dv(fp, fp + tn)}
    if p is not None:
        p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
        o["brier"] = float(np.mean((p - y) ** 2))
        o["log_loss"] = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
        two = len(set(y)) == 2 and len(set(p)) > 1
        o["roc_auc"] = float(roc_auc_score(y, p)) if two else None
        o["pr_auc"] = float(average_precision_score(y, p)) if two else None
        o["citl"] = float(y.mean() - p.mean())
    return o


def qboot_diff(D, a, b, B=4000):
    qs = sorted(D["target"].unique())
    d = (D[f"{a}_prob"] - D["y"]) ** 2 - (D[f"{b}_prob"] - D["y"]) ** 2
    vals = [float(np.mean(np.concatenate([d[D["target"] == q].to_numpy() for q in RNG.choice(qs, len(qs))]))) for _ in range(B)]
    return {"diff": float(d.mean()), "ci95": [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]}


def qsign(D, a, b):
    qa = D.groupby("target").apply(lambda g: pd.Series({"a": np.mean((g[f"{a}_prob"] - g["y"]) ** 2),
                                                         "b": np.mean((g[f"{b}_prob"] - g["y"]) ** 2)}))
    w, l_ = int((qa["a"] < qa["b"] - 1e-12).sum()), int((qa["a"] > qa["b"] + 1e-12).sum())
    return {"a_better_quarters": w, "a_worse_quarters": l_, "p": float(binomtest(w, w + l_, 0.5).pvalue) if w + l_ else 1.0}


def main():
    verify()
    S = pd.read_csv(SEALED, dtype={"province_code": str})
    Q = pd.read_csv(Q59, dtype={"province_code": str})
    D = Q.merge(S, on=["target", "province_code"], suffixes=("", "_c"))
    D = D[D["target"].isin(DEV_Q + TEST_Q)].copy()
    assert len(D) == 50
    D["y"] = D["y_T43"]
    MODEL = {  # name: (decision column, probability column)
        "A gov-only (forecast)": ("A_p", 0.5), "B news-only (forecast)": ("B_p", 0.5), "C gov+news (forecast)": ("C_p", 0.5),
        "D gov+news+history (forecast)": ("D_p", 0.5),
        "A gov-only (warning)": ("A_p_price", 0.5), "C gov+news (warning)": ("C_p_price", 0.5),
        "D gov+news+history (warning)": ("D_p_price", 0.5), "B news-only (warning)": ("B_p_price", 0.5),
        "E E56 (forecast)": ("E56_p", 0.5), "F E58-EW (warning)": ("E56_p_price", 0.5),
        "G price projection rule": ("BPROJ_p", 0.5)}
    for name, (col, thr) in MODEL.items():
        D[f"{name}_prob"], D[f"{name}_w"] = D[col], (D[col] >= thr).astype(int)
    D["H persistence_prob"] = D["PERSIST_pred"].astype(float)
    D["H persistence_w"] = D["PERSIST_pred"]
    D["H majority (LOW)_prob"], D["H majority (LOW)_w"] = 0.0, 0
    names = list(MODEL) + ["H persistence", "H majority (LOW)"]
    rows = []
    for split, g in [("ALL (50 rows, 10 quarters)", D), ("DEV (30 rows, 6 quarters)", D[D["target"].isin(DEV_Q)]),
                     ("TEST (20 rows, 4 quarters; 1 HIGH)", D[D["target"].isin(TEST_Q)])]:
        for n in names:
            mm = metr(g["y"], g[f"{n}_w"], None if n.startswith("H persistence") else g[f"{n}_prob"])
            mm["onset_recall"] = (float(g[(g["onset"] == 1)][f"{n}_w"].mean()) if (g["onset"] == 1).any() else None)
            mm["onsets"] = int(g["onset"].sum())
            qacc = g.groupby("target").apply(lambda x: float((x[f"{n}_w"] == x["y"]).mean()))
            mm["quarters_ge_0.75"] = int((qacc >= 0.75).sum())
            mm["quarters"] = int(len(qacc))
            rows.append({"split": split, "model": n, **mm})
    # six SOP-Q3 baselines on their 45 rows
    bl = pd.read_csv(BL, dtype={"province_code": str}).set_index(["target", "province_code"])
    D45 = D[[(q, p) in bl.index for q, p in zip(D["target"], D["province_code"])]]
    for b, nm in {"B1_PERSIST": "SOP naive persistence", "B6_LR_COMB": "SOP LR combined", "B2_LR_GOV": "SOP LR government-only",
                  "B4_LR_NLP": "SOP LR NLP-only", "B3_LGBM_GOV": "SOP LightGBM government-only", "B5_LGBM_NLP": "SOP LightGBM NLP-only"}.items():
        p = np.array([float(bl.loc[(q, pv), f"{b}_p"]) for q, pv in zip(D45["target"], D45["province_code"])])
        rows.append({"split": "SOP-Q3 rows (45; no 2024-Q2)", "model": nm, **metr(D45["y"], p >= 0.5, p)})
    for n in ("A gov-only (forecast)", "C gov+news (forecast)", "D gov+news+history (forecast)", "F E58-EW (warning)", "E E56 (forecast)"):
        rows.append({"split": "SOP-Q3 rows (45; no 2024-Q2)", "model": n, **metr(D45["y"], D45[f"{n}_w"], D45[f"{n}_prob"])})
    C = pd.DataFrame(rows)
    C.round(4).to_csv(E60 / "MODEL_CANDIDATE_COMPARISON.csv", index=False)
    # final choice on DEV (Brier of P(HIGH)), protocol section 6
    dev = C[C["split"].str.startswith("DEV")].set_index("model")
    br = {k: dev.loc[f"{k} (forecast)", "brier"] for k in ("A gov-only", "C gov+news", "D gov+news+history")}
    best = min(br, key=br.get)
    final = best if br[best] <= br["A gov-only"] - 0.005 or best == "A gov-only" else "A gov-only"
    # Q-news and Q-improve on ALL 50 rows
    qnews = {"C_vs_A_brier": qboot_diff(D, "C gov+news (forecast)", "A gov-only (forecast)"),
             "C_vs_A_sign": qsign(D, "C gov+news (forecast)", "A gov-only (forecast)"),
             "D_vs_A_brier": qboot_diff(D, "D gov+news+history (forecast)", "A gov-only (forecast)"),
             "C_vs_A_warning_onsets": {"C": int(D[(D["onset"] == 1)]["C gov+news (warning)_w"].sum()),
                                       "A": int(D[(D["onset"] == 1)]["A gov-only (warning)_w"].sum())},
             "B_vs_majority_brier": qboot_diff(D, "B news-only (forecast)", "H majority (LOW)"),
             "C_vs_E56_brier": qboot_diff(D, "C gov+news (forecast)", "E E56 (forecast)")}
    ci = qnews["C_vs_A_brier"]["ci95"]
    qnews["news_adds_measurable_value"] = bool(ci[1] < 0 and qnews["C_vs_A_warning_onsets"]["C"] >= qnews["C_vs_A_warning_onsets"]["A"])
    fw = f"{final} (warning)"
    allr = C[C["split"].str.startswith("ALL")].set_index("model")
    ew = allr.loc["F E58-EW (warning)"]
    fr = allr.loc[fw]
    pb = qboot_diff(D, fw, "F E58-EW (warning)")
    qimp = {"final_candidate": final, "dev_brier": br,
            "criteria": {"accuracy_ge_EW": fr["accuracy"] >= ew["accuracy"],
                         "balanced_ge_EW": (fr["balanced_accuracy"] or 0) >= (ew["balanced_accuracy"] or 0),
                         "onset_recall_ge_EW": (fr["onset_recall"] or 0) >= (ew["onset_recall"] or 0),
                         "fp_rate_le_EW_plus_0.05": (fr["fp_rate"] or 0) <= (ew["fp_rate"] or 0) + 0.05,
                         "paired_brier_ci_upper_lt_0": pb["ci95"][1] < 0},
            "paired_brier_vs_EW": pb, "sign_vs_EW": qsign(D, fw, "F E58-EW (warning)")}
    qimp["improved_over_EW"] = all(qimp["criteria"].values())
    # ablation table
    abl = []
    for n in ("A gov-only (forecast)", "B news-only (forecast)", "C gov+news (forecast)", "D gov+news+history (forecast)"):
        r = allr.loc[n]
        abl.append({"model": n, "accuracy": r["accuracy"], "balanced_accuracy": r["balanced_accuracy"], "brier": r["brier"],
                    "roc_auc": r["roc_auc"], "recall_HIGH": r["recall_HIGH"], "fp_rate": r["fp_rate"],
                    "onset_recall_warning": allr.loc[n.replace("(forecast)", "(warning)"), "onset_recall"]})
    for k, v in qnews.items():
        if isinstance(v, dict) and "ci95" in v:
            abl.append({"model": f"paired Brier {k}", "brier": v["diff"], "ci_low": v["ci95"][0], "ci_high": v["ci95"][1]})
    pd.DataFrame(abl).round(4).to_csv(E60 / "NEWS_ABLATION_RESULTS.csv", index=False)
    # per quarter and province for the final candidate, A, C, E56, EW
    qp = []
    for grp, key in (("quarter", "target"), ("province", "province")):
        for k, g in D.groupby(key):
            for n in (f"{final} (forecast)", fw, "A gov-only (forecast)", "C gov+news (forecast)", "E E56 (forecast)", "F E58-EW (warning)"):
                mm = metr(g["y"], g[f"{n}_w"], g[f"{n}_prob"])
                qp.append({"by": grp, "group": k, "model": n, **{x: mm[x] for x in ("n", "HIGH", "TP", "TN", "FP", "FN", "accuracy",
                                                                                    "balanced_accuracy", "recall_HIGH", "brier")},
                           "onsets": int(g["onset"].sum()), "onsets_warned": int(g[g["onset"] == 1][f"{n}_w"].sum())})
    pd.DataFrame(qp).round(4).drop_duplicates().to_csv(E60 / "QUARTERLY_AND_PROVINCE_RESULTS.csv", index=False)
    D.to_csv(E60 / "out" / "scored_rows.csv", index=False, float_format="%.6g")
    res = {"final_candidate": final, "q_news": qnews, "q_improve": qimp}
    (E60 / "out" / "score.json").write_text(json.dumps(res, indent=1, default=float))
    f = lambda v: None if v is None or v != v else round(float(v), 3)  # noqa: E731
    for r in rows:
        if r["split"].startswith(("ALL", "DEV", "TEST")) or "SOP" in r["split"]:
            print(f"{r['split'][:6]:6s} {r['model']:32s} acc {f(r['accuracy'])} bal {f(r['balanced_accuracy'])} recH {f(r['recall_HIGH'])} "
                  f"fpr {f(r['fp_rate'])} brier {f(r.get('brier'))} auc {f(r.get('roc_auc'))} onset {f(r.get('onset_recall'))} "
                  f"q>=.75 {r.get('quarters_ge_0.75')}/{r.get('quarters')}")
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()

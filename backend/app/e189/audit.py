"""
E189 step 1: audit of E184 (no training). Reads stored rows only; writes data/e189/audit/.

    python -m app.e189.audit
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, norm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from app.e178 import common as K

OUT = K.D / "e189" / "audit"
KEYS = ["key", "survey", "lead"]
CALABARZON = {"batangas", "cavite", "laguna", "quezon", "rizal"}
B = 2000


def truth(lead):
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    return G[G["lead"] == lead].reset_index(drop=True)


def rows(path, lead, p="p", **flt):
    d = pd.read_csv(path, float_precision="round_trip")
    d = d[d["lead"] == lead]
    for k, v in flt.items():
        d = d[d[k] == v]
    return d.groupby(KEYS)[p].mean().reset_index().rename(columns={p: "p"})


def metrics(y, p, q, cut=0.5):
    y, p, q = np.asarray(y).astype(bool), np.asarray(p, float), np.asarray(q, float)
    pr = p >= cut
    tp, fp, fn, tn = int((pr & y).sum()), int((pr & ~y).sum()), int((~pr & y).sum()), int((~pr & ~y).sum())
    n = len(y)
    acc = (tp + tn) / n
    z = 1.959964
    wl = (acc + z * z / (2 * n) - z * math.sqrt(acc * (1 - acc) / n + z * z / (4 * n * n))) / (1 + z * z / n)
    wh = (acc + z * z / (2 * n) + z * math.sqrt(acc * (1 - acc) / n + z * z / (4 * n * n))) / (1 + z * z / n)
    rec, spec = tp / (tp + fn), tn / (tn + fp)
    prec = tp / (tp + fp) if tp + fp else float("nan")
    lp = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    cal = LogisticRegression(C=1e6).fit(lp[:, None], y)
    return {"n": n, "positives": int(y.sum()), "negatives": int((~y).sum()), "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
            "correct": tp + tn, "accuracy": round(acc, 4), "accuracy_wilson95": [round(wl, 3), round(wh, 3)],
            "balanced_accuracy": round((rec + spec) / 2, 4), "precision": round(prec, 3), "recall": round(rec, 3), "specificity": round(spec, 3),
            "f1": round(2 * prec * rec / (prec + rec), 3), "false_positive_rate": round(fp / (fp + tn), 3), "false_negative_rate": round(fn / (fn + tp), 3),
            "brier_vs_q_true": round(float(np.mean((p - q) ** 2)), 4), "brier_vs_label": round(float(np.mean((p - y) ** 2)), 4),
            "roc_auc": round(float(roc_auc_score(y, p)), 3), "pr_auc": round(float(average_precision_score(y, p)), 3),
            "calibration_intercept": round(float(cal.intercept_[0]), 3), "calibration_slope": round(float(cal.coef_[0, 0]), 3)}


def cluster_ci(x, f, seed=189):
    """95 % region-cluster bootstrap CI of statistic f(frame)."""
    rng = np.random.default_rng(seed)
    regs = x["region"].unique()
    g = {r: x[x["region"] == r] for r in regs}
    v = [f(pd.concat([g[r] for r in rng.choice(regs, len(regs))], ignore_index=True)) for _ in range(B)]
    return [round(float(np.nanpercentile(v, 2.5)), 4), round(float(np.nanpercentile(v, 97.5)), 4)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {"leads": {}}
    e184o = K.D / "e184" / "out"
    variants = {
        "E168": lambda L: rows(e184o / ("lead3_rows.csv" if L == 3 else "all_rows.csv"), L, arm="E168_rerun", mode="main"),
        "E184": lambda L: rows(e184o / ("lead3_rows.csv" if L == 3 else "all_rows.csv"), L, arm="E184", mode="main"),
        "E182": lambda L: rows(K.D / "e182" / "out" / ("lead3_rows.csv" if L == 3 else "all_rows.csv"), L, arm="E182", mode="main"),
        "E185": lambda L: rows(K.D / "e185" / "out" / "all_rows.csv", L, arm="E185", mode="main"),
        "E186": lambda L: rows(K.D / "e186" / "out" / "all_rows.csv", L, arm="E186", mode="main"),
        "E188a": lambda L: rows(K.D / "e188" / "out" / "rows.csv", L, arm="E188a"),
        "E188b": lambda L: rows(K.D / "e188" / "out" / "rows.csv", L, arm="E188b"),
        "E180": lambda L: rows(K.D / "e180" / "out" / "all_rows.csv", L, arm="E180", mode="main"),
    }
    all_err = []
    for L in (1, 2, 3):
        x = truth(L)
        avail = {}
        for name, f in variants.items():
            try:
                r = f(L)
            except Exception:
                continue
            if len(r) == 72:
                x = x.merge(r.rename(columns={"p": name}), on=KEYS)
                avail[name] = True
        assert len(x) == 72
        y = x["y_high"].astype(bool)
        R = {"variants_available": list(avail)}
        R["metrics"] = {m: metrics(y, x[m], x["q_true"]) for m in ["PERS"] + list(avail)}
        R["E184_ci"] = {"accuracy": cluster_ci(x, lambda d: float(((d["E184"] >= .5) == d["y_high"].astype(bool)).mean())),
                        "brier": cluster_ci(x, lambda d: float(np.mean((d["E184"] - d["q_true"]) ** 2))),
                        "accuracy_minus_E168": cluster_ci(x, lambda d: float(((d["E184"] >= .5) == d["y_high"].astype(bool)).mean() - ((d["E168"] >= .5) == d["y_high"].astype(bool)).mean()))}
        cA, cB = (x["E184"] >= .5) == y, (x["E168"] >= .5) == y
        b, c = int((cA & ~cB).sum()), int((~cA & cB).sum())
        R["mcnemar_E184_vs_E168"] = {"E184_only_right": b, "E168_only_right": c, "p_exact": round(float(binomtest(b, b + c, .5).pvalue), 4) if b + c else 1.0}
        # by survey round (temporal windows)
        R["by_round"] = {s: {"n": int(len(g)), "positives": int(g["y_high"].sum()), "E168": round(float(((g["E168"] >= .5) == g["y_high"].astype(bool)).mean()), 3),
                             "E184": round(float(((g["E184"] >= .5) == g["y_high"].astype(bool)).mean()), 3), "PERS": round(float(((g["PERS"] >= .5) == g["y_high"].astype(bool)).mean()), 3)}
                         for s, g in x.groupby("survey")}
        R["by_island"] = {s: {"n": int(len(g)), "E184": round(float(((g["E184"] >= .5) == g["y_high"].astype(bool)).mean()), 3)} for s, g in x.groupby("island")}
        # label uncertainty: q_true = P(true prevalence above the HIGH line | survey estimate, se)
        q = x["q_true"].values
        R["label_uncertainty"] = {
            "oracle_expected_accuracy": round(float(np.mean(np.maximum(q, 1 - q))), 4),
            "rows_label_uncertain_q_0.2_0.8": int(((q > .2) & (q < .8)).sum()),
            "E184_errors": int((~cA).sum()),
            "E184_errors_on_uncertain_labels": int((~cA & (q > .2) & (q < .8)).sum()),
            "E184_errors_with_p_within_0.1_of_cut": int((~cA & (np.abs(x["E184"] - .5) < .1)).sum())}
        # hard rows: wrong in every variant
        wrong_all = np.ones(len(x), bool)
        for m in avail:
            wrong_all &= ((x[m] >= .5) != y).values
        R["hard_rows"] = {"wrong_in_every_variant": int(wrong_all.sum()), "variants": len(avail),
                          "ceiling_if_only_non_hard_fixed": round(1 - wrong_all.sum() / 72, 4),
                          "best_variant_accuracy": max(R["metrics"][m]["accuracy"] for m in avail)}
        R["needed_for_80pct"] = {"correct_needed": 58, "E184_correct": R["metrics"]["E184"]["correct"], "extra_rows_needed": 58 - R["metrics"]["E184"]["correct"]}
        cal = x[x["key"].isin(CALABARZON)]
        R["calabarzon_rows"] = {"n": int(len(cal)), "rows": cal[["key", "survey", "y_true", "q_true", "y_high"]].assign(E184=cal["E184"].round(3)).to_dict("records")}
        x["lead_"] = L
        x["E184_wrong"] = ~cA
        x["wrong_every_variant"] = wrong_all
        all_err.append(x[["key", "province", "region", "island", "survey", "lead_", "y_true", "se_true", "q_true", "y_high", "PERS", "E168", "E184", "E184_wrong", "wrong_every_variant"]])
        rep["leads"][L] = R
    E = pd.concat(all_err, ignore_index=True)
    E.to_csv(OUT / "rows_leads1_3.csv", index=False, lineterminator="\n")
    prov = E.groupby(["province", "survey"]).agg(n=("E184_wrong", "size"), E184_wrong=("E184_wrong", "sum"), q_true=("q_true", "mean")).reset_index()
    rep["provinces_wrong_at_all_3_leads"] = prov[prov["E184_wrong"] == 3][["province", "survey", "q_true"]].round(3).to_dict("records")
    # power: discordant pairs needed for an exact McNemar p < 0.05 with zero losses
    rep["power"] = {"min_net_fixes_with_zero_losses_for_p_lt_0.05": next(k for k in range(1, 20) if binomtest(k, k, .5).pvalue < .05),
                    "one_province_pp": round(100 / 72, 2)}
    r184 = json.loads((K.D / "e184" / "out" / "results.json").read_text())
    rep["controls_E184"] = {"leakage_max_abs_change_corrupt": r184["leakage_max_abs_change"], "shuffle": r184["shuffle"]}
    fid = json.loads((K.D / "e178" / "out" / "fidelity.json").read_text())
    rep["synthetic_fidelity_jitter"] = {j: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d["jitter"].items() if k in ("median_ks", "max_w1_sd", "corr_mad", "tstr_ratio", "copy_share", "exact_copies", "sign_agreement_share", "passed", "n_real", "n_syn")}
                                        for j, d in fid["jobs"].items() if "jitter" in d}
    rep["reproduction"] = {"E184_rerun_in_E188_max_abs_diff_p_leads_1_6": json.loads((K.D / "e188" / "out" / "results.json").read_text())["leads"]["1"]["reproduction_max_abs_diff_p"],
                           "stored_vs_recomputed_accuracy": {L: [r184["leads"][str(L)]["class"]["E184"]["accuracy"] if str(L) in r184["leads"] else None, rep["leads"][L]["metrics"]["E184"]["accuracy"]] for L in (1, 2, 3)}}
    K.dump_json(rep, OUT / "audit.json")
    for L, R in rep["leads"].items():
        m = R["metrics"]["E184"]
        print(f"L{L} E184 acc {m['accuracy']} {m['accuracy_wilson95']} ({m['correct']}/72, pos {m['positives']}) bal {m['balanced_accuracy']} prec {m['precision']} rec {m['recall']} spec {m['specificity']} "
              f"F1 {m['f1']} FPR {m['false_positive_rate']} FNR {m['false_negative_rate']} brier {m['brier_vs_q_true']} AUC {m['roc_auc']} PR-AUC {m['pr_auc']} cal {m['calibration_intercept']}/{m['calibration_slope']}")
        print("   ci", R["E184_ci"], "mcnemar", R["mcnemar_E184_vs_E168"])
        print("   rounds", R["by_round"])
        print("   label", R["label_uncertainty"], "hard", R["hard_rows"], "variants", R["variants_available"])
        print("   accuracies", {k: v["accuracy"] for k, v in R["metrics"].items()}, "calabarzon n", R["calabarzon_rows"]["n"])
    print("provinces wrong at all 3 leads:", rep["provinces_wrong_at_all_3_leads"])
    print("power", rep["power"], "controls", rep["controls_E184"])
    print("repro", rep["reproduction"])


if __name__ == "__main__":
    main()

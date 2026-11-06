"""
Final audit (reproduction only; fits nothing). Recomputes every reported metric from the saved out-of-sample forecasts,
traces both calibration definitions used in earlier reports, draws reliability diagrams, and writes one JSON.

    python -m app.final_audit.run -> data/final_audit/out/audit.json, reliability_*.png
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from app.e147 import evaluate as E7
from app.e151 import prov as Pv
from app.e156 import leads as LD
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "final_audit" / "out"
K = ["key", "survey", "lead"]
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def load():
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    e164 = pd.read_csv(D / "e164" / "out" / "oof.csv")[K + ["mu_AUTO", "AUTO", "half_AUTO"]]
    F = G.merge(e164, on=K, how="left")
    for name, files in (("FINAL", ["e165/out/all_rows.csv"]), ("E166", ["e166/out/all_rows.csv", "e166/out/all_rows_l3_8.csv"]), ("E167", ["e167/out/all_rows.csv"])):
        a = pd.concat([pd.read_csv(D / f) for f in files if (D / f).exists()])
        a = a[a["mode"] == "main"][K + ["mu", "p", "half"]].rename(columns={"mu": f"mu_{name}", "p": name, "half": f"half_{name}"})
        F = F.merge(a, on=K, how="left")
    F["ALWAYS_LOW"], F["mu_ALWAYS_LOW"], F["half_ALWAYS_LOW"] = 0.0, -5.0, 0.0
    for b in ("PSA", "LR"):
        F[f"mu_{b}"] = np.log(np.clip(F[b], 1e-4, 1 - 1e-4) / (1 - np.clip(F[b], 1e-4, 1 - 1e-4)))
        F[f"half_{b}"] = 0.0
    return F


def prob_slope(x, a, rng, n=2000):
    p = np.clip(x[a].values, 1e-4, 1 - 1e-4)
    z, y = np.log(p / (1 - p)), x["y_high"].values
    def fit(ii):
        if len(np.unique(y[ii])) < 2 or np.std(z[ii]) == 0:
            return np.nan
        return float(LogisticRegression(C=1e6).fit(z[ii].reshape(-1, 1), y[ii]).coef_[0, 0])
    regs = list(x.groupby("region").indices.values())
    bs = [b for b in (fit(np.concatenate([regs[j] for j in rng.integers(0, len(regs), len(regs))])) for _ in range(n)) if b == b]
    return round(fit(np.arange(len(x))), 3), [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)]


def metrics(x, a, rng):
    y = x["y_high"].values == 1
    p = x[a].values >= .5
    tp, fp, fn, tn = int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum()), int((~p & ~y).sum())
    hp, hr = tp / max(1, tp + fp), tp / max(1, tp + fn)
    lp, lr = tn / max(1, tn + fn), tn / max(1, tn + fp)
    f_h = 2 * hp * hr / max(1e-9, hp + hr)
    f_l = 2 * lp * lr / max(1e-9, lp + lr)
    out = {"n": int(len(x)), "accuracy": round((tp + tn) / len(x), 3), "balanced_accuracy": round((hr + lr) / 2, 3), "high_precision": round(hp, 3), "high_recall": round(hr, 3), "low_precision": round(lp, 3), "low_recall": round(lr, 3),
           "f1_high": round(f_h, 3), "macro_f1": round((f_h + f_l) / 2, 3), "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, "brier": round(float(np.mean((x[a] - x["q_true"]) ** 2)), 4)}
    if a != "ALWAYS_LOW":
        out["roc_auc"], out["pr_auc"] = round(float(roc_auc_score(y, x[a])), 3), round(float(average_precision_score(y, x[a])), 3)
        if a not in ("PSA", "LR"):
            sc = Pv.scale_test(x, a, rng, n=2000)
            out["C4_definition_logit_level_slope"] = round(float(np.polyfit(x[f"mu_{a}"], x["y_true"], 1)[0]), 3)
            out["C4_slope_ci95"] = [round(v, 2) for v in sc["slope_ci95"]]
            out["mean_signed_error_pts"] = round(float(np.mean(pct(x[f"mu_{a}"]) - pct(x["y_true"]))), 2)
        out["probability_logistic_slope"], out["probability_logistic_slope_ci95"] = prob_slope(x, a, rng)
        b = pd.cut(x[a], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
        out["reliability"] = x.groupby(b, observed=False).agg(n=("y_high", "size"), mean_p=(a, "mean"), observed=("y_high", "mean")).round(3).reset_index().astype(str).to_dict("records")
    return out


def diagram(x, arms, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "--", color="grey", lw=1, label="perfect")
    for a in arms:
        b = pd.cut(x[a], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
        g = x.groupby(b, observed=False).agg(m=(a, "mean"), o=("y_high", "mean"), n=("y_high", "size")).dropna()
        ax.plot(g["m"], g["o"], "o-", label=a)
        for _, r in g.iterrows():
            ax.annotate(int(r["n"]), (r["m"], r["o"]), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("Mean predicted P(HIGH)")
    ax.set_ylabel("Observed HIGH rate")
    ax.set_title("Reliability, Lead 1 (n = 72; point labels = rows)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    F = load()
    rng = np.random.default_rng(2026)
    arms = ["ALWAYS_LOW", "PERS", "PSA", "LR", "E158", "AUTO", "FINAL", "E166", "E167"]
    res = {"leads": {}, "by_round": {}, "calabarzon": {}}
    for L in (1, 2):
        x = F[F["lead"] == L].reset_index(drop=True)
        res["leads"][L] = {a: metrics(x, a, rng) for a in arms if x[a].notna().all()}
        res["by_round"][L] = {s: {a: {"n": int(len(g)), "accuracy": round(float(((g[a] >= .5) == (g["y_high"] == 1)).mean()), 3), "brier": round(float(np.mean((g[a] - g["q_true"]) ** 2)), 4),
                                      "mean_signed_error_pts": round(float(np.mean(pct(g[f"mu_{a}"]) - pct(g["y_true"]))), 2) if a not in ("ALWAYS_LOW", "PSA", "LR") else None} for a in ("E158", "E166")} for s, g in x.groupby("survey")}
        if L == 1:
            c = x[x["province"].isin(CAL)]
            res["calabarzon"] = c[["province", "survey"]].assign(observed=pct(c["y_true"]).round(1), E158=pct(c["mu_E158"]).round(1), E166=pct(c["mu_E166"]).round(1), E158_class_right=((c["E158"] >= .5) == (c["y_high"] == 1)), E166_class_right=((c["E166"] >= .5) == (c["y_high"] == 1))).to_dict("records")
            diagram(x, ["E158", "E166"], OUT / "reliability_lead1_E158_E166.png")
            diagram(x, ["PERS", "E158"], OUT / "reliability_lead1_PERS_E158.png")
    res["e156_reliability_lead1"] = {a: LD.evaluate(F[F["lead"] == 1].reset_index(drop=True), a, a)["leads"][0]["criteria"] for a in ("E158", "AUTO", "FINAL", "E166", "E167")}
    (OUT / "audit.json").write_text(json.dumps(res, indent=1, default=str), newline="\n")
    cols = ("n", "accuracy", "balanced_accuracy", "high_precision", "high_recall", "low_precision", "low_recall", "macro_f1", "roc_auc", "pr_auc", "brier", "C4_definition_logit_level_slope", "C4_slope_ci95", "probability_logistic_slope", "probability_logistic_slope_ci95", "mean_signed_error_pts")
    for L in (1, 2):
        print(f"\nLead {L}")
        print(pd.DataFrame({a: {c: v.get(c) for c in cols} | {"conf": v["confusion"]} for a, v in res["leads"][L].items()}).T.to_string())
    print(json.dumps(res["by_round"], indent=0))
    print(json.dumps(res["e156_reliability_lead1"]))


if __name__ == "__main__":
    main()

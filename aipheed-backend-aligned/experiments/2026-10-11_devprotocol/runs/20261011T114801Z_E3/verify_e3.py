"""
Independent verification of E3 run 20261011T114801Z_E3. Read-only: fits no model, writes one CSV.

Recomputes, without the runner's metric or bootstrap functions:
  * file integrity against manifest.json;
  * labels (y) from data/processed/labels.parquet and thresholds from the eligibility rules;
  * carry-forward and Equation 3 predictions from source data;
  * every metric, from the saved prediction files;
  * the quarter bootstraps (exact reproduction + an independent re-implementation).

Run from aipheed-backend-aligned/:
    PYTHONPATH=. ../backend/venv/Scripts/python.exe -W ignore experiments/2026-10-11_devprotocol/runs/20261011T114801Z_E3/verify_e3.py
"""
import glob
import hashlib
import json
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RUN = Path("experiments/2026-10-11_devprotocol/runs/20261011T114801Z_E3")
E1RUN = Path("experiments/2026-10-11_devprotocol/runs/20261011T111651Z")
OUT = RUN / "verification_recomputed_metrics.csv"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
report = {}

# ---------------------------------------------------------------- 1. file integrity
man = json.loads((RUN / "manifest.json").read_text())
cfg = json.loads((RUN / "config.json").read_text())
mism = [n for n, h in man["outputs_sha256"].items() if sha(RUN / n) != h]
report["files_in_manifest"] = len(man["outputs_sha256"])
report["manifest_hash_mismatches"] = mism
pred_files = sorted(glob.glob(str(RUN / "pred_*.csv")))
report["prediction_files"] = len(pred_files)
label_cols = {"y", "stress_score", "label_stress", "label"}
report["prediction_files_with_label_columns"] = [os.path.basename(p) for p in pred_files
                                                 if label_cols & set(pd.read_csv(p, nrows=0).columns)]
write_order = list(man["outputs_sha256"].keys())
report["all_predictions_written_before_scored_rows"] = all(
    write_order.index(os.path.basename(p)) < write_order.index("scored_rows.csv") for p in pred_files)
report["labels_revealed"] = len(man["labels_revealed_after_predictions"])
report["protected_files_unchanged_at_runtime"] = man["protected_files_unchanged"]

# ---------------------------------------------------------------- 2. rebuild labels and thresholds
import scripts.supplementary.devprotocol_rule_l as D

lab = pd.read_parquet("data/processed/labels.parquet")[["quarter", "province_code", "stress_score"]]
lab = lab[(lab["quarter"] >= "2021-Q1") & (lab["quarter"] <= "2025-Q4")]
report["label_rows_used"] = len(lab)
tau_global = float(lab["stress_score"].median())
tests = cfg["test_quarters"]
e1cfg = json.loads((E1RUN / "config.json").read_text())
elig_now = {q: D.eligible_training_quarters(q, "development") for q in tests}
report["test_quarters_same_as_E1"] = tests == e1cfg["test_primary"]
report["eligibility_same_as_E1_config"] = all(cfg["eligible_training_quarters"][q] == e1cfg["eligible_training_quarters"][q]
                                              for q in tests)
report["eligibility_same_as_recomputed_now"] = all(cfg["eligible_training_quarters"][q] == elig_now[q] for q in tests)
report["min_training_quarters"] = min(len(v) for v in elig_now.values())
tau_origin = {q: float(lab[lab["quarter"].isin(elig_now[q])]["stress_score"].median()) for q in tests}

preds = pd.concat([pd.read_csv(p).assign(file=os.path.basename(p)) for p in pred_files], ignore_index=True)
preds["analysis"] = preds["file"].str.extract(r"pred_(A-[a-z]+)__")[0]
preds["variant"] = preds["file"].str.extract(r"__(base|plusFSSI)__")[0].replace({"plusFSSI": "+FSSI"})
exp_tau = np.where(preds["analysis"] == "A-origin", preds["target_quarter"].map(tau_origin), tau_global)
report["max_abs_tau_difference"] = float(np.abs(preds["tau"] - exp_tau).max())
report["quarters_in_predictions"] = sorted(preds["target_quarter"].unique())
report["any_2026_row"] = bool(preds["target_quarter"].str.startswith("2026").any())
y = preds.merge(lab, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"], how="left")
preds["y"] = (y["stress_score"].values > preds["tau"].values).astype(int)

sr = pd.read_csv(RUN / "scored_rows.csv")
chk = preds.merge(sr, on=["analysis", "variant", "target_quarter", "province_code", "model"], suffixes=("", "_saved"))
report["scored_rows_matched"] = f"{len(chk)}/{len(sr)}"
report["y_mismatches_vs_saved"] = int((chk["y"] != chk["y_saved"]).sum())
report["pred_mismatches_vs_saved"] = int((chk["pred"] != chk["pred_saved"]).sum())

# ---------------------------------------------------------------- 3. baselines rebuilt from source
frame, _ = D.development_frame()
cf_bad = eq_bad = 0
for (a, v, q), g in preds.groupby(["analysis", "variant", "target_quarter"]):
    t = g["tau"].iloc[0]
    anchor = max(elig_now[q])
    last = lab[lab["quarter"] == anchor].set_index("province_code")["stress_score"]
    cf = g[g["model"] == "carry-forward"].set_index("province_code")
    cf_bad += int(((last.reindex(cf.index) > t).astype(int) != cf["pred"]).sum())
    te = frame[frame["target_quarter"] == q].set_index("province_code")
    s = te["sws_hunger"] + 2 * te["cpi_rel"]
    eq = g[g["model"] == "Eq3-rule"].set_index("province_code")
    eq_bad += int(((s.reindex(eq.index) > t).astype(int) != eq["pred"]).sum())
    eq_bad += int((np.abs((s.reindex(eq.index) - t) - eq["score"]) > 1e-9).sum())
report["carry_forward_prediction_mismatches"] = cf_bad
report["eq3_prediction_or_score_mismatches"] = eq_bad


# ---------------------------------------------------------------- 4. metrics (own implementation)
def auc(yv, s):
    """Mann-Whitney AUC with tie correction; None if undefined."""
    s = np.asarray(s, float)
    if np.isnan(s).any() or len(set(yv)) < 2 or np.ptp(s) == 0:
        return None
    pos, neg = s[yv == 1], s[yv == 0]
    gt = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return gt / (len(pos) * len(neg))


def weighted_prf(yv, pv):
    out = []
    for c in (0, 1):
        tp = ((pv == c) & (yv == c)).sum()
        prec = tp / (pv == c).sum() if (pv == c).sum() else 0.0
        rec = tp / (yv == c).sum()
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out.append((prec, rec, f1, (yv == c).sum()))
    w = np.array([o[3] for o in out]) / len(yv)
    return [float(sum(w[i] * out[i][k] for i in range(2))) for k in range(3)]


rows = []
for (a, v, m), g in preds.groupby(["analysis", "variant", "model"]):
    yv, pv = g["y"].values, g["pred"].values
    tn, fp = int(((yv == 0) & (pv == 0)).sum()), int(((yv == 0) & (pv == 1)).sum())
    fn, tp = int(((yv == 1) & (pv == 0)).sum()), int(((yv == 1) & (pv == 1)).sum())
    hr, lr = tp / (tp + fn), tn / (tn + fp)
    p, r, f = weighted_prf(yv, pv)
    rows.append({"analysis": a, "variant": v, "model": m, "correct": tp + tn, "rows": len(yv),
                 "row_accuracy": (tp + tn) / len(yv),
                 "mean_quarter_accuracy": g.assign(c=yv == pv).groupby("target_quarter")["c"].mean().mean(),
                 "balanced_accuracy": (hr + lr) / 2, "high_recall": hr, "low_recall": lr,
                 "weighted_precision": p, "weighted_recall": r, "weighted_f1": f,
                 "roc_auc": auc(yv, g["score"].values), "TN": tn, "FP": fp, "FN": fn, "TP": tp,
                 "n_high": int(yv.sum()), "n_low": int(len(yv) - yv.sum())})
rec = pd.DataFrame(rows)
rec.round(4).to_csv(OUT, index=False)

saved = json.loads((RUN / "metrics.json").read_text())["results"]
diffs = []
for _, r in rec.iterrows():
    s = saved[f"{r['analysis']} | {r['variant']}"][r["model"]]
    for mine, theirs in (("mean_quarter_accuracy", "mean_quarter_accuracy"), ("balanced_accuracy", "balanced_accuracy"),
                         ("high_recall", "high_recall"), ("low_recall", "low_recall"),
                         ("weighted_precision", "weighted_precision"), ("weighted_f1", "weighted_f1"),
                         ("roc_auc", "roc_auc")):
        a_, b_ = r[mine], s.get(theirs)
        if (a_ is None or (isinstance(a_, float) and np.isnan(a_))) and b_ is None:
            continue
        if a_ is None or b_ is None or abs(float(a_) - float(b_)) > 5e-4:
            diffs.append((r["analysis"], r["variant"], r["model"], mine, a_, b_))
    cm = s["confusion_[[TN,FP],[FN,TP]]"]
    if cm != [[r["TN"], r["FP"]], [r["FN"], r["TP"]]]:
        diffs.append((r["analysis"], r["variant"], r["model"], "confusion", cm))
report["metric_discrepancies_vs_saved"] = diffs

# ---------------------------------------------------------------- 5. bootstraps
def ba(yv, pv):
    yv, pv = np.asarray(yv), np.asarray(pv)
    if len(set(yv)) < 2:
        return np.nan
    return (np.mean(pv[yv == 1] == 1) + np.mean(pv[yv == 0] == 0)) / 2


boot = {}
prim = preds[(preds["analysis"] == "A-origin") & (preds["variant"] == "base")]
qs = sorted(prim["target_quarter"].unique())
e3 = prim[prim["model"] == "E3-LightGBM"].set_index(["target_quarter", "province_code"]).sort_index()
for base in ("carry-forward", "Eq3-rule"):
    b = prim[prim["model"] == base].set_index(["target_quarter", "province_code"]).sort_index()
    blocks = {q: (e3.loc[q, "y"].values, e3.loc[q, "pred"].values, b.loc[q, "pred"].values) for q in qs}
    # (a) exact reproduction of the runner's scheme: default_rng(42), integers(0, 7, 7), skip one-class draws
    rng = np.random.default_rng(42)
    d_a, skip = [], 0
    for _ in range(10_000):
        idx = rng.integers(0, len(qs), len(qs))
        yy = np.concatenate([blocks[qs[i]][0] for i in idx])
        d = ba(yy, np.concatenate([blocks[qs[i]][1] for i in idx])) - ba(yy, np.concatenate([blocks[qs[i]][2] for i in idx]))
        (skip := skip + 1) if np.isnan(d) else d_a.append(d)
    # (b) independent re-implementation: different generator and draw method, 20,000 draws
    rng2 = np.random.Generator(np.random.PCG64(2026))
    d_b = []
    for _ in range(20_000):
        pick = rng2.choice(qs, size=len(qs), replace=True)
        yy = np.concatenate([blocks[q][0] for q in pick])
        d = ba(yy, np.concatenate([blocks[q][1] for q in pick])) - ba(yy, np.concatenate([blocks[q][2] for q in pick]))
        if not np.isnan(d):
            d_b.append(d)
    yall = np.concatenate([blocks[q][0] for q in qs])
    point = ba(yall, np.concatenate([blocks[q][1] for q in qs])) - ba(yall, np.concatenate([blocks[q][2] for q in qs]))
    boot[base] = {"point": round(point, 4),
                  "exact_repro_ci95": [round(float(x), 4) for x in np.percentile(d_a, [2.5, 97.5])],
                  "exact_repro_draws_used": len(d_a), "exact_repro_skipped": skip,
                  "share_of_draws_le_0": round(float(np.mean(np.array(d_a) <= 0)), 4),
                  "independent_ci95_seed2026_20k": [round(float(x), 4) for x in np.percentile(d_b, [2.5, 97.5])]}
# accuracy interval: quarter bootstrap of E3 mean-quarter accuracy
acc_q = e3.assign(c=e3["y"] == e3["pred"]).groupby(level=0)["c"].mean().reindex(qs).values
rng = np.random.default_rng(42)
acc = [acc_q[rng.integers(0, 7, 7)].mean() for _ in range(10_000)]
boot["E3_mean_quarter_accuracy_ci95"] = [round(float(x), 4) for x in np.percentile(acc, [2.5, 97.5])]
boot["E3_per_quarter_accuracy"] = dict(zip(qs, acc_q.round(2).tolist()))
saved_boot = saved["A-origin | base"]["paired_balanced_accuracy_bootstrap_E3_minus"]
boot["saved"] = {k: saved_boot[k] for k in ("carry-forward", "Eq3-rule")}
boot["saved_E3_accuracy_ci95"] = saved["A-origin | base"]["E3-LightGBM"]["quarter_bootstrap_accuracy_95"]
report["bootstrap"] = boot

# same LOW rows caught?
low = prim[prim["y"] == 0].pivot_table(index=["target_quarter", "province_code"], columns="model", values="pred")
report["LOW_rows_A_origin"] = low[["E3-LightGBM", "carry-forward", "Eq3-rule"]].reset_index().to_dict("records")

# ---------------------------------------------------------------- 6. production / provenance
prov_e1, prov_e3 = e1cfg["input_provenance_sha256"], cfg["input_provenance_sha256"]
common = sorted(set(prov_e1) & set(prov_e3))
report["provenance_files_compared_E1_E3_now"] = len(common)
report["provenance_changed"] = [k for k in common if not (prov_e1[k] == prov_e3[k] == sha(k))]
print(json.dumps(report, indent=1, default=str))

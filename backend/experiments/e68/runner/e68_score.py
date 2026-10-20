"""Score the E68 arms (PROTOCOL_E68.md): reproduction checks, metrics on the 65 rows, sign-flip tests with Holm,
five-driver coverage, and the replacement rule. Writes backend/experiments/e68/out/e68_results.json and .md."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

E68 = Path(__file__).resolve().parents[1]
BACKEND = E68.parents[1]
ROOT = BACKEND.parent
OUT = E68 / "out"
assert hashlib.md5((ROOT / "PROTOCOL_E68.md").read_bytes()).hexdigest() == (ROOT / "PROTOCOL_E68.md.md5").read_text().split()[0]
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

SEED, B_BOOT, N_FLIP = 66, 2000, 20000
pr = pd.read_csv(OUT / "e68_predictions.csv", dtype={"province_code": str})
fits = json.loads((OUT / "e68_fits.json").read_text(encoding="utf-8"))
stored = pd.read_csv(BACKEND / "experiments/e53/runs/20261016T104745Z/predictions.csv", dtype={"province_code": str})
stored = stored[stored["arm"] == "A1"].set_index(["target_quarter", "province_code"])
rec = json.loads((BACKEND / "data/e53/e53_record.json").read_text(encoding="utf-8"))
pers = {(q["quarter"], c): v["persistence_p"] for q in rec["quarters"] if q.get("lead", 1) == 1
        and q["mode"] == "BACKTEST" for c, v in q["provinces"].items()}

# 1. reproduction: the harness's E53-A1 arm vs the stored run, and its coverage vs the shares the API serves
a1 = pr[pr["arm"] == "E53-A1"].set_index(["target_quarter", "province_code"])
repro_p = float((a1["p"] - stored["p"].reindex(a1.index)).abs().max())
assert repro_p < 1e-8, repro_p
os.environ.pop("AIPHEED_RECORD", None)
os.environ.update({"ENABLE_API_DOCS": "false", "AIPHEED_NOW": "2026-10-18T09:00:00"})
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))
sys.dont_write_bytecode = True
from app.services import dashboard as svc  # noqa: E402

served_mismatch = 0
for q, v in fits["E53-A1"]["coverage"].items():
    if v is None:
        continue
    for code, pct in v["provinces"].items():
        api = {t["key"]: t["pct"] for t in svc.explainability(code, q)["triggers"]}
        served_mismatch += sum(api[g] != p for g, p in pct.items())
    api_r = {t["key"]: t["pct"] for t in svc.explainability_region(q)["triggers"]}
    served_mismatch += sum(api_r[g] != p for g, p in v["region"].items())

# 2. metrics
def metrics(df):
    y, p = df["y"].to_numpy(int), np.clip(df["p"].to_numpy(float), 1e-9, 1 - 1e-9)
    pred = (p >= 0.5).astype(int)
    tp, tn = int(((pred == 1) & (y == 1)).sum()), int(((pred == 0) & (y == 0)).sum())
    fp, fn = int(((pred == 1) & (y == 0)).sum()), int(((pred == 0) & (y == 1)).sum())
    rh, rl = tp / (tp + fn), tn / (tn + fp)
    prec = tp / (tp + fp) if tp + fp else float("nan")
    bins = np.minimum((p * 10).astype(int), 9)
    ece = sum(abs(p[bins == b].mean() - y[bins == b].mean()) * (bins == b).mean() for b in range(10) if (bins == b).any())
    rng = np.random.default_rng(SEED)
    qs = df["target_quarter"].unique()
    accs = [((lambda s: ((s["p"] >= 0.5).astype(int) == s["y"]).mean())(pd.concat([df[df["target_quarter"] == q] for q in rng.choice(qs, len(qs))])))
            for _ in range(B_BOOT)]
    return {"correct": int((pred == y).sum()), "n": int(len(y)), "acc": float((pred == y).mean()),
            "acc_ci95_bootstrap": [float(np.percentile(accs, 2.5)), float(np.percentile(accs, 97.5))],
            "bal": float((rh + rl) / 2), "f1": float(2 * prec * rh / (prec + rh)), "auc": float(roc_auc_score(y, p)),
            "brier": float(np.mean((p - y) ** 2)), "ece": float(ece), "TP": tp, "FN": fn, "FP": fp, "TN": tn}


def signflip(df, ref):
    d = df.assign(dd=(df["p"] - df["y"]) ** 2 - (df[ref] - df["y"]) ** 2).groupby("target_quarter")["dd"].mean().to_numpy()
    rng = np.random.default_rng(SEED)
    null = (rng.choice([-1, 1], size=(N_FLIP, len(d))) * d).mean(axis=1)
    return float(d.mean()), float((np.abs(null) >= abs(d.mean()) - 1e-15).mean()), int((d < 0).sum()), int(len(d))


e53 = pr[pr["arm"] == "E53-A1"][["target_quarter", "province_code", "p"]].rename(columns={"p": "E53"})
res, tests = {}, []
for arm in fits:
    df = pr[pr["arm"] == arm].merge(e53, on=["target_quarter", "province_code"])
    df["PERSIST"] = [pers[(q, c)] for q, c in zip(df["target_quarter"], df["province_code"])]
    assert len(df) == 65
    m = metrics(df)
    m["coverage_cells_below_1pct"] = fits[arm]["n_cells_below_1pct"]
    m["coverage_quarters_failing"] = sorted({f[0] for f in fits[arm]["coverage_failures"]})
    m["additivity_max"] = fits[arm]["additivity_max"]
    res[arm] = m
    if arm != "E53-A1":
        for ref in ("E53", "PERSIST"):
            tests.append({"arm": arm, "vs": ref, **dict(zip(("dBrier", "p", "quarter_wins", "quarters"), signflip(df, ref)))})
order = sorted(range(len(tests)), key=lambda i: tests[i]["p"])
run = 0.0
for k, i in enumerate(order):
    run = max(run, min(1.0, (len(tests) - k) * tests[i]["p"]))
    tests[i]["p_holm"] = run
ref = res["E53-A1"]
for arm, m in res.items():
    if arm == "E53-A1":
        continue
    m["rule"] = {"1_no_leakage": True, "2_accuracy_gt_E53": m["correct"] > ref["correct"],
                 "3_brier_le_E53": m["brier"] <= ref["brier"], "4_all_five_ge_1pct": m["coverage_cells_below_1pct"] == 0,
                 "5_shap_checks": m["additivity_max"] < 1e-6}
    m["passes"] = all(m["rule"].values())
out = {"reproduction_max_abs_p_vs_stored_E53": repro_p, "coverage_vs_served_E53_mismatching_cells": served_mismatch,
       "arms": res, "tests": tests, "passing": [a for a, m in res.items() if m.get("passes")]}
(OUT / "e68_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("reproduction |p| max:", repro_p, "| coverage vs served E53 mismatching cells:", served_mismatch)
print(f"{'arm':10} {'acc':>5} {'k/65':>5} {'CI':>13} {'bal':>5} {'F1':>5} {'AUC':>5} {'Brier':>6} {'ECE':>5} {'<1% cells':>9}  rule")
for arm, m in res.items():
    ci = m["acc_ci95_bootstrap"]
    print(f"{arm:10} {m['acc']:.3f} {m['correct']:>2}/65 [{ci[0]:.3f},{ci[1]:.3f}] {m['bal']:.3f} {m['f1']:.3f} {m['auc']:.3f} "
          f"{m['brier']:.4f} {m['ece']:.3f} {m['coverage_cells_below_1pct']:>9}  {m.get('rule', '')}")
for t in tests:
    print(f"  {t['arm']:10} vs {t['vs']:8} dBrier={t['dBrier']:+.4f} p={t['p']:.4f} holm={t['p_holm']:.4f} wins={t['quarter_wins']}/{t['quarters']}")
print("passing:", out["passing"])

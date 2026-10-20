"""E72: FIRI v2 (served candidate C3) on the only direct food-insecurity outcome, regional SWS hunger > 11.3% at the
target quarter, Lead 1 and Lead 2, against always-elevated, climatology and the hunger outlook alone (H1).
Input: inputs/firi2_regional.csv = FINAL_Thesis_System/out/firi2/regional.csv @ 089bdf2 (unchanged copy).
Quarters are the units (one regional value each); development quarters (FIRI v2 was designed on them)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "E70_Objectives_Completion" / "runner"))
import e70_metrics as MT  # noqa: E402

np, pd = MT.np, MT.pd
R = pd.read_csv(HERE.parent / "inputs" / "firi2_regional.csv")
out = {}
for lead, g in R.groupby("lead"):
    g = g.dropna(subset=["C3", "y"]).reset_index(drop=True).assign(target_=lambda f: f["target"])
    g["target"] = g["target_"]
    m = {a: MT.metrics(g["y"], g[a]) for a in ("C3", "H1", "ALWAYS", "CLIM")}
    pv = {}
    for b in ("H1", "ALWAYS", "CLIM"):
        p = MT.paired(g, "C3", b)
        pv[b] = {k: p[k] for k in ("brier_diff", "ci95", "mcnemar_a_right_only", "mcnemar_b_right_only", "mcnemar_p", "acc_diff")}
    out[int(lead)] = {"quarters": int(len(g)), "above_11_3": int(g["y"].sum()), "targets": [g["target"].min(), g["target"].max()],
                      "metrics": {a: {k: v[k] for k in ("correct", "n", "accuracy", "acc_wilson95", "recall_HIGH", "recall_LOW",
                                                         "balanced_accuracy", "auc_roc", "brier", "TP", "FP", "FN", "TN")} for a, v in m.items()},
                      "C3_vs": pv}
(HERE.parent / "out" / "regional_outcome.json").write_text(json.dumps(out, indent=1, default=float))
for lead, o in out.items():
    print("lead", lead, o["quarters"], "above", o["above_11_3"], o["targets"])
    for a, v in o["metrics"].items():
        print(f"  {a:6s} {v['correct']}/{v['n']} acc {v['accuracy']:.3f} W{[round(x,3) for x in v['acc_wilson95']]} recH {v['recall_HIGH']} recL {v['recall_LOW']} bal {v['balanced_accuracy']} brier {v['brier']:.3f}")
    for b, p in o["C3_vs"].items():
        print(f"  C3 vs {b}: dBrier {p['brier_diff']:+.3f} {np.round(p['ci95'],3)} McNemar {p['mcnemar_a_right_only']}/{p['mcnemar_b_right_only']} p {p['mcnemar_p']:.3f}")

"""Print E53_results.json compactly (read only)."""
import json
from pathlib import Path

r = json.loads((Path(__file__).resolve().parents[1] / "E53_results.json").read_text(encoding="utf-8"))
print("run", r["run"], "rows", r["n_test_rows"], "A0 diff", r["A0_max_abs_diff_vs_walk_forward"], "adoption", r["adoption"])
print("training rows Q4", r["training_rows_Q4_origin"])
for f, s in r["feature_stats_training_Q4_origin"].items():
    print(f"  {f:20s} var {s['variance']:10.4f} distinct {s['distinct']:3d} missing {s['missing']}")
print("cond Q4 test rows", r["cond_q4_2026_test_rows"])
for a, o in r["arms"].items():
    m = o["metrics"]
    print(f"\n=== {a} Q4 cfg {o['pool_configs']['2026-Q4']}")
    print(f"  acc {m['accuracy']:.4f} bal {m['balanced_accuracy']:.4f} auc {m['auc']:.4f} brier {m['brier']:.4f} ll {m['log_loss']:.4f} "
          f"prec {m['precision']:.3f} LOW {m['LOW_caught']}/{m['LOW_rows']} TP {m['TP']} FP {m['FP']} max {m['max_p']:.3f}")
    print("  train", o["train_Q4_origin"])
    print("  test", o.get("test_vs_A0"), "dBrier", o.get("brier_diff_vs_A0"))
    print("  mean five %", {k: round(v, 2) for k, v in o["mean_five_driver_pct_65_rows"].items()}, "nonzero", o["drivers_nonzero"])
    print("  mean with other %", {k: round(v, 1) for k, v in o["mean_pct_with_other_65_rows"].items()})
    print("  splits Q4", o["splits_cond_Q4_model"], "| cond splits sum 13", o["splits_cond_sum_13_test_models"])
    print("  Q4 index", {k: round(v, 4) for k, v in o["q4_2026"]["index"].items()})
    q = o["q4_2026"]["drivers"]
    print("  Q4 drivers CALABARZON (a)", q["CALABARZON"]["a"], "(b)", q["CALABARZON"]["b"], "EV", round(q["shap_expected_value_logodds"], 3))
    for p in ("Cavite", "Laguna", "Quezon", "Rizal", "Batangas"):
        print(f"    {p:9s} (a) {list(q[p]['a'].values())} (b) {list(q[p]['b'].values())} top {q[p]['top_shap']}")
    print("  index", {k: round(v, 3) for k, v in o["index"].items()})
    print("  criteria", o["adoption"])
    print("  configs", o["pool_configs"])

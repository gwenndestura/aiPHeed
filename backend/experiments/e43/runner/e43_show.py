"""Print E43_results.json compactly (read only)."""
import json
from pathlib import Path

r = json.loads((Path(__file__).resolve().parents[1] / "E43_results.json").read_text(encoding="utf-8"))
print("REPRO", r["reproduction"])
lk = r["leakage"]
print("LEAK problems", lk["problems"], "rows", lk["rows_checked"])
print("NaN test65", lk["nan_rows_test_65"], "| NaN train@Q4", lk["nan_rows_training_at_Q4_2026_origin"],
      "| NaN Q4 test", lk["nan_rows_Q4_2026_test"])
print("Q4 composite values", lk["q4_2026_values"])
for a, m in r["metrics"].items():
    print(f"{a:16s} acc {m['accuracy']:.3f} ({m['correct']}/{m['n']}) ci {[round(x, 3) for x in m['accuracy_ci95']]} "
          f"brier {m['brier']:.4f} ll {m['log_loss']:.3f} auc {m['auc']:.3f} bal {m['balanced_accuracy']:.3f} "
          f"hi {m['high_recall']:.3f} lo {m['low_recall']:.3f}")
for a, v in r["paired_vs_E36"].items():
    print(f"{a:16s} dB {v['brier_diff_arm_minus_E36']:+.4f} ci {[round(x, 4) for x in v['brier_diff_ci95']]} "
          f"mcn {v['mcnemar_p']:.3f} ({v['mcnemar']['arm_only_correct']}/{v['mcnemar']['ref_only_correct']}) "
          f"sf1 {v['signflip_p_one_sided_improvement']:.4f} holm {v['holm_signflip_p']:.4f} b/w {v['dates_better']}/{v['dates_worse']}")
for a, v in r["adoption"]["by_arm"].items():
    print("ADOPT", a, v)
print("passing", r["adoption"]["passing_in_preference_order"], "selected", r["adoption"]["selected"])
for a, v in r["mean_abs_shap_eval"].items():
    print("SHAP-EVAL", a, {k: round(x, 4) for k, x in v["mean_abs"].items()},
          {k: round(x, 1) for k, x in v["share_pct"].items()}, v["drivers_with_nonzero_shap"])
for a, v in r["q4_2026"].items():
    print("Q4", a, v["chosen"], {k: round(x, 4) for k, x in v["p"].items()},
          {k: round(x, 1) for k, x in v["shap_share_pct_CALABARZON"].items()}, round(v["shap_share_sum"], 6))
for a, p in r["selection_path"].items():
    print("PATH", a, list(p.values()))

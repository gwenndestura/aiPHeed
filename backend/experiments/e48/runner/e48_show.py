"""Print E48_results.json compactly (read only)."""
import json
from pathlib import Path

r = json.loads((Path(__file__).resolve().parents[1] / "E48_results.json").read_text(encoding="utf-8"))
print("paper tau", r["paper_tau"])
print("repro A0", r["reproduction_A0"])
print("dates", {k: (len(v), v[0], v[-1]) for k, v in r["test_quarters"].items()})
print("base rates", json.dumps(r["base_rates"]))
for k, m in r["metrics"].items():
    print(f"{k:22s} n {m['n']} H/L {m['HIGH']}/{m['LOW']} acc {m['accuracy']:.3f} ci {[round(x, 3) for x in m['accuracy_ci95']]} "
          f"bal {m['balanced_accuracy']:.3f} auc {m['auc'] if m['auc'] is None else round(m['auc'], 3)} brier {m['brier']:.4f} "
          f"hi {m['high_recall']:.3f} lo {m['low_recall']:.3f}")
for k, v in r["paired"].items():
    print(k, f"dB {v['brier_diff_arm_minus_ref']:+.4f} ci {[round(x, 4) for x in v['brier_diff_ci95']]} mcn {v['mcnemar']} "
          f"accdiff {v['accuracy_diff']:+.3f} b/w {v['dates_better']}/{v['dates_worse']}")
print("adoption", r["adoption"])
for k, v in r["q4_2026"].items():
    print("Q4", k, v["chosen"], {a: round(b, 4) for a, b in v["p"].items()}, {a: round(b, 1) for a, b in v["shares_CALABARZON_pct"].items()})
print("trig values Q4 (A1)", r["q4_2026"]["A1"]["trig_values"])
for k, v in r["mean_abs_shap"].items():
    print("MEAN", k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items() if a != "share_pct"},
          {a: round(b, 1) for a, b in v["share_pct"].items()})
for k, v in r["selection_path"].items():
    print("PATH", k, list(v.values()))

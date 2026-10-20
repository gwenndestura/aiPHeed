"""Print E51_results.json compactly (read only)."""
import json
from pathlib import Path

r = json.loads((Path(__file__).resolve().parents[1] / "E51_results.json").read_text(encoding="utf-8"))
print("run", r["run"], "adoption", r["adoption"])
for v, o in r["variants"].items():
    print(f"\n##### {v}  dates {len(o['test_quarters'])} ({o['test_quarters'][0]}..{o['test_quarters'][-1]}) rows {o['n_test_rows']}"
          f"  labels differ from P50 {o['pct_labels_differ_from_P50']:.3f}")
    br = o["base_rate"]
    print("  base rate all", round(br["all"], 3), "n", br["n"], "| 2024-26", round(br["2024_2026"], 3), "|", {y: round(x, 2) for y, x in br["per_year"].items()})
    print("  tau", {q: round(x, 2) for q, x in list(o["tau_by_target"].items())[-5:]})
    pe = o["persistence"]
    print(f"  persistence acc {pe['accuracy']:.3f} brier {pe['brier']:.4f} | climatology brier {o['climatology_brier']:.4f}")
    for a, x in o["arms"].items():
        m = x["metrics"]
        print(f"  [{a}] {x['q4_config']}")
        print(f"     acc {m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} auc {m['auc']:.3f} brier {m['brier']:.4f} ll {m['log_loss']:.3f} "
              f"max {m['max_p']:.3f} BSS {x['brier_skill_vs_climatology']:.3f} p>=.99 {x['n_test_p_ge_0.99']} p>=.95 {x['n_test_p_ge_0.95']}"
              f" | train@Q4 acc {x['train_Q4_origin']['accuracy']:.3f} | EV {x['shap_expected_value_logodds']:.2f} vs rate {x['train_label_rate_Q4_origin']:.3f}")
        if "adoption" in x:
            print("     criteria", {k: v_ for k, v_ in x["adoption"]["criteria"].items()})
        print("     index", {q: round(y["CALABARZON"], 3) for q, y in x["index"].items()})
        print("     observed", {q: round(y, 2) for q, y in x["observed_share_HIGH"].items()})
        print("     Q4", {k: round(y, 3) for k, y in x["index"]["2026-Q4"].items()})
        d = x["drivers_q4_2026"]["CALABARZON"]
        print("     drivers (a)", d["a"], "(b)", d["b"])

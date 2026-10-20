"""Print E50_results.json compactly (read only)."""
import json
from pathlib import Path

r = json.loads((Path(__file__).resolve().parents[1] / "E50_results.json").read_text(encoding="utf-8"))
print("run", r["run"], "rows", r["n_test_rows"], "consistency", r["consistency_max_abs_diff"])
print("adoption", r["adoption"])
print("R0 disagreements", r["R0_disagreements"])
for a, o in r["arms"].items():
    m, mr = o["metrics"], o["metrics_raw"]
    print(f"\n=== {a}  Q4 cfg {o['configs']['2026-Q4']}")
    print(f"  C2/final acc {m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} auc {m['auc']:.3f} brier {m['brier']:.4f} "
          f"ll {m['log_loss']:.3f} max {m['max_p']:.3f} | raw acc {mr['accuracy']:.3f} bal {mr['balanced_accuracy']:.3f} "
          f"auc {mr['auc']:.3f} brier {mr['brier']:.4f} ll {mr['log_loss']:.3f} max {mr['max_p']:.3f}")
    print(f"  p>=.95 {o['n_test_p_ge_0.95']} p<=.05 {o['n_test_p_le_0.05']} p>=.99 {o['n_test_p_ge_0.99']} | train@Q4 {o['train_Q4_origin']} "
          f"raw {o['train_Q4_origin_raw']} | train mean over origins {o['train_mean_over_origins']}")
    print(f"  EV {o['shap_expected_value_logodds']} (p {o['shap_expected_value_p']}) vs train label rate {o['train_label_rate_Q4_origin']:.3f}")
    print("  criteria", o["adoption"]["criteria"])
    print("  index", {q: round(x["CALABARZON"], 3) for q, x in o["index"].items()})
    print("  Q4", {k: (round(v, 4) if isinstance(v, float) else {kk: round(vv, 3) for kk, vv in v.items()}) for k, v in o["q4_2026"].items()})
    print("  fixed", o["R0_disagreements_fixed"], "\n  new", o["new_disagreements"], "n_wrong", o["n_wrong"])
    dr = o["drivers_q4_2026"]
    print("  drivers (a)", dr["CALABARZON"]["a"], "(b)", dr["CALABARZON"]["b"])
    for p in ("Cavite", "Laguna", "Quezon", "Rizal", "Batangas"):
        print(f"    {p:9s} (a) {list(dr[p]['a'].values())} (b) {list(dr[p]['b'].values())}  top {list(o['q4_shap_logodds'][p].items())[:4]}")
    print("  shrink", {q: (v and v['a']) for q, v in o["shrink_params"].items()})
    print("  configs", o["configs"])

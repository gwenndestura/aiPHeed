"""Print E45_results.json compactly (read only)."""
import json
from pathlib import Path

r = json.loads((Path(__file__).resolve().parents[1] / "E45_results.json").read_text(encoding="utf-8"))
print("adoption", r["adoption"])
for v, o in r["variants"].items():
    m, pe, ah = o["metrics"], o["B1_PERSISTENCE"], o["ALWAYS_HIGH"]
    print(f"\n=== {v}  dates {len(o['test_quarters'])} {o['test_quarters'][0]}..{o['test_quarters'][-1]}  op {o['operational']}  fallback {o['fallback_raw']}")
    print("  base rate", {k: (round(x, 3) if isinstance(x, float) else x) for k, x in o["base_rate"].items() if k != "per_year"},
          {y: round(x, 2) for y, x in o["base_rate"]["per_year"].items()}, "| differ from T0", round(o["pct_differ_from_T0"], 3),
          f"({o['labels_compared_with_T0']})")
    for name, x in (("C2", m), ("raw", o["metrics_raw"]), ("persistence", pe), ("always-HIGH", ah)):
        print(f"  {name:12s} acc {x['accuracy']:.3f} bal {x['balanced_accuracy'] if x['balanced_accuracy'] is None else round(x['balanced_accuracy'], 3)} "
              f"auc {x['auc'] if x['auc'] is None else round(x['auc'], 3)} brier {x['brier']:.4f} ll {x['log_loss']:.3f} max {x['max_p']:.3f}")
    print("  n p>=0.95", o["n_p_ge_0.95"], "| adoption", o["adoption"])
    print("  index", {q: round(x["CALABARZON"], 3) for q, x in o["index"].items()})
    print("  Q4", {k: round(x, 4) for k, x in o["index"]["2026-Q4"].items()})
    print("  drivers Q4", o["drivers_q4_2026"]["CALABARZON"])
    t = o["tau_by_target"]
    print("  tau", {q: (round(x, 2) if isinstance(x, float) else {a: round(b, 1) for a, b in x.items()}) for q, x in list(t.items())[-4:]})

"""Print E49_results.json compactly (read only)."""
import json
from pathlib import Path

r = json.loads((Path(__file__).resolve().parents[1] / "E49_results.json").read_text(encoding="utf-8"))
print("configs", r["configs"], "| fallback", r["fallback_to_raw"])
print("adoption", r["adoption"])
for k, m in r["metrics"].items():
    d = m.get("brier_diff_vs_C0")
    print(f"{k:12s} acc {m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} auc {m['auc']:.3f} brier {m['brier']:.4f} "
          f"ll {m['log_loss']:.3f} ece {m['ece_3bin']:.3f} max {m['max_p']:.4f} mean {m['mean_p']:.3f} >=.99 {m['n_p_ge_0.99']}"
          + (f" dB {d:+.4f} ci {[round(x, 4) for x in m['brier_diff_vs_C0_ci95']]}" if d is not None else ""))
    print("     rel", [(b["bin"], b["n"], None if b["mean_p"] is None else round(b["mean_p"], 2),
                        None if b["observed_HIGH"] is None else round(b["observed_HIGH"], 2)) for b in m["reliability_5bin"]])
    print("     mistakes", m["confident_mistakes"])
print("params C1", {q: v for q, v in list(r["calibration_params"]["C1"].items())[-4:]})
print("params C2", {q: v for q, v in list(r["calibration_params"]["C2"].items())})
print("params C4", {q: v for q, v in list(r["calibration_params"]["C4"].items())[-4:]})
for k in ("C0", "C1", "C2", "C3", "C4"):
    h = r["index_history"][k]
    print("IDX", k, {q: round(v["CALABARZON"], 3) for q, v in h.items()})
print("observed", {q: round(v, 2) for q, v in r["observed_share_HIGH"].items()})
for k, v in r["q4_2026"].items():
    print("Q4", k, {a: round(b, 4) for a, b in v.items()})
print("C3 path", r["selection_path"]["C3"])

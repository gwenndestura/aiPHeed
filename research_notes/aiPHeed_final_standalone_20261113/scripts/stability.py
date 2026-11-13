r"""PROTOCOL_SA Rule 7a (reproduction) and 7e (missing-input sensitivity) for FINAL. Run: python -I stability.py"""
import glob, hashlib, json
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
K = ["key", "survey", "lead", "seed"]
old = pd.concat([pd.read_csv(f) for f in glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112/parts_fwd/FINAL__*.csv"))])
new = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts_rerun/FINALR__*.csv"))])
base = new[new.variant == "none"]
m = old[K + ["p", "mu"]].merge(base[K + ["p", "mu"]], on=K, suffixes=("_stored", "_rerun"))
rep = {"fits_compared": int(m.groupby(["survey", "lead", "seed"]).ngroups), "rows": int(len(m)),
       "max_abs_diff_p": float((m.p_stored - m.p_rerun).abs().max()), "max_abs_diff_mu": float((m.mu_stored - m.mu_rerun).abs().max())}
rep["pass"] = rep["fits_compared"] == 45 and rep["max_abs_diff_p"] <= 1e-9
seal = RN / "aiPHeed_hcw_final_optimization_20261112/evidence/sealed_enns2022_candidates.json"
rec = (RN / "aiPHeed_hcw_final_optimization_20261112/evidence/sealed_enns2022_candidates.sha256").read_text().split()[0]
rep["seal_sha256_recorded"], rep["seal_sha256_now"] = rec, hashlib.sha256(seal.read_bytes()).hexdigest()
rep["seal_unchanged"] = rep["seal_sha256_recorded"] == rep["seal_sha256_now"]
# 7e: Lead 1, seed 168, same fitted model, one input group missing
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
L1 = new[(new.lead == 1) & (new.seed == 168)].merge(LAB[["key", "survey", "lead", "y_high"]], on=["key", "survey", "lead"])
def ba(g):
    h, y = g.p >= .5, g.y_high == 1
    return 0.5 * ((h & y).sum() / y.sum() + (~h & ~y).sum() / (~y).sum())
b0 = L1[L1.variant == "none"].set_index(["key", "survey"])
sens = []
for v, g in L1.groupby("variant"):
    gi = g.set_index(["key", "survey"])
    sens.append({"variant": v, "balanced_accuracy": round(float(ba(g)), 3), "delta_BA": round(float(ba(g) - ba(b0.reset_index())), 3),
                 "mean_abs_change_p": round(float((gi.p - b0.p).abs().mean()), 3), "class_flips": int(((gi.p >= .5) != (b0.p >= .5)).sum())})
S = pd.DataFrame(sens).sort_values("delta_BA")
S.to_csv(EV / "R7e_missing_group_sensitivity_L1_seed168.csv", index=False)
rep["sensitivity_severe_any"] = bool((S.delta_BA.abs() > 0.10).any())
json.dump(rep, open(EV / "R7a_reproduction.json", "w"), indent=1)
print(json.dumps(rep, indent=1)); print(S.to_string(index=False))

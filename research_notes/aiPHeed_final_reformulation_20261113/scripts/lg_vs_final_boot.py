r"""Paired bootstrap (rows within round, 2000 reps) of LG - FINAL on absolute-label Brier, absolute error (pp) and soft Brier. Stored predictions only."""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; K = ["key", "survey", "lead"]
lg = lambda p: np.log(p / (1 - p)); ex = lambda z: 100 / (1 + np.exp(-z))
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["y_high"]]; LAB = LAB[LAB.lead == 1]
GT = pd.read_csv(RN / "aiPHeed_final_reliability_20261113" / "evidence" / "GT_evaluation_labels.csv")[["key", "survey", "p", "se_p"]].rename(columns={"p": "pct"})
D = LAB.merge(GT, on=["key", "survey"]); f = D.pct / 100; D["q"] = norm.cdf(lg(f) / ((D.se_p / 100) / (f * (1 - f))))
rd = lambda pat: pd.concat([pd.read_csv(x, usecols=K + ["p", "mu"]) for x in glob.glob(pat)]).groupby(K, as_index=False)[["p", "mu"]].mean()
F = rd(str(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd" / "FINAL__ENNS20*__1__*.csv"))
L = rd(str(RN / "aiPHeed_final_model_optimization_20261113" / "parts" / "LG__*.csv"))
d = D.merge(F, on=K).merge(L, on=K, suffixes=("_F", "_L"))
diff = {"brier": (d.p_L - d.y_high) ** 2 - (d.p_F - d.y_high) ** 2, "abs_err_pp": (ex(d.mu_L) - d.pct).abs() - (ex(d.mu_F) - d.pct).abs(),
        "soft_brier": (d.p_L - d.q) ** 2 - (d.p_F - d.q) ** 2}
rng = np.random.default_rng(20261113); idx = [np.where(d.survey.values == s)[0] for s in sorted(d.survey.unique())]
out = {}
for scope, mask in (("POOLED", np.ones(len(d), bool)), ("ENNS2021", d.survey.values == "ENNS2021")):
    for k, v in diff.items():
        v = v.values
        if scope == "POOLED":
            bs = [v[np.concatenate([rng.choice(i, len(i)) for i in idx])].mean() for _ in range(2000)]
        else:
            i = np.where(mask)[0]; bs = [v[rng.choice(i, len(i))].mean() for _ in range(2000)]
        out[f"{scope}_{k}"] = {"LG_minus_FINAL": round(float(v[mask].mean()), 4), "ci95": [round(float(np.quantile(bs, .025)), 4), round(float(np.quantile(bs, .975)), 4)]}
json.dump(out, open(HERE / "evidence" / "LG_vs_FINAL_bootstrap.json", "w"), indent=1); print(json.dumps(out, indent=1))

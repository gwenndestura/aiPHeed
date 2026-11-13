r"""PROTOCOL_ATTR sensitivity (listed in the protocol): ATTR on the relative label with 2021-fold training-transition drops, and paired bootstrap of
ATTR vs the PROTOCOL_REL models (REL-HB, REL-P, REL-LGBM, FINAL-as-REL). Stored predictions only."""
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.metrics import roc_auc_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; K = ["key", "survey", "lead"]
A = pd.read_csv(HERE / "parts" / "ATTR_all.csv"); A["p"] = norm.cdf(A.z_hat / A.sd)
R = pd.read_csv(RN / "aiPHeed_final_reformulation_20261113" / "evidence" / "REL_province_rows_L1.csv")
d = R.merge(A[A.variant == "main"][K + ["p"]].rename(columns={"p": "ATTR"}), on=K)
out = {"drops_2021": {}}
for v in ("main", "drop_T1", "drop_T2", "drop_T3"):
    x = R[R.survey == "ENNS2021"].merge(A[A.variant == v][K + ["p"]], on=K); h = x.p >= .5; y = x.y_rel == 1
    out["drops_2021"][v] = {"TP/FP/FN/TN": f"{int((h & y).sum())}/{int((h & ~y).sum())}/{int((~h & y).sum())}/{int((~h & ~y).sum())}",
                           "brier": round(float(((x.p - x.y_rel) ** 2).mean()), 4), "auc": round(float(roc_auc_score(x.y_rel, x.p)), 3)}
rng = np.random.default_rng(20261113); idx = [np.where(d.survey.values == s)[0] for s in ("ENNS2018", "ENNS2019", "ENNS2021")]
out["bootstrap_pooled_brier_relative"] = {}
for b in ("REL_HB", "REL_P", "REL_LGBM", "FINAL_as_REL"):
    v = ((d.ATTR - d.y_rel) ** 2 - (d[b] - d.y_rel) ** 2).values
    bs = [v[np.concatenate([rng.choice(i, len(i)) for i in idx])].mean() for _ in range(2000)]
    out["bootstrap_pooled_brier_relative"][f"ATTR - {b}"] = {"dBrier": round(float(v.mean()), 4), "ci95": [round(float(np.quantile(bs, .025)), 4), round(float(np.quantile(bs, .975)), 4)]}
json.dump(out, open(HERE / "evidence" / "ATTR_relative_sensitivity.json", "w"), indent=1); print(json.dumps(out, indent=1))

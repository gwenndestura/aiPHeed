r"""What-if bounds on the LOCKED forecasts (diagnostic only; nothing is selected or refitted). Run: python -I whatif.py"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
EV = Path(__file__).resolve().parents[1] / "evidence"
RN = Path(__file__).resolve().parents[2]
X = pd.read_csv(RN / "aiPHeed_final_cw_20261112/evidence/cw_rows_all_leads.csv")
rng = np.random.default_rng(7)
FIVE = {"Lanao del Norte", "Misamis Oriental", "Masbate", "Occidental Mindoro", "Agusan Del Sur"}
FA = {"Quirino", "Sorsogon", "Southern Leyte", "North Cotabato", "Sarangani"}      # confident false alarms / both-wrong LOW

def ci(p):
    d = ((p - X.q_true) ** 2 - (X.FIX - X.q_true) ** 2).values
    cl = (X.province + X.survey).values; u = np.unique(cl); idx = {c: np.flatnonzero(cl == c) for c in u}
    bs = [d[np.concatenate([idx[c] for c in rng.choice(u, len(u))])].mean() for _ in range(6000)]
    return [round(float(d.mean()), 4), round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]

out = {"FINAL as scored": ci(X.FINAL)}
m5 = X.province.isin(FIVE)
out["five misses at H_cw's probability (no other change)"] = ci(np.where(m5, X.FIX, X.FINAL))
out["five misses correctly called at 0.60 (no other change)"] = ci(np.where(m5, 0.60, X.FINAL))
mfa = X.province.isin(FA) & (X.y_high == 0)
out["five misses at 0.60 AND both-wrong LOW provinces at 0.45"] = ci(np.where(m5, 0.60, np.where(mfa, 0.45, X.FINAL)))
json.dump(out, open(EV / "RC3_whatif_bounds.json", "w"), indent=1)
print(json.dumps(out, indent=1))

r"""Outcome-free diagnostics for the root-cause report (no test outcome read):
(1) spread and confidence of FINAL's Lead 1 forecasts by fold (implied sd = mu / Phi^-1(p));
(2) covariate shift: standardised mean difference of each input, test vs training rows, per fold (Lead 1);
(3) anchor-level support: test anchors outside the training anchor range; training HIGH share (class balance).
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python diag_shift.py"""
import glob, json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
sys.path.insert(0, str(RN / "aiPHeed_final_standalone_20261113" / "scripts"))
from rerun_final import group_of     # noqa: E402
from app.hcw import engine as H      # noqa: E402
CACHE = RN / "aiPHeed_objective_completion_20261111" / "cache"
S = pd.concat([pd.read_csv(f) for f in glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112/parts_fwd/FINAL__*__1__*.csv"))])
allc = sorted({c for v in H.feature_sets().values() for c in v})
out = {}
for sv in ("ENNS2018", "ENNS2019", "ENNS2021"):
    o = pickle.load(open(CACHE / f"{sv}_1.pkl", "rb"))
    tr, te = o["tr"], o["te"]
    g = S[S.survey == sv]
    z = norm.ppf(np.clip(g.p, 1e-6, 1 - 1e-6))
    ok = np.abs(z) > 0.2
    smd = {}
    for c in allc:
        if c in tr and c in te and tr[c].notna().sum() > 5 and te[c].notna().sum() > 2:
            sd = tr[c].std()
            if sd and sd > 0:
                smd[c] = float((te[c].mean() - tr[c].mean()) / sd)
    sm = pd.Series(smd)
    out[sv] = {"test_gap": sorted(map(int, te.gap_q.unique())), "train_gaps": sorted(map(int, tr.gap_q.unique())),
               "train_high_share": round(float((tr.y_true >= 0).mean()), 3),
               "implied_sd_median": round(float(np.median(g.mu[ok] / z[ok])), 3),
               "share_forecasts_beyond_0.2_or_0.8": round(float(((g.p < .2) | (g.p > .8)).mean()), 3),
               "inputs_with_|SMD|>1": sm[sm.abs() > 1].round(2).to_dict(),
               "share_inputs_|SMD|>0.5": round(float((sm.abs() > .5).mean()), 3),
               "mean_|SMD|_by_group": sm.abs().groupby([group_of(c) for c in sm.index]).mean().round(2).to_dict(),
               "test_anchor_range_pct": [round(float(100 / (1 + np.exp(-te.y_anchor.min()))), 1), round(float(100 / (1 + np.exp(-te.y_anchor.max()))), 1)],
               "train_anchor_range_pct": [round(float(100 / (1 + np.exp(-tr.y_anchor.min()))), 1), round(float(100 / (1 + np.exp(-tr.y_anchor.max()))), 1)]}
json.dump(out, open(HERE / "evidence" / "D5_spread_shift_balance_outcome_free.json", "w"), indent=1)
print(json.dumps(out, indent=1))

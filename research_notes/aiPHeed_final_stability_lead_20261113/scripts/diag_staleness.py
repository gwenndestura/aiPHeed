r"""Training-only / outcome-free test of the elapsed-time variable used by RATE.
gap_q = quarters from the province's OWN anchor survey to the target (what RATE multiplies by).
stale = quarters from the LATEST RELEASED round at the origin to the target (the anchors' national level is refreshed to it).
For every fold-lead: how often they differ in training and test rows; and in TRAINING rows where they differ, whether the anchor
residual e = y - anchor scales with gap_q or with stale. Test outcomes are never read. Run: python -I diag_staleness.py"""
import json, pickle
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parents[1]
CACHE = HERE.parent / "aiPHeed_objective_completion_20261111" / "cache"
RQ = {"NNS2013": 8054, "FNRI2015": 8062, "ENNS2018": 8074, "ENNS2019": 8078, "ENNS2021": 8086}
LAG = 6


def stale(i, T):
    rel = [q for q in RQ.values() if q + LAG <= i]
    return T - max(rel)


rows, ev = [], {}
for sv, n in (("ENNS2018", 6), ("ENNS2019", 8), ("ENNS2021", 8)):
    for L in range(1, n + 1):
        o = pickle.load(open(CACHE / f"{sv}_{L}.pkl", "rb"))
        tr, te, AN = o["tr"].reset_index(drop=True), o["te"].reset_index(drop=True), o["AN"]
        tr["s"] = [stale(i, T) for i, T in zip(tr["i"], tr["T"])]
        te["s"] = [stale(i, T) for i, T in zip(te["i"], te["T"])]
        rows.append({"fold": sv, "lead": L, "origin": int(o["origin"]), "train_rows": len(tr), "train_rows_s_ne_g": int((tr.s != tr.gap_q).sum()),
                     "train_g": sorted(map(int, tr.gap_q.unique())), "train_s": sorted(map(int, tr.s.unique())),
                     "test_g": sorted(map(int, te.gap_q.unique())), "test_s": sorted(map(int, te.s.unique()))})
        if L == 1 and (tr.s != tr.gap_q).any():
            for a in AN:
                e = tr["y_true"].values - np.asarray(AN[a][0])
                d = tr.assign(e=e).drop_duplicates(["key", "survey", "ref_anchor"])
                grp = d.groupby(["gap_q", "s"]).agg(n=("e", "size"), mean_e=("e", "mean"), mean_abs_e=("e", lambda v: float(np.mean(np.abs(v))))).reset_index()
                grp["e_per_q_by_gap"], grp["e_per_q_by_stale"] = grp.mean_e / grp.gap_q, grp.mean_e / grp.s
                # which elapsed-time variable makes the per-quarter residual more homogeneous across groups (weighted CV)?
                w = grp.n / grp.n.sum()
                cv = lambda x: float(np.sqrt(np.sum(w * (x - np.sum(w * x)) ** 2)) / max(1e-9, abs(np.sum(w * x))))
                ev[f"{sv}_L{L}_anchor_{a}"] = {"groups": grp.round(4).to_dict("records"), "cv_per_quarter_rate_gap": round(cv(grp.e_per_q_by_gap), 3),
                                               "cv_per_quarter_rate_stale": round(cv(grp.e_per_q_by_stale), 3),
                                               "corr_abs_e_with_gap": round(float(np.corrcoef(np.abs(d.e), d.gap_q)[0, 1]), 3),
                                               "corr_abs_e_with_stale": round(float(np.corrcoef(np.abs(d.e), d.s)[0, 1]), 3)}
R = pd.DataFrame(rows)
R.to_csv(HERE / "evidence" / "D4_gap_vs_staleness_by_fold_lead.csv", index=False)
json.dump(ev, open(HERE / "evidence" / "D4_residual_scaling_training_only.json", "w"), indent=1)
print(R.to_string(index=False)); print(json.dumps(ev, indent=1)[:4000])

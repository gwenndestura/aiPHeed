r"""Statistical limit of per-round acceptance with the real round sizes (2018 8 HIGH/14 LOW, 2019 13/12, 2021 4/21).
Monte Carlo: a model whose TRUE per-province hit rates are (TPR, FPR); counts are binomial. Uses no new model output.
Operating points: FINAL pooled L1 (20/5/5/42) with Beta posterior uncertainty, and better hypothetical models. Also Clopper-Pearson CIs.
Only the count-based targets (recall, precision, F1, BA, accuracy) are simulated; Brier/ROC-AUC/PR-AUC passed for every arm in every round."""
import json
from pathlib import Path
import numpy as np
from scipy.stats import beta
EV = Path(__file__).resolve().parents[1] / "evidence"
ROUNDS = {"ENNS2018": (8, 14), "ENNS2019": (13, 12), "ENNS2021": (4, 21)}
rng = np.random.default_rng(20261113); N = 200_000


def passes(tp, fp, P, Nn):
    fn, tn = P - tp, Nn - fp
    rec = tp / P; prec = np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1), 0.0)
    f1 = np.where(tp > 0, 2 * prec * rec / np.maximum(prec + rec, 1e-12), 0.0)
    ba = (rec + tn / Nn) / 2; acc = (tp + tn) / (P + Nn)
    return (rec >= .7) & (prec >= .7) & (f1 >= .7) & (ba >= .7) & (acc >= .75)


def sim(tpr, fpr):
    out, joint = {}, np.ones(N, bool)
    for r, (P, Nn) in ROUNDS.items():
        t = np.broadcast_to(tpr, (N,)); f = np.broadcast_to(fpr, (N,))
        ok = passes(rng.binomial(P, t), rng.binomial(Nn, f), P, Nn)
        out[r] = round(float(ok.mean()), 3); joint &= ok
    out["all_three"] = round(float(joint.mean()), 3)
    return out


res = {"FINAL_pooled_point (TPR .80, FPR .106)": sim(20 / 25, 5 / 47),
       "FINAL_pooled_posterior (Beta(21,6), Beta(6,43))": sim(rng.beta(21, 6, N), rng.beta(6, 43, N)),
       "hypothetical TPR .90 FPR .05": sim(.90, .05), "hypothetical TPR .95 FPR .03": sim(.95, .03)}
cp = lambda k, n: [round(float(beta.ppf(.025, k, n - k + 1)) if k else 0.0, 3), round(float(beta.ppf(.975, k + 1, n - k)) if k < n else 1.0, 3)]
res["clopper_pearson_95"] = {"recall 3/4": cp(3, 4), "recall 1/4": cp(1, 4), "recall 2/4": cp(2, 4), "pooled recall 20/25": cp(20, 25)}
res["min_2021_requirement"] = "TP>=3 of 4 and FP<=1 of 21 (precision>=.70): 3 of the 4 HIGH must rank in the top 4 or 5 of 25"
json.dump(res, open(EV / "OPT_statistical_limit.json", "w"), indent=1); print(json.dumps(res, indent=1))

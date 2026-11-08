"""
E151 release gates, province-sentence value and quarterly movement, computed from the outputs.

    python -m app.e151.gates -> data/e151/out/gates.json
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import model as M
from app.e151 import OUT
from app.e151 import prov as Pv

warnings.filterwarnings("ignore")


def _tg(survey):
    """Upgrade 1: the required model with and without the province-sentence inputs, same rows."""
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - 1
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    from app.e150 import evaluate as Ev
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = Pv.add_inputs(S, M.rows_for(S, tg, [1], Pv.ORIGIN[survey]))
    tr = Pv.add_inputs(S, P.tr)
    base, _ = P.hier.predict(te, te["T"].values)
    o = te[["key", "survey", "lead"]].copy()
    for nm, cols in (("with_tg", Pv.GNT_COLS), ("without_tg", [c for c in Pv.GNT_COLS if c not in Pv.N_T])):
        m = Pv.Res2(cols).fit(tr)
        mu = base + m.predict(te)
        sd, _, _ = m.scale(te["gap_q"].values)
        o[nm] = norm.cdf(mu / sd)
    return o


def main():
    r = json.loads((OUT / "prov_results.json").read_text())
    s = json.loads((OUT / "sws_results.json").read_text())
    F = pd.read_csv(OUT / "prov_oof.csv")
    x = F[F["lead"] == 1].reset_index(drop=True)
    rng = np.random.default_rng(151)
    pairs = json.loads((OUT / "issue" / "pairs.json").read_text())
    n_sep = sum(v["separated_90"] for v in pairs.values())
    def gates(g, label):
        y = g["y_high"].values
        m = Pv.met(g, "GNT")
        major = max(y.mean(), 1 - y.mean())
        d = E7.diff_ci(g, "GNT", "PERS", "q_true", rng, n=2000)
        sc = Pv.scale_test(g, "GNT", rng, n=2000)
        return {"scope": label, "n": int(len(g)), "n_high": int(y.sum()),
                "R1_accuracy_ge_75": {"value": m["accuracy"], "pass": m["accuracy"] >= .75},
                "R2_auc_ge_70": {"value": m["auc"], "pass": m["auc"] >= .70},
                "R3_both_recalls_ge_50": {"high": m["recall"], "low": m["low_recall"], "pass": m["recall"] >= .5 and m["low_recall"] >= .5},
                "R4_brier_below_persistence": {"diff": d["diff"], "ci95": d["ci95"], "pass": d["ci95"][1] < 0},
                "R5_above_majority_rule": {"value": m["accuracy"], "majority": float(major), "pass": m["accuracy"] > major},
                "R6_coverage_80_98": {"value": m["coverage_90"], "pass": .80 <= m["coverage_90"] <= .98},
                "R7_slope_interval_includes_1": {"ci95": sc["slope_ci95"], "pass": sc["slope_ci95"][0] <= 1 <= sc["slope_ci95"][1]}, "mean_error_ci95_logit": sc["mean_error_ci95"], "may_be_called_prevalence": sc["may_be_called_prevalence"]}
    res = {"target": r["target"], "pool": gates(x, "pool of 2018, 2019, 2021"), "round_2021": gates(x[x["survey"] == "ENNS2021"].reset_index(drop=True), "2021 round"),
           "R8_province_pair_separated": {"pairs_separated": int(n_sep), "of": len(pairs), "pass": n_sep >= 1}, "R9_news_passes_q1": {"pass": bool(s["news_pass_q1"]), "gnt_minus_gov": s["tests"]["confirmation_L1"]["GNT-GOV"], "share_placebo_as_good": s["placebo_L1"]["share_placebo_better_or_equal"]}}
    allg = [v for k, v in res["pool"].items() if k[0] == "R"] + [v for k, v in res["round_2021"].items() if k[0] == "R"] + [res["R8_province_pair_separated"], res["R9_news_passes_q1"]]
    res["all_pass"] = bool(all(g["pass"] for g in allg))
    # province-sentence value
    T = pd.concat(Parallel(n_jobs=3)(delayed(_tg)(k) for k in ("ENNS2018", "ENNS2019", "ENNS2021")), ignore_index=True).merge(x[["key", "survey", "q_true", "region", "y_high"]], on=["key", "survey"])
    res["province_sentences"] = {"diff_brier_with_minus_without": E7.diff_ci(T, "with_tg", "without_tg", "q_true", rng, n=2000), "accuracy_with": float(((T["with_tg"] >= .5) == (T["y_high"] == 1)).mean()), "accuracy_without": float(((T["without_tg"] >= .5) == (T["y_high"] == 1)).mean()), "note": "All provinces; most have few sentences. Exploratory."}
    # quarterly movement: the same target forecast from different issue quarters
    pct = lambda v: 100 / (1 + np.exp(-v))
    z = F.sort_values(["key", "survey", "lead"]).assign(s=lambda d: pct(d["mu_GNT"]), a=lambda d: pct(d["mu_ANCHOR"]))
    d = z.groupby(["key", "survey"])["s"].diff().abs().dropna()
    res["quarterly_movement"] = {"mean_abs_change_points_between_consecutive_issue_quarters": float(d.mean()), "median": float(d.median()), "share_of_steps_over_1_point": float((d > 1).mean()), "same_target_range_mean": float(z.groupby(["key", "survey"])["s"].agg(lambda v: v.max() - v.min()).mean()), "note": "Movement is the change in the forecast of one target as the issue date moves; it is not a measured change."}
    (OUT / "gates.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, indent=0, default=float))


if __name__ == "__main__":
    main()

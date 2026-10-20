"""E49: calibrate the E48-A1 probabilities (lead 1, current trailing-median labels). Experiment only.

    python -B backend/experiments/e49/runner/e49_run.py  -> backend/experiments/e49/E49_results.json

Arms (E36 walk-forward, nested rule, seed 36; E48-A1 features = E36's 13 inputs + 5 trigger proportions):
  C0  raw E48-A1 (pool E48-T5: COMPACT_T5/COMB_T5 x G1/G4/G3/G2)
  C1  Platt scaling of C0: logistic regression on logit(p), fitted on the out-of-fold predictions of earlier dates
  C2  shrinkage of C0: p' = a*p + (1-a)*base_rate, a in {0, .05, ..., 1} chosen by lowest Brier on earlier dates;
      base_rate = Laplace HIGH rate of the training labels at that date's origin (known at the origin)
  C3  stronger LightGBM regularisation (pool E49-REG: same feature sets, settings R1/R2 below), no post-calibration
  C4  C3 + Platt (as C1)
"Earlier dates" for an outer date t = development dates whose TARGET was posted before O(t) (E36's eligibility
rule), so no outcome after the origin is used. Fewer than MIN_DATES such dates, or a single class -> raw p.

ADOPTION (fixed before results): lowest Brier among arms with accuracy >= C0 - 0.01 and log loss <= C0 log loss;
if none beats C0 on Brier, keep C0.
"""
from __future__ import annotations

import json
import math
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E49 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E49.parent / "e48" / "runner"))
import e48_lib as L  # noqa: E402
import e36_evaluate as E  # noqa: E402

L6, C, np, pd, M = L.L6, L.C, L.np, L.pd, E.M
L6.guard32.EXP = E49
NAMES = {p: C.NAMES[p] for p in L.PROVS}
MIN_DATES = 3
GRID_A = [round(x, 2) for x in np.arange(0, 1.0001, 0.05)]
# stronger regularisation: more rows per leaf, fewer and shallower trees, heavier L2
L6.GRID["R1"] = dict(num_leaves=2, max_depth=1, min_data_in_leaf=15, n_estimators=60, learning_rate=0.05,
                     reg_lambda=5.0, colsample_bytree=1.0)
L6.GRID["R2"] = dict(num_leaves=3, max_depth=2, min_data_in_leaf=20, n_estimators=60, learning_rate=0.05,
                     reg_lambda=10.0, colsample_bytree=0.8)


def register():
    L.register_pools()
    L6.POOLS["E49-REG"] = ([("COMPACT_T5", g) for g in ("R1", "R2")] + [("COMB_T5", g) for g in ("R1", "R2")],
                           ("COMB_T5", "R1"))


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def platt_fit(p, y):
    from sklearn.linear_model import LogisticRegression

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = LogisticRegression(C=1e6, max_iter=1000).fit(logit(p).reshape(-1, 1), y)
    return float(m.coef_[0][0]), float(m.intercept_[0])


def platt_apply(p, ab):
    a, b = ab
    return 1 / (1 + np.exp(-(a * logit(p) + b)))


def calibrated(raw: dict, labels: dict, base: dict, prior_of: dict, how: str):
    """raw[t] = {prov: p}; returns {t: {prov: p'}} and the dates that fell back to raw p."""
    out, fallback, params = {}, [], {}
    for t in raw:
        prior = prior_of[t]
        if len(prior) < MIN_DATES:
            out[t], params[t] = dict(raw[t]), None
            fallback.append(t)
            continue
        p = np.array([raw[tj][c] for tj in prior for c in L.PROVS])
        y = np.array([labels[tj][c] for tj in prior for c in L.PROVS])
        if how == "platt":
            if len(set(y)) < 2:
                out[t], params[t] = dict(raw[t]), None
                fallback.append(t)
                continue
            ab = platt_fit(p, y)
            out[t] = {c: float(platt_apply([raw[t][c]], ab)[0]) for c in L.PROVS}
            params[t] = {"slope": ab[0], "intercept": ab[1]}
        else:                                                  # shrink toward the base rate
            br = np.array([base[tj] for tj in prior for c in L.PROVS])
            a = min(GRID_A, key=lambda a: (float(np.mean((a * p + (1 - a) * br - y) ** 2)), -a))
            out[t] = {c: a * raw[t][c] + (1 - a) * base[t] for c in L.PROVS}
            params[t] = {"a": a, "base_rate": base[t]}
    return out, fallback, params


def frame(pr: dict, labels: dict, arm: str) -> pd.DataFrame:
    return pd.DataFrame([{"t": C.qs(t), "target_quarter": C.qs(t + 1), "province_code": c, "arm": arm,
                          "p": pr[t][c], "y": labels[t][c]} for t in pr for c in L.PROVS])


def reliability(g, edges=(0, .2, .4, .6, .8, 1.0001)):
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = g[(g["p"] >= lo) & (g["p"] < hi)]
        rows.append({"bin": f"{lo:.1f}-{min(hi, 1):.1f}", "n": int(len(s)),
                     "mean_p": float(s["p"].mean()) if len(s) else None,
                     "observed_HIGH": float(s["y"].mean()) if len(s) else None})
    return rows


def summary(g):
    m = M.point_metrics(g["y"], g["p"])
    b = M.bootstrap(g)
    wrong_hi = g[(g["p"] >= 0.9) & (g["y"] == 0)]
    wrong_lo = g[(g["p"] <= 0.1) & (g["y"] == 1)]
    return {"accuracy": m["accuracy"], "accuracy_ci95": b["accuracy_ci95"], "balanced_accuracy": m["balanced_accuracy"],
            "auc": m["roc_auc"], "brier": m["brier"], "log_loss": m["log_loss"], "ece_3bin": m["ece_3bin"],
            "max_p": float(g["p"].max()), "mean_p": float(g["p"].mean()), "n_p_ge_0.99": int((g["p"] >= 0.99).sum()),
            "reliability_5bin": reliability(g),
            "confident_mistakes": {
                "p>=0.9_but_LOW": [(r.target_quarter, NAMES[r.province_code], round(r.p, 3)) for r in wrong_hi.itertuples()],
                "p<=0.1_but_HIGH": [(r.target_quarter, NAMES[r.province_code], round(r.p, 3)) for r in wrong_lo.itertuples()]}}


def main():
    register()
    d = L.Data(paper=False)
    Pr, info = L6.walk_forward(d)
    dates = [C.qk(q) - 1 for q in info["dates"]]
    T = L6.OPERATIONAL_T
    labels = {t: {c: int(d.label(c, t + 1, t)) for c in L.PROVS} for t in dates}
    base = {}
    for t in dates + [T]:
        tr = d.train(t)
        base[t] = float((tr["y"].sum() + 1) / (len(tr) + 2))
    prior_of = {t: L6.eligible_prior_dates(d, t, dates) for t in dates + [T]}

    def arm_preds(pool):
        out = {}
        for t in dates:
            s = Pr[(Pr["arm"] == pool) & (Pr["t"] == C.qs(t))].set_index("province_code")["p"]
            out[t] = {c: float(s[c]) for c in L.PROVS}
        (fs, g), _ = L6.operational_choice(d, Pr, pool)
        op = L6.lgbm_predict(d.train(T), d.test(T), L6.FEATURE_SETS[fs], g)
        return out, {c: float(op[c]) for c in L.PROVS}, L6.cfg_name(fs, g)

    raw0, op0, cfg0 = arm_preds("E48-T5")
    raw3, op3, cfg3 = arm_preds("E49-REG")
    labels_all = {**labels, T: {c: 0 for c in L.PROVS}}        # T's labels are never used (it is never a prior date)
    arms, fallbacks, params, q4 = {}, {}, {}, {}
    for name, raw, op, how in (("C0", raw0, op0, None), ("C1", raw0, op0, "platt"), ("C2", raw0, op0, "shrink"),
                               ("C3", raw3, op3, None), ("C4", raw3, op3, "platt")):
        allraw = {**raw, T: op}
        if how is None:
            cal, fb, pa = allraw, [], {}
        else:
            cal, fb, pa = calibrated(allraw, labels_all, base, prior_of, how)
        arms[name] = {t: cal[t] for t in dates}
        q4[name] = cal[T]
        fallbacks[name] = [C.qs(t + 1) for t in fb if t != T]
        params[name] = {C.qs(t + 1): v for t, v in pa.items()}
    frames = {k: frame(v, labels, k) for k, v in arms.items()}
    pers = Pr[Pr["arm"] == "B1_PERSISTENCE"][["t", "target_quarter", "province_code", "p", "y"]].assign(arm="persistence")

    res = {"lead": 1, "test_quarters": info["dates"], "configs": {"C0_operational": cfg0, "C3_operational": cfg3},
           "selection_path": {"C0": {q: v["chosen"] for q, v in info["selections"]["E48-T5"].items()},
                              "C3": {q: v["chosen"] for q, v in info["selections"]["E49-REG"].items()}},
           "fallback_to_raw": fallbacks, "calibration_params": params,
           "metrics": {k: summary(v) for k, v in frames.items()} | {"persistence": summary(pers)}}
    c0 = res["metrics"]["C0"]
    cand = [k for k in ("C1", "C2", "C3", "C4") if res["metrics"][k]["accuracy"] >= c0["accuracy"] - 0.01 - 1e-12
            and res["metrics"][k]["log_loss"] <= c0["log_loss"] + 1e-12]
    best = min(cand, key=lambda k: res["metrics"][k]["brier"]) if cand else None
    chosen = best if best and res["metrics"][best]["brier"] < c0["brier"] else "C0"
    res["adoption"] = {"eligible": cand, "lowest_brier_eligible": best, "chosen": chosen}
    for k, v in frames.items():                                # paired Brier vs C0
        dlt = (M.per_date_losses(v)["bri"] - M.per_date_losses(frames["C0"])["bri"]).to_numpy()
        rng = np.random.default_rng(M.SEED)
        bs = [dlt[rng.choice(len(dlt), len(dlt), replace=True)].mean() for _ in range(M.B)]
        res["metrics"][k]["brier_diff_vs_C0"] = float(dlt.mean())
        res["metrics"][k]["brier_diff_vs_C0_ci95"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    show = sorted({"C0", chosen})
    res["index_history"] = {k: {**{C.qs(t + 1): {"CALABARZON": float(np.mean(list(arms[k][t].values()))),
                                                 **{NAMES[c]: arms[k][t][c] for c in L.PROVS}} for t in dates},
                                "2026-Q4": {"CALABARZON": float(np.mean(list(q4[k].values()))),
                                            **{NAMES[c]: q4[k][c] for c in L.PROVS}}}
                            for k in ("C0", "C1", "C2", "C3", "C4")}
    res["index_history_shown"] = show
    res["observed_share_HIGH"] = {C.qs(t + 1): float(np.mean(list(labels[t].values()))) for t in dates}
    res["q4_2026"] = {k: {"CALABARZON": float(np.mean(list(v.values()))), **{NAMES[c]: v[c] for c in L.PROVS}}
                      for k, v in q4.items()}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E49 / "runs" / stamp
    run.mkdir(parents=True)
    pd.concat(list(frames.values()) + [pers]).to_csv(run / "predictions.csv", index=False, float_format="%.10g")
    res["run"] = stamp
    C.write_json(E49 / "E49_results.json", C.clean(res))
    print("RUN", stamp, "chosen", chosen, "eligible", cand)


if __name__ == "__main__":
    main()

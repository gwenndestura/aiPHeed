"""E43 run (lead 1).  python -B backend/experiments/e43/runner/e43_run.py
-> backend/experiments/e43/{E43_results.json, runs/<stamp>/predictions.csv}

ADOPTION RULE (given in the task; written here before any E43 result was seen)
  Pass (non-inferior) iff ALL: (a) paired Brier-difference 95% CI includes 0 or lies below 0; (b) accuracy >= E36 - 0.01;
  (c) no leakage problem. "IMPROVES on E36" only if also Holm-adjusted (7 arms) one-sided sign-flip p < 0.05.
  Among passing arms prefer (1) more drivers with non-zero SHAP, (2) lower Brier, (3) fewer features.
  Arms containing OFW are PROVISIONAL.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e43_lib as L  # noqa: E402
import e36_evaluate as E6  # noqa: E402

L6, C, np, pd, M = L.L6, L.C, L.np, L.pd, E6.M
L6.guard32.EXP = L.E43
E36_RUN = L.ROOT / "aipheed-backend-aligned" / "experiments" / "E36_LightGBM_One_Quarter_Ahead" / "runs" / "20261015T023921Z"
REF = "E36-LGBM"
ARMS = ["E43-all4", "E43-noOFW", "E43-all4-fixed", "E43-CLIM", "E43-FISH", "E43-EMP", "E43-OFW"]
N_NEW = {"E43-all4": 4, "E43-noOFW": 3, "E43-all4-fixed": 4, "E43-CLIM": 1, "E43-FISH": 1, "E43-EMP": 1, "E43-OFW": 1}
BASELINES = E6.BASELINES
NAMES = {p: C.NAMES[p] for p in L.PROVS}
DRIVERS5 = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]


def metrics(g):
    m = M.point_metrics(g["y"], g["p"])
    b = M.bootstrap(g)
    return {"n": m["n"], "correct": int(round(m["accuracy"] * m["n"])), "accuracy": m["accuracy"],
            "accuracy_ci95": b["accuracy_ci95"], "brier": m["brier"], "log_loss": m["log_loss"], "auc": m["roc_auc"],
            "balanced_accuracy": m["balanced_accuracy"], "high_recall": m["recall"], "low_recall": m["specificity"]}


def paired(Pr, arm):
    a = Pr[Pr["arm"] == arm].sort_values(["t", "province_code"])
    r = Pr[Pr["arm"] == REF].sort_values(["t", "province_code"])
    j = a.merge(r, on=["t", "province_code"], suffixes=("_a", "_r"))
    ok_a = (j["p_a"] >= .5).astype(int).to_numpy() == j["y_a"].to_numpy()
    ok_r = (j["p_r"] >= .5).astype(int).to_numpy() == j["y_r"].to_numpy()
    d = (M.per_date_losses(a)["bri"] - M.per_date_losses(r)["bri"]).to_numpy()        # < 0: arm better
    rng = np.random.default_rng(M.SEED)
    boots = [d[rng.choice(len(d), len(d), replace=True)].mean() for _ in range(M.B)]
    return {"brier_diff_arm_minus_E36": float(d.mean()),
            "brier_diff_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "mcnemar_p": E6.mcnemar_exact(ok_a, ok_r)["p_two_sided"], "mcnemar": E6.mcnemar_exact(ok_a, ok_r),
            "signflip_p_one_sided_improvement": M.signflip_p(-d), "accuracy_diff": float(ok_a.mean() - ok_r.mean()),
            "dates_better": int((d < 0).sum()), "dates_worse": int((d > 0).sum())}


def shap_frame(d, t, fs, g):
    feats = L6.FEATURE_SETS[fs]
    model = L6.fit_lgbm(d.train(t), feats, g)
    te = d.test(t)
    if model is None:
        return None, te, feats
    return L6.shap_contributions(model, te[feats]).drop(columns="expected_value"), te, feats


def group_abs(c):
    grouped = {f for fs in L.GROUPS.values() for f in fs}
    out = {g: (c[[f for f in fs if f in c.columns]].abs().sum(axis=1) if any(f in c.columns for f in fs)
               else pd.Series(0.0, index=c.index)) for g, fs in L.GROUPS.items()}
    out["other"] = c[[f for f in c.columns if f not in grouped]].abs().sum(axis=1)
    return pd.DataFrame(out, index=c.index)


def main():
    L.install_monotone()
    L.register_pools()
    d = L.Data()
    Pr, info = L6.walk_forward(d)
    dates = info["dates"]
    origins = [L.qk(q) - 1 for q in dates]

    # E36 reproduction
    st = pd.read_csv(E36_RUN / "predictions.csv", dtype={"province_code": str})
    j = Pr.merge(st[["arm", "target_quarter", "province_code", "p", "y"]], on=["arm", "target_quarter", "province_code"],
                 suffixes=("", "_stored"))
    e36 = j[j["arm"] == REF]
    stored = json.loads((E36_RUN / "results.json").read_text(encoding="utf-8"))
    rep = {"arms_compared": int(j["arm"].nunique()), "rows_compared": int(len(j)),
           "max_abs_p_diff_all_arms": float((j["p"] - j["p_stored"]).abs().max()),
           "E36_max_abs_p_diff": float((e36["p"] - e36["p_stored"]).abs().max()),
           "labels_equal": bool((j["y"] == j["y_stored"]).all()),
           "E36_selection_path_equal": {q: v["chosen"] for q, v in info["selections"][REF].items()} ==
                                       {q: v["chosen"] for q, v in stored["selections"][REF].items()}}

    # Leakage + NaN counts (every training and test row of every origin, and the operational origin)
    problems, rows, nan_test, nan_train = [], 0, {c: 0 for c in L.COMPOSITES}, {c: 0 for c in L.COMPOSITES}
    for t in origins + [L6.OPERATIONAL_T]:
        tr, te = d.train(t), d.test(t)
        for X in (tr, te):
            problems += L.leakage_check(X)
            rows += len(X)
        if t in origins:
            for c in L.COMPOSITES:
                nan_test[c] += int(te[c].isna().sum())
    trT = d.train(L6.OPERATIONAL_T)
    nan_train = {c: int(trT[c].isna().sum()) for c in L.COMPOSITES}
    teT = d.test(L6.OPERATIONAL_T)
    leakage = {"rows_checked": rows, "problems": sorted(set(problems)),
               "rule": "every composite uses data of quarter t-1 (news: quarter t) and references over 2021-Q1..t-1",
               "nan_rows_test_65": nan_test, "nan_rows_training_at_Q4_2026_origin": {**nan_train, "of": int(len(trT))},
               "nan_rows_Q4_2026_test": {c: int(teT[c].isna().sum()) for c in L.COMPOSITES},
               "q4_2026_values": {NAMES[p]: {c: (None if v != v else round(float(v), 4)) for c, v in r.items()}
                                  for p, r in zip(teT["province_code"], teT[L.COMPOSITES].to_dict("records"))}}

    res = {"lead": 1, "test_quarters": dates, "reproduction": rep, "leakage": leakage,
           "metrics": {a: metrics(Pr[Pr["arm"] == a]) for a in [REF] + ARMS + BASELINES + ["ALWAYS_HIGH"]},
           "paired_vs_E36": {a: paired(Pr, a) for a in ARMS},
           "selection_path": {a: {q: v["chosen"] for q, v in info["selections"][a].items()} for a in [REF] + ARMS},
           "provisional_arms": sorted(L.PROVISIONAL)}
    holm = M.holm({a: res["paired_vs_E36"][a]["signflip_p_one_sided_improvement"] for a in ARMS})
    for a in ARMS:
        res["paired_vs_E36"][a]["holm_signflip_p"] = holm[a]

    # Mean |SHAP| per driver over the 65 evaluation rows (each arm's chosen model at each origin)
    def eval_shap(arm):
        frames = []
        for q in dates:
            fs, g = info["selections"][arm][q]["chosen"].split("x")
            c, _, _ = shap_frame(d, L.qk(q) - 1, fs, g)
            if c is not None:
                frames.append(group_abs(c))
        a = pd.concat(frames)
        return {"rows": int(len(a)), "mean_abs": {k: float(a[k].mean()) for k in a.columns},
                "share_pct": {k: float(a[k].sum() / a.to_numpy().sum() * 100) for k in a.columns},
                "drivers_with_nonzero_shap": [k for k in DRIVERS5 if a[k].sum() > 1e-9]}

    shap_eval = {a: eval_shap(a) for a in [REF] + ARMS}
    res["mean_abs_shap_eval"] = shap_eval

    # Adoption
    e36_acc = res["metrics"][REF]["accuracy"]
    by = {}
    for a in ARMS:
        ci = res["paired_vs_E36"][a]["brier_diff_ci95"]
        crit = {"a_brier_ci_includes_0_or_below": ci[0] <= 0,
                "b_accuracy_ge_E36_minus_0.01": res["metrics"][a]["accuracy"] >= e36_acc - 0.01 - 1e-12,
                "c_no_leakage": not leakage["problems"]}
        passed = all(crit.values())
        by[a] = {"criteria": crit, "pass_non_inferior": passed,
                 "improves_on_E36": passed and res["paired_vs_E36"][a]["holm_signflip_p"] < 0.05,
                 "drivers_with_nonzero_shap": len(shap_eval[a]["drivers_with_nonzero_shap"]),
                 "provisional": a in L.PROVISIONAL}
    passing = sorted([a for a in ARMS if by[a]["pass_non_inferior"]],
                     key=lambda a: (-by[a]["drivers_with_nonzero_shap"], res["metrics"][a]["brier"], N_NEW[a]))
    res["adoption"] = {"by_arm": by, "passing_in_preference_order": passing, "selected": passing[0] if passing else None}

    # Q4 2026 for E36, every passing arm, and E43-all4
    T = L6.OPERATIONAL_T
    res["q4_2026"] = {}
    for arm in dict.fromkeys([REF] + passing + ["E43-all4"]):
        (fs, g), _ = L6.operational_choice(d, Pr, arm)
        c, te, feats = shap_frame(d, T, fs, g)
        p = L6.lgbm_predict(d.train(T), te, feats, g)
        ga = group_abs(c)
        tot = ga.to_numpy().sum()
        shares = {k: float(ga[k].sum() / tot * 100) for k in ga.columns}
        res["q4_2026"][arm] = {"chosen": L6.cfg_name(fs, g),
                               "p": {"CALABARZON": float(np.mean(list(p.values()))), **{NAMES[k]: float(v) for k, v in p.items()}},
                               "shap_share_pct_CALABARZON": shares, "shap_share_sum": float(sum(shares.values())),
                               "provisional": arm in L.PROVISIONAL}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = L.E43 / "runs" / stamp
    run.mkdir(parents=True)
    keep = Pr[Pr["arm"].isin([REF] + ARMS + BASELINES + ["ALWAYS_HIGH"])].sort_values(["arm", "target_quarter", "province_code"])
    pred = keep.to_csv(index=False, float_format="%.10g", lineterminator="\n").encode()
    (run / "predictions.csv").write_bytes(pred)
    res["run"] = {"stamp": stamp, "predictions_sha256": hashlib.sha256(pred).hexdigest(),
                  "inputs_sha256": {k: C.sha(v) for k, v in L.INPUTS.items()}}
    C.write_json(L.E43 / "E43_results.json", C.clean(res))
    print("RUN", stamp, "selected:", res["adoption"]["selected"], "passing:", passing)


if __name__ == "__main__":
    main()

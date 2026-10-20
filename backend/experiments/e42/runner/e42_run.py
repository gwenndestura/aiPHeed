"""E42 run (lead 1).  python -B backend/experiments/e42/runner/e42_run.py -> backend/experiments/e42/{E42_results.json,
E42_results.md, runs/<stamp>/predictions.csv}.

The adoption rule below is the one given in the task, written into this file before any E42 result was seen.
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
import e42_lib as L  # noqa: E402
import e36_evaluate as E6  # noqa: E402  (same e36_lib object as L.L6)

L6, C, np, pd, M = L.L6, L.C, L.np, L.pd, E6.M
L6.guard32.EXP = L.E42
E36_RUN = L.ROOT / "aipheed-backend-aligned" / "experiments" / "E36_LightGBM_One_Quarter_Ahead" / "runs" / "20261015T023921Z"
REF = "E36-LGBM"                           # E36-repro: E36's nested procedure, recomputed here
ARMS = [REF, "E42-fixed", "E42-nested", "E42-abl-Climate", "E42-abl-FishKill", "E42-abl-Employment", "E42-abl-OFW"]
DIAG = ["E36-fixed-COMBxG2"]
BASELINES = E6.BASELINES
NAMES = {p: C.NAMES[p] for p in L.PROVS}
N_NEW = {"E42-fixed": 8, "E42-nested": 8, "E42-abl-Climate": 2, "E42-abl-FishKill": 2, "E42-abl-Employment": 2,
         "E42-abl-OFW": 2}

# ADOPTION RULE (fixed before results): an arm passes only if ALL hold
#   (a) the paired bootstrap 95% CI of (Brier arm - Brier E36) includes 0 or lies below 0,
#   (b) accuracy >= E36 accuracy - 0.01,
#   (c) no leakage issue found.
# Several pass -> lower Brier, then fewer new features.


def metrics(g: pd.DataFrame) -> dict:
    m = M.point_metrics(g["y"], g["p"])
    b = M.bootstrap(g)
    return {"n": m["n"], "HIGH": m["HIGH"], "LOW": m["LOW"], "correct": int(round(m["accuracy"] * m["n"])),
            "accuracy": m["accuracy"], "accuracy_ci95": b["accuracy_ci95"], "brier": m["brier"],
            "brier_ci95": b["brier_ci95"], "log_loss": m["log_loss"], "auc": m["roc_auc"],
            "balanced_accuracy": m["balanced_accuracy"], "high_recall": m["recall"], "low_recall": m["specificity"]}


def paired_vs_ref(Pr: pd.DataFrame, arm: str) -> dict:
    a = Pr[Pr["arm"] == arm].sort_values(["t", "province_code"])
    r = Pr[Pr["arm"] == REF].sort_values(["t", "province_code"])
    j = a.merge(r, on=["t", "province_code"], suffixes=("_a", "_r"))
    ok_a = (j["p_a"] >= .5).astype(int).to_numpy() == j["y_a"].to_numpy()
    ok_r = (j["p_r"] >= .5).astype(int).to_numpy() == j["y_r"].to_numpy()
    d = M.per_date_losses(a)["bri"] - M.per_date_losses(r)["bri"]                 # < 0: arm better
    rng = np.random.default_rng(M.SEED)
    v = d.to_numpy()
    boots = [v[rng.choice(len(v), len(v), replace=True)].mean() for _ in range(M.B)]
    return {"brier_diff_arm_minus_E36": float(v.mean()),
            "brier_diff_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "mcnemar": E6.mcnemar_exact(ok_a, ok_r), "accuracy_diff": float(ok_a.mean() - ok_r.mean()),
            "dates_better": int((v < 0).sum()), "dates_worse": int((v > 0).sum())}


def shap_rows(d, t, fs, g):
    feats = L6.FEATURE_SETS[fs]
    model = L6.fit_lgbm(d.train(t), feats, g)
    te = d.test(t)
    if model is None:
        return feats, None, te
    c = L6.shap_contributions(model, te[feats]).drop(columns="expected_value")
    return feats, c, te


def group_abs(c: pd.DataFrame) -> pd.DataFrame:
    """sum |SHAP| per group (market, the four drivers, other) for each row."""
    out = {g: c[[f for f in fs if f in c.columns]].abs().sum(axis=1) if any(f in c.columns for f in fs) else 0.0
           for g, fs in L.GROUPS.items()}
    grouped = {f for fs in L.GROUPS.values() for f in fs}
    out["other"] = c[[f for f in c.columns if f not in grouped]].abs().sum(axis=1)
    return pd.DataFrame(out, index=c.index)


def main():
    L.register_pools()
    d = L.Data()
    Pr, info = L6.walk_forward(d)
    dates = info["dates"]

    # E36 reproduction against E36's stored run
    st = pd.read_csv(E36_RUN / "predictions.csv", dtype={"province_code": str})
    j = Pr.merge(st[["arm", "target_quarter", "province_code", "p", "y"]], on=["arm", "target_quarter", "province_code"],
                 suffixes=("", "_stored"))
    e36 = j[j["arm"] == REF]
    stored_res = json.loads((E36_RUN / "results.json").read_text(encoding="utf-8"))
    rep = {"arms_compared": int(j["arm"].nunique()), "rows_compared": int(len(j)),
           "max_abs_p_diff_all_arms": float((j["p"] - j["p_stored"]).abs().max()),
           "E36_rows": int(len(e36)), "E36_max_abs_p_diff": float((e36["p"] - e36["p_stored"]).abs().max()),
           "labels_equal": bool((j["y"] == j["y_stored"]).all()),
           "E36_selection_path_equal": {q: v["chosen"] for q, v in info["selections"][REF].items()} ==
                                       {q: v["chosen"] for q, v in stored_res["selections"][REF].items()}}

    # Leakage check on every training and test row the walk-forward used, plus the operational origin
    problems, rows_checked, stale = [], 0, {"u_stale": 0, "remit_stale": 0}
    stale_rows = {"u_stale": [], "remit_stale": []}
    daily_rain_test_rows = 0
    for t in [L.qk(q) - 1 for q in dates] + [L6.OPERATIONAL_T]:
        for X in (d.train(t), d.test(t)):
            problems += L.leakage_check(X)
            rows_checked += len(X)
        te = d.test(t)
        for flag in stale:
            n = int(te[flag].sum())
            stale[flag] += n
            if n:
                stale_rows[flag].append(L.qs(t + 1))
        daily_rain_test_rows += int(te["rain_daily_service"].sum())
    train_stale = {f: int(sum(d.train(t)[f].sum() for t in [L.qk(q) - 1 for q in dates] + [L6.OPERATIONAL_T]))
                   for f in stale}
    leakage = {"rows_checked": rows_checked, "problems": sorted(set(problems)),
               "carried_forward_test_rows": stale, "carried_forward_test_targets": stale_rows,
               "carried_forward_training_rows": train_stale,
               "test_rows_with_2026_daily_service_rainfall": daily_rain_test_rows,
               "assumptions": ["Fisheries production of quarter t-1 is assumed published before O(t) (PSA release "
                               "dates not verified; same assumption as the risk-indicator layer).",
                               "2026 rainfall comes from NASA POWER's daily service, 2021-2025 from the monthly "
                               "service; comparability not verified."]}

    res = {"lead": 1, "test_quarters": dates, "inputs_added": L.DRIVERS, "reproduction": rep, "leakage": leakage,
           "metrics": {a: metrics(Pr[Pr["arm"] == a]) for a in ARMS + DIAG + BASELINES + ["ALWAYS_HIGH"]},
           "paired_vs_E36": {a: paired_vs_ref(Pr, a) for a in ARMS[1:] + DIAG},
           "selection_path": {a: {q: v["chosen"] for q, v in info["selections"][a].items()} for a in ARMS + DIAG}}

    # Adoption rule
    e36_acc = res["metrics"][REF]["accuracy"]
    verdicts = {}
    for a in ARMS[1:]:
        ci = res["paired_vs_E36"][a]["brier_diff_ci95"]
        crit = {"a_brier_ci_includes_0_or_favours_arm": ci[0] <= 0,
                "b_accuracy_ge_E36_minus_0.01": res["metrics"][a]["accuracy"] >= e36_acc - 0.01 - 1e-12,
                "c_no_leakage": not leakage["problems"]}
        verdicts[a] = {"criteria": crit, "pass": all(crit.values())}
    passing = sorted([a for a, v in verdicts.items() if v["pass"]], key=lambda a: (res["metrics"][a]["brier"], N_NEW[a]))
    res["adoption"] = {"rule": "pass iff (a) Brier-difference bootstrap 95% CI includes 0 or favours the arm, (b) "
                               "accuracy >= E36 - 0.01, (c) no leakage; ties -> lower Brier, then fewer features",
                       "by_arm": verdicts, "passing_in_order": passing, "selected": passing[0] if passing else None}
    best = passing[0] if passing else min(ARMS[1:], key=lambda a: res["metrics"][a]["brier"])
    res["best_arm_for_step4"] = {"arm": best, "why": "adopted" if passing else "no arm passed; lowest-Brier E42 arm shown"}

    # Step 4: Q4 2026 (operational origin 2026-10-01) and mean |SHAP| over the evaluation set
    T = L6.OPERATIONAL_T
    res["q4_2026"], res["mean_abs_shap_eval"] = {}, {}
    for arm in (REF, best):
        (fs, g), sel = L6.operational_choice(d, Pr, arm)
        feats, c, te = shap_rows(d, T, fs, g)
        p = L6.lgbm_predict(d.train(T), te, feats, g)
        ga = group_abs(c).assign(province=[NAMES[x] for x in te["province_code"]])
        tot = ga.drop(columns="province").to_numpy().sum()
        shares = {k: float(ga[k].sum() / tot * 100) for k in ga.columns if k != "province"}
        res["q4_2026"][arm] = {"chosen": L6.cfg_name(fs, g), "inputs": feats,
                               "p": {"CALABARZON": float(np.mean(list(p.values()))), **{NAMES[k]: float(v) for k, v in p.items()}},
                               "shap_share_pct_CALABARZON": shares,
                               "shap_share_sum": float(sum(shares.values()))}
        rows = []
        for q in dates:
            t = L.qk(q) - 1
            fs_, g_ = info["selections"][arm][q]["chosen"].split("x")
            _, cc, _ = shap_rows(d, t, fs_, g_)
            if cc is not None:
                rows.append(group_abs(cc))
        allr = pd.concat(rows)
        res["mean_abs_shap_eval"][arm] = {"rows": int(len(allr)), **{k: float(allr[k].mean()) for k in allr.columns},
                                          "share_pct": {k: float(allr[k].sum() / allr.to_numpy().sum() * 100) for k in allr.columns}}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = L.E42 / "runs" / stamp
    run.mkdir(parents=True)
    keep = Pr[Pr["arm"].isin(ARMS + DIAG + BASELINES + ["ALWAYS_HIGH"])].sort_values(["arm", "target_quarter", "province_code"])
    pred = keep.to_csv(index=False, float_format="%.10g", lineterminator="\n").encode()
    (run / "predictions.csv").write_bytes(pred)
    res["run"] = {"stamp": stamp, "predictions_sha256": hashlib.sha256(pred).hexdigest(),
                  "inputs_sha256": {k: C.sha(v) for k, v in L.INPUTS.items()}}
    C.write_json(L.E42 / "E42_results.json", C.clean(res))
    print("RUN", stamp, res["run"]["predictions_sha256"][:16], "selected:", res["adoption"]["selected"])


if __name__ == "__main__":
    main()

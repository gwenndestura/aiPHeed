"""E48 run (lead 1).  python -B backend/experiments/e48/runner/e48_run.py -> backend/experiments/e48/E48_results.json

ADOPTION (fixed before results): an arm with trigger features (A1, B1) is acceptable if the paired Brier-difference
95% CI versus its baseline (A0, B0) includes 0 or favours it AND its accuracy >= baseline accuracy - 0.01.
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
import e48_lib as L  # noqa: E402
import e36_evaluate as E6  # noqa: E402

L6, C, np, pd, M = L.L6, L.C, L.np, L.pd, E6.M
L6.guard32.EXP = L.E48
E36_RUN = L.ROOT / "aipheed-backend-aligned" / "experiments" / "E36_LightGBM_One_Quarter_Ahead" / "runs" / "20261015T023921Z"
NAMES = {p: C.NAMES[p] for p in L.PROVS}
DRIVERS = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
ARMS = {"A0": ("A", "E36-LGBM"), "A1": ("A", "E48-T5"), "B0": ("B", "E36-LGBM"), "B1": ("B", "E48-T5")}


def metrics(g):
    m = M.point_metrics(g["y"], g["p"])
    b = M.bootstrap(g)
    return {"n": m["n"], "HIGH": m["HIGH"], "LOW": m["LOW"], "accuracy": m["accuracy"], "accuracy_ci95": b["accuracy_ci95"],
            "balanced_accuracy": m["balanced_accuracy"], "auc": m["roc_auc"], "brier": m["brier"],
            "high_recall": m["recall"], "low_recall": m["specificity"]}


def paired(P, arm, ref):
    a = P[P["arm"] == arm].sort_values(["t", "province_code"])
    r = P[P["arm"] == ref].sort_values(["t", "province_code"])
    j = a.merge(r, on=["t", "province_code"], suffixes=("_a", "_r"))
    ok_a = (j["p_a"] >= .5).astype(int).to_numpy() == j["y_a"].to_numpy()
    ok_r = (j["p_r"] >= .5).astype(int).to_numpy() == j["y_r"].to_numpy()
    d = (M.per_date_losses(a)["bri"] - M.per_date_losses(r)["bri"]).to_numpy()
    rng = np.random.default_rng(M.SEED)
    boots = [d[rng.choice(len(d), len(d), replace=True)].mean() for _ in range(M.B)]
    return {"brier_diff_arm_minus_ref": float(d.mean()),
            "brier_diff_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "mcnemar": E6.mcnemar_exact(ok_a, ok_r), "accuracy_diff": float(ok_a.mean() - ok_r.mean()),
            "dates_better": int((d < 0).sum()), "dates_worse": int((d > 0).sum())}


def shap_groups(d, t, fs, g):
    feats = L6.FEATURE_SETS[fs]
    model = L6.fit_lgbm(d.train(t), feats, g)
    te = d.test(t)
    if model is None:
        return None, te, feats
    c = L6.shap_contributions(model, te[feats]).drop(columns="expected_value")
    grouped = {f for fs_ in L.GROUPS.values() for f in fs_}
    out = {k: (c[[f for f in v if f in c.columns]].abs().sum(axis=1) if any(f in c.columns for f in v)
               else pd.Series(0.0, index=c.index)) for k, v in L.GROUPS.items()}
    out["other"] = c[[f for f in c.columns if f not in grouped]].abs().sum(axis=1)
    return pd.DataFrame(out, index=c.index), te, feats


def main():
    L.register_pools()
    data = {"A": L.Data(paper=False), "B": L.Data(paper=True)}
    runs = {k: L6.walk_forward(d) for k, d in data.items()}
    dA, dB = data["A"], data["B"]

    st = pd.read_csv(E36_RUN / "predictions.csv", dtype={"province_code": str})
    j = runs["A"][0].merge(st[["arm", "target_quarter", "province_code", "p", "y"]],
                           on=["arm", "target_quarter", "province_code"], suffixes=("", "_s"))
    e36 = j[j["arm"] == "E36-LGBM"]
    res = {"lead": 1, "paper_tau": {"value": dB.tau_paper, "province_quarters": dB.tau_paper_n,
                                    "period": list(dB.tau_paper_range)},
           "reproduction_A0": {"rows": int(len(e36)), "max_abs_p_diff": float((e36["p"] - e36["p_s"]).abs().max()),
                               "all_arms_max_abs_p_diff": float((j["p"] - j["p_s"]).abs().max()),
                               "labels_equal": bool((j["y"] == j["y_s"]).all())},
           "test_quarters": {k: r[1]["dates"] for k, r in runs.items()}}

    # base rates: every labelled province-quarter, current (lead-1 trailing tau) vs paper (global median)
    s = dA.S1.dropna(subset=["S1"]).copy()
    cur, pap = [], []
    for _, x in s.iterrows():
        tau = dA.tau(int(x["tq"]) - 1)
        cur.append(np.nan if tau != tau else float(x["S1"] > tau))
        pap.append(float(x["S1"] > dB.tau_paper))
    s["cur"], s["pap"], s["yr"] = cur, pap, s["quarter"].str[:4]
    both = s.dropna(subset=["cur"])
    res["base_rates"] = {
        "current_overall": float(both["cur"].mean()), "paper_overall_same_rows": float(both["pap"].mean()),
        "paper_overall_all_rows": float(s["pap"].mean()), "rows_compared": int(len(both)),
        "rows_without_current_label": int(s["cur"].isna().sum()),
        "share_labels_differ": float((both["cur"] != both["pap"]).mean()),
        "per_year": {y: {"current": float(g["cur"].mean()), "paper": float(g["pap"].mean()), "n": int(len(g)),
                         "differ": int((g["cur"] != g["pap"]).sum())} for y, g in both.groupby("yr")}}

    # metrics and paired comparisons
    res["metrics"] = {}
    for key, (lab, arm) in ARMS.items():
        P = runs[lab][0]
        res["metrics"][key] = metrics(P[P["arm"] == arm])
    for lab in ("A", "B"):
        P = runs[lab][0]
        for b in ("ALWAYS_HIGH", "B1_PERSISTENCE") + tuple(E6.BASELINES[1:]):
            res["metrics"][f"{lab}:{b}"] = metrics(P[P["arm"] == b])
    res["paired"] = {"A1_vs_A0": paired(runs["A"][0], "E48-T5", "E36-LGBM"),
                     "B1_vs_B0": paired(runs["B"][0], "E48-T5", "E36-LGBM")}
    res["adoption"] = {}
    for arm, base, key in (("A1", "A0", "A1_vs_A0"), ("B1", "B0", "B1_vs_B0")):
        ci = res["paired"][key]["brier_diff_ci95"]
        crit = {"brier_ci_includes_0_or_favours": ci[0] <= 0,
                "accuracy_ge_baseline_minus_0.01": res["metrics"][arm]["accuracy"] >= res["metrics"][base]["accuracy"] - 0.01 - 1e-12}
        res["adoption"][arm] = {"criteria": crit, "acceptable": all(crit.values())}
    res["selection_path"] = {key: {q: v["chosen"] for q, v in runs[lab][1]["selections"][arm].items()}
                             for key, (lab, arm) in ARMS.items()}

    # Q4 2026 and mean |SHAP| over the test rows
    T = L6.OPERATIONAL_T
    res["q4_2026"], res["mean_abs_shap"] = {}, {}
    for key, (lab, arm) in ARMS.items():
        d, (P, info) = data[lab], runs[lab]
        (fs, g), _ = L6.operational_choice(d, P, arm)
        ga, te, feats = shap_groups(d, T, fs, g)
        p = L6.lgbm_predict(d.train(T), te, feats, g)
        tot = ga.to_numpy().sum()
        res["q4_2026"][key] = {"chosen": L6.cfg_name(fs, g),
                               "p": {"CALABARZON": float(np.mean(list(p.values()))), **{NAMES[k]: float(v) for k, v in p.items()}},
                               "shares_CALABARZON_pct": {k: float(ga[k].sum() / tot * 100) for k in ga.columns},
                               "trig_values": {NAMES[c]: {f: round(float(v), 4) for f, v in r.items()}
                                               for c, r in zip(te["province_code"], te[L.TRIG].to_dict("records"))}}
        frames = []
        for q, v in info["selections"][arm].items():
            fs_, g_ = v["chosen"].split("x")
            gq, _, _ = shap_groups(d, L.qk(q) - 1, fs_, g_)
            if gq is not None:
                frames.append(gq)
        a = pd.concat(frames)
        res["mean_abs_shap"][key] = {"rows": int(len(a)), **{k: float(a[k].mean()) for k in a.columns},
                                     "share_pct": {k: float(a[k].sum() / a.to_numpy().sum() * 100) for k in a.columns}}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = L.E48 / "runs" / stamp
    run.mkdir(parents=True)
    for lab, (P, _) in runs.items():
        keep = P[P["arm"].isin(["E36-LGBM", "E48-T5", "ALWAYS_HIGH"] + E6.BASELINES)].sort_values(["arm", "target_quarter", "province_code"])
        (run / f"predictions_{lab}.csv").write_bytes(keep.to_csv(index=False, float_format="%.10g", lineterminator="\n").encode())
    res["run"] = stamp
    C.write_json(L.E48 / "E48_results.json", C.clean(res))
    print("RUN", stamp, "adoption", {k: v["acceptable"] for k, v in res["adoption"].items()})


if __name__ == "__main__":
    main()

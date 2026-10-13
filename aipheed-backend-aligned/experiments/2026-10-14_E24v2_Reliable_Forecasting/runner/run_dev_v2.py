"""E24v2 class C (development) evaluation: the new candidates on E24's exact rows, plus 2026-Q1/Q2 (viewed in E18,
never used to select anything) and the noise ceiling.  FROZEN_EVALUATION_PROTOCOL.md 4-7.
Usage: python -B runner/run_dev_v2.py"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402

import e23_lib as L  # noqa: E402
import pcf  # noqa: E402
import run_e24 as R24  # noqa: E402
import v2lib as V2  # noqa: E402

EXP = guard.EXP
qk, qs = L.qk, L.qs
REQ_BASE = ["B1_naive_persistence", "B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only", "B5_lgbm_gov_only",
            "B6_lgbm_nlp_only"]


def jd(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


# ------------------------------------------------------------------------------------------ class C rows
def dev_t1(data):
    E = V2.load_e24_predictions("T1")
    base = E[E["model"] == "B1_naive_persistence"].copy()
    S = data["V"]["T1"].rename(columns={"v": "S1"})
    new, cache, dcache, det = [], {}, {}, []
    for (k, fq), g in base.groupby(["lead", "feature_quarter"]):
        t = qk(fq)
        tau = float(g["threshold"].iloc[0])
        tau_chk, _ = L.threshold_at(S, data["rounds"], t)
        assert abs(tau - tau_chk) < 1e-9, "threshold differs from E23 rule"
        _, tr_s, _ = V2.t1_training(data, t, int(k), tau, cache)
        g = g.sort_values("province_code")
        b1p = V2.calibrated_persistence(tr_s, g["y_last"].to_numpy())
        arms = {"B1p_calibrated_persistence": dict(zip(g["province_code"], b1p))}
        for name, sup, n, now in (("FINAL_V2_PCF", False, 600, False), ("PCF_S_supplementary", True, 600, False),
                                  ("PCF_n300_sensitivity", False, 300, False), ("PCF_NOW_A3", False, 600, True)):
            out = V2.pcf_t1(data, t, int(k), tau, sup, n, dcache, now)
            arms[name] = {p: v[0] for p, v in out.items()}
            if name == "FINAL_V2_PCF":
                for p, v in out.items():
                    det.append({"lead": int(k), "feature_quarter": fq, "province_code": p, **{
                        kk: vv for kk, vv in v[1].items() if not isinstance(vv, list)}})
        for arm, d in arms.items():
            x = g.copy()
            x["model"] = arm
            x["score"] = x["province_code"].map(d)
            new.append(x)
    P = pd.concat([E] + new, ignore_index=True)
    return P, pd.DataFrame(det)


def dev_t2(data):
    E = V2.load_e24_predictions("T2")
    base = E[E["model"] == "B1_naive_persistence"].copy()
    new, dcache = [], {}
    for (k, fq), g in base.groupby(["lead", "feature_quarter"]):
        t = qk(fq)
        g = g.sort_values("province_code")
        tr = V2.t2_training_long(data, t, int(k))
        arms = {"B1p_calibrated_persistence": dict(zip(g["province_code"],
                                                       V2.calibrated_persistence(tr, g["y_last"].to_numpy())))}
        out = V2.t2_models(data, t, int(k), dcache)
        arms["M3_pcf_D"] = {p: v[0] for p, v in out["M3_pcf_D"].items()}
        arms["FINAL_V2_M4_pcf_D_now"] = {p: v[0] for p, v in out["M4_pcf_D_now"].items()}
        for arm, d in arms.items():
            x = g.copy()
            x["model"] = arm
            x["score"] = x["province_code"].map(d)
            new.append(x)
    return pd.concat([E] + new, ignore_index=True)


# ------------------------------------------------------------------------------------------ C1-C9 (E24 definitions)
def score(P, final, target, extra_baselines=("B1p_calibrated_persistence",)):
    rows, out = [], {}
    models = list(P["model"].unique())
    applicable = REQ_BASE + list(extra_baselines)
    for k in sorted(P["lead"].unique()):
        d = P[P["lead"] == k]
        f = d[d["model"] == final]
        nH, nL, no = int(f["y"].sum()), int((1 - f["y"]).sum()), int(f["origin"].nunique())
        ev = no >= L.MIN_ORIGINS and nH >= L.MIN_PER_CLASS and nL >= L.MIN_PER_CLASS
        mm = {}
        for m in models:
            dm = d[d["model"] == m].sort_values(["origin", "province_code"])
            assert len(dm) == len(f)
            mm[m] = R24.metrics(dm["y"], dm["score"])
            rows.append({"target": target, "lead": int(k), "model": m, "n_rows": len(dm), "n_test_quarters": no,
                         "HIGH": nH, "LOW": nL, "evaluable": ev,
                         **{q: mm[m][q] for q in ("accuracy", "balanced_accuracy", "precision", "recall", "F1",
                                                  "specificity", "ROC_AUC", "Brier", "TP", "FP", "FN", "TN")}})
        strongest = max(applicable, key=lambda m: (mm[m]["accuracy"], -mm[m]["Brier"]))
        others = [m for m in models if m != final]
        tests = {b: R24.compare(d, final, b) for b in others}
        hp = L.holm({b: tests[b]["acc_p_one_sided"] for b in REQ_BASE})
        for b in REQ_BASE:
            tests[b]["acc_p_holm"] = hp[b]
        fin = f.sort_values(["origin", "province_code"])
        changed = fin["y"].to_numpy() != fin["y_last"].to_numpy()
        corr = ((fin["score"].to_numpy() >= .5).astype(int) == fin["y"].to_numpy())
        ci = L.cluster_boot_auc(fin["origin"].to_numpy(), fin["y"].to_numpy(), fin["score"].to_numpy()) if ev \
            else {"ci_low": None}
        t_s, t_p = tests[strongest], tests["B1_naive_persistence"]
        crit = {
            "C1_accuracy_gt_75": bool(mm[final]["accuracy"] > 0.75),
            "C2_beats_strongest": bool(t_s["acc_diff"] > 0 and t_s["acc_p_one_sided"] < 0.05 and t_s["brier_diff"] <= 0),
            "C3_not_HIGH_dominance": bool((mm[final]["balanced_accuracy"] or 0) >= 0.60 and
                                          (mm[final]["balanced_accuracy"] or 0) > (mm[strongest]["balanced_accuracy"] or 0)),
            "C4_defensible_across_folds": bool(t_s["origins_better"] > t_s["origins_worse"] and t_s["loo_acc_diff_min"] >= 0),
            "C5_info_beyond_persistence": bool(int((corr & changed).sum()) > int((~corr & ~changed).sum())),
            "C6_reliability_rule": bool(ev and ci.get("ci_low") is not None and ci["ci_low"] > 0.5 and
                                        t_p["brier_p_one_sided"] < 0.05),
            "C9_generalizes_unseen": "NOT ASSESSABLE on class C (development); see the prospective seal"}
        out[str(k)] = {"n_test_quarters": no, "HIGH": nH, "LOW": nL, "evaluable": ev, "strongest_baseline": strongest,
                       "metrics": mm, "tests": tests, "criteria": crit, "label_change_rows": int(changed.sum()),
                       "final_correct_on_changed": int((corr & changed).sum()),
                       "final_wrong_on_unchanged": int((~corr & ~changed).sum()), "auc_ci_final": ci}
    return pd.DataFrame(rows), out


# ------------------------------------------------------------------------------------------ 2026-Q1/Q2 check
def late_2026(data):
    """Targets 2026-Q1/Q2 (viewed in E18; never used to select). Only models that need no 2026 news/government
    features: B1, B1p, PCF, PCF-S, M2 (E24-frozen LightGBM on P) for T1; B1, B1p, M1, M3, M4 for T2."""
    S = data["V"]["T1"].rename(columns={"v": "S1"})
    VT1, VT2 = data["V"]["T1"], data["V"]["T2"]
    rows, cache = [], {}
    for t, k in ((qk("2025-Q4"), 1), (qk("2025-Q4"), 2), (qk("2026-Q1"), 1)):
        tq = qs(t + k)
        tau, _ = L.threshold_at(S, data["rounds"], t)
        tr_p, tr_s, pub = V2.t1_training(data, t, k, tau, cache)
        te = pd.DataFrame({"province_code": V2.PROVS, "t": t})
        te = R24.pairs(te, VT1, k)
        te["y"] = (te["v"] > tau).astype(int)
        te = R24.pblock(VT1, pub, te, tau, cache).sort_values("province_code").reset_index(drop=True)
        sc = {"B1_naive_persistence": te["y_last"].to_numpy(float),
              "B1p_calibrated_persistence": V2.calibrated_persistence(tr_s, te["y_last"].to_numpy())}
        for name, sup, now in (("FINAL_V2_PCF", False, False), ("PCF_S_supplementary", True, False),
                               ("PCF_NOW_A3", False, True)):
            o = V2.pcf_t1(data, t, k, tau, sup, use_now=now)
            sc[name] = np.array([o[p][0] for p in te["province_code"]])
        p2, _, _, _ = R24.nested_lgbm(tr_s, tr_p, R24.P_COLS, te, k)
        sc["M2_lgbm_P_E24frozen"] = p2
        for m, v in sc.items():
            for i, r in te.iterrows():
                rows.append({"target": "T1", "lead": k, "feature_quarter": qs(t), "target_quarter": tq,
                             "province_code": r["province_code"], "model": m, "score": float(v[i]), "y": int(r["y"]),
                             "y_last": float(r["y_last"]), "value": float(r["v"]), "threshold": tau})
        # T2
        te2 = R24.pairs(pd.DataFrame({"province_code": V2.PROVS, "t": t}), VT2, k)
        te2["y"] = (te2["v"] > 0).astype(int)
        te2 = te2.sort_values("province_code").reset_index(drop=True)
        ylast = np.array([float(data["Dm"][(p, t - 1)] > 0) for p in te2["province_code"]])
        tr = V2.t2_training_long(data, t, k)
        mod = V2.t2_models(data, t, k)
        Vlong = data["Dall"].rename(columns={"D": "v"}).assign(tq=lambda x: x["quarter"].map(qk))
        pub2 = lambda q, tt: qk(q) <= tt - 1   # noqa: E731
        grid = pd.DataFrame([(p, tt) for tt in range(qk(V2.LONG_FIRST), t) for p in V2.PROVS],
                            columns=["province_code", "t"])
        c2 = {}
        trl = pd.concat([R24.pairs(grid, Vlong, kk) for kk in [k]], ignore_index=True)
        trl = trl[trl["target_q"] <= t - 1]
        trl = R24.pblock(Vlong, pub2, trl, 0.0, c2)
        trl["y"] = (trl["v"] > 0).astype(int)
        te2p = R24.pblock(Vlong, pub2, te2[["province_code", "t", "v", "target_quarter", "lead", "target_q", "y"]], 0.0, c2)
        sc2 = {"B1_naive_persistence": ylast, "B1p_calibrated_persistence": V2.calibrated_persistence(tr, ylast),
               "M1_lr_P_1995window": L.fit_lr(trl, R24.P_COLS, te2p),
               "M3_pcf_D": np.array([mod["M3_pcf_D"][p][0] for p in te2["province_code"]]),
               "FINAL_V2_M4_pcf_D_now": np.array([mod["M4_pcf_D_now"][p][0] for p in te2["province_code"]])}
        for m, v in sc2.items():
            for i, r in te2.iterrows():
                rows.append({"target": "T2", "lead": k, "feature_quarter": qs(t), "target_quarter": tq,
                             "province_code": r["province_code"], "model": m, "score": float(v[i]), "y": int(r["y"]),
                             "y_last": float(ylast[i]), "value": float(r["v"]), "threshold": 0.0})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------ noise ceiling
def noise_ceiling(P1, data):
    r = data["rounds"]
    Hq = r[r["definition_A"]].groupby("quarter")["H"].agg(["mean", "count"])
    # 2026 H (authorized production rounds, one per quarter): H = S1 - 2D, identical for all five provinces
    s1 = data["V"]["T1"].merge(data["V"]["T2"][["province_code", "quarter", "v"]], on=["province_code", "quarter"],
                               suffixes=("", "_D"))
    h26 = (s1["v"] - 2 * s1["v_D"]).groupby(s1["quarter"]).agg(["mean", "std"])
    for q in h26.index:
        if q not in Hq.index:
            assert h26.loc[q, "std"] < 1e-9
            Hq.loc[q] = [h26.loc[q, "mean"], 1]
    d = P1[(P1["lead"] == 1) & (P1["model"] == "B1_naive_persistence")].copy()
    out = {}
    for n in (600, 300):
        se = d["target_quarter"].map(lambda q: np.sqrt(pcf.samp_var(Hq.loc[q, "mean"], n) / Hq.loc[q, "count"]))
        z = (d["value"] - d["threshold"]) / se
        pf = norm.cdf(-z.abs())
        err = (d["score"] >= .5).astype(int) != d["y"]
        chg = d["y"] != d["y_last"]
        out[f"n{n}"] = {"rows": int(len(d)), "expected_sampling_flips_all_rows": float(pf.sum()),
                        "expected_sampling_flips_on_persistence_errors": float(pf[err].sum()),
                        "persistence_errors": int(err.sum()), "label_change_rows": int(chg.sum()),
                        "rows_within_1_SE_of_tau": int((z.abs() < 1).sum()),
                        "rows_within_2_SE_of_tau": int((z.abs() < 2).sum()),
                        "per_change_row": [{"target_quarter": a, "province_code": b, "S1": float(v), "tau": float(t),
                                            "z": float(zz), "p_flip": float(pp)} for a, b, v, t, zz, pp in
                                           zip(d.loc[chg, "target_quarter"], d.loc[chg, "province_code"],
                                               d.loc[chg, "value"], d.loc[chg, "threshold"], z[chg], pf[chg])]}
    return out


def main():
    R24.check_frozen()
    runid = "DEV_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rd = EXP / "runs" / runid
    rd.mkdir(parents=True)
    data = V2.load_all()
    P1, det = dev_t1(data)
    P2 = dev_t2(data)
    LT = late_2026(data)
    seals = {}
    for name, df in (("predictions_T1_dev", P1), ("predictions_T2_dev", P2), ("predictions_2026Q1Q2", LT),
                     ("pcf_T1_components", det)):
        b = df.to_csv(index=False, lineterminator="\n").encode()
        (rd / f"{name}.csv").write_bytes(b)
        seals[name] = hashlib.sha256(b).hexdigest()
    rows1, res1 = score(P1, "FINAL_V2_PCF", "T1")
    rows2, res2 = score(P2, "FINAL_V2_M4_pcf_D_now", "T2")
    nc = noise_ceiling(P1, data)
    late = {}
    for (tg, k), g in LT.groupby(["target", "lead"]):
        late[f"{tg}_k{k}"] = {m: {"accuracy": float(((gg["score"] >= .5).astype(int) == gg["y"]).mean()),
                                  "brier": float(((gg["score"] - gg["y"]) ** 2).mean()), "rows": int(len(gg))}
                              for m, gg in g.groupby("model")}
    pd.concat([rows1, rows2]).to_csv(rd / "metrics_dev.csv", index=False, lineterminator="\n")
    (rd / "results_dev.json").write_text(json.dumps({"T1": res1, "T2": res2, "noise_ceiling": nc, "late_2026": late,
                                                     "seals": seals, "access_log": guard.ACCESS_LOG,
                                                     "integrity": data["log"]}, indent=1, default=jd),
                                         encoding="utf-8")
    print(runid, seals)
    for tg, res, fin in (("T1", res1, "FINAL_V2_PCF"), ("T2", res2, "FINAL_V2_M4_pcf_D_now")):
        for k in sorted(res, key=int):
            r = res[k]
            print(tg, k, r["n_test_quarters"], r["HIGH"], r["LOW"], "final acc", round(r["metrics"][fin]["accuracy"], 3),
                  "brier", round(r["metrics"][fin]["Brier"], 3), "| B1", round(r["metrics"]["B1_naive_persistence"]["accuracy"], 3),
                  round(r["metrics"]["B1_naive_persistence"]["Brier"], 3), "| B1p brier",
                  round(r["metrics"]["B1p_calibrated_persistence"]["Brier"], 3), "| strongest", r["strongest_baseline"],
                  {c: v for c, v in r["criteria"].items() if c != "C9_generalizes_unseen"})
    print(json.dumps(nc["n600"], indent=1, default=jd)[:2500])
    print(json.dumps(late, indent=1)[:3000])


if __name__ == "__main__":
    main()

"""E55: E53-A1 at lead 2 (target F = origin quarter + 2). Experiment only.

    python -B backend/experiments/e55/runner/e55_run.py  -> backend/experiments/e55/E55_results.json

Same inputs as E53-A1 (E36's 13 + five trigger proportions + five cond_*), same pool (COMPACT_T5_C / COMB_T5_C x
G1/G4/G3/G2), seed 36, nested rule (E36's select, prior dates = E37's eligible_prior at k = 2: targets posted before
the origin), and E49-C2 shrinkage fitted on earlier eligible dates only. The walk-forward is E37's generic lead-k
procedure (e37_lib.walk_forward(d, 2)) on E53's Data. Timing at origin O(t) (first day of quarter t+1), target t+2:
SWS/CPI/news inputs exactly as E37/E38 at k = 2; cond_* use data quarter t-1 = F-3 (the latest complete quarter
published before the origin), ranked against strictly earlier quarters. No outcome after the origin is used.

Comparison on identical rows (E38's 55 lead-2 development rows, 11 target quarters 2023-Q3..2026-Q3): E38-LGBM as
stored in E38 run 20261015T033922Z (its own nested threshold) and persistence (B1). Tests: exact McNemar on
correctness and two-sided sign-flip on per-date Brier, each Holm-adjusted over the two comparisons.

ADOPTION (fixed before results): eligible only if accuracy >= 0.75, balanced accuracy >= 0.75, Brier <= persistence's
Brier on the same rows, and LOW caught >= half of the LOW rows. Otherwise "not eligible"; no further tuning.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E55 = Path(__file__).resolve().parents[1]
BACKEND = E55.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e53" / "runner"))
import e53_run as X53  # noqa: E402  (Data with cond_*, register, shares, holm; brings in e37/e38/e48/e36 libs)

X, R, L, L6, C, np, pd, M, EV = X53.X, X53.R, X53.L, X53.L6, X53.C, X53.np, X53.pd, X53.M, X53.EV
L7 = L.L8.L7
L6.guard32.EXP = E55
K = 2
POOL = "E53-A1"
NAMES, PROVS = X53.NAMES, X53.PROVS
E38_RUN = (BACKEND.parent / "aipheed-backend-aligned" / "experiments" / "E38_Lead2_Diagnosis_Tuning" / "runs"
           / "20261015T033922Z" / "predictions.csv")


def metrics(g: pd.DataFrame, thr=None) -> dict:
    """g: columns p, y (and optional threshold column)."""
    th = g["threshold"] if thr is None and "threshold" in g else 0.5
    pred = (g["p"] >= th).astype(int)
    y = g["y"].astype(int)
    tp, tn = int(((pred == 1) & (y == 1)).sum()), int(((pred == 0) & (y == 0)).sum())
    nh, nl = int((y == 1).sum()), int((y == 0).sum())
    pm = M.point_metrics(y, g["p"])
    return {"n": int(len(g)), "accuracy": float((pred == y).mean()),
            "balanced_accuracy": float(((tp / nh if nh else 0) + (tn / nl if nl else 0)) / 2),
            "auc": pm["roc_auc"], "brier": float(((g["p"] - y) ** 2).mean()), "LOW_caught": tn, "LOW_rows": nl,
            "HIGH_caught": tp, "HIGH_rows": nh}


def main():
    os.chdir(BACKEND)
    X53.register()
    E31 = X.live_engine()
    d = X53.Data(X53.build_cond())
    Pr, info = L7.walk_forward(d, K)
    dates = [C.qk(q) - K for q in info["dates"]]
    T = L7.OPERATIONAL_T
    alld = dates + [T]
    labels = {t: {c: int(d.label(c, t + K, t)) for c in PROVS} for t in dates}
    labels_all = {**labels, T: {c: 0 for c in PROVS}}
    base = {t: float((d.train(t, K)["y"].sum() + 1) / (len(d.train(t, K)) + 2)) for t in alld}
    prior_of = {t: L7.eligible_prior(d, t, K, dates) for t in alld}

    raw, cfg, models = {}, {}, {}
    for t in alld:
        if t == T:
            (fs, g), sel = L7.operational_choice(d, Pr, K, POOL)
        else:
            fs, g = info["selections"][POOL][C.qs(t + K)]["chosen"].split("x")
        feats = L6.FEATURE_SETS[fs]
        tr, te = d.train(t, K), d.test(t, K)
        ptr, pte, m = X.lgbm_arrays(tr, te, feats, g)
        raw[t], cfg[t], models[t] = dict(zip(te["province_code"], pte)), L6.cfg_name(fs, g), (m, feats, te, ptr, tr)
    wf = Pr[Pr["arm"] == POOL]
    chk = float(max(abs(raw[C.qk(r.t)][r.province_code] - r.p) for r in wf.itertuples()))
    cal, fb, pa = R.calibrated(raw, labels_all, base, prior_of, "shrink")

    rows = pd.DataFrame([{"t": C.qs(t), "target_quarter": C.qs(t + K), "province_code": c, "arm": "E55",
                          "p": cal[t][c], "p_raw": raw[t][c], "y": labels[t][c]} for t in dates for c in PROVS])
    e38 = pd.read_csv(E38_RUN, dtype={"province_code": str})
    ref = {"E38": e38[e38["arm"] == "E38-LGBM"], "persistence": e38[e38["arm"] == "B1_PERSISTENCE"]}
    key = ["target_quarter", "province_code"]
    out = {"lead": K, "test_quarters": info["dates"], "n_rows": int(len(rows)),
           "walk_forward_check_max_abs_diff": chk, "pool_configs": {C.qs(t + K): cfg[t] for t in alld},
           "shrink_params": {C.qs(t + K): v for t, v in pa.items()}, "fallback_raw": [C.qs(t + K) for t in fb if t != T]}
    same = {}
    for name, g in ref.items():
        j = rows.merge(g[key + ["p", "y"] + (["threshold"] if "threshold" in g else [])], on=key, suffixes=("", "_ref"))
        assert len(j) == len(rows) == 55, (name, len(j))
        assert (j["y"] == j["y_ref"]).all(), f"labels differ from {name}"
        same[name] = j
    m55 = metrics(rows)
    m55_raw = metrics(rows.assign(p=rows["p_raw"]))
    mref = {"E38": metrics(same["E38"].assign(p=same["E38"]["p_ref"], threshold=same["E38"]["threshold"])),
            "persistence": metrics(same["persistence"].assign(p=same["persistence"]["p_ref"]))}
    # paired tests vs E38 and persistence (E38 correctness uses its own nested threshold)
    ok55 = ((rows.sort_values(key)["p"] >= 0.5).astype(int) == rows.sort_values(key)["y"]).to_numpy()
    b55 = M.per_date_losses(rows)["bri"]
    mc, sf = {}, {}
    for name, j in same.items():
        j = j.sort_values(key)
        thr = j["threshold"] if name == "E38" else 0.5
        okr = ((j["p_ref"] >= thr).astype(int) == j["y"]).to_numpy()
        mc[name] = EV.mcnemar_exact(ok55, okr)
        bref = M.per_date_losses(j.assign(p=j["p_ref"]))["bri"]
        sf[name] = EV.signflip_two((b55 - bref).to_numpy())
        mc[name]["brier_diff_E55_minus_ref"] = float((b55 - bref).mean())
    hm, hs = X53.holm({k: v["p_two_sided"] for k, v in mc.items()}), X53.holm(sf)
    out["metrics"] = {"E55_C2": m55, "E55_raw": m55_raw, **mref}
    out["tests_vs"] = {k: {"mcnemar": mc[k], "mcnemar_p_holm": hm[k], "signflip_brier_p": sf[k],
                           "signflip_brier_p_holm": hs[k]} for k in mc}
    m_, mtr = models[T][0], models[T]
    out["train_2027Q1_origin"] = {"raw": X.train_metrics(mtr[3], mtr[4]["y"]),
                                  "calibrated": X.train_metrics(X.shrink(mtr[3], pa.get(T)), mtr[4]["y"])}
    crit = {"accuracy_ge_0.75": m55["accuracy"] >= 0.75, "balanced_accuracy_ge_0.75": m55["balanced_accuracy"] >= 0.75,
            "brier_le_persistence": m55["brier"] <= mref["persistence"]["brier"] + 1e-12,
            "LOW_caught_ge_half": m55["LOW_caught"] >= m55["LOW_rows"] / 2}
    out["adoption"] = {"criteria": crit, "eligible": all(crit.values()),
                       "verdict": "eligible" if all(crit.values()) else "not eligible"}
    # 2027-Q1 forecast (PREVIEW) with five-driver shares (live panel method, E53 mapping; evidence quarter t)
    m, feats, te, _, _ = models[T]
    shap = {}
    if m is not None:
        cc = L6.shap_contributions(m, te[feats])
        out["shap_expected_value_logodds_2027Q1"] = float(cc["expected_value"].iloc[0])
        shap = {c: cc.drop(columns="expected_value").iloc[i].to_dict() for i, c in enumerate(te["province_code"])}
    per, pool_mag, pool_other = {}, {k: 0.0 for k in X53.GROUPS}, 0.0
    for code, s in shap.items():
        mag, other, _ = X53.shares(E31, s, code, C.qs(T))
        per[NAMES[code]] = {"p_high": cal[T][code], "p_raw": raw[T][code],
                            "drivers_a": dict(zip(X53.GROUPS, X.integer_shares([mag[k] for k in X53.GROUPS]))),
                            "drivers_b": dict(zip(list(X53.GROUPS) + ["other"],
                                                  X.integer_shares([mag[k] for k in X53.GROUPS] + [other]))),
                            "top_inputs": {f: round(v, 3) for f, v in sorted(s.items(), key=lambda kv: -abs(kv[1]))[:5]}}
        for k in X53.GROUPS:
            pool_mag[k] += mag[k]
        pool_other += other
    out["forecast_2027Q1"] = {
        "label": "PREVIEW (lead 2, origin 2026-10-01; not served)", "config": cfg[T],
        "CALABARZON": {"index": float(np.mean(list(cal[T].values()))),
                       "drivers_a": dict(zip(X53.GROUPS, X.integer_shares([pool_mag[k] for k in X53.GROUPS]))),
                       "drivers_b": dict(zip(list(X53.GROUPS) + ["other"],
                                             X.integer_shares([pool_mag[k] for k in X53.GROUPS] + [pool_other])))},
        **per}
    out["cond_2027Q1_inputs"] = {NAMES[c]: {k: (None if v != v else round(float(v), 1)) for k, v in r.items()}
                                 for c, r in te.set_index("province_code")[X53.COND].iterrows()}
    out["index_by_target"] = {C.qs(t + K): float(np.mean(list(cal[t].values()))) for t in alld}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E55 / "runs" / stamp
    run.mkdir(parents=True)
    rows.to_csv(run / "predictions.csv", index=False, float_format="%.10g")
    out["run"] = stamp
    C.write_json(E55 / "E55_results.json", C.clean(out))
    print("RUN", stamp, "check", chk, "| E55", {k: round(v, 3) if isinstance(v, float) else v for k, v in m55.items()},
          "|", out["adoption"]["verdict"])


if __name__ == "__main__":
    main()

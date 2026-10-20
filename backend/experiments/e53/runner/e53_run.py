"""E53: retrain with measured driver-condition inputs (cond_*), lead 1. Experiment only.

    python -B backend/experiments/e53/runner/e53_run.py  -> backend/experiments/e53/E53_results.json

cond_* (no leakage). For the row of origin t (target F = t+1) the data quarter is Q = t-1 = F-2 (the latest complete
quarter before the origin). Each component is the percent rank of its quarter-Q value against that series' history
STRICTLY BEFORE Q (2021-Q1..Q-1): rank = 100 * #{h < x} / n, n = number of earlier values; fewer than 2 earlier values
-> missing (LightGBM's missing-value handling; no imputation). Series and sources as E52 (read only):
  cond_market      mean(rank D, rank rice CPI YoY)                          PSA provincial CPI
  cond_climate     max(rank |rainfall anomaly|, rank storm signal)         NASA POWER daily (e43), NOAA IBTrACS
  cond_fish        rank of max(0, -ln(V_Q / V_Q-4)), fisheries production   PSA OpenStat (proxy)
  cond_employment  mean(rank u, rank u_Q - u_Q-4), national LFS             PSA OpenStat (national)
  cond_ofw         rank of max(0, -real peso remittance growth)            BSP (curated / provisional), FX, food CPI
Data revisions are not modelled (the values are the current vintages).

Arms (E36 walk-forward, nested rule, seed 36, threshold 0.5, the G1/G4/G3/G2 grid; E49-C2 shrinkage fitted on earlier
dates only; nothing else -- no monotone constraints, weights or feature tricks):
  A0  E49 as served: pool E48-T5 (COMPACT_T5 / COMB_T5) + C2    (must match acc 0.846, bal 0.841, AUC 0.855)
  A1  E48-A1 features + cond_*: pool (COMPACT_T5 + cond, COMB_T5 + cond) + C2
  A2  E36 features + cond_* (trig_* replaced): pool (COMPACT + cond, COMB + cond) + C2

Attribution: exact TreeSHAP of the model fitted at each origin; groups market = D_last, Dnow, rice_rel, trig_market,
cond_market; climate = trig_climate, cond_climate; fish_kill = trig_fish_kill, cond_fish; employment =
trig_employment, cond_employment; ofw_remittance = trig_ofw_remittance, cond_ofw. Group magnitude = |signed sum|
plus the news inputs' |SHAP| split by the topics of the validated titles of the evidence quarter t, exactly as the live
e31_engine.five_trigger_drivers (its news_topic_shares is loaded from the live file by path).

Tests vs A0 (65 rows): exact McNemar on correctness and two-sided sign-flip on per-date Brier differences, each
Holm-adjusted over the two comparisons (A1, A2).

ADOPTION (fixed before results): eligible only if balanced accuracy >= 0.83, AUC >= 0.84, Brier <= 0.16 and LOW rows
caught >= 10/12. Among eligible arms prefer the most drivers with non-zero attribution (mean five-driver share over the
65 test rows > 0.05%); tie -> higher balanced accuracy, then lower Brier. None eligible -> say so; no further tuning.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E53 = Path(__file__).resolve().parents[1]
BACKEND = E53.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e50" / "runner"))
sys.path.insert(0, str(BACKEND / "experiments" / "e52" / "runner"))
import e50_run as X  # noqa: E402  (brings in e49_run / e48_lib / e36_lib)
import e52_scores as S  # noqa: E402  (E52 data loaders, read only)

R, L, L6, C, np, pd, M = X.R, X.L, X.L6, X.C, X.np, X.pd, X.M
EV = R.E                                                   # e36_evaluate (McNemar, sign-flip)
L6.guard32.EXP = E53
NAMES, PROVS = X.NAMES, X.PROVS
COND = ["cond_market", "cond_climate", "cond_fish", "cond_employment", "cond_ofw"]
TRIG = ["trig_market", "trig_climate", "trig_employment", "trig_ofw_remittance", "trig_fish_kill"]
GROUPS = {"market": ["D_last", "Dnow", "rice_rel", "trig_market", "cond_market"],
          "climate": ["trig_climate", "cond_climate"], "fish_kill": ["trig_fish_kill", "cond_fish"],
          "employment": ["trig_employment", "cond_employment"], "ofw_remittance": ["trig_ofw_remittance", "cond_ofw"]}
ARMS = {"A0": "E48-T5", "A1": "E53-A1", "A2": "E53-A2"}


def strict_rank(s: dict, q: int) -> float:
    x = s.get(q, float("nan"))
    h = [s[k] for k in range(S.START, q) if k in s and s[k] == s[k]]
    if x != x or len(h) < 2:
        return float("nan")
    return 100.0 * sum(v < x for v in h) / len(h)


def build_cond():
    d = S.load()
    out = {}
    for p in PROVS:
        for q in range(S.qk("2021-Q1"), S.qk("2026-Q3") + 1):
            out[(p, q)] = {
                "cond_market": S.nanmean(strict_rank(d["D"][p], q), strict_rank(d["RICE"][p], q)),
                "cond_climate": S.nanmax(strict_rank(d["RAIN"][p], q), strict_rank(d["TC"][p], q)),
                "cond_fish": strict_rank(d["FISH"][p], q),
                "cond_employment": S.nanmean(strict_rank(d["U"], q), strict_rank(d["DU"], q)),
                "cond_ofw": strict_rank(d["OFW"][p], q)}
    return out


class Data(L.Data):
    def __init__(self, cond):
        super().__init__(paper=False)
        self.cond = cond

    def features(self, t, k):
        Xf = super().features(t, k).copy()
        q = t - 1                                          # data quarter F-2 for target t+1 (lead 1)
        for c in COND:
            Xf[c] = [self.cond.get((p, q), {}).get(c, float("nan")) for p in Xf["province_code"]]
        return Xf


def register():
    X.register()                                           # E48-T5 (+ E49-REG, E50) pools
    L6.FEATURE_SETS.update({"COMPACT_T5_C": L6.FEATURE_SETS["COMPACT_T5"] + COND, "COMB_T5_C": L6.FEATURE_SETS["COMB_T5"] + COND,
                            "COMPACT_C": L6.COMPACT + COND, "COMB_C": L6.COMB + COND})
    L6.POOLS["E53-A1"] = ([("COMPACT_T5_C", g) for g in L6.COMPLEXITY] + [("COMB_T5_C", g) for g in L6.COMPLEXITY],
                          ("COMB_T5_C", "G1"))
    L6.POOLS["E53-A2"] = ([("COMPACT_C", g) for g in L6.COMPLEXITY] + [("COMB_C", g) for g in L6.COMPLEXITY],
                          ("COMB_C", "G1"))


def shares(E31, shap: dict, code: str, ev_q: str):
    """five-driver magnitudes (live method, E53 mapping) + Other; returns (mag dict, other, direct dict)."""
    grouped = {f for fs in GROUPS.values() for f in fs}
    mag = {g: abs(sum(shap.get(f, 0.0) for f in fs)) for g, fs in GROUPS.items()}
    direct = dict(mag)
    assigned = 0.0
    for level, nf in E31.NEWS_FEATURES.items():
        sh, _ = E31.news_topic_shares(code if level == "province" else None, ev_q)
        a = sum(abs(shap.get(f, 0.0)) for f in nf)
        for g, w in sh.items():
            mag[g] += w * a
            assigned += w * a
    other = sum(abs(v) for f, v in shap.items() if f not in grouped) - assigned
    return mag, other, direct


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m, run, out = len(items), 0.0, {}
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, p * (m - i)))
        out[k] = run
    return out


def main():
    os.chdir(BACKEND)
    register()
    E31 = X.live_engine()
    d = Data(build_cond())
    Pr, info = L6.walk_forward(d)
    dates = [C.qk(x) - 1 for x in info["dates"]]
    T = L6.OPERATIONAL_T
    alld = dates + [T]
    labels = {t: {c: int(d.label(c, t + 1, t)) for c in PROVS} for t in dates}
    labels_all = {**labels, T: {c: 0 for c in PROVS}}
    base = {t: float((d.train(t)["y"].sum() + 1) / (len(d.train(t)) + 2)) for t in alld}
    prior_of = {t: L6.eligible_prior_dates(d, t, dates) for t in alld}
    trT = d.train(T)
    res = {"lead": 1, "test_quarters": info["dates"], "n_test_rows": 5 * len(dates), "training_rows_Q4_origin": len(trT),
           "feature_stats_training_Q4_origin": {f: {"variance": float(trT[f].astype(float).var()),
                                                    "distinct": int(trT[f].astype(float).nunique(dropna=True)),
                                                    "missing": int(trT[f].isna().sum())} for f in COND + TRIG},
           "cond_q4_2026_test_rows": {NAMES[p]: {c: (None if v != v else round(float(v), 1)) for c, v in r.items()}
                                      for p, r in d.test(T).set_index("province_code")[COND].iterrows()},
           "arms": {}}
    frames = {}
    for arm, pool in ARMS.items():
        raw, chosen_cfg, models = {}, {}, {}
        for t in alld:
            if t == T:
                fs, g = L6.operational_choice(d, Pr, pool)[0]
            else:
                fs, g = info["selections"][pool][C.qs(t + 1)]["chosen"].split("x")
            feats = L6.FEATURE_SETS[fs]
            tr, te = d.train(t), d.test(t)
            ptr, pte, m = X.lgbm_arrays(tr, te, feats, g)
            raw[t] = dict(zip(te["province_code"], pte))
            chosen_cfg[t] = L6.cfg_name(fs, g)
            models[t] = (m, feats, te, ptr, tr)
        if arm == "A0":                                    # reproduction check against the walk-forward arm
            s = Pr[Pr["arm"] == pool]
            res["A0_max_abs_diff_vs_walk_forward"] = float(max(abs(raw[C.qk(r.t)][r.province_code] - r.p) for r in s.itertuples()))
        cal, _fb, pa = R.calibrated(raw, labels_all, base, prior_of, "shrink")
        rows = [{"t": C.qs(t), "target_quarter": C.qs(t + 1), "province_code": c, "arm": arm, "p": cal[t][c],
                 "p_raw": raw[t][c], "y": labels[t][c]} for t in dates for c in PROVS]
        g = pd.DataFrame(rows)
        frames[arm] = g
        s = R.summary(g)
        pred = g["p"] >= 0.5
        tp, fp = int((pred & (g["y"] == 1)).sum()), int((pred & (g["y"] == 0)).sum())
        tn, n_low = int((~pred & (g["y"] == 0)).sum()), int((g["y"] == 0).sum())
        # attribution over the 65 test rows and at Q4 2026; split counts
        row_a, row_b, nz = [], [], {k: 0.0 for k in GROUPS}
        splits_q4, splits_all = {}, {c: 0 for c in COND}
        q4 = {}
        for t in alld:
            m, feats, te, ptr, tr = models[t]
            if m is None:
                continue
            imp = dict(zip(feats, m.booster_.feature_importance("split")))
            if t == T:
                splits_q4 = {f: int(imp.get(f, 0)) for f in COND + TRIG}
            else:
                for c in COND:
                    splits_all[c] += int(imp.get(c, 0))
            cc = L6.shap_contributions(m, te[feats])
            ev = float(cc["expected_value"].iloc[0])
            per, pool_mag, pool_other = {}, {k: 0.0 for k in GROUPS}, 0.0
            for i, code in enumerate(te["province_code"]):
                shap = cc.drop(columns="expected_value").iloc[i].to_dict()
                mag, other, direct = shares(E31, shap, code, C.qs(t))
                tot = sum(mag.values())
                a = {k: (v / tot * 100 if tot > 0 else 0.0) for k, v in mag.items()}
                b = {k: (v / (tot + other) * 100 if tot + other > 0 else 0.0) for k, v in mag.items()} | \
                    {"other": other / (tot + other) * 100 if tot + other > 0 else 0.0}
                if t != T:
                    row_a.append(a)
                    row_b.append(b)
                per[NAMES[code]] = {"a": dict(zip(GROUPS, X.integer_shares([mag[k] for k in GROUPS]))),
                                    "b": dict(zip(list(GROUPS) + ["other"], X.integer_shares([mag[k] for k in GROUPS] + [other]))),
                                    "direct": {k: round(v, 4) for k, v in direct.items()},
                                    "top_shap": {f: round(v, 3) for f, v in sorted(shap.items(), key=lambda kv: -abs(kv[1]))[:5]}}
                for k in GROUPS:
                    pool_mag[k] += mag[k]
                pool_other += other
            if t == T:
                q4 = {"CALABARZON": {"a": dict(zip(GROUPS, X.integer_shares([pool_mag[k] for k in GROUPS]))),
                                     "b": dict(zip(list(GROUPS) + ["other"], X.integer_shares([pool_mag[k] for k in GROUPS] + [pool_other])))},
                      **per, "shap_expected_value_logodds": ev}
        mean_a = {k: float(np.mean([r[k] for r in row_a])) for k in GROUPS}
        mean_b = {k: float(np.mean([r[k] for r in row_b])) for k in list(GROUPS) + ["other"]}
        m, feats, te, ptr, tr = models[T]
        o = {"pool_configs": {C.qs(t + 1): chosen_cfg[t] for t in alld},
             "metrics": {"accuracy": s["accuracy"], "accuracy_ci95": s["accuracy_ci95"],
                         "balanced_accuracy": s["balanced_accuracy"], "auc": s["auc"], "brier": s["brier"],
                         "log_loss": s["log_loss"], "precision": tp / (tp + fp) if tp + fp else None,
                         "LOW_caught": tn, "LOW_rows": n_low, "TP": tp, "FP": fp, "max_p": s["max_p"]},
             "train_Q4_origin": {"raw": X.train_metrics(ptr, tr["y"]),
                                 "calibrated": X.train_metrics(X.shrink(ptr, pa.get(T)), tr["y"])},
             "mean_five_driver_pct_65_rows": mean_a, "mean_pct_with_other_65_rows": mean_b,
             "drivers_nonzero": [k for k, v in mean_a.items() if v > 0.05],
             "splits_cond_Q4_model": splits_q4, "splits_cond_sum_13_test_models": splits_all,
             "q4_2026": {"index": {"CALABARZON": float(np.mean(list(cal[T].values()))), **{NAMES[c]: float(cal[T][c]) for c in PROVS}},
                         "drivers": q4},
             "index": {C.qs(t + 1): float(np.mean(list(cal[t].values()))) for t in alld},
             "shrink_params": {C.qs(t + 1): v for t, v in pa.items()}}
        res["arms"][arm] = o
    # tests vs A0, Holm over the two comparisons
    ok0 = ((frames["A0"]["p"] >= .5) == frames["A0"]["y"]).to_numpy()
    b0 = M.per_date_losses(frames["A0"])["bri"]
    mc, sf = {}, {}
    for arm in ("A1", "A2"):
        ok = ((frames[arm]["p"] >= .5) == frames[arm]["y"]).to_numpy()
        mc[arm] = EV.mcnemar_exact(ok, ok0)
        sf[arm] = EV.signflip_two((M.per_date_losses(frames[arm])["bri"] - b0).to_numpy())
        res["arms"][arm]["brier_diff_vs_A0"] = float((M.per_date_losses(frames[arm])["bri"] - b0).mean())
    hm, hs = holm({a: v["p_two_sided"] for a, v in mc.items()}), holm(sf)
    for arm in ("A1", "A2"):
        res["arms"][arm]["test_vs_A0"] = {"mcnemar": mc[arm], "mcnemar_p_holm": hm[arm],
                                          "signflip_brier_p": sf[arm], "signflip_brier_p_holm": hs[arm]}
    elig = []
    for arm, o in res["arms"].items():
        mt = o["metrics"]
        crit = {"balanced_accuracy_ge_0.83": mt["balanced_accuracy"] >= 0.83, "auc_ge_0.84": mt["auc"] >= 0.84,
                "brier_le_0.16": mt["brier"] <= 0.16, "LOW_caught_ge_10": mt["LOW_caught"] >= 10}
        o["adoption"] = {"criteria": crit, "eligible": all(crit.values())}
        if all(crit.values()):
            elig.append(arm)
    pick = (max(elig, key=lambda a: (len(res["arms"][a]["drivers_nonzero"]), res["arms"][a]["metrics"]["balanced_accuracy"],
                                     -res["arms"][a]["metrics"]["brier"])) if elig else None)
    res["adoption"] = {"eligible": elig, "preferred": pick or "none eligible"}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E53 / "runs" / stamp
    run.mkdir(parents=True)
    pd.concat(frames.values()).to_csv(run / "predictions.csv", index=False, float_format="%.10g")
    res["run"] = stamp
    C.write_json(E53 / "E53_results.json", C.clean(res))
    print("RUN", stamp, "A0 check", res["A0_max_abs_diff_vs_walk_forward"], "eligible", elig, "preferred", res["adoption"]["preferred"])


if __name__ == "__main__":
    main()

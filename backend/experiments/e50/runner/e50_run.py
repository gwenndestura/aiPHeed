"""E50: fix the overfitting of the served model (lead 1, current trailing-median labels). Experiment only.

    python -B backend/experiments/e50/runner/e50_run.py  -> backend/experiments/e50/E50_results.json

Everything is E36's walk-forward (origins, training rows, nested rule = lowest mean per-date Brier on eligible prior
dates, tie 0.002 -> simpler, seed 36, threshold 0.5) on the 65 test rows (13 dates x 5 provinces).

Arms
  R0  E49-C2 as served: pool E48-T5 (COMPACT_T5/COMB_T5 x G1/G4/G3/G2) + C2 shrinkage (must reproduce acc 0.846,
      Brier 0.151, Q4 2026 CALABARZON 0.778)
  R1  COMB_T5 (E48-A1 features), regularised LightGBM; pool num_leaves {2,4} x min_data_in_leaf {15,10} x
      lambda_l2 {5,1} (listed simplest first: fewer leaves, more rows per leaf, heavier L2), otherwise G2's settings
      (150 trees, learning rate 0.05, colsample 0.8); monotone +1 on Dnow, D_last, H_last, y_last; nested rule
  R2  R1 without the inert inputs (trig_market, trig_employment, trig_ofw_remittance, trig_fish_kill)
  R3  B3 government logistic regression alone (E36's B3_LR_GOV, unchanged)
  R4  paper blend (Chapter 3, Stage 4): 0.4 x R1 + 0.4 x B3 + 0.2 x LR on trig_climate, trig_fish_kill,
      trig_ofw_remittance (inputs constant in that origin's training rows are dropped; all constant -> Laplace rate)
  R1, R2, R4 get E49-C2 shrinkage p' = a*p + (1-a)*base_rate with a in {0,.05,..,1} chosen by lowest Brier on the
  EARLIER eligible dates only (a = 1 = no shrinkage, chosen whenever shrinking does not lower that Brier; raw p when
  fewer than 3 earlier dates). The raw (unshrunk) metrics are reported as well.

Attribution at Q4 2026: TreeSHAP (LightGBM); linear SHAP coef*z for the LR (standardised inputs, training mean 0);
R4 = 0.4/0.4/0.2-weighted component attributions in each component's log-odds (approximate: a probability blend
has no exact additive log-odds decomposition). Driver shares use the live panel method (the live engine file loaded
by path): (a) normalised over the five drivers, (b) with "Other model inputs" in the denominator.

ADOPTION (fixed before results): acceptable only if ALL of AUC >= 0.80; balanced accuracy >= 0.83; Brier <= 0.151;
log loss <= 0.489; training accuracy at the Q4 2026 origin <= 0.95; no test p >= 0.99 (65 rows). Several pass ->
lowest Brier; a tie (Brier within 0.002, E36's tie tolerance) -> R4 (paper). None passes -> keep E49-C2.
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E50 = Path(__file__).resolve().parents[1]
BACKEND = E50.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e49" / "runner"))
import e49_run as R  # noqa: E402  (E49 calibration helpers; brings in e48_lib / e36_lib)

L, L6, C, np, pd, M = R.L, R.L6, R.C, R.np, R.pd, R.M
L6.guard32.EXP = E50
NAMES, PROVS = R.NAMES, L.PROVS
INERT = ["trig_market", "trig_employment", "trig_ofw_remittance", "trig_fish_kill"]
MONO = {"Dnow", "D_last", "H_last", "y_last"}
TRIG_LR = ["trig_climate", "trig_fish_kill", "trig_ofw_remittance"]
TIE = 0.002
ADOPT = dict(auc=0.80, balanced_accuracy=0.83, brier=0.151, log_loss=0.489, train_accuracy=0.95, max_test_p=0.99)


def register():
    R.register()                                             # E48-T5 (+ E49-REG) pools
    L6.FEATURE_SETS["E50_R2"] = [f for f in L6.FEATURE_SETS["COMB_T5"] if f not in INERT]
    for arm, fs in (("R1", "COMB_T5"), ("R2", "E50_R2")):
        feats = L6.FEATURE_SETS[fs]
        mono = [1 if f in MONO else 0 for f in feats]
        pool = []
        for nl in (2, 4):
            for mdl in (15, 10):
                for lam in (5.0, 1.0):
                    g = f"{arm}n{nl}m{mdl}l{int(lam)}"
                    L6.GRID[g] = dict(num_leaves=nl, max_depth=-1, min_data_in_leaf=mdl, n_estimators=150,
                                      learning_rate=0.05, reg_lambda=lam, colsample_bytree=0.8,
                                      monotone_constraints=mono)
                    pool.append((fs, g))
        L6.POOLS[f"E50-{arm}"] = (pool, pool[0])


# ------------------------------------------------------------------ fitting helpers returning train + test arrays
def lgbm_arrays(tr, te, feats, g):
    m = L6.fit_lgbm(tr, feats, g)
    if m is None:
        r = (tr["y"].sum() + 1) / (len(tr) + 2)
        return np.full(len(tr), r), np.full(len(te), r), None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (m.predict_proba(tr[feats].astype(float))[:, 1], m.predict_proba(te[feats].astype(float))[:, 1], m)


def lr_arrays(tr, te, feats):
    """Same estimator as e36_lib.lr_predict (StandardScaler + LogisticRegression(C=1)), returning train and test p and
    the linear SHAP (coef * z) of the test rows. Inputs constant in the training rows are dropped."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    y = tr["y"].to_numpy(int)
    feats = [f for f in feats if tr[f].astype(float).nunique(dropna=True) > 1]
    if len(set(y)) < 2 or not feats:
        r = (y.sum() + 1) / (len(y) + 2)
        return np.full(len(tr), r), np.full(len(te), r), {"features": feats, "intercept": math.log(r / (1 - r)),
                                                          "shap": [{} for _ in range(len(te))]}
    sc = StandardScaler().fit(tr[feats].to_numpy(float))
    Z = np.nan_to_num(sc.transform(tr[feats].to_numpy(float)), nan=0.0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = LogisticRegression(C=1.0, max_iter=5000).fit(Z, y)
    Zt = np.nan_to_num(sc.transform(te[feats].to_numpy(float)), nan=0.0)
    coef = m.coef_[0]
    shap = [dict(zip(feats, coef * (z - Z.mean(axis=0)))) for z in Zt]
    ev = float(m.intercept_[0] + coef @ Z.mean(axis=0))
    return m.predict_proba(Z)[:, 1], m.predict_proba(Zt)[:, 1], {"features": feats, "intercept": ev, "shap": shap}


def train_metrics(p, y):
    p = np.clip(np.asarray(p, float), 1e-15, 1 - 1e-15)
    y = np.asarray(y, int)
    return {"accuracy": float(((p >= 0.5) == y).mean()), "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "n_p_ge_0.99": int((p >= 0.99).sum()), "mean_p": float(p.mean())}


def shrink(p, prm):
    return p if prm is None else prm["a"] * np.asarray(p) + (1 - prm["a"]) * prm["base_rate"]


# ------------------------------------------------------------------ live panel method
def live_engine():
    spec = importlib.util.spec_from_file_location("live_e31_engine", BACKEND / "app" / "ml" / "inference" / "e31_engine.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def integer_shares(values):                                  # app/services/dashboard._integer_shares
    total = sum(values)
    if total <= 0:
        return [0] * len(values)
    exact = [v / total * 100 for v in values]
    floors = [int(x) for x in exact]
    for i in sorted(range(len(exact)), key=lambda i: exact[i] - floors[i], reverse=True)[:100 - sum(floors)]:
        floors[i] += 1
    return floors


def panel(E31, shap_by_prov: dict, ev_q: str) -> dict:
    """shap_by_prov[code] = {feature: log-odds SHAP}. Returns (a) five-driver and (b) with-Other shares, per province
    and pooled for CALABARZON, exactly as e31_engine.five_trigger_drivers + dashboard.explainability(_region)."""
    groups = list(E31.TRIGGER_GROUP_FEATURES)
    grouped = {f for fs in E31.TRIGGER_GROUP_FEATURES.values() for f in fs}
    pool, pool_other, out = {g: 0.0 for g in groups}, 0.0, {}
    for code, shap in shap_by_prov.items():
        mag = {g: abs(sum(shap.get(f, 0.0) for f in fs)) for g, fs in E31.TRIGGER_GROUP_FEATURES.items()}
        direct = dict(mag)
        assigned = 0.0
        for level, nf in E31.NEWS_FEATURES.items():
            sh, _ = E31.news_topic_shares(code if level == "province" else None, ev_q)
            a = sum(abs(shap.get(f, 0.0)) for f in nf)
            for g, w in sh.items():
                mag[g] += w * a
                assigned += w * a
        other = sum(abs(v) for f, v in shap.items() if f not in grouped) - assigned
        out[NAMES[code]] = {"a": dict(zip(groups, integer_shares([mag[g] for g in groups]))),
                            "b": dict(zip(groups + ["other"], integer_shares([mag[g] for g in groups] + [other]))),
                            "direct": {g: round(direct[g], 4) for g in groups},
                            "news_allocated": {g: round(mag[g] - direct[g], 4) for g in groups},
                            "other_abs": round(other, 4)}
        for g in groups:
            pool[g] += mag[g]
        pool_other += other
    out["CALABARZON"] = {"a": dict(zip(groups, integer_shares([pool[g] for g in groups]))),
                         "b": dict(zip(groups + ["other"], integer_shares([pool[g] for g in groups] + [pool_other])))}
    return out


# ------------------------------------------------------------------ main
def main():
    os.chdir(BACKEND)                                        # the live engine's record/news paths are relative
    register()
    d = L.Data(paper=False)
    Pr, info = L6.walk_forward(d)
    dates = [C.qk(q) - 1 for q in info["dates"]]
    T = L6.OPERATIONAL_T
    alld = dates + [T]
    labels = {t: {c: int(d.label(c, t + 1, t)) for c in PROVS} for t in dates}
    labels_all = {**labels, T: {c: 0 for c in PROVS}}       # T's labels are never used (it is never a prior date)
    base = {t: float((d.train(t)["y"].sum() + 1) / (len(d.train(t)) + 2)) for t in alld}
    prior_of = {t: L6.eligible_prior_dates(d, t, dates) for t in alld}

    def chosen(pool, t):
        if t == T:
            return L6.operational_choice(d, Pr, pool)[0]
        fs, g = info["selections"][pool][C.qs(t + 1)]["chosen"].split("x")
        return fs, g

    # raw predictions, training predictions and the fitted Q4 models for every arm, at every origin
    raw = {a: {} for a in ("R0", "R1", "R2", "R3", "R4")}
    trn = {a: {} for a in raw}                               # trn[arm][t] = training p (raw)
    cfg = {a: {} for a in raw}
    q4 = {}
    for t in alld:
        tr, te = d.train(t), d.test(t)
        codes = list(te["province_code"])
        for arm, pool in (("R0", "E48-T5"), ("R1", "E50-R1"), ("R2", "E50-R2")):
            fs, g = chosen(pool, t)
            ptr, pte, m = lgbm_arrays(tr, te, L6.FEATURE_SETS[fs], g)
            raw[arm][t], trn[arm][t], cfg[arm][t] = dict(zip(codes, pte)), ptr, L6.cfg_name(fs, g)
            if t == T:
                q4[arm] = {"model": m, "features": L6.FEATURE_SETS[fs], "te": te}
        ptr3, pte3, lr3 = lr_arrays(tr, te, L6.GOV)
        ptrT, pteT, lrT = lr_arrays(tr, te, TRIG_LR)
        raw["R3"][t], trn["R3"][t], cfg["R3"][t] = dict(zip(codes, pte3)), ptr3, "B3_LR_GOV"
        raw["R4"][t] = {c: 0.4 * raw["R1"][t][c] + 0.4 * raw["R3"][t][c] + 0.2 * p for c, p in zip(codes, pteT)}
        trn["R4"][t] = 0.4 * trn["R1"][t] + 0.4 * ptr3 + 0.2 * ptrT
        cfg["R4"][t] = f"0.4*{cfg['R1'][t]} + 0.4*B3 + 0.2*LR{lrT['features']}"
        if t == T:
            q4["R3"], q4["R4_trig"] = {"lr": lr3, "te": te}, {"lr": lrT}
    # consistency: R0 raw = the walk-forward E48-T5 arm; R3 = B3_LR_GOV
    chk = {}
    for arm, wf in (("R0", "E48-T5"), ("R3", "B3_LR_GOV")):
        s = Pr[Pr["arm"] == wf]
        chk[arm] = float(max(abs(raw[arm][C.qk(r.t)][r.province_code] - r.p) for r in s.itertuples()))

    # calibration (shrinkage fitted on earlier dates only) for R0, R1, R2, R4; R3 stays raw
    final, params = {}, {}
    for arm in raw:
        if arm == "R3":
            final[arm], params[arm] = raw[arm], {}
            continue
        cal, _fb, pa = R.calibrated(raw[arm], labels_all, base, prior_of, "shrink")
        final[arm], params[arm] = cal, pa
    rows = []
    for arm in raw:
        for t in dates:
            for c in PROVS:
                rows.append({"t": C.qs(t), "target_quarter": C.qs(t + 1), "province_code": c, "arm": arm,
                             "p": final[arm][t][c], "p_raw": raw[arm][t][c], "y": labels[t][c]})
    df = pd.DataFrame(rows)

    res = {"lead": 1, "test_quarters": info["dates"], "n_test_rows": int(len(df) / len(raw)),
           "consistency_max_abs_diff": chk, "arms": {}}
    wrong0 = {(r.target_quarter, NAMES[r.province_code]) for r in df[df["arm"] == "R0"].itertuples() if (r.p >= 0.5) != r.y}
    E31 = live_engine()
    ev_q = C.qs(T)
    for arm in raw:
        g = df[df["arm"] == arm]
        s = R.summary(g)
        sr = R.summary(g.assign(p=g["p_raw"]))
        trT = d.train(T)
        tm_T = train_metrics(shrink(trn[arm][T], params[arm].get(T)), trT["y"])
        tm_T_raw = train_metrics(trn[arm][T], trT["y"])
        tm_all = [train_metrics(shrink(trn[arm][t], params[arm].get(t)), d.train(t)["y"]) for t in dates]
        wrong = {(r.target_quarter, NAMES[r.province_code]) for r in g.itertuples() if (r.p >= 0.5) != r.y}
        # attribution at Q4 2026
        if arm in ("R0", "R1", "R2"):
            m, feats, te = q4[arm]["model"], q4[arm]["features"], q4[arm]["te"]
            if m is None:
                shap, evlog = {c: {} for c in te["province_code"]}, None
            else:
                cc = L6.shap_contributions(m, te[feats])
                evlog = float(cc["expected_value"].iloc[0])
                shap = {c: cc.drop(columns="expected_value").iloc[i].to_dict() for i, c in enumerate(te["province_code"])}
        elif arm == "R3":
            lr, te = q4["R3"]["lr"], q4["R3"]["te"]
            shap = {c: lr["shap"][i] for i, c in enumerate(te["province_code"])}
            evlog = lr["intercept"]
        else:                                                # R4: weighted component attributions (approximate)
            te = q4["R1"]["te"]
            cc = L6.shap_contributions(q4["R1"]["model"], te[q4["R1"]["features"]])
            ev1 = float(cc["expected_value"].iloc[0])
            shap = {}
            for i, c in enumerate(te["province_code"]):
                s1 = cc.drop(columns="expected_value").iloc[i].to_dict()
                acc = {f: 0.4 * v for f, v in s1.items()}
                for f, v in q4["R3"]["lr"]["shap"][i].items():
                    acc[f] = acc.get(f, 0.0) + 0.4 * v
                for f, v in q4["R4_trig"]["lr"]["shap"][i].items():
                    acc[f] = acc.get(f, 0.0) + 0.2 * v
                shap[c] = acc
            evlog = 0.4 * ev1 + 0.4 * q4["R3"]["lr"]["intercept"] + 0.2 * q4["R4_trig"]["lr"]["intercept"]
        q4p = final[arm][T]
        o = {"metrics": {k: s[k] for k in ("accuracy", "accuracy_ci95", "balanced_accuracy", "auc", "brier", "log_loss",
                                            "ece_3bin", "max_p", "mean_p", "reliability_5bin", "confident_mistakes")},
             "metrics_raw": {k: sr[k] for k in ("accuracy", "balanced_accuracy", "auc", "brier", "log_loss", "max_p")},
             "n_test_p_ge_0.95": int((g["p"] >= 0.95).sum()), "n_test_p_le_0.05": int((g["p"] <= 0.05).sum()),
             "n_test_p_ge_0.99": int((g["p"] >= 0.99).sum()),
             "train_Q4_origin": tm_T, "train_Q4_origin_raw": tm_T_raw,
             "train_mean_over_origins": {k: float(np.mean([x[k] for x in tm_all])) for k in ("accuracy", "log_loss")},
             "train_label_rate_Q4_origin": float(trT["y"].mean()),
             "shap_expected_value_logodds": evlog,
             "shap_expected_value_p": (None if evlog is None else 1 / (1 + math.exp(-evlog))),
             "configs": {C.qs(t + 1): cfg[arm][t] for t in alld},
             "shrink_params": {C.qs(t + 1): v for t, v in params[arm].items()},
             "index": {C.qs(t + 1): {"CALABARZON": float(np.mean(list(final[arm][t].values()))),
                                     **{NAMES[c]: float(final[arm][t][c]) for c in PROVS}} for t in alld},
             "q4_2026": {"CALABARZON": float(np.mean(list(q4p.values()))), **{NAMES[c]: float(q4p[c]) for c in PROVS},
                         "raw": {NAMES[c]: float(raw[arm][T][c]) for c in PROVS}},
             "R0_disagreements_fixed": sorted(wrong0 - wrong), "R0_disagreements_kept": sorted(wrong0 & wrong),
             "new_disagreements": sorted(wrong - wrong0), "n_wrong": len(wrong),
             "drivers_q4_2026": panel(E31, shap, ev_q),
             "q4_shap_logodds": {NAMES[c]: {f: round(v, 4) for f, v in sorted(s_.items(), key=lambda kv: -abs(kv[1]))}
                                 for c, s_ in shap.items()}}
        crit = {"auc_ge_0.80": (o["metrics"]["auc"] or 0) >= ADOPT["auc"],
                "balanced_accuracy_ge_0.83": (o["metrics"]["balanced_accuracy"] or 0) >= ADOPT["balanced_accuracy"],
                "brier_le_0.151": o["metrics"]["brier"] <= ADOPT["brier"],
                "log_loss_le_0.489": o["metrics"]["log_loss"] <= ADOPT["log_loss"],
                "train_accuracy_le_0.95": tm_T["accuracy"] <= ADOPT["train_accuracy"],
                "no_test_p_ge_0.99": o["n_test_p_ge_0.99"] == 0}
        o["adoption"] = {"criteria": crit, "acceptable": all(crit.values())}
        res["arms"][arm] = o
    res["R0_disagreements"] = sorted(wrong0)
    ok = [a for a, o in res["arms"].items() if o["adoption"]["acceptable"]]
    pick = None
    if ok:
        best = min(res["arms"][a]["metrics"]["brier"] for a in ok)
        near = [a for a in ok if res["arms"][a]["metrics"]["brier"] <= best + TIE]
        pick = "R4" if "R4" in near and len(near) > 1 else min(near, key=lambda a: res["arms"][a]["metrics"]["brier"])
    res["adoption"] = {"acceptable": ok, "chosen": pick or "keep E49-C2 (R0)", "rule": ADOPT, "tie": TIE}
    res["observed_share_HIGH"] = {C.qs(t + 1): float(np.mean(list(labels[t].values()))) for t in dates}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E50 / "runs" / stamp
    run.mkdir(parents=True)
    df.to_csv(run / "predictions.csv", index=False, float_format="%.10g")
    res["run"] = stamp
    C.write_json(E50 / "E50_results.json", C.clean(res))
    print("RUN", stamp, "acceptable", ok, "chosen", res["adoption"]["chosen"], "consistency", chk)


if __name__ == "__main__":
    main()

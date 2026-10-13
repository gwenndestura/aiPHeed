"""
E9 runner: S1 targets, guarded allowlist-only inputs, walk-forward comparison of baselines and LightGBM.
Run from C:\\Users\\admin\\aipheed\\aipheed-backend-aligned with:  python -B <this file>
Protocol: ../03_FROZEN_PROTOCOL.md (must exist; its SHA-256 is recorded).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard  # noqa: E402

guard.install()                                     # before ANY project import

import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import warnings  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(guard.AL))
import scripts.supplementary.devprotocol_rule_l as D  # noqa: E402
from app.ml.features import risk_score_v2 as R  # noqa: E402

import metrics as M  # noqa: E402
import safe_frame as F  # noqa: E402
from vault import Stop, Vault, sha_file  # noqa: E402

warnings.filterwarnings("ignore")
EXP = guard.EXP
PROTOCOL = EXP / "03_FROZEN_PROTOCOL.md"
TAU0_RECORDED = 10.84335
AS_OF = pd.Timestamp("2023-10-01")
MIN_TRAIN_Q = 8
SELECTION_END = "2024-Q4"
PARAMS = dict(num_leaves=4, min_child_samples=5, n_estimators=100, learning_rate=0.05, random_state=42, verbosity=-1)
MONO_UP = {"last_published_stress", "sws_hunger"}
REQUIRED = ["last_published_stress", "sws_hunger", "cpi_rel", "food_cpi_yoy"]
CORE = ["last_published_stress", "sws_hunger", "sws_change"]
COMPACT = CORE + ["cpi_rel", "cpi_rel_lag1", "food_cpi_yoy", "food_cpi_yoy_lag1", "cpi_dev"]
EXPANDED = COMPACT + ["poverty_incidence", "headline_cpi", "food_minus_headline_yoy",
                      "food_minus_headline_yoy_lag1", "unemployment_rate"]
ML_ARMS = {"M1_core": CORE, "M2_compact": COMPACT, "M3_expanded": EXPANDED}
STRESS_ORDER = ["B1_carry_forward", "B2_regional", "B3_eq3_rule", "M1_core", "M2_compact", "M3_expanded"]
CODE_FILES = ["app/ml/features/risk_score_v2.py", "scripts/supplementary/devprotocol_rule_l.py",
              "scripts/supplementary/timing_audit.py", "app/ml/corpus/sws_hunger_fetcher.py"]


# ---------------------------------------------------------------- fold logic
def reasons_for(row) -> list[str]:
    r = [f"missing input: {c}" for c in REQUIRED if pd.isna(row.get(c))]
    if pd.notna(row.get("sws_age")) and row["sws_age"] > R.SWS_MAX_AGE_QUARTERS:
        r.append(f"stale SWS input ({int(row['sws_age'])} quarters)")
    return r


def train_filter(X: pd.DataFrame) -> tuple[list[str], list[str]]:
    keep, drop = [], []
    for c in X.columns:
        x = X[c]
        (drop if x.isna().mean() > 0.5 or x.dropna().nunique() < 2 else keep).append(c)
    return keep, drop


def fit_clf(X, y):
    from lightgbm import LGBMClassifier
    return LGBMClassifier(objective="binary", **PARAMS,
                          monotone_constraints=[1 if c in MONO_UP else 0 for c in X.columns]).fit(X, y)


def fit_reg(X, y):
    from lightgbm import LGBMRegressor
    return LGBMRegressor(objective="regression", **PARAMS,
                         monotone_constraints=[1 if c in MONO_UP else 0 for c in X.columns]).fit(X, y)


def calibration(tr: pd.DataFrame, feats: list[str], y: np.ndarray, tq: list[str]) -> dict:
    oof = []
    for i in range(MIN_TRAIN_Q, len(tq)):
        m_tr = tr["target_quarter"].isin(tq[:i]).values
        m_te = (tr["target_quarter"] == tq[i]).values
        if len(set(y[m_tr])) < 2:
            continue
        mdl = fit_clf(tr.loc[m_tr, feats], y[m_tr])
        oof.append(pd.DataFrame({"q": tq[i], "p": mdl.predict_proba(tr.loc[m_te, feats])[:, 1], "y": y[m_te]}))
    if not oof:
        return {"applied": False, "oof_quarters": 0, "reason": "no inner out-of-fold quarters"}
    o = pd.concat(oof)
    nq, npos, nneg = o["q"].nunique(), int(o["y"].sum()), int((o["y"] == 0).sum())
    ok = nq >= 8 and min(npos, nneg) >= 10
    out = {"applied": bool(ok), "oof_quarters": int(nq), "oof_high": npos, "oof_low": nneg,
           "reason": "sufficient inner evidence" if ok else "insufficient inner evidence (need >= 8 quarters, >= 10 per class)"}
    if ok:
        from sklearn.linear_model import LogisticRegression
        lg = np.log(np.clip(o["p"], 1e-6, 1 - 1e-6) / (1 - np.clip(o["p"], 1e-6, 1 - 1e-6)))
        out["_platt"] = LogisticRegression().fit(lg.values.reshape(-1, 1), o["y"].values)
    return out


def predict_all(frame: pd.DataFrame, stress: pd.DataFrame, vault: Vault, published, tau0: float,
                tests: list[str]) -> tuple[pd.DataFrame, list[dict]]:
    preds, folds = [], []
    for T in tests:
        tq = F.eligible_training_quarters(stress, T, published)
        te = frame[frame["target_quarter"] == T].sort_values("province_code").reset_index(drop=True)
        rs = [reasons_for(r) for _, r in te.iterrows()]
        fold = {"target": T, "n_train_quarters": len(tq), "train_quarters": tq}
        if len(tq) < MIN_TRAIN_Q:
            rs = [r + [f"training history {len(tq)} quarters (< {MIN_TRAIN_Q})"] for r in rs]
        lab = vault.train(tq, T)
        tr = frame[frame["target_quarter"].isin(tq)].merge(
            lab, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"], how="inner")
        y = (tr["stress"] > tau0).astype(int).values
        fold.update({"n_train_rows": int(len(tr)), "train_HIGH": int(y.sum()), "train_LOW": int((y == 0).sum())})

        def base(arm, kind):
            d = te[["province_code", "target_quarter"]].copy()
            d["arm"], d["kind"] = arm, kind
            d["insufficient_reasons"] = ["; ".join(r) for r in rs]
            return d

        # baselines
        for arm, s in (("B1_carry_forward", te["last_published_stress"]), ("B2_regional", te["sws_hunger"]),
                       ("B3_eq3_rule", te["sws_hunger"] + 2.0 * te["cpi_rel"])):
            d = base(arm, "stress")
            d["stress_pred"] = s.values
            d["probability"] = np.nan
            preds.append(d)
        d = base("B4_majority", "class_only")
        d["stress_pred"] = np.nan
        d["probability"] = np.nan
        d["majority"] = "HIGH" if y.sum() * 2 >= len(y) else "LOW"
        preds.append(d)

        # LightGBM arms
        fold["arms"] = {}
        for arm, feats in ML_ARMS.items():
            keep, drop = train_filter(tr[feats])
            info = {"features_used": keep, "features_dropped_training_filter": drop}
            dc, dr = base(arm, "probability"), base(arm, "stress")
            dc["stress_pred"], dr["probability"] = np.nan, np.nan
            if len(tq) < MIN_TRAIN_Q or not keep:
                dc["probability"], dr["stress_pred"] = np.nan, np.nan
            else:
                reg = fit_reg(tr[keep], tr["stress"].values)
                dr["stress_pred"] = reg.predict(te[keep])
                info["regressor_train_mae"] = float(np.mean(np.abs(reg.predict(tr[keep]) - tr["stress"].values)))
                info["regressor_gain"] = dict(zip(keep, map(float, reg.booster_.feature_importance("gain"))))
                if len(set(y)) < 2:
                    dc["probability"] = np.nan
                    dc["insufficient_reasons"] = [s + ("; " if s else "") + "training labels one class" for s in dc["insufficient_reasons"]]
                else:
                    clf = fit_clf(tr[keep], y)
                    p_raw = clf.predict_proba(te[keep])[:, 1]
                    cal = calibration(tr, keep, y, tq)
                    if cal.get("applied"):
                        lg = np.log(np.clip(p_raw, 1e-6, 1 - 1e-6) / (1 - np.clip(p_raw, 1e-6, 1 - 1e-6)))
                        p = cal.pop("_platt").predict_proba(lg.reshape(-1, 1))[:, 1]
                    else:
                        p = p_raw
                    dc["probability_raw"], dc["probability"] = p_raw, p
                    info["calibration"] = cal
                    info["classifier_train_brier"] = float(np.mean((clf.predict_proba(tr[keep])[:, 1] - y) ** 2))
                    info["classifier_gain"] = dict(zip(keep, map(float, clf.booster_.feature_importance("gain"))))
            fold["arms"][arm] = info
            preds += [dc, dr]
        folds.append(fold)
    P = pd.concat(preds, ignore_index=True)

    # classification per row (identical INSUFFICIENT rules for every arm)
    def cls(r):
        if r["insufficient_reasons"]:
            return R.INSUFFICIENT_DATA
        if r["kind"] == "probability":
            return R.final_classification(r["probability"], [])
        if r["kind"] == "class_only":
            return r["majority"]
        v = r["stress_pred"]
        return R.INSUFFICIENT_DATA if pd.isna(v) else (R.HIGH if v > tau0 else R.LOW)
    P["classification"] = P.apply(cls, axis=1)
    P.loc[(P["kind"] == "probability") & (P["classification"] == R.INSUFFICIENT_DATA), "probability"] = np.nan
    return P, folds


# ---------------------------------------------------------------- scoring
def score(P: pd.DataFrame, truth: pd.DataFrame, tau0: float, tests: list[str]) -> dict:
    t = truth.rename(columns={"quarter": "target_quarter", "stress": "stress_true"})
    S = P.merge(t, on=["target_quarter", "province_code"], how="left")
    if S["stress_true"].isna().any():
        raise Stop("missing truth for a test row")
    S["event_true"] = S["stress_true"] > tau0
    # common evaluable rows: no arm INSUFFICIENT for that province-quarter
    bad = S[S["classification"] == R.INSUFFICIENT_DATA][["target_quarter", "province_code"]].drop_duplicates()
    key = S[["target_quarter", "province_code"]].apply(tuple, axis=1)
    S["common_evaluable"] = ~key.isin(set(map(tuple, bad.values)))
    sel = [q for q in tests if F.qi(q) <= F.qi(SELECTION_END)]
    fin = [q for q in tests if F.qi(q) > F.qi(SELECTION_END)]
    out = {"periods": {"selection": sel, "final": fin, "all": tests}, "arms": {}}
    for (arm, kind), g in S[S["common_evaluable"]].groupby(["arm", "kind"]):
        res = {}
        for pname, qs_ in out["periods"].items():
            h = g[g["target_quarter"].isin(qs_)]
            if h.empty:
                continue
            r = {"rows": int(len(h)), "quarters": int(h["target_quarter"].nunique()),
                 "classification": M.classification(h["event_true"].values, (h["classification"] == R.HIGH).values)}
            if kind == "probability":
                r["brier"] = M.brier(h["event_true"].values, h["probability"].values)
                r["auc"] = M.ranking_auc(h["event_true"].values, h["probability"].values)
                r["mean_probability"] = float(h["probability"].mean())
            if kind == "stress":
                r["stress"] = M.stress_errors(h.rename(columns={})[["target_quarter", "province_code", "stress_pred", "stress_true"]])
                r["auc_of_stress_score"] = M.ranking_auc(h["event_true"].values, h["stress_pred"].values)
            per_q_acc = {q: float(((x["classification"] == R.HIGH) == x["event_true"]).mean())
                         for q, x in h.groupby("target_quarter")}
            r["per_quarter_accuracy"] = per_q_acc
            res[pname] = r
        out["arms"][f"{arm}|{kind}"] = res
    # per-province (all test quarters)
    prov = []
    for (arm, kind), g in S[S["common_evaluable"]].groupby(["arm", "kind"]):
        for p, h in g.groupby("province_code"):
            d = {"arm": arm, "kind": kind, "province_code": p, "rows": int(len(h)),
                 "accuracy": float(((h["classification"] == R.HIGH) == h["event_true"]).mean())}
            if kind == "stress":
                d["mae"] = float((h["stress_pred"] - h["stress_true"]).abs().mean())
            prov.append(d)
    out["per_province"] = prov
    out["n_common_rows"] = int(S[S["common_evaluable"]][["target_quarter", "province_code"]].drop_duplicates().shape[0])
    out["insufficient_rows"] = S[S["classification"] == R.INSUFFICIENT_DATA][
        ["arm", "kind", "target_quarter", "province_code", "insufficient_reasons"]].to_dict("records")
    return out, S


def select(scores: dict, S: pd.DataFrame, tests: list[str]) -> dict:
    sel = [q for q in tests if F.qi(q) <= F.qi(SELECTION_END)]
    C = S[S["common_evaluable"] & (S["kind"] == "stress") & S["target_quarter"].isin(sel)]
    perq = {a: g.groupby("target_quarter").apply(lambda x: (x["stress_pred"] - x["stress_true"]).abs().mean()).to_dict()
            for a, g in C.groupby("arm")}
    mae = {a: float(np.mean(list(v.values()))) for a, v in perq.items()}
    cur, trail = "B1_carry_forward", []
    for a in STRESS_ORDER[1:]:
        wins = sum(perq[a][q] < perq[cur][q] for q in sel)
        ok = mae[a] <= 0.90 * mae[cur] and wins >= 3
        trail.append({"candidate": a, "vs": cur, "mae_candidate": mae[a], "mae_current": mae[cur],
                      "ratio": mae[a] / mae[cur], "quarters_better": int(wins), "moved": bool(ok)})
        if ok:
            cur = a
    return {"rule": "simplest stress arm; move only if MAE <= 0.90x current and better in >= 3 of 5 selection quarters",
            "selection_quarters": sel, "selection_mae": mae, "trail": trail, "selected": cur}


# ---------------------------------------------------------------- diagnostics
def diagnostics(stress: pd.DataFrame, tests: list[str], published, tau0: float, S: pd.DataFrame, folds: list[dict]) -> dict:
    st = stress.copy()
    st["year"] = st["quarter"].str[:4]
    st["HIGH"] = st["stress"] > tau0
    st["regional_only_HIGH"] = st["sws_hunger_pct"] > tau0
    by_year = st.groupby("year").agg(rows=("HIGH", "size"), HIGH=("HIGH", "sum")).reset_index()
    comp = {"var_total": float(st["stress"].var()), "var_regional": float(st["sws_hunger_pct"].var()),
            "var_provincial_2d": float((2 * st["deviation"]).var())}
    alpha = []
    for a in (0.0, 1.0, 2.0, 2.74, 4.0):
        s_a = st.assign(stress=st["sws_hunger_pct"] + a * st["deviation"])
        tau_a, used = R.reference_threshold(s_a[["province_code", "quarter", "stress"]], published, AS_OF)
        tt = s_a[s_a["quarter"].isin(tests)]
        alpha.append({"alpha": a, "tau_as_of_2023_10_01": tau_a, "test_rows": int(len(tt)),
                      "test_HIGH": int((tt["stress"] > tau_a).sum())})
    share = []
    for (arm, kind), g in S[S["common_evaluable"]].groupby(["arm", "kind"]):
        for q, h in g.groupby("target_quarter"):
            share.append({"arm": arm, "kind": kind, "quarter": q, "pred_HIGH": int((h["classification"] == R.HIGH).sum()),
                          "true_HIGH": int(h["event_true"].sum()), "rows": int(len(h)),
                          "mean_probability": float(h["probability"].mean()) if kind == "probability" else None})
    stab = {}
    for arm in ("M2_compact", "M3_expanded"):
        tops = []
        for f in folds:
            g = f["arms"][arm].get("regressor_gain")
            if g:
                tops.append([k for k, _ in sorted(g.items(), key=lambda kv: -kv[1])[:3]])
        jac = [len(set(a) & set(b)) / len(set(a) | set(b)) for i, a in enumerate(tops) for b in tops[i + 1:]]
        stab[arm] = {"top3_by_fold": tops, "mean_pairwise_jaccard_top3": float(np.mean(jac)) if jac else None}
    overfit = []
    for f in folds:
        for arm in ML_ARMS:
            tr_mae = f["arms"][arm].get("regressor_train_mae")
            h = S[(S["arm"] == arm) & (S["kind"] == "stress") & (S["target_quarter"] == f["target"]) & S["common_evaluable"]]
            if tr_mae is not None and len(h):
                overfit.append({"target": f["target"], "arm": arm, "train_mae": tr_mae,
                                "test_mae": float((h["stress_pred"] - h["stress_true"]).abs().mean())})
    return {"label_distribution_by_year_tau0": by_year.to_dict("records"),
            "regional_only_agreement_share": float((st["HIGH"] == st["regional_only_HIGH"]).mean()),
            "variance_components": comp, "alpha_sensitivity": alpha, "pred_vs_true_HIGH": share,
            "importance_stability": stab, "train_vs_test_mae": overfit}


# ---------------------------------------------------------------- main
def main() -> None:
    if not PROTOCOL.exists():
        raise Stop("frozen protocol missing")
    started = datetime.now(timezone.utc)
    run = EXP / "runs" / started.strftime("%Y%m%dT%H%M%SZ")
    run.mkdir(parents=True, exist_ok=False)
    import lightgbm, sklearn, pyarrow  # noqa: E401
    manifest = {"started_utc": started.isoformat(), "protocol_sha256": sha_file(PROTOCOL),
                "git_head": "recorded outside the guarded process in 00_ENVIRONMENT.md",
                "python": sys.version.split()[0], "platform": platform.platform(),
                "versions": {"pandas": pd.__version__, "numpy": np.__version__, "lightgbm": lightgbm.__version__,
                             "sklearn": sklearn.__version__, "pyarrow": pyarrow.__version__},
                "allowlist_sha256_start": guard.verify_allowlist(),
                "code_sha256": {f: guard.sha256(f) for f in CODE_FILES},
                "runner_sha256": {p.name: sha_file(p) for p in sorted(HERE.glob("*.py"))},
                "params": PARAMS, "seed": 42}

    src = F.load_sources(guard)
    stress, rounds = F.s1_targets(D, R, src["psa"])
    for d in (stress,):
        if (d["quarter"].map(F.qi) > F.qi(F.QMAX)).any():
            raise Stop("a quarter after 2025-Q4 appeared in targets")
    if any(F.qi(r.quarter) > F.qi(F.QMAX) for r in rounds):
        raise Stop("SWS round after 2025-Q4 present")
    chk = stress.merge(src["lab"], on=["province_code", "quarter"], how="inner")
    maxdiff = float((chk["stress"] - chk["stress_score"]).abs().max())
    if len(chk) != len(stress) or maxdiff > 1e-3:
        raise Stop(f"S1 cross-check failed: {len(chk)} of {len(stress)} rows matched, max diff {maxdiff}")
    published = lambda q: D.label_published(q, "development")[0]
    tau0, tau_q = R.reference_threshold(stress[["province_code", "quarter", "stress"]], published, AS_OF)
    if abs(tau0 - TAU0_RECORDED) > 1e-3:
        raise Stop(f"tau0 {tau0} differs from recorded {TAU0_RECORDED}")

    label_q = sorted(stress["quarter"].unique(), key=F.qi)
    all_targets = F.quarter_range("2021-Q2", F.QMAX)
    frame = F.build_frame(D, R, src, stress, rounds, all_targets)
    tests = [q for q in label_q if len(F.eligible_training_quarters(stress, q, published)) >= MIN_TRAIN_Q]

    vault = Vault(stress, published)
    P1, folds = predict_all(frame, stress, vault, published, tau0, tests)
    P2, _ = predict_all(frame, stress, vault, published, tau0, tests)
    num = ["stress_pred", "probability"]
    if not np.allclose(P1[num].fillna(-999).values, P2[num].fillna(-999).values, atol=0, rtol=0) or \
            not (P1["classification"] == P2["classification"]).all():
        raise Stop("non-deterministic predictions")
    pred_path = run / "predictions.csv"
    P1.to_csv(pred_path, index=False)
    sealed = vault.seal(pred_path)

    truth = vault.reveal(tests, pred_path)
    scores, S = score(P1, truth, tau0, tests)
    selection = select(scores, S, tests)
    diag = diagnostics(stress, tests, published, tau0, S, folds)

    frame.to_csv(run / "input_frame.csv", index=False)
    stress.to_csv(run / "s1_targets_2021_2025.csv", index=False)
    S.to_csv(run / "scored_rows.csv", index=False)
    (run / "folds.json").write_text(json.dumps(folds, indent=1, default=str), encoding="utf-8")
    (run / "metrics.json").write_text(json.dumps(scores, indent=1, default=str), encoding="utf-8")
    (run / "selection.json").write_text(json.dumps(selection, indent=1, default=str), encoding="utf-8")
    (run / "diagnostics.json").write_text(json.dumps(diag, indent=1, default=str), encoding="utf-8")
    manifest.update({
        "tau0": tau0, "tau0_quarters": tau_q, "s1_crosscheck": {"rows": len(chk), "max_abs_diff": maxdiff},
        "label_quarters": label_q, "n_label_quarters": len(label_q), "test_quarters": tests,
        "impossible_zero_set_missing": src["impossible_zero_set_missing"],
        "predictions_sha256_sealed_before_outcomes": sealed, "determinism_check": "two runs identical",
        "access_log": guard.ACCESS_LOG, "allowlist_sha256_end": guard.verify_allowlist(),
        "finished_utc": datetime.now(timezone.utc).isoformat()})
    outs = {p.name: sha_file(p) for p in sorted(run.glob("*")) if p.name != "manifest.json"}
    manifest["outputs_sha256"] = outs
    (run / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str), encoding="utf-8")
    print(f"RUN {run.name}: tau0={tau0:.4f} tests={tests} selected={selection['selected']}")


if __name__ == "__main__":
    main()

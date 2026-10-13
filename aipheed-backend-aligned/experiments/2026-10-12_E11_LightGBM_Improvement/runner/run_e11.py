"""
E11 runner (see ../E11_PROTOCOL.md). Run from the aligned backend root:  python -B <this file>
Guarded: reads only the E9 allowlist (hash-pinned, row-filtered <= 2025-Q4) and E9's own frame for an equality check.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard  # noqa: E402

guard.install()

import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import warnings  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

E9 = guard.AL / "experiments" / "2026-10-12_E9_S1_safe_training"
sys.path.insert(0, str(E9 / "runner"))
sys.path.insert(0, str(guard.AL))
import scripts.supplementary.devprotocol_rule_l as D  # noqa: E402
from app.ml.features import risk_score_v2 as R  # noqa: E402
import metrics as M  # noqa: E402  (E9 metric functions)
import safe_frame as F  # noqa: E402  (E9 frame)
import e11_lib as L  # noqa: E402

warnings.filterwarnings("ignore")
EXP = guard.EXP
PROTOCOL = EXP / "E11_PROTOCOL.md"
E9_FRAME = E9 / "runs" / "20261012T140816Z" / "input_frame.csv"
TAU0 = 10.84335
MIN_TRAIN_Q = 8
ROLL = 8
SEL_END = "2024-Q4"
COMBOS = [("direct", "core"), ("direct", "core_plus"), ("direct", "compact"), ("direct", "expanded"),
          ("decomp", "provincial"), ("resid", "residual")]
CLF_FS = ["core", "compact"]
REQUIRED = ["last_published_stress", "sws_hunger", "cpi_rel", "food_cpi_yoy"]


class Stop(RuntimeError):
    pass


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Vault:
    def __init__(self, stress, published):
        self._s = stress[["province_code", "quarter", "stress", "deviation"]].copy()
        self._pub = published
        self._sealed = None

    def train(self, quarters, target):
        for q in quarters:
            pub = self._pub(q)
            if F.qi(q) >= F.qi(target) or pub is None or pub >= F.qstart(target):
                raise Stop(f"vault: label {q} not available at the origin of {target}")
        return self._s[self._s["quarter"].isin(quarters)].copy()

    def seal(self, path):
        self._sealed = sha(path)
        return self._sealed

    def reveal(self, quarters, path):
        if self._sealed is None or sha(path) != self._sealed:
            raise Stop("vault: outcomes requested before sealed predictions")
        return self._s[self._s["quarter"].isin(quarters)].copy()


def reasons_for(r) -> str:
    rs = [f"missing input: {c}" for c in REQUIRED if pd.isna(r.get(c))]
    if pd.notna(r.get("sws_age")) and r["sws_age"] > R.SWS_MAX_AGE_QUARTERS:
        rs.append("stale SWS input")
    return "; ".join(rs)


def predict_all(frame, stress, vault, published, tests):
    rows, folds = [], []

    def emit(te, arm, structure, fs, cfg, window, kind, stress_pred=None, prob=None, extra=None):
        d = te[["province_code", "target_quarter", "insufficient_reasons"]].copy()
        d["arm"], d["structure"], d["feature_set"], d["config"], d["window"], d["kind"] = arm, structure, fs, cfg, window, kind
        d["stress_pred"] = np.nan if stress_pred is None else stress_pred
        d["probability"] = np.nan if prob is None else prob
        if extra:
            for k, v in extra.items():
                d[k] = v
        rows.append(d)

    for window in ("expanding", "rolling8"):
        for T in tests:
            tq_all = F.eligible_training_quarters(stress, T, published)
            tq = tq_all if window == "expanding" else tq_all[-ROLL:]
            lab = vault.train(tq, T)
            tr = frame[frame["target_quarter"].isin(tq)].merge(
                lab, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"], how="inner")
            te = frame[frame["target_quarter"] == T].sort_values("province_code").reset_index(drop=True)
            te["insufficient_reasons"] = [reasons_for(r) for _, r in te.iterrows()]
            y_bin = (tr["stress"].values > TAU0).astype(int)
            fold = {"target": T, "window": window, "train_quarters": tq, "n_train_rows": int(len(tr)),
                    "train_HIGH": int(y_bin.sum()), "train_LOW": int((y_bin == 0).sum()), "arms": {}}
            # baselines
            emit(te, "B1_carry_forward", "baseline", "-", "-", window, "stress", te["last_published_stress"].values)
            emit(te, "B2_regional", "baseline", "-", "-", window, "stress", te["sws_hunger"].values)
            emit(te, "B3_S1_rule", "baseline", "-", "-", window, "stress", te["s1rule"].values)
            emit(te, "B4_majority", "baseline", "-", "-", window, "class_only",
                 extra={"majority": "HIGH" if y_bin.sum() * 2 >= len(y_bin) else "LOW"})
            inner = L.inner_quarters(tq, published, F.qi, F.qstart)
            fold["n_inner_quarters"] = len(inner)
            # regressors
            for structure, fs in COMBOS:
                feats = L.FS[fs]
                if window == "expanding":
                    for cfg in L.CONFIGS:
                        p, keep, tmae, gain = L.fit_predict_reg(structure, tr, te, feats, cfg)
                        emit(te, f"FIXED|{structure}|{fs}|{cfg}", structure, fs, cfg, window, "stress", p)
                        fold["arms"][f"FIXED|{structure}|{fs}|{cfg}"] = {"features_used": keep, "train_mae": tmae, "gain": gain}
                scores = {c: [] for c in L.CONFIGS}
                for qt, itr in inner:
                    tri, tei = tr[tr["target_quarter"].isin(itr)], tr[tr["target_quarter"] == qt]
                    for cfg in L.CONFIGS:
                        p, _, _, _ = L.fit_predict_reg(structure, tri, tei, feats, cfg)
                        if not np.all(np.isnan(p)):
                            scores[cfg].append(float(np.nanmean(np.abs(p - tei["stress"].values))))
                chosen, means = L.choose(scores)
                p, keep, tmae, gain = L.fit_predict_reg(structure, tr, te, feats, chosen)
                arm = f"NESTED|{structure}|{fs}"
                emit(te, arm, structure, fs, chosen, window, "stress", p)
                fold["arms"][arm] = {"chosen": chosen, "inner_mean_mae": means, "features_used": keep,
                                     "train_mae": tmae, "gain": gain}
            # classifiers (nested by inner Brier; E6 calibration rule)
            for fs in CLF_FS:
                feats = L.FS[fs]
                scores, oof = {c: [] for c in L.CONFIGS}, {c: [] for c in L.CONFIGS}
                for qt, itr in inner:
                    tri, tei = tr[tr["target_quarter"].isin(itr)], tr[tr["target_quarter"] == qt]
                    yi = (tei["stress"].values > TAU0).astype(int)
                    for cfg in L.CONFIGS:
                        p, _ = L.fit_predict_clf(tri, tei, feats, cfg, TAU0)
                        if not np.all(np.isnan(p)):
                            scores[cfg].append(float(np.mean((p - yi) ** 2)))
                            oof[cfg].append(pd.DataFrame({"q": qt, "p": p, "y": yi}))
                chosen, means = L.choose(scores)
                p, keep = L.fit_predict_clf(tr, te, feats, chosen, TAU0)
                cal = {"applied": False, "reason": "no inner out-of-fold predictions"}
                if oof[chosen]:
                    o = pd.concat(oof[chosen])
                    nq, npos, nneg = o["q"].nunique(), int(o["y"].sum()), int((o["y"] == 0).sum())
                    ok = nq >= 8 and min(npos, nneg) >= 10
                    cal = {"applied": bool(ok), "oof_quarters": int(nq), "oof_high": npos, "oof_low": nneg,
                           "reason": "sufficient" if ok else "insufficient (need >= 8 quarters and >= 10 per class)"}
                    if ok:
                        from sklearn.linear_model import LogisticRegression
                        lg = lambda v: np.log(np.clip(v, 1e-6, 1 - 1e-6) / (1 - np.clip(v, 1e-6, 1 - 1e-6)))
                        platt = LogisticRegression().fit(lg(o["p"].values).reshape(-1, 1), o["y"].values)
                        p = platt.predict_proba(lg(p).reshape(-1, 1))[:, 1]
                arm = f"NESTED_CLF|direct|{fs}"
                emit(te, arm, "direct", fs, chosen, window, "probability", prob=p)
                fold["arms"][arm] = {"chosen": chosen, "inner_mean_brier": means, "features_used": keep, "calibration": cal}
            folds.append(fold)
    P = pd.concat(rows, ignore_index=True)

    def cls(r):
        if r["insufficient_reasons"]:
            return R.INSUFFICIENT_DATA
        if r["kind"] == "probability":
            return R.INSUFFICIENT_DATA if pd.isna(r["probability"]) else R.final_classification(r["probability"], [])
        if r["kind"] == "class_only":
            return r["majority"]
        return R.INSUFFICIENT_DATA if pd.isna(r["stress_pred"]) else (R.HIGH if r["stress_pred"] > TAU0 else R.LOW)
    P["classification"] = P.apply(cls, axis=1)
    return P, folds


def evaluate(S, tests):
    sel = [q for q in tests if F.qi(q) <= F.qi(SEL_END)]
    periods = {"all": tests, "e9_selection_period": sel, "e9_final_period": [q for q in tests if q not in sel]}
    out = {}
    for (arm, window, kind), g in S.groupby(["arm", "window", "kind"]):
        g = g[g["classification"] != R.INSUFFICIENT_DATA]
        res = {}
        for pname, qs in periods.items():
            h = g[g["target_quarter"].isin(qs)]
            if h.empty:
                continue
            r = {"rows": int(len(h)), "quarters": int(h["target_quarter"].nunique()),
                 "classification": M.classification(h["event_true"].values, (h["classification"] == R.HIGH).values)}
            if kind == "stress":
                se = M.stress_errors(h[["target_quarter", "province_code", "stress_pred", "stress_true"]])
                se["bias"] = float((h["stress_pred"] - h["stress_true"]).mean())
                r["stress"] = se
                r["auc_of_stress"] = M.ranking_auc(h["event_true"].values, h["stress_pred"].values)
            if kind == "probability":
                r["brier"] = M.brier(h["event_true"].values, h["probability"].values)
                r["auc"] = M.ranking_auc(h["event_true"].values, h["probability"].values)
                r["mean_probability"] = float(h["probability"].mean())
            if pname == "all":
                hh = h[h["event_true"]]
                r["classification_HIGH_rows_only"] = M.classification(hh["event_true"].values, (hh["classification"] == R.HIGH).values)
            res[pname] = r
        out[f"{arm}|{window}|{kind}"] = res
    return out


def comparisons(S, tests):
    st = S[(S["kind"] == "stress") & (S["classification"] != R.INSUFFICIENT_DATA)].copy()
    st["err"] = (st["stress_pred"] - st["stress_true"]).abs()
    perq = st.groupby(["arm", "window", "target_quarter"])["err"].mean()
    out = {}
    for (arm, window) in st[["arm", "window"]].drop_duplicates().itertuples(index=False):
        for ref in ("B1_carry_forward", "B2_regional", "B3_S1_rule"):
            if arm == ref:
                continue
            a = perq.loc[(arm, window)].reindex(tests)
            b = perq.loc[(ref, window)].reindex(tests)
            if a.isna().any() or b.isna().any():
                continue
            bs = M.cluster_bootstrap_diff(a.to_dict(), b.to_dict(), tests)
            out[f"{arm}|{window}|vs_{ref}"] = {"mean_diff": bs["mean_diff"], "ci95": bs["ci95"],
                                                "quarters_better": int((a < b).sum()), "per_quarter_diff": (a - b).round(4).to_dict(),
                                                "signflip_p": L.signflip_p((a - b).values)}
    return out


def recommendation(scores, comps):
    out = {}
    b3 = scores["B3_S1_rule|expanding|stress"]["all"]["stress"]["mean_concordant_share"]
    for structure, fs in COMBOS:
        arm = f"NESTED|{structure}|{fs}"
        c = comps[f"{arm}|expanding|vs_B3_S1_rule"]
        roll = comps.get(f"{arm}|rolling8|vs_B3_S1_rule")
        conc = scores[f"{arm}|expanding|stress"]["all"]["stress"]["mean_concordant_share"]
        crit = {"1_better_in_>=5_of_7": c["quarters_better"] >= 5,
                "2_mean<0_and_upper<0": c["mean_diff"] < 0 and c["ci95"][1] < 0,
                "3_concordance>=B3": conc >= b3 - 1e-12,
                "4_rolling_same_direction": bool(roll is not None and roll["mean_diff"] < 0)}
        out[arm] = {"criteria": crit, "all_met": all(crit.values()), "mean_diff_vs_B3": c["mean_diff"],
                    "ci95": c["ci95"], "quarters_better": c["quarters_better"], "concordance": conc, "B3_concordance": b3}
    out["decision"] = ("recommend LightGBM candidate(s): " + ", ".join(k for k, v in out.items() if isinstance(v, dict) and v["all_met"])) \
        if any(isinstance(v, dict) and v["all_met"] for v in out.values()) else \
        "no candidate meets all four criteria: S1 rule stays primary; LightGBM experimental"
    return out


def diagnostics(frame, stress, S, folds, tests):
    lab = frame.merge(stress[["province_code", "quarter", "stress", "deviation", "sws_hunger_pct"]],
                      left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"], how="inner")
    feats = sorted(set(sum(L.FS.values(), [])))
    d = {"within_quarter_variance_share": L.within_quarter_share(frame, feats),
         "target_within_quarter_share": L.within_quarter_share(lab.rename(columns={"stress": "stress_target"}), ["stress_target", "deviation"]),
         "corr_deviation_vs_anchor_dev": float(lab[["deviation", "anchor_dev"]].dropna().corr().iloc[0, 1]),
         "corr_deviation_vs_cpi_rel": float(lab[["deviation", "cpi_rel"]].dropna().corr().iloc[0, 1]),
         "note": "correlations use all 2021-2025 labelled rows (descriptive, in-sample)"}
    gshare = {}
    for f in folds:
        if f["window"] != "expanding":
            continue
        for arm, info in f["arms"].items():
            g = info.get("gain")
            if arm.startswith("NESTED|direct") and g:
                tot = sum(g.values()) or 1.0
                gshare.setdefault(arm, []).append(sum(v for k, v in g.items() if k in L.REGIONAL_FEATURES or k == "last_published_stress") / tot)
    d["direct_nested_gain_share_regional_or_lps"] = {k: [round(x, 3) for x in v] for k, v in gshare.items()}
    d["nested_choices"] = {f"{f['window']}|{f['target']}": {a: i.get("chosen") for a, i in f["arms"].items() if "chosen" in i} for f in folds}
    d["inner_quarters"] = {f"{f['window']}|{f['target']}": f["n_inner_quarters"] for f in folds}
    ov = []
    for f in folds:
        for arm, info in f["arms"].items():
            if info.get("train_mae") is not None:
                h = S[(S["arm"] == arm) & (S["window"] == f["window"]) & (S["target_quarter"] == f["target"])]
                ov.append({"arm": arm, "window": f["window"], "target": f["target"], "train_mae": info["train_mae"],
                           "test_mae": float((h["stress_pred"] - h["stress_true"]).abs().mean())})
    d["train_vs_test_mae"] = ov
    obs = S[(S["arm"] == "B1_carry_forward") & (S["window"] == "expanding")].pivot(index="target_quarter", columns="province_code", values="stress_true")
    dev = obs.sub(obs.mean(axis=1), axis=0).reindex(tests)
    d["observed_rank_persistence_kendall_consecutive"] = {
        f"{a}->{b}": float(pd.Series(dev.loc[a]).corr(pd.Series(dev.loc[b]), method="kendall")) for a, b in zip(tests[:-1], tests[1:])}
    return d


def main():
    if not PROTOCOL.exists():
        raise Stop("protocol missing")
    started = datetime.now(timezone.utc)
    run = EXP / "runs" / started.strftime("%Y%m%dT%H%M%SZ")
    run.mkdir(parents=True, exist_ok=False)
    import lightgbm, sklearn, pyarrow  # noqa: E401
    man = {"started_utc": started.isoformat(), "protocol_sha256": sha(PROTOCOL),
           "allowlist_sha256_start": guard.verify_allowlist(),
           "code_sha256": {"run_e11.py": sha(Path(__file__)), "e11_lib.py": sha(HERE / "e11_lib.py"), "guard.py": sha(HERE / "guard.py"),
                           "E9 safe_frame.py": sha(E9 / "runner" / "safe_frame.py"), "E9 metrics.py": sha(E9 / "runner" / "metrics.py"),
                           "risk_score_v2.py": guard.sha256("app/ml/features/risk_score_v2.py"),
                           "devprotocol_rule_l.py": guard.sha256("scripts/supplementary/devprotocol_rule_l.py")},
           "environment": {"python": sys.version.split()[0], "platform": platform.platform(), "pandas": pd.__version__,
                           "numpy": np.__version__, "lightgbm": lightgbm.__version__, "sklearn": sklearn.__version__,
                           "pyarrow": pyarrow.__version__},
           "configs": L.CONFIGS, "common": L.COMMON, "feature_sets": L.FS, "seed": 42}

    src = F.load_sources(guard)
    stress, rounds = F.s1_targets(D, R, src["psa"])
    chk = stress.merge(src["lab"], on=["province_code", "quarter"], how="inner")
    if len(chk) != len(stress) or (chk["stress"] - chk["stress_score"]).abs().max() > 1e-3:
        raise Stop("S1 cross-check failed")
    published = lambda q: D.label_published(q, "development")[0]
    tau0, tq0 = R.reference_threshold(stress[["province_code", "quarter", "stress"]], published, pd.Timestamp("2023-10-01"))
    if abs(tau0 - TAU0) > 1e-3:
        raise Stop("tau0 mismatch")
    frame = F.build_frame(D, R, src, stress, rounds, F.quarter_range("2021-Q2", F.QMAX))
    import io
    try:
        pd.testing.assert_frame_equal(pd.read_csv(io.StringIO(frame.to_csv(index=False))), pd.read_csv(E9_FRAME),
                                      check_exact=True)
    except AssertionError as e:
        raise Stop(f"rebuilt frame differs from the E9 frame: {str(e)[:200]}")
    hist = L.label_history_features(frame, stress, published, F.qi, F.qstart)
    frame = frame.merge(hist, on=["target_quarter", "province_code"], how="left")
    if not (frame["anchor_check"].fillna("") == frame["anchor_quarter"].fillna("")).all():
        raise Stop("anchor mismatch between E9 frame and E11 history features")
    frame["s1rule"] = frame["sws_hunger"] + 2.0 * frame["cpi_rel"]
    label_q = sorted(stress["quarter"].unique(), key=F.qi)
    tests = [q for q in label_q if len(F.eligible_training_quarters(stress, q, published)) >= MIN_TRAIN_Q]

    vault = Vault(stress, published)
    P1, folds = predict_all(frame, stress, vault, published, tests)
    P2, _ = predict_all(frame, stress, vault, published, tests)
    num = ["stress_pred", "probability"]
    if not (np.array_equal(P1[num].fillna(-999).values, P2[num].fillna(-999).values)
            and (P1["classification"] == P2["classification"]).all()):
        raise Stop("non-deterministic predictions")
    pred_path = run / "predictions.csv"
    P1.to_csv(pred_path, index=False)
    sealed = vault.seal(pred_path)

    truth = vault.reveal(tests, pred_path).rename(columns={"quarter": "target_quarter", "stress": "stress_true",
                                                           "deviation": "deviation_true"})
    S = P1.merge(truth, on=["target_quarter", "province_code"], how="left")
    if S["stress_true"].isna().any():
        raise Stop("missing truth")
    S["event_true"] = S["stress_true"] > TAU0
    scores = evaluate(S, tests)
    comps = comparisons(S, tests)
    rec = recommendation(scores, comps)
    diag = diagnostics(frame, stress, S, folds, tests)

    frame.to_csv(run / "frame_e11.csv", index=False)
    S.to_csv(run / "scored_rows.csv", index=False)
    for name, obj in (("folds", folds), ("metrics", scores), ("comparisons", comps), ("recommendation", rec), ("diagnostics", diag)):
        (run / f"{name}.json").write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
    man.update({"tau0": tau0, "tau0_quarters": tq0, "label_quarters": label_q, "tests": tests,
                "frame_equals_e9": True, "predictions_sealed_sha256": sealed, "determinism": "two passes identical",
                "n_arms": int(P1[["arm", "window", "kind"]].drop_duplicates().shape[0]),
                "access_log_parquet": [a for a in guard.ACCESS_LOG if a["op"] == "read_parquet"],
                "access_log_opens": sorted({a["path"] for a in guard.ACCESS_LOG if a["op"] == "open"}),
                "allowlist_sha256_end": guard.verify_allowlist(), "finished_utc": datetime.now(timezone.utc).isoformat()})
    man["outputs_sha256"] = {p.name: sha(p) for p in sorted(run.glob("*")) if p.name != "manifest.json"}
    (run / "manifest.json").write_text(json.dumps(man, indent=1, default=str), encoding="utf-8")
    print(f"RUN {run.name} | arms {man['n_arms']} | decision: {rec['decision']}")


if __name__ == "__main__":
    main()

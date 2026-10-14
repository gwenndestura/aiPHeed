"""E25 runner (FROZEN_EVALUATION_PROTOCOL.md; hashes checked first).

Phase 1 predicts every model at every feasible (target, lead, origin) and SEALS the predictions (SHA-256).
Phase 2 scores them (score_e25.py): metrics, paired tests, Holm, criteria C1-C9 and P1-P9, hypotheses, supporting
analyses.
Usage: python -B runner/run_e25.py [--synthetic SEED]
  --synthetic: the identical code on generated data (tests/synthetic.py); used only to debug the runner before
               the one real run. Writes runs/SYNTH_<id>/."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402

import e23_lib as L  # noqa: E402
import e25lib as E  # noqa: E402

EXP = guard.EXP
qk, qs = E.qk, E.qs
T1_LABEL_ARMS = ["B1_naive_persistence", "B1p_calibrated_persistence", "CLIM_training_rate", "REF_always_HIGH",
                 "MAJ_training_majority", "PCF21", "PCF21_NOW", "PCF21_SUPP", "PCF21_HIER", "PCF21_MR", "PCF21_LI",
                 "ENS_PCF21_B1p", "GATE_PCF21_B1p", "CAL_PCF21", "E24_LR_P", "DIAG_ORACLE_H", "DIAG_ORACLE_D"]
T2_LABEL_ARMS = ["B1_naive_persistence", "B1p_calibrated_persistence", "CLIM_training_rate", "REF_always_HIGH",
                 "MAJ_training_majority", "M4_21", "M3_21", "D_HIER", "D_HIER_NOW", "E24_LR_P_T2", "ENS_M4_B1p"]
FEATURE_ARMS = ["B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only", "B5_lgbm_gov_only", "B6_lgbm_nlp_only",
                "PROPOSED_lgbm_combined"]
ABLATION_ARMS = ["ABL_no_FSSI", "ABL_no_FSSI_group", "ABL_no_cpi_dev"]
FSSI_GROUP = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel"]
PCF_ARMS = ["PCF21", "PCF21_NOW", "PCF21_SUPP", "PCF21_HIER", "PCF21_MR", "PCF21_LI"]
D_ARMS = {"M4_21": "ols_now", "M3_21": "ols", "D_HIER": "hier", "D_HIER_NOW": "hier_now"}


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def jd(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if np.isnan(o) else float(o)
    if isinstance(o, float) and np.isnan(o):
        return None
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (pd.Timestamp,)):
        return o.isoformat()
    return str(o)


def check_frozen():
    for ln in (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").splitlines():
        p = ln.split()
        if len(p) == 2 and len(p[0]) == 64 and sha_bytes((EXP / p[1]).read_bytes()) != p[0]:
            raise SystemExit(f"E25: {p[1]} differs from its frozen hash; stop.")


# ================================================================================================ data
def load_real():
    rounds = E.load_rounds()
    comp, c26, D = E.load_components()
    monthly, Dnow, cmp = E.load_monthly(c26, comp)
    X, gov_cols, masked, const = E.load_features(rounds[rounds["definition_A"]])
    return assemble(rounds, D, Dnow, X, gov_cols, {"masked_cells": masked, "constant_features": const,
                                                     "dnow_vs_E12_D": cmp, "window_log": E.WINDOW_LOG})


def assemble(rounds, D, Dnow, X, gov_cols, audit):
    Dm = {(r.province_code, qk(r.quarter)): float(r.D) for r in D.itertuples()}
    Nm = {(r.province_code, qk(r.quarter)): float(r.Dnow) for r in Dnow.itertuples()}
    Fbar = D.groupby("quarter")["F"].mean()
    Fq = {qk(q): v for q, v in Fbar.items()}
    rfc = {t: Fq[t - 1] - Fq[t - 2] for t in Fq if t - 1 in Fq and t - 2 in Fq}   # known at O(t)
    targets = {"T1_A": E.Target("T1", "A", rounds, D), "T1_B": E.Target("T1", "B", rounds, D),
               "T1_C": E.Target("T1", "C", rounds, D), "T1_F": E.Target("T1", "A", rounds, D, 14.6),
               "T2": E.Target("T2", "-", rounds, D)}
    return {"rounds": rounds, "D": D, "Dnow": Dnow, "Dm": Dm, "Nm": Nm, "X": X, "gov_cols": gov_cols,
            "targets": targets, "extras": {"regional_food_change": rfc}, "audit": audit}


# ================================================================================================ helpers
def feature_frames(T, X, t, k, tau, cache):
    """Training pairs (lead k and pooled over leads) and the five test rows, with features (E23 frame)."""
    trs = []
    for kk in E.LEADS:
        tr = E.training_pairs(T, t, kk, tau, cache)
        if len(tr):
            trs.append(tr.assign(lead=kk))
    allp = pd.concat(trs, ignore_index=True)
    allp = allp.merge(X.drop(columns=["quarter"]), on=["province_code", "t"], how="inner")
    tr_s = allp[allp["lead"] == k].copy()
    return tr_s, allp


def inner_gate_cal(T, data, t, k, tau, tr, cache, hc, dc):
    """Inner forecasts for GATE and CAL: the last 3 distinct training target quarters v, each forecast from its
    own earlier origin O(v - k) by PCF21 and B1p, labels under the outer tau. Training data only."""
    vq = sorted(tr["target_q"].unique())[-3:]
    ys, pp, pb = [], [], []
    for v in vq:
        tv = v - k
        out = E.pcf_t1("PCF21", data["rounds"], data["Dm"], data["Nm"], tv, k, tau, data["extras"], hc, dc)
        trv = E.training_pairs(T, tv, k, tau, cache)
        if out is None or trv.empty:
            continue
        lv = E.last_values(T, tv)
        rows = T.V[T.V["tq"] == v].sort_values("province_code")
        for r in rows.itertuples():
            last = lv[r.province_code][0]
            yl = float(last > tau) if last == last else np.nan
            if yl != yl:
                continue
            ys.append(int(r.v > tau))
            pp.append(out[r.province_code]["p"])
            pb.append(float(E.calibrated_persistence(trv, [yl])[0]))
    if not ys:
        return None
    return {"n": len(ys), "brier_pcf": E.brier(ys, pp), "brier_b1p": E.brier(ys, pb), "y": ys, "p_pcf": pp}


# ================================================================================================ T1
def run_t1(name, T, data, with_features: bool, keep_models: dict):
    preds, details, meta = [], [], {}
    cache, hc, dc = {}, {}, {}
    rounds, Dm, Nm, X = data["rounds"], data["Dm"], data["Nm"], data["X"]
    N, G = L.NLP, data["gov_cols"] + ["sws_hunger"]
    cols_of = {"B2_lr_combined": N + G, "B3_lr_gov_only": G, "B4_lr_nlp_only": N, "B5_lgbm_gov_only": G,
               "B6_lgbm_nlp_only": N, "PROPOSED_lgbm_combined": N + G}
    for k in E.LEADS:
        for t in range(qk(E.FIRST_Q), qk("2026-Q1") + 1):
            if t + k > qk(E.LAST_Q):
                continue
            tau = T.tau(t)
            te = E.test_rows(T, t, k, tau)
            if te is None:
                continue
            tr = E.training_pairs(T, t, k, tau, cache)
            if tr.empty or tr["target_q"].nunique() < E.MIN_TRAIN_QUARTERS:
                continue
            assert tr["target_q"].max() <= t - 1 and all(T.pub(q, t) for q in tr["target_quarter"].unique())  # C7
            key = f"{name}|k{k}|{qs(t)}"
            m = {"target": name, "lead": k, "t": qs(t), "origin": E.origin(t).date().isoformat(),
                 "target_quarter": te["target_quarter"].iloc[0], "tau": tau,
                 "n_train_quarters": int(tr["target_q"].nunique()), "n_train_rows": int(len(tr)),
                 "train_HIGH": int(tr["y"].sum()), "train_LOW": int((1 - tr["y"]).sum()),
                 "test_HIGH": int(te["y"].sum()), "test_LOW": int((1 - te["y"]).sum())}
            s = {"B1_naive_persistence": te["y_last"].to_numpy(float),
                 "B1p_calibrated_persistence": E.calibrated_persistence(tr, te["y_last"].to_numpy()),
                 "CLIM_training_rate": E.climatology(tr, 5), "REF_always_HIGH": np.ones(5),
                 "MAJ_training_majority": np.full(5, 1.0 if tr["y"].mean() >= .5 else 0.0),
                 "E24_LR_P": E.lr_p(tr, te)}
            pcf_out = {}
            for arm in PCF_ARMS:
                o = E.pcf_t1(arm, rounds, Dm, Nm, t, k, tau, data["extras"], hc, dc)
                if o is not None:
                    pcf_out[arm] = o
                    s[arm] = np.array([o[p]["p"] for p in te["province_code"]])
            if "PCF21" in pcf_out:
                s["ENS_PCF21_B1p"] = (s["PCF21"] + s["B1p_calibrated_persistence"]) / 2
                inn = inner_gate_cal(T, data, t, k, tau, tr, cache, hc, dc)
                if inn is not None and inn["brier_pcf"] < inn["brier_b1p"] - 1e-12:
                    s["GATE_PCF21_B1p"], m["gate"] = s["PCF21"], "PCF21"
                else:
                    s["GATE_PCF21_B1p"], m["gate"] = s["B1p_calibrated_persistence"], "B1p"
                a = E.temperature(inn["p_pcf"], inn["y"]) if inn is not None else 1.0
                s["CAL_PCF21"], m["cal_temperature"] = E.apply_temperature(s["PCF21"], a), a
                m["inner"] = None if inn is None else {kk: inn[kk] for kk in ("n", "brier_pcf", "brier_b1p")}
                o = pcf_out["PCF21"]
                if T.name.startswith("T1") and hasattr(T, "H") and te["target_quarter"].iloc[0] in T.H.index:
                    Hr = float(T.H[te["target_quarter"].iloc[0]])
                    s["DIAG_ORACLE_H"] = np.array([1 - norm.cdf((tau - Hr - 2 * o[p]["mu_D"]) / max(2 * o[p]["sd_D"], 1e-9))
                                                   for p in te["province_code"]])
                    Dr = {p: Dm[(p, t + k)] for p in te["province_code"]}
                    s["DIAG_ORACLE_D"] = np.array([1 - norm.cdf((tau - o[p]["mu_H"] - 2 * Dr[p]) / o[p]["sd_H"])
                                                   for p in te["province_code"]])
            # continuous random-walk reference for T1-cont: RMSE of (v - v_last) over the training pairs
            rw_sd = float(np.sqrt(np.nanmean((tr["v"] - tr["v_last"]) ** 2)))
            for arm, o in pcf_out.items():
                for p in te["province_code"]:
                    details.append({"target": name, "lead": k, "t": qs(t), "province_code": p, "model": arm, **o[p]})
            if with_features and t <= qk(E.LAST_FEATURE_Q):
                tr_s, tr_p = feature_frames(T, X, t, k, tau, cache)
                teX = te.merge(X.drop(columns=["quarter"]), on=["province_code", "t"], how="left")
                assert len(teX) == 5 and (teX["province_code"].to_numpy() == te["province_code"].to_numpy()).all()
                for arm in ("B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only"):
                    s[arm] = L.fit_lr(tr_s, cols_of[arm], teX)
                for arm in ("B5_lgbm_gov_only", "B6_lgbm_nlp_only", "PROPOSED_lgbm_combined"):
                    sel = L.inner_select(tr_s, tr_p, cols_of[arm], k)
                    p, mdl, use = L.lgbm_predict(tr_s, tr_p, cols_of[arm], sel["config"], teX, k)
                    s[arm] = p
                    m[f"cfg_{arm}"] = sel["config"]
                    if arm == "PROPOSED_lgbm_combined":
                        if mdl is not None:
                            sh = L.shap_abs(mdl, teX, use, k)
                            m["shap_mean_abs"] = sh.abs().mean().to_dict()
                            m["shap_rank_top5"] = list(sh.abs().mean().sort_values(ascending=False).index[:5])
                            keep_models[key] = {"model": mdl, "use": use, "teX": teX, "k": k}
                        for abl, drop in (("ABL_no_FSSI", ["FSSI"]), ("ABL_no_FSSI_group", FSSI_GROUP),
                                          ("ABL_no_cpi_dev", ["cpi_dev"])):
                            pa, _, _ = L.lgbm_predict(tr_s, tr_p, [c for c in cols_of[arm] if c not in drop],
                                                      sel["config"], teX, k)
                            s[abl] = pa
                m["n_train_rows_features"] = int(len(tr_s))
            meta[key] = m
            for arm, v in s.items():
                for i, r in te.reset_index(drop=True).iterrows():
                    preds.append({"target": name, "lead": k, "t": qs(t), "origin": m["origin"],
                                  "target_quarter": r["target_quarter"], "province_code": r["province_code"],
                                  "model": arm, "score": float(v[i]), "y": int(r["y"]), "y_last": r["y_last"],
                                  "value": float(r["v"]), "v_last": r["v_last"], "threshold": tau, "rw_sd": rw_sd})
    return pd.DataFrame(preds), pd.DataFrame(details), meta


# ================================================================================================ T2
def run_t2(T, data, keep_models: dict):
    preds, details, meta = [], [], {}
    cache, dc = {}, {}
    Dm, Nm, X = data["Dm"], data["Nm"], data["X"]
    N, G = L.NLP, data["gov_cols"] + ["sws_hunger"]
    cols_of = {"B2_lr_combined": N + G, "B3_lr_gov_only": G, "B4_lr_nlp_only": N, "B5_lgbm_gov_only": G,
               "B6_lgbm_nlp_only": N, "PROPOSED_lgbm_combined": N + G}
    for k in E.LEADS:
        for t in range(qk(E.FIRST_Q), qk("2026-Q1") + 1):
            if t + k > qk(E.LAST_Q):
                continue
            te = E.test_rows(T, t, k, 0.0)
            if te is None:
                continue
            tr = E.training_pairs(T, t, k, 0.0, cache)
            if tr.empty or tr["target_q"].nunique() < E.MIN_TRAIN_QUARTERS:
                continue
            assert tr["target_q"].max() <= t - 1
            key = f"T2|k{k}|{qs(t)}"
            m = {"target": "T2", "lead": k, "t": qs(t), "origin": E.origin(t).date().isoformat(),
                 "target_quarter": te["target_quarter"].iloc[0], "n_train_quarters": int(tr["target_q"].nunique()),
                 "test_HIGH": int(te["y"].sum()), "test_LOW": int((1 - te["y"]).sum())}
            s = {"B1_naive_persistence": te["y_last"].to_numpy(float),
                 "B1p_calibrated_persistence": E.calibrated_persistence(tr, te["y_last"].to_numpy()),
                 "CLIM_training_rate": E.climatology(tr, 5), "REF_always_HIGH": np.ones(5),
                 "MAJ_training_majority": np.full(5, 1.0 if tr["y"].mean() >= .5 else 0.0),
                 "E24_LR_P_T2": E.lr_p(tr, te)}
            for arm, spec in D_ARMS.items():
                o = E.t2_prob(spec, Dm, Nm, t, k, dc)
                if o is not None:
                    s[arm] = np.array([o[p]["p"] for p in te["province_code"]])
                    for p in te["province_code"]:
                        details.append({"target": "T2", "lead": k, "t": qs(t), "province_code": p, "model": arm,
                                        **o[p]})
            if "M4_21" in s:
                s["ENS_M4_B1p"] = (s["M4_21"] + s["B1p_calibrated_persistence"]) / 2
            if t <= qk(E.LAST_FEATURE_Q):
                tr_s, tr_p = feature_frames(T, X, t, k, 0.0, cache)
                teX = te.merge(X.drop(columns=["quarter"]), on=["province_code", "t"], how="left")
                for arm in ("B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only"):
                    s[arm] = L.fit_lr(tr_s, cols_of[arm], teX)
                for arm in ("B5_lgbm_gov_only", "B6_lgbm_nlp_only", "PROPOSED_lgbm_combined"):
                    sel = L.inner_select(tr_s, tr_p, cols_of[arm], k)
                    p, mdl, use = L.lgbm_predict(tr_s, tr_p, cols_of[arm], sel["config"], teX, k)
                    s[arm] = p
                    m[f"cfg_{arm}"] = sel["config"]
                    if arm == "PROPOSED_lgbm_combined" and mdl is not None:
                        keep_models[key] = {"model": mdl, "use": use, "teX": teX, "k": k}
            meta[key] = m
            for arm, v in s.items():
                for i, r in te.reset_index(drop=True).iterrows():
                    preds.append({"target": "T2", "lead": k, "t": qs(t), "origin": m["origin"],
                                  "target_quarter": r["target_quarter"], "province_code": r["province_code"],
                                  "model": arm, "score": float(v[i]), "y": int(r["y"]), "y_last": r["y_last"],
                                  "value": float(r["v"]), "v_last": r["v_last"], "threshold": 0.0, "rw_sd": np.nan})
    return pd.DataFrame(preds), pd.DataFrame(details), meta


# ================================================================================================ main
def predict_all(data):
    keep = {}
    out = {}
    P, Dt, M = run_t1("T1_A", data["targets"]["T1_A"], data, True, keep)
    out["T1_A"] = (P, Dt, M)
    for nm in ("T1_B", "T1_C", "T1_F"):
        out[nm] = run_t1(nm, data["targets"][nm], data, False, {})
    out["T2"] = run_t2(data["targets"]["T2"], data, keep)
    return out, keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", type=int, default=None)
    a = ap.parse_args()
    check_frozen()
    runid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if a.synthetic is not None:
        sys.path.insert(0, str(EXP / "tests"))
        import synthetic
        data = synthetic.make(a.synthetic, assemble)
        rd = EXP / "runs" / f"SYNTH_{runid}"
        allow = []
    else:
        allow = guard.verify_allowlist()
        data = load_real()
        rd = EXP / "runs" / runid
    rd.mkdir(parents=True)
    out, keep = predict_all(data)
    seals = {}
    for nm, (P, Dt, M) in out.items():
        b = P.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode()
        (rd / f"predictions_{nm}.csv").write_bytes(b)
        seals[nm] = sha_bytes(b)
        if len(Dt):
            Dt.to_csv(rd / f"details_{nm}.csv", index=False, lineterminator="\n", float_format="%.12g")
        (rd / f"fold_meta_{nm}.json").write_text(json.dumps(M, indent=1, default=jd), encoding="utf-8")
    (rd / "SEALS.json").write_text(json.dumps(seals, indent=1), encoding="utf-8")
    import score_e25
    results = score_e25.score_all(rd, out, keep, data)
    (rd / "results.json").write_text(json.dumps(results, indent=1, default=jd), encoding="utf-8")
    import lightgbm
    import scipy
    import sklearn
    man = {"run_id": runid, "synthetic_seed": a.synthetic, "seals": seals, "allowlist": allow,
           "audit": data["audit"], "access_log": guard.ACCESS_LOG,
           "runner_sha256": {p.name: sha_bytes(p.read_bytes()) for p in sorted((EXP / "runner").glob("*.py"))},
           "protocol": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8"),
           "versions": {"python": platform.python_version(), "lightgbm": lightgbm.__version__,
                        "sklearn": sklearn.__version__, "scipy": scipy.__version__, "numpy": np.__version__,
                        "pandas": pd.__version__}}
    (rd / "manifest.json").write_text(json.dumps(man, indent=1, default=jd), encoding="utf-8")
    print(rd.name, json.dumps(seals))


if __name__ == "__main__":
    main()

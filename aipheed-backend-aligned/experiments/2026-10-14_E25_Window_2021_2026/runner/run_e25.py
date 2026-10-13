"""E25 evaluation on the 2021-Q1..2026-Q2 window (FROZEN_EVALUATION_PROTOCOL.md, E25).

    python -B runner/run_e25.py                # primary run (pre-2021 cells masked)
    python -B runner/run_e25.py --equivalence  # code check only: unmasked required models must equal E24's sealed
                                               # predictions (not a result; nothing from it is reported as evidence)
"""
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
import platform  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e23_lib as L  # noqa: E402
import e25lib as W  # noqa: E402
import pcf  # noqa: E402
import run_e23 as R  # noqa: E402
import run_e24 as R24  # noqa: E402

EXP = guard.EXP
qk, qs = L.qk, L.qs
REQ = ["B1_naive_persistence", "B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only", "B5_lgbm_gov_only",
       "B6_lgbm_nlp_only", "PROPOSED_lgbm_combined"]
REF = ["B1p_calibrated_persistence", "REF_always_HIGH", "MAJ_training_majority"]
CAND = {"T1": {"a": "PCF21", "b": "PCF21_NOW", "final": "PCF21"},
        "T2": {"a": "M3_21", "b": "M4_21", "final": "M4_21"}}
LAST_ORIGIN = qk("2026-Q1")


def check_frozen():
    h, f = (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[:2]
    if hashlib.sha256((EXP / f).read_bytes()).hexdigest() != h:
        raise SystemExit("E25: protocol changed after freezing; stop.")


def jd(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def run_target(target: str, data: dict, only_required=False):
    V, rounds, Dm, Nm = data["V"][target], data["rounds"], data["Dm"], data["Nm"]
    X = L.build_frame(data["ff"], rounds, data["gov_cols"])
    W.assert_quarters(f"feature frame ({target})", X["quarter"], hi="2025-Q4")
    pub = R24.make_pub(target, rounds)
    G = data["gov_cols"] + ["sws_hunger"]
    N = L.NLP
    cols_of = {"B2_lr_combined": N + G, "B3_lr_gov_only": G, "B4_lr_nlp_only": N, "B5_lgbm_gov_only": G,
               "B6_lgbm_nlp_only": N, "PROPOSED_lgbm_combined": N + G}
    tmin = qk(W.FIRST_Q)
    grid = pd.DataFrame([(p, t) for t in range(tmin, LAST_ORIGIN + 1) for p in W.PROVS], columns=["province_code", "t"])
    PX = {k: R24.pairs(X, V, k) for k in L.LEADS}
    PG = {k: R24.pairs(grid, V, k) for k in L.LEADS}
    allX = pd.concat(PX.values(), ignore_index=True)
    allG = pd.concat(PG.values(), ignore_index=True)
    preds, meta, cache = [], {}, {}
    for k in L.LEADS:
        for t in range(tmin, LAST_ORIGIN + 1):
            teg = PG[k][PG[k]["t"] == t].sort_values("province_code").reset_index(drop=True)
            if len(teg) != 5:
                continue
            assert teg["target_q"].max() <= qk(W.LAST_Q)
            tau = R24.threshold(target, V, pub, t)
            okq = {q: pub(q, t) for q in allG["target_quarter"].unique()}
            trG = allG[allG["target_quarter"].map(okq)].copy()
            trG["y"] = (trG["v"] > tau).astype(int)
            assert trG.empty or trG["target_q"].max() <= t - 1
            trG = R24.pblock(V, pub, trG, tau, cache)
            trG_s = trG[trG["lead"] == k]
            te = R24.pblock(V, pub, teg.assign(y=(teg["v"] > tau).astype(int)), tau, cache)
            if te["y_last"].isna().any():
                continue
            m = {"lead": k, "feature_quarter": qs(t), "target_quarter": te["target_quarter"].iloc[0], "threshold": tau,
                 "train_quarters": {}}
            s = {"B1_naive_persistence": te["y_last"].to_numpy(float), "REF_always_HIGH": np.ones(5)}
            nq_lab = int(trG_s["target_q"].nunique())
            if nq_lab >= L.MIN_TRAIN_QUARTERS:
                s["B1p_calibrated_persistence"] = np.array([(trG_s.loc[trG_s["y_last"] == yl, "y"].sum() + 1) /
                                                            ((trG_s["y_last"] == yl).sum() + 2) for yl in te["y_last"]])
                s["MAJ_training_majority"] = np.full(5, 1.0 if trG_s["y"].mean() >= 0.5 else 0.0)
                m["train_quarters"]["label_history"] = nq_lab
            # ---- required models (features exist for t <= 2025-Q4)
            if t in set(X["t"]):
                trX = allX[allX["target_quarter"].map(okq) & (allX["t"] >= tmin)].copy()
                trX["y"] = (trX["v"] > tau).astype(int)
                trX_s = trX[trX["lead"] == k].copy()
                teX = PX[k][PX[k]["t"] == t].sort_values("province_code").reset_index(drop=True)
                if trX_s["target_q"].nunique() >= L.MIN_TRAIN_QUARTERS and len(teX) == 5:
                    assert trX["target_q"].max() <= t - 1
                    assert all(pub(q, t) for q in trX["target_quarter"].unique())
                    teX = teX.assign(y=(teX["v"] > tau).astype(int))
                    assert (teX["province_code"].to_numpy() == te["province_code"].to_numpy()).all()
                    m["train_quarters"]["required"] = int(trX_s["target_q"].nunique())
                    for name in ("B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only"):
                        s[name] = L.fit_lr(trX_s, cols_of[name], teX)
                    for name in ("B5_lgbm_gov_only", "B6_lgbm_nlp_only", "PROPOSED_lgbm_combined"):
                        p, mdl, use, sel = R24.nested_lgbm(trX_s, trX, cols_of[name], teX, k)
                        s[name] = p
                        m[f"cfg_{name}"] = sel["config"]
                        if name == "PROPOSED_lgbm_combined" and mdl is not None:
                            m["shap_mean_abs"] = L.shap_abs(mdl, teX, use, k).abs().mean().to_dict()
            # ---- candidates
            if not only_required:
                for slot in ("a", "b"):
                    name = CAND[target][slot]
                    now = name in ("PCF21_NOW", "M4_21")
                    beta, sig, npairs, nq = W.d_model(Dm, Nm, t, k, now)
                    m["train_quarters"][name] = nq
                    if beta is None:
                        continue
                    mu = [W.d_point(Dm, Nm, p, t, beta, now) for p in te["province_code"]]
                    if any(x is None for x in mu):
                        continue
                    if target == "T2":
                        s[name] = np.array([pcf.p_pos(x, sig) for x in mu])
                    else:
                        times, ys, nqr = W.h_inputs(rounds, t)
                        m["train_quarters"][name + "_sws_round_quarters"] = nqr
                        if nqr < L.MIN_TRAIN_QUARTERS:
                            continue
                        hf = pcf.h_forecast(times, ys, float(t + k))
                        s[name] = np.array([pcf.p_high(tau, hf["mu_H"], hf["V_H"], x, sig) for x in mu])
                        if slot == "a":
                            m["pcf_components"] = {"mu_H": hf["mu_H"], "V_H": hf["V_H"], "sigma_eta": hf["sigma_eta"],
                                                   "gap": hf["gap"], "mu_D": dict(zip(te["province_code"], mu)),
                                                   "sigma_D": sig}
            meta[f"k{k}_{qs(t)}"] = m
            for arm, v in s.items():
                for i, r in te.iterrows():
                    preds.append({"target": target, "lead": k, "feature_quarter": qs(t),
                                  "origin": L.origin_of(t).date().isoformat(), "target_quarter": r["target_quarter"],
                                  "province_code": r["province_code"], "model": arm, "score": float(v[i]),
                                  "y": int(r["y"]), "y_last": float(r["y_last"]), "value": float(r["v"]), "threshold": tau})
    return pd.DataFrame(preds), meta


def equivalence():
    data = W.load(mask=False)
    out = {}
    E24RUN = guard.E24_DIR / "runs" / "20261013T160107Z"
    for target in ("T1", "T2"):
        P, _ = run_target(target, data, only_required=True)
        f = E24RUN / f"predictions_{target}.csv"
        seal = json.loads((E24RUN / f"SEAL_{target}.json").read_text())["sha256"]
        assert hashlib.sha256(f.read_bytes()).hexdigest() == seal
        E = pd.read_csv(f, dtype={"province_code": str})
        k = ["lead", "origin", "province_code", "model"]
        mm = P[P["model"].isin(REQ + ["MAJ_training_majority"])].merge(E[k + ["score", "y"]], on=k, suffixes=("", "_e24"))
        nE = int(E[E["model"].isin(REQ)].shape[0])
        out[target] = {"rows_compared": int(len(mm)), "e24_required_rows": nE,
                       "max_abs_diff": float((mm["score"] - mm["score_e24"]).abs().max()),
                       "labels_identical": bool((mm["y"] == mm["y_e24"]).all())}
    (EXP / "runs" / "equivalence_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


def main():
    check_frozen()
    if "--equivalence" in sys.argv:
        return equivalence()
    runid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rd = EXP / "runs" / runid
    rd.mkdir(parents=True)
    data = W.load(mask=True)
    seals = {}
    for target in ("T1", "T2"):
        P, meta = run_target(target, data)
        b = P.to_csv(index=False, lineterminator="\n").encode()
        (rd / f"predictions_{target}.csv").write_bytes(b)
        seals[target] = hashlib.sha256(b).hexdigest()
        (rd / f"fold_meta_{target}.json").write_text(json.dumps(meta, indent=1, default=jd), encoding="utf-8")
    import lightgbm, sklearn, scipy
    man = {"run_id": runid, "seals": seals, "window": [W.FIRST_Q, W.LAST_Q], "window_assertions": W.WINDOW_LOG,
           "masked_cells": data["masked"], "dnow_in_window_check": data["dnow_check"], "integrity": data["integrity"],
           "access_log": guard.ACCESS_LOG, "protocol": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8"),
           "versions": {"python": platform.python_version(), "lightgbm": lightgbm.__version__,
                        "sklearn": sklearn.__version__, "scipy": scipy.__version__, "numpy": np.__version__,
                        "pandas": pd.__version__}}
    (rd / "manifest.json").write_text(json.dumps(man, indent=1, default=jd), encoding="utf-8")
    print(runid, seals)
    print(json.dumps({"masked": data["masked"], "dnow_check": data["dnow_check"]}, indent=1, default=jd))


if __name__ == "__main__":
    main()

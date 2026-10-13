"""E24v2 class-A back-cast (BX): T2 = 1[D > 0], targets 1995..2020, never examined before.
FROZEN_EVALUATION_PROTOCOL.md sections 2-6.  Usage: python -B runner/run_bx.py   (refuses if the protocol changed
or if the comparability gate did not pass).  No value after 2020-Q4 enters training or testing."""
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
from scipy.stats import norm  # noqa: E402

import e23_lib as L  # noqa: E402
import run_e24 as R24  # noqa: E402

EXP = guard.EXP
qk, qs = L.qk, L.qs
FIRST, LAST = "1995-Q1", "2020-Q4"
P_COLS = R24.P_COLS
MODELS = ["B1_naive_persistence", "B1p_calibrated_persistence", "MAJ_training_majority", "CLIM_province_rate",
          "M1_lr_P_E24frozen", "M2_lgbm_P_E24frozen", "M3_pcf_D", "M4_pcf_D_now"]
CONFIRMATORY = {"HB1": ("M1_lr_P_E24frozen", "B1p_calibrated_persistence", "brier"),
                "HB2": ("M1_lr_P_E24frozen", "B1_naive_persistence", "acc"),
                "HB3": ("M4_pcf_D_now", "B1p_calibrated_persistence", "brier"),
                "HB4": ("M4_pcf_D_now", "B1_naive_persistence", "acc")}


def check_frozen():
    R24.check_frozen()
    gate = json.loads((EXP / "data" / "comparability_gate.json").read_text(encoding="utf-8"))
    if not gate["backcast_valid"]:
        raise SystemExit("E24v2 BX: comparability gate failed; the back-cast is void.")
    return gate


def load():
    q = pd.read_csv(EXP / "data" / "quarterly_D_1995_2025.csv", dtype={"province_code": str})
    dn = pd.read_csv(EXP / "data" / "dnow_1995_2025.csv", dtype={"province_code": str})
    q = q[q["quarter"].map(qk) <= qk(LAST)].dropna(subset=["D"])
    dn = dn[dn["quarter"].map(qk) <= qk(LAST)]
    assert q["quarter"].map(qk).max() <= qk(LAST) and dn["quarter"].map(qk).max() <= qk(LAST)
    V = q.rename(columns={"D": "v"})[["province_code", "quarter", "v"]].copy()
    V["tq"] = V["quarter"].map(qk)
    return V.reset_index(drop=True), dn


# ------------------------------------------------------------------------------------------ PCF-D models
def pcf_fit_predict(tr: pd.DataFrame, te: pd.DataFrame, xcols: list[str]) -> np.ndarray:
    """Least squares WITHOUT intercept of the target D on xcols; Gaussian P(D > 0) = Phi(mu / sigma)."""
    a = tr.dropna(subset=xcols + ["v"])
    X, y = a[xcols].to_numpy(float), a["v"].to_numpy(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    sig = float(np.sqrt((resid ** 2).sum() / max(len(y) - 1, 1)))
    Xt = te[xcols].to_numpy(float)
    assert not np.isnan(Xt).any(), "PCF test row without its predictor"
    return norm.cdf((Xt @ beta) / max(sig, 1e-9)), beta, sig


def calibrated_persistence(tr: pd.DataFrame, te: pd.DataFrame) -> np.ndarray:
    out = []
    for yl in te["y_last"].to_numpy():
        g = tr[tr["y_last"] == yl]
        out.append((g["y"].sum() + 1.0) / (len(g) + 2.0))
    return np.asarray(out, float)


def province_rate(tr: pd.DataFrame, te: pd.DataFrame) -> np.ndarray:
    s = tr.groupby("province_code")["y"].agg(["sum", "count"])
    return np.array([(s.loc[p, "sum"] + 1.0) / (s.loc[p, "count"] + 2.0) if p in s.index else 0.5
                     for p in te["province_code"]], float)


# ------------------------------------------------------------------------------------------ run
def run(V, dn):
    pub = lambda q, t: qk(q) <= t - 1      # noqa: E731  (T2 label rule, as E24)
    tmin, tmax = qk(FIRST), qk(LAST)
    X = pd.DataFrame([(p, t) for t in range(tmin, tmax + 1) for p in sorted(V["province_code"].unique())],
                     columns=["province_code", "t"])
    X["quarter"] = X["t"].map(qs)
    X = X.merge(dn[["province_code", "quarter", "Dnow", "rice_dev_now"]], on=["province_code", "quarter"], how="left")
    PR = {k: R24.pairs(X, V, k) for k in L.LEADS}
    cache: dict = {}
    PR = {k: R24.pblock(V, pub, PR[k], 0.0, cache) for k in L.LEADS}
    for k in L.LEADS:
        PR[k]["y"] = (PR[k]["v"] > 0).astype(int)
    allp = pd.concat(PR.values(), ignore_index=True)
    preds, meta = [], {}
    for k in L.LEADS:
        for t in range(tmin, tmax + 1):
            te = PR[k][PR[k]["t"] == t].sort_values("province_code").reset_index(drop=True)
            if len(te) != 5 or te["target_q"].iloc[0] > tmax:
                continue
            trp = allp[(allp["target_q"] <= t - 1) & (allp["t"] >= tmin)].copy()
            tr_s = trp[trp["lead"] == k].copy()
            if tr_s["target_q"].nunique() < L.MIN_TRAIN_QUARTERS or te["v_last"].isna().any() or te["Dnow"].isna().any():
                continue
            assert trp["target_q"].max() <= t - 1                          # no training target at/after the origin
            assert (te["target_q"] == t + k).all() and te["target_q"].max() <= tmax
            s, m = {}, {"lead": k, "feature_quarter": qs(t), "target_quarter": te["target_quarter"].iloc[0],
                        "n_train_quarters": int(tr_s["target_q"].nunique()), "test_HIGH": int(te["y"].sum())}
            s["B1_naive_persistence"] = te["y_last"].to_numpy(float)
            s["B1p_calibrated_persistence"] = calibrated_persistence(tr_s, te)
            s["MAJ_training_majority"] = np.full(5, 1.0 if tr_s["y"].mean() >= 0.5 else 0.0)
            s["CLIM_province_rate"] = province_rate(tr_s, te)
            s["M1_lr_P_E24frozen"] = L.fit_lr(tr_s, P_COLS, te)
            p, _, _, sel = R24.nested_lgbm(tr_s, trp, P_COLS, te, k)
            s["M2_lgbm_P_E24frozen"] = p
            m["cfg_M2"] = sel["config"]
            s["M3_pcf_D"], m["beta_M3"], m["sigma_M3"] = pcf_fit_predict(tr_s, te, ["v_last"])
            s["M4_pcf_D_now"], m["beta_M4"], m["sigma_M4"] = pcf_fit_predict(tr_s, te, ["Dnow", "v_last"])
            meta[f"k{k}_{qs(t)}"] = m
            for arm in MODELS:
                for i, r in te.iterrows():
                    preds.append({"target": "T2_BX", "lead": k, "feature_quarter": qs(t),
                                  "origin": L.origin_of(t).date().isoformat(), "target_quarter": r["target_quarter"],
                                  "province_code": r["province_code"], "model": arm, "score": float(s[arm][i]),
                                  "y": int(r["y"]), "y_last": float(r["y_last"]), "value": float(r["v"]),
                                  "threshold": 0.0})
    return pd.DataFrame(preds), meta


def halves(d, a, b, kind):
    o = sorted(d["origin"].unique())
    cut = o[len(o) // 2]
    out = []
    for part in (d[d["origin"] < cut], d[d["origin"] >= cut]):
        da = part[part["model"] == a].sort_values(["origin", "province_code"])
        db = part[part["model"] == b].sort_values(["origin", "province_code"])
        y = da["y"].to_numpy()
        if kind == "acc":
            v = float(((da["score"].to_numpy() >= .5) == y).mean() - ((db["score"].to_numpy() >= .5) == y).mean())
        else:
            v = float(((da["score"].to_numpy() - y) ** 2).mean() - ((db["score"].to_numpy() - y) ** 2).mean())
        out.append(v)
    return {"first_half": out[0], "second_half": out[1], "split_origin": cut}


def score(P):
    rows, res = [], {}
    for k in sorted(P["lead"].unique()):
        d = P[P["lead"] == k]
        f = d[d["model"] == "M4_pcf_D_now"]
        nH, nL, no = int(f["y"].sum()), int((1 - f["y"]).sum()), int(f["origin"].nunique())
        ev = no >= L.MIN_ORIGINS and nH >= L.MIN_PER_CLASS and nL >= L.MIN_PER_CLASS
        mm = {}
        for m in MODELS:
            dm = d[d["model"] == m].sort_values(["origin", "province_code"])
            mm[m] = R24.metrics(dm["y"], dm["score"])
            rows.append({"target": "T2_BX", "lead": int(k), "model": m, "n_rows": len(dm), "n_test_quarters": no,
                         "HIGH": nH, "LOW": nL, "evaluable": ev,
                         **{q: mm[m][q] for q in ("accuracy", "balanced_accuracy", "precision", "recall", "F1",
                                                  "specificity", "ROC_AUC", "Brier", "TP", "FP", "FN", "TN")}})
        tests = {a: {b: R24.compare(d, a, b) for b in MODELS if b != a}
                 for a in ("M1_lr_P_E24frozen", "M2_lgbm_P_E24frozen", "M3_pcf_D", "M4_pcf_D_now")}
        ci = {a: L.cluster_boot_auc(d[d["model"] == a].sort_values(["origin", "province_code"])["origin"].to_numpy(),
                                    d[d["model"] == a].sort_values(["origin", "province_code"])["y"].to_numpy(),
                                    d[d["model"] == a].sort_values(["origin", "province_code"])["score"].to_numpy())
              for a in ("M1_lr_P_E24frozen", "M4_pcf_D_now")}
        st = {h: halves(d, a, b, kind) for h, (a, b, kind) in CONFIRMATORY.items()}
        res[str(k)] = {"n_test_quarters": no, "HIGH": nH, "LOW": nL, "evaluable": ev, "metrics": mm, "tests": tests,
                       "auc_ci": ci, "halves": st}
    # confirmatory family: lead 1, Holm over HB1-HB4
    r1 = res["1"]
    raw = {}
    for h, (a, b, kind) in CONFIRMATORY.items():
        t = r1["tests"][a][b]
        raw[h] = t["brier_p_one_sided"] if kind == "brier" else t["acc_p_one_sided"]
    adj = L.holm(raw)
    conf = {}
    for h, (a, b, kind) in CONFIRMATORY.items():
        t, hv = r1["tests"][a][b], r1["halves"][h]
        eff = t["brier_diff"] if kind == "brier" else t["acc_diff"]
        good = (lambda v: v < 0) if kind == "brier" else (lambda v: v > 0)
        conf[h] = {"model": a, "baseline": b, "metric": kind, "effect": eff, "p_one_sided": raw[h], "p_holm": adj[h],
                   "halves": hv, "stable_both_halves": bool(good(hv["first_half"]) and good(hv["second_half"])),
                   "supported": bool(adj[h] < 0.05 and good(eff) and good(hv["first_half"]) and good(hv["second_half"]))}
    # lead-time reliability (E23 rule, vs B1; stricter vs B1p), Holm across leads, M4
    lt = {}
    for base in ("B1_naive_persistence", "B1p_calibrated_persistence"):
        pv = {k: res[k]["tests"]["M4_pcf_D_now"][base]["brier_p_one_sided"] for k in res}
        ad = L.holm(pv)
        ok = {k: bool(res[k]["evaluable"] and res[k]["auc_ci"]["M4_pcf_D_now"]["ci_low"] is not None and
                      res[k]["auc_ci"]["M4_pcf_D_now"]["ci_low"] > 0.5 and ad[k] < 0.05 and
                      res[k]["tests"]["M4_pcf_D_now"][base]["brier_diff"] < 0) for k in res}
        furthest = 0
        for k in sorted(res, key=int):
            if ok[k]:
                furthest = int(k)
            else:
                break
        lt[base] = {"per_lead_pass": ok, "p_holm": ad, "furthest_reliable_lead": furthest}
    return pd.DataFrame(rows), res, conf, lt


def main():
    gate = check_frozen()
    runid = "BX_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rd = EXP / "runs" / runid
    rd.mkdir(parents=True)
    V, dn = load()
    P, meta = run(V, dn)
    b = P.to_csv(index=False, lineterminator="\n").encode()
    (rd / "predictions_BX.csv").write_bytes(b)
    seal = hashlib.sha256(b).hexdigest()
    (rd / "SEAL_BX.json").write_text(json.dumps({"sha256": seal, "rows": len(P)}), encoding="utf-8")
    Pr = pd.read_csv(rd / "predictions_BX.csv", dtype={"province_code": str})
    rows, res, conf, lt = score(Pr)
    rows.to_csv(rd / "metrics_BX.csv", index=False, lineterminator="\n")
    (rd / "results_BX.json").write_text(json.dumps({"confirmatory": conf, "lead_time": lt, "by_lead": res},
                                                   indent=1, default=str), encoding="utf-8")
    (rd / "fold_meta_BX.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    import lightgbm, sklearn, scipy
    man = {"run_id": runid, "seal": seal, "gate": gate, "access_log": guard.ACCESS_LOG,
           "protocol": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8"),
           "versions": {"python": platform.python_version(), "lightgbm": lightgbm.__version__,
                        "sklearn": sklearn.__version__, "scipy": scipy.__version__, "numpy": np.__version__,
                        "pandas": pd.__version__}}
    (rd / "manifest.json").write_text(json.dumps(man, indent=1, default=str), encoding="utf-8")
    print(runid, seal)
    print(json.dumps(conf, indent=1, default=str))
    print(json.dumps({b: {"furthest": v["furthest_reliable_lead"], "pass": v["per_lead_pass"]} for b, v in lt.items()}))
    for k in sorted(res, key=int):
        r = res[k]
        print(k, r["n_test_quarters"], r["HIGH"], r["LOW"], {m: (round(r["metrics"][m]["accuracy"], 3),
                                                              round(r["metrics"][m]["Brier"], 3)) for m in MODELS})


if __name__ == "__main__":
    main()

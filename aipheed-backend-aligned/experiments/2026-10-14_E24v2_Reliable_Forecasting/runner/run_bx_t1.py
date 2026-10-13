"""E24v2 T1 back-cast (PROTOCOL_AMENDMENTS.md A2): the APPROVED label S1 = H + 2D on 1998-2020 quarters, once the owner
supplies and authorizes a long SWS Balance Luzon hunger file.  It cannot run without that file.

    python -B runner/run_bx_t1.py --sws <csv> --authorization <json> [--out <dir>]

SWS CSV columns (one row per survey round):
    quarter        fieldwork quarter, YYYY-QN (<= 2020-Q4; any later row aborts the run)
    H              % of families experiencing involuntary hunger, Balance Luzon
    published      publication date YYYY-MM-DD, or empty when unknown
    source         the document the value was taken from
Authorization JSON: {"authorized_by": ..., "authorized_on": ..., "authorized_files": [{"path": ..., "sha256": ...}]}

Timing (A2): a round counts at origin O(t) iff its publication date is before O(t), or, when unknown, iff its
fieldwork quarter <= t-1.  A label S1(p,q) is published iff q <= t-1 and every round of q counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e23_lib as L  # noqa: E402
import pcf  # noqa: E402
import run_e24 as R24  # noqa: E402

EXP = guard.EXP
qk, qs = L.qk, L.qs
LAST = "2020-Q4"
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
MODELS = ["B1_naive_persistence", "B1p_calibrated_persistence", "FINAL_V2_PCF", "PCF_NOW_A3", "M2_lgbm_P_E24frozen"]
CONF = {"HT1": ("FINAL_V2_PCF", "B1p_calibrated_persistence", "brier"),
        "HT2": ("FINAL_V2_PCF", "B1_naive_persistence", "acc"),
        "HT3": ("PCF_NOW_A3", "B1_naive_persistence", "acc")}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_inputs(sws: Path, auth: Path) -> dict:
    a = json.loads(auth.read_text(encoding="utf-8"))
    rec = {Path(r["path"]).name: r["sha256"] for r in a.get("authorized_files", [])}
    if not a.get("authorized_by") or not a.get("authorized_on"):
        raise SystemExit("authorization lacks authorized_by / authorized_on; refusing")
    if rec.get(sws.name) != sha(sws):
        raise SystemExit("the SWS file is not authorized by file name and SHA-256; refusing")
    for p in (EXP / "runner" / "PROTOCOL_SHA256.txt", EXP / "runner" / "AMENDMENTS_SHA256.txt"):
        h, f = p.read_text(encoding="utf-8").split()[:2]
        if sha(EXP / f) != h:
            raise SystemExit(f"{f} changed after it was frozen; refusing")
    return a


def load(sws: Path):
    r = pd.read_csv(sws, dtype=str)
    r["H"] = r["H"].astype(float)
    if (r["quarter"].map(qk) > qk(LAST)).any():
        raise SystemExit("the SWS file contains a round after 2020-Q4; refusing (A2: no row after 2020)")
    r["published"] = pd.to_datetime(r["published"].replace("", np.nan))
    gate = json.loads((EXP / "data" / "comparability_gate.json").read_text(encoding="utf-8"))
    if not gate["backcast_valid"]:
        raise SystemExit("comparability gate failed")
    q = pd.read_csv(EXP / "data" / "quarterly_D_1995_2025.csv", dtype={"province_code": str})
    n = pd.read_csv(EXP / "data" / "dnow_1995_2025.csv", dtype={"province_code": str})
    q = q[q["quarter"].map(qk) <= qk(LAST)].dropna(subset=["D"])
    Dm = {(a.province_code, qk(a.quarter)): a.D for a in q.itertuples()}
    Nm = {(a.province_code, qk(a.quarter)): a.Dnow for a in n.itertuples() if qk(a.quarter) <= qk(LAST)}
    H = r.groupby("quarter")["H"].mean()
    S = pd.DataFrame([{"province_code": p, "quarter": hq, "v": H[hq] + 2 * Dm[(p, qk(hq))]}
                      for hq in H.index for p in PROVS if (p, qk(hq)) in Dm])
    S["tq"] = S["quarter"].map(qk)
    return r, S, Dm, Nm


def usable(r: pd.DataFrame, t: int) -> pd.Series:
    o = L.origin_of(t)
    return np.where(r["published"].notna(), r["published"] < o, r["quarter"].map(qk) <= t - 1)


def make_pub(r: pd.DataFrame):
    cache = {}

    def pub(q, t):
        key = (q, t)
        if key not in cache:
            g = r[r["quarter"] == q]
            cache[key] = bool(len(g)) and qk(q) <= t - 1 and bool(usable(g, t).all())
        return cache[key]
    return pub


def d_model(Dm, Nm, t, k, now):
    X, y = [], []
    for tp in range(qk("1995-Q1") + 1, t - k):
        for p in PROVS:
            dl, dt = Dm.get((p, tp - 1)), Dm.get((p, tp + k))
            if dl is None or dt is None:
                continue
            if now:
                dn = Nm.get((p, tp))
                if dn is None:
                    continue
                X.append([dn, dl])
            else:
                X.append([dl])
            y.append(dt)
    return pcf.d_fit(np.asarray(X, float), np.asarray(y, float))


def run(r, S, Dm, Nm, leads):
    pub = make_pub(r)
    grid = pd.DataFrame([(p, t) for t in range(S["tq"].min(), qk(LAST) + 1) for p in PROVS], columns=["province_code", "t"])
    PR = {k: R24.pairs(grid, S, k) for k in leads}
    preds, cache = [], {}
    for k in leads:
        for t in sorted(PR[k]["t"].unique()):
            te = PR[k][PR[k]["t"] == t].sort_values("province_code").reset_index(drop=True)
            if len(te) != 5 or te["target_q"].iloc[0] > qk(LAST):
                continue
            okS = S[S["quarter"].map(lambda q: pub(q, t))]
            if okS.empty:
                continue
            tau = float(okS["v"].median())
            allp = pd.concat([PR[kk] for kk in leads], ignore_index=True)
            okq = {q: pub(q, t) for q in allp["target_quarter"].unique()}
            trp = allp[allp["target_quarter"].map(okq)].copy()
            trp["y"] = (trp["v"] > tau).astype(int)
            tr_s = trp[trp["lead"] == k]
            if tr_s["target_q"].nunique() < L.MIN_TRAIN_QUARTERS:
                continue
            assert trp["target_q"].max() <= t - 1
            trp = R24.pblock(S, pub, trp, tau, cache)
            tr_s = trp[trp["lead"] == k].copy()
            te = R24.pblock(S, pub, te.assign(y=(te["v"] > tau).astype(int)), tau, cache)
            if te["y_last"].isna().any():
                continue
            rr = r[usable(r, t)]
            if len(rr) < 2:
                continue
            hf = pcf.h_forecast(rr["quarter"].map(qk).to_numpy(float), rr["H"].to_numpy(float), float(t + k))
            sc = {"B1_naive_persistence": te["y_last"].to_numpy(float)}
            sc["B1p_calibrated_persistence"] = np.array([(tr_s.loc[tr_s["y_last"] == yl, "y"].sum() + 1) /
                                                         ((tr_s["y_last"] == yl).sum() + 2) for yl in te["y_last"]])
            for name, now in (("FINAL_V2_PCF", False), ("PCF_NOW_A3", True)):
                beta, sig = d_model(Dm, Nm, t, k, now)
                mu = [float(np.dot(beta, [Nm[(p, t)], Dm[(p, t - 1)]] if now else [Dm[(p, t - 1)]]))
                      for p in te["province_code"]]
                sc[name] = np.array([pcf.p_high(tau, hf["mu_H"], hf["V_H"], m, sig) for m in mu])
            p2, _, _, _ = R24.nested_lgbm(tr_s, trp, R24.P_COLS, te, k)
            sc["M2_lgbm_P_E24frozen"] = p2
            for m in MODELS:
                for i, row in te.iterrows():
                    preds.append({"target": "T1_BX", "lead": k, "feature_quarter": qs(t),
                                  "origin": L.origin_of(t).date().isoformat(), "target_quarter": row["target_quarter"],
                                  "province_code": row["province_code"], "model": m, "score": float(sc[m][i]),
                                  "y": int(row["y"]), "y_last": float(row["y_last"]), "value": float(row["v"]),
                                  "threshold": tau})
    return pd.DataFrame(preds)


def score(P):
    out = {}
    for k, d in P.groupby("lead"):
        mm = {m: R24.metrics(g.sort_values(["origin", "province_code"])["y"], g.sort_values(["origin", "province_code"])["score"])
              for m, g in d.groupby("model")}
        tests = {a: {b: R24.compare(d, a, b) for b in MODELS if b != a} for a in ("FINAL_V2_PCF", "PCF_NOW_A3")}
        out[str(k)] = {"n_test_quarters": int(d["origin"].nunique()), "HIGH": int(d[d.model == MODELS[0]]["y"].sum()),
                       "LOW": int((1 - d[d.model == MODELS[0]]["y"]).sum()), "metrics": mm, "tests": tests}
    conf = {}
    if "1" in out:
        raw = {h: out["1"]["tests"][a][b]["brier_p_one_sided" if kind == "brier" else "acc_p_one_sided"]
               for h, (a, b, kind) in CONF.items()}
        adj = L.holm(raw)
        for h, (a, b, kind) in CONF.items():
            t = out["1"]["tests"][a][b]
            conf[h] = {"model": a, "baseline": b, "metric": kind, "p_one_sided": raw[h], "p_holm": adj[h],
                       "effect": t["brier_diff"] if kind == "brier" else t["acc_diff"]}
    return out, conf


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sws", required=True)
    ap.add_argument("--authorization", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--leads", default="1,2,3,4,5,6,7,8")
    a = ap.parse_args(argv)
    sws, auth = Path(a.sws).resolve(), Path(a.authorization).resolve()
    rec = check_inputs(sws, auth)
    r, S, Dm, Nm = load(sws)
    P = run(r, S, Dm, Nm, [int(x) for x in a.leads.split(",")])
    if P.empty:
        raise SystemExit("no evaluable origin (too few labelled quarters)")
    rd = Path(a.out) if a.out else EXP / "runs" / ("BXT1_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    rd.mkdir(parents=True, exist_ok=True)
    b = P.to_csv(index=False, lineterminator="\n").encode()
    (rd / "predictions_T1_BX.csv").write_bytes(b)
    res, conf = score(P)
    (rd / "results_T1_BX.json").write_text(json.dumps({"seal": hashlib.sha256(b).hexdigest(), "authorization": rec,
                                                       "confirmatory": conf, "by_lead": res}, indent=1, default=str),
                                           encoding="utf-8")
    print(json.dumps(conf, indent=1, default=str))
    return rd


if __name__ == "__main__":
    main()

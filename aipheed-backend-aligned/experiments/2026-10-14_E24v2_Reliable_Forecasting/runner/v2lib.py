"""E24v2 shared data access and model application for classes B and C (FROZEN_EVALUATION_PROTOCOL.md).
Import after guard.install().  Reads only: E12 pinned files, authorized Jan-Jun 2026 CPI/SWS (via run_e23.load),
this experiment's acquired PSA series, and E24's sealed predictions (hash re-verified)."""
from __future__ import annotations

import hashlib
import io
import json

import numpy as np
import pandas as pd

import e23_lib as L
import guard
import pcf
import run_e24 as R24

qk, qs = L.qk, L.qs
EXP = guard.EXP
E24RUN = guard.E24_DIR / "runs" / "20261013T160107Z"
LONG_FIRST = "1995-Q1"


def load_e24_predictions(target: str) -> pd.DataFrame:
    p = E24RUN / f"predictions_{target}.csv"
    seal = json.loads((E24RUN / f"SEAL_{target}.json").read_text(encoding="utf-8"))["sha256"]
    assert hashlib.sha256(p.read_bytes()).hexdigest() == seal, f"E24 {target} predictions differ from their seal"
    return pd.read_csv(p, dtype={"province_code": str})


def load_all():
    comp, rounds, ff, gov_cols, V, log = R24.load()
    # long D panel: index-based back-cast <= 2020-Q4, approved E12 values 2021-2025, authorized 2026 H1
    bx = pd.read_csv(EXP / "data" / "quarterly_D_1995_2025.csv", dtype={"province_code": str})
    bx = bx[bx["quarter"].map(qk) <= qk("2020-Q4")].dropna(subset=["D"])[["province_code", "quarter", "D"]]
    t2 = V["T2"].rename(columns={"v": "D"})[["province_code", "quarter", "D"]]
    assert t2["quarter"].map(qk).min() == qk("2021-Q1") and t2["quarter"].map(qk).max() == qk("2026-Q2")
    Dall = pd.concat([bx, t2], ignore_index=True)
    assert not Dall.duplicated(["province_code", "quarter"]).any()
    # Dnow: months 1-2 of each quarter (index-based through 2025; authorized monthly YoY for 2026 H1)
    dn = pd.read_csv(EXP / "data" / "dnow_1995_2025.csv", dtype={"province_code": str})[["province_code", "quarter", "Dnow"]]
    c26 = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.COLL / "provincial_food_cpi_yoy_2026H1_raw.csv")),
                      dtype={"province_code": str})
    c26["month"] = c26["reference_month"].str[5:7].astype(int)
    c26 = c26[((c26["month"] - 1) % 3) < 2].copy()
    c26["quarter"] = c26["reference_month"].map(lambda m: f"{m[:4]}-Q{(int(m[5:7]) - 1) // 3 + 1}")
    c26["dev"] = c26["food_cpi_yoy_pct_raw"] - c26.groupby("reference_month")["food_cpi_yoy_pct_raw"].transform("mean")
    d26 = c26.groupby(["province_code", "quarter"])["dev"].mean().reset_index(name="Dnow")
    Dnow = pd.concat([dn, d26], ignore_index=True)
    assert not Dnow.duplicated(["province_code", "quarter"]).any()
    Dm = {(r.province_code, qk(r.quarter)): r.D for r in Dall.itertuples()}
    Nm = {(r.province_code, qk(r.quarter)): r.Dnow for r in Dnow.itertuples()}
    return {"comp": comp, "rounds": rounds, "V": V, "log": log, "Dm": Dm, "Nm": Nm, "Dall": Dall, "Dnow": Dnow}


PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]


def d_model(Dm, Nm, t: int, k: int, use_now: bool):
    """Fit PCF-D (M3) or PCF-D-NOW (M4) at origin O(t), lead k, on every pair with target t'+k <= t-1."""
    X, y = [], []
    for tp in range(qk(LONG_FIRST) + 1, t - k):           # t' + k <= t - 1
        for p in PROVS:
            dl, dt = Dm.get((p, tp - 1)), Dm.get((p, tp + k))
            if dl is None or dt is None:
                continue
            if use_now:
                dnw = Nm.get((p, tp))
                if dnw is None:
                    continue
                X.append([dnw, dl])
            else:
                X.append([dl])
            y.append(dt)
    beta, sig = pcf.d_fit(np.asarray(X, float), np.asarray(y, float))
    return beta, sig, len(y)


def d_predict(Dm, Nm, p: str, t: int, beta, use_now: bool) -> float:
    x = [Nm[(p, t)], Dm[(p, t - 1)]] if use_now else [Dm[(p, t - 1)]]
    return float(np.dot(beta, x))


def h_rounds(rounds: pd.DataFrame, origin: pd.Timestamp, include_supp: bool):
    r = rounds[rounds["published"] < origin]
    r = r[r["definition_A"] | (include_supp & (r["source"] == "supplementary"))]
    return r["quarter"].map(qk).to_numpy(float), r["H"].to_numpy(float)


def pcf_t1(data, t: int, k: int, tau: float, include_supp=False, n=pcf.N_SWS, dcache=None, use_now=False) -> dict:
    """P(HIGH) for every province at origin O(t), lead k. Returns {province: (p, details)}."""
    times, ys = h_rounds(data["rounds"], L.origin_of(t), include_supp)
    hf = pcf.h_forecast(times, ys, float(t + k), n)
    key = (t, k, use_now)
    if dcache is not None and key in dcache:
        beta, sig, nn = dcache[key]
    else:
        beta, sig, nn = d_model(data["Dm"], data["Nm"], t, k, use_now)
        if dcache is not None:
            dcache[key] = (beta, sig, nn)
    out = {}
    for p in PROVS:
        muD = d_predict(data["Dm"], data["Nm"], p, t, beta, use_now)
        out[p] = (pcf.p_high(tau, hf["mu_H"], hf["V_H"], muD, sig),
                  {**hf, "mu_D": muD, "sigma_D": sig, "beta_D": [float(b) for b in beta], "n_D_pairs": nn,
                   "mu_S1": hf["mu_H"] + 2 * muD, "tau": tau})
    return out


def t2_models(data, t: int, k: int, dcache=None) -> dict:
    out = {}
    for name, now in (("M3_pcf_D", False), ("M4_pcf_D_now", True)):
        key = (t, k, now)
        if dcache is not None and key in dcache:
            beta, sig, nn = dcache[key]
        else:
            beta, sig, nn = d_model(data["Dm"], data["Nm"], t, k, now)
            if dcache is not None:
                dcache[key] = (beta, sig, nn)
        out[name] = {p: (pcf.p_pos(d_predict(data["Dm"], data["Nm"], p, t, beta, now), sig),
                         {"beta": [float(b) for b in beta], "sigma": sig, "n_pairs": nn}) for p in PROVS}
    return out


def calibrated_persistence(tr: pd.DataFrame, y_last_te) -> np.ndarray:
    out = []
    for yl in y_last_te:
        g = tr[tr["y_last"] == yl]
        out.append((g["y"].sum() + 1.0) / (len(g) + 2.0))
    return np.asarray(out, float)


def t1_training(data, t: int, k: int, tau: float, cache: dict, first="2021-Q1"):
    """E24-identical T1 training pairs (published before O(t), feature quarter >= 2021-Q1) with the P block,
    for every lead (pooled) and for lead k. Uses a (province, t) grid: only label history is needed."""
    V = data["V"]["T1"]
    pub = R24.make_pub("T1", data["rounds"])
    grid = pd.DataFrame([(p, tt) for tt in range(qk(first), t) for p in PROVS], columns=["province_code", "t"])
    allp = pd.concat([R24.pairs(grid, V, kk) for kk in L.LEADS], ignore_index=True)
    okq = {q: pub(q, t) for q in allp["target_quarter"].unique()}
    pubp = allp[allp["target_quarter"].map(okq)].copy()
    pubp["y"] = (pubp["v"] > tau).astype(int)
    assert pubp["target_q"].max() <= t - 1
    pubp = R24.pblock(V, pub, pubp, tau, cache)
    return pubp, pubp[pubp["lead"] == k].copy(), pub


def t2_training_long(data, t: int, k: int):
    """T2 training pairs over the long D history (1995+) with y_last = 1[D(t'-1) > 0]."""
    Dm, rows = data["Dm"], []
    for tp in range(qk(LONG_FIRST) + 1, t - k):
        for p in PROVS:
            dl, dt = Dm.get((p, tp - 1)), Dm.get((p, tp + k))
            if dl is not None and dt is not None:
                rows.append({"y_last": float(dl > 0), "y": int(dt > 0)})
    return pd.DataFrame(rows)

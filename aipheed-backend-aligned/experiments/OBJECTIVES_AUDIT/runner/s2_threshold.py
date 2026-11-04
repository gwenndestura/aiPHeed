"""S2 (S2_ADDENDUM.md, hash checked): K1 with a walk-forward decision threshold, evaluated descriptively.

    python s2_threshold.py   # -> ../out/s2_results.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
ADD = HERE / "S2_ADDENDUM.md"
OUT = HERE / "out"
sys.path.insert(0, str(EXP / "NEW_MODEL" / "ALLBASE" / "runner"))
import phase_c as PC  # noqa: E402

V, H, R = PC.V, PC.H, PC.R
GRID = [round(0.30 + 0.05 * i, 2) for i in range(9)]


def check() -> str:
    b = ADD.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"ADDENDUM-SHA256: ") and last.split()[1].decode() == h, "S2 addendum changed"
    return h


def bal(p, y, tau):
    c = (p >= tau).astype(int)
    pos, neg = y == 1, y == 0
    if not pos.any() or not neg.any():
        return np.nan
    return 0.5 * ((c[pos] == 1).mean() + (c[neg] == 0).mean())


def choose(P: pd.DataFrame, y: dict, known: set, t: int) -> tuple[float, int]:
    g = P[(P["t"] < t) & P["q"].isin(known)]
    if len(g) < PC.WMIN_PAIRS:
        return 0.5, int(len(g))
    yy = g["q"].map(y).to_numpy(int)
    sc = {tau: round(float(bal(g["K1"].to_numpy(), yy, tau)), 12) for tau in GRID}
    return max(GRID, key=lambda tau: (sc[tau], -abs(tau - 0.5), -tau)), int(len(g))


def remap(p: float, tau: float) -> float:
    """Monotone map with p' >= 0.5 exactly when p >= tau, so the frozen R1-R7 code sees S2's classes."""
    return 0.5 * p / tau if p < tau else 0.5 + 0.5 * (p - tau) / (1 - tau)


def main():
    pre = check()
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    y = dict(zip(lab_bl["q"].astype(int), lab_bl["y"].astype(int)))
    B = pd.read_csv(HERE.parent / "NEW_MODEL" / "ALLBASE" / "out" / "blends.csv")
    rng = np.random.default_rng(PC.SEED)
    rows, leak = [], True
    for k in (1, 2):
        P = B[B["lead"] == k][["t", "q", "K1"]].sort_values("t")
        for t in P["t"]:
            known = H.complete_bl(d, t)
            tau, n = choose(P, y, known, t)
            for _ in range(PC.REPS):
                Q = P.copy()
                Q.loc[Q["t"] >= t, "K1"] = rng.uniform(0, 1, int((Q["t"] >= t).sum()))
                yq = {q: (v if q in known else int(rng.integers(0, 2))) for q, v in y.items()}
                if choose(Q, yq, known, t) != (tau, n):
                    leak = False
            p = float(P[P["t"] == t]["K1"].iloc[0])
            rows.append({"t": t, "lead": k, "q": int(P[P["t"] == t]["q"].iloc[0]), "K1": p, "tau": tau, "n_past": n,
                         "S2": remap(p, tau)})
    S = pd.DataFrame(rows)
    S.to_csv(OUT / "s2_forecasts.csv", index=False)
    CBF = pd.read_csv(PC.N.OUT / "forecasts.csv")
    L = pd.read_csv(PC.N.LEADS_FILE)
    comp = pd.concat([CBF[CBF["name"] == "C-b"][["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      S[["t", "lead", "q", "K1"]].rename(columns={"K1": "p"}).assign(name="K1"),
                      S[["t", "lead", "q", "S2"]].rename(columns={"S2": "p"}).assign(name="S2")], ignore_index=True)
    res = {"addendum_sha256": pre, "threshold_leakage_unchanged": leak, "label": "DESCRIPTIVE; adoption impossible (G2)",
           "leads": {}}
    for k in (1, 2):
        W = R.frame(comp, k, lab_bl).dropna(subset=["C-b", "K1", "S2"])
        Lk = {}
        for n in ("C-b", "K1", "S2"):
            s = PC._summ(W, n)
            if n == "S2":
                s["metrics"]["brier_of_K1_probability"] = float(((W["K1"] - W["y"]) ** 2).mean())
                s["metrics"]["auc_of_K1_probability"] = Lk["K1"]["metrics"]["auc"]
                s["note"] = "R5 and the Brier/AUC shown by the frozen code use the remapped probability; S2's true " \
                            "probability is K1's"
            Lk[n] = s
        ev = S[(S["lead"] == k) & S["q"].between(H.EVAL_FIRST, H.EVAL_LAST)]
        Lk["tau"] = {"min": float(ev["tau"].min()), "median": float(ev["tau"].median()), "max": float(ev["tau"].max())}
        res["leads"][str(k)] = Lk
    (OUT / "s2_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("leakage unchanged:", leak)
    for k in ("1", "2"):
        for n in ("C-b", "K1", "S2"):
            m = res["leads"][k][n]["metrics"]
            print(f"L{k} {n:4s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} failed {res['leads'][k][n]['failed']}")
        print("   tau", res["leads"][k]["tau"])


if __name__ == "__main__":
    main()

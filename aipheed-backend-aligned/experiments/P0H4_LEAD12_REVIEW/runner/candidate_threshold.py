"""Candidate T (PROTOCOL.md): rolling-origin decision threshold chosen on earlier labelled forecasts only.
Read-only inputs; writes out/candidate_threshold.json. Refuses to run if PROTOCOL.md differs from its frozen hash."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from reproduce import HERE, OUT, P, ROOT, load, rules, scores

GRID = [round(x, 2) for x in np.arange(0.05, 0.951, 0.05)]


def frozen_ok() -> None:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    have = hashlib.sha256((HERE.parent / "PROTOCOL.md").read_bytes()).hexdigest()
    assert want == have, "PROTOCOL.md changed after freezing"


def issue_of(t: int) -> str:
    n = t + 1
    return f"{n // 4}-{3 * (n % 4) + 1:02d}-01"


def label_known(q: int, t: int, rounds: pd.DataFrame) -> bool:
    if q > t - 1:
        return False
    rq = rounds[rounds["qi"] == q]
    return len(rq) > 0 and bool((rq["published"] < issue_of(t)).all())


def bal(y: np.ndarray, yh: np.ndarray) -> float:
    pos, neg = y.sum(), len(y) - y.sum()
    return ((((yh == 1) & (y == 1)).sum() / pos) + (((yh == 0) & (y == 0)).sum() / neg)) / 2


def choose(train: pd.DataFrame) -> float:
    if len(train) < 20 or train["y"].sum() < 3:
        return 0.5
    y, p = train["y"].to_numpy(int), train[P].to_numpy(float)
    best = max(GRID, key=lambda c: (round(bal(y, (p >= c).astype(int)), 10), -abs(c - 0.5)))
    return float(best)


def main():
    frozen_ok()
    d = load()
    s = pd.read_csv(ROOT / "backend" / "data" / "inputs" / "sws_rounds.csv")
    s = s[~s["round"].str.startswith("Stratbase")].copy()
    s["qi"] = s["quarter"].map(lambda q: int(q[:4]) * 4 + int(q[-1]) - 1)
    out = {"protocolSha256": (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0], "trials": 2}
    for k in (1, 2):
        g = d[d["lead"] == k].copy()
        thr = {}
        for t in sorted(g["t"].unique()):
            train = g[[label_known(q, t, s) and tt < t for q, tt in zip(g["q"], g["t"])]]
            thr[int(t)] = (choose(train), len(train), int(train["y"].sum()))
        g["thr"] = g["t"].map(lambda t: thr[int(t)][0])
        g["p_cand"] = (g[P] >= g["thr"]).astype(float) * 0.999 + (g[P] < g["thr"]).astype(float) * 0.001
        cand = scores(g, "p_cand")
        cand.update({k2: None for k2 in ("auc", "prAuc", "brier")})          # a threshold changes no probability
        gc = g.assign(**{P: g["p_cand"]})
        cand_rules = rules(gc)
        r5 = rules(g)["R5 Brier < PERSIST-SI and < CLIM, one-sided cluster p < 0.10"]
        cand_rules["R5 Brier < PERSIST-SI and < CLIM, one-sided cluster p < 0.10"] = {**r5, "note": "probabilities unchanged"}
        out[f"lead{k}"] = {"current": scores(g), "candidate": cand, "candidateRules": cand_rules,
                           "thresholdByOrigin": {f"{t // 4}-Q{t % 4 + 1}": {"threshold": v[0], "trainRows": v[1], "trainHigh": v[2]}
                                                 for t, v in thr.items()}}
    l1_ok = all(v["pass"] for v in out["lead1"]["candidateRules"].values())
    for k in (1, 2):
        ok = all(v["pass"] for v in out[f"lead{k}"]["candidateRules"].values())
        out[f"lead{k}"]["decision"] = ("recommend for approval" if ok and l1_ok else "negative result: not recommended")
    (OUT / "candidate_threshold.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for k in (1, 2):
        o = out[f"lead{k}"]
        for name in ("current", "candidate"):
            m = o[name]
            print(f"LEAD {k} {name:9s} acc {m['accuracy']:.4f} bal {m['balanced']:.4f} P {m['precision'] or 0:.3f} R {m['recall']:.3f} "
                  f"spec {m['specificity']:.3f} F1 {m['f1']:.3f} TP/FP/FN/TN {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']}")
        print("   thresholds:", {q: v["threshold"] for q, v in o["thresholdByOrigin"].items()})
        print("   rules:", {r.split()[0]: v["pass"] for r, v in o["candidateRules"].items()}, "->", o["decision"])


if __name__ == "__main__":
    main()

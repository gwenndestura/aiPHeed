"""E197 (docs/e197/PROTOCOL.md): F1-maximising cut-off on training rows for E196. Local only.   python -m app.e197.run"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e168 import lgbm_only as E
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e191 import run as R
from app.e194 import run as E194

warnings.filterwarnings("ignore")
OUT = K.D / "e197" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e197" / "PROTOCOL.md"
GRID = tuple(round(0.30 + 0.05 * k, 2) for k in range(9))
SETS = {"ENNS2018": ("ENNS2018", 1), "ENNS2019": ("ENNS2019", 1), "ENNS2021_L12": ("ENNS2021", 1), "ENNS2021_L3": ("ENNS2021", 3)}


def part(name, rank):
    s, l = SETS[name]
    tr, te, AN = R.load(R.FR / f"{s}_L{l}_main.pkl")
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cfg = E194.stage_a_ranked(tr, AN, folds)[rank][2]
    stream = RT.job_id(s, l, "main")
    oofs = [R.run_cfg(tr, te, AN, folds, cfg, R.spec_of("e184"), seed, stream)[1] for seed in E194.SEEDS]
    return name, rank, np.mean(oofs, axis=0)


def f1(p, y, t):
    pr = p >= t
    tp, fp, fn = int((pr & y).sum()), int((pr & ~y).sum()), int((~pr & y).sum())
    return 2 * tp / max(1, 2 * tp + fp + fn)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    log("start", protocol_sha256=K.sha256(PROTOCOL))
    res = Parallel(n_jobs=R.N_JOBS, verbose=5)(delayed(part)(n, r) for n in SETS for r in range(E194.TOPK))
    cut = {}
    for n, (s, l) in SETS.items():
        tr = R.load(R.FR / f"{s}_L{l}_main.pkl")[0]
        oof = np.mean([o for nn, _, o in res if nn == n], axis=0)
        y = tr["y_true"].values
        gap = tr["gap_q"].values.astype(float)
        p = norm.cdf(oof / E.A4.scale(y - oof, gap, gap)[0])
        yy = y >= 0
        sc = {t: f1(p, yy, t) for t in GRID}
        best = max(GRID, key=lambda t: (round(sc[t], 12), -abs(t - 0.5)))
        cut[n] = {"cutoff": best, "train_f1": {str(t): round(v, 4) for t, v in sc.items()}, "train_high_share": round(float(yy.mean()), 3)}
    log("cutoffs", **{n: c["cutoff"] for n, c in cut.items()})
    # apply to E196's outer probabilities
    P = pd.read_csv(K.D / "e196" / "out" / "e194_rerun_rows.csv")
    W = P.pivot_table(index=["key", "survey"], columns="lead", values="p")
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    out = {"protocol": "docs/e197/PROTOCOL.md", "cutoffs": cut, "leads": {}}
    dec = []
    for L in (1, 2, 3):
        s_ = (W[[1, 2]].mean(axis=1) if L == 1 else W[L]).rename("p").reset_index()
        x = G[G["lead"] == L].merge(s_, on=["key", "survey"])
        assert len(x) == 72
        def t_of(sv):
            return cut["ENNS2021_L3" if (sv == "ENNS2021" and L >= 3) else ("ENNS2021_L12" if sv == "ENNS2021" else sv)]["cutoff"]
        x["t"] = x["survey"].map(t_of)
        y = x["y_high"].astype(bool).values
        r = {}
        for nm, pred in (("E196", x["p"].values >= 0.5), ("E197", x["p"].values >= x["t"].values)):
            tp, fp, fn, tn = int((pred & y).sum()), int((pred & ~y).sum()), int((~pred & y).sum()), int((~pred & ~y).sum())
            r[nm] = {"accuracy": round((tp + tn) / 72, 4), "f1": round(2 * tp / (2 * tp + fp + fn), 4), "precision": round(tp / max(1, tp + fp), 3),
                     "recall": round(tp / (tp + fn), 3), "tp": tp, "fp": fp, "fn": fn, "tn": tn}
        out["leads"][L] = r
        dec.append(r["E197"]["f1"] >= 0.75 and r["E197"]["f1"] >= r["E196"]["f1"] and r["E197"]["accuracy"] >= r["E196"]["accuracy"])
    out["decision"] = "E197 cut-off adopted" if all(dec) else "E197 not adopted: E196 keeps 0.50 (F1 0.772 / 0.759 / 0.746)"
    K.dump_json(out, OUT / "results.json")
    log("evaluated", decision=out["decision"])
    print(json.dumps({n: c["cutoff"] for n, c in cut.items()}), {n: c["train_high_share"] for n, c in cut.items()})
    for L, r in out["leads"].items():
        print(f"L{L}: E196 {r['E196']} | E197 {r['E197']}")
    print(out["decision"])


if __name__ == "__main__":
    main()

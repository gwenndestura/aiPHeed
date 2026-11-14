"""E194 (docs/e194/PROTOCOL.md): mean of E184 over the top-5 Stage-A configurations, 20 draws each. Local only."""
from __future__ import annotations

import time
import warnings
from itertools import product

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import binomtest
from sklearn.model_selection import GroupKFold

from app.e168 import lgbm_only as E
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e191 import run as R

warnings.filterwarnings("ignore")
OUT = K.D / "e194" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e194" / "PROTOCOL.md"
SEEDS = tuple(range(17901, 17921))
LEADS = (1, 2, 3, 4, 5, 6)
TOPK = 5


def stage_a_ranked(tr, AN, folds):
    """E168's Stage A loop (app.e182.candidate.stage_a), returning every configuration ranked by inner SSE (stable)."""
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    out = []
    for k, (a, f, pr, h) in enumerate(product(E.ANCH, E.FS, (False, True), E.HPO)):
        atr = AN[a][0]
        oof = np.zeros(len(tr))
        for i_tr, i_te in folds:
            oof[i_te] = atr[i_te] + E.LGBRes(E.FS[f], *h, pr).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
        out.append((float(np.sum(w * (y - oof) ** 2)), k, (a, f, pr, h)))
    out.sort(key=lambda t: (t[0], t[1]))
    return out


def job(survey, lead):
    t0 = time.time()
    tr, te, AN = R.load(R.FR / f"{survey}_L{lead}_main.pkl")
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    ranked = stage_a_ranked(tr, AN, folds)[:TOPK]
    stream = RT.job_id(survey, lead, "main")
    rows = []
    for rank, (sse, _, cfg) in enumerate(ranked, 1):
        for s in SEEDS:
            mu, p, half = R.run_cfg(tr, te, AN, folds, cfg, R.spec_of("e184"), s, stream)[0]
            o = te[RT.KEYS].copy()
            o["rank"], o["cfg"], o["inner_sse"], o["seed"], o["p"] = rank, "|".join(map(str, cfg)), sse, s, p
            rows.append(o)
    return {"rows": pd.concat(rows, ignore_index=True), "job": stream, "cfgs": [("|".join(map(str, c)), round(s, 3)) for s, _, c in ranked],
            "seconds": round(time.time() - t0, 1)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    log("start", protocol_sha256=K.sha256(PROTOCOL))
    order = sorted([(s, l) for s in RT.SURVEYS for l in LEADS], key=lambda t: t[0] != "ENNS2021")
    J = Parallel(n_jobs=R.N_JOBS, verbose=5)(delayed(job)(s, l) for s, l in order)
    for j in J:
        log("job", job=j["job"], cfgs=j["cfgs"], seconds=j["seconds"])
    S = pd.concat([j["rows"] for j in J], ignore_index=True)
    S.to_csv(OUT / "per_cfg_seed_rows.csv", index=False, lineterminator="\n")
    e84, _ = R._stored()
    c193 = pd.read_csv(K.D / "e193" / "out" / "per_seed_rows.csv").groupby(RT.KEYS)["p"].mean().reset_index().rename(columns={"p": "E184conv"})
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    rep = S[(S["rank"] == 1) & (S["seed"] <= 17905)].groupby(RT.KEYS)["p"].mean().reset_index().merge(e84.rename(columns={"p": "ps"}), on=RT.KEYS)
    res = {"protocol": "docs/e194/PROTOCOL.md", "reproduction_rank1_5draws_vs_E184": float(np.max(np.abs(rep["p"] - rep["ps"]))), "leads": {}}
    arms = {"E194": S.groupby(RT.KEYS)["p"].mean(), "E194_k3": S[S["rank"] <= 3].groupby(RT.KEYS)["p"].mean()}
    for L in LEADS:
        x = G[G["lead"] == L].merge(e84.rename(columns={"p": "E184"}), on=RT.KEYS).merge(c193, on=RT.KEYS)
        for a, v in arms.items():
            x = x.merge(v.reset_index().rename(columns={"p": a}), on=RT.KEYS)
        assert len(x) == 72
        y = x["y_high"].astype(bool)
        d = {"metrics": {a: R.metrics(y, x[a], x["q_true"]) for a in ("PERS", "E184", "E184conv", "E194", "E194_k3")}}
        for a in ("E194", "E194_k3"):
            v = E.E7.diff_ci(x, a, "E184conv", "q_true", np.random.default_rng(194), n=2000)
            vp = E.E7.diff_ci(x, a, "PERS", "q_true", np.random.default_rng(194), n=2000)
            cA, cB = (x[a] >= .5) == y, (x["E184conv"] >= .5) == y
            b, c = int((cA & ~cB).sum()), int((~cA & cB).sum())
            d[a] = {"brier_minus_E184conv": [round(v["diff"], 5), [round(t, 5) for t in v["ci95"]]],
                    "mcnemar": {"only_this_right": b, "only_E184conv_right": c, "p": round(float(binomtest(b, b + c, .5).pvalue), 4) if b + c else 1.0},
                    "owner_rule": bool(d["metrics"][a]["accuracy"] >= .75 and vp["ci95"][1] < 0)}
        res["leads"][L] = d
    dec = {}
    for a in ("E194", "E194_k3"):
        acc = [res["leads"][L]["metrics"][a]["accuracy"] - res["leads"][L]["metrics"]["E184conv"]["accuracy"] for L in LEADS]
        br = [res["leads"][L]["metrics"][a]["brier"] - res["leads"][L]["metrics"]["E184conv"]["brier"] for L in LEADS]
        dec[a] = {"acc_ge_all": all(z >= -1e-9 for z in acc), "brier_le_all": all(z <= 1e-12 for z in br), "acc_gt_any": any(z > 1e-9 for z in acc)}
        dec[a]["qualifies"] = all(dec[a].values())
    res["decision_checks"] = dec
    res["decision"] = "E194 preferred to E184 (candidate only)" if dec["E194"]["qualifies"] else "E194 does not meet the rule: E184 stays"
    K.dump_json(res, OUT / "results.json")
    K.write_hashes([OUT / n for n in ("per_cfg_seed_rows.csv", "results.json", "run_log.jsonl")], OUT / "hashes.json")
    log("evaluated", decision=res["decision"])
    print("repro:", res["reproduction_rank1_5draws_vs_E184"])
    for L in LEADS:
        M = res["leads"][L]["metrics"]
        print(f"L{L}: " + " | ".join(f"{a} {100*M[a]['accuracy']:.1f}% FA{M[a]['false_positives']} miss{M[a]['false_negatives']} B{M[a]['brier']:.4f}" for a in ("E184", "E184conv", "E194", "E194_k3")),
              "| E194 vs conv", res["leads"][L]["E194"]["mcnemar"], res["leads"][L]["E194"]["brier_minus_E184conv"], "rule", res["leads"][L]["E194"]["owner_rule"])
    print(dec)
    print(res["decision"])


if __name__ == "__main__":
    main()

"""E193 (docs/e193/PROTOCOL.md): E184 with 100 synthetic draws per (survey, lead). Local only.   python -m app.e193.run"""
from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import binomtest
from sklearn.model_selection import GroupKFold

from app.e168 import lgbm_only as E
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e182 import candidate as C182
from app.e191 import run as R

warnings.filterwarnings("ignore")
OUT = K.D / "e193" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e193" / "PROTOCOL.md"
SEEDS = tuple(range(17901, 18001))
LEADS = (1, 2, 3, 4, 5, 6)


def job(survey, lead):
    t0 = time.time()
    tr, te, AN = R.load(R.FR / f"{survey}_L{lead}_main.pkl")
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cfg, _ = C182.stage_a(tr, AN, folds)
    stream = RT.job_id(survey, lead, "main")
    out = []
    for s in SEEDS:
        mu, p, half = R.run_cfg(tr, te, AN, folds, cfg, R.spec_of("e184"), s, stream)[0]
        o = te[RT.KEYS].copy()
        o["seed"], o["mu"], o["p"], o["half"] = s, mu, p, half
        out.append(o)
    return {"rows": pd.concat(out, ignore_index=True), "job": stream, "seconds": round(time.time() - t0, 1)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    log("start", protocol_sha256=K.sha256(PROTOCOL), seeds=[SEEDS[0], SEEDS[-1]])
    order = sorted([(s, l) for s in RT.SURVEYS for l in LEADS], key=lambda t: t[0] != "ENNS2021")
    J = Parallel(n_jobs=R.N_JOBS, verbose=5)(delayed(job)(s, l) for s, l in order)
    for j in J:
        log("job", job=j["job"], seconds=j["seconds"])
    S = pd.concat([j["rows"] for j in J], ignore_index=True)
    S.to_csv(OUT / "per_seed_rows.csv", index=False, lineterminator="\n")
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    e84, _ = R._stored()
    res = {"protocol": "docs/e193/PROTOCOL.md", "leads": {}}
    first5 = S[S["seed"] <= 17905].groupby(RT.KEYS)["p"].mean().reset_index().merge(e84.rename(columns={"p": "ps"}), on=RT.KEYS)
    res["reproduction_first5_vs_E184_max_abs_diff_p"] = float(np.max(np.abs(first5["p"] - first5["ps"])))
    for L in LEADS:
        x = G[G["lead"] == L][RT.KEYS + ["y_high", "q_true", "PERS", "region"]]
        s = S[S["lead"] == L]
        y = x["y_high"].astype(bool).values
        curve = {}
        for n in (5, 10, 20, 50, 100):
            m = s[s["seed"] < 17901 + n].groupby(RT.KEYS)["p"].mean().reset_index()
            z = x.merge(m, on=RT.KEYS)
            curve[n] = {"accuracy": round(float(((z["p"] >= .5) == z["y_high"].astype(bool)).mean()), 4), "brier": round(float(np.mean((z["p"] - z["q_true"]) ** 2)), 5)}
        single = s.merge(x, on=RT.KEYS).assign(ok=lambda d: (d["p"] >= .5) == d["y_high"].astype(bool)).groupby("seed")["ok"].mean()
        b5 = s.assign(block=(s["seed"] - 17901) // 5).groupby(["block"] + RT.KEYS)["p"].mean().reset_index().merge(x, on=RT.KEYS)
        b5 = b5.assign(ok=(b5["p"] >= .5) == b5["y_high"].astype(bool)).groupby("block")["ok"].mean()
        z = x.merge(s.groupby(RT.KEYS)["p"].mean().reset_index().rename(columns={"p": "E193"}), on=RT.KEYS).merge(e84.rename(columns={"p": "E184"}), on=RT.KEYS)
        assert len(z) == 72
        yy = z["y_high"].astype(bool)
        v = E.E7.diff_ci(z, "E193", "E184", "q_true", np.random.default_rng(193), n=2000)
        vp = E.E7.diff_ci(z, "E193", "PERS", "q_true", np.random.default_rng(193), n=2000)
        cA, cB = (z["E193"] >= .5) == yy, (z["E184"] >= .5) == yy
        b, c = int((cA & ~cB).sum()), int((~cA & cB).sum())
        res["leads"][L] = {"E184": R.metrics(yy, z["E184"], z["q_true"]), "E193": R.metrics(yy, z["E193"], z["q_true"]),
                           "brier_minus_E184": [round(v["diff"], 5), [round(t, 5) for t in v["ci95"]]],
                           "mcnemar": {"only_E193_right": b, "only_E184_right": c, "p": round(float(binomtest(b, b + c, .5).pvalue), 4) if b + c else 1.0},
                           "owner_rule_E193": bool(((z["E193"] >= .5) == yy).mean() >= .75 and vp["ci95"][1] < 0),
                           "convergence": curve,
                           "single_draw_accuracy": {"mean": round(float(single.mean()), 4), "sd": round(float(single.std()), 4), "min": round(float(single.min()), 4), "max": round(float(single.max()), 4)},
                           "five_draw_blocks_accuracy": {"mean": round(float(b5.mean()), 4), "sd": round(float(b5.std()), 4), "min": round(float(b5.min()), 4), "max": round(float(b5.max()), 4), "n_blocks": int(len(b5))}}
    K.dump_json(res, OUT / "results.json")
    K.write_hashes([OUT / n for n in ("per_seed_rows.csv", "results.json", "run_log.jsonl")], OUT / "hashes.json")
    log("done")
    print("repro:", res["reproduction_first5_vs_E184_max_abs_diff_p"])
    for L, d in res["leads"].items():
        print(f"L{L}: E184 {100*d['E184']['accuracy']:.1f}% FA{d['E184']['false_positives']} B{d['E184']['brier']:.4f} | E193 {100*d['E193']['accuracy']:.1f}% FA{d['E193']['false_positives']} miss{d['E193']['false_negatives']} B{d['E193']['brier']:.4f} "
              f"| {d['mcnemar']} {d['brier_minus_E184']} rule {d['owner_rule_E193']} | curve {d['convergence']} | single {d['single_draw_accuracy']} | 5-draw blocks {d['five_draw_blocks_accuracy']}")


if __name__ == "__main__":
    main()

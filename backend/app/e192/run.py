"""
E192 (docs/e192/PROTOCOL.md): trajectory-consistent, correlation-preserving synthetic rows. One job per (survey, lead),
so E184 reproduces exactly. Local only.

    python -m app.e192.run
"""
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
from app.e191 import gens as GN
from app.e191 import run as R

warnings.filterwarnings("ignore")
OUT = K.D / "e192" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e192" / "PROTOCOL.md"
SEEDS20 = tuple(range(17901, 17921))
LEADS = (1, 2, 3, 4, 5, 6)


def job(survey, lead):
    t0 = time.time()
    tr, te, AN = R.load(R.FR / f"{survey}_L{lead}_main.pkl")
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cfg, _ = C182.stage_a(tr, AN, folds)
    stream = RT.job_id(survey, lead, "main")
    out, qual = [], None
    for arm, spec, seeds in (("E184", R.spec_of("e184"), SEEDS20[:5]), ("traj", R.spec_of("traj"), SEEDS20[:5]),
                             ("trajcorr", {"gens": [("trajcorr", 1.0)]}, SEEDS20)):
        runs = []
        for k, s in enumerate(seeds):
            P, _, _, q = R.run_cfg(tr, te, AN, folds, cfg, spec, s, stream, want_quality=(arm == "trajcorr" and k == 0))
            runs.append(P)
            qual = q or qual
        sets = {"E184": [("E184", runs)], "traj": [("traj", runs)], "trajcorr": [("E192", runs[:5]), ("E192_20", runs)]}[arm]
        for name, rs in sets:
            o = te[RT.KEYS].copy()
            o["arm"] = name
            o["mu"], o["p"], o["half"] = (np.mean([np.asarray(r[k], float) for r in rs], axis=0) for k in range(3))
            out.append(o)
    return {"rows": pd.concat(out, ignore_index=True), "job": stream, "quality": qual, "seconds": round(time.time() - t0, 1)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    log("start", protocol_sha256=K.sha256(PROTOCOL))
    J = Parallel(n_jobs=R.N_JOBS, verbose=5)(delayed(job)(s, l) for s in RT.SURVEYS for l in LEADS)
    for j in J:
        log("job", job=j["job"], seconds=j["seconds"], quality=j["quality"])
    Rr = pd.concat([j["rows"] for j in J], ignore_index=True)
    Rr.to_csv(OUT / "rows.csv", index=False, lineterminator="\n")
    e84, _ = R._stored()
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    arms = ["E184", "traj", "E192", "E192_20"]
    res = {"protocol": "docs/e192/PROTOCOL.md", "leads": {}}
    m = Rr[Rr["arm"] == "E184"].merge(e84.rename(columns={"p": "ps"}), on=RT.KEYS)
    res["reproduction_E184_max_abs_diff_p"] = float(np.max(np.abs(m["p"] - m["ps"])))
    for L in LEADS:
        x = G[G["lead"] == L]
        for a in arms:
            x = x.merge(Rr[(Rr["lead"] == L) & (Rr["arm"] == a)][RT.KEYS + ["p"]].rename(columns={"p": a}), on=RT.KEYS)
        assert len(x) == 72
        y = x["y_high"].astype(bool)
        d = {"metrics": {a: R.metrics(y, x[a], x["q_true"]) for a in ["PERS"] + arms}}
        for a in arms[1:]:
            v = E.E7.diff_ci(x, a, "E184", "q_true", np.random.default_rng(192), n=2000)
            vp = E.E7.diff_ci(x, a, "PERS", "q_true", np.random.default_rng(192), n=2000)
            cA, cB = (x[a] >= .5) == y, (x["E184"] >= .5) == y
            b, c = int((cA & ~cB).sum()), int((~cA & cB).sum())
            d[a] = {"brier_minus_E184": [round(v["diff"], 5), [round(z, 5) for z in v["ci95"]]],
                    "mcnemar": {"only_this_right": b, "only_E184_right": c, "p": round(float(binomtest(b, b + c, .5).pvalue), 4) if b + c else 1.0},
                    "owner_rule": bool(d["metrics"][a]["accuracy"] >= .75 and vp["ci95"][1] < 0)}
        res["leads"][L] = d
    dec = {}
    for a in ("E192", "E192_20"):
        acc = [res["leads"][L]["metrics"][a]["accuracy"] - res["leads"][L]["metrics"]["E184"]["accuracy"] for L in LEADS]
        br = [res["leads"][L]["metrics"][a]["brier"] - res["leads"][L]["metrics"]["E184"]["brier"] for L in LEADS]
        dec[a] = {"acc_ge_all": all(z >= -1e-9 for z in acc), "brier_le_all": all(z <= 1e-12 for z in br), "acc_gt_any": any(z > 1e-9 for z in acc),
                  "mean_brier": float(np.mean([res["leads"][L]["metrics"][a]["brier"] for L in LEADS]))}
        dec[a]["qualifies"] = dec[a]["acc_ge_all"] and dec[a]["brier_le_all"] and dec[a]["acc_gt_any"]
    q = [a for a in dec if dec[a]["qualifies"]]
    res["decision_checks"] = dec
    res["decision"] = f"{min(q, key=lambda a: dec[a]['mean_brier'])} preferred to E184 (candidate only; not staged)" if q else "Neither E192 arm meets the rule: E184 stays"
    K.dump_json(res, OUT / "results.json")
    K.write_hashes([OUT / n for n in ("rows.csv", "results.json", "run_log.jsonl")], OUT / "hashes.json")
    log("evaluated", decision=res["decision"])
    print("repro E184:", res["reproduction_E184_max_abs_diff_p"])
    for L in LEADS:
        M = res["leads"][L]["metrics"]
        print(f"L{L}: " + " | ".join(f"{a} {100*M[a]['accuracy']:.1f}% FA{M[a]['false_positives']} miss{M[a]['false_negatives']} B{M[a]['brier']:.4f}" for a in arms),
              "| E192 vs E184", res["leads"][L]["E192"]["mcnemar"], res["leads"][L]["E192"]["brier_minus_E184"], "| E192_20", res["leads"][L]["E192_20"]["mcnemar"], res["leads"][L]["E192_20"]["brier_minus_E184"],
              "| rule", {a: res["leads"][L][a]["owner_rule"] for a in arms[1:]})
    print(dec)
    print(res["decision"])


if __name__ == "__main__":
    main()

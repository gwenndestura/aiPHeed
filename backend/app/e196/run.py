"""E196 (docs/e196/PROTOCOL.md): E194 re-run with inner OOF saved; lagged-averaging rule chosen per job on training rows."""
from __future__ import annotations

import json
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
from app.e191 import run as R
from app.e194 import run as E194

warnings.filterwarnings("ignore")
OUT = K.D / "e196" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e196" / "PROTOCOL.md"
LEADS = (1, 2, 3, 4, 5, 6)
KS = ["key", "survey"]


def job(survey, lead):
    t0 = time.time()
    tr, te, AN = R.load(R.FR / f"{survey}_L{lead}_main.pkl")
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    ranked = E194.stage_a_ranked(tr, AN, folds)[:E194.TOPK]
    stream = RT.job_id(survey, lead, "main")
    ps, oofs = [], []
    for sse, _, cfg in ranked:
        for s in E194.SEEDS:
            P, oof, _, _ = R.run_cfg(tr, te, AN, folds, cfg, R.spec_of("e184"), s, stream)
            ps.append(np.asarray(P[1], float))
            oofs.append(oof)
    o = te[RT.KEYS].copy()
    o["p"] = np.mean(ps, axis=0)
    t = tr[["key", "survey", "lead", "y_true", "se_true"]].copy()
    t["oof"] = np.mean(oofs, axis=0)
    t["w"] = 1.0 / (t["se_true"] ** 2 + 0.05)
    # rule selection on training rows only
    W = t.pivot_table(index=KS, columns="lead", values="oof")
    Y = t.groupby(KS)[["y_true", "w"]].first()
    cand = {"S1": [lead], "S2": [lead, lead + 1], "S3": [lead, lead + 1, lead + 2]}
    avail = {k: all(l in W.columns for l in v) for k, v in cand.items()}
    # S1 (E194 unchanged) needs no training lead; S2/S3 only when their leads exist in the training rows (and S1's too)
    use = ["S1"] + [k for k in ("S2", "S3") if avail[k] and avail["S1"]]
    score, best, common = {}, "S1", []
    if len(use) > 1:
        common = W[cand[use[-1]]].dropna().index
        for k in use:
            m = W.loc[common, cand[k]].mean(axis=1)
            score[k] = float(np.sum(Y.loc[common, "w"] * (Y.loc[common, "y_true"] - m) ** 2)) if len(common) else np.inf
        for k in use:
            if len(common) and score[k] < score[best] - 1e-12:
                best = k
    return {"rows": o, "job": stream, "survey": survey, "lead": lead, "rule": best, "scores": score, "n_common": int(len(common)),
            "seconds": round(time.time() - t0, 1)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    log("start", protocol_sha256=K.sha256(PROTOCOL))
    order = sorted([(s, l) for s in RT.SURVEYS for l in LEADS], key=lambda t: t[0] != "ENNS2021")
    J = Parallel(n_jobs=R.N_JOBS, verbose=5)(delayed(job)(s, l) for s, l in order)
    for j in J:
        log("job", job=j["job"], rule=j["rule"], scores=j["scores"], n_common=j["n_common"], seconds=j["seconds"])
    P = pd.concat([j["rows"] for j in J], ignore_index=True)
    P.to_csv(OUT / "e194_rerun_rows.csv", index=False, lineterminator="\n")
    rules = {(j["survey"], j["lead"]): j["rule"] for j in J}
    e194 = pd.read_csv(K.D / "e194" / "out" / "per_cfg_seed_rows.csv").groupby(RT.KEYS)["p"].mean().reset_index()
    chk = P.merge(e194, on=RT.KEYS, suffixes=("", "_stored"))
    res = {"protocol": "docs/e196/PROTOCOL.md", "rerun_vs_E194_max_abs_diff_p": float(np.max(np.abs(chk["p"] - chk["p_stored"]))),
           "rules": {f"{s}|L{l}": r for (s, l), r in rules.items()}, "leads": {}}
    Wp = P.pivot_table(index=KS, columns="lead", values="p")
    sets = {"S1": 1, "S2": 2, "S3": 3}
    out = []
    for (s, L), r in rules.items():
        if L > 4:
            continue
        ls = list(range(L, L + sets[r]))
        sub = Wp.loc[Wp.index.get_level_values("survey") == s, ls].mean(axis=1).rename("p").reset_index()
        sub["lead"] = L
        out.append(sub)
    E196 = pd.concat(out, ignore_index=True)
    e84, _ = R._stored()
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    for L in (1, 2, 3, 4):
        x = G[G["lead"] == L]
        for a, d in (("E184", e84), ("E194", P), ("E196", E196)):
            x = x.merge(d[d["lead"] == L][RT.KEYS + ["p"]].rename(columns={"p": a}), on=RT.KEYS)
        assert len(x) == 72
        y = x["y_high"].astype(bool)
        r = {a: R.metrics(y, x[a], x["q_true"]) for a in ("E184", "E194", "E196")}
        for ref in ("E194", "E184"):
            v = E.E7.diff_ci(x, "E196", ref, "q_true", np.random.default_rng(196), n=2000)
            cA, cB = (x["E196"] >= .5) == y, (x[ref] >= .5) == y
            b, c = int((cA & ~cB).sum()), int((~cA & cB).sum())
            r[f"vs_{ref}"] = {"fixed": b, "broken": c, "p": round(float(binomtest(b, b + c, .5).pvalue), 4) if b + c else 1.0,
                              "brier_diff": [round(v["diff"], 5), [round(t, 5) for t in v["ci95"]]]}
        vp = E.E7.diff_ci(x, "E196", "PERS", "q_true", np.random.default_rng(196), n=2000)
        r["owner_rule"] = bool(r["E196"]["accuracy"] >= .75 and vp["ci95"][1] < 0)
        res["leads"][L] = r
    acc = [res["leads"][L]["E196"]["accuracy"] - res["leads"][L]["E194"]["accuracy"] for L in (1, 2, 3)]
    br = [res["leads"][L]["E196"]["brier"] - res["leads"][L]["E194"]["brier"] for L in (1, 2, 3)]
    res["decision_checks"] = {"acc_ge": all(a >= -1e-9 for a in acc), "brier_le": all(b <= 1e-12 for b in br), "acc_gt_any": any(a > 1e-9 for a in acc)}
    res["decision"] = "E196 preferred to E194 (candidate only)" if all(res["decision_checks"].values()) else "E196 not preferred: E194 stays best"
    K.dump_json(res, OUT / "results.json")
    K.write_hashes([OUT / n for n in ("e194_rerun_rows.csv", "results.json", "run_log.jsonl")], OUT / "hashes.json")
    log("evaluated", decision=res["decision"])
    print("rerun vs E194:", res["rerun_vs_E194_max_abs_diff_p"])
    print("rules:", json.dumps(res["rules"]))
    for j in J:
        print(j["job"], j["rule"], {k: round(v, 2) for k, v in j["scores"].items()}, "n_common", j["n_common"])
    for L, r in res["leads"].items():
        print(f"L{L}: " + " | ".join(f"{a} {100*r[a]['accuracy']:.1f}% FA{r[a]['false_positives']} miss{r[a]['false_negatives']} B{r[a]['brier']:.4f}" for a in ("E184", "E194", "E196")),
              "| vs E194", r["vs_E194"], "| vs E184", r["vs_E184"], "| rule", r["owner_rule"])
    print(res["decision_checks"], res["decision"])


if __name__ == "__main__":
    main()

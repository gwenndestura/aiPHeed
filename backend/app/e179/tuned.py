"""
E179 (docs/e179/PROTOCOL.md): E168 with synthetic training rows, the augmentation tuned on inner folds only.

Stage A  E168's own selection (anchor, feature set, pruning, LightGBM settings) on real rows, exactly as
         app.e168.lgbm_only.run_proc; without augmentation the model is E168's.
Stage B  129 augmentation settings (incl. none) scored by region GroupKFold on the job's training rows: synthetic rows
         from each inner fold's real training rows, in its fit set only; weighted logit SSE on real held-out rows.
         One-standard-error rule against "none"; if nothing is clearly better, E179 = E168 for the job.

    python -m app.e179.tuned run      -> data/e179/out/
    python -m app.e179.tuned report   re-evaluate data/e179/out/all_rows.csv (no refit)
"""
from __future__ import annotations

import os
import sys
import time
import warnings
from itertools import product

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import GroupKFold

from app.e168 import lgbm_only as E           # E168 code, used read-only
from app.e178 import augment as A
from app.e178 import common as K
from app.e178 import retrain as RT

warnings.filterwarnings("ignore")
ROOT = K.D / "e179"
OUT = ROOT / "out"
SYN = ROOT / "synthetic"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e179" / "PROTOCOL.md"
RATIOS = (0.25, 0.5, 1.0, 2.0)
WEIGHTS = (0.2, 0.4, 0.7, 1.0)
JITTER_SDS = (0.1, 0.25, 0.5)
FOCUS = ("uniform", "boundary")
SETTINGS = ([None] + [("jitter", r, a, s, f) for r in RATIOS for a in WEIGHTS for s in JITTER_SDS for f in FOCUS]
            + [("smote", r, a, A.JITTER_SD, f) for r in RATIOS for a in WEIGHTS for f in FOCUS])
SEEDS = (17901, 17902, 17903, 17904, 17905)
PRIMARY = SEEDS[0]
N_JOBS = RT.N_JOBS


def setting_name(s) -> str:
    return "none" if s is None else f"{s[0]}|r={s[1]:g}|w={s[2]:g}|sd={s[3]:g}|{s[4]}"


def _augment(real, an, s, seed, job, fold):
    g, r, _, sd, foc = s
    return A.augment(real, an, g, r, A.rng_for(seed, job, f"{fold}|sd{sd:g}|{foc}", g, r), A.feature_columns(real), seed,
                     jitter_sd=sd, focus=foc, tag="E179")


def run_proc_tuned(tr, te, AN, seeds, job, settings=SETTINGS, keep_syn=False):
    """Stage A once, Stage B per seed. Returns rows (one block per arm and seed), the selection log and balance log."""
    assert "is_synthetic" not in te.columns, "outer rows must be real"
    tr = tr.reset_index(drop=True)
    y, q, w = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    # ---- Stage A: lgbm_only.run_proc's selection loop, unchanged
    best = None
    for a, f, pr, h in product(E.ANCH, E.FS, (False, True), E.HPO):
        atr = AN[a][0]
        oof = np.zeros(len(tr))
        for i_tr, i_te in folds:
            oof[i_te] = atr[i_te] + E.LGBRes(E.FS[f], *h, pr).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
        sse = float(np.sum(w * (y - oof) ** 2))
        if best is None or sse < best["sse"]:
            best = {"sse": sse, "cfg": (a, f, pr, h), "oof": oof}
    a, f, pr, h = best["cfg"]
    atr, ate = AN[a]
    fold_sse = lambda o: np.array([float(np.sum(w[i] * (y[i] - o[i]) ** 2)) for _, i in folds])
    base = {"oof": best["oof"], "folds": fold_sse(best["oof"]), "sse": best["sse"]}
    tag0 = f"{a}|{f}|prune={pr}|leaves={h[0]},minchild={h[1]},lambda={h[2]},trees={h[3]}"

    def final(s, seed):
        cand_oof = base["oof"] if s is None else cands[s]["oof"]
        syn_out, info = None, None
        if s is None:
            mdl = E.LGBRes(E.FS[f], *h, pr).fit(tr.assign(e=y - atr))
        else:
            syn, sa, info = _augment(tr, {x: np.asarray(AN[x][0], float) for x in E.ANCH}, s, seed, job, "final")
            mdl = RT.LGBResAug(E.FS[f], *h, pr)
            mdl.syn_weight = s[2]
            mdl.fit(tr.assign(e=y - atr), syn.assign(e=syn["y_true"].values - sa[a]))
            if keep_syn:
                syn_out = syn.assign(**{f"anchor_{x}": sa[x] for x in sa}, job=job, setting=setting_name(s))
        mu = ate + mdl.predict(te)
        P, chosen, inner = RT._calibrate(tr, te, folds, cand_oof, mu, y, q, w, gap)
        return P, chosen, inner, len(mdl.use_), syn_out, info

    rows, sel, bal, syn_keep = [], [], [], []

    def emit(arm, seed, s, out):
        P, chosen, inner, nf, syn_out, info = out
        o = te[RT.KEYS].copy().reset_index(drop=True)
        o["seed"], o["arm"], o["setting"] = seed, arm, setting_name(s)
        o["cfg"] = f"{tag0}|cal={chosen}" + ("" if s is None else f"|aug={setting_name(s)}")
        o["cal"], o["n_features"] = chosen, nf
        for k_, (mu, p, half) in P.items():
            o[f"mu_{k_}"], o[f"p_{k_}"], o[f"half_{k_}"] = mu, p, half
        o["mu"], o["p"], o["half"] = P[chosen]
        rows.append(o)
        if syn_out is not None:
            syn_keep.append(syn_out.assign(seed=seed, arm=arm))
        if info is not None and arm == "E179":
            bal.append({"job": job, "seed": seed, "fold": "final", "setting": setting_name(s), **info})

    emit("E168_rerun", seeds[0], None, final(None, seeds[0]))
    for seed in seeds:
        # ---- Stage B: every setting on the inner folds, synthetic rows from each fold's training rows only
        cache, cands = {}, {}
        for s in settings[1:]:
            oof = np.zeros(len(tr))
            for fi, (i_tr, i_te) in enumerate(folds):
                k = (fi, s[0], s[1], s[3], s[4])
                if k not in cache:
                    real = tr.iloc[i_tr].reset_index(drop=True)
                    syn, sa, _ = _augment(real, {x: np.asarray(AN[x][0], float)[i_tr] for x in E.ANCH}, s, seed, job, fi)
                    cache[k] = (syn, sa)
                syn, sa = cache[k]
                m = RT.LGBResAug(E.FS[f], *h, pr)
                m.syn_weight = s[2]
                m.fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr]), syn.assign(e=syn["y_true"].values - sa[a]))
                oof[i_te] = atr[i_te] + m.predict(tr.iloc[i_te])                 # real held-out rows only
            cands[s] = {"oof": oof, "folds": fold_sse(oof), "sse": float(np.sum(w * (y - oof) ** 2))}
        gain = {s: (float(np.mean(c["folds"] - base["folds"])), float(np.std(c["folds"] - base["folds"], ddof=1) / np.sqrt(len(folds))))
                for s, c in cands.items()}
        eligible = [s for s in settings[1:] if gain[s][0] + gain[s][1] < 0]
        chosen = min(eligible, key=lambda s: (cands[s]["sse"], settings.index(s))) if eligible else None
        best_any = min(settings, key=lambda s: (base["sse"] if s is None else cands[s]["sse"], settings.index(s)))
        sel.append({"job": job, "seed": seed, "config": tag0, "sse_none": base["sse"], "n_eligible": len(eligible),
                    "chosen": setting_name(chosen), "sse_chosen": base["sse"] if chosen is None else cands[chosen]["sse"],
                    "gain_mean": None if chosen is None else gain[chosen][0], "gain_se": None if chosen is None else gain[chosen][1],
                    "min_setting": setting_name(best_any), "sse_min": base["sse"] if best_any is None else cands[best_any]["sse"]})
        emit("E179", seed, chosen, final(chosen, seed))
        emit("E179_min", seed, best_any, final(best_any, seed))
    return rows, sel, bal, syn_keep


def task(survey, lead, H, L, S_P, mode, seeds, keep_syn=False):
    t0 = time.time()
    job = RT.job_id(survey, lead, mode)
    tr, te, AN = RT.build(survey, lead, H, L, S_P, mode)
    rows, sel, bal, syn = run_proc_tuned(tr, te, AN, seeds, job, keep_syn=keep_syn)
    out = pd.concat(rows, ignore_index=True)
    out["mode"] = mode
    return {"rows": out, "sel": pd.DataFrame(sel), "bal": pd.DataFrame(bal), "syn": pd.concat(syn, ignore_index=True) if syn else None,
            "job": job, "seconds": round(time.time() - t0, 1), "n_train": len(tr)}


def _decision(acc, res):
    return ("E179 BETTER THAN E168 on the pre-registered rule (candidate only; not promoted; the owner decides)" if all(acc.values())
            else "E179: TUNED SYNTHETIC AUGMENTATION DID NOT IMPROVE THE MODEL ON THE PRE-REGISTERED RULE (E168 stays in production)")


def evaluate(log=None):
    log = log or K.RunLog(OUT / "run_log.jsonl", fresh=False)
    Al = pd.read_csv(OUT / "all_rows.csv", float_precision="round_trip")
    e8 = pd.read_csv(E.OUT / "all_rows.csv", float_precision="round_trip")
    x = Al[Al["arm"] == "E168_rerun"].merge(e8, on=RT.KEYS + ["mode"], suffixes=("", "_e168"))
    check = {"rows": int(len(x)), "max_abs_diff_p": float(np.max(np.abs(x["p"] - x["p_e168"]))),
             "max_abs_diff_mu": float(np.max(np.abs(x["mu"] - x["mu_e168"]))), "same_config": bool((x["cfg"] == x["cfg_e168"]).all())}
    log("e168_rerun_check", **check)
    sel = pd.read_csv(OUT / "selection.csv")
    res = RT.evaluate(log, OUT, name="E179", protocol="docs/e179/PROTOCOL.md", primary_seed=PRIMARY,
                      extra_outs=[OUT / "selection.csv"] + sorted(SYN.rglob("*.parquet")), decision_text=_decision)
    res["e168_rerun_check"] = check
    res["selection"] = {"primary_seed": sel[sel["seed"] == PRIMARY][["job", "chosen", "n_eligible", "gain_mean", "gain_se", "min_setting"]].to_dict("records"),
                        "share_jobs_using_augmentation_all_seeds": round(float((sel["chosen"] != "none").mean()), 3)}
    K.dump_json(res, OUT / "results.json")
    K.write_hashes([OUT / n for n in ("all_rows.csv", "balance.csv", "results.json", "selection.csv")] + sorted(SYN.rglob("*.parquet"))
                   + [OUT / "run_log.jsonl"], OUT / "hashes.json")
    print("E168 rerun check:", check)
    print("selection (primary seed):")
    print(sel[sel["seed"] == PRIMARY][["job", "chosen", "n_eligible", "gain_mean", "gain_se", "min_setting"]].to_string(index=False))
    return res


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL), n_settings=len(SETTINGS), seeds=SEEDS, n_jobs=N_JOBS)
    H, L, S_P = K.pipeline_inputs()
    jobs = [(s, l, "main", SEEDS) for s, l in RT.MAIN] + [(s, 1, m, (PRIMARY,)) for s in RT.SURVEYS for m in RT.CONTROLS]
    jobs.sort(key=lambda j: (RT.SURVEYS.index(j[0]), j[2] != "main"))
    t0 = time.time()
    R = Parallel(n_jobs=N_JOBS, verbose=5)(delayed(task)(s, l, H, L, S_P, m, sd, keep_syn=(m == "main")) for s, l, m, sd in jobs)
    for r in R:
        log("job", job=r["job"], seconds=r["seconds"], n_train=r["n_train"])
    pd.concat([r["rows"] for r in R], ignore_index=True).to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    pd.concat([r["sel"] for r in R], ignore_index=True).to_csv(OUT / "selection.csv", index=False, lineterminator="\n")
    pd.concat([r["bal"] for r in R if len(r["bal"])] or [pd.DataFrame(columns=["job"])], ignore_index=True).to_csv(OUT / "balance.csv", index=False, lineterminator="\n")
    syn = [r["syn"] for r in R if r["syn"] is not None]
    if syn:
        (SYN / "train").mkdir(parents=True, exist_ok=True)
        s = pd.concat(syn, ignore_index=True)
        s[s["seed"] == PRIMARY].to_parquet(SYN / "train" / f"train_rows_seed{PRIMARY}.parquet", index=False)
    log("fitted", seconds=round(time.time() - t0, 1))
    evaluate(log)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"run": run, "report": evaluate}.get(cmd, lambda: sys.exit("usage: python -m app.e179.tuned run | report"))()

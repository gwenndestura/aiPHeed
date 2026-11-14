"""
E178 Part B: E168 with synthetic training rows (docs/e178/PROTOCOL.md, Part B). A candidate only: nothing here registers,
promotes or changes E168.

    python -m app.e178.retrain equiv      this code with augmentation off reproduces E168 (all 18 E168 jobs)
    python -m app.e178.retrain fidelity   Stage 1: fidelity of each generator on the six outer training sets
    python -m app.e178.retrain eval       Stage 2: outer jobs, controls and seeds -> data/e178/out/
    python -m app.e178.retrain report     re-evaluate data/e178/out/all_rows.csv only (no refit)

The outer frames are E168's own: build() runs app.e168.lgbm_only.task unchanged and stops it at its run_proc call.
run_proc_aug() is lgbm_only.run_proc with one addition: synthetic rows in the LightGBM fit sets (inner folds: from that
fold's real training rows; final model: from the job's real training rows). Out-of-fold errors, the variance scale, the
calibration layers and every reported metric use real rows only.
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings
from itertools import product

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import binomtest, norm
from sklearn.model_selection import GroupKFold

from app.e168 import lgbm_only as E           # E168 code, used read-only
from app.e178 import augment as A
from app.e178 import common as K

warnings.filterwarnings("ignore")
SURVEYS = ("ENNS2021", "ENNS2019", "ENNS2018")     # largest training sets first
MAIN = [(s, l) for s in SURVEYS for l in (1, 2)]
CONTROLS = ("shuf1", "shuf2", "shuf3", "corrupt")
MENU = [(g, r) for g in A.GENERATORS for r in A.RATIOS]
OUT = K.OUT
D = K.D
N_JOBS = max(1, min(7, (os.cpu_count() or 2) - 1))
KEYS = ["key", "survey", "lead"]


def job_id(survey: str, lead: int, mode: str) -> str:
    return f"{survey}|L{lead}|{mode}"


def arm_name(key) -> str:
    return "E168" if key is None else f"E178_{key[0]}_r{key[1]:g}"


# ---------------------------------------------------------------------------------------------------- the learner
def _params(m: E.LGBRes, use: list[str]) -> dict:
    """The LightGBM parameters of app.e168.lgbm_only.LGBRes.fit (tests check they stay identical)."""
    return dict(objective="regression", num_leaves=m.nl, max_depth=-1, min_child_samples=m.mcs, reg_lambda=m.lam, reg_alpha=0.0,
                min_split_gain=0.0, n_estimators=m.ne, learning_rate=0.02, colsample_bytree=0.8, subsample=0.8, subsample_freq=1,
                monotone_constraints=[E.Pv.SIGN.get(c, 0) for c in use], monotone_constraints_method="basic", random_state=168,
                n_jobs=1, verbose=-1)


class LGBResAug(E.LGBRes):
    """LGBRes with synthetic rows in the fit set. Column filter and pruning are computed on the real rows only; synthetic
    rows get weight SYN_WEIGHT x 1/(se^2 + 0.05). Without synthetic rows it is LGBRes exactly."""

    def fit(self, d, syn=None):
        if syn is None or len(syn) == 0:
            return super().fit(d)
        use = [c for c in self.cols if c in d and d[c].notna().any() and d[c].nunique() > 1]
        if self.prune and len(use) > 1:
            R = d[use].rank().corr().abs()
            keep = []
            for c in use:
                if all(not (R.at[c, k] > 0.95) for k in keep):
                    keep.append(c)
            use = keep
        self.use_ = use
        X = pd.concat([d[use], syn[use]], ignore_index=True)
        e = np.r_[d["e"].values, syn["e"].values]
        alpha = getattr(self, "syn_weight", A.SYN_WEIGHT)              # E178: 0.4 fixed; E179 tunes it on inner folds
        w = np.r_[1.0 / (d["se_true"].values ** 2 + 0.05), alpha / (syn["se_true"].values ** 2 + 0.05)]
        self.m_ = lgb.LGBMRegressor(**_params(self, use)).fit(X, e, sample_weight=w)
        return self


# ------------------------------------------------------------------------------------------------- the procedure
def _calibrate(tr, te, folds, oof, mu, y, q, w, gap):
    """lgbm_only.run_proc's calibration block, unchanged: three layers cross-fitted on the real inner OOF forecasts."""
    sd, _ = E.A4.scale(y - oof, gap, gap)
    lin, pl = np.zeros(len(tr)), np.zeros(len(tr))
    for i_tr, i_te in folds:
        Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w[i_tr])[:, None]
        ab = np.linalg.lstsq(Z, y[i_tr] * np.sqrt(w[i_tr]), rcond=None)[0]
        lin[i_te] = ab[0] + ab[1] * oof[i_te]
        pl[i_te] = E.F5.soft_platt(oof[i_tr], q[i_tr]).predict_proba(oof[i_te].reshape(-1, 1))[:, 1]
    sdl, _ = E.A4.scale(y - lin, gap, gap)
    inner = {"raw": float(np.mean((norm.cdf(oof / sd) - q) ** 2)), "linear": float(np.mean((norm.cdf(lin / sdl) - q) ** 2)), "platt": float(np.mean((pl - q) ** 2))}
    chosen = min(inner, key=inner.get)
    sd_te, half = E.A4.scale(y - oof, gap, te["gap_q"].values)
    Z = np.column_stack([np.ones(len(tr)), oof]) * np.sqrt(w)[:, None]
    ab = np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0]
    mu_lin = ab[0] + ab[1] * mu
    sd_lin, half_lin = E.A4.scale(y - lin, gap, te["gap_q"].values)
    P = {"raw": (mu, norm.cdf(mu / sd_te), half), "linear": (mu_lin, norm.cdf(mu_lin / sd_lin), half_lin),
         "platt": (mu, E.F5.soft_platt(oof, q).predict_proba(mu.reshape(-1, 1))[:, 1], half)}
    return P, chosen, inner


def run_proc_aug(tr, te, AN, menu, seed: int, job: str, keep_syn: bool = False):
    """lgbm_only.run_proc with synthetic training rows for each (generator, ratio) in `menu`; an empty menu is E168.
    Returns {key: arm} for every key ((generator, ratio), or None) and the class-balance log."""
    assert "is_synthetic" not in te.columns, "outer rows must be real"
    tr = tr.reset_index(drop=True)
    y, q, w = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cols = A.feature_columns(tr)
    keys = list(menu) or [None]
    SY, bal = {}, []
    for fi, (i_tr, i_te) in enumerate(folds):
        real = tr.iloc[i_tr].reset_index(drop=True)
        an = {a: np.asarray(AN[a][0], float)[i_tr] for a in E.ANCH}
        for g, r in menu:
            syn, sa, info = A.augment(real, an, g, r, A.rng_for(seed, job, fi, g, r), cols, seed)
            assert not set(syn["parent"]) - set(range(len(real)))
            SY[(fi, g, r)] = (syn, sa)
            bal.append({"job": job, "seed": seed, "fold": str(fi), "generator": g, "ratio": r, **info})
    best = {}
    for key in keys:
        for a, f, pr, h in product(E.ANCH, E.FS, (False, True), E.HPO):
            atr = AN[a][0]
            oof = np.zeros(len(tr))
            for fi, (i_tr, i_te) in enumerate(folds):
                d = tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])
                if key is None:
                    m = E.LGBRes(E.FS[f], *h, pr).fit(d)
                else:
                    syn, sa = SY[(fi, *key)]
                    m = LGBResAug(E.FS[f], *h, pr).fit(d, syn.assign(e=syn["y_true"].values - sa[a]))
                oof[i_te] = atr[i_te] + m.predict(tr.iloc[i_te])           # real held-out rows only
            sse = float(np.sum(w * (y - oof) ** 2))
            if key not in best or sse < best[key]["sse"]:
                best[key] = {"sse": sse, "cfg": (a, f, pr, h), "oof": oof}
    arms = {}
    for key in keys:
        a, f, pr, h = best[key]["cfg"]
        atr, ate = AN[a]
        oof, syn_out = best[key]["oof"], None
        if key is None:
            mdl = E.LGBRes(E.FS[f], *h, pr).fit(tr.assign(e=y - atr))
        else:
            g, r = key
            syn, sa, info = A.augment(tr, {an: np.asarray(AN[an][0], float) for an in E.ANCH}, g, r, A.rng_for(seed, job, "final", g, r), cols, seed)
            bal.append({"job": job, "seed": seed, "fold": "final", "generator": g, "ratio": r, **info})
            mdl = LGBResAug(E.FS[f], *h, pr).fit(tr.assign(e=y - atr), syn.assign(e=syn["y_true"].values - sa[a]))
            if keep_syn:
                syn_out = syn.assign(**{f"anchor_{an}": sa[an] for an in sa}, job=job)
        mu = ate + mdl.predict(te)
        P, chosen, inner = _calibrate(tr, te, folds, oof, mu, y, q, w, gap)
        aug = "" if key is None else f"|aug={key[0]},r={key[1]:g}"
        tag = f"{a}|{f}|prune={pr}|leaves={h[0]},minchild={h[1]},lambda={h[2]},trees={h[3]}|cal={chosen}{aug}"
        arms[key] = {"P": P, "chosen": chosen, "tag": tag, "inner": inner, "n_features": len(mdl.use_), "sse": best[key]["sse"], "syn": syn_out}
    return arms, bal


class _Captured(Exception):
    pass


def build(survey: str, lead: int, H, L, S_P, mode: str):
    """E168's outer frames for one job: app.e168.lgbm_only.task runs unchanged up to its run_proc call (shuffle and
    corruption included), where it is stopped and its (tr, te, AN) are taken."""
    def stop(tr, te, AN, ablate=False):
        raise _Captured(tr, te, AN)
    with K.patched(E, "run_proc", stop):
        try:
            E.task(survey, lead, H, L, S_P, mode)
        except _Captured as c:
            return c.args
    raise RuntimeError("lgbm_only.task did not reach run_proc")


def task_aug(survey, lead, H, L, S_P, mode, seed, menu, keep_syn=False):
    t0 = time.time()
    job = job_id(survey, lead, mode)
    tr, te, AN = build(survey, lead, H, L, S_P, mode)
    arms, bal = run_proc_aug(tr, te, AN, menu, seed, job, keep_syn)
    rows = []
    for key, v in arms.items():
        o = te[KEYS].copy().reset_index(drop=True)
        o["mode"], o["seed"], o["arm"], o["generator"], o["ratio"] = mode, seed, arm_name(key), None if key is None else key[0], None if key is None else key[1]
        o["cfg"], o["cal"], o["n_features"], o["inner_sse"] = v["tag"], v["chosen"], v["n_features"], v["sse"]
        for k_, (mu, p, half) in v["P"].items():
            o[f"mu_{k_}"], o[f"p_{k_}"], o[f"half_{k_}"] = mu, p, half
        o["mu"], o["p"], o["half"] = v["P"][v["chosen"]]
        for k_, x in v["inner"].items():
            o[f"inner_brier_{k_}"] = x
        rows.append(o)
    out = pd.concat(rows, ignore_index=True)
    if menu:                                   # selected arms: by generator, and the primary E178 (lowest inner SSE)
        sse = {k_: v["sse"] for k_, v in arms.items()}
        pick = {f"E178_{g}": min((k_ for k_ in sse if k_[0] == g), key=lambda k_: (sse[k_], menu.index(k_))) for g in {g for g, _ in menu}}
        pick["E178"] = min(sse, key=lambda k_: (sse[k_], menu.index(k_)))
        for name, k_ in pick.items():
            out = pd.concat([out, out[out.arm == arm_name(k_)].assign(arm=name)], ignore_index=True)
    syn = pd.concat([v["syn"] for v in arms.values() if v["syn"] is not None], ignore_index=True) if keep_syn and menu else None
    return {"rows": out, "balance": pd.DataFrame(bal), "syn": syn, "job": job, "seed": seed, "seconds": round(time.time() - t0, 1),
            "n_train": len(tr), "n_test": len(te)}


# ------------------------------------------------------------------------------------------------------ commands
def _check_inputs(log) -> None:
    prov = {"regional_income_long.csv": K.sha256(K.INCOME_RAW) if K.INCOME_RAW.exists() else None}
    want = json.loads(K.INCOME_LOCK.read_text())["hashes"]["regional_income_long.csv"]
    if prov["regional_income_long.csv"] != want:
        raise K.ProvenanceError("regional_income_long.csv missing or not the locked file")
    from app.e155 import test as T155
    prov["sunstar"] = "raw file" if T155.SUN.exists() else "empty stand-in (columns used by no E168 feature set)"
    log("inputs", **prov)


def equiv() -> None:
    """E168's 18 jobs through this module with augmentation off; must equal data/e168/out/all_rows.csv."""
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "equiv_log.jsonl")
    _check_inputs(log)
    H, L, S_P = K.pipeline_inputs()
    jobs = [(s, l, "main") for s, l in MAIN] + [(s, 1, m) for s in SURVEYS for m in CONTROLS]
    t0 = time.time()
    R = Parallel(n_jobs=N_JOBS)(delayed(task_aug)(s, l, H, L, S_P, m, A.PRIMARY_SEED, []) for s, l, m in jobs)
    got = pd.concat([r["rows"] for r in R], ignore_index=True)
    ref = pd.read_csv(E.OUT / "all_rows.csv", float_precision="round_trip")
    x = ref.merge(got, on=KEYS + ["mode"], suffixes=("_e168", "_aug"))
    cols = ["mu", "p", "half"] + [f"{a}_{k}" for k in ("raw", "linear", "platt") for a in ("mu", "p", "half")]
    diff = {c: float(np.max(np.abs(x[f"{c}_e168"] - x[f"{c}_aug"]))) for c in cols}
    same_cfg = bool((x["cfg_e168"] == x["cfg_aug"]).all())
    doc = {"rows_compared": int(len(x)), "rows_expected": int(len(ref)), "same_configuration": same_cfg, "max_abs_diff": diff,
           "bit_for_bit": same_cfg and len(x) == len(ref) and all(v == 0.0 for v in diff.values()), "seconds": round(time.time() - t0, 1)}
    K.dump_json(doc, OUT / "equivalence.json")
    log("equivalence", **doc)
    print(json.dumps(doc, indent=1))


def _fid_job(survey, lead, H, L, S_P):
    tr, te, AN = build(survey, lead, H, L, S_P, "main")
    atr = {a: np.asarray(AN[a][0], float) for a in E.ANCH}
    return {g: A.fidelity(tr, atr, g, A.PRIMARY_SEED, job_id(survey, lead, "main")) for g in A.GENERATORS}


def fidelity() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "fidelity_log.jsonl")
    _check_inputs(log)
    H, L, S_P = K.pipeline_inputs()
    R = Parallel(n_jobs=min(N_JOBS, len(MAIN)))(delayed(_fid_job)(s, l, H, L, S_P) for s, l in MAIN)
    res = {job_id(s, l, "main"): r for (s, l), r in zip(MAIN, R)}
    acc = [g for g in A.GENERATORS if all(res[j][g]["passed"] for j in res)]
    doc = {"thresholds": A.FIDELITY, "seed": A.PRIMARY_SEED, "ratio": 1.0, "jobs": res, "accepted_generators": acc,
           "rejected_generators": [g for g in A.GENERATORS if g not in acc]}
    K.dump_json(doc, OUT / "fidelity.json")
    log("fidelity", accepted=acc, summary={j: {g: {k: v for k, v in m.items() if k not in ("per_feature",)} for g, m in r.items()} for j, r in res.items()})
    print(json.dumps({"accepted": acc, "jobs": {j: {g: {**m["checks"], "median_ks": round(m["median_ks"], 3), "max_w1_sd": round(m["max_w1_sd"], 3),
                                                       "corr_mad": round(m["corr_mad"], 3), "tstr_ratio": round(m["tstr_ratio"], 3),
                                                       "copy_share": round(m["copy_share"], 3)} for g, m in r.items()} for j, r in res.items()}}, indent=1))


def run_eval() -> None:
    fid = json.loads((OUT / "fidelity.json").read_text())
    accepted = fid["accepted_generators"]
    log = K.RunLog(OUT / "run_log.jsonl")
    _check_inputs(log)
    log("start", protocol_sha256=K.sha256(K.DOCS / "PROTOCOL.md"), accepted_generators=accepted, seeds=A.SEEDS,
        ratios=A.RATIOS, syn_weight=A.SYN_WEIGHT, n_jobs=N_JOBS)
    if not accepted:
        _not_run(fid, log)
        return
    menu = [(g, r) for g, r in MENU if g in accepted]
    H, L, S_P = K.pipeline_inputs()
    jobs = [(s, l, "main", sd) for sd in A.SEEDS for s, l in MAIN] + [(s, 1, m, A.PRIMARY_SEED) for s in SURVEYS for m in CONTROLS]
    jobs.sort(key=lambda j: (SURVEYS.index(j[0]), j[3] != A.PRIMARY_SEED))
    t0 = time.time()
    R = Parallel(n_jobs=N_JOBS, verbose=5)(delayed(task_aug)(s, l, H, L, S_P, m, sd, menu, keep_syn=(m == "main" and sd == A.PRIMARY_SEED))
                                           for s, l, m, sd in jobs)
    for r in R:
        log("job", job=r["job"], seed=r["seed"], seconds=r["seconds"], n_train=r["n_train"], n_test=r["n_test"])
    Al = pd.concat([r["rows"] for r in R], ignore_index=True)
    Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    bal = pd.concat([r["balance"] for r in R if r["seed"] == A.PRIMARY_SEED and r["job"].endswith("|main")], ignore_index=True)
    bal.to_csv(OUT / "balance.csv", index=False, lineterminator="\n")
    (K.SYN / "train").mkdir(parents=True, exist_ok=True)
    syn = pd.concat([r["syn"] for r in R if r["syn"] is not None], ignore_index=True)
    syn.to_parquet(K.SYN / "train" / f"train_rows_seed{A.PRIMARY_SEED}.parquet", index=False)
    log("fitted", seconds=round(time.time() - t0, 1), rows=len(Al), synthetic_train_rows=len(syn))
    evaluate(log)


FID_KEYS = ("median_ks", "max_w1_sd", "max_w1_feature", "corr_mad", "tstr_ratio", "copy_share", "exact_copies",
            "median_real_nn", "sign_agreement_share", "n_features", "n_real", "real_high", "real_low", "n_syn", "syn_high",
            "syn_low", "smote_fallback_jitter")


def _not_run(fid: dict, log) -> dict:
    """The protocol's outcome when every generator failed the fidelity criteria: Stage 2 is not run. Records why, the
    class balance the generators would have produced, and the hashes."""
    summ = {j: {g: {**{k: m[k] for k in FID_KEYS}, "checks": m["checks"], "passed": m["passed"]} for g, m in r.items()}
            for j, r in fid["jobs"].items()}
    failed = {g: {j: [c for c, ok in r[g]["checks"].items() if not ok] for j, r in fid["jobs"].items() if not r[g]["passed"]}
              for g in A.GENERATORS}
    bal = []
    for j, r in fid["jobs"].items():
        m = next(iter(r.values()))
        high = np.r_[np.ones(m["real_high"], bool), np.zeros(m["real_low"], bool)]
        for rt in A.RATIOS:
            a = A.allocate(high, int(round(rt * m["n_real"])))
            bal.append({"job": j, "ratio": rt, "real_high": m["real_high"], "real_low": m["real_low"],
                        "real_high_share": round(m["real_high"] / m["n_real"], 3), "syn_high_planned": a[1], "syn_low_planned": a[0],
                        "after_high_share": round((m["real_high"] + a[1]) / (m["n_real"] + a[0] + a[1]), 3),
                        **{f"{g}_syn_high_realised_r1": r[g]["syn_high"] for g in r if rt == 1.0}})
    pd.DataFrame(bal).to_csv(OUT / "balance.csv", index=False, lineterminator="\n")
    doc = {"protocol": "docs/e178/PROTOCOL.md", "stage2_run": False,
           "decision": ("NOT RUN: no synthetic generator met the fidelity criteria. Synthetic augmentation was not adopted; "
                        "E168 stays in production."),
           "rule": "A generator that fails any primary fidelity criterion in any of the six outer training sets is rejected; "
                   "if both are rejected, Stage 2 is not run.",
           "thresholds": fid["thresholds"], "rejected_generators": fid["rejected_generators"], "failed_checks": failed,
           "fidelity_summary": summ, "class_balance": bal, "E168_reference": {k: json.loads((E.OUT / "results.json").read_text())[k]
                                                                               for k in ("shuffle", "leakage_max_abs_change", "decision")}}
    K.dump_json(doc, OUT / "results.json")
    log("stage2_not_run", rejected=fid["rejected_generators"], failed_checks=failed)
    outs = [OUT / n for n in ("results.json", "fidelity.json", "balance.csv", "equivalence.json", "deviations.json", "fidelity_log.jsonl", "equiv_log.jsonl")]
    log("hashes")
    K.write_hashes(outs + [OUT / "run_log.jsonl"], OUT / "hashes.json")
    print(json.dumps({k: doc[k] for k in ("decision", "rejected_generators", "failed_checks")}, indent=1))
    return doc


# ---------------------------------------------------------------------------------------------------- evaluation
def _frame(Al, Ld, seed, arms):
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    E8 = pd.read_csv(E.OUT / "all_rows.csv", float_precision="round_trip")
    x = G[G["lead"] == Ld].merge(E8[(E8["lead"] == Ld) & (E8["mode"] == "main")][KEYS + ["mu", "p", "half"]]
                                 .rename(columns={"mu": "mu_E168", "p": "E168", "half": "half_E168"}), on=KEYS)
    m = Al[(Al["lead"] == Ld) & (Al["mode"] == "main") & (Al["seed"] == seed)]
    for a in arms:
        x = x.merge(m[m["arm"] == a][KEYS + ["mu", "p", "half", "cfg"]].rename(columns={"mu": f"mu_{a}", "p": a, "half": f"half_{a}", "cfg": f"cfg_{a}"}), on=KEYS)
    assert len(x) == 72, (Ld, seed, len(x))
    return x


def _metrics(x, a, rng):
    from app.e156 import leads as LD
    mm = E.C.cls_metrics(x, a, rng)
    f_low = 2 * mm["low_precision"] * mm["low_recall"] / max(1e-9, mm["low_precision"] + mm["low_recall"])
    mm["macro_f1"] = round((mm["f1"] + f_low) / 2, 3)
    mm["prob_calibration"] = E.F5.prob_cal(x, a, rng)
    b = pd.cut(x[a], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
    mm["reliability"] = x.groupby(b, observed=False).agg(n=("y_high", "size"), mean_p=(a, "mean"), observed=("y_high", "mean")).round(3).reset_index().astype(str).to_dict("records")
    mm["E156"] = LD.evaluate(x, a, a)["leads"][0]["criteria"]
    return mm


def _mcnemar(x, a, b):
    cA, cB = (x[a] >= .5) == (x["y_high"] == 1), (x[b] >= .5) == (x["y_high"] == 1)
    bb, cc = int((cA & ~cB).sum()), int((~cA & cB).sum())
    return {f"{a}_only_right": bb, f"{b}_only_right": cc, "p": round(float(binomtest(bb, bb + cc, .5).pvalue), 4) if bb + cc else 1.0}


STAB = ("accuracy", "balanced_accuracy", "high_recall", "high_precision", "f1", "macro_f1", "auc", "brier", "calibration_slope")


def evaluate(log=None, d=OUT, exploratory: bool = False, name: str = "E178", protocol: str = "docs/e178/PROTOCOL.md",
             primary_seed: int = A.PRIMARY_SEED, extra_outs=(), decision_text=None) -> dict:
    """Score arm `name` (and every other arm in d/all_rows.csv) on the 72 real outer rows per lead, as lgbm_only.evaluate."""
    log = log or K.RunLog(d / "run_log.jsonl", fresh=False)
    Al = pd.read_csv(d / "all_rows.csv", float_precision="round_trip")
    arms = sorted(a for a in Al["arm"].unique())
    desc = ["PERS", "E168"] + [name] + [a for a in arms if a not in (name, "E168")]
    res = {"protocol": protocol, "primary_seed": primary_seed, "leads": {}, "mcnemar": {}, "stability": {}}
    for Ld in (1, 2):
        x = _frame(Al, Ld, primary_seed, [a for a in arms if a != "E168"])
        rng = np.random.default_rng(178)
        cm = {a: _metrics(x, a, rng) for a in desc}
        dci = E.E7.diff_ci(x, name, "E168", "q_true", np.random.default_rng(178), n=2000)
        res["mcnemar"][Ld] = _mcnemar(x, name, "E168")
        per = {s: {a: {"accuracy": round(float(((g[a] >= .5) == (g["y_high"] == 1)).mean()), 3), "brier": round(float(np.mean((g[a] - g["q_true"]) ** 2)), 4)}
                   for a in ("PERS", "E168", name)} for s, g in x.groupby("survey")}
        sel = x.groupby("survey")[f"cfg_{name}"].first().to_dict()
        res["leads"][Ld] = {"class": cm, f"brier_{name}_minus_E168": {"diff": round(dci["diff"], 4), "ci95": [round(z, 4) for z in dci["ci95"]]},
                            "per_round": per, f"selected_{name}": sel,
                            "brier_minus_E168_by_arm": {a: round(float(np.mean((x[a] - x["q_true"]) ** 2) - np.mean((x["E168"] - x["q_true"]) ** 2)), 4) for a in desc[2:]}}
        if Ld == 1:
            x1 = x
    x = x1
    for m in CONTROLS:
        c = Al[(Al["lead"] == 1) & (Al["mode"] == m) & (Al["arm"] == name)][KEYS + ["mu", "p"]].rename(columns={"mu": f"mu_{m}", "p": m})
        x = x.merge(c, on=KEYS)
    assert len(x) == 72
    x["SHUF"] = x[["shuf1", "shuf2", "shuf3"]].mean(axis=1)
    v = E.E7.diff_ci(x, name, "SHUF", "q_true", np.random.default_rng(178), n=2000)
    res["shuffle"] = {"brier_shuffled": round(float(np.mean((x["SHUF"] - x["q_true"]) ** 2)), 4), f"{name}_minus_shuffled": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]}
    res["leakage_max_abs_change"] = float(np.max(np.abs(x[f"mu_{name}"] - x["mu_corrupt"])))
    e168 = json.loads((E.OUT / "results.json").read_text())
    res["E168_reference"] = {"shuffle": e168["shuffle"], "leakage_max_abs_change": e168["leakage_max_abs_change"]}
    # stability over generator seeds
    seeds = sorted(Al["seed"].unique())
    rule12 = []
    for Ld in (1, 2):
        per_seed = {}
        for sd in seeds:
            xs = _frame(Al, Ld, sd, [name])
            mm = E.C.cls_metrics(xs, name, np.random.default_rng(178))
            dd = E.E7.diff_ci(xs, name, "E168", "q_true", np.random.default_rng(178), n=2000)
            f_low = 2 * mm["low_precision"] * mm["low_recall"] / max(1e-9, mm["low_precision"] + mm["low_recall"])
            per_seed[int(sd)] = {**{k: mm[k] for k in STAB if k != "macro_f1"}, "macro_f1": round((mm["f1"] + f_low) / 2, 3),
                                 "brier_minus_E168": round(dd["diff"], 4), "brier_minus_E168_ci95": [round(z, 4) for z in dd["ci95"]],
                                 "accuracy_E168": round(float(((xs["E168"] >= .5) == (xs["y_high"] == 1)).mean()), 3)}
        res["stability"][Ld] = {"per_seed": per_seed, "mean_sd": {k: [round(float(np.mean([p[k] for p in per_seed.values()])), 4),
                                                                      round(float(np.std([p[k] for p in per_seed.values()], ddof=1)), 4) if len(per_seed) > 1 else None]
                                                                  for k in list(STAB) + ["brier_minus_E168"]}}
    for sd in seeds:
        rule12.append(int(sd) if all(res["stability"][Ld]["per_seed"][int(sd)]["brier_minus_E168_ci95"][1] < 0 and
                                     res["stability"][Ld]["per_seed"][int(sd)]["accuracy"] >= res["stability"][Ld]["per_seed"][int(sd)]["accuracy_E168"]
                                     for Ld in (1, 2)) else None)
    res["seeds_meeting_criteria_1_2"] = [s for s in rule12 if s is not None]
    bp = d / "balance.csv"                       # class balance (primary seed, final fits)
    if bp.exists():
        b = pd.read_csv(bp)
        f = b[b["fold"].astype(str) == "final"]
        keep = [c for c in ("job", "setting", "generator", "ratio", "n_real", "real_high", "real_low", "n_syn", "syn_high", "syn_low", "smote_fallback_jitter") if c in f]
        res["class_balance_final_fits"] = f[keep].to_dict("records")
    l1, l2 = res["leads"][1], res["leads"][2]
    acc = {"brier_ci_upper_below_0_lead1": l1[f"brier_{name}_minus_E168"]["ci95"][1] < 0,
           "brier_ci_upper_below_0_lead2": l2[f"brier_{name}_minus_E168"]["ci95"][1] < 0,
           "accuracy_at_least_E168_lead1": l1["class"][name]["accuracy"] >= l1["class"]["E168"]["accuracy"],
           "accuracy_at_least_E168_lead2": l2["class"][name]["accuracy"] >= l2["class"]["E168"]["accuracy"],
           "leakage_below_1e-9": res["leakage_max_abs_change"] < 1e-9,
           "beats_shuffled": res["shuffle"]["ci95"][1] < 0}
    res["decision_rule"] = acc
    res["decision"] = (f"{name} BETTER THAN E168 (candidate only; not promoted)" if all(acc.values())
                       else f"{name}: SYNTHETIC AUGMENTATION DID NOT IMPROVE THE MODEL (E168 stays in production)")
    if exploratory:
        res["status"] = EXP_NOTE
        res["seeds_available"] = [int(s) for s in seeds]
        res["decision"] = ("EXPLORATORY, outside the protocol (the E178 result stays 'Stage 2 not run'): the augmented model "
                           + ("would have met" if all(acc.values()) else "would NOT have met") + " the pre-registered decision rule.")
    if decision_text:
        res["decision"] = decision_text(acc, res)
    K.dump_json(res, d / "results.json")
    log("evaluated", decision=res["decision"], rule=acc)
    if exploratory:
        outs = [d / n for n in ("all_rows.csv", "balance.csv", "results.json")] + sorted((d / "synthetic").rglob("*.parquet")) + sorted(d.glob("rows_phase*.csv"))
    elif name == "E178":
        outs = [d / n for n in ("all_rows.csv", "balance.csv", "results.json", "fidelity.json", "equivalence.json", "deviations.json")] + \
               [K.SYN / "train" / f"train_rows_seed{A.PRIMARY_SEED}.parquet"]
    else:
        outs = [d / n for n in ("all_rows.csv", "balance.csv", "results.json")] + list(extra_outs)
    log("hashes")
    K.write_hashes(outs + [d / "run_log.jsonl"], d / "hashes.json")
    _print(res, name)
    return res


# ------------------------------------------------------------------------------------- exploratory (deviation D2)
EXP = K.ROOT / "exploratory"
EXP_NOTE = ("EXPLORATORY, outside docs/e178/PROTOCOL.md (deviation D2, run at the owner's request on 2026-11-09). Both "
            "generators failed the pre-registered fidelity criteria, so the protocol's result is 'Stage 2 not run' and E168 "
            "stays in production; these numbers cannot change that result. Otherwise the Stage 2 design is unchanged: both "
            "generators, r in {0.25, 0.5, 1.0} chosen by inner region GroupKFold, synthetic weight 0.4, seeds 17801-17805, "
            "controls at Lead 1, metrics on the 72 real outer rows only.")


def explore() -> None:
    """python -m app.e178.retrain explore 1|2. Phase 1: primary seed and the Lead-1 controls; phase 2: the four stability
    seeds. Each phase re-evaluates everything available. Writes only to data/e178/exploratory/."""
    phase = sys.argv[2] if len(sys.argv) > 2 else "1"
    if phase not in ("1", "2", "eval"):
        sys.exit("usage: python -m app.e178.retrain explore 1|2|eval")
    if phase == "eval":                          # re-score the saved rows only (no refit)
        evaluate(K.RunLog(EXP / "run_log.jsonl", fresh=False), EXP, exploratory=True)
        return
    EXP.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(EXP / "run_log.jsonl", fresh=(phase == "1"))
    _check_inputs(log)
    log("start", phase=phase, note=EXP_NOTE, menu=MENU, seeds=A.SEEDS, syn_weight=A.SYN_WEIGHT, n_jobs=N_JOBS,
        protocol_sha256=K.sha256(K.DOCS / "PROTOCOL.md"))
    H, L, S_P = K.pipeline_inputs()
    if phase == "1":
        jobs = [(s, l, "main", A.PRIMARY_SEED) for s, l in MAIN] + [(s, 1, m, A.PRIMARY_SEED) for s in SURVEYS for m in CONTROLS]
    else:
        jobs = [(s, l, "main", sd) for sd in A.SEEDS[1:] for s, l in MAIN]
    jobs.sort(key=lambda j: SURVEYS.index(j[0]))
    t0 = time.time()
    R = Parallel(n_jobs=N_JOBS, verbose=5)(delayed(task_aug)(s, l, H, L, S_P, m, sd, MENU, keep_syn=(phase == "1" and m == "main"))
                                           for s, l, m, sd in jobs)
    for r in R:
        log("job", job=r["job"], seed=r["seed"], seconds=r["seconds"], n_train=r["n_train"], n_test=r["n_test"])
    pd.concat([r["rows"] for r in R], ignore_index=True).to_csv(EXP / f"rows_phase{phase}.csv", index=False, lineterminator="\n")
    if phase == "1":
        pd.concat([r["balance"] for r in R if r["job"].endswith("|main")], ignore_index=True).to_csv(EXP / "balance.csv", index=False, lineterminator="\n")
        (EXP / "synthetic" / "train").mkdir(parents=True, exist_ok=True)
        pd.concat([r["syn"] for r in R if r["syn"] is not None], ignore_index=True).to_parquet(
            EXP / "synthetic" / "train" / f"train_rows_seed{A.PRIMARY_SEED}.parquet", index=False)
    parts = [pd.read_csv(p, float_precision="round_trip") for p in sorted(EXP.glob("rows_phase*.csv"))]
    pd.concat(parts, ignore_index=True).to_csv(EXP / "all_rows.csv", index=False, lineterminator="\n")
    log("fitted", phase=phase, seconds=round(time.time() - t0, 1))
    evaluate(log, EXP, exploratory=True)


def _print(res, name: str = "E178") -> None:
    print(json.dumps({k: res[k] for k in ("decision", "decision_rule", "leakage_max_abs_change", "shuffle", "mcnemar", "seeds_meeting_criteria_1_2")}, indent=1, default=str))
    cols = ("accuracy", "balanced_accuracy", "high_precision", "high_recall", "f1", "macro_f1", "auc", "brier", "calibration_slope", "calibration_slope_ci95")
    for Ld in (1, 2):
        r = res["leads"][Ld]
        print(f"\nLead {Ld}  Brier {name}-E168 {r[f'brier_{name}_minus_E168']}  selected {r[f'selected_{name}']}")
        print(pd.DataFrame({a: {c: v.get(c) for c in cols} | {"conf": v["confusion"]} for a, v in r["class"].items()}).T.to_string())
        print("stability mean/sd:", res["stability"][Ld]["mean_sd"])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"equiv": equiv, "fidelity": fidelity, "eval": run_eval, "report": evaluate, "explore": explore}.get(
        cmd, lambda: sys.exit("usage: python -m app.e178.retrain equiv | fidelity | eval | report | explore 1|2"))()

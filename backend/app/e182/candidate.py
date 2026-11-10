"""
E182 (docs/e182/PROTOCOL.md): E168's selection plus one fixed augmentation setting (jitter, r = 2, weight 1.0, 0.5 SD,
boundary focus), averaged over generator seeds 17901-17905, with the leakage and shuffled controls and an ENNS 2022 seal.

    python -m app.e182.candidate run    main jobs + Lead-1 controls -> data/e182/out/all_rows.csv, results.json
    python -m app.e182.candidate seal   ENNS 2022 forecasts -> data/e182/out/sealed_enns2022.json

Everything reuses the shared pipeline: E168's selection loop (Stage A), app.e178.augment's generators through
app.e179.tuned._augment, app.e178.retrain.LGBResAug / _calibrate / evaluate.
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from datetime import datetime, timezone
from itertools import product

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e168 import lgbm_only as E
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e179 import tuned as T

warnings.filterwarnings("ignore")
OUT = K.D / "e182" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e182" / "PROTOCOL.md"
SETTING = ("jitter", 2.0, 1.0, 0.5, "boundary")
NAME = "E182"
SEAL = OUT / "sealed_enns2022.json"


def stage_a(tr, AN, folds):
    """E168's selection on real rows (the loop of app.e168.lgbm_only.run_proc)."""
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    best = None
    for a, f, pr, h in product(E.ANCH, E.FS, (False, True), E.HPO):
        atr = AN[a][0]
        oof = np.zeros(len(tr))
        for i_tr, i_te in folds:
            oof[i_te] = atr[i_te] + E.LGBRes(E.FS[f], *h, pr).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
        sse = float(np.sum(w * (y - oof) ** 2))
        if best is None or sse < best["sse"]:
            best = {"sse": sse, "cfg": (a, f, pr, h), "oof": oof}
    return best["cfg"], best["oof"]


def fixed(tr, te, AN, seeds, stream, setting=SETTING, contrib=False, oof_p=False):
    """E168 (no augmentation) and the fixed-setting candidate (mean over `seeds`) for one outer job. With contrib=True also
    the mean over seeds of the final models' LightGBM contributions on te (for the dashboard's driver bars)."""
    assert "is_synthetic" not in te.columns, "outer rows must be real"
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    y, q, w = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cfg, base_oof = stage_a(tr, AN, folds)
    a, f, pr, h = cfg
    atr, ate = AN[a]
    an_all = {x: np.asarray(AN[x][0], float) for x in E.ANCH}
    mdl = E.LGBRes(E.FS[f], *h, pr).fit(tr.assign(e=y - atr))
    P0, c0, _ = RT._calibrate(tr, te, folds, base_oof, ate + mdl.predict(te), y, q, w, gap)
    tag = f"{a}|{f}|prune={pr}|leaves={h[0]},minchild={h[1]},lambda={h[2]},trees={h[3]}"
    runs, cals, contribs, use_cols, oofps = [], [], [], None, []
    for seed in seeds:
        oof = np.zeros(len(tr))
        for fi, (i_tr, i_te) in enumerate(folds):
            syn, sa = T._augment(tr.iloc[i_tr].reset_index(drop=True), {x: v[i_tr] for x, v in an_all.items()}, setting, seed, stream, fi)[:2]
            m = RT.LGBResAug(E.FS[f], *h, pr)
            m.syn_weight = setting[2]
            m.fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr]), syn.assign(e=syn["y_true"].values - sa[a]))
            oof[i_te] = atr[i_te] + m.predict(tr.iloc[i_te])                     # real held-out rows only
        syn, sa = T._augment(tr, an_all, setting, seed, stream, "final")[:2]
        m = RT.LGBResAug(E.FS[f], *h, pr)
        m.syn_weight = setting[2]
        m.fit(tr.assign(e=y - atr), syn.assign(e=syn["y_true"].values - sa[a]))
        P, chosen, _ = RT._calibrate(tr, te, folds, oof, ate + m.predict(te), y, q, w, gap)
        if oof_p:                                   # E187: real training rows' inner out-of-fold P(HIGH), raw layer
            oofps.append(norm.cdf(oof / E.A4.scale(y - oof, gap, gap)[0]))
        runs.append(P[chosen])
        cals.append(chosen)
        if contrib:
            contribs.append(m.m_.predict(te[m.use_], pred_contrib=True))
            use_cols = list(m.use_)
    mean = tuple(np.mean([np.asarray(r[k]) for r in runs], axis=0) for k in range(3))
    out = {"E168": P0[c0], NAME: mean, "cfg": tag, "cal_E168": c0, "cal_seeds": cals}
    if contrib:
        out["contrib"], out["contrib_cols"], out["anchor"] = np.mean(contribs, axis=0), use_cols, np.asarray(ate, float)
    if oof_p:
        out["oof_p"], out["train_high"] = np.mean(oofps, axis=0), (y >= 0).astype(int)
    return out


def job(survey, lead, H, L, S_P, mode):
    t0 = time.time()
    tr, te, AN = RT.build(survey, lead, H, L, S_P, mode)
    stream = RT.job_id(survey, lead, "main" if mode in ("main", "corrupt") else mode)   # corrupt on the main stream (D3)
    r = fixed(tr, te, AN, T.SEEDS, stream)
    rows = []
    for arm in ("E168_rerun", NAME):
        mu, p, half = r["E168" if arm == "E168_rerun" else NAME]
        o = te[RT.KEYS].copy().reset_index(drop=True)
        o["mode"], o["arm"], o["seed"], o["mu"], o["p"], o["half"] = mode, arm, 0, mu, p, half
        o["cfg"] = f"{r['cfg']}|cal={r['cal_E168']}" + ("" if arm == "E168_rerun" else f"|aug={T.setting_name(SETTING)}|seeds=17901-17905|cal={'/'.join(r['cal_seeds'])}")
        rows.append(o)
    return {"rows": pd.concat(rows, ignore_index=True), "job": RT.job_id(survey, lead, mode), "seconds": round(time.time() - t0, 1)}


def _decision(acc, res):
    return (f"{NAME} BETTER THAN E168 on the pre-registered rule (candidate only; not promoted; the owner decides)" if all(acc.values())
            else f"{NAME}: DID NOT MEET THE PRE-REGISTERED RULE (E168 stays in production)")


def evaluate(log=None) -> dict:
    log = log or K.RunLog(OUT / "run_log.jsonl", fresh=False)
    Al = pd.read_csv(OUT / "all_rows.csv", float_precision="round_trip")
    v = pd.read_csv(K.D / "e181" / "out" / "variant_rows.csv", float_precision="round_trip")
    v = v[v["variant"] == T.setting_name(SETTING)].groupby(RT.KEYS)[["mu", "p"]].mean().reset_index()
    c = Al[(Al["arm"] == NAME) & (Al["mode"] == "main")].merge(v, on=RT.KEYS, suffixes=("", "_e181"))
    e8 = pd.read_csv(E.OUT / "all_rows.csv", float_precision="round_trip")
    d8 = Al[Al["arm"] == "E168_rerun"].merge(e8, on=RT.KEYS + ["mode"], suffixes=("", "_e168"))
    checks = {"same_as_e181_variant": {"rows": int(len(c)), "max_abs_diff_p": float(np.max(np.abs(c["p"] - c["p_e181"])))},
              "e168_rerun": {"rows": int(len(d8)), "max_abs_diff_p": float(np.max(np.abs(d8["p"] - d8["p_e168"])))}}
    log("checks", **checks)
    extra = [SEAL] if SEAL.exists() else []
    res = RT.evaluate(log, OUT, name=NAME, protocol="docs/e182/PROTOCOL.md", primary_seed=0, extra_outs=extra, decision_text=_decision)
    res["checks"] = checks
    res["e181_forward_check_reference"] = json.loads((K.D / "e181" / "out" / "post_hoc_nofloor.json").read_text())["select_then_test_on_2019_2021"]
    K.dump_json(res, OUT / "results.json")
    K.write_hashes([OUT / n for n in ("all_rows.csv", "results.json")] + extra + [OUT / "run_log.jsonl"], OUT / "hashes.json")
    print("checks:", checks)
    return res


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL), setting=T.setting_name(SETTING), seeds=T.SEEDS)
    H, L, S_P = K.pipeline_inputs()
    jobs = [(s, l, "main") for s, l in RT.MAIN] + [(s, 1, m) for s in RT.SURVEYS for m in RT.CONTROLS]
    jobs.sort(key=lambda j: RT.SURVEYS.index(j[0]))
    t0 = time.time()
    R = Parallel(n_jobs=RT.N_JOBS, verbose=5)(delayed(job)(s, l, H, L, S_P, m) for s, l, m in jobs)
    pd.concat([r["rows"] for r in R], ignore_index=True).to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    for r in R:
        log("job", job=r["job"], seconds=r["seconds"])
    log("fitted", seconds=round(time.time() - t0, 1))
    evaluate(log)


# ------------------------------------------------------------------------------------------------- ENNS 2022 seal
def _seal_lead(lead, H, L, S_P):
    from app.e168 import enns2022_seal as S22

    def stop(tr, te, AN, ablate=False):
        raise RT._Captured(tr, te, AN)

    with K.patched(S22, "run_proc", stop):
        try:
            S22.task(lead, H, L, S_P)
            raise RuntimeError("enns2022_seal.task did not reach run_proc")
        except RT._Captured as c:
            tr, te, AN = c.args
    te = te.reset_index(drop=True)
    r = fixed(tr, te, AN, T.SEEDS, f"ENNS2022|L{lead}|seal")
    pct = lambda z: 100 / (1 + np.exp(-np.asarray(z, float)))
    o = te[[c for c in ("key", "province", "region", "island", "lead", "gap_q") if c in te]].copy()
    for name, (mu, p, half) in (("E168", r["E168"]), (NAME, r[NAME])):
        o[f"{name}_score"], o[f"{name}_p_high"] = pct(mu).round(2), np.round(p, 4)
        o[f"{name}_low90"], o[f"{name}_high90"] = pct(mu - half).round(2), pct(mu + half).round(2)
        o[f"{name}_class"], o[f"mu_{name}"] = np.where(np.asarray(p) >= .5, "HIGH", "LOW"), mu
    return o


def seal() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl", fresh=not (OUT / "run_log.jsonl").exists())
    if SEAL.exists():
        raise SystemExit("already sealed: " + K.sha256(SEAL))
    RT._check_inputs(log)
    H, L, S_P = K.pipeline_inputs()
    F = pd.concat(Parallel(n_jobs=2)(delayed(_seal_lead)(l, H, L, S_P) for l in (1, 2)), ignore_index=True)
    old = json.loads((K.D / "e168" / "out" / "sealed_enns2022.json").read_text())
    m = pd.DataFrame(old["forecasts"]).merge(F[["key", "lead", "mu_E168"]], on=["key", "lead"], suffixes=("_sealed", "_rerun"))
    check = {"rows": int(len(m)), "of": len(old["forecasts"]), "max_abs_diff_mu": float(np.max(np.abs(m["mu_E168_sealed"] - m["mu_E168_rerun"])))}
    doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "target": old["target"], "origin": old["origin"],
           "model": f"{NAME}: E168's selection + fixed augmentation {T.setting_name(SETTING)}, mean of seeds 17901-17905 (docs/e182/PROTOCOL.md)",
           "rule": "HIGH = p_high >= 0.5; score only on HFIAS moderate_or_severe provincial rows once public and verified comparable; no re-fitting",
           "e168_seal_check": check, "forecasts": F.round(6).to_dict("records")}
    SEAL.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8", newline="\n")
    sha = K.sha256(SEAL)
    log("sealed", sha256=sha, rows=len(F), e168_check=check)
    print("sealed", len(F), "rows; sha256", sha, "; E168 check", check)


# ----------------------------------------------------------------------------------- Lead 3 (descriptive addendum)
def lead3() -> None:
    """Addendum (owner question, 2026-11-10): E182 at Lead 3, the third served lead, on the same 72 real rows, against
    E168's stored Lead-3 rows (data/e168/out/all_rows_l3_8.csv, app.e168.longer_leads). The setting was fixed using
    Leads 1-2 only. Descriptive: the pre-registered decision covered Leads 1-2."""
    from scipy.stats import binomtest
    log = K.RunLog(OUT / "run_log.jsonl", fresh=False)
    RT._check_inputs(log)
    if (OUT / "lead3_rows.csv").exists() and "--refit" not in sys.argv:          # re-score the saved rows
        rows = pd.read_csv(OUT / "lead3_rows.csv", float_precision="round_trip")
    else:
        H, L, S_P = K.pipeline_inputs()
        R = Parallel(n_jobs=3)(delayed(job)(s, 3, H, L, S_P, "main") for s in RT.SURVEYS)
        rows = pd.concat([r["rows"] for r in R], ignore_index=True)
        rows.to_csv(OUT / "lead3_rows.csv", index=False, lineterminator="\n")
    e8 = pd.read_csv(E.OUT / "all_rows_l3_8.csv", float_precision="round_trip")
    e8 = e8[(e8["lead"] == 3) & (e8["mode"] == "main")]
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    x = G[G["lead"] == 3].merge(e8[RT.KEYS + ["mu", "p", "half"]].rename(columns={"mu": "mu_E168", "p": "E168", "half": "half_E168"}), on=RT.KEYS)
    for arm, col in ((NAME, NAME), ("E168_rerun", "E168_rerun")):
        x = x.merge(rows[rows["arm"] == arm][RT.KEYS + ["mu", "p", "half"]].rename(columns={"mu": f"mu_{col}", "p": col, "half": f"half_{col}"}), on=RT.KEYS)
    assert len(x) == 72
    rerun = float(np.max(np.abs(x["E168"] - x["E168_rerun"])))
    rng = np.random.default_rng(182)
    keep = ("accuracy", "balanced_accuracy", "high_precision", "high_recall", "low_recall", "f1", "auc", "brier", "calibration_slope", "confusion")
    met = {a: {k: v for k, v in RT._metrics(x, a, rng).items() if k in keep} for a in ("PERS", "E168", NAME)}
    d = E.E7.diff_ci(x, NAME, "E168", "q_true", np.random.default_rng(182), n=2000)
    cA, cB = (x[NAME] >= .5) == (x["y_high"] == 1), (x["E168"] >= .5) == (x["y_high"] == 1)
    bb, cc = int((cA & ~cB).sum()), int((~cA & cB).sum())
    doc = {"label": "Descriptive addendum: Lead 3 was not part of the pre-registered E182 decision (Leads 1-2)",
           "rows": int(len(x)), "e168_rerun_max_abs_diff_p": rerun, "metrics": met,
           "brier_E182_minus_E168": {"diff": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]]},
           "mcnemar": {"E182_only_right": bb, "E168_only_right": cc, "p": round(float(binomtest(bb, bb + cc, .5).pvalue), 4) if bb + cc else 1.0}}
    K.dump_json(doc, OUT / "lead3_results.json")
    log("lead3", **{k: doc[k] for k in ("rows", "e168_rerun_max_abs_diff_p", "brier_E182_minus_E168", "mcnemar")})
    K.write_hashes([OUT / n for n in ("all_rows.csv", "results.json", "sealed_enns2022.json", "lead3_rows.csv", "lead3_results.json")]
                   + [OUT / "run_log.jsonl"], OUT / "hashes.json")
    print(pd.DataFrame({a: {k: m[k] for k in keep if k != "confusion"} | {"conf": m["confusion"]} for a, m in met.items()}).T.to_string())
    print("Brier E182-E168:", doc["brier_E182_minus_E168"], "McNemar:", doc["mcnemar"], "E168 rerun diff:", rerun)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"run": run, "report": evaluate, "seal": seal, "lead3": lead3}.get(
        cmd, lambda: sys.exit("usage: python -m app.e182.candidate run | report | seal | lead3"))()

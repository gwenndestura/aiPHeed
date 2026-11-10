"""
E185 (docs/e185/PROTOCOL.md): E184's setting as the base, 17 alternatives (12 Gaussian-copula, 4 jitter, none), chosen
per job and seed on inner region folds with a one-standard-error rule against E184's setting (app.e179.tuned.
run_proc_tuned with base_setting); forecast = mean over seeds 17901-17905; Leads 1-3, controls, ENNS 2022 seal.

    python -m app.e185.candidate run    -> data/e185/out/all_rows.csv, selection.csv, results.json
    python -m app.e185.candidate seal   -> data/e185/out/sealed_enns2022.json
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import binomtest

from app.e168 import lgbm_only as E
from app.e178 import augment as A
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e179 import tuned as T

warnings.filterwarnings("ignore")
OUT = K.D / "e185" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e185" / "PROTOCOL.md"
E184_SETTING = ("jitter", 1.0, 1.0, 0.5, "boundary")
SETTINGS = ([None, E184_SETTING]
            + [("copula", r, w, A.JITTER_SD, f) for r in (0.5, 1.0, 2.0) for w in (0.5, 1.0) for f in ("uniform", "boundary")]
            + [("jitter", r, w, 0.5, "boundary") for r in (0.5, 2.0) for w in (0.5, 1.0)])
NAME = "E185"
LEADS = (1, 2, 3)
SEAL = OUT / "sealed_enns2022.json"


def _mean_rows(rows, te, arm_in="E179"):
    """Mean over seeds of the chosen setting's forecast (the arm run_proc_tuned calls 'E179')."""
    d = pd.concat([r for r in rows if r["arm"].iloc[0] == arm_in], ignore_index=True)
    return d.groupby(RT.KEYS, sort=False)[["mu", "p", "half"]].mean().reset_index()


def job(survey, lead, H, L, S_P, mode):
    t0 = time.time()
    tr, te, AN = RT.build(survey, lead, H, L, S_P, mode)
    jid = RT.job_id(survey, lead, mode)
    stream = RT.job_id(survey, lead, "main" if mode in ("main", "corrupt") else mode)
    rows, sel, _, _ = T.run_proc_tuned(tr, te, AN, T.SEEDS, jid, settings=SETTINGS, stream=stream, base_setting=E184_SETTING)
    m = _mean_rows(rows, te).assign(arm=NAME)
    e168 = next(r for r in rows if r["arm"].iloc[0] == "E168_rerun")[RT.KEYS + ["mu", "p", "half"]].assign(arm="E168_rerun")
    out = pd.concat([m, e168], ignore_index=True).assign(mode=mode, seed=0)
    out["cfg"] = np.where(out["arm"] == NAME, "E185 = mean over seeds of the inner-fold choice (base E184)", "E168")
    return {"rows": out, "sel": pd.DataFrame(sel).assign(mode=mode), "job": jid, "seconds": round(time.time() - t0, 1)}


def _frame(Ld, rows):
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    if Ld == 3:
        e8 = pd.read_csv(E.OUT / "all_rows_l3_8.csv", float_precision="round_trip")
        e84 = pd.read_csv(K.D / "e184" / "out" / "lead3_rows.csv", float_precision="round_trip")
    else:
        e8 = pd.read_csv(E.OUT / "all_rows.csv", float_precision="round_trip")
        e84 = pd.read_csv(K.D / "e184" / "out" / "all_rows.csv", float_precision="round_trip")
    x = G[G["lead"] == Ld]
    for name, src in (("E168", e8[(e8["lead"] == Ld) & (e8["mode"] == "main")]),
                      ("E184", e84[(e84["lead"] == Ld) & (e84["mode"] == "main") & (e84["arm"] == "E184")]),
                      (NAME, rows[(rows["lead"] == Ld) & (rows["mode"] == "main") & (rows["arm"] == NAME)])):
        x = x.merge(src[RT.KEYS + ["mu", "p", "half"]].rename(columns={"mu": f"mu_{name}", "p": name, "half": f"half_{name}"}), on=RT.KEYS)
    assert len(x) == 72, (Ld, len(x))
    return x


def evaluate(log=None) -> dict:
    log = log or K.RunLog(OUT / "run_log.jsonl", fresh=False)
    rows = pd.read_csv(OUT / "all_rows.csv", float_precision="round_trip")
    sel = pd.read_csv(OUT / "selection.csv")
    keep = ("accuracy", "balanced_accuracy", "high_precision", "high_recall", "low_recall", "f1", "macro_f1", "auc", "brier", "calibration_slope", "confusion")
    res = {"protocol": "docs/e185/PROTOCOL.md", "leads": {}}
    for Ld in LEADS:
        x = _frame(Ld, rows)
        rng = np.random.default_rng(185)
        met = {a: {k: v for k, v in RT._metrics(x, a, rng).items() if k in keep} for a in ("PERS", "E168", "E184", NAME)}
        ci = {b: E.E7.diff_ci(x, NAME, b, "q_true", np.random.default_rng(185), n=2000) for b in ("PERS", "E168", "E184")}
        cA, cB = (x[NAME] >= .5) == (x["y_high"] == 1), (x["E184"] >= .5) == (x["y_high"] == 1)
        bb, cc = int((cA & ~cB).sum()), int((~cA & cB).sum())
        res["leads"][Ld] = {"metrics": met, **{f"brier_minus_{b}": {"diff": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]} for b, v in ci.items()},
                            "mcnemar_vs_E184": {"E185_only_right": bb, "E184_only_right": cc, "p": round(float(binomtest(bb, bb + cc, .5).pvalue), 4) if bb + cc else 1.0},
                            "same_as_E184_rows": int(np.isclose(x[NAME], x["E184"], atol=1e-12).sum())}
    x1 = _frame(1, rows)
    for m in RT.CONTROLS:
        c = rows[(rows["lead"] == 1) & (rows["mode"] == m) & (rows["arm"] == NAME)][RT.KEYS + ["mu", "p"]].rename(columns={"mu": f"mu_{m}", "p": m})
        x1 = x1.merge(c, on=RT.KEYS)
    x1["SHUF"] = x1[["shuf1", "shuf2", "shuf3"]].mean(axis=1)
    v = E.E7.diff_ci(x1, NAME, "SHUF", "q_true", np.random.default_rng(185), n=2000)
    res["shuffle"] = {"brier_shuffled": round(float(np.mean((x1["SHUF"] - x1["q_true"]) ** 2)), 4), "E185_minus_shuffled": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]}
    res["leakage_max_abs_change"] = float(np.max(np.abs(x1[f"mu_{NAME}"] - x1["mu_corrupt"])))
    main = sel[sel["mode"] == "main"]
    res["selection"] = {"share_kept_E184": round(float((main["chosen"] == T.setting_name(E184_SETTING)).mean()), 3),
                        "share_copula": round(float(main["chosen"].str.startswith("copula").mean()), 3),
                        "chosen_counts": main["chosen"].value_counts().to_dict()}
    L = res["leads"]
    better = {f"lead{Ld}_brier_ci_vs_E184_below_0": L[Ld]["brier_minus_E184"]["ci95"][1] < 0 for Ld in LEADS}
    better |= {f"lead{Ld}_accuracy_at_least_E184": L[Ld]["metrics"][NAME]["accuracy"] >= L[Ld]["metrics"]["E184"]["accuracy"] for Ld in LEADS}
    owner = {f"lead{Ld}_accuracy_at_least_75": L[Ld]["metrics"][NAME]["accuracy"] >= 0.75 for Ld in LEADS}
    owner |= {f"lead{Ld}_beats_persistence": L[Ld]["brier_minus_PERS"]["ci95"][1] < 0 for Ld in LEADS}
    owner["leakage_below_1e-9"] = res["leakage_max_abs_change"] < 1e-9
    res |= {"better_than_E184_rule": better, "owner_rule": owner,
            "decision": ("E185 BETTER THAN E184" if all(better.values()) and all(owner.values())
                         else "THE NEW SYNTHETIC GENERATOR DID NOT IMPROVE E184 (E184 stays the synthetic-data candidate)")}
    K.dump_json(res, OUT / "results.json")
    log("evaluated", decision=res["decision"], selection=res["selection"])
    K.write_hashes([OUT / n for n in ("all_rows.csv", "selection.csv", "results.json")] + ([SEAL] if SEAL.exists() else []) + [OUT / "run_log.jsonl"], OUT / "hashes.json")
    for Ld in LEADS:
        m = L[Ld]["metrics"]
        print(f"Lead {Ld}:", {a: (m[a]["accuracy"], m[a]["balanced_accuracy"], m[a]["high_recall"], m[a]["brier"]) for a in m},
              "vsE184", L[Ld]["brier_minus_E184"], L[Ld]["mcnemar_vs_E184"], "rows equal to E184:", L[Ld]["same_as_E184_rows"])
    print("selection:", res["selection"]); print("leakage", res["leakage_max_abs_change"], "shuffle", res["shuffle"]); print(res["decision"])
    return res


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl", fresh=not (OUT / "run_log.jsonl").exists())
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL), n_settings=len(SETTINGS), seeds=T.SEEDS)
    H, L, S_P = K.pipeline_inputs()
    jobs = [(s, l, "main") for s in RT.SURVEYS for l in LEADS] + [(s, 1, m) for s in RT.SURVEYS for m in RT.CONTROLS]
    jobs.sort(key=lambda j: RT.SURVEYS.index(j[0]))
    t0 = time.time()
    R = Parallel(n_jobs=RT.N_JOBS, verbose=5)(delayed(job)(s, l, H, L, S_P, m) for s, l, m in jobs)
    pd.concat([r["rows"] for r in R], ignore_index=True).to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    pd.concat([r["sel"] for r in R], ignore_index=True).to_csv(OUT / "selection.csv", index=False, lineterminator="\n")
    for r in R:
        log("job", job=r["job"], seconds=r["seconds"])
    log("fitted", seconds=round(time.time() - t0, 1))
    evaluate(log)


def _seal_lead(lead, H, L, S_P):
    from app.e168 import enns2022_seal as S22

    def stop(tr, te, AN, ablate=False):
        raise RT._Captured(tr, te, AN)

    with K.patched(S22, "run_proc", stop):
        try:
            S22.task(lead, H, L, S_P)
            raise RuntimeError("enns2022_seal.task did not reach run_proc")
        except RT._Captured as c_:
            tr, te, AN = c_.args
    te = te.reset_index(drop=True).assign(survey="ENNS2022")
    rows, _, _, _ = T.run_proc_tuned(tr, te, AN, T.SEEDS, f"ENNS2022|L{lead}|seal", settings=SETTINGS, base_setting=E184_SETTING)
    m = _mean_rows(rows, te)
    e168 = next(r for r in rows if r["arm"].iloc[0] == "E168_rerun")
    pct = lambda z: 100 / (1 + np.exp(-np.asarray(z, float)))
    o = te[[c for c in ("key", "province", "region", "island", "lead", "gap_q") if c in te]].copy()
    for name, d in (("E168", e168), (NAME, m)):
        mu, p, half = d["mu"].values, d["p"].values, d["half"].values
        o[f"{name}_score"], o[f"{name}_p_high"] = pct(mu).round(2), np.round(p, 4)
        o[f"{name}_low90"], o[f"{name}_high90"] = pct(mu - half).round(2), pct(mu + half).round(2)
        o[f"{name}_class"], o[f"mu_{name}"] = np.where(p >= .5, "HIGH", "LOW"), mu
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
    mm = pd.DataFrame(old["forecasts"]).merge(F[["key", "lead", "mu_E168"]], on=["key", "lead"], suffixes=("_sealed", "_rerun"))
    check = {"rows": int(len(mm)), "of": len(old["forecasts"]), "max_abs_diff_mu": float(np.max(np.abs(mm["mu_E168_sealed"] - mm["mu_E168_rerun"])))}
    doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "target": old["target"], "origin": old["origin"],
           "model": "E185: E184's setting as base, inner-fold choice among 18 settings (Gaussian copula, jitter), mean of seeds 17901-17905",
           "rule": "HIGH = p_high >= 0.5; score only on HFIAS moderate_or_severe provincial rows once public and verified comparable; no re-fitting",
           "e168_seal_check": check, "forecasts": F.round(6).to_dict("records")}
    SEAL.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8", newline="\n")
    log("sealed", sha256=K.sha256(SEAL), rows=len(F), e168_check=check)
    print("sealed", len(F), "rows; sha256", K.sha256(SEAL), "; E168 check", check)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"run": run, "report": evaluate, "seal": seal}.get(cmd, lambda: sys.exit("usage: python -m app.e185.candidate run | report | seal"))()

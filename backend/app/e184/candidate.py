"""
E184 evaluation (docs/e184/PROTOCOL.md): E168's selection plus synthetic training rows balanced 50/50 with the real rows
(jitter, r = 1, weight 1.0, 0.5 SD, boundary focus; mean of seeds 17901-17905), at the three served leads, with the
leakage and shuffled controls, the owner's deployment rule, and an ENNS 2022 seal.

    python -m app.e184.candidate run    -> data/e184/out/all_rows.csv, lead3_rows.csv, results.json
    python -m app.e184.candidate seal   -> data/e184/out/sealed_enns2022.json

Reuses app.e182.candidate.fixed (E168's selection loop + fixed augmentation) with E184's setting.
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
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e179 import tuned as T
from app.e182 import candidate as C

warnings.filterwarnings("ignore")
OUT = K.D / "e184" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e184" / "PROTOCOL.md"
SETTING = ("jitter", 1.0, 1.0, 0.5, "boundary")       # 50/50: one synthetic row per real row, equal weight
NAME = "E184"
MODEL_ID = "e184-lgbm-syn50-1.0"
SEAL = OUT / "sealed_enns2022.json"
LEADS = (1, 2, 3)


def job(survey, lead, H, L, S_P, mode):
    t0 = time.time()
    tr, te, AN = RT.build(survey, lead, H, L, S_P, mode)
    stream = RT.job_id(survey, lead, "main" if mode in ("main", "corrupt") else mode)
    r = C.fixed(tr, te, AN, T.SEEDS, stream, setting=SETTING)
    rows = []
    for arm, key in (("E168_rerun", "E168"), (NAME, C.NAME)):
        mu, p, half = r[key]
        o = te[RT.KEYS].copy().reset_index(drop=True)
        o["mode"], o["arm"], o["seed"], o["mu"], o["p"], o["half"] = mode, arm, 0, mu, p, half
        o["cfg"] = f"{r['cfg']}|cal={r['cal_E168']}" + ("" if arm == "E168_rerun" else f"|aug={T.setting_name(SETTING)}|seeds=17901-17905|cal={'/'.join(r['cal_seeds'])}")
        rows.append(o)
    return {"rows": pd.concat(rows, ignore_index=True), "job": RT.job_id(survey, lead, mode), "seconds": round(time.time() - t0, 1)}


def _lead3_frame(rows3):
    e8 = pd.read_csv(E.OUT / "all_rows_l3_8.csv", float_precision="round_trip")
    e8 = e8[(e8["lead"] == 3) & (e8["mode"] == "main")]
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    x = G[G["lead"] == 3].merge(e8[RT.KEYS + ["mu", "p", "half"]].rename(columns={"mu": "mu_E168", "p": "E168", "half": "half_E168"}), on=RT.KEYS)
    for arm in (NAME, "E168_rerun"):
        x = x.merge(rows3[rows3["arm"] == arm][RT.KEYS + ["mu", "p", "half"]].rename(columns={"mu": f"mu_{arm}", "p": arm, "half": f"half_{arm}"}), on=RT.KEYS)
    assert len(x) == 72
    return x


def evaluate(log=None) -> dict:
    log = log or K.RunLog(OUT / "run_log.jsonl", fresh=False)
    Al = pd.read_csv(OUT / "all_rows.csv", float_precision="round_trip")
    rows3 = pd.read_csv(OUT / "lead3_rows.csv", float_precision="round_trip")
    v = pd.read_csv(K.D / "e181" / "out" / "variant_rows.csv", float_precision="round_trip")
    v = v[v["variant"] == T.setting_name(SETTING)].groupby(RT.KEYS)[["p"]].mean().reset_index()
    c = Al[(Al["arm"] == NAME) & (Al["mode"] == "main")].merge(v, on=RT.KEYS, suffixes=("", "_e181"))
    e8 = pd.read_csv(E.OUT / "all_rows.csv", float_precision="round_trip")
    d8 = Al[Al["arm"] == "E168_rerun"].merge(e8, on=RT.KEYS + ["mode"], suffixes=("", "_e168"))
    checks = {"same_as_e181_variant": {"rows": int(len(c)), "max_abs_diff_p": float(np.max(np.abs(c["p"] - c["p_e181"])))},
              "e168_rerun_leads12": {"rows": int(len(d8)), "max_abs_diff_p": float(np.max(np.abs(d8["p"] - d8["p_e168"])))}}
    dec = lambda acc, res: ("E184 better than E168 on the strict rule" if all(acc.values()) else "E184 not better than E168 on the strict rule (reported, not a deployment condition)")
    res = RT.evaluate(log, OUT, name=NAME, protocol="docs/e184/PROTOCOL.md", primary_seed=0, extra_outs=[], decision_text=dec)
    keep = ("accuracy", "balanced_accuracy", "high_precision", "high_recall", "low_recall", "f1", "macro_f1", "auc", "brier", "calibration_slope", "confusion")
    per_lead = {}
    for Ld in LEADS:
        if Ld == 3:
            x = _lead3_frame(rows3)
            checks["e168_rerun_lead3_max_abs_diff_p"] = float(np.max(np.abs(x["E168"] - x["E168_rerun"])))
        else:
            x = RT._frame(Al, Ld, 0, [NAME])
        rng = np.random.default_rng(184)
        met = {a: {k: v_ for k, v_ in RT._metrics(x, a, rng).items() if k in keep} for a in ("PERS", "E168", NAME)}
        vp = E.E7.diff_ci(x, NAME, "PERS", "q_true", np.random.default_rng(184), n=2000)
        v8 = E.E7.diff_ci(x, NAME, "E168", "q_true", np.random.default_rng(184), n=2000)
        cA, cB = (x[NAME] >= .5) == (x["y_high"] == 1), (x["E168"] >= .5) == (x["y_high"] == 1)
        bb, cc = int((cA & ~cB).sum()), int((~cA & cB).sum())
        per_lead[Ld] = {"metrics": met,
                        "brier_minus_persistence": {"diff": round(vp["diff"], 4), "ci95": [round(z, 4) for z in vp["ci95"]]},
                        "brier_minus_E168": {"diff": round(v8["diff"], 4), "ci95": [round(z, 4) for z in v8["ci95"]]},
                        "mcnemar_vs_E168": {"E184_only_right": bb, "E168_only_right": cc,
                                            "p": round(float(binomtest(bb, bb + cc, .5).pvalue), 4) if bb + cc else 1.0}}
    owner = {f"lead{Ld}_accuracy_at_least_75": per_lead[Ld]["metrics"][NAME]["accuracy"] >= 0.75 for Ld in LEADS}
    owner |= {f"lead{Ld}_beats_persistence_brier_ci": per_lead[Ld]["brier_minus_persistence"]["ci95"][1] < 0 for Ld in LEADS}
    owner["leakage_below_1e-9"] = res["leakage_max_abs_change"] < 1e-9
    res |= {"checks": checks, "served_leads": per_lead, "deployment_rule": owner, "deployable": all(owner.values()),
            "model_id": MODEL_ID, "setting": T.setting_name(SETTING)}
    K.dump_json(res, OUT / "results.json")
    log("deployment_rule", deployable=res["deployable"], rule=owner, checks=checks)
    K.write_hashes([OUT / n for n in ("all_rows.csv", "lead3_rows.csv", "results.json")] + ([SEAL] if SEAL.exists() else []) + [OUT / "run_log.jsonl"], OUT / "hashes.json")
    for Ld in LEADS:
        m = per_lead[Ld]["metrics"]
        print(f"Lead {Ld}:", {a: (m[a]["accuracy"], m[a]["balanced_accuracy"], m[a]["high_recall"], m[a]["brier"]) for a in m},
              "vsPERS", per_lead[Ld]["brier_minus_persistence"], "vsE168", per_lead[Ld]["brier_minus_E168"], per_lead[Ld]["mcnemar_vs_E168"])
    print("deployment rule:", owner, "-> deployable:", res["deployable"])
    print("checks:", checks)
    return res


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl", fresh=not (OUT / "run_log.jsonl").exists())
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL), setting=T.setting_name(SETTING), seeds=T.SEEDS)
    H, L, S_P = K.pipeline_inputs()
    jobs = [(s, l, "main") for s in RT.SURVEYS for l in LEADS] + [(s, 1, m) for s in RT.SURVEYS for m in RT.CONTROLS]
    jobs.sort(key=lambda j: RT.SURVEYS.index(j[0]))
    t0 = time.time()
    R = Parallel(n_jobs=RT.N_JOBS, verbose=5)(delayed(job)(s, l, H, L, S_P, m) for s, l, m in jobs)
    A = pd.concat([r["rows"] for r in R], ignore_index=True)
    A[A["lead"] != 3].to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    A[A["lead"] == 3].to_csv(OUT / "lead3_rows.csv", index=False, lineterminator="\n")
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
    te = te.reset_index(drop=True)
    r = C.fixed(tr, te, AN, T.SEEDS, f"ENNS2022|L{lead}|seal", setting=SETTING)
    pct = lambda z: 100 / (1 + np.exp(-np.asarray(z, float)))
    o = te[[c for c in ("key", "province", "region", "island", "lead", "gap_q") if c in te]].copy()
    for name, (mu, p, half) in (("E168", r["E168"]), (NAME, r[C.NAME])):
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
           "model": f"{MODEL_ID}: E168's selection + synthetic rows balanced 50/50 ({T.setting_name(SETTING)}), mean of seeds 17901-17905",
           "rule": "HIGH = p_high >= 0.5; score only on HFIAS moderate_or_severe provincial rows once public and verified comparable; no re-fitting",
           "e168_seal_check": check, "forecasts": F.round(6).to_dict("records")}
    SEAL.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8", newline="\n")
    log("sealed", sha256=K.sha256(SEAL), rows=len(F), e168_check=check)
    print("sealed", len(F), "rows; sha256", K.sha256(SEAL), "; E168 check", check)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"run": run, "report": evaluate, "seal": seal}.get(cmd, lambda: sys.exit("usage: python -m app.e184.candidate run | report | seal"))()

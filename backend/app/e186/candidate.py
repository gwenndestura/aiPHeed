"""
E186 (docs/e186/PROTOCOL.md): E184's procedure (E168 selection + synthetic rows 50/50, mean of seeds 17901-17905) with
two more feature sets in Stage A's menu: GOV+local and FULL+local, where local = provincial farmgate palay, wholesale rice
and NASA rainfall columns from data/e152/out/local_panel.parquet. Leads 1-3, controls, ENNS 2022 seal.

    python -m app.e186.candidate run    -> data/e186/out/all_rows.csv, results.json
    python -m app.e186.candidate seal   -> data/e186/out/sealed_enns2022.json
"""
from __future__ import annotations

import contextlib
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
from app.e182 import candidate as C182
from app.e184 import candidate as C184

warnings.filterwarnings("ignore")
OUT = K.D / "e186" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e186" / "PROTOCOL.md"
LOCAL = ["l_fg_yoy", "l_fg_rel", "r_fg_yoy", "l_rice_yoy", "l_rice_rel", "r_rice_yoy", "l_terms", "l_rain3", "l_rain6", "r_rain3"]
NAME = "E186"
LEADS = (1, 2, 3)
SEAL = OUT / "sealed_enns2022.json"


@contextlib.contextmanager
def local_menu():
    """E168's feature-set menu plus GOV+local and FULL+local; the local columns also join the shuffled-trigger set.
    Applied inside each worker process for the duration of a job."""
    fs = {**E.FS, "GOV+local": E.FS["GOV"] + LOCAL, "FULL+local": E.FS["FULL"] + LOCAL}
    with K.patched(E, "FS", fs), K.patched(E, "TRIG", list(E.TRIG) + LOCAL):
        yield


def job(survey, lead, H, L, S_P, mode):
    t0 = time.time()
    with local_menu():
        tr, te, AN = RT.build(survey, lead, H, L, S_P, mode)
        stream = RT.job_id(survey, lead, "main" if mode in ("main", "corrupt") else mode)
        r = C182.fixed(tr, te, AN, T.SEEDS, stream, setting=C184.SETTING)
    mu, p, half = r[C182.NAME]
    o = te[RT.KEYS].copy().reset_index(drop=True)
    o["mode"], o["arm"], o["seed"], o["mu"], o["p"], o["half"] = mode, NAME, 0, mu, p, half
    o["cfg"] = f"{r['cfg']}|aug={T.setting_name(C184.SETTING)}|seeds=17901-17905"
    o["feature_set"] = r["cfg"].split("|")[1]
    return {"rows": o, "job": RT.job_id(survey, lead, mode), "seconds": round(time.time() - t0, 1)}


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
                      (NAME, rows[(rows["lead"] == Ld) & (rows["mode"] == "main")])):
        x = x.merge(src[RT.KEYS + ["mu", "p", "half"]].rename(columns={"mu": f"mu_{name}", "p": name, "half": f"half_{name}"}), on=RT.KEYS)
    assert len(x) == 72, (Ld, len(x))
    return x


def evaluate(log=None) -> dict:
    log = log or K.RunLog(OUT / "run_log.jsonl", fresh=False)
    rows = pd.read_csv(OUT / "all_rows.csv", float_precision="round_trip")
    keep = ("accuracy", "balanced_accuracy", "high_precision", "high_recall", "low_recall", "f1", "macro_f1", "auc", "brier", "calibration_slope", "confusion")
    res = {"protocol": "docs/e186/PROTOCOL.md", "leads": {}}
    for Ld in LEADS:
        x = _frame(Ld, rows)
        rng = np.random.default_rng(186)
        met = {a: {k: v for k, v in RT._metrics(x, a, rng).items() if k in keep} for a in ("PERS", "E168", "E184", NAME)}
        ci = {b: E.E7.diff_ci(x, NAME, b, "q_true", np.random.default_rng(186), n=2000) for b in ("PERS", "E168", "E184")}
        cA, cB = (x[NAME] >= .5) == (x["y_high"] == 1), (x["E184"] >= .5) == (x["y_high"] == 1)
        bb, cc = int((cA & ~cB).sum()), int((~cA & cB).sum())
        res["leads"][Ld] = {"metrics": met, **{f"brier_minus_{b}": {"diff": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]} for b, v in ci.items()},
                            "mcnemar_vs_E184": {"E186_only_right": bb, "E184_only_right": cc, "p": round(float(binomtest(bb, bb + cc, .5).pvalue), 4) if bb + cc else 1.0}}
    x1 = _frame(1, rows)
    for m in RT.CONTROLS:
        c = rows[(rows["lead"] == 1) & (rows["mode"] == m)][RT.KEYS + ["mu", "p"]].rename(columns={"mu": f"mu_{m}", "p": m})
        x1 = x1.merge(c, on=RT.KEYS)
    x1["SHUF"] = x1[["shuf1", "shuf2", "shuf3"]].mean(axis=1)
    v = E.E7.diff_ci(x1, NAME, "SHUF", "q_true", np.random.default_rng(186), n=2000)
    res["shuffle"] = {"brier_shuffled": round(float(np.mean((x1["SHUF"] - x1["q_true"]) ** 2)), 4),
                      "accuracy_shuffled": round(float(((x1["SHUF"] >= .5) == (x1["y_high"] == 1)).mean()), 3),
                      "E186_minus_shuffled": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]}
    res["leakage_max_abs_change"] = float(np.max(np.abs(x1[f"mu_{NAME}"] - x1["mu_corrupt"])))
    main = rows[rows["mode"] == "main"].drop_duplicates(["survey", "lead"])
    res["feature_sets_chosen"] = {f"{r.survey}|L{r.lead}": r.feature_set for r in main.itertuples()}
    res["share_local_chosen"] = round(float(main["feature_set"].str.endswith("+local").mean()), 3)
    L = res["leads"]
    better = {f"lead{Ld}_brier_ci_vs_E184_below_0": L[Ld]["brier_minus_E184"]["ci95"][1] < 0 for Ld in LEADS}
    better |= {f"lead{Ld}_accuracy_at_least_E184": L[Ld]["metrics"][NAME]["accuracy"] >= L[Ld]["metrics"]["E184"]["accuracy"] for Ld in LEADS}
    owner = {f"lead{Ld}_accuracy_at_least_75": L[Ld]["metrics"][NAME]["accuracy"] >= 0.75 for Ld in LEADS}
    owner |= {f"lead{Ld}_beats_persistence": L[Ld]["brier_minus_PERS"]["ci95"][1] < 0 for Ld in LEADS}
    owner["leakage_below_1e-9"] = res["leakage_max_abs_change"] < 1e-9
    res |= {"better_than_E184_rule": better, "owner_rule": owner, "reaches_80": {Ld: L[Ld]["metrics"][NAME]["accuracy"] >= 0.80 for Ld in LEADS},
            "beats_shuffled": res["shuffle"]["ci95"][1] < 0,
            "decision": ("E186 BETTER THAN E184" if all(better.values()) and all(owner.values())
                         else "THE PROVINCIAL LOCAL DATA DID NOT IMPROVE E184 (E184 stays the candidate)")}
    K.dump_json(res, OUT / "results.json")
    log("evaluated", decision=res["decision"], feature_sets=res["feature_sets_chosen"])
    K.write_hashes([OUT / n for n in ("all_rows.csv", "results.json")] + ([SEAL] if SEAL.exists() else []) + [OUT / "run_log.jsonl"], OUT / "hashes.json")
    for Ld in LEADS:
        m = L[Ld]["metrics"]
        print(f"Lead {Ld}:", {a: (m[a]["accuracy"], m[a]["balanced_accuracy"], m[a]["high_recall"], m[a]["brier"]) for a in m},
              "vsE184", L[Ld]["brier_minus_E184"], L[Ld]["mcnemar_vs_E184"])
    print("feature sets:", res["feature_sets_chosen"]); print("leakage", res["leakage_max_abs_change"], "shuffle", res["shuffle"])
    print("reaches 80:", res["reaches_80"]); print(res["decision"])
    return res


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl", fresh=not (OUT / "run_log.jsonl").exists())
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL), local=LOCAL, setting=T.setting_name(C184.SETTING), seeds=T.SEEDS)
    H, L, S_P = K.pipeline_inputs()
    jobs = [(s, l, "main") for s in RT.SURVEYS for l in LEADS] + [(s, 1, m) for s in RT.SURVEYS for m in RT.CONTROLS]
    jobs.sort(key=lambda j: RT.SURVEYS.index(j[0]))
    t0 = time.time()
    R = Parallel(n_jobs=RT.N_JOBS, verbose=5)(delayed(job)(s, l, H, L, S_P, m) for s, l, m in jobs)
    pd.concat([r["rows"] for r in R], ignore_index=True).to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    for r in R:
        log("job", job=r["job"], seconds=r["seconds"])
    log("fitted", seconds=round(time.time() - t0, 1))
    evaluate(log)


def _seal_lead(lead, H, L, S_P):
    from app.e168 import enns2022_seal as S22

    def stop(tr, te, AN, ablate=False):
        raise RT._Captured(tr, te, AN)

    with local_menu(), K.patched(S22, "run_proc", stop):
        try:
            S22.task(lead, H, L, S_P)
            raise RuntimeError("enns2022_seal.task did not reach run_proc")
        except RT._Captured as c_:
            tr, te, AN = c_.args
    with local_menu():
        te = te.reset_index(drop=True)
        r = C182.fixed(tr, te, AN, T.SEEDS, f"ENNS2022|L{lead}|seal", setting=C184.SETTING)
    pct = lambda z: 100 / (1 + np.exp(-np.asarray(z, float)))
    o = te[[c for c in ("key", "province", "region", "island", "lead", "gap_q") if c in te]].copy()
    for name, (mu, p, half) in (("E168_menu_local", r["E168"]), (NAME, r[C182.NAME])):
        o[f"{name}_score"], o[f"{name}_p_high"] = pct(mu).round(2), np.round(p, 4)
        o[f"{name}_class"], o[f"mu_{name}"] = np.where(np.asarray(p) >= .5, "HIGH", "LOW"), mu
    o["feature_set"] = r["cfg"].split("|")[1]
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
    doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "target": old["target"], "origin": old["origin"],
           "model": "E186: E184 + provincial local data in the feature-set menu (docs/e186/PROTOCOL.md)",
           "rule": "HIGH = p_high >= 0.5; score only on HFIAS moderate_or_severe provincial rows once public and verified comparable; no re-fitting",
           "forecasts": F.round(6).to_dict("records")}
    SEAL.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8", newline="\n")
    log("sealed", sha256=K.sha256(SEAL), rows=len(F))
    print("sealed", len(F), "rows; sha256", K.sha256(SEAL))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"run": run, "report": evaluate, "seal": seal}.get(cmd, lambda: sys.exit("usage: python -m app.e186.candidate run | report | seal"))()

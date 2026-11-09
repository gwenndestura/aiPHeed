"""
E180 (docs/e180/PROTOCOL.md): E179 averaged over generator seeds 17901-17905, and sealed ENNS 2022 forecasts.

    python -m app.e180.ensemble controls   E179's Lead-1 controls at all five seeds -> data/e180/out/controls_*.csv
    python -m app.e180.ensemble eval       E180 = seed mean of E179 -> data/e180/out/all_rows.csv, results.json
    python -m app.e180.ensemble seal       E168 / E179 / E180 forecasts for ENNS 2022 -> data/e180/out/sealed_enns2022.json
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

from app.e178 import common as K
from app.e178 import retrain as RT
from app.e179 import tuned as T

warnings.filterwarnings("ignore")
ROOT = K.D / "e180"
OUT = ROOT / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e180" / "PROTOCOL.md"
ENS_SEED = 18000                      # label of the seed-mean rows
SEAL = OUT / "sealed_enns2022.json"
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def _log(fresh=False):
    OUT.mkdir(parents=True, exist_ok=True)
    return K.RunLog(OUT / "run_log.jsonl", fresh=fresh and not (OUT / "run_log.jsonl").exists())


def controls() -> None:
    log = _log(fresh=True)
    RT._check_inputs(log)
    log("controls_start", protocol_sha256=K.sha256(PROTOCOL), seeds=T.SEEDS)
    H, L, S_P = K.pipeline_inputs()
    jobs = [(s, m) for s in RT.SURVEYS for m in RT.CONTROLS]
    t0 = time.time()
    R = Parallel(n_jobs=RT.N_JOBS, verbose=5)(delayed(T.task)(s, 1, H, L, S_P, m, T.SEEDS, False,
                                                               RT.job_id(s, 1, "main") if m == "corrupt" else None) for s, m in jobs)
    pd.concat([r["rows"] for r in R], ignore_index=True).to_csv(OUT / "controls_rows.csv", index=False, lineterminator="\n")
    pd.concat([r["sel"] for r in R], ignore_index=True).to_csv(OUT / "controls_selection.csv", index=False, lineterminator="\n")
    for r in R:
        log("job", job=r["job"], seconds=r["seconds"], n_train=r["n_train"])
    log("controls_done", seconds=round(time.time() - t0, 1))


def ensemble(df: pd.DataFrame) -> pd.DataFrame:
    """Mean of E179's mu, p and half over the generator seeds, per outer row and mode."""
    d = df[(df["arm"] == "E179") & df["seed"].isin(T.SEEDS)]
    g = d.groupby(RT.KEYS + ["mode"])
    out = g[["mu", "p", "half"]].mean().reset_index()
    out["n_seeds"] = g.size().values
    out["arm"], out["seed"] = "E180", ENS_SEED
    out["cfg"] = "E180 = mean of E179 over seeds " + "-".join(str(s) for s in (T.SEEDS[0], T.SEEDS[-1]))
    return out


def evaluate() -> dict:
    log = _log()
    main = pd.read_csv(T.OUT / "all_rows.csv", float_precision="round_trip")
    main = main[main["mode"] == "main"]
    ctrl = pd.read_csv(OUT / "controls_rows.csv", float_precision="round_trip")
    ens = pd.concat([ensemble(main), ensemble(ctrl)], ignore_index=True)
    assert (ens["n_seeds"] == len(T.SEEDS)).all(), "every row must average all five seeds"
    e179 = main[(main["arm"] == "E179") & (main["seed"] == T.PRIMARY)].assign(seed=ENS_SEED)       # descriptive: E179 seed 17901
    cols = RT.KEYS + ["mode", "arm", "seed", "mu", "p", "half", "cfg"]
    pd.concat([ens[cols + ["n_seeds"]], e179[cols]], ignore_index=True).to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    dec = lambda acc, res: ("E180 BETTER THAN E168 on the pre-registered rule (candidate only; not promoted; the owner decides)" if all(acc.values())
                            else "E180: THE SEED ENSEMBLE DID NOT IMPROVE THE MODEL ON THE PRE-REGISTERED RULE (E168 stays in production)")
    extra = [OUT / n for n in ("controls_rows.csv", "controls_selection.csv")] + ([SEAL] if SEAL.exists() else [])
    return RT.evaluate(log, OUT, name="E180", protocol="docs/e180/PROTOCOL.md", primary_seed=ENS_SEED, extra_outs=extra, decision_text=dec)


# ------------------------------------------------------------------------------------------------- ENNS 2022 seal
def _seal_lead(lead: int, H, L, S_P) -> dict:
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
    if "survey" not in te:
        te = te.assign(survey="ENNS2022")
    rows, sel, _, _ = T.run_proc_tuned(tr, te, AN, T.SEEDS, f"ENNS2022|L{lead}|seal")
    by = {(r["arm"].iloc[0], int(r["seed"].iloc[0])): r for r in rows}
    base = te[[c for c in ("key", "province", "region", "island", "lead", "gap_q") if c in te]].copy()

    def put(name, mu, p, half):
        base[f"{name}_score"], base[f"{name}_p_high"] = pct(mu).round(2), np.round(p, 4)
        base[f"{name}_low90"], base[f"{name}_high90"] = pct(mu - half).round(2), pct(mu + half).round(2)
        base[f"{name}_class"] = np.where(np.asarray(p) >= .5, "HIGH", "LOW")
        base[f"mu_{name}"] = mu

    r168 = by[("E168_rerun", T.PRIMARY)]
    put("E168", r168["mu"].values, r168["p"].values, r168["half"].values)
    r179 = by[("E179", T.PRIMARY)]
    put("E179", r179["mu"].values, r179["p"].values, r179["half"].values)
    s = [by[("E179", sd)] for sd in T.SEEDS]
    put("E180", np.mean([x["mu"].values for x in s], axis=0), np.mean([x["p"].values for x in s], axis=0), np.mean([x["half"].values for x in s], axis=0))
    base["E179_config"] = r179["cfg"].values
    return {"rows": base, "sel": sel}


def seal() -> None:
    log = _log()
    if SEAL.exists():
        raise SystemExit("already sealed: " + K.sha256(SEAL))
    RT._check_inputs(log)
    H, L, S_P = K.pipeline_inputs()
    t0 = time.time()
    R = Parallel(n_jobs=2)(delayed(_seal_lead)(l, H, L, S_P) for l in (1, 2))
    F = pd.concat([r["rows"] for r in R], ignore_index=True)
    old = json.loads((K.D / "e168" / "out" / "sealed_enns2022.json").read_text())
    o = pd.DataFrame(old["forecasts"]).merge(F[["key", "lead", "mu_E168"]], on=["key", "lead"], suffixes=("_sealed", "_rerun"))
    check = {"rows": int(len(o)), "of": len(old["forecasts"]), "max_abs_diff_mu": float(np.max(np.abs(o["mu_E168_sealed"] - o["mu_E168_rerun"])))}
    doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "target": old["target"], "origin": old["origin"],
           "models": {"E168": "Stage A of E179 without augmentation (= E168's procedure); must match data/e168/out/sealed_enns2022.json",
                      "E179": "E179 (docs/e179/PROTOCOL.md), generator seed 17901",
                      "E180": "mean of E179 over generator seeds 17901-17905 (docs/e180/PROTOCOL.md)"},
           "rule": "HIGH = p_high >= 0.5; score only on HFIAS moderate_or_severe provincial rows once public and verified comparable; no re-fitting",
           "e168_seal_check": check, "e179_selection": pd.concat([r["sel"] for r in R]).to_dict("records"),
           "forecasts": F.round(6).to_dict("records")}
    SEAL.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8", newline="\n")
    sha = K.sha256(SEAL)
    log("sealed", sha256=sha, rows=len(F), e168_check=check, seconds=round(time.time() - t0, 1))
    print("sealed", len(F), "rows; sha256", sha, "; E168 check", check)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"controls": controls, "eval": evaluate, "seal": seal}.get(cmd, lambda: sys.exit("usage: python -m app.e180.ensemble controls | eval | seal"))()

"""
E196 seal (docs/e196/CONFIRMATION_PROTOCOL.md): E196's forecasts for the ENNS 2022 provincial targets, made with the
same frames as E184's seal (app.e168.enns2022_seal up to run_proc), so they can be scored once when the labels are public.
E196 Lead 1 = mean of E194's Lead-1 and Lead-2 forecasts; E196 Lead 2 = E194's Lead-2 forecast (rules chosen on
training rows in E196). E194 = mean of the top-5 Stage-A configurations x 20 synthetic draws (E184's augmentation).

    python -m app.e196.seal          (refuses to overwrite an existing seal)
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
from sklearn.model_selection import GroupKFold

from app.e178 import common as K
from app.e178 import retrain as RT
from app.e191 import run as R
from app.e194 import run as E194

warnings.filterwarnings("ignore")
OUT = K.D / "e196" / "out"
SEAL = OUT / "sealed_enns2022.json"
E184_SEAL = K.D / "e184" / "out" / "sealed_enns2022.json"
pct = lambda z: 100 / (1 + np.exp(-np.asarray(z, float)))


def frames(lead):
    from app.e168 import enns2022_seal as S22
    H, L, S_P = K.pipeline_inputs()

    def stop(tr, te, AN, ablate=False):
        raise RT._Captured(tr, te, AN)

    with K.patched(S22, "run_proc", stop):
        try:
            S22.task(lead, H, L, S_P)
            raise RuntimeError("enns2022_seal.task did not reach run_proc")
        except RT._Captured as c_:
            tr, te, AN = c_.args
    return tr.reset_index(drop=True), te.reset_index(drop=True), AN


def part(lead, rank):
    t0 = time.time()
    tr, te, AN = frames(lead)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    sse, _, cfg = E194.stage_a_ranked(tr, AN, folds)[rank - 1]
    stream = f"ENNS2022|L{lead}|seal"                      # E184's seal stream: rank 1 x draws 17901-17905 = E184
    runs = [R.run_cfg(tr, te, AN, folds, cfg, R.spec_of("e184"), s, stream)[0] for s in E194.SEEDS]
    o = te[[c for c in ("key", "province", "region", "island", "lead", "gap_q") if c in te]].copy()
    for k, nm in enumerate(("mu", "p", "half")):
        o[nm] = np.mean([np.asarray(r[k], float) for r in runs], axis=0)
        o[f"{nm}_first5"] = np.mean([np.asarray(r[k], float) for r in runs[:5]], axis=0)
    o["rank"], o["cfg"], o["inner_sse"], o["n_train"] = rank, "|".join(map(str, cfg)), sse, len(tr)
    return o, round(time.time() - t0, 1)


def main():
    if SEAL.exists():
        raise SystemExit("already sealed: " + K.sha256(SEAL))
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "seal_log.jsonl", fresh=not (OUT / "seal_log.jsonl").exists())
    log("seal_start", protocol_sha256=K.sha256(K.BACKEND_DIR.parent / "docs" / "e196" / "CONFIRMATION_PROTOCOL.md"))
    res = Parallel(n_jobs=R.N_JOBS, verbose=5)(delayed(part)(l, r) for l in (1, 2) for r in range(1, E194.TOPK + 1))
    P = pd.concat([r[0] for r in res], ignore_index=True)
    P.to_csv(OUT / "seal_parts.csv", index=False, lineterminator="\n")
    keys = ["key", "lead"]
    E194f = P.groupby(keys)[["mu", "p", "half"]].mean().reset_index()
    # reproduction: rank-1, first 5 draws = E184's sealed probabilities
    old = pd.DataFrame(json.loads(E184_SEAL.read_text())["forecasts"])
    r1 = P[P["rank"] == 1][keys + ["p_first5"]].merge(old[keys + ["E184_p_high"]], on=keys)
    check = {"rows": int(len(r1)), "of": int(len(old)), "max_abs_diff_p_vs_sealed_E184_4dp": float(np.max(np.abs(r1["p_first5"].round(4) - r1["E184_p_high"])))}
    W = {nm: E194f.pivot_table(index="key", columns="lead", values=nm) for nm in ("mu", "p", "half")}
    base = P[P["rank"] == 1].drop_duplicates(keys)[["key", "province", "region", "island", "lead", "gap_q"]]
    rows = []
    for _, b in base.iterrows():
        k, L = b["key"], int(b["lead"])
        ls = [1, 2] if L == 1 else [2]                         # E196 rules (chosen on training rows): S2 at Lead 1, S1 at Lead 2
        mu, p, half = (float(np.mean([W[nm].at[k, l] for l in ls])) for nm in ("mu", "p", "half"))
        e = E194f[(E194f["key"] == k) & (E194f["lead"] == L)].iloc[0]
        rows.append({**b.to_dict(), "E196_score": round(float(pct(mu)), 2), "E196_p_high": round(p, 4),
                     "E196_low90": round(float(pct(mu - half)), 2), "E196_high90": round(float(pct(mu + half)), 2),
                     "E196_class": "HIGH" if p >= .5 else "LOW", "mu_E196": round(mu, 6), "E196_averages_leads": ls,
                     "E194_p_high": round(float(e["p"]), 4)})
    F = pd.DataFrame(rows).merge(old[keys + ["E184_p_high", "E184_class"]], on=keys, how="left")
    doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "target": json.loads(E184_SEAL.read_text())["target"],
           "origin": json.loads(E184_SEAL.read_text())["origin"],
           "model": "E196: E194 (top-5 Stage-A configurations x 20 E184 synthetic draws) with lagged averaging chosen on training rows "
                    "(Lead 1 = mean of E194 Leads 1-2; Lead 2 = E194 Lead 2)",
           "rule": "HIGH = p_high >= 0.5; scored once, per docs/e196/CONFIRMATION_PROTOCOL.md, on HFIAS moderate_or_severe provincial rows "
                   "once public and verified comparable; no re-fitting",
           "e184_seal_reproduction": check, "e184_seal_sha256": K.sha256(E184_SEAL),
           "configs": P.groupby(["lead", "rank"])["cfg"].first().reset_index().to_dict("records"),
           "forecasts": F.to_dict("records")}
    SEAL.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8", newline="\n")
    h = K.sha256(SEAL)
    log("sealed", sha256=h, rows=len(F), e184_check=check, seconds=[r[1] for r in res])
    print("sealed", len(F), "rows; sha256", h)
    print("E184 reproduction:", check)
    print(F.groupby("lead")[["E184_class", "E196_class"]].apply(lambda d: {"E184_HIGH": int((d["E184_class"] == "HIGH").sum()), "E196_HIGH": int((d["E196_class"] == "HIGH").sum()),
                                                                           "class_agree": int((d["E184_class"] == d["E196_class"]).sum()), "n": len(d)}).to_dict())


if __name__ == "__main__":
    {"": main}.get("" if len(sys.argv) < 2 else sys.argv[1], lambda: sys.exit("usage: python -m app.e196.seal"))()

"""
E183 checks (docs/e183/DESIGN.md).

    python -m app.e183.checks equiv        E168's 18 jobs through the changed lgbm_only.task = stored E168 rows
    python -m app.e183.checks production   serve._forecast (changed) at the production cut-off = production artifact
    python -m app.e183.checks s2           scenario S2 on the live Lead-1 rows, before vs after the fix
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.e168 import robust as RB
from app.e178 import common as K
from app.e178 import retrain as RT

OUT = K.D / "e183" / "out"
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def equiv() -> None:
    from app.e168 import lgbm_only as E
    OUT.mkdir(parents=True, exist_ok=True)
    H, L, S_P = K.pipeline_inputs()
    jobs = [(s, l, "main") for s, l in RT.MAIN] + [(s, 1, m) for s in RT.SURVEYS for m in RT.CONTROLS]
    R = Parallel(n_jobs=RT.N_JOBS)(delayed(RT.task_aug)(s, l, H, L, S_P, m, 17801, []) for s, l, m in jobs)
    got = pd.concat([r["rows"] for r in R], ignore_index=True)
    ref = pd.read_csv(E.OUT / "all_rows.csv", float_precision="round_trip")
    x = ref.merge(got, on=RT.KEYS + ["mode"], suffixes=("_e168", "_now"))
    doc = {"rows_compared": int(len(x)), "rows_expected": int(len(ref)), "same_configuration": bool((x["cfg_e168"] == x["cfg_now"]).all()),
           "max_abs_diff_selected": {c: float(np.max(np.abs(x[f"{c}_e168"] - x[f"{c}_now"]))) for c in ("mu", "p", "half")}}
    K.dump_json(doc, OUT / "equivalence.json")
    print(doc)


def production() -> None:
    prod = K.production_issue()
    if not K.at_production_cutoff(prod):
        sys.exit(K.rerun_at_cutoff("app.e183.checks", ["production"], prod))
    OUT.mkdir(parents=True, exist_ok=True)
    from app.e168 import serve as SV

    def lead(l):
        with K.sun_standin():
            return SV._forecast(l, prod["issue"])
    rows = [r for rs in Parallel(n_jobs=3)(delayed(lead)(l) for l in (1, 2, 3)) for r in rs]
    live = {(r["province"], r["lead"]): r for r in prod["live"]["provinces"]}
    bad = [f"{(r['province'], r['lead'])} {f}" for r in rows for f in ("target_quarter", "score_pct", "range90_pct", "p_high", "risk_class", "config")
           if live[(r["province"], r["lead"])][f] != r[f]]
    doc = {"rows": len(rows), "equal_to_production": not bad, "mismatches": bad,
           "inputs_filled": {f"{r['province']}|L{r['lead']}": r["inputs_filled"] for r in rows},
           "data_complete_all": all(r["data_complete"] for r in rows)}
    K.dump_json(doc, OUT / "production_check.json")
    print(doc)


def s2() -> None:
    """S2 masks (E178 Part A, seeds 17811-17813) and 'all triggers missing' on the live Lead-1 rows: masked inputs passed
    to the model as missing (before E183) vs filled by fill_unseen_missing (after)."""
    prod = K.production_issue()
    if not K.at_production_cutoff(prod):
        sys.exit(K.rerun_at_cutoff("app.e183.checks", ["s2"], prod))
    OUT.mkdir(parents=True, exist_ok=True)
    from app.e168 import lgbm_only as E
    from app.e168 import serve as SV
    from app.e178 import scenarios as S
    store = {}
    orig = E.run_proc

    def spy(tr, te, AN, ablate=False):
        te = te.reset_index(drop=True)
        V, _ = S.build_variants(tr, te)
        V = [v for v in V if v["scenario_id"] in ("S0", "S2")]
        blocks, meta = [], []
        for v in V:
            after, filled = RB.fill_unseen_missing(tr, v["te"])
            blocks += [v["te"], after]
            meta += [(v, "before", [[] for _ in range(len(te))]), (v, "after", filled)]
        te_all = pd.concat(blocks, ignore_index=True)
        AN_all = {a: (atr, np.tile(np.asarray(ate, float), len(blocks))) for a, (atr, ate) in AN.items()}
        P, chosen, tag, *_ = orig(tr, te_all, AN_all, ablate)
        store.update(P=P[chosen], tag=tag, meta=meta, n=len(te), te=te)
        raise RT._Captured()

    with K.sun_standin(), K.patched(E, "run_proc", spy):
        try:
            SV._forecast(1, prod["issue"])
        except RT._Captured:
            pass
    mu, p, half = store["P"]
    n, rows = store["n"], []
    for b, (v, when, filled) in enumerate(store["meta"]):
        used = RB.used_by(store["tag"], filled)
        for k in range(n):
            j = b * n + k
            rows.append({"province": store["te"]["province"].iloc[k], "variant": v["variant"], "group": v["group"], "masked_share": v["param"],
                         "when": when, "p_high": float(p[j]), "score_pct": round(float(pct(mu[j])), 2),
                         "range90_width_pts": round(float(pct(mu[j] + half[j]) - pct(mu[j] - half[j])), 2),
                         "inputs_filled_used": len(used[k]), "is_synthetic": v["scenario_id"] != "S0", "scenario_id": v["scenario_id"]})
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "s2_before_after.csv", index=False, lineterminator="\n")
    s0 = d[d["variant"] == "real inputs"].groupby(["province", "when"])["p_high"].first().unstack()
    summ = (d[d["scenario_id"] == "S2"].groupby(["group", "masked_share", "province", "when"])
            .agg(p_mean=("p_high", "mean"), score_mean=("score_pct", "mean"), flagged=("inputs_filled_used", lambda s: float((s > 0).mean())))
            .reset_index())
    summ["p_real"] = summ["province"].map(s0["before"])
    K.dump_json({"label": K.LABEL, "config": store["tag"], "s0_before_equals_after": bool(np.allclose(s0["before"], s0["after"])),
                 "rows": summ.round(4).to_dict("records")}, OUT / "s2_summary.json")
    print(summ.pivot_table(index=["group", "masked_share", "province"], columns="when", values=["p_mean", "score_mean"]).round(4).to_string())


if __name__ == "__main__":
    {"equiv": equiv, "production": production, "s2": s2}[sys.argv[1]]()

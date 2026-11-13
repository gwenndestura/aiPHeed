"""Seal the candidates of PROTOCOL_FINAL.md for ENNS 2022 (every province, Leads 1-2), with exactly the construction of the existing
H_cw seal (aiPHeed_objective_completion_20261111/scripts/seal_hcw_enns2022.py); only the engine options differ.
BASE is run as an integrity check and must reproduce the existing H_cw seal. No 2022 outcome exists locally.
Writes evidence/sealed_enns2022_candidates.json (+ .sha256). Run from C:\\Users\\admin\\aipheed_hcw\\backend with PYTHONPATH=."""
import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

warnings.filterwarnings("ignore")
STUDY = Path(__file__).resolve().parents[1]
RN = STUDY.parent
EV = STUDY / "evidence"
SEAL = EV / "sealed_enns2022_candidates.json"
OLD = RN / "aiPHeed_objective_completion_20261111" / "evidence" / "sealed_enns2022_hcw.json"
SEEDS = (168, 1, 2, 3, 4)
ARMS = {"BASE": {}, "IMPUTE": dict(miss="median"), "RATE": dict(rate="lin"), "FINAL": json.loads((EV / "final_config.json").read_text())["config"]}
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def job(arm, lead, seed):
    for p in (str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"), str(STUDY / "scripts")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    from app.e147 import features as Fe
    from app.e150 import model as M
    from app.e151 import prov as Pv
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    from app.e164 import auto as A4
    from app.e166 import nested_source as N
    from app.e166.enns2022 import ORIGIN, T22, targets
    from app.hcw import engine as H
    from app.paths import BACKEND_DIR
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    Hn, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    S = Pv.Store2(None)
    i = T22 - lead
    rel = M.released(i, Pv.ROUNDS)
    assert "ENNS2021" not in rel
    P = M.Pipeline(S, i, Pv.ROUNDS, ORIGIN)
    te = N.add_sources(E154.add_income(Pv.add_inputs(S, M.rows_for(S, targets(S), [lead], ORIGIN)), Hn), L, Hn, S_P).reset_index(drop=True)
    tr = N.add_sources(E154.add_income(Pv.add_inputs(S, P.tr), Hn), L, Hn, S_P).reset_index(drop=True)
    AN = A4.anchors(S, P, tr, te)
    cp = pd.read_parquet(BACKEND_DIR / "data" / "hcw" / "out" / "cand_panel.parquet")
    new = [c for c in H.ADD if c in cp and c not in tr]
    tr = tr.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    te = te.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    r = EF.fit_predict(tr, te, {a: AN[a] for a in H.ANC}, seed, **ARMS[arm])
    return te[["key", "province", "region", "island", "lead", "gap_q"]].assign(arm=arm, seed=seed, p=r["p"], mu=r["mu"], cfg=r["cfg"], released="|".join(rel), origin=ORIGIN,
                                                                               train_gaps="|".join(map(str, sorted(set(tr["gap_q"].astype(int))))))


def safe(*a):
    try:
        return job(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1500:]}"


if __name__ == "__main__":
    if SEAL.exists():
        raise SystemExit("already sealed: " + hashlib.sha256(SEAL.read_bytes()).hexdigest())
    R = Parallel(n_jobs=20, verbose=5)(delayed(safe)(a, l, s) for a in ARMS for l in (1, 2) for s in SEEDS)
    bad = [x for x in R if isinstance(x, str)]
    if bad:
        raise SystemExit("\n".join(bad[:3]))
    R = pd.concat(R, ignore_index=True)
    g = R.groupby(["arm", "key", "province", "region", "island", "lead", "gap_q", "released", "origin", "train_gaps"], as_index=False)[["p", "mu"]].mean()
    oj = json.loads(OLD.read_text())
    old = pd.DataFrame(oj.get("forecasts", oj.get("rows", [])))
    pc = next((c for c in ("p_high", "p") if c in old.columns), None)
    check = None
    if pc:
        m = g[g.arm == "BASE"].merge(old[["key", "lead", pc]].rename(columns={pc: "p_old"}), on=["key", "lead"])
        check = {"rows": int(len(m)), "max_abs_diff_BASE_vs_existing_hcw_seal": float((m.p - m.p_old).abs().max()), "class_agreement": float(((m.p >= .5) == (m.p_old >= .5)).mean())}
    g["pct"], g["cls"] = pct(g.mu).round(2), np.where(g.p >= .5, "HIGH", "LOW")
    body = {"sealed_utc": datetime.now(timezone.utc).isoformat(), "protocol_sha256": (STUDY / "PROTOCOL_FINAL.sha256").read_text().split()[0],
            "note": "Candidates sealed before any ENNS 2022 provincial outcome is available locally. BASE = H_cw integrity check.", "arms": ARMS, "integrity_check": check,
            "class_counts": g.groupby(["arm", "lead"])["cls"].value_counts().unstack(fill_value=0).reset_index().to_dict("records"), "rows": g.round(6).to_dict("records")}
    SEAL.write_text(json.dumps(body, indent=1), newline="\n")
    h = hashlib.sha256(SEAL.read_bytes()).hexdigest()
    (EV / "sealed_enns2022_candidates.sha256").write_text(h + "\n", newline="\n")
    print(h, check)
    print(g.groupby(["arm", "lead"])["cls"].value_counts().unstack(fill_value=0))
    print(g[g.region.astype(str).str.contains("CALABARZON")].pivot_table(index=["province", "lead"], columns="arm", values="p").round(3))

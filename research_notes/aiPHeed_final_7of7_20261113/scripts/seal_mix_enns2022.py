r"""FINAL_7_OF_7_IMPROVEMENT_PROTOCOL (sha a365da1f): prospective seal of FINAL-MIX and its components for ENNS 2022 (every province,
Leads 1-2, seeds 168/1/2/3/4), with exactly the construction of
aiPHeed_hcw_final_optimization_20261112/scripts/seal_candidates_enns2022.py (FINAL arm: rate='lin', miss='mind').
Each fit predicts the test rows twice: elapsed time g = gap_q (FINAL) and s = quarters since the latest released round (FINAL-ET);
FINAL-MIX = mean of the two probabilities. Integrity check: the FINAL rows must equal the FINAL rows of the existing seal (4ad9267f).
No 2022 outcome exists locally. Writes evidence/sealed_enns2022_final_mix.json (+ .sha256).
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python seal_mix_enns2022.py"""
import hashlib, json, sys, warnings
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
OPT = RN / "aiPHeed_hcw_final_optimization_20261112"
SEAL = HERE / "evidence" / "sealed_enns2022_final_mix.json"
OLD = OPT / "evidence" / "sealed_enns2022_candidates.json"
SEEDS = (168, 1, 2, 3, 4)
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def job(lead, seed):
    for p in (str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"), str(OPT / "scripts")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    from app.e147 import features as Fe
    from app.e148 import model as M8
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
    s = T22 - max(M8.RQ[x] for x in rel)
    te_s = te.assign(gap_q=np.full(len(te), s, dtype=te["gap_q"].dtype))
    T = pd.concat([te.assign(variant="FINAL"), te_s.assign(variant="FINAL-ET")], ignore_index=True)
    AN2 = {a: (AN[a][0], np.tile(np.asarray(AN[a][1]), 2)) for a in H.ANC}
    r = EF.fit_predict(tr, T, AN2, seed, rate="lin", miss="mind")
    return T[["key", "province", "region", "island", "lead", "gap_q", "variant"]].assign(seed=seed, p=r["p"], mu=r["mu"], cfg=r["cfg"], released="|".join(rel),
                                                                                          origin=ORIGIN, stale_q=int(s), own_gap_q=np.tile(te["gap_q"].values, 2))


if __name__ == "__main__":
    R = pd.concat(Parallel(n_jobs=10, verbose=5)(delayed(job)(L, s) for L in (1, 2) for s in SEEDS), ignore_index=True)
    R.to_csv(HERE / "evidence" / "seal_mix_seed_rows.csv", index=False, lineterminator="\n")
    A = R.groupby(["key", "province", "region", "island", "lead", "variant", "own_gap_q", "stale_q", "released", "origin"], as_index=False)[["p", "mu"]].mean()
    W = A.pivot_table(index=["key", "province", "region", "island", "lead", "own_gap_q", "stale_q", "released", "origin"], columns="variant", values="p").reset_index()
    W["FINAL-MIX"] = 0.5 * (W["FINAL"] + W["FINAL-ET"])
    rows = []
    for arm in ("FINAL", "FINAL-ET", "FINAL-MIX"):
        for _, r in W.iterrows():
            rows.append({"arm": arm, "key": r.key, "province": r.province, "region": r.region, "lead": int(r.lead), "own_gap_q": int(r.own_gap_q),
                         "stale_q": int(r.stale_q), "released": r.released, "p": round(float(r[arm]), 6), "cls": "HIGH" if r[arm] >= .5 else "LOW"})
    old = json.load(open(OLD))
    o = pd.DataFrame([x for x in old["rows"] if x["arm"] == "FINAL"])[["key", "lead", "p"]]
    chk = W[["key", "lead", "FINAL"]].merge(o, on=["key", "lead"])
    integ = {"rows_compared": int(len(chk)), "max_abs_diff_vs_existing_FINAL_seal": float((chk["FINAL"] - chk["p"]).abs().max()),
             "existing_seal_sha256": hashlib.sha256(OLD.read_bytes()).hexdigest()}
    doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "protocol": "FINAL_7_OF_7_IMPROVEMENT_PROTOCOL.md", "protocol_sha256": "a365da1fe32b50f36b117aeb6accb1b2685e7ec244bc5f7a4fce0dccb7d9d3fa",
           "acceptance_protocol_sha256": "15202d27800c3eb1e7efea5abe33a8dcf7ac67d6b9170eeb3c8080839ba957eb",
           "note": "No 2022 outcome exists locally. FINAL-MIX = mean of FINAL (g) and FINAL-ET (s) probabilities; HIGH at 0.50.",
           "integrity_check": integ, "class_counts": {f"{a}_L{l}": int(sum(1 for x in rows if x["arm"] == a and x["lead"] == l and x["cls"] == "HIGH"))
                                                      for a in ("FINAL", "FINAL-ET", "FINAL-MIX") for l in (1, 2)},
           "rows": rows}
    SEAL.write_text(json.dumps(doc, indent=1), newline="\n")
    sha = hashlib.sha256(SEAL.read_bytes()).hexdigest()
    (SEAL.parent / (SEAL.name + ".sha256")).write_text(f"{sha}  {SEAL.name}\n", newline="\n")
    print(json.dumps({k: doc[k] for k in ("integrity_check", "class_counts")}, indent=1), "\nsha256", sha)

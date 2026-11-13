r"""Live fits for the experimental seals (issue 2026-Q4, information cut-off 2026-11-01, five CALABARZON provinces, Leads 1-5, seeds 168/1/2/3/4).
Exactly the official FINAL live path (aiPHeed_final_dashboard_preview_20261113/scripts/build_corrected.py `_one`, variant g = own-survey gap,
app.hcw.final_engine.fit_predict), with one switch:
  NOPAIR  no change (must reproduce SEALED_FINAL_2027Q1_2028Q1.json official_p_high_FINAL)
  LG      + genuine long-gap pair rows (build_lg.make_pairs: FNRI2015 withheld from the anchor -> NNS2013 anchor) in the training table
Also writes the Lead-1 live training/test tables for ATTR. Never reads a provincial outcome after 2021 (none exists).
Run from C:\Users\admin\aipheed_hcw\backend with AIPHEED_LIVE_ASOF=2026-11-01 PYTHONPATH=.   Usage: python seal_fits.py"""
import json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; PARTS = HERE / "parts"
CAND = RN / "aiPHeed_final_dashboard_preview_20261113" / "out_final" / "cand_panel.parquet"
LEADS, SEEDS = (1, 2, 3, 4, 5), (168, 1, 2, 3, 4)
for p in [str(RN / "aiPHeed_final_model_optimization_20261113" / "scripts"), str(RN / "aiPHeed_study_20261110" / "evidence" / "scripts"),
          str(RN / "aiPHeed_complete_validation" / "tests"), str(RN / "aiPHeed_objective_completion_20261111" / "scripts"),
          str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"), str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]:
    if p not in sys.path:
        sys.path.append(p)


def tables(lead, pairs):
    from app.e147 import features as Fe
    from app.e150 import model as M
    from app.e151 import prov as Pv
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    from app.e164 import auto as A4
    from app.e166 import nested_source as N
    from app.fi5.target import qindex
    from app.hcw import engine as H
    from app.hcw import serve as SV
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    issue = qindex("2026-Q4")
    Hn, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, issue, Pv.ROUNDS, "F")
    npairs = 0
    if pairs:
        import build_lg as B
        X = B.make_pairs(S, issue, "F"); npairs = len(X)
        P.tr = pd.concat([P.tr.assign(lg_pair=0), X], ignore_index=True)
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(SV.CAL)].assign(T=issue + lead, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"])
    te = N.add_sources(Pv.add_inputs(S, M.rows_for(S, five, [lead], "F")), L, Hn, S_P).reset_index(drop=True)
    tr = N.add_sources(Pv.add_inputs(S, P.tr), L, Hn, S_P).reset_index(drop=True)
    AN = A4.anchors(S, P, tr, te)
    cp = pd.read_parquet(CAND)
    new = [c for c in H.ADD if c in cp and c not in tr]
    tr = tr.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    te = te.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    info = {"n_train": len(tr), "n_pairs": npairs, "train_rounds": tr.groupby("survey").size().to_dict(), "issue": int(issue)}
    if pairs and npairs:
        Pp = tr[tr.get("lg_pair", 0) == 1]
        info["pair_anchor_rq"] = sorted(Pp.rq_anchor.unique().tolist()); info["pair_targets"] = Pp.groupby("survey").key.nunique().to_dict()
    return tr, te, AN, info


def one(arm, lead, seed):
    f = PARTS / f"{arm}__L{lead}__{seed}.csv"
    if f.exists():
        return str(f)
    from app.hcw import final_engine as FE
    tr, te, AN, info = tables(lead, arm == "LG")
    r = FE.fit_predict(tr, te, AN, seed)
    te[["province", "key", "T", "i", "gap_q", "y_anchor", "rq_anchor"]].assign(arm=arm, lead=lead, seed=seed, mu=np.asarray(r["mu"]), p=np.asarray(r["p"]),
                                                                               half=np.asarray(r["half"]), cal=str(r["cal"]), cfg=str(r.get("cfg", "")),
                                                                               n_train=info["n_train"], n_pairs=info["n_pairs"]).to_csv(f, index=False, lineterminator="\n")
    if seed == 168 and lead == 1:
        json.dump(info, open(PARTS / f"{arm}__info.json", "w"), indent=1, default=str)
        if arm == "NOPAIR":
            pickle.dump({"tr": tr, "te": te}, open(PARTS / "ATTR_live_tables_L1.pkl", "wb"))
    return str(f)


def safe(*a):
    try:
        return one(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1500:]}"


if __name__ == "__main__":
    PARTS.mkdir(parents=True, exist_ok=True)
    J = [(a, l, s) for a in ("NOPAIR", "LG") for l in LEADS for s in SEEDS]
    R = Parallel(n_jobs=16, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:3], sep="\n", flush=True)

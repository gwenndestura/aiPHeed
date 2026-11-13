r"""PROTOCOL_SA Rule 7a (determinism) and 7e (missing-input sensitivity) for the candidate FINAL-SA: Lead 1, seed 168, each round;
the same capped engine predicts the test rows and copies with one input group missing. Compares the unperturbed block with the
stored candidate parts. Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python stability_sa.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_sa as RS          # noqa: E402
import rerun_final as RF     # noqa: E402


def one(sv):
    for p in RS.PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import run_qs
    from app.hcw import engine as H
    EF, M4Cap = RS.capped_class()
    tr, te, AN = run_qs.load(sv, 1)
    te = te.reset_index(drop=True)
    allc = sorted({c for v in H.feature_sets().values() for c in v if c in te.columns})
    blocks = [te.assign(variant="none")] + [te.assign(**{c: np.nan for c in allc if RF.group_of(c) == g}, variant=f"missing_{g}")
                                            for g in ("market", "climate", "employment", "poverty", "agri_fish", "news_aggregate")]
    AN2 = {a: (AN[a][0], np.tile(np.asarray(AN[a][1]), len(blocks))) for a in AN}
    T = pd.concat(blocks, ignore_index=True)
    old = EF.M4
    EF.M4 = M4Cap
    try:
        r = EF.fit_predict(tr, T, AN2, 168, rate="lin", miss="mind", cw="balanced")
    finally:
        EF.M4 = old
    return T[["key", "survey", "variant"]].assign(p=r["p"], thr=r["thr"])


R = pd.concat(Parallel(n_jobs=3)(delayed(one)(sv) for sv in ("ENNS2018", "ENNS2019", "ENNS2021")))
stored = pd.concat([pd.read_csv(HERE / "parts_sa" / f"FINALSA__{sv}__1__168.csv") for sv in ("ENNS2018", "ENNS2019", "ENNS2021")])
m = R[R.variant == "none"].merge(stored[["key", "survey", "p"]], on=["key", "survey"], suffixes=("", "_stored"))
rep = {"rows": int(len(m)), "max_abs_diff_p_vs_stored": float((m.p - m.p_stored).abs().max())}
rep["deterministic"] = rep["rows"] == 72 and rep["max_abs_diff_p_vs_stored"] <= 1e-9
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
X = R.merge(LAB[LAB.lead == 1][["key", "survey", "y_high"]], on=["key", "survey"])
X["cut"] = X["thr"]
def ba(g):
    h, y = g.p >= g.cut, g.y_high == 1
    return 0.5 * ((h & y).sum() / y.sum() + (~h & ~y).sum() / (~y).sum())
b0 = X[X.variant == "none"].set_index(["key", "survey"])
rows = []
for v, g in X.groupby("variant"):
    gi = g.set_index(["key", "survey"])
    rows.append({"variant": v, "balanced_accuracy": round(float(ba(g)), 3), "delta_BA": round(float(ba(g) - ba(b0.reset_index())), 3),
                 "mean_abs_change_p": round(float((gi.p - b0.p).abs().mean()), 3), "class_flips": int(((gi.p >= gi.cut) != (b0.p >= b0.cut)).sum())})
S = pd.DataFrame(rows).sort_values("delta_BA")
S.to_csv(HERE / "evidence" / "R7e_missing_group_sensitivity_FINALSA_L1_seed168.csv", index=False)
rep["sensitivity_severe_any"] = bool((S.delta_BA.abs() > 0.10).any())
json.dump(rep, open(HERE / "evidence" / "R7a_FINALSA_determinism.json", "w"), indent=1)
print(json.dumps(rep, indent=1)); print(S.to_string(index=False))

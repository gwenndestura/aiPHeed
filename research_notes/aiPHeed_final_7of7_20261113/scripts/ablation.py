r"""Group contribution evidence for the dashboard trigger-group decision (FINAL, unchanged model; seed 168).
(a) WITHHOLD: at every fold-lead (22), the fitted FINAL model predicts the test rows and copies with one meaning-based group set to
    missing (as if unpublished; MIND fills training medians + flags). Outcome-free measures: probability change, class flips.
(b) RETRAIN: at Lead 1, each round, FINAL is refitted with one group removed from its candidate inputs (feature sets).
Groups are defined by what the inputs measure (GROUPS below), not by the dashboard design. No outcome is read here.
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python ablation.py [--jobs N]"""
import argparse, sys
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
PATHS = [str(RN / "aiPHeed_objective_completion_20261111" / "scripts"), str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"),
         str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"), str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]
FOLDS = [(sv, L) for sv, n in (("ENNS2018", 6), ("ENNS2019", 8), ("ENNS2021", 8)) for L in range(1, n + 1)]


def group(c: str) -> str:
    """Meaning-based groups for FINAL's 77 candidate inputs (definitions in FINAL_INPUT_FEATURE_AUDIT.md)."""
    if c in ("gap_q", "lead"):
        return "timing"
    if c in ("hh_grdp_g", "hh_grdp_rel", "income_growth", "income_rel"):
        return "regional_accounts"
    if c in ("p_poverty", "p_poverty_gap", "p_subsistence", "p_density"):
        return "poverty_vulnerability"
    if c.startswith(("cpi_", "l_fg", "l_rice", "l_terms")):
        return "market_prices"
    if c.startswith(("c_rain", "c_soil", "c_tc", "rain_", "soil_", "tc_", "vu_")) or c == "oni":
        return "climate"
    if c.startswith("unemp"):
        return "employment"
    if c.startswith(("ag_", "agri_", "c_agri", "l_fish")):
        return "agri_fish_production"
    return "news_nlp"          # *_e_*, *_tp_*, p_tg_*, p_intensity, *_net_since, r_e_net, h2 (news-model SWS hunger increment)


GROUPS = ("market_prices", "climate", "employment", "regional_accounts", "poverty_vulnerability", "agri_fish_production", "news_nlp")


def job(kind, survey, lead, drop=None):
    f = HERE / "ablation" / (f"WITHHOLD__{survey}__{lead}.csv" if kind == "withhold" else f"RETRAIN__{survey}__{lead}__{drop}.csv")
    if f.exists():
        return str(f)
    for p in PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    import run_qs
    from app.hcw import engine as H
    tr, te, AN = run_qs.load(survey, lead)
    te = te.reset_index(drop=True)
    allc = sorted({c for v in H.feature_sets().values() for c in v if c in te.columns})
    if kind == "withhold":
        blocks = [te.assign(variant="none")] + [te.assign(**{c: np.nan for c in allc if group(c) == g}, variant=f"no_{g}") for g in GROUPS]
        T = pd.concat(blocks, ignore_index=True)
        AN2 = {a: (AN[a][0], np.tile(np.asarray(AN[a][1]), len(blocks))) for a in AN}
        r = EF.fit_predict(tr, T, AN2, 168, rate="lin", miss="mind", cw="balanced")
        out = T[["key", "survey", "lead", "variant"]].assign(p=r["p"])
    else:
        orig = H.feature_sets
        H.feature_sets = lambda: {k: [c for c in v if group(c) != drop] for k, v in orig().items()}
        try:
            r = EF.fit_predict(tr, te, AN, 168, rate="lin", miss="mind", cw="balanced")
        finally:
            H.feature_sets = orig
        out = te[["key", "survey", "lead"]].assign(variant=f"retrain_without_{drop}", p=r["p"], selected=";".join(r["model"].use_))
    (HERE / "ablation").mkdir(exist_ok=True)
    out.to_csv(f.with_suffix(".tmp"), index=False, lineterminator="\n")
    f.with_suffix(".tmp").replace(f)
    return str(f)


def safe(*a):
    try:
        return job(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1200:]}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=12)
    a = ap.parse_args()
    J = [("withhold", sv, L) for sv, L in FOLDS] + [("retrain", sv, 1, g) for sv in ("ENNS2018", "ENNS2019", "ENNS2021") for g in GROUPS]
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=a.jobs, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:6], sep="\n", flush=True)

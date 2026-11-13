r"""PROTOCOL_INPUTS (sha 4cb830c6, locked before this script ran): fits arms B0, D-*, F-ALL, N-OFF, N-OFF-F on FINAL's folds.
Engine unchanged (research engine_final, rate=lin, miss=mind, cw=balanced). No test outcome is read here.
Run from C:\Users\admin\aipheed_hcw\backend (engine identical to the branch's app/hcw) with PYTHONPATH=.
Usage: python inputs_run.py [jobs] [leads, e.g. 1,2]"""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parents[1]; PARTS = HERE / "parts"
RN = Path(r"C:\Users\admin\aipheed_final\research_notes")          # where the fold caches and research engines live
for p in [RN / "aiPHeed_final_model_optimization_20261113" / "scripts", RN / "aiPHeed_study_20261110" / "evidence" / "scripts",
          RN / "aiPHeed_complete_validation" / "tests", RN / "aiPHeed_objective_completion_20261111" / "scripts",
          RN / "aiPHeed_hcw_optimization_20261112" / "scripts", RN / "aiPHeed_hcw_independent_check_20261112" / "scripts",
          RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts"]:
    if str(p) not in sys.path:
        sys.path.append(str(p))

SEEDS = (168, 1, 2, 3, 4)
SURVEYS = ("ENNS2018", "ENNS2019", "ENNS2021")
POV = ["p_poverty", "p_subsistence", "p_poverty_gap"]
OFFICIAL = POV + ["p_density", "hh_grdp_g", "hh_grdp_rel", "oni"]
ONI_NEW = ["oni_12m", "oni_max12", "nino_m12", "nina_m12", "oni_lag2q"]
POP_NEW = ["p_density_c", "p_popgrowth"]
NEW = POP_NEW + ONI_NEW
NEW_SIGNS = {"oni_12m": 1, "oni_max12": 1, "nino_m12": 1, "nina_m12": 0, "oni_lag2q": 1, "p_density_c": 0, "p_popgrowth": 0}
DROPS = {"B0": [], "D-ALL": OFFICIAL, "D-POV": POV, "D-DEN": ["p_density"], "D-GRDP": ["hh_grdp_g", "hh_grdp_rel"], "D-ONI": ["oni"],
         "F-ALL": [], "N-OFF": ["p_density"], "N-OFF-F": ["p_density"]}
FORCE = {"F-ALL": OFFICIAL, "N-OFF-F": POV + POP_NEW + ["hh_grdp_g", "hh_grdp_rel"] + ONI_NEW}
ARMS = list(DROPS)


def issue_date(i: int) -> pd.Timestamp:
    """Quarter index i = year*4 + (quarter-1); the issue date is the first day of that quarter."""
    return pd.Timestamp(year=int(i) // 4, month=(int(i) % 4) * 3 + 1, day=1)


# ---------------- official inputs (as of the issue date) ----------------
CENSUS = {2010: ("Total Population (01 May 2010)", pd.Timestamp("2010-05-01")), 2015: ("Total Population (01 August 2015)", pd.Timestamp("2015-08-01")),
          2020: ("Total Population (01 May 2020)", pd.Timestamp("2020-05-01")), 2024: ("Total Population (01 July 2024)", pd.Timestamp("2024-07-01"))}


@lru_cache(maxsize=None)
def census():
    from app.e137 import features as F
    raw = F.RAW / "psa"
    pop = pd.read_csv(raw / "population_2010_2024.csv", dtype=str, encoding="latin-1")
    pop = pop[pop.iloc[:, 0].str.match(r"^\.\.\.\.[^.]")]
    pop["k"] = pop.iloc[:, 0].str.replace("*", "", regex=False).map(F.nospace)
    area = pd.read_csv(raw / "land_area_density_2024.csv", dtype=str, encoding="latin-1")
    area = area[area.iloc[:, 0].str.match(r"^\.\.\.\.[^.]")]
    area["k"] = area.iloc[:, 0].str.replace("*", "", regex=False).map(F.nospace)
    a = pd.to_numeric(area.set_index("k").filter(like="Land Area").iloc[:, 0], errors="coerce")
    p = pop.set_index("k")
    out = pd.DataFrame({y: pd.to_numeric(p[c].str.replace(",", ""), errors="coerce") for y, (c, _) in CENSUS.items()})
    out = out[~out.index.duplicated()]
    out["area"] = a[~a.index.duplicated()].reindex(out.index)
    return out


@lru_cache(maxsize=None)
def oni_table():
    from app.fi5 import sources as S
    d = S.oni()
    # historical rule only (season end + 10 days); the live 'seen' log never makes a value earlier than the rule for past seasons
    d["available_from"] = d["period_end"] + pd.Timedelta(days=10)
    return d.reset_index(drop=True)


def official_row(key: str, i: int) -> dict:
    from app.e137 import features as F
    d = issue_date(i)
    out = {c: np.nan for c in NEW}
    C, k = census(), F.nospace(key)
    rel = [y for y in CENSUS if pd.Timestamp(year=y + 2, month=1, day=1) <= d]        # census C usable from 1 January of C+2
    if k in C.index and rel:
        y1 = max(rel)
        if pd.notna(C.at[k, y1]) and pd.notna(C.at[k, "area"]) and C.at[k, "area"] > 0:
            out["p_density_c"] = float(np.log(C.at[k, y1] / C.at[k, "area"]))
        if len(rel) >= 2:
            y0 = sorted(rel)[-2]
            if pd.notna(C.at[k, y0]) and pd.notna(C.at[k, y1]) and C.at[k, y0] > 0:
                yrs = (CENSUS[y1][1] - CENSUS[y0][1]).days / 365.25
                out["p_popgrowth"] = float(np.log(C.at[k, y1] / C.at[k, y0]) / yrs * 100)
    O = oni_table()
    av = O[O["available_from"] < d]
    if len(av) >= 12:
        last = av["oni"].iloc[-12:].values
        out.update(oni_12m=float(last.mean()), oni_max12=float(last.max()), nino_m12=float((last >= 0.5).sum()), nina_m12=float((last <= -0.5).sum()))
    av6 = O[O["available_from"] < d - pd.DateOffset(months=6)]
    if len(av6):
        out["oni_lag2q"] = float(av6["oni"].iloc[-1])
    return out


def add_official(df: pd.DataFrame) -> pd.DataFrame:
    rows = {(k, i): official_row(k, i) for k, i in df[["key", "i"]].drop_duplicates().itertuples(index=False)}
    add = pd.DataFrame([rows[(k, i)] for k, i in df[["key", "i"]].itertuples(index=False)], index=df.index)
    return pd.concat([df.drop(columns=[c for c in NEW if c in df]), add], axis=1)


# ---------------- one fit ----------------
def job(arm, survey, lead, seed):
    tag = f"{arm}__{survey}__L{lead}__{seed}"
    f = PARTS / f"{tag}.csv"
    if f.exists():
        return str(f)
    import engine_final as EF
    import engine_opt as EO
    import run_qs
    from app.hcw import engine as H
    tr, te, AN = run_qs.load(survey, lead)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    drop, force, new = set(DROPS[arm]), FORCE.get(arm, []), arm.startswith("N-OFF")
    if new:
        tr, te = add_official(tr), add_official(te)
        H.NEW_SIGN.update(NEW_SIGNS)
    fs0 = H.feature_sets
    def fs():
        FS = fs0()
        return {k: [c for c in v if c not in drop] + ([c for c in NEW if c not in v] if new else []) for k, v in FS.items()}
    sel0 = EO.M2._select
    def sel(self, d):
        use = list(sel0(self, d))
        for c in force:
            if c in self.cols and c in d and c not in use and d[c].notna().any() and d[c].nunique() > 1:
                use.append(c)
        return use
    H.feature_sets = fs
    if force:
        EO.M2._select = sel
    try:
        r = EF.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")
    finally:
        H.feature_sets, EO.M2._select = fs0, sel0
    te[["key", "survey", "lead"]].assign(arm=arm, seed=seed, p=r["p"], mu=r["mu"], cal=r["cal"], cfg=r["cfg"],
                                         selected=";".join(r["model"].use_), n_train=len(tr)).to_csv(f, index=False, lineterminator="\n")
    return str(f)


def safe(*a):
    try:
        return job(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1500:]}"


if __name__ == "__main__":
    PARTS.mkdir(exist_ok=True)
    leads = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "1,2").split(",")]
    J = [(a, s, L, sd) for L in leads for a in ARMS for s in SURVEYS for sd in SEEDS]
    print(len(J), "jobs", flush=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import inputs_run as M                      # workers unpickle functions by module name, not __main__
    R = Parallel(n_jobs=int(sys.argv[1]) if len(sys.argv) > 1 else 18, verbose=5)(delayed(M.safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:4], sep="\n", flush=True)

"""Shared code for the prospective protocol (../PROSPECTIVE_PLAN.md): plan check, table rebuild, the frozen REF+news /
REF refit at one origin, baselines, input freshness, labels, the seal ledger and an independent R1-R7 recomputation.
The ALLBASE registry (NEW_MODEL/ALLBASE/PHASE_B_PROSPECTIVE_REGISTRY_SPEC.md) adds the seven established baselines and
the candidates K1-K3, each with the specification of its development run.

The model code is IMPROVE_V2's / OPTION_1's, imported read only; nothing here changes a setting.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import math
import re
import subprocess
from datetime import date
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
ROOT = EXP.parents[1]
PLAN = HERE / "PROSPECTIVE_PLAN.md"
PROS = HERE / "prospective"
LEDGER = PROS / "SEAL_LEDGER.md"
sys.path.insert(0, str(EXP / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402

H = V.H
OPT_SEAL = EXP / "OPTION_1" / "sealed_prospective_REFNEWS.csv"
OPT_SEAL_SHA = "cc1ff11b589256746a2503160c22d5a25ee1f0272b6fa5900b6d4b9ff9db5216"
STORED_TABLE = EXP / "IMPROVE_V2" / "out" / "table_pooled.csv"
SWS_FILE = H.LONG / "sws_area_rounds_full.csv"
E112_FILE = EXP / "E112_Food_Insecurity_Forecasting" / "out" / "news_quarterly_corpus.csv"
FIRST_ISSUE = "2027-01-01"
FIRST_TARGET = H.qi("2027-Q1")
LEADS = (1, 2)
CB_DIR = EXP / "NEW_MODEL" / "NEWS_V2"
ADDENDUM_CB = CB_DIR / "PROSPECTIVE_ADDENDUM_CB.md"              # in force: C-b adopted by the team, 2026-11-03
CB_SEAL = CB_DIR / "sealed_prospective_CB.csv"
CB_SEAL_SHA = "67baec6689cbbafc248caac722cc4daa28196c1958ab55ac1100983dd8691015"
_REF = V.cols(False, False)
MODELS = {"C-b": _REF[:-1] + ["z_N1R"] + _REF[-1:], "REF+news": V.cols(False, True), "REF": _REF}
MAIN = "C-b"
# ALLBASE registry: LightGBM (fit_origin, first origin), logistic (iv2_lib.logit_lead, first origin), blends of C-b + LOGIT
ALLBASE = EXP / "NEW_MODEL" / "ALLBASE"
sys.path.insert(0, str(ALLBASE / "runner"))
import phase_c as PC  # noqa: E402      (reversal features and the K2 weight rule, as run in Phase C)

GOV = ["R_food_yoy", "R_head_yoy", "R_rice_yoy", "R_food_mom", "R_C3", "R_C4", "ONI_last", "ONI_max12",
       "tc_mean"] + H.WORLD                                      # OBJECTIVES_COMPLETION h3.GOV
LGBM_EXTRA = {"K3": (PC.K3, H.FIRST_ORIGIN), "LGBM-GOV": (GOV + ["lead"], H.FIRST_ORIGIN),
              "LGBM-NLP": (V.NEWS + ["lead"], V.NEWS_ERA)}
LOGIT_MODELS = {"LOGIT": (H.T2_B, H.FIRST_ORIGIN), "PSA-only": (V.PSA, H.FIRST_ORIGIN), "NLP-only": (V.NEWS, V.NEWS_ERA)}
BLENDS = ("K1", "K2")
CONSTANT = {"ALWAYS-HIGH": 1.0}
SCORED = list(MODELS) + list(LGBM_EXTRA) + list(LOGIT_MODELS) + list(BLENDS) + list(CONSTANT) + ["PERSIST", "CLIM"]
CANDIDATES = ("K1", "K2", "K3")
COMPARATORS = ("PERSIST", "PSA-only", "LOGIT", "NLP-only", "LGBM-GOV", "LGBM-NLP", "ALWAYS-HIGH")
ALG4_N, FAMILY_MIN = 4, 20                    # Algorithm 4 holdout size; prospective 42-test family from 20 quarters
NEWS_WIN, NEWS_MINP = 8, 4                                       # NEWS_V2 PLAN section 1: z over t-8..t-1, >= 4 values
SEAL_WINDOW_DAYS = 14
MIN_QUARTERS, REVIEW_MIN, REVIEW_P = 40, 20, 0.05
SEED, B = 2036, 5000
NEWS_FRESH_DAYS = 14              # the E112 quarter must have been collected to within 14 days of O(t)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_plan() -> str:
    b = PLAN.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    assert last.startswith(b"PLAN-SHA256: "), "PROSPECTIVE_PLAN.md has no hash line"
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.split()[1].decode() == h, "PROSPECTIVE_PLAN.md changed after it was hashed"
    b = ADDENDUM_CB.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    assert last.startswith(b"ADDENDUM-SHA256: ") and \
        last.split()[1].decode() == hashlib.sha256(body + b"\n").hexdigest(), "Addendum CB changed after it was hashed"
    return h


def add_news_anomaly(T: pd.DataFrame) -> pd.DataFrame:
    """C-b's z_N1R (NEWS_V2 PLAN section 1): (N1R(t) - mean(N1R over origins t-8..t-1)) / sd (ddof 1), NaN if fewer than
    4 past values or sd = 0. One value per origin, from the BL rows of the rebuilt table; past origins only."""
    s = T[T["area"] == "BL"].drop_duplicates("t").set_index("t").sort_index()["N1R"]
    z = {}
    for t in s.index:
        past = s.loc[[x for x in range(t - NEWS_WIN, t) if x in s.index]].dropna()
        sd = float(past.std(ddof=1)) if len(past) >= 2 else float("nan")
        z[t] = float((s[t] - past.mean()) / sd) if pd.notna(s[t]) and len(past) >= NEWS_MINP and sd > 0 else np.nan
    return T.assign(z_N1R=T["t"].map(z))


def check_allbase() -> str:
    """The ALLBASE pre-registration hash (the K1-K3 definitions and the registry revision are fixed there)."""
    return PC.check_prereg()


def add_reversal(T: pd.DataFrame, d) -> pd.DataFrame:
    """K3's four reversal features (PHASE_B_EXPERIMENT_DESIGN section 2), one value per origin, from BL readings
    published before O(t): the Phase C implementation A, unchanged."""
    F = pd.DataFrame([{"t": t, **PC.reversal_a(d, t)} for t in sorted(T["t"].unique())])
    return T.drop(columns=[c for c in PC.REV if c in T]).merge(F, on="t", how="left")


def logit_origin(S: pd.DataFrame, d, lab: pd.DataFrame, t: int, cols: list[str], first: int) -> pd.DataFrame:
    """IMPROVE_V2 run_iv2 baseline path at one origin: iv2_lib.logit_lead (one model per lead, labels known at O(t))."""
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"][["q", "y"]]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    f = V.logit_lead(S, t, kb, cols, clim, first)
    f = f[f["lead"].isin(LEADS)].copy()
    f["cfg"], f["n_train"] = None, -1
    return f[["t", "lead", "q", "p", "fallback", "cfg", "n_train", "h_last", "sws_newest_published"]]


def k2_weight(d, t: int, lead: int, prospective: pd.DataFrame | None = None) -> tuple[float, int]:
    """The K2 rule (design section 3, phase_c.choose_w) at origin t: past C-b / LOGIT pairs from the development runs
    (origins <= 2026-Q3) plus earlier sealed prospective rows (columns t, q, lead, model, p); labels known at O(t)."""
    cb = pd.read_csv(CB_DIR / "out" / "forecasts.csv")
    cb = cb[(cb["name"] == "C-b") & (cb["lead"] == lead)][["t", "q", "p"]].rename(columns={"p": "cb"})
    lg = pd.read_csv(ALLBASE / "out" / "fits.csv")
    lg = lg[(lg["name"] == "LOGIT_regen") & (lg["lead"] == lead)][["t", "p"]].rename(columns={"p": "lg"})
    Pp = cb.merge(lg, on="t", how="inner")
    Pp = Pp[Pp["t"] <= V.LAST_ORIGIN]
    if prospective is not None and len(prospective):
        x = prospective[(prospective["lead"] == lead) & prospective["model"].isin(["C-b", "LOGIT"])]
        x = x.pivot_table(index=["t", "q"], columns="model", values="p", aggfunc="first").reset_index()
        if {"C-b", "LOGIT"} <= set(x.columns):
            x = x.rename(columns={"C-b": "cb", "LOGIT": "lg"})[["t", "q", "cb", "lg"]]
            Pp = pd.concat([Pp, x[x["t"] > V.LAST_ORIGIN]], ignore_index=True)
    lab = V.area_labels(d)
    lab = lab[lab["area"] == "BL"]
    return PC.choose_w(Pp, dict(zip(lab["q"].astype(int), lab["y"].astype(int))), H.complete_bl(d, t), t)


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def model_version(name: str) -> dict:
    """model_version / feature_version / config_sha256 of a sealed model (registry spec section 2)."""
    code = {"iv2_lib": sha(EXP / "IMPROVE_V2" / "runner" / "iv2_lib.py"),
            "hr_lib": sha(EXP / "HISTORY_RETRAIN" / "runner" / "hr_lib.py")}
    if name in MODELS or name in LGBM_EXTRA:
        cols, first = (MODELS[name], H.FIRST_ORIGIN) if name in MODELS else LGBM_EXTRA[name]
        cfg = {"kind": "LightGBM stacked leads 1-15", "grid": H.GRID, "seed": H.SEED_LGBM, "first_origin": first}
    elif name in LOGIT_MODELS:
        cols, first = LOGIT_MODELS[name]
        cfg = {"kind": "L2 logistic C=1, median imputation, standardized, one model per lead", "first_origin": first}
    elif name in BLENDS:
        cols = ["C-b", "LOGIT"]
        cfg = {"kind": name, "w": 0.5} if name == "K1" else {"kind": name, "w_grid": PC.WGRID, "min_pairs": PC.WMIN_PAIRS,
                                                               "fallback": 0.5, "ties": "closest to 0.5, then lower"}
    elif name in CONSTANT:
        cols, cfg = [], {"kind": name, "p": CONSTANT[name]}
    else:
        cols, cfg = [], {"kind": name, "rule": "IMPROVE_V2 baseline (prospective_lib.baselines)"}
    feat = {"cols": cols, "code": code, **({"reversal": sha(ALLBASE / "runner" / "phase_c.py")} if name == "K3" else {})}
    return {"model_version": _h({"cols": cols, "cfg": cfg})[:16], "feature_version": _h(feat)[:16],
            "config_sha256": _h(cfg)}


def feature_cutoff(d, t: int) -> dict:
    """The newest period of each source available at O(t) (registry spec section 2)."""
    m0 = H.m0_of(t)

    def ym(ix):
        ix = [int(x) for x in ix if int(x) <= m0]
        return f"{max(ix) // 12}-{max(ix) % 12 + 1:02d}" if ix else None

    def qq(ix, lim):
        ix = [int(x) for x in ix if int(x) <= lim]
        return H.qs(max(ix)) if ix else None
    fo = d.idx.get((H.REGION, "food"))
    kn = H.known(d, t, "BL")
    e = pd.read_csv(E112_FILE)
    er = e[e["q"] <= t].sort_values("q")
    prods = [qq(s_.index, t - 1) for (g, _), s_ in d.prod.items() if g == H.REGION]
    tcs = [qq(s_.index, t) for s_ in d.tc.values()]
    return {"cpi_food_month": ym(fo.index) if fo is not None else None, "oni_month": ym(d.oni.index),
            "pinksheet_month": ym(d.pink.index), "production_quarter": max([x for x in prods if x], default=None),
            "typhoon_quarter_min_over_provinces": min([x for x in tcs if x], default=None),
            "news_quarter": H.qs(int(er["q"].iloc[-1])) if len(er) else None,
            "news_last_published": str(er["last_published"].iloc[-1]) if len(er) else None,
            "sws_newest_quarter": H.qs(kn[-1][0]) if kn else None, "sws_newest_published": kn[-1][2] if kn else None}


def generation_record(dry_run: bool) -> dict:
    import platform

    import lightgbm
    import sklearn
    run = Path(__file__).resolve().parent
    return {"python": platform.python_version(), "lightgbm": lightgbm.__version__, "sklearn": sklearn.__version__,
            "pandas": pd.__version__, "numpy": np.__version__, "scripts": {s: sha(run / s) for s in SCRIPTS},
            "phase_c": sha(ALLBASE / "runner" / "phase_c.py"), "allbase_prereg": check_allbase(),
            "k2_history": {"ALLBASE/out/fits.csv": sha(ALLBASE / "out" / "fits.csv"),
                           "NEWS_V2/out/forecasts.csv": sha(CB_DIR / "out" / "forecasts.csv")}, "dry_run": dry_run}


def origin_of_issue(issue: str) -> int:
    """O(t) = the first day of quarter t+1; the issue date must be the first day of a quarter."""
    d = pd.Timestamp(issue)
    assert d.day == 1 and d.month in (1, 4, 7, 10), f"{issue} is not the first day of a quarter"
    t = d.year * 4 + (d.month - 1) // 3 - 1
    assert H.issue(t) == d.strftime("%Y-%m-%d")
    return t


def code_commit() -> dict:
    def git(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = git("status", "--porcelain", "--", "aipheed-backend-aligned/experiments/IMPROVE_V2/runner",
                "aipheed-backend-aligned/experiments/HISTORY_RETRAIN/runner",
                "aipheed-backend-aligned/experiments/OPTION_1/runner",
                "aipheed-backend-aligned/experiments/SENIOR_REVIEW/runner",
                "aipheed-backend-aligned/experiments/NEW_MODEL/ALLBASE/runner",
                "aipheed-backend-aligned/experiments/NEW_MODEL/ALLBASE/PHASE_B_PREREGISTRATION.md")
    return {"commit": git("rev-parse", "HEAD"), "model_code_dirty": bool(dirty)}


def input_hashes() -> dict:
    files = sorted((EXP / "HISTORY_RETRAIN" / "data").glob("*.csv")) + sorted(H.LONG.glob("*.csv")) + [
        E112_FILE, EXP / "FIRI_V2_DATA_AUDIT" / "out" / "training_table_lead1.csv",
        EXP / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv"]
    return {str(p.relative_to(EXP)).replace("\\", "/"): sha(p) for p in files if p.exists()}


# ================================================================================================ table and fit
_G: dict = {}


def _init_rows():
    _G["d"] = H.load()
    _G["sc"] = V.intensities()


def _rows(t: int) -> list[dict]:
    return [r for r in V.rows_origin(_G["d"], t, _G["sc"]) if r["area"] == "BL"]


def build_table(origins: list[int], workers: int = 8) -> pd.DataFrame:
    """The BL rows of the IMPROVE_V2 pooled table, rebuilt from the current data files (iv2_lib.rows_origin)."""
    with Pool(workers, initializer=_init_rows) as pool:
        parts = pool.map(_rows, origins)
    T = pd.DataFrame([r for p in parts for r in p])
    return T


def fit_origin(S: pd.DataFrame, d, lab: pd.DataFrame, t: int, cols: list[str], first: int = H.FIRST_ORIGIN) -> pd.DataFrame:
    """OPTION_1 run_option1._origin (V.fit_base, BL, classification), test Leads 1-2, for the given column list; rows
    before `first` are dropped (LGBM-NLP: 2021-Q1, as OBJECTIVES_COMPLETION h3._fit)."""
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[(S["area"] == "BL") & (S["t"] >= first)]
    te = src[(src["t"] == t) & src["lead"].isin(LEADS)].copy()
    assert len(te) == len(LEADS), f"no table rows at origin {H.qs(t)}"
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"], te["cfg"] = np.nan, False, None
    if H.eligible(trb):
        cfg = H.lgbm_select(tr, cols, mono=False)
        m = H.LGBM(cfg, cols, False).fit(tr)
        te["p"], te["cfg"] = m.predict(te), cfg["id"]
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    te["n_train"] = len(tr)
    return te[["t", "lead", "q", "p", "fallback", "cfg", "n_train", "h_last", "sws_newest_published"]]


def baselines(d, lab: pd.DataFrame, t: int) -> dict:
    """PERSIST-SI and CLIM exactly as IMPROVE_V2 / OPTION_1 (CLIM also stands in when no reading is known)."""
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    ps = H.persist_t2(d, t)
    return {"persist_si": ps if not np.isnan(ps) else clim, "clim": clim, "clim_quarters": int(len(kb))}


def freshness(d, t: int) -> dict:
    """Has each source been refreshed to what the release rules allow at O(t)? (A stale source is not a source that
    disappeared: it means the data files were not updated before sealing.)"""
    m0 = H.m0_of(t)
    O = pd.Timestamp(H.issue(t))
    e = pd.read_csv(E112_FILE)
    er = e[e["q"] == t]
    out = {
        "cpi_region_food_month2": (H.REGION, "food") in d.idx and m0 in d.idx[(H.REGION, "food")].index,
        "cpi_region_rice_month2": (H.REGION, "rice") in d.idx and m0 in d.idx[(H.REGION, "rice")].index,
        "oni_month2": m0 in d.oni.index,
        "pinksheet_month2": m0 in d.pink.index,
        "production_quarter_t-1": any((t - 1) in s.index for (g, _), s in d.prod.items() if g == H.REGION),
        "typhoons_quarter_t": all(t in s.index for s in d.tc.values()),
        "e112_news_quarter_t": bool(len(er)) and (O - pd.Timestamp(er.iloc[0]["last_published"])).days
                                <= NEWS_FRESH_DAYS and pd.Timestamp(er.iloc[0]["last_published"]) < O,
    }
    return out


def labels_at(scoring_date: str, sws_file: Path = SWS_FILE) -> pd.DataFrame:
    """BL labels known on the scoring date (PLAN section 2): mean of non-commissioned rounds published before the date,
    for quarters that ended before it; y = H > 11.3. A round's quarter is the file's `quarter` (fieldwork start)."""
    s = pd.read_csv(sws_file)
    s = s[~s["commissioned"].astype(bool) & s["balance_luzon"].notna()]
    s = s[s["published"].astype(str).str[:10] < scoring_date]
    s["q"] = s["quarter"].map(H.qi)
    end = s["q"].map(lambda q: pd.Timestamp(H.issue(q)))          # O(q) = first day after quarter q
    s = s[end <= pd.Timestamp(scoring_date)]
    g = s.groupby("q").agg(H=("balance_luzon", "mean"), rounds=("balance_luzon", "size"),
                           mode=("mode", lambda x: ";".join(sorted(set(map(str, x))))),
                           base=("respondent_base", lambda x: ";".join(sorted(set(map(str, x)))))).reset_index()
    g["y"] = (g["H"] > H.H_LINE).astype(int)
    return g


# ================================================================================================ ledger
LEDGER_HEAD = ["# Prospective seal ledger (PROSPECTIVE_PLAN.md)", "",
               "One row per sealed file. Sealed files are never edited. The 2027-Q1 Lead-2 forecast sealed in "
               "OPTION_1 (`OPTION_1/sealed_prospective_REFNEWS.csv`, SHA-256 `cc1ff11b...5216`) counts by reference "
               "(PLAN section 1) and is verified at every scoring.", "",
               "| File | SHA-256 | Issue date | Targets | Sealed at | Code commit |", "|---|---|---|---|---|---|"]
ROW_RE = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \| (\d{4}-\d{2}-\d{2}) \| ([^|]+) \| ([^|]+) \| `?([0-9a-f]*)`? \|$")


SCRIPTS = ["prospective_lib.py", "seal_next.py", "score_prospective.py", "dryrun_test.py"]


def init_ledger(path: Path) -> dict:
    """Create the ledger once, before the first issue (PLAN section 7): the scripts' SHA-256, then the empty seal table
    (the seal table is the last block, so sealed rows are appended below it)."""
    assert not path.exists(), "the ledger already exists"
    run = Path(__file__).resolve().parent
    hs = {s: sha(run / s) for s in SCRIPTS}
    lines = LEDGER_HEAD[:4] + ["## Scripts (committed before the first issue date)", "",
                               "| Script | SHA-256 |", "|---|---|"] + [f"| {s} | {h} |" for s, h in hs.items()] + \
        ["", f"Protocol: `PROSPECTIVE_PLAN.md`, SHA-256 `{check_plan()}`.", "", "## Sealed files", ""] + LEDGER_HEAD[4:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hs


def read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line.strip())
        if m:
            out.append({"file": m.group(1), "sha256": m.group(2), "issue": m.group(3), "targets": m.group(4).strip(),
                        "sealed_at": m.group(5).strip(), "commit": m.group(6)})
    return out


def append_ledger(path: Path, row: dict):
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else list(LEDGER_HEAD)
    lines.append(f"| `{row['file']}` | `{row['sha256']}` | {row['issue']} | {row['targets']} | {row['sealed_at']} | "
                 f"`{row['commit']}` |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ================================================================================================ scoring helpers
def wilson(k: int, n: int, z: float = 1.6448536269514722) -> tuple[float, float] | None:
    """90% Wilson interval for a proportion."""
    if n == 0:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - h, c + h)


def independent_rules(g: pd.DataFrame, col: str) -> dict:
    """R1-R7 recomputed without the frozen code (SENIOR_REVIEW AUDIT.md D1): plain numpy / pandas."""
    g = g.sort_values("q").reset_index(drop=True)
    y, p = g["y"].to_numpy(int), g[col].to_numpy(float)
    c = (p >= .5).astype(int)
    acc = float((c == y).mean())
    tp, fp = int(((c == 1) & (y == 1)).sum()), int(((c == 1) & (y == 0)).sum())
    fn, tn = int(((c == 0) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    prec = tp / (tp + fp) if tp + fp else None
    bal = (rec + spec) / 2 if rec is not None and spec is not None else None
    accq = lambda x: float((((x[col] >= .5).astype(int)) == x["y"]).mean()) if len(x) else float("nan")  # noqa: E731
    qs_ = sorted(g["q"].unique())
    thirds = [accq(g[g["q"].isin(x)]) for x in np.array_split(np.array(qs_), 3)]
    loqo = min(accq(g[g["q"] != q]) for q in qs_) if len(qs_) > 1 else float("nan")
    r5 = []
    for b in ("PERSIST-SI_p", "CLIM_p"):
        dv = (g[col] - g["y"]) ** 2 - (g[b] - g["y"]) ** 2
        byq = {q: dv[g["q"] == q] for q in qs_}
        qv = g["q"].unique()
        rng = np.random.default_rng(SEED)
        bs = [float(pd.concat([byq[q] for q in rng.choice(qv, len(qv))]).mean()) for _ in range(B)]
        r5.append(float(dv.mean()) < 0 and float(np.mean(np.asarray(bs) >= 0)) < .10)
    base_low = float((y == 0).mean())
    base_ps = float(((g["PERSIST-SI_p"] >= .5).astype(int) == y).mean())
    return {"R1": len(qs_) >= 10 and len(g) >= 40, "R2": acc >= .75, "R3": bal is not None and bal >= .70,
            "R4": acc > base_low and acc > base_ps, "R5": all(r5),
            "R6": prec is not None and rec is not None and prec >= .6 and rec >= .6,
            "R7": bool(all(np.isfinite(thirds)) and min(thirds) >= .6 and np.isfinite(loqo) and loqo >= .7)}


def today() -> str:
    return date.today().isoformat()


def dumps(x) -> str:
    return json.dumps(x, indent=1, default=str)

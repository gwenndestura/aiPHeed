"""Shared code for the prospective protocol (../PROSPECTIVE_PLAN.md): plan check, table rebuild, the frozen REF+news /
REF refit at one origin, baselines, input freshness, labels, the seal ledger and an independent R1-R7 recomputation.

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
MODELS = {"REF+news": V.cols(False, True), "REF": V.cols(False, False)}
MAIN = "REF+news"
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
    return h


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
                "aipheed-backend-aligned/experiments/SENIOR_REVIEW/runner")
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


def fit_origin(S: pd.DataFrame, d, lab: pd.DataFrame, t: int, cols: list[str]) -> pd.DataFrame:
    """OPTION_1 run_option1._origin (V.fit_base, BL, classification), test Leads 1-2, for the given column list."""
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
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

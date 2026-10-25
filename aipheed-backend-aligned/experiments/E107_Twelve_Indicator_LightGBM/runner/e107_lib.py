"""E107 library (PROTOCOL.md): one LightGBM on the 12 aiPHeed indicator families, rolling-origin evaluation at Leads 1-4.

Time words. Quarters are integers qi = year*4 + quarter-1. Origin t: the latest quarter the forecast looks back from.
Issue date O(t): 00:00 on day 1 of quarter t+1. Lead k: the target quarter is t+k. Every feature of origin t is computed
from data published before O(t) (`L.Data.cut(t)` for CPI, SWS, production, LFS; `K.cut_extra` for typhoons, ENSO,
remittances, rice; the backend's own as-of functions for the PAGASA advisory, FSSI-v3 and the hunger outlook).

Targets.
  T43 (primary, Chapter I section 1.7 food-insecurity risk): province p, quarter q is HIGH iff Balance Luzon SWS
      involuntary hunger H_q > 11.3 AND (food CPI YoY_pq > P60_p OR food-minus-headline YoY_pq > gap P60_p); frozen
      2021-22 thresholds (E40 label_spec.json). A composite risk proxy, not a measured provincial prevalence.
  R (observed outcome check): quarter q is HIGH iff H_q > 11.3. The only observed food-insecurity outcome in the
      project (SWS Balance Luzon, regional: one value per quarter for all five provinces).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E107 = Path(__file__).resolve().parents[1]
EXP = E107.parent
REPO = EXP.parents[1]
BACKEND = REPO / "backend"
sys.path.insert(0, str(EXP / "E43_Five_Trigger_Risk" / "runner"))
import e43_lib as K  # noqa: E402

L, np, pd = K.L, K.np, K.pd
DATA_IN = E107 / "data_inputs"
# The three extra sources E43 reads from the untracked aipheed-backend-aligned/data/processed folder of the main checkout,
# copied byte-for-byte (data_inputs/SHA256SUMS.txt) so the run is reproducible from this branch alone.
K.EXTRA_FILES = {"climate": DATA_IN / "pagasa_climate.parquet", "ofw": DATA_IN / "bsp_macro.parquet",
                 "rice": DATA_IN / "psa_rice_prices.parquet"}

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)                                   # the backend's as-of functions read data/... relative paths
from app.ml.inference import climate_watch as CW  # noqa: E402
from app.ml.inference import firi as FI  # noqa: E402
from app.ml.inference import thesis_system as TS  # noqa: E402
from app.news import pipeline_v3 as P3  # noqa: E402

PROVS, NAMES, qi, qs = L.PROVS, L.NAMES, L.qi, L.qs
HUNGER_LINE = 11.3
LEADS = (1, 2, 3, 4)
FIRST_ORIGIN, LAST_ORIGIN = qi("2021-Q1"), qi("2026-Q3")
LAST_OUTCOME = qi("2026-Q3")
FINAL_BLOCK = [qi(q) for q in ("2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3")]   # PROTOCOL section 6: scored last, once
MIN_TRAIN_Q, MIN_TRAIN_HIGH, MIN_TRAIN_LOW = 6, 5, 5
SEED = 107

# ================================================================================================ indicator inventory
# The 12 indicator families are the FIRI v2 indicators (backend/app/ml/inference/firi.py LABELS). Each family enters
# LightGBM as the column(s) below. A1 is a forecast in FIRI; here it enters as its non-learned structural inputs (the
# CPI base-effect projection for the target quarter), because LightGBM is itself the food-price-pressure forecaster.
INVENTORY = [
    dict(code="A1", name="Food-price-pressure forecast", domain="A Affordability", source="PSA CPI food and all-items "
         "index, monthly (OpenSTAT 0012M4ACP22)", frequency="monthly", level="province",
         availability="months through month 2 of quarter t (published before O(t))",
         transformation="latest index held flat to the target months of t+k, YoY against the same months a year "
         "earlier; minus the province's frozen 2021-22 P60 food and gap thresholds (lead-specific)",
         missing="NaN if fewer than 2 base months are published or before 2021", columns=["A1_food", "A1_gap"]),
    dict(code="A2", name="Headline inflation above the usual level", domain="A Affordability",
         source="PSA CPI all-items YoY", frequency="monthly", level="province",
         availability="latest two published months (months 1-2 of t)",
         transformation="headline YoY minus the province's 2021-22 headline P60 (firi.HEADLINE_P60)",
         missing="NaN if either month is missing", columns=["A2"]),
    dict(code="A3", name="Wholesale rice price change", domain="A Affordability", source="PSA wholesale rice prices",
         frequency="quarterly", level="province", availability="quarter t-1",
         transformation="YoY % change t-1 vs t-5", missing="NaN before 2022-Q2 (no pre-2021 base)", columns=["A3"]),
    dict(code="V1", name="Poverty and population density", domain="V Vulnerability",
         source="PSA SAE 2021 poverty, POPCEN 2024 population, land area", frequency="static", level="province",
         availability="treated as a static structural profile at every origin (served FIRI Amendment 1; strictly "
                      "published 2025)", transformation="0.6 x min-max poverty + 0.4 x min-max density",
         missing="none", columns=["V1"]),
    dict(code="C1", name="PAGASA El Nino alert/advisory in force", domain="C Climate and food production",
         source="PAGASA ENSO alert system items", frequency="event", level="national",
         availability="items issued strictly before O(t)", transformation="1 if an El Nino Alert/Advisory is in "
         "force, else 0", missing="0 before the first item (2023-03-24; La Nina/none in 2021-22)", columns=["C1"]),
    dict(code="C2", name="Typhoons within 300 km", domain="C Climate and food production", source="IBTrACS tracks",
         frequency="quarterly", level="province", availability="quarter t (complete at O(t))",
         transformation="count", missing="NaN for 2026-Q3 (fetched mid-quarter)", columns=["C2"]),
    dict(code="C3", name="Palay/corn production drop", domain="C Climate and food production",
         source="PSA palay and corn production (OpenSTAT)", frequency="quarterly", level="province",
         availability="quarter t-1", transformation="-(lower of palay and corn YoY %, t-1 vs t-5)",
         missing="NaN before 2022-Q2", columns=["C3"]),
    dict(code="C4", name="Fisheries production drop", domain="C Climate and food production",
         source="PSA fisheries production", frequency="quarterly", level="province", availability="quarter t-1",
         transformation="-(fisheries YoY %, t-1 vs t-5)", missing="NaN before 2022-Q2", columns=["C4"]),
    dict(code="E1", name="Unemployment change (national)", domain="E Household economy", source="PSA LFS",
         frequency="monthly", level="national", availability="months of quarter t-1",
         transformation="quarter-mean unemployment rate t-1 minus t-5 (points)", missing="NaN before 2022-Q2",
         columns=["E1"]),
    dict(code="E2", name="Remittance decline (national)", domain="E Household economy",
         source="BSP OFW cash remittances (USD)", frequency="quarterly", level="national",
         availability="quarter t-1", transformation="-(YoY %, t-1 vs t-5)",
         missing="NaN before 2022-Q2 and after 2025-Q4 (series not acquired beyond)", columns=["E2"]),
    dict(code="N1", name="Food Stress Sentiment Index (FSSI-v3)", domain="N News warning signals",
         source="news headlines (RSS), XLM-RoBERTa zero-shot intensity", frequency="quarterly", level="province",
         availability="admitted headlines of quarter t published before O(t)",
         transformation="bias-weighted mean intensity (app.news.pipeline_v3.fssi_v3)",
         missing="NaN when fewer than 5 admitted headlines (status not SUFFICIENT); never zero", columns=["N1"]),
    dict(code="H1", name="Regional hunger outlook above 11.3%", domain="H Regional hunger",
         source="SWS Balance Luzon involuntary hunger, approved rounds", frequency="quarterly", level="region",
         availability="rounds posted before O(t)", transformation="P(hunger at t+k > 11.3) = 1 - Phi((11.3 - latest "
         "reading) / sigma_k), sigma_k = RMSE of the same rule's earlier lead-k errors (thesis_system.regional_hunger)",
         missing="none from 2021-Q3", columns=["H1"]),
]
FAMILIES = [f["code"] for f in INVENTORY]
COLUMNS = [c for f in INVENTORY for c in f["columns"]]
FAMILY_OF = {c: f["code"] for f in INVENTORY for c in f["columns"]}
DOMAIN_OF = {c: FAMILY_OF[c][0] for c in COLUMNS}
DOMAINS = ["A", "V", "C", "E", "N", "H"]
EXPECTED_FAMILIES = sorted(FI.LABELS)                # the authoritative list: the 12 FIRI indicators


# ================================================================================================ data
_CACHE: dict = {}


def data():
    """(d_full, extra) loaded once; both loaders refuse rows before 2021 (study-window rule)."""
    if "d" not in _CACHE:
        _CACHE["d"], _CACHE["x"] = L.load(), K.load_extra()
    return _CACHE["d"], _CACHE["x"]


def issue(t: int) -> str:
    return L.origin(t).date().isoformat()


def projection_bases(t: int, k: int) -> list[int]:
    """Base months (a year before each target month of t+k) that can be published at O(t): 2021-01 <= b <= m0."""
    return [m - 12 for m in L.target_months(t, k) if L.FIRST_YM <= m - 12 <= L.m0_of(t)]


def projection(d_cut: L.Data, t: int, k: int, p: str, commodity: str) -> float:
    """Mean YoY of the target months of t+k with the latest published index (month m0) held flat."""
    s = L._series(d_cut, p, commodity)
    m0 = L.m0_of(t)
    if m0 not in s.index:
        return float("nan")
    vals = [100 * (s[m0] / s[b] - 1) for b in projection_bases(t, k) if b in s.index]
    return float(np.mean(vals)) if len(vals) >= 2 else float("nan")


def _origin_rows(d_full, x_full, t: int) -> list[dict]:
    """Lead-independent raw values of every province at origin t."""
    th = L.e40_spec()
    base = K.features(d_full, x_full, [t]).set_index("province_code")
    hz = CW.hazard(issue(t))[0]
    vul = FI.vulnerability()
    rows = []
    for p in PROVS:
        b = base.loc[p]
        fn, gap = b["F_now"], b["gap_now"]
        crops = [v for v in (b["palay_yoy"], b["corn_yoy"]) if pd.notna(v)]
        fs = P3.fssi_v3(p, t)
        rows.append({
            "t": t, "province_code": p,
            "A2": (fn - gap) - FI.HEADLINE_P60[p] if pd.notna(fn) and pd.notna(gap) else np.nan,
            "A3": b["rice_whsl_yoy"], "V1": vul[p], "C1": 1.0 if hz else 0.0,
            "C2": np.nan if qs(t) in FI.INCOMPLETE_TYPHOON_QUARTERS else b["tc_count"],
            "C3": -min(crops) if crops else np.nan,
            "C4": -b["fish_yoy"] if pd.notna(b["fish_yoy"]) else np.nan,
            "E1": b["ur_yoy"], "E2": -b["remit_usd_yoy"] if pd.notna(b["remit_usd_yoy"]) else np.nan,
            "N1": fs["fssi"] if fs["status"] == "SUFFICIENT" else np.nan, "N1_articles": fs["n"],
            "_food_th": th["food"][p], "_gap_th": th["gap"][p]})
    return rows


def feature_table(k: int, origins=None, d_full=None, x_full=None) -> pd.DataFrame:
    """One row per (origin t, province) with the 13 columns of the 12 families for lead k."""
    if d_full is None:
        d_full, x_full = data()
    origins = list(range(FIRST_ORIGIN, LAST_ORIGIN + 1)) if origins is None else list(origins)
    key = ("X", k, tuple(origins), id(d_full))
    if key in _CACHE:
        return _CACHE[key].copy()
    out = []
    for t in origins:
        dc = d_full.cut(t)
        rh = TS.regional_hunger(t, k)
        for r in _origin_rows(d_full, x_full, t):
            p = r["province_code"]
            f = projection(dc, t, k, p, "food")
            h = projection(dc, t, k, p, "all_items")
            r.update(lead=k, issue_date=issue(t), target_q=t + k,
                     A1_food=f - r["_food_th"], A1_gap=(f - h) - r["_gap_th"],
                     H1=rh.get("probabilityAbove11_3", np.nan))
            out.append(r)
    X = pd.DataFrame(out).drop(columns=["_food_th", "_gap_th"])
    X[COLUMNS] = X[COLUMNS].astype(float)
    _CACHE[key] = X
    return X.copy()


# ================================================================================================ labels
def t43_frame(d) -> pd.DataFrame:
    """T43 per (province, quarter) for quarters with an approved SWS round and a complete CPI quarter in d."""
    return K.label_frame(d, "T43")[["province_code", "q", "y", "H", "F", "HL"]]


def r_frame(d) -> pd.DataFrame:
    """R per quarter: 1 if Balance Luzon hunger (mean of the quarter's approved rounds) > 11.3."""
    h = L.h_quarters(d)
    return h.assign(y=(h["H"] > HUNGER_LINE).astype(int))[["q", "y", "H"]]


def known_labels(t: int, target: str, d_full=None) -> pd.DataFrame:
    """Labels complete before O(t): every approved SWS round of the quarter posted, CPI quarter complete, q <= t-1."""
    d_full = d_full or data()[0]
    c = d_full.cut(t)
    full_n, cut_n = d_full.sws.groupby("q").size(), c.sws.groupby("q").size()
    complete = {q for q in cut_n.index if cut_n[q] == full_n.get(q, -1) and q <= t - 1}
    if target == "T43":
        lab = t43_frame(c)
        return lab[lab["q"].isin(complete)]
    lab = r_frame(c)
    lab = lab[lab["q"].isin(complete)]
    return _per_province(lab)


def outcomes(target: str, d_full=None) -> pd.DataFrame:
    """Observed labels as known now (evaluation outcomes), one row per province and quarter."""
    d_full = d_full or data()[0]
    if target == "T43":
        return t43_frame(d_full)
    return _per_province(r_frame(d_full))


def _per_province(r: pd.DataFrame) -> pd.DataFrame:
    """A regional label frame repeated for the five provinces (columns kept when empty)."""
    return pd.DataFrame([{"province_code": p, "q": q, "y": y, "H": h}
                         for q, y, h in zip(r["q"], r["y"], r["H"]) for p in PROVS],
                        columns=["province_code", "q", "y", "H"])


def training_rows(X: pd.DataFrame, t: int, k: int, target: str) -> pd.DataFrame:
    """(features of t', label of t'+k) with t'+k <= t-1 and the label complete before O(t)."""
    lab = known_labels(t, target)
    tr = X[(X["t"] < t) & (X["target_q"] <= t - 1)].rename(columns={"target_q": "q"})
    return tr.merge(lab[["province_code", "q", "y"]], on=["province_code", "q"], how="inner")


def eligible(tr: pd.DataFrame) -> bool:
    return (tr["q"].nunique() >= MIN_TRAIN_Q and int(tr["y"].sum()) >= MIN_TRAIN_HIGH
            and int((1 - tr["y"]).sum()) >= MIN_TRAIN_LOW)


def persistence(t: int, target: str) -> dict[str, tuple[int, int]]:
    """Province -> (latest label known at O(t), its quarter)."""
    lab = known_labels(t, target)
    out = {}
    for p, g in lab.groupby("province_code"):
        g = g.sort_values("q")
        out[p] = (int(g["y"].iloc[-1]), int(g["q"].iloc[-1]))
    return out


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, obj) -> None:
    Path(path).write_text(json.dumps(obj, indent=1, default=_js) + "\n", encoding="utf-8", newline="\n")


def _js(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not math.isfinite(float(o)) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))

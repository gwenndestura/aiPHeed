"""
Setup H + class weights: the four added input groups (palay/corn, rainfall/typhoon, regional GRDP) by province x issue quarter,
ported unchanged from the research builder (research_notes/aiPHeed_study_20261110/evidence/scripts/cand_build.py). Built only from
public files already in backend/data (no download).

    python -m app.hcw.inputs   -> data/hcw/out/cand_panel.parquet

Every value uses data released before the first day of the issue quarter (same release rules as the served inputs):
  PSA quarterly palay / corn production (OpenSTAT 2E4EVCP0): quarter usable 45 days after it ends (E137 rule).
  NASA POWER monthly rainfall at the province centroid: months ending 2 months before the issue date (served c_rain_anom_6m rule).
  IBTrACS WP best tracks: storm points before the issue date.
  PSA regional accounts, GRDP per capita at constant 2018 prices: year Y usable from Q3 of Y+1 (E154 rule used for regional consumption).
  PSA census population (2010, 2015): census year + 2.
Writes out/cand_panel.parquet and out/cand_coverage.csv. Reads no outcome.
"""
import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR
from app.e137 import features as F
from app.e147 import features as Fe
from app.e148 import panel as Pn
from app.e154 import model as E154

B = BACKEND_DIR / "data"
HERE = B / "hcw" / "out"
HERE.mkdir(parents=True, exist_ok=True)
keys = pd.read_parquet(B / "e148" / "out" / "gov_panel.parquet")["key"].unique()
base = pd.read_csv(B / "e158" / "out" / "oof.csv")[["key", "region"]].drop_duplicates("key")
REG = dict(zip(base["key"], base["region"]))


def quarterly(lab):
    a = F._quarterly("palay_corn_quarterly.csv", "Ecosystem/Croptype", (lab,))
    d = pd.read_csv(F.BACKEND_DIR / "data" / "e137" / "raw" / "y2023" / "psa" / "palay_corn_q_2020_2023.csv", encoding="utf-8-sig")
    d = d[d["Ecosystem/Croptype"] == lab].copy()
    d["k"] = d["Geolocation"].map(F.nospace)
    qc = [c for c in d.columns if c[:4].isdigit() and "Quarter" in c]
    d[qc] = d[qc].apply(pd.to_numeric, errors="coerce")
    b = d.groupby("k")[qc].sum(min_count=1)
    a = a.join(b[[c for c in b.columns if c not in a.columns]], how="outer")
    # 2026-11-13: quarters after 2023 from the monthly live PSA download of the same OpenSTAT table (2E4EVCP0), by crop. Without
    # this the by-crop inputs stopped at 2023-Q4 while the combined series (app.e147.features) already used the live file, so the
    # 2026-Q4 issue compared 2023 with 2022. The overlapping 2023 quarters agree exactly (checked 2026-11-13). Release timing is
    # unchanged: F._published_quarters still decides which quarters an issue may use.
    from app.e168 import live_data as LD
    p = LD._f("psa/palay_corn_q.csv")
    if p is not None:
        v = pd.read_csv(p, encoding="latin-1")
        v = v[v["Ecosystem/Croptype"] == lab].copy()
        v["k"] = v["Geolocation"].map(F.nospace)
        vc = [c for c in v.columns if c[:4].isdigit() and "Quarter" in c]
        v[vc] = v[vc].apply(pd.to_numeric, errors="coerce")
        lv = v.groupby("k")[vc].sum(min_count=1)
        new = [c for c in lv.columns if c not in a.columns and lv[c].notna().any()]
        a = a.join(lv[new], how="outer") if new else a
    return a


PAL, CORN = quarterly("Palay"), quarterly("Corn")
COLS = sorted(set(PAL.columns) | set(CORN.columns), key=lambda c: (int(c[:4]), int(c[-1])))
RAIN = {}
for k, s in F._rain().items():
    RAIN[k] = s.dropna()
for k, s in Fe._rain_late().items():
    old = RAIN.get(k)
    RAIN[k] = s.dropna() if old is None else pd.concat([old, s[s.index > old.index.max()]]).sort_index()
TR = pd.read_csv(F.RAW / "ibtracs" / "ibtracs.WP.list.v04r01.csv", skiprows=[1], usecols=["SID", "ISO_TIME", "LAT", "LON", "USA_WIND", "WMO_WIND"], low_memory=False)
TR["t"] = pd.to_datetime(TR["ISO_TIME"], errors="coerce")
for c in ("LAT", "LON", "USA_WIND", "WMO_WIND"):
    TR[c] = pd.to_numeric(TR[c], errors="coerce")
TR["w"] = TR["USA_WIND"].fillna(TR["WMO_WIND"])
TR = TR[(TR["t"] >= "1990-01-01") & TR["LAT"].between(2, 23) & TR["LON"].between(113, 131)]
GEO = F._geo()
GR = pd.read_csv(B / "e154" / "raw" / "regional_income_long.csv")
GR = GR[(GR["table"] == "grdp_pc") & GR["type of valuation"].str.contains("Constant")].copy()
# 2024-2025 GRDP per person, ESTIMATED from PSA's current total-GRDP release (app.hcw.grdp_extend); only years PSA has not yet
# published per person are added, so every value up to 2023 stays exactly as published.
_EXT = B / "hcw" / "raw" / "grdp_pc_2024_2025_estimated.csv"
if _EXT.exists():
    _e = pd.read_csv(_EXT)
    _e = _e[~_e["year"].isin(GR["year"].unique())]
    GR = pd.concat([GR, _e[GR.columns]], ignore_index=True)
GR["reg"] = GR["region"].map(lambda s: next((v for k, v in E154.REG.items() if k in s), None))
GR = GR.dropna(subset=["reg"]).pivot_table(index="year", columns="reg", values="value").pipe(np.log)
CEN = F._census()
import os
CUT = os.environ.get("CAND_CUTOFF")  # leakage test: every source truncated at this date; values for issue quarters starting on/before it must not change
if CUT:
    cut = pd.Timestamp(CUT)
    qend = lambda c: pd.Timestamp(year=int(c[:4]), month=3 * int(c[-1]), day=1) + pd.offsets.MonthEnd(0)
    PAL = PAL[[c for c in PAL.columns if qend(c) < cut]]
    CORN = CORN[[c for c in CORN.columns if qend(c) < cut]]
    COLS = [c for c in COLS if qend(c) < cut]
    RAIN = {k: s[s.index.to_timestamp(how="end") < cut] for k, s in RAIN.items()}
    TR = TR[TR["t"] < cut]
    GR = GR[GR.index < cut.year]


def storms(k):
    xy = GEO.get(k)
    if xy is None:
        return None
    d = TR[F._km(TR["LAT"].values, TR["LON"].values, xy[1], xy[0]) <= F.TC_RADIUS_KM]
    return d.groupby("SID").agg(t=("t", "min"), w=("w", "max")).reset_index()


rows = []
for key in keys:
    k = key.replace(" ", "")
    st = storms(k)
    rain = RAIN.get(k)
    reg = REG.get(key)
    for i in range(Pn.FIRST, Pn.LAST + 1):
        d = Pn.q_start(i)
        o = {"key": key, "qi": i}
        pub = F._published_quarters(COLS, d)
        for nm, tab in (("palay", PAL), ("corn", CORN)):
            if k in tab.index and len(pub) >= 8:
                v = tab.reindex(columns=pub).loc[k]
                l4, p4 = v[pub[-4:]].sum(min_count=4), v[pub[-8:-4]].sum(min_count=4)
                o[f"ag_{nm}_yoy"] = float(np.log(l4 / p4)) if l4 > 0 and p4 > 0 else np.nan
        if k in PAL.index and k in CORN.index and len(pub) >= 16:
            tot = PAL.reindex(columns=pub).loc[k].fillna(0) + CORN.reindex(columns=pub).loc[k].fillna(0)
            l4 = tot[pub[-4:]].sum()
            prev = [tot[pub[-4 * (j + 1) - 4: -4 * (j + 1)]].sum() for j in range(3)]
            o["ag_dev3y"] = float(np.log(l4 / np.mean(prev))) if l4 > 0 and np.mean(prev) > 0 else np.nan
            c = F._latest([2010, 2015], d)
            pop = CEN.at[k, c] if (c and k in CEN.index) else np.nan
            o["ag_pc"] = float(np.log(l4 / pop)) if l4 > 0 and pop == pop and pop > 0 else np.nan
        if rain is not None:
            last = (d - pd.Timedelta(days=30)).to_period("M") - 1
            m6, m12 = pd.period_range(last - 5, last, freq="M"), pd.period_range(last - 11, last, freq="M")
            if all(m in rain.index for m in m12):
                clim_m = {m: rain.reindex([pd.Period(year=y, month=m.month, freq="M") for y in range(2000, 2010)]).mean() for m in m12}
                o["vu_dry6"] = float(sum(rain[m] < 0.5 * clim_m[m] for m in m6))
                cl = [rain.reindex([pd.Period(year=y, month=m.month, freq="M") for m in m12]).mean() for y in range(2000, 2010)]
                o["vu_rain12"] = float((rain[m12].mean() - np.mean(cl)) / np.std(cl, ddof=1))
        if st is not None:
            win = st[(st["t"] < d) & (st["t"] >= d - pd.Timedelta(days=365))]
            o["vu_tc_wind"] = float(win["w"].fillna(0).sum() / 100.0)
            o["vu_tc_strong"] = float((win["w"] >= 64).sum())
            o["vu_tc_clim"] = float(((st["t"] >= "1990-01-01") & (st["t"] < "2010-01-01")).sum() / 20.0)
        y = E154.available_year(i)
        if reg in GR.columns and y in GR.index and (y - 1) in GR.index:
            o["hh_grdp_g"] = float(GR.at[y, reg] - GR.at[y - 1, reg])
            o["hh_grdp_rel"] = float(GR.at[y, reg] - GR.loc[y].mean())
        rows.append(o)
P = pd.DataFrame(rows)
P.to_parquet(HERE / ("cand_panel_cut.parquet" if CUT else "cand_panel.parquet"), index=False)
if CUT:
    raise SystemExit
cov = []
for c in [c for c in P.columns if c not in ("key", "qi")]:
    x = P[["key", "qi", c]].dropna()
    cov.append({"col": c, "first_issue_q": int(x["qi"].min()) if len(x) else None, "last_issue_q": int(x["qi"].max()) if len(x) else None, "provinces": x["key"].nunique(), "missing_2013_2021": round(float(P[(P["qi"] >= 8052) & (P["qi"] <= 8086)][c].isna().mean()), 3)})
print(pd.DataFrame(cov).to_string(index=False))
pd.DataFrame(cov).to_csv(HERE / "cand_coverage.csv", index=False, lineterminator="\n")

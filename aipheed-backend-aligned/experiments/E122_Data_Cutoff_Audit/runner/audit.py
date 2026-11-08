"""E122: 2021-2026 cutoff and point-in-time audit of FIRI3. Reads every source file, re-derives every change-type series
independently from 2021+ levels, runs FIRI3 (Amendment 1) and traces every score back to its observations.
No model is trained; FIRI v2, production and E118-E121 outputs are not modified.

    python audit.py
"""
from __future__ import annotations

import calendar
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
REPO = EXP.parent.parent
B = REPO / "backend"
sys.path.insert(0, str(B))
sys.path.insert(0, str(EXP / "E120_FIRI_Consolidated_Design" / "runner"))
from app.ml.inference import firi3 as F3      # noqa: E402
from app.ml.inference import firi as FI       # noqa: E402  (read only)
import e120 as E120                           # noqa: E402

P = E120.P
E118C = EXP / "E118_FAO_Data_Discovery" / "data" / "clean"
CUT_LO, CUT_HI = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-12-31")
ORIGINS = list(range(F3.START_Q, 2026 * 4 + 3))
NAME = {v: k for k, v in FI.PROVINCES.items()}
PROV_NAME = FI.PROVINCES


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def m2d(m):        # month index year*12+month-1 -> Timestamp
    return pd.Timestamp(int(m) // 12, int(m) % 12 + 1, 1)


def q2d(q):
    return pd.Timestamp(int(q) // 4, (int(q) % 4) * 3 + 1, 1)


# ------------------------------------------------------------------------------------------------ source registry
def e118(name):
    d = pd.read_csv(E118C / f"{name}.csv")
    f = d["freq"].iloc[0]
    return pd.DataFrame({"unit": d["unit"], "date": d["period"].map(m2d if f == "M" else q2d), "item": d["item"], "value": d["value"]}), f


def src_frames():
    """id -> (frame with unit, date, value[, item], meta)."""
    S = {}

    def put(i, df, **meta):
        S[i] = (df, meta)

    y = pd.read_csv(P.INPUTS["cpi_yoy_prov"], dtype={"province_code": str})
    put("S01", pd.DataFrame({"unit": y["province_code"].map(PROV_NAME), "date": pd.to_datetime(y["reference_month"] + "-01"), "value": y["yoy_pct"], "item": y["commodity"]}),
        name="Provincial CPI year-on-year (food, all items), PSA-published", file=P.INPUTS["cpi_yoy_prov"], org="PSA (OpenSTAT 0012M4ACP23)", geo="province (5)", freq="monthly",
        used=True, indicator="FMA", features="FMA_food_cpi; FMA_headline_cpi", pub="day 10 of m+1; archived PSA release for 32 province-months (ledger V1/V2)", pub_verified="partial")
    c = pd.read_csv(P.INPUTS["cpi_region_index"])
    put("S02", pd.DataFrame({"unit": c["geolocation"], "date": c["ym"].map(m2d), "value": c["value"], "item": c["commodity_description"]}),
        name="CPI index (2018=100) by region incl. Region IV-A", file=P.INPUTS["cpi_region_index"], org="PSA (OpenSTAT 0012M4ACP22)", geo="national, regions",
        freq="monthly", used=True, indicator="FMA", features="FMA_food_cpi_R; FMA_headline_cpi_R", pub="day 10 of m+1 (rule)", pub_verified="no")
    led = pd.read_csv(P.INPUTS["ledger"], dtype=str)
    put("S03", pd.DataFrame({"unit": led["province"], "date": pd.to_datetime(led["reference_month"] + "-01"), "value": 1.0}),
        name="PSA CPI release-date ledger (availability evidence)", file=P.INPUTS["ledger"], org="aiPHeed (archived PSA releases)", geo="province (5)", freq="monthly",
        used=True, indicator="FMA", features="availability of FMA_food_cpi / FMA_headline_cpi", pub="archive capture dates", pub_verified="for V1/V2 rows")
    r = pd.read_parquet(P.INPUTS["rice_whsl"])
    put("S04", pd.DataFrame({"unit": r["province_name"], "date": r["quarter"].map(lambda s: q2d(F3.qindex(s))), "value": r["price_php_per_kg"]}),
        name="Wholesale rice price (well-milled), quarterly", file=P.INPUTS["rice_whsl"], org="PSA", geo="province (5)", freq="quarterly", used=True, indicator="FMA",
        features="FMA_rice_wholesale", pub="start of q+2 (rule)", pub_verified="no")
    for i, n, feats, ind, used in (("S05", "retail_poultry", "FMA_chicken", "FMA", True), ("S06", "retail_livestock", "FMA_pork", "FMA", True),
                                   ("S07", "retail_fish", "FMA_tilapia", "FMA", True), ("S08", "farmgate_cereals", "FMA_rice_R", "FMA", True),
                                   ("S09", "prod_palay_corn", "AFP_palay; AFP_corn; AFP_palay_R; AFP_corn_R", "AFP", True),
                                   ("S10", "prod_vegetables_rootcrops", "AFP_vegetables; AFP_rootcrops; AFP_vegetables_R; AFP_rootcrops_R", "AFP", True),
                                   ("S11", "prod_fisheries", "AFP_fisheries; AFP_fisheries_R", "AFP", True), ("S12", "prod_chicken", "AFP_chicken", "AFP", True),
                                   ("S13", "prod_livestock", "AFP_livestock", "AFP", True),
                                   ("S14", "nasa_power_monthly", "CEC_rain_departure; CEC_heat; CEC_rain_departure_R; CEC_heat_R", "CEC", True),
                                   ("C01", "cpi_bottom30_yoy", "(context) bottom-30% CPI", "FMA", False), ("C02", "retail_cereals", "(alternative) retail rice", "FMA", False),
                                   ("C03", "wholesale_cereals", "(excluded) corngrits", "FMA", False), ("C04", "wholesale_fish", "(excluded) wholesale fish", "FMA", False),
                                   ("C05", "prod_aquaculture", "(alternative) aquaculture", "AFP", False), ("C06", "retail_fruit_veg", "(profile) vegetable prices", "FMA", False),
                                   ("C07", "retail_leafy_veg", "(profile) vegetable prices", "FMA", False), ("C08", "retail_rootcrops", "(profile) root-crop prices", "FMA", False),
                                   ("C09", "farmgate_livestock_household", "(profile) farmgate hog", "FMA", False), ("C10", "cpi_bottom30_index", "(context) bottom-30% CPI index", "FMA", False)):
        df, f = e118(n)
        put(i, df, name=f"E118 {n}", file=E118C / f"{n}.csv", org="PSA OpenSTAT (NASA POWER for nasa_power_monthly)" if n != "nasa_power_monthly" else "NASA POWER",
            geo="province (5) + Region IV-A" if "Region IV-A" in set(df["unit"]) else "province (5)", freq="monthly" if f == "M" else "quarterly", used=used, indicator=ind,
            features=feats, pub=("first day of m+2 (rule)" if n == "nasa_power_monthly" else "day 15 of m+1 (rule)" if f == "M" else "start of q+2 (rule)"), pub_verified="no")
    pf = pd.read_csv(P.INPUTS["profile"])
    put("S15", pd.DataFrame({"unit": pf["province"], "date": pf["t"].map(q2d), "value": pf["C2_tc_local_100km"]}),
        name="Tropical cyclones within 100 km (from IBTrACS tracks)", file=P.INPUTS["profile"], org="NOAA IBTrACS via corrected pipeline", geo="province (5)", freq="quarterly",
        used=True, indicator="CEC", features="CEC_cyclones_100km", pub="start of q+1 (real-time tracks)", pub_verified="yes")
    par = pd.read_csv(P.INPUTS["par"])
    put("S16", pd.DataFrame({"unit": "PHILIPPINES", "date": par["q"].map(q2d), "value": par["tc_par"]}), name="Tropical cyclones in PAR", file=P.INPUTS["par"],
        org="NOAA IBTrACS (E114)", geo="national", freq="quarterly", used=True, indicator="CEC", features="CEC_cyclones_R", pub="start of q+1", pub_verified="yes")
    lf = pd.read_csv(P.INPUTS["lfs"], encoding="latin-1")
    mon = {m: i for i, m in enumerate(calendar.month_name) if m}
    lf = lf[lf["Month"].isin(mon)]
    put("S17", pd.DataFrame({"unit": "PHILIPPINES", "date": [pd.Timestamp(int(y_), mon[m], 1) for y_, m in zip(lf["Year"], lf["Month"])],
                             "value": pd.to_numeric(lf["Unemployment Rate Both sexes"], errors="coerce")}),
        name="LFS unemployment rate, national, monthly", file=P.INPUTS["lfs"], org="PSA LFS", geo="national", freq="monthly", used=True, indicator="EHS",
        features="EHS_unemployment_change_R", pub="first day of m+3 (rule)", pub_verified="no")
    rm = pd.read_csv(P.INPUTS["remit"])
    put("S18", pd.DataFrame({"unit": "PHILIPPINES", "date": rm["q"].map(q2d), "value": rm["remit_usd_bn"]}), name="OFW cash remittances, national, quarterly",
        file=P.INPUTS["remit"], org="BSP via dated reports", geo="national", freq="quarterly", used=True, indicator="EHS", features="EHS_remittance_decline_R",
        pub="first dated report; else start of q+2", pub_verified="partial")
    e = pd.read_csv(P.INPUTS["emp_owner"])
    put("S19", pd.DataFrame({"unit": e["province"], "date": e["year"].map(lambda v: pd.Timestamp(int(v), 1, 1)), "value": e["unemployment_rate_pct"]}),
        name="Provincial annual unemployment / underemployment (owner file)", file=P.INPUTS["emp_owner"], org="PSA provincial LFS tables (owner-compiled)", geo="province (5)",
        freq="annual", used=True, indicator="EHS", features="EHS_unemployment_prov; EHS_underemployment_prov", pub="30 June of Y+1 (rule; no dates in file)", pub_verified="no")
    v = pd.read_csv(P.INPUTS["vuln"])
    put("S20", pd.DataFrame({"unit": v["province"], "date": pd.Timestamp(2021, 1, 1), "value": v["poverty_lgu_estimate"]}),
        name="LGU poverty incidence (PSA SAE 2021) and population (POPCEN 2024)", file=P.INPUTS["vuln"], org="PSA", geo="LGU (142) -> province", freq="static (2021 / 2024)",
        used=True, indicator="PSV", features="PSV_poverty", pub="2025-07-01 (V1 rule in firi.py)", pub_verified="provisional")
    st = pd.read_csv(P.INPUTS["stack"], dtype={"province_code": str})
    st1 = st[st["lead"] == 1]
    put("S21", pd.DataFrame({"unit": st1["province_code"].map(PROV_NAME), "date": st1["t"].map(q2d), "value": st1["N1"]}),
        name="FSSI-v3 provincial news index (from the 2021-01-01..2026-10-14 article corpus)", file=P.INPUTS["stack"], org="aiPHeed news pipeline v3", geo="province (5)",
        freq="quarterly", used=True, indicator="FIS", features="FIS_fssi", pub="articles published before the issue (dated)", pub_verified="yes")
    g = pd.read_csv(P.INPUTS["gdelt"])
    put("S22", pd.DataFrame({"unit": "PHILIPPINES", "date": pd.to_datetime(g["Date"], errors="coerce"), "value": g["Value"], "item": g["category"]}),
        name="GDELT DOC daily volume intensity by food category", file=P.INPUTS["gdelt"], org="GDELT Project", geo="national", freq="daily", used=True, indicator="FIS",
        features="FIS_shortage_news_R", pub="dated articles (start of q+1)", pub_verified="yes")
    o = pd.read_csv(P.INPUTS["oni"])
    put("C11", pd.DataFrame({"unit": "GLOBAL", "date": [pd.Timestamp(int(a), int(b), 1) for a, b in zip(o["end_year"], o["end_month"])], "value": o["oni"]}),
        name="NOAA ONI (context)", file=P.INPUTS["oni"], org="NOAA CPC", geo="global", freq="monthly", used=False, indicator="CEC", features="(context) ENSO", pub="day 10 of m+1", pub_verified="no")
    cl = pd.read_parquet(P.INPUTS["climate"])
    put("C12", pd.DataFrame({"unit": cl["province_name"], "date": [pd.Timestamp(int(a), (int(str(b)[-1]) - 1) * 3 + 1, 1) for a, b in zip(cl["year"], cl["quarter"])],
                             "value": cl["tc_count"]}), name="Cyclones within 300 km (C2, alternative)", file=P.INPUTS["climate"], org="IBTrACS via PAGASA climate table",
        geo="province (5)", freq="quarterly", used=False, indicator="CEC", features="(alternative) C2_typhoons_300km", pub="start of q+1", pub_verified="yes")
    s = pd.read_csv(P.INPUTS["subsistence"], dtype={"province_code": str})
    put("C13", pd.DataFrame({"unit": s["province_code"].map(PROV_NAME), "date": s["reference_year"].map(lambda v: pd.Timestamp(int(v), 1, 1)), "value": s["subsistence_incidence_pct"]}),
        name="Subsistence incidence (profile)", file=P.INPUTS["subsistence"], org="PSA", geo="province (5)", freq="triennial", used=False, indicator="PSV",
        features="(profile) subsistence", pub="2024-08-15 (dated)", pub_verified="yes")
    put("C14", pd.DataFrame({"unit": ["BATANGAS", "CAVITE", "LAGUNA", "QUEZON", "RIZAL"], "date": pd.Timestamp(2023, 1, 1), "value": 1.0}),
        name="FIES 2023 expenditure groups (profile)", file=P.INPUTS["fies2023"], org="PSA FIES", geo="province (5)", freq="triennial", used=False, indicator="PSV",
        features="(profile) food share", pub="not in file", pub_verified="no")
    sw = pd.read_csv(P.INPUTS["sws_area"])
    put("T01", pd.DataFrame({"unit": "Balance Luzon", "date": sw["quarter"].map(lambda q_: q2d(F3.qindex(q_))), "value": sw["balance_luzon"]}),
        name="SWS hunger by area (TARGET; never a FIRI3 input)", file=P.INPUTS["sws_area"], org="Social Weather Stations", geo="Balance Luzon", freq="quarterly",
        used=False, indicator="outside FIRI3", features="(target) none", pub="published dates", pub_verified="yes")
    # raw news article stores behind FSSI-v3
    rows = []
    for p in (B / "data" / "news_e31" / "articles.jsonl", B / "data" / "news_e60" / "articles.jsonl"):
        if p.exists():
            for line in p.open(encoding="utf-8"):
                try:
                    a = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rows.append({"unit": "corpus", "date": pd.to_datetime((a.get("ph_date") or "")[:10], errors="coerce"), "value": 1.0, "file": p.name})
    if rows:
        nd = pd.DataFrame(rows)
        put("S23", nd, name="News article stores (E31 + E60) behind FSSI-v3", file=B / "data" / "news_e31" / "articles.jsonl", org="aiPHeed news collector",
            geo="Philippines (geocoded to province)", freq="daily", used=True, indicator="FIS", features="FIS_fssi (via pipeline_v3.admitted: 2021-01-01..2026-10-14)",
            pub="article publication date", pub_verified="yes")
    return S


# ------------------------------------------------------------------------------------------------ independent re-derivation
def q_from_monthly(df, how="mean", days=False):
    df = df[(df["date"] >= CUT_LO)].copy()
    if days:
        df["value"] = df["value"] * df["date"].map(lambda d: calendar.monthrange(d.year, d.month)[1])
    df["q"] = df["date"].dt.year * 4 + (df["date"].dt.month - 1) // 3
    g = df.groupby(["unit", "q"])["value"]
    out = g.agg(how).reset_index()
    out["n"] = g.size().values
    return out[out["n"] == 3].drop(columns="n").rename(columns={"q": "period"})


def yoy2021(q, pct=True):
    """YoY using only 2021+ quarters on both sides (the base must be in the frame)."""
    q = q[q["period"] >= F3.START_Q]
    b = q.assign(period=q["period"] + 4).rename(columns={"value": "base"})
    m = q.merge(b, on=["unit", "period"])
    with np.errstate(divide="ignore", invalid="ignore"):
        m["value"] = 100 * (m["value"] / m["base"] - 1) if pct else m["value"] - m["base"]
    return m[np.isfinite(m["value"])][["unit", "period", "value"]]


def anomaly2021(q):
    out = []
    for (u), g in q[q["period"] >= F3.START_Q].groupby("unit"):
        for r in g.itertuples():
            prev = g[(g["period"] < r.period) & (g["period"] % 4 == r.period % 4)]
            if len(prev):
                out.append({"unit": u, "period": r.period, "value": r.value - prev["value"].mean()})
    return pd.DataFrame(out)


def shadow(S):
    """Every scored change-type series re-derived from its level source with 2021+ data only."""
    R = {}
    df = S["S02"][0]
    for item, feat in (("01.1 - FOOD", "region_cpi_food_yoy_pct"), ("0 - ALL ITEMS", "region_cpi_headline_yoy_pct")):
        x = df[(df["unit"] == "Region IV-A (CALABARZON)") & (df["item"] == item) & (df["date"] >= CUT_LO)].sort_values("date").set_index("date")["value"]
        base = x.shift(12, freq="MS").reindex(x.index)                                    # 12 months earlier, 2021+ only
        m = pd.DataFrame({"unit": "Region IV-A", "date": x.index, "value": (100 * (x / base - 1)).values}).dropna()
        R[feat] = q_from_monthly(m)
    r = S["S04"][0].assign(period=lambda d: d["date"].dt.year * 4 + (d["date"].dt.month - 1) // 3)
    R["rice_wholesale_yoy_pct"] = yoy2021(r[["unit", "period", "value"]])
    for sid, pat, feat in (("S05", "FRESH CHICKEN, FULLY DRESSED, BROILER", "retail_chicken_yoy_pct"), ("S06", "FRESH PORK, KASIM", "retail_pork_yoy_pct"),
                           ("S07", "FRESH FISH, TILAPIA, MEDIUM", "retail_tilapia_yoy_pct"), ("S08", "Palay [Paddy] Other Variety", "farmgate_palay_yoy_pct")):
        d = S[sid][0]
        d = d[d["item"].str.upper().str.startswith(pat.upper())].dropna(subset=["value"])
        R[feat] = yoy2021(q_from_monthly(d))
    prod = S["S09"][0].assign(period=lambda d: d["date"].dt.year * 4 + (d["date"].dt.month - 1) // 3)
    for item, feat in (("Palay", "palay_production_yoy_pct"), ("Corn", "corn_production_yoy_pct")):
        R[feat] = yoy2021(prod[prod["item"].str.strip().str.upper() == item.upper()].groupby(["unit", "period"])["value"].sum(min_count=1).reset_index().dropna())
    v = S["S10"][0].assign(period=lambda d: d["date"].dt.year * 4 + (d["date"].dt.month - 1) // 3)
    v = v[~v["item"].str.startswith("..")]
    root = v["item"].map(lambda x: any(x.startswith(r_) for r_ in ("Camote", "Cassava", "Gabi [Taro]", "Potato", "Ubi", "Singkamas", "Tugi", "Arrowroot")) and "tops" not in x)
    for grp, sub in (("vegetables_only_production_yoy_pct", v[~root]), ("rootcrops_only_production_yoy_pct", v[root])):
        R[grp] = yoy2021(sub.groupby(["unit", "period"])["value"].sum(min_count=1).reset_index().dropna())
    for sid, sel, feat in (("S11", lambda d: d["item"].str.strip().str.upper() == "FISHERIES", "fisheries_production_yoy_pct"),
                           ("S12", lambda d: d["item"].str.strip().str.upper() == "CHICKEN", "chicken_production_yoy_pct"),
                           ("S13", lambda d: ~d["item"].str.startswith(".."), "livestock_production_yoy_pct")):
        d = S[sid][0].assign(period=lambda x: x["date"].dt.year * 4 + (x["date"].dt.month - 1) // 3)
        R[feat] = yoy2021(d[sel(d)].groupby(["unit", "period"])["value"].sum(min_count=1).reset_index().dropna())
    n = S["S14"][0]
    for par_, feat, how, days in (("PRECTOTCORR", "rainfall_anomaly_mm", "sum", True), ("T2M", "temperature_anomaly_c", "mean", False)):
        q = q_from_monthly(n[n["item"] == par_].dropna(subset=["value"]), how=how, days=days)
        prov = anomaly2021(q)
        tot = q.groupby("period").filter(lambda g: g["unit"].nunique() == 5)
        an_p = prov.groupby("period").filter(lambda g: g["unit"].nunique() == 5).groupby("period")["value"].mean().reset_index()
        R[feat] = pd.concat([prov, an_p.assign(unit="CALABARZON (mean of 5 province points)")])
    lf = S["S17"][0].dropna()
    lf = lf[lf["date"] >= CUT_LO].assign(period=lambda d: d["date"].dt.year * 4 + (d["date"].dt.month - 1) // 3)
    R["E1_unemployment_change_pp"] = yoy2021(lf.groupby(["unit", "period"])["value"].mean().reset_index(), pct=False)
    rm = S["S18"][0].assign(period=lambda d: d["date"].dt.year * 4 + (d["date"].dt.month - 1) // 3)
    R["E2_remittance_decline_pct"] = yoy2021(rm[["unit", "period", "value"]]).assign(value=lambda d: -d["value"])
    return R


# ------------------------------------------------------------------------------------------------ main
def main():
    proto_ok = sha(EXP / "E121_FIRI3_Implementation" / "E121_FIRI3_PROTOCOL.md") == F3.PROTOCOL_SHA256
    amend_ok = sha(ROOT / "E122_FIRI3_PROTOCOL_AMENDMENT_1.md") == F3.AMENDMENT_1_SHA256 == (HERE / "AMENDMENT_1_SHA256.txt").read_text().strip()
    assert proto_ok and amend_ok, "protocol / amendment hash mismatch"
    watched = [B / "app" / "ml" / "inference" / "firi.py", B / "data" / "thesis" / "firi2_history.csv", B / "data" / "thesis" / "firi2_reference.json"]
    before = {str(p.relative_to(REPO)): sha(p) for p in watched}
    S = src_frames()
    L, ann = E120.load()
    obs = L.assign(source=L["feature"] + " @ " + L["unit"])
    ann = ann.assign(source=ann["feature"] + " @ " + ann["unit"] + " (" + ann["ref"] + ")")
    clean, ann_c, log = F3.validate_inputs(obs, ann)
    RUN = F3.compute(obs, ann, ORIGINS)
    RUN2 = F3.compute(obs.sample(frac=1, random_state=7), ann, ORIGINS)
    deterministic = all(RUN[k].to_csv(index=False) == RUN2[k].to_csv(index=False) for k in ("features", "overall"))
    FS, IND, OV = RUN["features"], RUN["indicators"], RUN["overall"]

    # ---------------- 1. independent re-derivation vs the inputs FIRI3 consumes
    SH = shadow(S)
    rederive = []
    for feat, sh in SH.items():
        mine = L[L["feature"] == feat][["unit", "period", "value"]]
        units = set(sh["unit"]) & set(mine["unit"]) if len(sh) else set(mine["unit"])
        a = mine[mine["unit"].isin(units)].merge(sh[sh["unit"].isin(units)], on=["unit", "period"], how="outer", suffixes=("_pipeline", "_independent"), indicator=True)
        both = a[a["_merge"] == "both"]
        rederive.append({"series": feat, "units": "; ".join(sorted(units)), "pipeline_rows": int((a["_merge"] != "right_only").sum()),
                         "independent_rows": int((a["_merge"] != "left_only").sum()), "matched": int(len(both)),
                         "only_in_pipeline": int((a["_merge"] == "left_only").sum()), "only_independent": int((a["_merge"] == "right_only").sum()),
                         "max_abs_diff": float((both["value_pipeline"] - both["value_independent"]).abs().max()) if len(both) else None,
                         "pipeline_first_period": F3.qlabel(int(mine["period"].min())) if len(mine) else "",
                         "only_in_pipeline_periods": " ".join(sorted({F3.qlabel(int(p)) for p in a.loc[a["_merge"] == "left_only", "period"]}))})
    RD = pd.DataFrame(rederive)
    RD["agrees"] = (RD["only_in_pipeline"] == 0) & (RD["max_abs_diff"].fillna(0) < 1e-6)

    # ---------------- 2. dataset audit
    feats_by_series = {f.series: f.code for f in F3.FEATURES}
    ds = []
    for sid, (df, m) in S.items():
        d = df.dropna(subset=["date", "value"])                                         # empty cells (e.g. unreleased months) are not observations
        pre = d["date"] < CUT_LO
        post = d["date"] > CUT_HI
        el = d[~pre & ~post]
        units = sorted(set(map(str, el["unit"].dropna())))
        # missing periods inside the window (per unit, at the dataset's frequency)
        gaps = ""
        if m["freq"] in ("monthly", "quarterly") and len(el):
            step = "MS" if m["freq"] == "monthly" else "QS"
            per_unit = []
            for u, g in el.groupby("unit"):
                full = pd.date_range(g["date"].min(), g["date"].max(), freq=step)
                miss = len(set(full) - set(g.loc[g["value"].notna(), "date"]))
                if miss:
                    per_unit.append(f"{u}: {miss}")
            gaps = "; ".join(per_unit[:8]) + (" ..." if len(per_unit) > 8 else "")
        ingest = ""
        if "E118" in str(m["file"]):
            ingest = "2026-10-31 (E118 acquisition log)"
        elif "E114" in str(m["file"]):
            ingest = "2026-10-25 (E114 fetch log)"
        elif "E107" in str(m["file"]) and "fetched_at" in pd.read_parquet(m["file"]).columns:
            ingest = str(pd.read_parquet(m["file"])["fetched_at"].min())[:10] + " (fetched_at)"
        ds.append({"dataset_id": sid, "dataset": m["name"], "original_file": str(Path(m["file"]).relative_to(REPO)) if str(m["file"]).startswith(str(REPO)) else str(m["file"]),
                   "file_sha256": sha(m["file"]), "source_organization": m["org"], "geographic_coverage": m["geo"], "frequency": m["freq"],
                   "earliest_raw_observation": str(d["date"].min().date()) if len(d) else "", "latest_raw_observation": str(d["date"].max().date()) if len(d) else "",
                   "earliest_eligible_observation": str(el["date"].min().date()) if len(el) else "", "latest_eligible_observation": str(el["date"].max().date()) if len(el) else "",
                   "publication_rule": m["pub"], "publication_dates_verified": m["pub_verified"], "ingestion_date": ingest,
                   "pre2021_observations": int(pre.sum()), "post2026_observations": int(post.sum()), "eligible_2021_2026_observations": int(len(el)),
                   "excluded_observations": int(pre.sum() + post.sum()), "missing_periods_in_window": gaps or "none",
                   "units_in_window": "; ".join(units[:12]) + (" ..." if len(units) > 12 else ""), "used_in_firi3": m["used"], "indicator": m["indicator"],
                   "features": m["features"]})
    DS = pd.DataFrame(ds)

    # ---------------- 3. feature audit (current values, priors and comparison bases actually used)
    fa, trace_rows = [], {}
    for f in F3.FEATURES:
        sc = "provincial" if f.scope == "P" else "regional"
        units = list(F3.PROVINCES) if f.scope == "P" else [f.unit]
        rows_f = FS[FS["feature"] == f.code]
        scored = rows_f[rows_f["score"].notna()]
        if f.normalization == "rank5":
            a = ann_c[ann_c["feature"] == f.series]
            raw = ann[ann["feature"] == f.series]
            used_refs = sorted(set(scored["period"].astype(str)))
            fa.append({"feature": f.code, "indicator": f.indicator, "scope": sc, "source_dataset": f.dataset, "series": f.series,
                       "raw_observation_range": f"{raw['ref'].min()}..{raw['ref'].max()}" if len(raw) else "", "observations_used": "reference years " + ", ".join(used_refs),
                       "publication_dates_used": "; ".join(sorted(set(scored["avail_date"].astype(str)))), "earliest_observation_used": min(used_refs) if used_refs else "",
                       "latest_observation_used": max(used_refs) if used_refs else "", "n_observations_used": int(len(a[a["ref"].isin(used_refs)])),
                       "n_observations_excluded": int(len(raw) - len(a)), "excluded_detail": "", "geographic_level": "province (5)", "frequency": "annual",
                       "transformation": "none (level)", "lag_or_window": "latest published reference year (no lag, no window)",
                       "normalization": "cross-province mid-rank (5 values of the same year)", "historical_reference_observations": "the 5 provinces' values of the same year",
                       "earliest_underlying_period": min(used_refs) if used_refs else "", "pre2021_influence": bool(used_refs and min(used_refs) < "2021"),
                       "future_influence": bool((scored["avail_date"].astype(str) >= scored["issue_date"].astype(str)).any()),
                       "computable_with_eligible_data_only": bool(len(scored)), "first_scored_origin": scored["origin"].min() if len(scored) else "",
                       "scored_unit_origins": int(len(scored)), "status_detail": "; ".join(f"{k}: {v}" for k, v in rows_f["status"].value_counts().items())})
            for r in scored.itertuples():
                trace_rows[(sc, r.unit, r.t, f.code)] = {"earliest": f"{r.period}-Q1", "latest": f"{r.period}-Q4", "n": 5, "pub": r.status}
            continue
        o = clean[(clean["feature"] == f.series) & clean["unit"].isin(units)]
        raw = obs[(obs["feature"] == f.series) & obs["unit"].isin(units)]
        x = f.direction * (o["value"].abs() if f.transform == "abs" else o["value"])
        used_prior, used_cur, max_future = set(), set(), False
        for r in scored.itertuples():
            cur = F3.qindex(r.period)
            pr = o[(o["avail"].astype(str) < r.issue_date) & (o["period"] < cur)]
            used_prior |= set(zip(pr["unit"], pr["period"]))
            used_cur.add((r.unit, cur))
            if (pr["avail"].astype(str) >= r.issue_date).any() or r.avail_date >= r.issue_date:
                max_future = True
            base = 4 if f.series in F3.BASE_REQUIRED else 0
            pmin = int(pr["period"].min()) if len(pr) else cur
            trace_rows[(sc, r.unit, r.t, f.code)] = {"earliest": F3.qlabel(min(pmin, cur) - base), "latest": r.period, "n": int(len(pr)) + 1, "pub": r.status}
        allused = used_prior | used_cur
        per = [p for _, p in allused]
        base_q = 4 if f.series in F3.BASE_REQUIRED else 0
        und = (min(per) - base_q) if per else None
        excl = raw[~raw.index.isin(o.index)]
        rd = RD.set_index("series").loc[f.series] if f.series in set(RD["series"]) else None
        fa.append({"feature": f.code, "indicator": f.indicator, "scope": sc, "source_dataset": f.dataset, "series": f.series,
                   "raw_observation_range": f"{F3.qlabel(int(raw['period'].min()))}..{F3.qlabel(int(raw['period'].max()))}" if len(raw) else "",
                   "observations_used": f"{len(used_cur)} current + {len(used_prior - used_cur)} reference-only (unit-quarters)",
                   "publication_dates_used": f"{scored['avail_date'].min()}..{scored['avail_date'].max()}" if len(scored) else "",
                   "earliest_observation_used": F3.qlabel(min(per)) if per else "", "latest_observation_used": F3.qlabel(max(per)) if per else "",
                   "n_observations_used": int(len(allused)), "n_observations_excluded": int(len(excl)),
                   "excluded_detail": "; ".join(f"{F3.qlabel(int(p))}" for p in sorted(set(excl["period"])))[:120],
                   "geographic_level": "province (5)" if f.scope == "P" else f.unit, "frequency": "quarterly",
                   "transformation": ("|x|" if f.transform == "abs" else "x") + (" x -1" if f.direction < 0 else ""),
                   "lag_or_window": ("YoY vs the same quarter one year earlier (2021+ base)" if f.series.endswith(("_yoy_pct", "_drop")) or "change" in f.series or "decline" in f.series
                                     else "anomaly vs mean of earlier same-quarter 2021+ years" if "anomaly" in f.series else "none (level)") +
                                    ("; monthly -> 3-month mean" if f.dataset in ("D01", "D02", "D03", "D07", "D08", "D09", "D10", "D36", "D37", "D40") else ""),
                   "normalization": f"expanding mid-rank percentile, >= {F3.MIN_PRIOR} earlier available observations, current excluded",
                   "historical_reference_observations": f"{len(used_prior)} unit-quarters ({F3.qlabel(min(p for _, p in used_prior))}..{F3.qlabel(max(p for _, p in used_prior))})" if used_prior else "none",
                   "earliest_underlying_period": F3.qlabel(und) if und is not None else "", "pre2021_influence": bool(und is not None and und < F3.START_Q),
                   "future_influence": max_future, "computable_with_eligible_data_only": bool(len(scored)),
                   "independent_rederivation": ("agrees" if rd["agrees"] else "DISAGREES") if rd is not None else ("PSA-published (not re-derivable)" if f.dataset in ("D01", "D02") else "level series"),
                   "first_scored_origin": scored["origin"].min() if len(scored) else "", "scored_unit_origins": int(len(scored)),
                   "status_detail": "; ".join(f"{k}: {v}" for k, v in rows_f["status"].value_counts().items())})
    FA = pd.DataFrame(fa)
    FA["audit_status"] = np.where(FA["pre2021_influence"] | FA["future_influence"], "FAIL",
                                  np.where(FA["computable_with_eligible_data_only"], "PASS", "UNAVAILABLE (insufficient post-2021 history)"))
    FA.loc[FA["independent_rederivation"].eq("DISAGREES"), "audit_status"] = "FAIL"

    # ---------------- 4. publication audit
    pub_rule = {f.code: "" for f in F3.FEATURES}
    pub = []
    for f in F3.FEATURES:
        s = FS[(FS["feature"] == f.code) & FS["score"].notna()]
        st = s["status"].value_counts().to_dict()
        ver = float((s["status"] == "verified").mean()) if len(s) else None
        src_verified = None  # set below once the source is known
        cls = None
        src = {"D01": "S01/S03", "D02": "S01/S03", "D03": "S02", "D05": "S04", "D07": "S08", "D08": "S05", "D09": "S06", "D10": "S07", "D20": "S09", "D21": "S09",
               "D22": "S10", "D23": "S10", "D24": "S11", "D26": "S12", "D27": "S13", "D33": "S15", "D34": "S16", "D36": "S14", "D37": "S14", "D40": "S17", "D41": "S19",
               "D42": "S18", "D50": "S20", "D60": "S21/S23", "D62": "S22"}[f.dataset]
        first = src.split("/")[0]
        src_verified = S[first][1]["pub_verified"]
        cls = ("not scored" if not len(s) else
               "verified and eligible" if ver == 1.0 and src_verified == "yes" else
               "provisionally eligible (availability date from a documented rule or assumption, not an archived release)")
        pub.append({"feature": f.code, "indicator": f.indicator, "source_datasets": src, "observation_date": "period of the observation (quarter or reference year)",
                    "publication_rule_or_date": S[first][1]["pub"], "publication_verified": S[first][1]["pub_verified"],
                    "ingestion_date": DS.set_index("dataset_id").loc[first, "ingestion_date"] or "repository file (no fetch log)",
                    "issue_dates_scored": f"{s['issue_date'].min()}..{s['issue_date'].max()}" if len(s) else "", "scored_rows": int(len(s)),
                    "status_counts": "; ".join(f"{k}: {v}" for k, v in st.items()), "verified_share": round(ver, 3) if ver is not None else None,
                    "all_available_before_issue": bool((s["avail_date"].astype(str) < s["issue_date"].astype(str)).all()) if len(s) else None,
                    "classification": cls,
                    "note": ("retrospective: data ingested in 2026 after most issue dates; availability rests on the dated rule" if S[first][1]["pub_verified"] != "yes" else
                             "dated evidence before each issue")})
    PUB = pd.DataFrame(pub)

    # ---------------- 5. geographic audit
    geo = []
    region_of = {f.series: f.unit for f in F3.FEATURES if f.scope == "R"}
    for f in F3.FEATURES:
        if f.normalization == "rank5":
            a = ann_c[ann_c["feature"] == f.series]
            dup = int(a.duplicated(["unit", "ref"]).sum())
            geo.append({"feature": f.code, "scope": "provincial", "expected_units": "5 provinces", "units_found": "; ".join(sorted(a["unit"].unique())),
                        "wrong_units": "", "duplicates": dup, "identical_across_5_share": round(float(a.groupby("ref")["value"].agg(lambda s: s.nunique() == 1 and len(s) == 5).mean()), 3),
                        "equals_regional_or_national_share": None, "mixed_levels": False, "aggregation": "LGU -> province (population-weighted)" if f.code == "PSV_poverty" else "as published",
                        "audit_status": "PASS" if set(a["unit"]) == set(F3.PROVINCES) and not dup else "FAIL"})
            continue
        units = list(F3.PROVINCES) if f.scope == "P" else [f.unit]
        o = clean[(clean["feature"] == f.series) & clean["unit"].isin(units)]
        dup = int(o.duplicated(["unit", "period"]).sum())
        ident = eqreg = None
        if f.scope == "P":
            pv = o.pivot_table(index="period", columns="unit", values="value")
            full = pv.dropna()
            ident = round(float((full.nunique(axis=1) == 1).mean()), 3) if len(full) else None
            other = L[(L["feature"] == f.series) & L["unit"].isin(["Region IV-A", "PHILIPPINES"])]
            if len(other):
                rr = other.groupby("period")["value"].first()
                cm = full.join(rr.rename("reg"), how="inner")
                eqreg = round(float(cm.apply(lambda r: all(np.isclose(r[c], r["reg"]) for c in full.columns), axis=1).mean()), 3) if len(cm) else None
        used_units = set(FS[(FS["feature"] == f.code)]["series_unit"])
        geo.append({"feature": f.code, "scope": "provincial" if f.scope == "P" else "regional", "expected_units": "5 provinces" if f.scope == "P" else f.unit,
                    "units_found": "; ".join(sorted(o["unit"].unique())), "wrong_units": "; ".join(sorted(set(o["unit"]) - set(units))), "duplicates": dup,
                    "identical_across_5_share": ident, "equals_regional_or_national_share": eqreg,
                    "mixed_levels": bool(len(used_units) > 1), "aggregation": ("CALABARZON = mean of the 5 province centroid points (approved proxy)" if f.unit and f.unit.startswith("CALABARZON")
                                                                               else "national series labelled national" if f.unit == "PHILIPPINES" else "as published"),
                    "audit_status": "PASS"})
    GEO = pd.DataFrame(geo)
    GEO.loc[(GEO["duplicates"] > 0) | (GEO["wrong_units"].fillna("") != "") | GEO["mixed_levels"] | (GEO["equals_regional_or_national_share"].fillna(0) > .5), "audit_status"] = "FAIL"

    # ---------------- 6. traceability per score
    tr = []
    for r in OV.itertuples():
        cf = FS[(FS["scope"] == r.scope) & (FS["unit"] == r.unit) & (FS["t"] == r.t) & FS["score"].notna()]
        cf = cf[cf["indicator"].isin(str(r.indicators_used).split())] if r.status == "computed" else cf.iloc[0:0]
        tt = [trace_rows[(r.scope, r.unit, r.t, x)] for x in cf["feature"]]
        recomputed = None
        if r.status == "computed":
            ind = IND[(IND["scope"] == r.scope) & (IND["unit"] == r.unit) & (IND["t"] == r.t) & IND["available"]]
            # rebuild from feature scores: component means -> indicator means -> equal mean
            comp = cf.groupby(["indicator", "component"])["score"].mean().groupby("indicator").mean()
            recomputed = float(comp.mean())
        earliest = min((x["earliest"] for x in tt), default="")
        tr.append({"issue_date": r.issue_date, "origin": r.origin, "scope": r.scope, "unit": r.unit, "status": r.status, "firi3": r.firi3, "band": r.band,
                   "indicators_used": r.indicators_used, "indicators_missing": r.indicators_missing, "contributing_features": " ".join(cf["feature"]),
                   "earliest_observation_used": earliest, "latest_observation_used": max((x["latest"] for x in tt), default=""),
                   "n_observations_underlying": int(sum(x["n"] for x in tt)), "completeness": f"{r.indicators_available}/{r.indicators_defined}",
                   "verification_share": r.verification_share, "publication_status": "; ".join(f"{k}: {v}" for k, v in cf["status"].value_counts().items()),
                   "recomputed_from_features": recomputed,
                   "reproduces": (abs(recomputed - r.firi3) < 1e-12) if recomputed is not None else None,
                   "all_inputs_2021_plus": (earliest >= "2021") if earliest else None,
                   "all_inputs_available_before_issue": bool((cf["avail_date"].astype(str) < r.issue_date).all()) if len(cf) else None})
    TR = pd.DataFrame(tr)

    # ---------------- 7. violations: compare with the pre-amendment (E121) run
    v1 = pd.read_csv(EXP / "E121_FIRI3_Implementation" / "E121_FIRI3_OVERALL_RESULTS.csv")
    m = v1[["scope", "unit", "t", "firi3", "band", "indicators_used"]].merge(OV[["scope", "unit", "t", "firi3", "band", "indicators_used"]], on=["scope", "unit", "t"], suffixes=("_e121", "_amended"))
    m["changed"] = ~((m["firi3_e121"].isna() & m["firi3_amended"].isna()) | np.isclose(m["firi3_e121"].fillna(-9), m["firi3_amended"].fillna(-9), atol=1e-12))
    eff = {"rows": int(len(m)), "changed": int(m["changed"].sum()),
           "computable_e121": int(m["firi3_e121"].notna().sum()), "computable_amended": int(m["firi3_amended"].notna().sum()),
           "lost": int((m["firi3_e121"].notna() & m["firi3_amended"].isna()).sum()), "gained": int((m["firi3_e121"].isna() & m["firi3_amended"].notna()).sum()),
           "mean_abs_change_where_both": round(float((m["firi3_e121"] - m["firi3_amended"]).abs().dropna().mean()), 4),
           "max_abs_change_where_both": round(float((m["firi3_e121"] - m["firi3_amended"]).abs().dropna().max()), 4),
           "band_changes_where_both": int(((m["band_e121"] != m["band_amended"]) & m["firi3_e121"].notna() & m["firi3_amended"].notna()).sum()),
           "by_scope": {sc: {"changed": int(g["changed"].sum()), "computable_e121": int(g["firi3_e121"].notna().sum()), "computable_amended": int(g["firi3_amended"].notna().sum())}
                        for sc, g in m.groupby("scope")}}
    fs1 = pd.read_csv(EXP / "E121_FIRI3_Implementation" / "E121_FIRI3_FEATURE_RESULTS.csv")
    aff = fs1.merge(FS[["scope", "unit", "t", "feature", "score"]], on=["scope", "unit", "t", "feature"], suffixes=("_e121", "_amended"))
    aff = aff[~np.isclose(aff["score_e121"].fillna(-9), aff["score_amended"].fillna(-9), atol=1e-12)]
    feat_aff = aff.groupby("feature").size().to_dict()
    bad_rows = obs[obs["feature"].isin(F3.BASE_REQUIRED) & (obs["period"] < F3.FIRST_CHANGE_Q)]
    viol = [{"id": "V1", "type": "pre-2021 comparison base", "series": "cpi_food_yoy_pct; cpi_headline_yoy_pct",
             "records": f"{len(bad_rows)} province-quarter rows, 2021-Q1..2021-Q4 (PSA-published YoY of 2021 months vs 2020)",
             "source_file": str(Path(P.INPUTS["cpi_yoy_prov"]).relative_to(REPO)),
             "introduced_by": "E119 preprocess.build_series (provincial CPI 'PSA-published YoY' kept as a declared exception); passed by E120 load and firi3 v1 validate_inputs",
             "affected_features": "; ".join(f"{k} ({v} rows)" for k, v in feat_aff.items()),
             "affected_indicators": "FMA (provincial) as current values in 2021 quarters and as percentile reference values for later quarters",
             "affected_scores": f"{eff['by_scope'].get('provincial', {}).get('changed', 0)} provincial unit-origins changed; regional unaffected ({eff['by_scope'].get('regional', {}).get('changed', 0)})",
             "effect": f"mean |change| {eff['mean_abs_change_where_both']}, max {eff['max_abs_change_where_both']}, band changes {eff['band_changes_where_both']}; computable {eff['computable_e121']} -> {eff['computable_amended']}",
             "correction": "firi3 Amendment 1: change-type series admitted only from 2022-Q1 (base inside the window); rows rejected before scoring and normalization",
             "regression_test": "tests/unit/test_e122_cutoff.py::test_2021_yoy_rejected_before_normalization", "status": "corrected"}]
    for r in RD[~RD["agrees"]].itertuples():
        viol.append({"id": f"V-{r.series}", "type": "re-derivation mismatch", "series": r.series, "records": f"{r.only_in_pipeline} rows only in pipeline ({r.only_in_pipeline_periods}); max diff {r.max_abs_diff}",
                     "source_file": "", "introduced_by": "to investigate", "affected_features": "", "affected_indicators": "", "affected_scores": "", "effect": "", "correction": "", "regression_test": "", "status": "open"})
    warn = [{"id": "W1", "type": "warning (not a cutoff violation)", "series": "N1_fssi_v3", "records": "article intensities from a general pretrained multilingual NLI model (zero-shot, joeddav/xlm-roberta-large-xnli)",
             "source_file": "backend/app/ml/nlp/classifier.py", "introduced_by": "model weights pretrained on general text, not food-insecurity observations", "affected_features": "FIS_fssi",
             "affected_indicators": "FIS", "affected_scores": "", "effect": "", "correction": "none (no observation enters; disclosed)", "regression_test": "", "status": "disclosed"},
            {"id": "W2", "type": "warning", "series": "N1_fssi_v3", "records": "relevance rules (classifier v2) developed on a DEV annotation half of 2021-26 articles",
             "source_file": "backend/app/news/classifier_v2.py", "introduced_by": "design-time use of articles later than some issue dates (rule wording, not values)",
             "affected_features": "FIS_fssi", "affected_indicators": "FIS", "affected_scores": "", "effect": "not quantifiable", "correction": "none; disclosed", "regression_test": "", "status": "disclosed"},
            {"id": "W3", "type": "warning", "series": "poverty_incidence_popweighted_pct", "records": "PSA SAE 2021 is a model estimate whose auxiliary data include the 2020 census; POPCEN 2024 weights",
             "source_file": str(Path(P.INPUTS["vuln"]).relative_to(REPO)), "introduced_by": "PSA's estimation method (a published 2021 estimate, not a comparison computed here)",
             "affected_features": "PSV_poverty", "affected_indicators": "PSV", "affected_scores": "", "effect": "", "correction": "none; disclosed", "regression_test": "", "status": "disclosed"},
            {"id": "W4", "type": "warning", "series": "all", "records": "retrospective reconstruction: inputs ingested 2026-10 (current vintage); availability for most series rests on release rules",
             "source_file": "", "introduced_by": "", "affected_features": "all except cyclones, FSSI, GDELT, poverty", "affected_indicators": "all", "affected_scores": "all historical",
             "effect": "", "correction": "prospective snapshots from 2026-Q4", "regression_test": "", "status": "disclosed"}]
    VI = pd.DataFrame(viol + warn)

    # ---------------- checks
    fsc = FS[FS["score"].notna()]
    checks = {
        "protocol_and_amendment_hash": proto_ok and amend_ok, "deterministic": deterministic,
        "no_scored_period_before_2021": bool((fsc["period"].astype(str).str[:4].astype(int) >= 2021).all()),
        "no_change_series_before_2022": bool((fsc[fsc["series"].isin(F3.BASE_REQUIRED)]["period"].map(F3.qindex) >= F3.FIRST_CHANGE_Q).all()),
        "no_underlying_period_before_2021": bool((TR["all_inputs_2021_plus"].dropna()).all()) and not FA["pre2021_influence"].any(),
        "no_period_after_2026": bool((clean["period"] <= 2026 * 4 + 3).all()),
        "all_available_before_issue": bool((fsc["avail_date"].astype(str) < fsc["issue_date"].astype(str)).all()),
        "no_future_reference_values": not FA["future_influence"].any(),
        "independent_rederivation_agrees": bool(RD["agrees"].all()),
        "geography_pass": bool((GEO["audit_status"] == "PASS").all()),
        "every_score_reproduces": bool(TR["reproduces"].dropna().all()),
        "firi_v2_unchanged": before == {k: sha(REPO / k) for k in before},
        "sws_absent_from_inputs": not any(any(k in s.lower() for k in F3.FORBIDDEN) for s in set(clean["feature"])),
    }

    # ---------------- snapshots of the amended version (write once)
    snapdir = ROOT / "snapshots"
    snap_log = []
    for t in ORIGINS:
        o_ = F3.qlabel(t)
        d = snapdir / o_
        blobs = {"features.csv": FS[FS["t"] == t].to_csv(index=False, lineterminator="\n", float_format="%.12g").encode(),
                 "overall.csv": OV[OV["t"] == t].to_csv(index=False, lineterminator="\n", float_format="%.12g").encode()}
        files = {k: hashlib.sha256(b).hexdigest() for k, b in blobs.items()}
        if (d / "manifest.json").exists():
            assert json.loads((d / "manifest.json").read_text())["files"] == files, f"snapshot {o_} would change: refused"
            snap_log.append("verified unchanged")
            continue
        d.mkdir(parents=True)
        for k, b in blobs.items():
            (d / k).write_bytes(b)
        (d / "manifest.json").write_text(json.dumps({"origin": o_, "issue_date": F3.issue_date(t), "kind": "retrospective", "firi3_version": F3.VERSION,
                                                     "protocol_sha256": F3.PROTOCOL_SHA256, "amendment_1_sha256": F3.AMENDMENT_1_SHA256, "files": files,
                                                     "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=1))
        snap_log.append("written")

    out = {"E122_DATASET_CUTOFF_AUDIT.csv": DS, "E122_FEATURE_CUTOFF_AUDIT.csv": FA, "E122_PUBLICATION_DATE_AUDIT.csv": PUB, "E122_GEOGRAPHIC_AUDIT.csv": GEO,
           "E122_FINAL_SCORE_TRACEABILITY.csv": TR, "E122_CUTOFF_VIOLATIONS.csv": VI}
    for k, v in out.items():
        v.to_csv(ROOT / k, index=False, lineterminator="\n", float_format="%.10g")
    (ROOT / "out").mkdir(exist_ok=True)
    RD.to_csv(ROOT / "out" / "independent_rederivation.csv", index=False, lineterminator="\n")
    m.to_csv(ROOT / "out" / "e121_vs_amended.csv", index=False, lineterminator="\n", float_format="%.10g")
    FS.to_csv(ROOT / "out" / "firi3_amended_features.csv", index=False, lineterminator="\n", float_format="%.10g")
    OV.to_csv(ROOT / "out" / "firi3_amended_overall.csv", index=False, lineterminator="\n", float_format="%.10g")
    IND.assign(component_scores=IND["component_scores"].map(json.dumps)).to_csv(ROOT / "out" / "firi3_amended_indicators.csv", index=False, lineterminator="\n", float_format="%.10g")
    first_by_year = FA.assign(y=FA["first_scored_origin"].str[:4]).groupby("y")["feature"].agg(list).to_dict()
    summ = {"checks": checks, "log": log, "effect_vs_e121": eff, "first_scored_by_year": first_by_year, "snapshots": {k: snap_log.count(k) for k in set(snap_log)},
            "scores": {sc: {"computable": int(g["firi3"].notna().sum()), "possible": int(len(g)), "first": g.loc[g["firi3"].notna(), "origin"].min(),
                            "k": g.loc[g["firi3"].notna(), "indicators_available"].value_counts().sort_index().to_dict(),
                            "bands": g["band"].value_counts().to_dict()} for sc, g in OV.groupby("scope")},
            "datasets_with_pre2021": DS.loc[DS["pre2021_observations"] > 0, ["dataset_id", "dataset", "pre2021_observations"]].values.tolist()}
    json.dump(summ, open(ROOT / "out" / "summary.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 250)
    print(json.dumps(summ, indent=1, default=str))
    print(RD.to_string())
    print(FA[["feature", "earliest_observation_used", "earliest_underlying_period", "n_observations_used", "n_observations_excluded", "first_scored_origin", "pre2021_influence", "future_influence", "independent_rederivation", "audit_status"]].to_string())
    print(GEO[["feature", "duplicates", "identical_across_5_share", "equals_regional_or_national_share", "audit_status"]].to_string())
    print(DS[["dataset_id", "earliest_raw_observation", "latest_raw_observation", "pre2021_observations", "eligible_2021_2026_observations", "missing_periods_in_window"]].to_string())
    assert all(checks.values()), checks


if __name__ == "__main__":
    main()

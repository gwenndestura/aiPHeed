"""E119 preprocessing (E119_PREPROCESSING_PROTOCOL.md, hash checked). No training; raw inputs read-only (SHA-256 checked
before and after). Builds 2021+ cleaned observation tables per FIRI v2 indicator, as-of (point-in-time) regional and
provincial datasets, an annual provincial table, the unified 12-indicator dataset and all reports.

    python preprocess.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
X = ROOT.parent
REPO = X.parents[1]
B = REPO / "backend"
sys.path.insert(0, str(B))
from app.ml.inference import firi as FI  # noqa: E402

PROVS = ["Cavite", "Laguna", "Batangas", "Rizal", "Quezon"]
CODE = {v: k for k, v in FI.PROVINCES.items()}
START_Y, START_YM, START_Q = 2021, 2021 * 12, 2021 * 4
ORIGINS = list(range(2021 * 4, 2026 * 4 + 3))                     # 2021-Q1 .. 2026-Q3
TRIGGER = {"A1": "market_prices", "A2": "market_prices", "A3": "market_prices", "C4": "fish_production", "C1": "climate",
           "C2": "climate", "C3": "climate", "E1": "employment", "E2": "ofw_remittances", "N1": "news_nlp (other input)",
           "V1": "poverty_vulnerability (other input)", "H1": "regional_hunger (target component)"}
FAO = {"A1": "access; stability", "A2": "access", "A3": "access; availability", "V1": "access; utilization", "C1": "stability; availability",
       "C2": "stability; availability", "C3": "availability; stability", "C4": "availability", "E1": "access", "E2": "access",
       "N1": "stability (signals across dimensions)", "H1": "access; utilization (experienced hunger outcome)"}
E118 = X / "E118_FAO_Data_Discovery" / "data"
INPUTS = {
    "cpi_yoy_prov": X / "E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv",
    "cpi_region_index": X / "E114_Final_Run/data/cov_cpi.csv",
    "ledger": X / "LEAD2_FIVE_TRIGGER/data/psa_cpi_availability_ledger_20261029.csv",
    "profile": X / "CORRECTED_PIPELINE/out/provincial_profile.csv",
    "national": X / "CORRECTED_PIPELINE/out/national_context.csv",
    "remit": X / "CORRECTED_PIPELINE/out/remittances_quarterly_corrected.csv",
    "rice_whsl": X / "E107_Twelve_Indicator_LightGBM/data_inputs/psa_rice_prices.parquet",
    "climate": X / "E107_Twelve_Indicator_LightGBM/data_inputs/pagasa_climate.parquet",
    "stack": X / "LEAD2_FIVE_TRIGGER/data/stack_l2.csv",
    "oni": X / "E114_Final_Run/data/cov_oni.csv",
    "par": X / "E114_Final_Run/data/cov_ibtracs_par.csv",
    "lfs": X / "E114_Final_Run/data/cov_lfs.csv",
    "gdelt": X / "E114_Final_Run/data/cov_gdelt_doc.csv",
    "sws_area": X / "E114_Final_Run/data/sws_area_rounds_full.csv",
    "sws_backend": B / "data/inputs/sws_rounds.csv",
    "vuln": B / "data/inputs/lgu_vulnerability.csv",
    "subsistence": B / "data/inputs/psa_subsistence_population_2021_2023.csv",
    "fies2023": E118 / "raw/psa_fies_expenditure_groups_2023.csv",
    "emp_owner": X / "E116_FIRI_Domains/data/owner/calabarzon_provincial_employment_food_insecurity_relevant_2021_2026.csv",
    **{f"e118_{n}": E118 / f"clean/{n}.csv" for n in ("retail_cereals", "retail_poultry", "retail_livestock", "retail_fish", "farmgate_cereals",
                                                      "wholesale_cereals", "cpi_bottom30_yoy", "prod_palay_corn", "prod_fisheries",
                                                      "prod_aquaculture", "prod_vegetables_rootcrops", "prod_chicken", "prod_livestock", "nasa_power_monthly")},
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def qs(q):
    return f"{q // 4}-Q{q % 4 + 1}"


def ms(m):
    return f"{m // 12}-{m % 12 + 1:02d}"


def qstart(q):
    return date(q // 4, (q % 4) * 3 + 1, 1)


def issue(t):
    return qstart(t + 1).isoformat()


def mday(m, day):
    n = m + 1
    return date(n // 12, n % 12 + 1, day).isoformat()


def mfirst(m, ahead):
    n = m + ahead
    return date(n // 12, n % 12 + 1, 1).isoformat()


# ================================================================================================ observation series
# every series: DataFrame(period (quarter index), value, avail (ISO date), status, obs_label) per (feature, unit)
SERIES: dict = {}
META: dict = {}     # feature -> dict(indicator, role, unit_label, resolution, source, aggregation, rule, units)
OUTLIERS: list = []


def add(feature, unit, df, **meta):
    df = df[df["period"] >= START_Q].dropna(subset=["value"]).sort_values("period").reset_index(drop=True)
    SERIES[(feature, unit)] = df
    META.setdefault(feature, {**meta, "units": set()})["units"].add(unit)
    d = df["value"].diff().dropna()
    if len(d) > 8:
        mad = (d - d.median()).abs().median() * 1.4826
        if mad > 0:
            for i in d.index[(d - d.median()).abs() > 6 * mad]:
                OUTLIERS.append({"feature": feature, "unit": unit, "period": qs(int(df.loc[i, "period"])), "value": float(df.loc[i, "value"]),
                                 "change": float(d.loc[i]), "robust_z": float((d.loc[i] - d.median()) / mad), "action": "kept (flagged)"})


def monthly_to_q(m: pd.DataFrame, how="mean", days=False):
    """m: period (ym), value, avail, status. Quarterly value only when all 3 months exist (no partial quarters)."""
    m = m[m["period"] >= START_YM].copy()
    m["q"] = m["period"] // 3
    if days:
        m["value"] = m["value"] * m["period"].map(lambda p: (date(p // 12 + (p % 12 == 11), (p % 12 + 1) % 12 + 1, 1) - date(p // 12, p % 12 + 1, 1)).days)
    g = m.groupby("q")
    out = pd.DataFrame({"period": g.size().index, "n": g.size().values, "value": g["value"].agg(how).values,
                        "cv": (g["value"].std() / g["value"].mean()).values, "avail": g["avail"].max().values,
                        "status": g["status"].agg(lambda s: "verified" if (s == "verified").all() else "rule_unverified").values})
    out = out[out["n"] == 3].drop(columns="n")
    out["obs_label"] = out["period"].map(qs)
    return out


def yoy(df, pct=True):
    """YoY change from 2021+ values only: the value 4 quarters earlier must itself be a 2021+ observation."""
    d = df[df["period"] >= START_Q].set_index("period")                    # a pre-2021 value never serves as a base
    prev = d["value"].reindex(d.index - 4).to_numpy()
    out = d.copy()
    with np.errstate(divide="ignore", invalid="ignore"):
        v = (100 * (d["value"].to_numpy() / prev - 1)) if pct else (d["value"].to_numpy() - prev)
    out["value"] = np.where(np.isfinite(v), v, np.nan)              # base of 0: YoY undefined, left missing
    out["avail"] = [max(a, d["avail"].get(p - 4, a)) for p, a in zip(d.index, d["avail"])]
    return out.reset_index().dropna(subset=["value"])


def build_series():
    # ---------------- A1 / A2: provincial CPI YoY (PSA-published 2021+ observations), status from the release ledger
    y = pd.read_csv(INPUTS["cpi_yoy_prov"], dtype={"province_code": str})
    led = pd.read_csv(INPUTS["ledger"], dtype=str)
    ver = {(r["reference_month"], r["province"]): r["archive_release_date"] for _, r in led.iterrows() if r["class"] in ("V1", "V2")}
    for comm, feat in (("food", "cpi_food_yoy_pct"), ("all_items", "cpi_headline_yoy_pct")):
        for code, g in y[y["commodity"] == comm].groupby("province_code"):
            p = FI.PROVINCES[code]
            m = pd.DataFrame({"period": g["reference_month"].str[:4].astype(int) * 12 + g["reference_month"].str[5:7].astype(int) - 1,
                              "value": pd.to_numeric(g["yoy_pct"], errors="coerce")})
            m["avail"] = [ver.get((ms(x), p)) or mday(x, 10) for x in m["period"]]
            m["status"] = ["verified" if (ms(x), p) in ver else "rule_unverified" for x in m["period"]]
            add(feat, p, monthly_to_q(m), indicator="A1" if comm == "food" else "A2", role="direct (PSA-published YoY)",
                unit_label="% YoY (quarter mean of monthly)", resolution="province", source="PSA OpenSTAT 0012M4ACP23 (E40)",
                aggregation="quarterly mean of 3 published months", rule="day 10 of m+1; archived release where verified")
    # Region IV-A CPI index -> YoY computed here from 2021+ index only (so from 2022)
    c = pd.read_csv(INPUTS["cpi_region_index"])
    c = c[(c["geolocation"] == "Region IV-A (CALABARZON)") & (c["ym"] >= START_YM)]
    for comm, feat, ind in (("01.1 - FOOD", "region_cpi_food_yoy_pct", "A1"), ("0 - ALL ITEMS", "region_cpi_headline_yoy_pct", "A2")):
        g = c[c["commodity_description"] == comm].set_index("ym")["value"].sort_index()
        m = pd.DataFrame({"period": g.index, "value": 100 * (g.to_numpy() / g.reindex(g.index - 12).to_numpy() - 1)})
        m["avail"], m["status"] = m["period"].map(lambda x: mday(x, 10)), "rule_unverified"
        add(feat, "Region IV-A", monthly_to_q(m.dropna()), indicator=ind, role="direct (regional)", unit_label="% YoY", resolution="region",
            source="PSA OpenSTAT 0012M4ACP22 (E114)", aggregation="YoY of 2021+ index, quarterly mean", rule="day 10 of m+1")
    # ---------------- A3 rice: existing wholesale rice (quarterly) + new retail / farmgate / wholesale monthly
    r = pd.read_parquet(INPUTS["rice_whsl"])
    for p, g in r.groupby("province_name"):
        q = pd.DataFrame({"period": g["quarter"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1), "value": g["price_php_per_kg"]})
        q["avail"], q["status"], q["obs_label"] = q["period"].map(lambda x: qstart(x + 2).isoformat()), "rule_unverified", q["period"].map(qs)
        add("rice_wholesale_price_php_kg", p, q, indicator="A3", role="direct (served A3 source)", unit_label="PHP/kg", resolution="province",
            source="PSA wholesale rice prices (E107 parquet)", aggregation="quarterly as published", rule="quarter q at start of q+2")
        add("rice_wholesale_yoy_pct", p, yoy(add_ret(q)), indicator="A3", role="direct (A3 definition: YoY)", unit_label="% YoY", resolution="province",
            source="derived", aggregation="YoY of 2021+ quarterly price", rule="as source")
    for key, pat, feat, ind, role in (("e118_retail_cereals", "RICE, REGULAR-MILLED", "retail_rice_regular", "A3", "supporting (retail, r = 0.86 with A3)"),
                                      ("e118_farmgate_cereals", "Palay [Paddy] Other Variety", "farmgate_palay", "A3", "supporting (producer price)"),
                                      ("e118_retail_poultry", "FRESH CHICKEN, FULLY DRESSED, BROILER", "retail_chicken", "A1", "supporting (food price component)"),
                                      ("e118_retail_livestock", "FRESH PORK, KASIM", "retail_pork", "A1", "supporting (food price component)"),
                                      ("e118_retail_fish", "FRESH FISH, TILAPIA, MEDIUM", "retail_tilapia", "A1", "supporting (food price component)")):
        d = pd.read_csv(INPUTS[key])
        d = d[d["item"].str.upper().str.startswith(pat.upper())]
        for u, g in d.groupby("unit"):
            m = pd.DataFrame({"period": g["period"].astype(int), "value": g["value"]})
            m["avail"], m["status"] = m["period"].map(lambda x: mday(x, 15)), "rule_unverified"
            q = monthly_to_q(m.dropna())
            res = "region" if u == "Region IV-A" else "province"
            add(f"{feat}_price_php_kg", u, q[["period", "value", "avail", "status", "obs_label"]], indicator=ind, role=role, unit_label="PHP/kg (quarter mean)",
                resolution=res, source=f"PSA OpenSTAT ({key[5:]}, E118)", aggregation="quarterly mean of 3 published months", rule="day 15 of m+1 (rule)")
            add(f"{feat}_volatility_cv", u, q.assign(value=q["cv"])[["period", "value", "avail", "status", "obs_label"]], indicator=ind, role=role,
                unit_label="within-quarter CV", resolution=res, source="derived", aggregation="SD / mean of the 3 months", rule="as source")
            add(f"{feat}_yoy_pct", u, yoy(q[["period", "value", "avail", "status", "obs_label"]]), indicator=ind, role=role, unit_label="% YoY",
                resolution=res, source="derived", aggregation="YoY of 2021+ quarterly mean", rule="as source")
    b = pd.read_csv(INPUTS["e118_cpi_bottom30_yoy"])
    b = b[b["item"].str.strip() == "01.1 - FOOD"]
    for u, g in b.groupby("unit"):
        m = pd.DataFrame({"period": g["period"].astype(int), "value": g["value"]})
        m["avail"], m["status"] = m["period"].map(lambda x: mday(x, 10)), "rule_unverified"
        add("cpi_bottom30_food_yoy_pct", u, monthly_to_q(m.dropna()), indicator="A1", role="supporting (redundant: r = 0.94 with all-income food CPI)",
            unit_label="% YoY", resolution="province", source="PSA OpenSTAT 0022M4ABIR2 (E118)", aggregation="quarterly mean", rule="day 10 of m+1")
    # ---------------- C3 palay/corn, C4 fisheries, aquaculture, vegetables, livestock (quarterly as published)
    for key, item_pat, feat, ind, role, sign in (("e118_prod_palay_corn", "Palay", "palay_production_t", "C3", "direct", -1),
                                                 ("e118_prod_palay_corn", "Corn", "corn_production_t", "C3", "direct", -1),
                                                 ("e118_prod_fisheries", "FISHERIES", "fisheries_production_t", "C4", "direct", -1),
                                                 ("e118_prod_aquaculture", "AQUACULTURE", "aquaculture_production_t", "C4", "supporting (subsector of C4)", -1),
                                                 ("e118_prod_vegetables_rootcrops", None, "vegetables_rootcrops_production_t", None, "unassigned (availability support)", 1),
                                                 ("e118_prod_chicken", "CHICKEN", "chicken_production_t", None, "unassigned (availability support; 2023+)", 1),
                                                 ("e118_prod_livestock", None, "livestock_production_t", None, "unassigned (availability support; 2023+)", 1)):
        d = pd.read_csv(INPUTS[key])
        if item_pat == "AQUACULTURE":
            d = d[d["item"].str.strip().str.upper() == "TOTAL"]                 # published total, not total + sub-items
        elif item_pat:
            d = d[d["item"].str.strip().str.upper() == item_pat.upper()]
        else:
            d = d[~d["item"].str.startswith("..")]                               # top-level items only (".." rows are sub-items)
        for u, g in d.groupby("unit"):
            q = g.groupby("period")["value"].sum(min_count=1).reset_index()
            q.columns = ["period", "value"]
            q["period"] = q["period"].astype(int)
            q["avail"], q["status"], q["obs_label"] = q["period"].map(lambda x: qstart(x + 2).isoformat()), "rule_unverified", q["period"].map(qs)
            res = "region" if u == "Region IV-A" else "province"
            add(feat, u, q, indicator=ind, role=role, unit_label="metric tons (as published)", resolution=res, source=f"PSA OpenSTAT ({key[5:]}, E118)",
                aggregation="quarterly as published (sum over listed items where needed)", rule="quarter q at start of q+2 (rule)")
            add(feat.replace("_t", "_yoy_pct"), u, yoy(q), indicator=ind, role=role, unit_label="% YoY", resolution=res, source="derived",
                aggregation="YoY of 2021+ quarterly value", rule="as source")
    # C3 indicator itself: -(lower of palay and corn YoY); C4: -(fisheries YoY)
    for u in PROVS + ["Region IV-A"]:
        pal, cor = SERIES.get(("palay_production_yoy_pct", u)), SERIES.get(("corn_production_yoy_pct", u))
        if pal is not None and cor is not None:
            m = pal.merge(cor, on="period", suffixes=("_p", "_c"))
            v = pd.DataFrame({"period": m["period"], "value": -np.minimum(m["value_p"], m["value_c"]),
                              "avail": np.maximum(m["avail_p"], m["avail_c"]), "status": "rule_unverified", "obs_label": m["period"].map(qs)})
            add("C3_palay_corn_drop", u, v, indicator="C3", role="direct (FIRI C3 definition)", unit_label="% (minus lower YoY)",
                resolution="region" if u == "Region IV-A" else "province", source="derived", aggregation="-min(palay YoY, corn YoY)", rule="as source")
        f = SERIES.get(("fisheries_production_yoy_pct", u))
        if f is not None:
            add("C4_fisheries_drop", u, f.assign(value=-f["value"]), indicator="C4", role="direct (FIRI C4 definition)", unit_label="% (minus YoY)",
                resolution="region" if u == "Region IV-A" else "province", source="derived", aggregation="-fisheries YoY", rule="as source")
    # ---------------- C1 ENSO (national), C2 typhoons (provincial 300 km, national PAR), local 100 km from the corrected pipeline
    o = pd.read_csv(INPUTS["oni"])
    o["period"] = o["end_year"] * 12 + o["end_month"] - 1
    m = o[["period", "oni"]].rename(columns={"oni": "value"})
    m["avail"], m["status"] = m["period"].map(lambda x: mday(x, 10)), "rule_unverified"
    add("oni_quarter_mean", "PHILIPPINES (global index)", monthly_to_q(m)[["period", "value", "avail", "status", "obs_label"]], indicator="C1",
        role="supporting (ENSO state behind the C1 advisory)", unit_label="degC anomaly", resolution="global/national", source="NOAA CPC ONI (E114)",
        aggregation="quarterly mean", rule="day 10 of m+1 (rule)")
    st = pd.read_csv(INPUTS["stack"], dtype={"province_code": str})
    s1 = st[st["lead"] == 1].drop_duplicates("t")
    add("C1_el_nino_in_force", "PHILIPPINES", pd.DataFrame({"period": s1["t"], "value": s1["C1"], "avail": [issue(int(t)) for t in s1["t"]],
                                                            "status": "verified", "obs_label": "advisory state before issue"}).assign(avail=lambda d: [(date.fromisoformat(a) - timedelta(days=1)).isoformat() for a in d["avail"]]),
        indicator="C1", role="direct (served C1)", unit_label="0/1", resolution="national", source="PAGASA ENSO items (enso_context.py)",
        aggregation="state in force before the issue", rule="dated items")
    cl = pd.read_parquet(INPUTS["climate"])
    cl["period"] = cl["year"].astype(int) * 4 + cl["quarter"].astype(str).str[-1].astype(int) - 1
    for p, g in cl.groupby("province_name"):
        q = pd.DataFrame({"period": g["period"], "value": pd.to_numeric(g["tc_count"], errors="coerce")})
        q.loc[q["period"].map(qs).isin(FI.INCOMPLETE_TYPHOON_QUARTERS), "value"] = np.nan
        q["avail"], q["status"], q["obs_label"] = q["period"].map(lambda x: qstart(x + 1).isoformat()), "verified", q["period"].map(qs)
        add("C2_typhoons_300km", p, q, indicator="C2", role="direct (served C2)", unit_label="storms in quarter", resolution="province",
            source="IBTrACS via pagasa_climate.parquet", aggregation="count of distinct storms within 300 km", rule="quarter complete")
    pf = pd.read_csv(INPUTS["profile"], dtype={"province_code": str})
    for p, g in pf.groupby("province"):
        q = pd.DataFrame({"period": g["t"], "value": g["C2_tc_local_100km"]})
        q["avail"], q["status"], q["obs_label"] = q["period"].map(lambda x: qstart(x + 1).isoformat()), "verified", q["period"].map(qs)
        add("typhoons_local_100km", p, q, indicator="C2", role="supporting (local exposure)", unit_label="storms in quarter", resolution="province",
            source="IBTrACS raw (corrected pipeline)", aggregation="count within 100 km", rule="quarter complete")
    par = pd.read_csv(INPUTS["par"])
    q = pd.DataFrame({"period": par["q"], "value": par["tc_par"]})
    q["avail"], q["status"], q["obs_label"] = q["period"].map(lambda x: qstart(x + 1).isoformat()), "verified", q["period"].map(qs)
    add("typhoons_PAR", "PHILIPPINES", q[q["period"] <= 2026 * 4 + 1], indicator="C2", role="supporting (national exposure)", unit_label="storms in quarter",
        resolution="national", source="IBTrACS PAR box (E114)", aggregation="count", rule="quarter complete")
    # ---------------- climate support (unassigned): NASA POWER rainfall totals / temperature, anomalies vs earlier 2021+ years
    npw = pd.read_csv(INPUTS["e118_nasa_power_monthly"])
    for par_, feat, how, days in (("PRECTOTCORR", "rainfall_total_mm", "sum", True), ("T2M", "temperature_mean_c", "mean", False)):
        for u, g in npw[npw["item"] == par_].groupby("unit"):
            m = pd.DataFrame({"period": g["period"].astype(int), "value": g["value"]})
            m["avail"], m["status"] = m["period"].map(lambda x: mfirst(x, 2)), "rule_unverified"
            q = monthly_to_q(m, how=how, days=days)[["period", "value", "avail", "status", "obs_label"]]
            add(feat, u, q, indicator=None, role="unassigned (climate-domain support; no matching FIRI indicator)", unit_label="mm per quarter" if days else "degC",
                resolution="province (centroid point)", source="NASA POWER (E118)", aggregation="quarterly total" if days else "quarterly mean", rule="first day of m+2 (rule)")
            an = []
            for r in q.itertuples():
                prev = q[(q["period"] < r.period) & (q["period"] % 4 == r.period % 4)]
                if len(prev):
                    an.append({"period": r.period, "value": r.value - prev["value"].mean(), "avail": r.avail, "status": r.status, "obs_label": r.obs_label})
            add(feat.replace("_total_mm", "_anomaly_mm").replace("_mean_c", "_anomaly_c"), u, pd.DataFrame(an), indicator=None,
                role="unassigned (climate-domain support)", unit_label="vs mean of the same quarter in earlier 2021+ years", resolution="province (centroid point)",
                source="derived", aggregation="value minus earlier same-quarter mean (2021+)", rule="as source")
    for feat in ("rainfall_total_mm", "temperature_mean_c", "rainfall_anomaly_mm", "temperature_anomaly_c"):
        parts = [SERIES[(feat, p)] for p in PROVS if (feat, p) in SERIES]
        cat = pd.concat(parts).groupby("period").agg(value=("value", "mean"), n=("value", "size"), avail=("avail", "max"), status=("status", "first")).reset_index()
        cat = cat[cat["n"] == 5].drop(columns="n")
        cat["obs_label"] = cat["period"].map(qs)
        add(feat, "CALABARZON (mean of 5 province points)", cat, indicator=None, role="unassigned (regional proxy)", unit_label=META[feat]["unit_label"],
            resolution="region proxy", source="derived", aggregation="mean of the five province-centroid points", rule="as source")
    # ---------------- E1 unemployment (national monthly -> quarterly mean, change vs 4 quarters earlier, 2021+)
    lf = pd.read_csv(INPUTS["lfs"], encoding="latin-1")
    MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    lf = lf[lf["Month"].isin(MON)]
    m = pd.DataFrame({"period": lf["Year"].astype(int) * 12 + lf["Month"].map(MON.index), "value": pd.to_numeric(lf["Unemployment Rate Both sexes"], errors="coerce")}).dropna()
    m["avail"], m["status"] = m["period"].map(lambda x: mfirst(x, 3)), "rule_unverified"
    m = m[m["period"] >= START_YM]
    m["q"] = m["period"] // 3
    q = m.groupby("q").agg(value=("value", "mean"), avail=("avail", "max"), status=("status", "first")).reset_index().rename(columns={"q": "period"})
    q["obs_label"] = q["period"].map(qs)
    add("unemployment_rate_pct", "PHILIPPINES", q, indicator="E1", role="direct source", unit_label="% (quarter mean of survey months)", resolution="national",
        source="PSA LFS (E114)", aggregation="mean of available survey months in the quarter", rule="first day of m+3 (rule)")
    add("E1_unemployment_change_pp", "PHILIPPINES", yoy(q, pct=False), indicator="E1", role="direct (FIRI E1 definition)", unit_label="pp vs 4 quarters earlier",
        resolution="national", source="derived", aggregation="change vs same quarter a year earlier (2021+)", rule="as source")
    # ---------------- E2 remittances (national; first dated publication)
    rm = pd.read_csv(INPUTS["remit"])
    q = pd.DataFrame({"period": rm["q"], "value": rm["remit_usd_bn"],
                      "avail": [d if isinstance(d, str) else qstart(int(p) + 2).isoformat() for d, p in zip(rm["first_dated_publication"], rm["q"])],
                      "status": rm["status"], "obs_label": rm["quarter"]})
    add("remittances_usd_bn", "PHILIPPINES", q, indicator="E2", role="direct source", unit_label="USD bn", resolution="national",
        source="BSP via dated news reports (corrected pipeline)", aggregation="quarterly as reported", rule="first dated report; else start of q+2 (rule)")
    e2 = yoy(q)
    add("E2_remittance_decline_pct", "PHILIPPINES", e2.assign(value=-e2["value"]), indicator="E2", role="direct (FIRI E2 definition)", unit_label="% (minus YoY)",
        resolution="national", source="derived", aggregation="-YoY (2021+)", rule="as source")
    # ---------------- N1 news: provincial FSSI-v3 (served), national GDELT shares
    for code, g in st[st["lead"] == 1].groupby("province_code"):
        q = pd.DataFrame({"period": g["t"], "value": g["N1"], "articles": g["N1_articles"]})
        q["avail"], q["status"], q["obs_label"] = q["period"].map(lambda x: qstart(x + 1).isoformat()), "verified", q["period"].map(qs)
        add("N1_fssi_v3", FI.PROVINCES[code], q[["period", "value", "avail", "status", "obs_label"]], indicator="N1", role="direct (served N1)",
            unit_label="index", resolution="province", source="aiPHeed news corpus", aggregation="FSSI-v3 (needs >= 5 admitted articles)", rule="articles dated")
        add("N1_admitted_articles", FI.PROVINCES[code], q.assign(value=q["articles"])[["period", "value", "avail", "status", "obs_label"]], indicator="N1",
            role="supporting (coverage)", unit_label="count", resolution="province", source="aiPHeed news corpus", aggregation="count", rule="articles dated")
    gd = pd.read_csv(INPUTS["gdelt"])
    dcol = [c for c in gd.columns if c.lower().startswith("date")][0]
    gd["d"] = pd.to_datetime(gd[dcol], errors="coerce")
    gd = gd[gd["d"] >= "2021-01-01"]
    gd["period"] = gd["d"].dt.year * 4 + (gd["d"].dt.month - 1) // 3
    for cat_, g in gd.groupby("category"):
        q = g.groupby("period").agg(value=("value" if "value" in g else g.columns[2], "mean")).reset_index()
        q["avail"], q["status"], q["obs_label"] = q["period"].map(lambda x: qstart(x + 1).isoformat()), "verified", q["period"].map(qs)
        add(f"news_gdelt_{cat_}_share", "PHILIPPINES", q[q["period"] <= 2026 * 4 + 2], indicator="N1", role="supporting (national news signal)",
            unit_label="share of monitored articles", resolution="national", source="GDELT DOC (E114)", aggregation="quarterly mean of monthly shares", rule="quarter complete")
    # ---------------- H1 regional hunger: Balance Luzon readings (non-commissioned, from SWS tables)
    sw = pd.read_csv(INPUTS["sws_area"])
    sw = sw[sw["commissioned"] == False]  # noqa: E712
    sw["period"] = sw["quarter"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    rounds = sw[["period", "balance_luzon", "published"]].rename(columns={"balance_luzon": "value", "published": "avail"})
    rounds = rounds[rounds["period"] >= START_Q]
    return rounds


def add_ret(q):
    return q


# ================================================================================================ as-of extraction
def asof(feature, unit, iss):
    s = SERIES.get((feature, unit))
    if s is None or not len(s):
        return None
    h = s[s["avail"] < iss]
    if not len(h):
        return None
    r = h.iloc[-1]
    return r


def regional_dataset(rounds):
    feats_unit = [("region_cpi_food_yoy_pct", "Region IV-A"), ("region_cpi_headline_yoy_pct", "Region IV-A"),
                  ("farmgate_palay_yoy_pct", "Region IV-A"), ("C3_palay_corn_drop", "Region IV-A"), ("C4_fisheries_drop", "Region IV-A"),
                  ("aquaculture_production_yoy_pct", "Region IV-A"), ("vegetables_rootcrops_production_yoy_pct", "Region IV-A"),
                  ("C1_el_nino_in_force", "PHILIPPINES"), ("oni_quarter_mean", "PHILIPPINES (global index)"), ("typhoons_PAR", "PHILIPPINES"),
                  ("rainfall_total_mm", "CALABARZON (mean of 5 province points)"), ("rainfall_anomaly_mm", "CALABARZON (mean of 5 province points)"),
                  ("temperature_anomaly_c", "CALABARZON (mean of 5 province points)"),
                  ("E1_unemployment_change_pp", "PHILIPPINES"), ("unemployment_rate_pct", "PHILIPPINES"), ("E2_remittance_decline_pct", "PHILIPPINES")]
    feats_unit += [(f, "PHILIPPINES") for (f, u) in SERIES if f.startswith("news_gdelt_")]
    rows, pit = [], []
    rq = rounds.groupby("period").agg(y=("value", "mean"), target_published=("avail", "max")).reset_index()
    for t in ORIGINS:
        iss = issue(t)
        known = rounds[rounds["avail"] < iss].groupby("period")["value"].mean()
        for k in (1, 2):
            q = t + k
            row = {"origin": qs(t), "t": t, "issue_date": iss, "lead": k, "target_quarter": qs(q), "target_q": q,
                   "y_bl_hunger": rq.set_index("period")["y"].get(q, np.nan), "y_published": rq.set_index("period")["target_published"].get(q, None)}
            if len(known):
                row.update({"H1_bl_latest": float(known.iloc[-1]), "H1_bl_latest_quarter": qs(int(known.index[-1])),
                            "H1_bl_previous": float(known.iloc[-2]) if len(known) > 1 else np.nan,
                            "H1_bl_change": float(known.iloc[-1] - known.iloc[-2]) if len(known) > 1 else np.nan,
                            "H1_staleness_q": t - int(known.index[-1]), "H1_status": "verified"})
                pit.append({"dataset": "regional", "origin": qs(t), "issue_date": iss, "lead": k, "target_quarter": qs(q), "feature": "H1_bl_latest",
                            "unit": "Balance Luzon", "obs_period": qs(int(known.index[-1])), "avail_date": rounds[(rounds["period"] == known.index[-1]) & (rounds["avail"] < iss)]["avail"].max(),
                            "status": "verified"})
            else:
                row.update({"H1_bl_latest": np.nan, "H1_status": "not_collected (no 2021+ round published yet)"})
            for f, u in feats_unit:
                r = asof(f, u, iss)
                col = f
                row[col] = np.nan if r is None else float(r["value"])
                row[f"{col}__status"] = "missing (none available before issue)" if r is None else r["status"]
                row[f"{col}__period"] = None if r is None else r["obs_label"]
                if r is not None:
                    pit.append({"dataset": "regional", "origin": qs(t), "issue_date": iss, "lead": k, "target_quarter": qs(q), "feature": f, "unit": u,
                                "obs_period": r["obs_label"], "obs_q": int(r["period"]), "avail_date": r["avail"], "status": r["status"]})
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(pit)


PROV_FEATS = ["cpi_food_yoy_pct", "cpi_headline_yoy_pct", "rice_wholesale_yoy_pct", "retail_rice_regular_yoy_pct", "retail_rice_regular_price_php_kg",
              "retail_rice_regular_volatility_cv", "farmgate_palay_yoy_pct", "retail_chicken_yoy_pct", "retail_pork_yoy_pct", "retail_tilapia_yoy_pct",
              "cpi_bottom30_food_yoy_pct", "C2_typhoons_300km", "typhoons_local_100km", "C3_palay_corn_drop", "C4_fisheries_drop",
              "aquaculture_production_yoy_pct", "N1_fssi_v3", "N1_admitted_articles", "rainfall_total_mm", "rainfall_anomaly_mm",
              "temperature_anomaly_c", "vegetables_rootcrops_production_yoy_pct", "chicken_production_yoy_pct", "livestock_production_yoy_pct"]


def provincial_dataset():
    pf = pd.read_csv(INPUTS["profile"], dtype={"province_code": str})
    rows, pit = [], []
    for t in ORIGINS:
        iss = issue(t)
        for p in PROVS:
            pr = pf[(pf["t"] == t) & (pf["province"] == p)].iloc[0]
            row = {"province": p, "province_code": CODE[p], "origin": qs(t), "t": t, "issue_date": iss,
                   "A1_food_projection_asof": pr["A1_food_asof"], "A1_gap_projection_asof": pr["A1_gap_asof"], "A2_headline_above_usual_asof": pr["A2_asof"],
                   "A_status": pr["A_status"], "A_cpi_month": pr["cpi_newest_month"]}
            for c in ("A1_food_projection_asof", "A1_gap_projection_asof", "A2_headline_above_usual_asof"):
                if pd.notna(row[c]):
                    pit.append({"dataset": "provincial", "origin": qs(t), "issue_date": iss, "lead": None, "target_quarter": None, "feature": c, "unit": p,
                                "obs_period": pr["cpi_newest_month"], "avail_date": mday(int(pr["cpi_newest_month"][:4]) * 12 + int(pr["cpi_newest_month"][5:]) - 1, 10),
                                "status": "verified" if str(pr["A_status"]).startswith("verified") else "rule_unverified"})
            for f in PROV_FEATS:
                r = asof(f, p, iss)
                row[f] = np.nan if r is None else float(r["value"])
                row[f"{f}__status"] = "missing (none available before issue)" if r is None else r["status"]
                row[f"{f}__period"] = None if r is None else r["obs_label"]
                if r is not None:
                    pit.append({"dataset": "provincial", "origin": qs(t), "issue_date": iss, "lead": None, "target_quarter": None, "feature": f, "unit": p,
                                "obs_period": r["obs_label"], "obs_q": int(r["period"]), "avail_date": r["avail"], "status": r["status"]})
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(pit)


def annual_table():
    rows = []
    FI.VULN = INPUTS["vuln"]
    FI.vulnerability.cache_clear()
    vul = FI.vulnerability()
    for code, v in vul.items():
        rows.append({"province": FI.PROVINCES[code], "indicator": "V1", "feature": "V1_vulnerability_profile", "reference_year": "2021 SAE / 2024 POPCEN",
                     "value": v, "published": FI.V_AVAILABLE_FROM, "status": "verified (publication date)", "resolution": "province (from 142 LGUs)"})
    s = pd.read_csv(INPUTS["subsistence"], dtype={"province_code": str})
    for r in s.itertuples():
        rows.append({"province": FI.PROVINCES.get(r.province_code, r.province_code), "indicator": "V1", "feature": "subsistence_incidence_pct",
                     "reference_year": int(r.reference_year), "value": r.subsistence_incidence_pct, "published": r.publication_date,
                     "status": "verified (publication date)", "resolution": "province", "cv_pct": r.cv_pct})
    f = pd.read_csv(INPUTS["fies2023"], encoding="latin-1")
    f = f[f.iloc[:, 1].str.strip() == "Food and Non-Alcoholic Beverages"]
    for r in f.itertuples():
        name = str(r[1]).strip()
        prov = next((p for p in PROVS if name.upper().startswith(p.upper()) and name.upper() != "QUEZON CITY"), None)
        if prov:
            rows.append({"province": prov, "indicator": "V1", "feature": "fies_food_share_of_expenditure_pct", "reference_year": 2023, "value": float(r[3]),
                         "published": None, "status": "rule_unverified (publication date not in file)", "resolution": "province (Quezon excl. Lucena)"})
    e = pd.read_csv(INPUTS["emp_owner"])
    e = e[e["data_status"] != "Not yet available"]
    for r in e.itertuples():
        for c in ("unemployment_rate_pct", "underemployment_rate_pct"):
            v = getattr(r, c)
            derived = False
            if c == "unemployment_rate_pct" and pd.isna(v) and pd.notna(r.employment_rate_pct):
                v, derived = 100 - r.employment_rate_pct, True
            if pd.notna(v):
                rows.append({"province": r.province, "indicator": "E1", "feature": f"provincial_{c}_annual", "reference_year": int(r.year), "value": float(v),
                             "published": None, "status": "rule_unverified (assumed by 30 June of the next year)" + ("; derived 100 - employment rate" if derived else ""),
                             "resolution": "province, annual"})
    return pd.DataFrame(rows)


# ================================================================================================ reports
def leakage_checks(R, RP, P, PP, rounds):
    res = {}
    res["features_observed_before_target"] = bool((RP.dropna(subset=["obs_q"]).apply(lambda r: r["obs_q"] < int(r["target_quarter"][:4]) * 4 + int(r["target_quarter"][-1]) - 1, axis=1)).all())
    res["features_available_before_issue"] = bool((pd.concat([RP, PP])["avail_date"].astype(str) < pd.concat([RP, PP])["issue_date"].astype(str)).all())
    res["no_target_quarter_hunger_in_features"] = bool((R["H1_bl_latest_quarter"].dropna().map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1) < R.loc[R["H1_bl_latest_quarter"].notna(), "target_q"]).all())
    h = RP[RP["feature"].str.startswith("H1_")]
    res["sws_history_published_before_issue"] = bool(len(h) and (h["avail_date"].astype(str) < h["issue_date"].astype(str)).all())
    allq = pd.concat([v for v in SERIES.values()])
    res["no_pre2021_observation_in_any_series"] = bool((allq["period"] >= START_Q).all())
    published_yoy = {"cpi_food_yoy_pct", "cpi_headline_yoy_pct", "cpi_bottom30_food_yoy_pct"}   # PSA-published 2021 YoY (declared exception)
    derived = [s for (f, u), s in SERIES.items() if f not in published_yoy and f.endswith(("_yoy_pct", "_drop", "_change_pp", "_decline_pct"))]
    res["computed_changes_start_2022"] = bool(all((s["period"] >= START_Q + 4).all() for s in derived))
    res["no_imputation_or_zero_fill"] = "by construction: missing values stay NaN; monthly-to-quarter only with 3 published months"
    res["derived_stats_use_only_2021_plus_and_past"] = "YoY requires the 2021+ value 4 quarters earlier; anomalies use earlier same-quarter 2021+ values only; thresholds as-of (corrected pipeline)"
    return res


def main():
    proto = ROOT / "E119_PREPROCESSING_PROTOCOL.md"
    assert sha(proto) == (HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "protocol changed"
    before = {k: sha(v) for k, v in INPUTS.items()}
    rounds = build_series()
    R, RP = regional_dataset(rounds)
    P, PP = provincial_dataset()
    A = annual_table()
    lk = leakage_checks(R, RP, P, PP, rounds)
    assert lk["features_observed_before_target"] and lk["features_available_before_issue"] and lk["no_target_quarter_hunger_in_features"] and lk["no_pre2021_observation_in_any_series"] and lk["sws_history_published_before_issue"] and lk["computed_changes_start_2022"], lk
    after = {k: sha(v) for k, v in INPUTS.items()}
    assert before == after, "a raw input changed"
    R.to_csv(ROOT / "E119_REGIONAL_MODELING_DATASET.csv", index=False, lineterminator="\n", float_format="%.10g")
    P.to_csv(ROOT / "E119_PROVINCIAL_VULNERABILITY_DATASET.csv", index=False, lineterminator="\n", float_format="%.10g")
    A.to_csv(ROOT / "E119_PROVINCIAL_ANNUAL_INDICATORS.csv", index=False, lineterminator="\n", float_format="%.10g")
    pd.concat([RP, PP]).to_csv(ROOT / "E119_POINT_IN_TIME_VALIDATION.csv", index=False, lineterminator="\n")
    # per-indicator observation outputs
    for code in list(FI.LABELS) + ["UNASSIGNED"]:
        parts = []
        for (f, u), s in SERIES.items():
            ind = META[f]["indicator"] or "UNASSIGNED"
            if ind == code:
                parts.append(s.assign(feature=f, unit=u, indicator=ind, role=META[f]["role"], unit_label=META[f]["unit_label"],
                                      resolution=META[f]["resolution"], source=META[f]["source"], period_label=s["period"].map(qs)))
        d = OUT / "indicators" / code
        d.mkdir(parents=True, exist_ok=True)
        if code == "H1":                                                    # SWS rounds (Balance Luzon, non-commissioned), not a SERIES entry
            parts = [rounds.assign(feature="sws_bl_total_hunger", unit="Balance Luzon", indicator="H1", role="direct (published SWS round)", unit_label="%",
                                   resolution="region (Balance Luzon)", source="SWS tables (E114)", status="verified", period_label=rounds["period"].map(qs))]
        if code == "V1":                                                    # annual / static provincial table
            parts = [A[A["indicator"] == "V1"].assign(unit=A["province"], period_label=A["reference_year"].astype(str), unit_label="index 0-1")]
        if parts:
            pd.concat(parts).to_csv(d / "observations_clean.csv", index=False, lineterminator="\n", float_format="%.10g")
    pd.DataFrame(OUTLIERS).to_csv(OUT / "outlier_flags.csv", index=False, lineterminator="\n")
    json.dump({"inputs_sha256": before, "leakage": lk, "series": len(SERIES), "outliers_flagged": len(OUTLIERS),
               "regional_rows": len(R), "provincial_rows": len(P), "annual_rows": len(A)}, open(OUT / "manifest.json", "w"), indent=1, default=str)
    meta = pd.DataFrame([{"feature": f, **{k: v for k, v in m.items() if k != "units"}, "units": "; ".join(sorted(m["units"]))} for f, m in META.items()])
    meta.to_csv(OUT / "feature_meta.csv", index=False, lineterminator="\n")
    print(json.dumps({"series": len(SERIES), "regional": R.shape, "provincial": P.shape, "annual": A.shape, "outliers": len(OUTLIERS), "leakage": lk}, default=str, indent=1))


if __name__ == "__main__":
    main()

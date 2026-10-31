"""E118 inventory: one row per discovered dataset (acquired ones carry measured coverage from verify.py).

    python build_inventory.py   # ../FAO_FOOD_SECURITY_DATA_INVENTORY.csv and the five per-dimension / target CSVs
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/"

# id, dataset, indicator, FAO dimension, source, url, geography (provincial?), frequency, coverage, publication lag, access,
# direct FI measure?, target?, feature?, validation?, class, reason, acquired key (or "")
R = [
    ("T1", "SWS Social Weather Survey hunger", "% families with involuntary hunger (past 3 months)", "access/utilization (experienced hunger)", "Social Weather Stations",
     "https://www.sws.org.ph", "region (4 areas; Balance Luzon contains CALABARZON); not provincial", "quarterly (irregular rounds)", "1998-Q3 to 2026-Q3 (106 quarters)", "~2-8 weeks (dated releases)", "public releases",
     "yes (experienced hunger)", "yes, regional only", "history only", "yes (regional)", "A", "only repeated, time-varying direct measure; regional", "in repository (E114)"),
    ("T2", "FNRI ENNS / NNS household FIES", "moderate-or-severe food insecurity (FIES), % households", "access", "DOST-FNRI",
     "https://enutrition.fnri.dost.gov.ph", "provincial only in some rounds: ENNS 2018-19 pooled (selected provinces), ENNS 2021 (Batangas, Cavite, Lucena); NNS 2023 regional", "irregular (2018-19, 2021, 2023)", "<= 3 points per province", "~1 year", "reports public; microdata by request (FNRI)",
     "yes", "no (too few, irregular)", "no", "yes, cross-sectional", "D", "direct but irregular and not all provinces", "in repository (E87)"),
    ("T3", "CBMS 2024 (POPCEN-CBMS) FIES items", "household food insecurity experience (SDG 2.1.2)", "access", "PSA / LGUs",
     "https://psa.gov.ph/cbms", "barangay / city-municipal (all LGUs that ran CBMS)", "one window (Jul 2023-Jun 2024)", "1 point", "LGU preliminary results 2025", "request to PSA/LGUs (E87 request drafted, not sent)",
     "yes", "no (one window)", "no", "yes, cross-sectional at LGU level (strongest)", "D", "best provincial/LGU validation source, single round", ""),
    ("T4", "PSA subsistence incidence (food poverty)", "% families below the food threshold", "access", "PSA",
     PX + "DB/3D/0033C3DP030.px ; DB/1F/FS/0101F3DS05A.px", "province (Quezon excl. Lucena from 2018)", "triennial (1991, 2006, 2009, 2012, 2015, 2018, 2021, 2023)", "8 points per province", "~1 year (e.g. 2023 published 2024-08-15)", "public",
     "proxy (food poverty, not experienced food insecurity)", "no (8 points, CV up to 88% for Cavite)", "no (too infrequent)", "yes, long-run provincial check", "C", "provincial and repeated but triennial and imprecise", "subsistence_1991_2015, subsistence_2018_2021"),
    ("T5", "NNC Operation Timbang Plus", "underweight, stunting, wasting among children 0-59 months", "utilization", "National Nutrition Council / LGUs",
     "https://www.nnc.gov.ph (403 to automated access)", "province and municipality (LGU weighing)", "annual (Jan-Mar weighing)", "~2010-2025 (per NNC regional releases)", "~6-12 months", "request to NNC IV-A (FOI); news releases only for other regions",
     "yes (nutrition outcome; not food insecurity itself)", "candidate annual provincial target (utilization)", "no", "yes", "C", "repeated provincial outcome, annual; coverage gaps when LGUs do not submit", ""),
    ("T6", "PSA FIES (Family Income and Expenditure Survey)", "food share of family expenditure; income", "access", "PSA",
     PX + "DB/1E/IE/0071E3ATME0.px", "province (Quezon excl. Lucena)", "triennial (2018, 2021, 2023)", "3 recent points", "~1 year", "public tables; PUF on request",
     "proxy", "no", "no", "context", "C", "provincial, triennial", "fies_expenditure_groups_2023"),
    ("T7", "PSA NDHS 2022 (nutrition, water, sanitation)", "child nutrition, WASH", "utilization", "PSA / DHS Program",
     "https://dhsprogram.com", "region", "one-off (2022)", "1 point", "~1 year", "registration", "partly", "no", "no", "regional context", "E", "regional, single round", ""),
    ("A1", "PSA palay and corn production", "volume and area harvested", "availability", "PSA OpenSTAT", PX + "DB/2E/CS/0012E4EVCP0.px", "province", "quarterly", "1987-Q1 to 2026-Q3", "~6-8 weeks (rule, unverified)", "public API",
     "no", "no", "yes (C3)", "", "B", "existing C3; release dates unverified", "prod_palay_corn"),
    ("A2", "PSA fisheries production by subsector", "volume", "availability", "PSA OpenSTAT", PX + "DB/2E/FS/0132E4GVFP1.px", "province", "quarterly", "1993-Q1 to 2026-Q2 (provinces)", "~6-8 weeks", "public API",
     "no", "no", "yes (C4)", "", "B", "existing C4", "prod_fisheries"),
    ("A3", "PSA aquaculture production by species", "volume", "availability", "PSA OpenSTAT", PX + "DB/2E/FS/0072E4GVAP0.px", "province", "quarterly", "1996-Q1 to 2026-Q2; 87% of species cells empty", "~6-8 weeks", "public API",
     "no", "no", "yes (overlaps C4: a fisheries subsector)", "", "B", "detail of C4, not new", "prod_aquaculture"),
    ("A4", "PSA vegetables and root crops production", "volume by crop", "availability", "PSA OpenSTAT", PX + "DB/2E/CS/0082E4EVCP3.px", "province", "quarterly", "2010-Q1 to 2026-Q2 (142 crops)", "~8 weeks", "public API",
     "no", "no", "yes (new)", "", "B", "new provincial availability signal", "prod_vegetables_rootcrops"),
    ("A5", "PSA fruit crops production", "volume", "availability", "PSA OpenSTAT", PX + "DB/2E/CS/0072E4EVCP2.px", "province", "quarterly", "2010-2026", "~8 weeks", "public API", "no", "no", "yes (new)", "", "B", "new", ""),
    ("A6", "PSA chicken and livestock production", "volume by animal type", "availability", "PSA OpenSTAT", PX + "DB/2E/LP/PDN/0052E4FPCT0.px ; 0082E4FPLS2.px", "province", "quarterly", "2023-Q1 to 2026-Q2 only", "~6 weeks", "public API",
     "no", "no", "yes, but too short", "", "C", "provincial series start 2023", "prod_chicken, prod_livestock"),
    ("A7", "PSA livestock and poultry inventory", "heads by type", "availability", "PSA OpenSTAT", PX + "DB/2E/LP/INV/NEW/0022E4FINL5.px", "province", "quarterly", "2010-2026 (1994-2023 old series)", "~6 weeks", "public API", "no", "no", "yes (new)", "", "B", "new", ""),
    ("A8", "PSA cereals stock inventory index", "monthly cereals stocks", "availability/stability", "PSA OpenSTAT", PX + "DB/3L/FAV/0013L5ECSI0.px", "national", "monthly", "per table", "~1 month", "public API",
     "no", "no", "national context only", "", "D", "national", ""),
    ("A9", "PSA domestic trade via road transport", "volume/value of goods", "availability", "PSA OpenSTAT", "DB/2L (Volume and Value of Domestic Trade via Road Transport)", "province", "quarterly", "2025-2026 only", "~1 quarter", "public API",
     "no", "no", "too short", "", "C", "two years only", ""),
    ("A10", "DA / NDRRMC agricultural damage reports", "damage and production loss per event", "availability/stability", "DA / NDRRMC",
     "https://monitoring-dashboard.ndrrmc.gov.ph ; DA DRRM reports (PDF)", "province/municipality per event", "event-based", "irregular", "days", "PDF situation reports",
     "no", "no", "possible after manual extraction", "", "D", "event PDFs; no time series", ""),
    ("B1", "PSA retail prices of agricultural commodities (2018 series)", "monthly retail price per commodity (e.g. regular-milled rice, broiler chicken, pork kasim, tilapia)", "access", "PSA OpenSTAT",
     PX + "DB/2M/2018NEW/0042M4ARN01.px (cereals); ARN05, ARN06, ARN09, ARN10, ARN11, ARN02", "province", "monthly", "2018-01 to 2026-09; key items 97% of months in every province", "~1 month (rule, unverified)", "public API",
     "no", "no", "yes (new commodity-level prices)", "", "A", "provincial monthly, complete for key foods; release timing to verify", "retail_*"),
    ("B2", "PSA retail prices (1990-2021 series)", "monthly retail price", "access", "PSA OpenSTAT", PX + "DB/2M (Retail Prices of Agricultural Commodities, 1990-2021)", "province", "monthly", "1990-2021", "~1 month", "public API",
     "no", "no", "yes (historical depth)", "", "B", "series break with 2018 series to reconcile", ""),
    ("B3", "PSA farmgate prices", "monthly farmgate price (palay, corn, livestock)", "availability/access", "PSA OpenSTAT", PX + "DB/2M/NFG/0032M4AFN01.px ; 0032M4AFN10.px", "province", "monthly", "2010-01 to 2026-09", "~1 month", "public API",
     "no", "no", "yes (new; producer income)", "", "B", "missing for some commodities", "farmgate_cereals, farmgate_livestock_household"),
    ("B4", "PSA wholesale prices", "monthly wholesale price", "access", "PSA OpenSTAT", PX + "DB/2M/NWSNEW/0052M4AWB01.px ; 0052M4AWB10.px", "province (fish: 3 provinces only)", "monthly", "2010-2026 (1990-2021 old series)", "~1 month", "public API",
     "no", "no", "yes (A3 analogue)", "", "B", "overlaps A3; fish partial", "wholesale_cereals, wholesale_fish"),
    ("B5", "PSA CPI for bottom 30% income households", "food CPI and YoY for the poorest households", "access", "PSA OpenSTAT", PX + "DB/2M/PI/BIH/2018NEW/0022M4ABIR1.px ; ABIR2", "province", "monthly", "2018-01 to 2026-09", "~5 days after month (rule)", "public API",
     "no", "no", "yes, but r = 0.94 with all-income food CPI (largely redundant)", "", "B", "targets the poor; mostly redundant with A1/A2", "cpi_bottom30_index, cpi_bottom30_yoy"),
    ("B6", "PSA CPI 2012=100 by province (annual)", "annual CPI 1994-2018", "access", "PSA OpenSTAT", PX + "DB/3L/FAC/0013L5ECPI0.px", "province", "annual", "1994-2018", "-", "public API",
     "no", "no", "vintage reference only (annual)", "", "D", "fills the 2012=100 vintage gap at annual resolution only", "cpi_2012base_1994_2018"),
    ("B7", "PSA CPI all income (existing)", "monthly food and all-items CPI", "access", "PSA OpenSTAT", PX + "DB/2M/PI/CPI/2018NEW/0012M4ACP22.px", "province", "monthly", "2018-2026 (+1994-2017 back-cast)", "~5 days; release dates partly verified", "public API",
     "no", "no", "yes (A1, A2)", "", "B", "existing", "in repository"),
    ("B8", "PSA LFS employment and unemployment", "unemployment, underemployment", "access", "PSA", PX + "DB/1B/LFS/0021B3FKEI2.px (national); provincial annual in PSA releases", "national monthly; provincial annual only (2021+)", "monthly (national) / annual (province)", "2005-2026 national; 2021-2025 provincial", "~5-6 weeks", "public; provincial from releases",
     "no", "no", "national only (E1)", "", "C", "no quarterly provincial series", "owner file (E116)"),
    ("B9", "NWPC Region IV-A wage orders", "daily minimum wage (agri / non-agri)", "access", "DOLE-NWPC / RTWPB IV-A", "https://nwpc.dole.gov.ph", "region (rates by province/area class)", "irregular (wage orders, roughly yearly)", "orders IVA-19 to IVA-22 (2022-2025)", "dated orders", "public",
     "no", "no", "step feature (real wage = wage / CPI)", "", "B", "dated, but changes only once a year", ""),
    ("B10", "BSP OFW cash remittances", "USD cash remittances", "access", "BSP", "https://www.bsp.gov.ph/SitePages/Statistics/External.aspx (403 to automated access)", "national (by source country, not destination province)", "monthly", "1989-2026", "~6 weeks", "manual download",
     "no", "no", "national context only", "", "C", "no provincial destination data; manual download needed", "partial in repository"),
    ("B11", "DSWD 4Ps program coverage", "active beneficiary households", "access (social protection)", "DSWD", "https://pantawid.dswd.gov.ph (quarterly PDF reports)", "province / municipality", "quarterly reports", "2020-2024 (PDF)", "~1 quarter", "PDF; manual extraction",
     "no", "no", "possible (policy context)", "", "D", "administrative counts in PDFs", ""),
    ("B12", "World Bank RTFP market prices", "modelled monthly food prices by market", "access", "World Bank Microdata Library", "https://microdata.worldbank.org/catalog/6172", "market (108 markets nationwide)", "monthly", "2007-01 to 2025-11", "varies", "free registration",
     "no", "no", "not point-in-time: ML-imputed estimates", "", "E", "imputed values; leakage risk", ""),
    ("B13", "WFP food prices (HDX)", "monthly retail prices by market", "access", "WFP via HDX (source: PSA)", "https://data.humdata.org/dataset/wfp-food-prices-for-philippines", "market / province", "monthly", "2000-01 to 2024-06", "-", "public CSV",
     "no", "no", "redundant with B1/B2 (same PSA source)", "", "E", "duplicate of PSA retail prices", ""),
    ("S1", "NASA POWER monthly climate at province centroids", "precipitation, 2 m temperature, max temperature, humidity", "stability", "NASA LaRC POWER (MERRA-2 / satellite)",
     "https://power.larc.nasa.gov/api/temporal/monthly/point", "province (centroid point)", "monthly", "1981-01 to 2025-12, 0% missing", "~1-2 months; values can be revised", "public API",
     "no", "no", "yes (new: fills the empty rainfall column)", "", "B", "point values, not station data; vintage revisions", "nasa_power"),
    ("S2", "CHIRPS rainfall", "satellite-gauge monthly rainfall (0.05 deg)", "stability", "UCSB Climate Hazards Center", "https://data.chc.ucsb.edu/products/ (v2 monthly path returned 404)", "gridded (aggregable to provinces)", "monthly / pentad", "1981+", "~3 weeks (prelim) / ~2 months (final)", "public",
     "no", "no", "yes, after aggregation", "", "B", "needs raster aggregation; prelim vs final vintages", ""),
    ("S3", "PAGASA station rainfall and temperature", "station observations", "stability", "PAGASA", "https://www.pagasa.dost.gov.ph (data request)", "station", "daily", "decades", "request", "formal request and fee",
     "no", "no", "yes (best quality)", "", "C", "not public", ""),
    ("S4", "IBTrACS tropical cyclone tracks", "storm tracks", "stability", "NOAA NCEI", "https://www.ncei.noaa.gov/products/international-best-track-archive", "point tracks (province exposure computable)", "event / 3-hourly", "1842+", "near real time; best-track revised", "public",
     "no", "no", "yes (C2)", "", "A", "existing C2", "in repository"),
    ("S5", "NOAA ONI / PAGASA ENSO advisories", "ENSO state", "stability", "NOAA CPC / PAGASA", "https://www.cpc.ncep.noaa.gov", "global / national", "monthly / event", "1950+", "~1 week", "public",
     "no", "no", "yes (C1)", "", "A", "existing C1", "in repository"),
    ("S6", "MODIS / VIIRS vegetation indices (NDVI)", "crop greenness", "stability/availability", "NASA LP DAAC", "https://lpdaac.usgs.gov", "gridded", "16-day", "2000+", "~2 weeks", "Earthdata login",
     "no", "no", "possible", "", "C", "login and raster processing", ""),
    ("O1", "FAOSTAT food security indicators", "prevalence of undernourishment, FIES (national)", "all four", "FAO", "https://www.fao.org/faostat", "national", "annual (3-year averages)", "2000+", "~1 year", "public",
     "partly (national PoU, FIES)", "no", "no", "national context", "E", "national only", ""),
    ("O2", "GDELT news volume", "news coverage shares", "stability (signals)", "GDELT", "https://api.gdeltproject.org", "national (Philippines)", "daily", "2017+", "real time", "public",
     "no", "no", "N1 context", "", "B", "existing; adds noise in E117", "in repository"),
]
COLS = ["id", "dataset", "indicator", "fao_dimension", "source", "url_or_endpoint", "geography", "frequency", "historical_coverage",
        "publication_lag", "access", "direct_food_insecurity_measure", "suitable_as_target", "suitable_as_feature", "supports_validation",
        "classification", "classification_reason", "acquired"]


def main():
    inv = pd.DataFrame(R, columns=COLS)
    cov = pd.read_csv(ROOT / "out" / "acquired_coverage.csv")
    ov = json.loads((ROOT / "out" / "overlap_checks.json").read_text())
    stats = []
    for r in inv.itertuples():
        keys = [k.strip() for k in str(r.acquired).split(",")]
        keys = [k for k in keys if k in set(cov["dataset"])] + ([k for k in cov["dataset"] if str(r.acquired).startswith("retail_*") and k.startswith("retail_")])
        c = cov[cov["dataset"].isin(keys)]
        stats.append({"measured_provinces": "; ".join(sorted(set(", ".join(c["provinces_with_data"].dropna()).split(", ")) - {""})) if len(c) else "",
                      "measured_first": c["first_period"].dropna().min() if len(c) else "", "measured_latest": c["latest_period"].dropna().max() if len(c) else "",
                      "measured_missing_pct_table": c["missing_pct"].dropna().round(1).astype(str).str.cat(sep="; ") if len(c) else ""})
    inv = pd.concat([inv, pd.DataFrame(stats)], axis=1)
    inv.to_csv(ROOT / "FAO_FOOD_SECURITY_DATA_INVENTORY.csv", index=False, lineterminator="\n")
    inv[inv["id"].str.startswith("T")].to_csv(ROOT / "DIRECT_FOOD_INSECURITY_TARGETS.csv", index=False, lineterminator="\n")
    pm = inv[inv["geography"].str.startswith(("province", "region + 5"), na=False) & inv["frequency"].str.contains("monthly|quarterly", na=False)]
    pm.to_csv(ROOT / "PROVINCIAL_MONTHLY_QUARTERLY_DATA.csv", index=False, lineterminator="\n")
    for dim, fn in (("availability", "FOOD_AVAILABILITY_DATA.csv"), ("access", "FOOD_ACCESS_DATA.csv"),
                    ("utilization", "FOOD_UTILIZATION_DATA.csv"), ("stability", "FOOD_STABILITY_DATA.csv")):
        inv[inv["fao_dimension"].str.contains(dim) | inv["fao_dimension"].eq("all four")].to_csv(ROOT / fn, index=False, lineterminator="\n")
    print(inv.groupby("classification").size().to_dict(), len(pm), json.dumps(ov["key_commodity_coverage"].get("farmgate_cereals"), default=str))


if __name__ == "__main__":
    main()

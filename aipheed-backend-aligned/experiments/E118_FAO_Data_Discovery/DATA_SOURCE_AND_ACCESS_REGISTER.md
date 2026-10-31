# E118 data source and access register (2026-10-31)

**How it was searched.**
- **PSA OpenSTAT, programmatically:** 1,245 tables listed across 10 subject folders; 672 candidate tables scanned for geography, periodicity and year span.
- **Web searches:** FNRI, NNC, CBMS, DSWD, NWPC, WFP/HDX, World Bank and climate providers.
- **Probes:** direct API checks.
- **Restrictions kept:** no SWS or PSA "latest release" searches (the protected 2026-H2 rule); no access controls bypassed.

**Where the details are.** Every dataset is a row in `FAO_FOOD_SECURITY_DATA_INVENTORY.csv`: source, URL or endpoint, classification and reason.

## Publicly downloadable (acquired here, raw files unmodified in `data/raw/`, fetch log in `data/acquisition_log.json`)

| Source | Access | Acquired |
|---|---|---|
| PSA OpenSTAT PX-Web API (`https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/...`) | open JSON/CSV API; no key | 23 tables: retail, farmgate and wholesale prices; bottom-30% CPI; 2012=100 CPI (annual); vegetables, chicken, livestock, aquaculture, palay/corn and fisheries production; subsistence incidence 1991-2021; FIES 2023 expenditure groups |
| NASA POWER (`https://power.larc.nasa.gov/api/temporal/monthly/point`) | open API; no key | monthly precipitation, temperature, max temperature and humidity at the five province centroids, 1981-2025 |

## Public, not acquired (reason)

| Source | Reason |
|---|---|
| WFP food prices on HDX | the same PSA retail prices (duplicate) |
| World Bank RTFP (microdata.worldbank.org/catalog/6172) | modelled, imputed prices (not point-in-time); free registration |
| CHIRPS (data.chc.ucsb.edu) | v2 monthly path returned 404; needs raster aggregation; next step |
| PSA retail prices 1990-2021 and inventory tables | identified; acquire with the same script when the experiment needs the depth |
| NWPC wage orders | dated text orders; manual transcription |
| DSWD 4Ps quarterly reports | PDF tables; manual extraction |
| NDRRMC / DA damage reports | event PDFs |

## Requires a formal request or login (procedure)

| Data | Holder | Procedure |
|---|---|---|
| CBMS 2024 FIES by barangay / city-municipality | PSA (CBMS Service) and the LGUs | Data request to PSA under its data-sharing guidelines, or through each LGU's CBMS focal person. The E87 request is drafted but unsent: it needs the researchers' names and signatures. |
| ENNS / NNS FIES and nutrition microdata, provincial tables | DOST-FNRI | FNRI data request form or eFOI (foi.gov.ph/agencies/fnri). Ask for provincial FIES 2018-19, 2021 and 2023 with standard errors. |
| Operation Timbang Plus provincial and municipal results | NNC Region IV-A | eFOI to NNC (foi.gov.ph/agencies/nnc) or a letter to NNC IV-A. Ask for annual OPT Plus prevalence by province and municipality, 2015-2025. |
| BSP OFW remittances (1989+) | BSP | manual download from bsp.gov.ph (automated access returns 403) |
| PAGASA station rainfall / temperature | PAGASA CADS | climate data request form, with a fee |
| MODIS / VIIRS NDVI | NASA LP DAAC | free Earthdata login |
| FNRI ENNS PUF, PSA FIES PUF | FNRI, PSA | microdata request (PSA FIES 2023 PUF already with the owner) |

**No external request was sent.**

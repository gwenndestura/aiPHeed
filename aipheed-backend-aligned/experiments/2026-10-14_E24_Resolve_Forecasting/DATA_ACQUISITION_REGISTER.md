# Data acquisition register (E24, prioritized)

**Status values:**

| Status | Meaning |
|---|---|
| AUTHORIZED | In the project and on the hash-pinned allowlist |
| PUBLIC – NOT ACQUIRED | Published officially but not obtainable from this environment, or not yet downloaded |
| PROTECTED | Exists in the project but not authorized (never opened) |
| PENDING PUBLICATION | Not yet released by the agency |
| UNAVAILABLE | Not published at the needed level by any official source found |

**No national or regional value is ever used as a provincial or municipal observation.**

| P | Variable (geography) | Years / quarters needed | Official source & access | Status | Release timing | Contribution to the approved objectives | Enough history for chronological evaluation? |
|---|---|---|---|---|---|---|---|
| **1** | **New labelled quarters of the approved target** (S1 = SWS Balance Luzon hunger + 2 × provincial food CPI deviation) | 2026-Q3 onward, **≥ 12–20 new quarters** (see `runs/minimum_data.json`) | SWS survey releases; PSA OpenStat 0012M4ACP23 (provincial food CPI) | 2026-Q3 PROTECTED; 2026-Q4+ PENDING PUBLICATION | SWS: 1–3 months after fieldwork; CPI: ~5th of the next month (provincial later) | **The only route to C9 (untouched holdout) and to H2/H3 becoming testable** | Only by accumulating new quarters. A model anticipating 75% of label changes needs ≈ 12–16 quarters for 80% power; ≥ 5 LOW rows needs ≈ 20 quarters (88%). |
| **2** | **2026 news and government features at forecast cutoffs** (province) | 2026-Q1…Q4 | Project corpus (GDELT, RSS, Google News) with original publication times; PSA, BSP, DOE, PAGASA series | PROTECTED / not authorized | Continuous / monthly | Needed to **seal** prospective forecasts for 2026-Q3+ and to produce the 2027-Q1 forecast | — |
| **3** | **Municipal poverty incidence, PSA 2021 SAE** (city/municipality, with SE/CV) | 2021 (and 2023 if released) | PSA "2021 City and Municipal Level Poverty Estimates" (released 2024-04-02), workbook `2018 - 2021 SAE_with PSGC_noHUC.xlsx`; psa.gov.ph/statistics/poverty-sae | **PUBLIC – NOT ACQUIRED.** psa.gov.ph and foi.gov.ph return HTTP 403 to automated access (2026-10-14; not bypassed). The project holds 16 of 142 municipal values. | Released | Objective 3 / H4: replaces the province-mean substitute for 126 LGUs. Ingestion and validation code is ready (`backend_dev/app/quarterly/lgu_poverty.py`, `runner/lgu_rankings_v2.py --sae`). | Static weight; no time series needed. **Note the "noHUC" scope:** HUCs (e.g. Lucena, Antipolo) may be in a separate table. |
| **4** | **Provincial food-insecurity outcome** (FIES moderate+severe, by province) | Any year, ideally repeated | DOST-FNRI NNS microdata (data-sharing request); PSA CBMS; a DA- or LGU-run FIES module | UNAVAILABLE as published tables (FNRI publishes region level only) | Survey cycles (2–3 years) | **Would let provincial forecasts be validated against a measured outcome**, which the composite proxy cannot do | No: at most 1–2 points per province. Validation only, not training. |
| **5** | Regional FIES anchor | 2023 (verified 19.1%, CI 17.0–21.1); 2019 | enutrition.fnri.dost.gov.ph | 2023 AUTHORIZED-PUBLIC (verified); 2019 PUBLIC – NOT LOCATED (HFIAS scale, not comparable) | Done | Objective 5 face validity (descriptive) | n/a |
| **6** | **Provincial CPI release dates** (RSSO IV-A) | 2021–2026 | rsso04a.psa.gov.ph release pages | PUBLIC – NOT ACQUIRED (Cloudflare; manual verification needed) | Monthly | Exact timing of the D component and of cpi_dev; removes the "national + 14 days" proxy | n/a |
| **7** | Provincial unemployment | 2021+ | PSA LFS | UNAVAILABLE (no provincial quarterly table in any of 20 LFS tables) | — | None; documented limitation | — |
| **8** | Supplementary SWS rounds (2025-Q2/Q3, different respondent base) | 2025 | SWS | AUTHORIZED values in E12, **not used as labels** | Done | Would fill 2 label gaps **only if the adviser approves** the change of respondent base | — |

## Next steps (in order)

1. **You (file-by-file authorization):** 2026 news and government features for the prospective sealing of 2026-Q3/Q4 forecasts.
2. **You (manual download):** the PSA 2021 SAE workbook from a browser. Then authorize it, and run:

   ```
   python -B runner/lgu_rankings_v2.py --sae "<path>" --sae-year 2021
   ```

   This creates `data_v2/` and LGU ranking v2. The original file is untouched.
3. **Adviser:** approve the reliability rule, the H4/H5 rules, the threshold definition, and the use of the supplementary SWS rounds.
4. **DOST-FNRI / PSA:** request provincial FIES (NNS microdata) or CBMS outputs for an independent provincial outcome.

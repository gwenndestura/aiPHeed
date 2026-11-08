# Deliverable 1. Provincial dataset audit

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

## Workbook
- File: `aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx`. The upload named "(1)" is not on disk; the only copy (Downloads,
  2026-11-03 01:35) is byte-identical to `backend/data/fi_labels/raw/owner_supplied/` (SHA-256 `6655178448d5…`, also in
  `raw/MANIFEST.csv`). The original is kept unchanged; values are read from its sheet exports.
- 10 sheets: READ ME, Labeled Provincial Data (50 long-format records), FNRI 2015 Provinces, ENNS Provincial, PSA Subsistence,
  PSA Food Threshold, Regional Benchmarks, QA and Corrections, Sources, Label Dictionary. Three cell comments
  (ENNS reference years differ by province; PSA Table 1 source; thresholds are annual per-capita PHP).
- Metadata: written by openpyxl on 2026-11-02; the comments are authored "OpenAI", so the workbook was compiled with an AI
  assistant. Its values are therefore treated as transcriptions to verify, not as primary data.
- `province_code` is empty in all 50 records. PSA Quezon excludes Lucena City (HUC); whether the FNRI and ENNS Quezon
  values include Lucena is not stated (**unverified**).

## Records by outcome and reference year
| outcome | reference_year | provinces | records | verification |
|---|---|---|---|---|
| ENNS_MODSEV | 2018 | Laguna | 1 | unverified_secondary |
| ENNS_MODSEV | 2019 | Quezon, Rizal | 2 | unverified_secondary |
| ENNS_MODSEV | 2021 | Batangas, Cavite | 2 | unverified_secondary |
| ENNS_SEV | 2018 | Laguna | 1 | unverified_secondary |
| ENNS_SEV | 2019 | Quezon, Rizal | 2 | unverified_secondary |
| ENNS_SEV | 2021 | Batangas, Cavite | 2 | unverified_secondary |
| FNRI15_INSEC | 2015 | Batangas, Cavite, Laguna, Quezon, Rizal | 5 | verified_primary |
| FNRI15_SEV | 2015 | Batangas, Cavite, Laguna, Quezon, Rizal | 5 | verified_primary |
| PSA_SUB_FAM | 2018 | Batangas, Cavite, Laguna, Quezon, Rizal | 5 | verified_primary |
| PSA_SUB_FAM | 2021 | Batangas, Cavite, Laguna, Quezon, Rizal | 5 | verified_primary |
| PSA_SUB_FAM | 2023 | Batangas, Cavite, Laguna, Quezon, Rizal | 5 | verified_primary |
| PSA_SUB_POP | 2018 | Batangas, Cavite, Laguna, Quezon, Rizal | 5 | verified_primary |
| PSA_SUB_POP | 2021 | Batangas, Cavite, Laguna, Quezon, Rizal | 5 | verified_primary |
| PSA_SUB_POP | 2023 | Batangas, Cavite, Laguna, Quezon, Rizal | 5 | verified_primary |

## Verification
- **40 of 50 records verified [V]:** the 10 FNRI 2015 values equal the FNRI 2015 report appendices; the 30 PSA subsistence
  values equal PSA OpenSTAT Tables 3 and 4 (checked again in FI12 code: `outcomes.build` asserts equality to 0.05 pp).
- **10 ENNS records unverified [S]:** they come from the DEPDev CALABARZON RDP results matrix. The DEPDev PDF returns HTTP 403
  to scripted download and the FNRI tables are behind a firewall from this network. Instrument (HFIAS or FIES), fieldwork
  months, sample sizes and SEs are not given.
- Regional benchmarks: FNRI 2015 (n = 4,328) [V]; 2023 NNS FIES moderate-to-severe 19.1 % (17.0–21.1) [V]; ENNS pooled
  51.5 % HFIAS and 2023 severe 1.7 % [S]; PIA 2025 22.6 % (news report) not used.

## Per-dataset assessment
| Dataset | Source / publication | Reference year | Unit | Precision | Comparable across years? |
|---|---|---|---|---|---|
| FNRI 2015 FSS | DOST-FNRI, Philippine Nutrition Facts and Figures 2015 | 2015 | % of households (HFIAS categories) | SE and 95 % CI per province; n 735–1,076 | Single wave; HFIAS, not FIES |
| ENNS provincial | DOST-FNRI ENNS, reproduced by DEPDev RDP 2023–2028 midterm matrix (published 2026-02) | Laguna 2018; Quezon, Rizal 2019; Batangas, Cavite 2021 | % of households | none published in the matrix | No: one year per province; severe values split 1.5–2.4 % (2021) vs 7.9–13.7 % (2018–19), and severe vs moderate-to-severe rank correlation is −0.1 within the same survey, which indicates a scale or instrument difference |
| PSA subsistence incidence | PSA full-year poverty statistics (OpenSTAT Tables 3/4; RSSO IV-A release) | 2018, 2021, 2023 (income year) | % of families / % of population below the food threshold | CV 17–62 % per province (median 34 %) | Yes, same methodology; but food poverty, not experienced food insecurity |
| PSA food threshold | PSA OpenSTAT Table 3a | 2018, 2021, 2023 | PHP per capita per year | — | Context only |

## Sampling reliability (FI12 [R])
| outcome-year | Cochran Q p (provinces differ?) | noise-ceiling ρ (median) | top province reproducible | significantly above CALABARZON |
|---|---|---|---|---|
| FNRI15_INSEC · 2015 | 0.61 | 0.70 | 0.64 | none |
| FNRI15_SEV · 2015 | 0.46 | 0.70 | 0.44 | none |
| PSA_SUB_FAM · 2018 | 0.00 | 0.90 | 0.98 | Quezon |
| PSA_SUB_FAM · 2021 | 0.00 | 0.95 | 1.00 | Quezon |
| PSA_SUB_FAM · 2023 | 0.09 | 0.87 | 0.90 | none |
| PSA_SUB_POP · 2018 | 0.00 | 0.90 | 0.99 | Quezon |
| PSA_SUB_POP · 2021 | 0.00 | 0.97 | 1.00 | Quezon |
| PSA_SUB_POP · 2023 | 0.17 | 0.80 | 0.91 | none |

- The noise ceiling is the median Spearman between the published values and a re-draw with the published SEs: a perfect
  predictor of the true provincial values would score about this against the published numbers.
- **FNRI 2015: the five provinces are not statistically distinguishable** (Q p = 0.46); no province differs from the
  regional 19.0 %. A ranking of 2015 provinces cannot be validated.
- **PSA 2018 and 2021: provinces differ; Quezon is significantly above CALABARZON in both.** PSA 2023: not distinguishable.
- ENNS: no SEs, so reliability cannot be assessed.

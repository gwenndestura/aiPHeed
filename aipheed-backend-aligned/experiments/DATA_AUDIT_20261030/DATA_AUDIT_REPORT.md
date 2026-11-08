# aiPHeed data audit (2026-10-30)

| | |
|---|---|
| Scope | read-only; no source file modified, nothing repaired, no model trained |
| Branch | `aiPHeed/e115-mean-reversion-prospective` (local) |
| Runner | `runner/audit.py`; source hashes in `out/audit.json` |

## Tables

| File | Contents |
|---|---|
| `DATASET_COVERAGE.csv` | 21 datasets: source, agency, indicators, processing state, frequency, rows, units, period range, latest observation, missing, duplicates, gaps, publication-date evidence |
| `INDICATOR_COMPLETENESS.csv` | the 12 FIRI v2 indicators: domain, input, resolution, coverage in the served training stack, missing by year and province, availability status, classification |
| `TEMPORAL_ALIGNMENT_REPORT.csv` | issue / latest observation / target relationships, point-in-time checks on every stack row, known timing violations |
| `GEOGRAPHICAL_COVERAGE_REPORT.csv` | units per dataset, provinces present, 142-LGU check, resolution |
| `DATA_QUALITY_REPORT.csv` | expected vs actual observations, duplicates, negatives, zeros, abrupt changes, longest gaps, values copied across provinces |
| `TRAINING_READINESS_REPORT.md` | what can be trained and evaluated |
| `DATA_ISSUES_AND_RECOMMENDATIONS.md` | every issue, its effect, the correction, and whether existing data can fix it |

## 1. Inventory

| Dataset | Agency | Feeds | Geography | Coverage (non-missing) | Frequency | State | Publication-date evidence |
|---|---|---|---|---|---|---|---|
| CPI index by province (OpenSTAT 0012M4ACP22) | PSA | A1, A2 | 5 provinces | 2021-01 to 2026-09 | monthly | raw, final vintage | retrieval stamp. Release-date ledger: base months 35/36 archive-verified; refresh months 32 verified, 61 owner-reported, 79 unresolved |
| CPI YoY by province (0012M4ACP23) | PSA | A1/A2, price label | 5 provinces | 2021-01 to 2026-09 | monthly | raw | retrieval stamp |
| Wholesale rice prices | PSA | A3 | 5 provinces | 2021-Q1 to 2026-Q3 (2.6% missing) | quarterly | processed | none (rule t−1) |
| LGU vulnerability (SAE 2021 poverty, POPCEN 2024) | PSA | V1 | 142 LGUs (all present) | 2021 SAE / 2024 census | static | processed; 1 missing poverty value (substitute used) | published 2024-25 |
| Subsistence incidence | PSA | target candidate / V | 5 provinces | 2021, 2023 | triennial | raw | 2024-08-15 |
| ENSO alert items (in `enso_context.py`) | PAGASA | C1 | national | 2023-2026 dated items | event | raw | each item dated |
| Climate panel (typhoons, ENSO, drought, rainfall) | PAGASA / IBTrACS | C2 | 5 provinces | 2021-Q1 to 2026-Q3 | quarterly | processed | fetched_at only. **Rainfall anomaly column 100% empty.** Typhoon counts identical across provinces in 61% of quarters. |
| Palay / corn production | PSA | C3 | region + 5 provinces | 2021-Q1 to 2026-Q2 | quarterly | raw, final revisions | none (rule t−1) |
| Fisheries production | PSA | C4 | region + 5 provinces | 2021-Q1 to 2026-Q2 | quarterly | raw, final revisions | none (rule t−1) |
| LFS rates | PSA | E1 | **national only** | 2021-01 to 2026-08 | monthly | raw | none (rule t−1) |
| OFW cash remittances (model panel) | BSP | E2 | national, **copied to all 5 provinces (100% identical)** | 2021-Q1 to **2025-Q4** | quarterly | processed | fetched_at only |
| OFW cash remittances (audit copy) | BSP | E2 | national | 2021-Q1 to 2026-Q2 | quarterly | processed | none |
| FSSI news panel | aiPHeed corpus | N1 | 5 provinces | 2021-Q1 to 2026-Q4; **80% missing** | quarterly | derived | article timestamps |
| SWS rounds, Balance Luzon | SWS | H1, target | region (1 value per quarter) | 2021-Q2 to 2026-Q3 (no 2025-Q1 round) | quarterly | raw | published date (verified) |
| SWS hunger by area | SWS | long-history target | 4 SWS areas | 1998-Q3 to 2026-Q3; 106 quarters, 7 without a round | quarterly | raw | published; pre-2021 = month end + 60 days (rule) |
| Area CPI / fish / palay (E116) | PSA | A1/A2, C4, C3 (area) | 4 / 4 / 3 areas | 1995 / 1993 / 1987 to 2026 | monthly / quarterly | derived (CPI 1994-2017 back-cast) | none (rules) |
| FNRI FIES observations | DOST-FNRI | target candidate | 2 provinces, 1 HUC, region | 2021, 2023 snapshots | irregular | raw (transcribed) | report year |
| Owner provincial employment | PSA (owner) | E1 provincial | 5 provinces | 2021-2025 annual (gaps 2024-25) | annual | raw | none |
| Served training stack (`stack_l2.csv`) | aiPHeed | all 12 | 5 provinces | origins 2021-Q1 to 2026-Q3 | quarterly × lead | derived | issue_date, psa_newest_month, sws/news publication |

## 2. The 12 indicators: domain mapping and readiness

The domain mapping matches `firi.DOMAIN_OF`. The trigger domains follow ADDENDUM_1.

| Code | Indicator | Trigger domain | Resolution in the model | Lead 1-2 missing | Availability | Classification |
|---|---|---|---|---|---|---|
| A1 | Food-price-pressure forecast | Market and prices | province, monthly | 11% (2021 origins) | base month verified; refresh partly unresolved; final vintage | **B** ready after correction |
| A2 | Headline above usual | Market and prices | province, monthly | 0% | as A1 | **B** |
| A3 | Wholesale rice change | Market and prices | province, quarterly | 27% (all 2021) | lag assumed | **B** |
| V1 | Poverty and density | (poverty, other input) | LGU → province, static | 0% | published after most origins | **D** not suitable as a forecasting input (structural profile) |
| C1 | El Niño advisory | Climate | national event | 0% | verified | **A** ready (two values, national) |
| C2 | Typhoons within 300 km | Climate | province, but identical in 61% of quarters | 4% (2026-Q3 incomplete) | plausible | **B** |
| C3 | Palay/corn drop | Climate | province, quarterly | 22% (2021) | lag assumed | **B** |
| C4 | Fisheries drop | Fish production | province, quarterly | 22% (2021) | lag assumed | **B** |
| E1 | Unemployment change | Employment | **national copied to provinces** | 22% | lag assumed | **C** insufficient: no quarterly provincial or regional series |
| E2 | Remittance decline | OFW remittances | **national copied to provinces**; model panel stops at 2025-Q4 | 22% | lag assumed | **C** insufficient: national, 2021+ only |
| N1 | FSSI news index | (news, other input) | province | **83%** | verified | **C** insufficient coverage |
| H1 | Regional hunger outlook | (target component) | **region copied to provinces** | 9% | verified | **B**: valid as a regional input only, not as five provincial observations |

**Domains.**

| Domain | Data status |
|---|---|
| Market and prices | **usable after correction** (timing verification, vintages) |
| Fish production | **usable after correction**: provincial quarterly 2021+, area-level 1993+; lags unverified |
| Climate | **partly usable**: ENSO, typhoons and palay usable; rainfall absent; typhoon counts barely vary across provinces |
| Employment | **insufficient**: national monthly; provincial annual only |
| OFW remittances | **insufficient**: national, 2021+; long series blocked |

## 3. Temporal alignment

**Point-in-time checks on every Lead 1-2 stack row: 0 violations.**
- target = origin + lead;
- the newest CPI month ends before the issue;
- SWS rounds are published before the issue;
- news is published before the issue.

**Known violations and assumptions** (detail in `TEMPORAL_ALIGNMENT_REPORT.csv`):
- **600 training rows** use the 2021-22 price thresholds before they could be computed.
- **375 training rows** use the 2018=100 CPI before it was public.
- **3 of 29 archived headline rates** differ from the final vintage.
- **V1** is published 2024-25 but used at every origin.
- **The lags of A3, C3, C4, E1 and E2 are assumed.** Shifting them one quarter worsens B0's Lead-2 development Brier from 0.177 to 0.189.
- **The CPI refresh used by CR / CR-ANC is unverified** for most months.
- **No evaluation row is affected** by the threshold or base-year issues.

**Lead definitions.**
- Issue O(t) is day 1 of quarter t+1. CPI runs through month 2 of quarter t, and the newest SWS round is usually quarter t−1.
- Lead 1 targets t+1; Lead 2 targets t+2.
- Lead 2 is re-issued under schedule B after the SWS release.

## 4. Geography

**Provincial coverage.**
- All five provinces are present and standardized in every provincial dataset.
- All 142 LGUs are present in the vulnerability table.

**Substitutions that are not five independent observations:**
- H1 and the hunger part of the target: one Balance Luzon value per quarter.
- E1 and E2: national.
- C1: national.
- C2: mostly identical across provinces.

Overall, 38% of indicator × period cells in the served stack are identical across the five provinces.

**Effect.** The provincial T43c rows have 13-14 independent hunger observations per lead, not 65-70. The model can learn "which quarter" from national and regional columns, rather than "which province".

## 5. Quality

**No issues found:**
- duplicates (the SWS multiple rounds per quarter are averaged and are not duplicates);
- negative values where impossible;
- unit or date-format problems.

**Abrupt changes:** in fisheries (seasonal quarterly levels) and area CPI (2008 and 2023 shocks). These are real, not errors.

**Missing values.** These are NaN, never zero. Their causes:
- no pre-2021 base for YoY: 2021 origins of A3, C3, C4, E1, E2;
- not yet released: 2026-Q3/Q4;
- unavailable historically: news before 2023, rainfall entirely;
- not collected: OFW long series, regional LFS.

## 6. Target validity

| Target | What it measures | Resolution | Verdict |
|---|---|---|---|
| SWS hunger | experienced hunger (severe end of food insecurity) | regional, quarterly, 1998-2026 | valid for **regional** forecasting |
| T43c (hunger > 11.3 and price pressure) | composite proxy; price half built from the same CPI as A1/A2 | regional value × provincial price | not a provincial food-insecurity outcome; partly circular with the market predictors |
| 11.3% line | P60 of 6 quarters (2021-22), the lowest-hunger stretch on record; long-run median 13.8% | — | not defensible as a threshold |
| FNRI FIES; subsistence incidence; CBMS | broader food insecurity / food poverty | provincial snapshots (2021, 2023, 2023-24) | **cross-sectional validation only** |

**Decision.** The data support **regional hunger forecasting** and a **provincial vulnerability assessment**. They do not support provincial food-insecurity forecasting. See `TRAINING_READINESS_REPORT.md` and `DATA_ISSUES_AND_RECOMMENDATIONS.md`.

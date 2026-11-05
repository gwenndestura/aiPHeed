# Province-specific non-price evidence (2026-11-05)

**Pre-registration:** `PREREGISTRATION_PV.md` (PLAN-SHA256 632f495d…).
**Script:** `runner/pv_model.py`.
**Outputs:** `out/pv_fits.csv`, `out/pv_results.json`, `out/pv_validation_table.csv`.
**New data:** `data/raw_prov/` (PSA OpenSTAT, `FETCH_LOG.json` with SHA-256).
- C-B6D-E-X is reproduced exactly (2.2e-16) and **unchanged**.
- Leakage check passed (production truncated at t − 1 gives identical features).

## 1. Diagnosis: why provinces differ only through prices

- **Eq. 3 (Ch. III):** S = H + 2D.
  - H = SWS Balance Luzon hunger: **one value per quarter for all five provinces**.
  - D = the province's food-CPI deviation, **the only province-specific term in the target**.
- **Consequence:** a forecast of the Eq. 3 label can differ across provinces only through what predicts D. More
  province-specific inputs cannot change that, because the *label itself* differs across provinces only by price.
- **Changing it requires changing the target (Eq. 3):** an **adviser decision**. It is not made here.

## 2. Inventory of province-specific non-price indicators (verified)

| Indicator | Source (table) | Province-level? | Period | Use at O(t) | Used |
|---|---|---|---|---|---|
| Palay + corn production | PSA `2E/CS/0012E4EVCP0` | **Yes**, 5 provinces | quarterly 1987–2026 | quarter t − 1 (PSA releases about 6 weeks after quarter end; assumption disclosed) | Part A |
| Fisheries production | PSA `2E/FS/0132E4GVFP1` | **Yes** | quarterly 1993–2026 (data from 1993) | quarter t − 1 | Part A |
| Subsistence (food-poverty) incidence, families | PSA `1F/FY/0051F3DF030` | **Yes** | 2018, 2021, 2023 only; **CV 17–59%** | Published 1–2 years after the reference year | Part V (outcome) |
| Poverty incidence, families | PSA `1F/FY/0011F3DF010` | **Yes** | 2018, 2021, 2023 | as above | Part V (outcome) |
| Typhoon exposure | IBTrACS + province centroids (`backend/data/cb6_auto/seed/province_centroids.json`) | Derivable; the repo holds only the regional `tc_mean` / PAR counts | — | — | **Not built** (raw tracks not in the repo) |
| Province-geocoded news (FSSI) | project corpus | Yes, 2021+ only (about 17% coverage) | 2021–2026 | yes | Not added (no pre-2021 history) |
| Employment (LFS) | PSA OpenSTAT `1B/LFS`, `3K/E2` | **No:** national only | — | — | Kept national (E1) |
| OFW remittances | BSP | **No:** national only | — | — | Kept national (E2) |
| Quarterly provincial food-insecurity prevalence | none (SWS regional; FNRI 2021: 2 provinces) | **No** | — | — | — |

**No national or regional value was used as if it were provincial.**

## 3. Part A: C-B6D-E-XA (province crop and fisheries shocks in the provincial term)

**B-ext, 250 province-quarters, identical rows:**

| | C-B6D-E-XA L1 | C-B6D-E-X L1 | C-B6D-E-XA L2 | C-B6D-E-X L2 |
|---|---|---|---|---|
| Accuracy | 0.772 | 0.772 | 0.728 | 0.736 |
| Balanced accuracy | 0.711 | 0.711 | 0.669 | 0.674 |
| Precision / Recall | 0.821 / 0.863 | 0.821 / 0.863 | 0.799 / 0.817 | 0.801 / 0.829 |
| F1 | 0.841 | 0.841 | 0.808 | 0.815 |
| AUC [95% CI] | 0.736 [0.61, 0.86] | 0.739 [0.62, 0.86] | 0.716 [0.59, 0.82] | 0.711 [0.58, 0.82] |
| Brier | 0.181 | 0.181 | 0.192 | 0.193 |
| R1–R7 failed | none | none | R2, R3 | R2, R3 |
| Quarters with different provincial calls | 16 | 17 | 9 | 8 |

**Paired Brier, XA minus the comparator (Holm over 6):**

| Comparator | Lead 1 | Lead 2 |
|---|---|---|
| C-B6D-E-X | +0.0008 (p 0.87) | −0.0017 (p 0.042, Holm 0.15) |
| PERSIST-X | −0.111 (**Holm < 0.001**) | −0.116 (**Holm < 0.001**) |
| CLIM-X | −0.039 (Holm 0.15) | −0.033 (Holm 0.15) |

**Contribution:**
- The non-price part makes up 24% (Lead 1) and 41% (Lead 2) of |D̂|.
- **But the coefficients are tiny:** crops +0.009, fisheries −0.006, against 0.65 for D1 at the last origin. The
  production shocks are large numbers with small weights, and they change almost no call.

**Decision (pre-registered): not adopted.** No Brier gain at Lead 1; the Lead 2 gain is not significant after Holm.
**C-B6D-E-X remains the provincial candidate.**

## 4. Part V: does the provincial differentiation track measured provincial food poverty?

**Setup:**
- 15 province-years (2018, 2021, 2023).
- Within-year Spearman ρ (n = 5); the pooled mean ρ with a permutation test within each year.

| Signal | vs subsistence incidence: ρ 2018 / 2021 / 2023 | mean ρ (p) | vs poverty incidence: mean ρ (p) |
|---|---|---|---|
| V1: realised Eq. 3 provincial term 2D | −0.30 / −0.05 / +0.62 | +0.09 (0.39) | −0.25 (0.80) |
| V2: C-B6D-E-X Lead 1 probability | +0.30 / −0.05 / +0.36 | +0.20 (0.25) | −0.08 (0.61) |
| V3: C-B6D-E-XA Lead 1 probability | +0.10 / −0.05 / +0.36 | +0.14 (0.32) | −0.15 (0.70) |

**Reading (pre-registered rule): not shown.** Neither Eq. 3's provincial term nor the forecasts rank provinces
consistently with PSA's measured provincial food poverty or poverty.
- **Example:** Quezon has the highest subsistence and poverty incidence in 2018 and 2021 (2.6% / 4.7%; 9.3% / 16.3%),
  but its realised 2D was negative in 2023 (−5.4), the lowest of the five.
- **Power is low:** n = 5 per year, and subsistence CVs reach 59%. This is not proof of no relationship. **But the
  provincial differences in Eq. 3 cannot be presented as measured provincial food-insecurity differences.**

## 5. What this means

1. **Within the approved methodology (Eq. 3), the provincial signal is price-based by construction.** Province-specific
   non-price inputs (crops, fisheries) were tested and add nothing measurable.
2. **The independent check found no evidence that Eq. 3's price-based provincial term tracks measured provincial food
   poverty** (2018–2023).
3. **The forecast stays food-insecurity focused through measured regional hunger.** Its *provincial* differentiation
   should be described as **food-price pressure**, not as measured provincial food insecurity.

## 6. Adviser decisions needed

| Decision | Why |
|---|---|
| Keep Eq. 3 as the target and describe the provincial part as food-price pressure | The supported option; no change to the methodology |
| **Or** amend Eq. 3 to add a province food-poverty component (e.g. the latest published PSA subsistence or poverty incidence as of O(t)) | Changes the thesis target and Ch. III; only 3 vintages exist (2018, 2021, 2023), so the component would be a slow-moving structural term |
| The 11.0 cut-off (the paper's text says the all-period median) | Pending from earlier |

## 7. Data that would genuinely resolve the limitation

| Data | Holder | Request |
|---|---|---|
| Provincial food-insecurity prevalence (FIES), yearly or better | PSA (FIES SDG 2.1.2 provincial tables); DOST-FNRI (ENNS/NNS provincial estimates) | The provincial FIES moderate/severe series 2015–2025 with CVs |
| Provincial LFS unemployment | PSA (regional/provincial LFS tables, PDF only now) | The machine-readable provincial or regional quarterly series |
| OFW remittances by origin province | PSA Survey on Overseas Filipinos (yearly, regional); BSP | Regional/provincial cash-remittance series |
| Provincial typhoon exposure | NOAA IBTrACS (public) | Download the WP tracks; compute distance to the province centroids (feasible; needs pre-registration) |
| LGU nutrition outcomes | NNC OPT Plus; LGU nutrition offices | Municipal underweight/stunting series (as an outcome check only) |

**Independent validation plan (when FIES provincial data are obtained):**
- Part V's test, with FIES as the outcome.
- Fix the years before looking.
- Province-year Spearman with the within-year permutation.
- Report the CVs.
- "Validated" only if p < 0.05.

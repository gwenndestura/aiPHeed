# Official Outcome Comparison (Task C; descriptive only)

**What this is:** a comparison of aiPHeed's provincial price-pressure indicator with official food-related statistics. **No training, no thresholds, no forecasting accuracy.**

**Sources:**

- `runs/a1_20261013T030455Z/metrics_a1.json` → `official_comparison`
- Inputs: `psa_subsistence.parquet` (read-only, 2021 and 2023 only) and `nns_fies.parquet`

## 1. Checking the source numbers first

The E13 audit is an initial assessment. Each PSA subsistence row was therefore checked for internal consistency: is the reported 95% CI equal to p ± 1.96 × p × CV/100?

**Result:** all 12 rows (10 provincial, 2 regional) agree within 0.15 points. **The values, CVs and CIs in the project file are internally consistent with 95% intervals.** This checks the file against itself. **It does not check it against PSA's publication**, which was not opened.

## 2. Provincial subsistence incidence against relative price pressure

**Method:**

- Each province's annual mean D (and mean F) for the same year is compared with its subsistence incidence.
- A pair of provinces counts as **distinguishable** when |z| ≥ 1.96, with SE = p × CV/100. This is descriptive: independence is assumed and there is no multiplicity adjustment.

| Year | Higher subsistence | Lower | Difference (points) | z | Higher subsistence also had higher mean D? |
|---|---|---|---|---|---|
| 2021 | Quezon (4.7) | Batangas (0.6) | 4.1 | 4.9 | Yes (0.86 vs −0.34) |
| 2021 | Quezon | Cavite (1.5) | 3.2 | 3.4 | Yes (0.86 vs −1.72) |
| 2021 | Quezon | Laguna (1.5) | 3.2 | 3.6 | Yes (0.86 vs 0.30) |
| 2021 | Quezon | Rizal (0.6) | 4.1 | 4.9 | **No** (0.86 vs 0.91) |
| 2021 | Laguna (1.5) | Batangas (0.6) | 0.9 | 2.1 | Yes |
| 2021 | Laguna | Rizal (0.6) | 0.9 | 2.2 | **No** (0.30 vs 0.91) |
| 2023 | Rizal (1.5) | Cavite (0.4) | 1.1 | 2.6 | Yes (1.82 vs 0.73) |
| 2023 | Rizal | Quezon (0.5) | 1.0 | 2.4 | Yes (1.82 vs −2.71) |

| Pairs | Concordant with D | Concordant with F |
|---|---|---|
| **Distinguishable (8 of 20)** | **6 of 8** | 6 of 8 |
| All 20 | 13 of 20 | — |

**How to read this:**

- **The pairs are not independent.** Four of the six 2021 pairs involve Quezon, and each year is one cross-section.
- **The most precise contrast does not support "high pressure = high deprivation".**
  - In 2021, Quezon's subsistence incidence was clearly the highest (CV 17%). Its relative price pressure was close to Rizal's, which had the **lowest** incidence.
  - In 2023, Quezon had the **lowest** D of all five provinces (−2.71).
- **The 2023 values are imprecise.** 4 of 5 have CV above 30%. Only Rizal stands out.
- **What can be said:** "In the few contrasts that the sampling error allows, provinces with higher subsistence incidence usually, but not always, had higher relative food-price pressure in the same year (6 of 8 pairs). That is too few, and too dependent, to treat as validation."
- **Subsistence incidence is income-based food poverty. It is not experienced food insecurity.**

## 3. Regional FIES (2025) against SWS hunger (2025)

| Measure | Value | Scope | Instrument |
|---|---|---|---|
| FNRI FIES, moderate or severe | 22.6% (one value; secondary source) | Region IV-A | Household food-insecurity experience scale |
| SWS involuntary hunger, 2025 rounds | 24.0, 17.0, 15.3, 23.8, 16.7 (mean 19.4%) | Balance Luzon | Self-reported hunger in the past 3 months |

**Different instruments, recall periods and geographies.** They are shown side by side only.

**The project file lists FIES in five rows, but they hold one distinct value.** It was used once, at the regional level.

## 4. Conclusion

**Descriptive consistency:** limited and mixed. **This is not validation.**

**Actual provincial food-insecurity prediction accuracy: not evaluated**, because no independent, repeated provincial outcome exists.

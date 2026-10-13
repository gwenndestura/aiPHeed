# Data Availability and Feature-Timing Audit (E17)

**Source of the timing rule.** The current implementation's own rule (`config/governing_model.json`, "strict Rule 3 (frame_t2)"; code `scripts/supplementary/algorithm4_timing_valid.py`):

- government series of quarter t−1;
- news of quarter t;
- SWS = latest round released before quarter t+1 begins;
- poverty incidence as published.

**Forecast origin.** O = the first day of quarter t+1. **Target** = the label of quarter t+k, for lead time k.

This audit checks that rule against the data. **Every departure from the implementation is listed in §3.**

## 1. Inputs at origin O (start of quarter t+1)

| Input group | Columns | Row used | Evidence it was available before O | Classification |
|---|---|---|---|---|
| News (9) | FSSI, FSSI_lag1, FSSI_lag2, FSSI_accel, five triggers | Quarter t | Articles published in quarter t, before O | **Available in principle.** The audited 371-article set and the pipeline were built in 2026 (development reconstruction, not real-time). Two triggers are all zero in 2021–2025 (constant). |
| Government (36) | Food CPI (level, YoY, lag, accel), cpi_dev, rice price, unemployment, food − headline, headline CPI, OFW remittances, FX, diesel, gasoline, Brent, typhoon count and severity, rainfall anomaly, drought alert, ENSO, five commodity prices, with their lags and accels | Quarter t−1 | Monthly or quarterly series for t−1 are published within about 6 weeks after t−1 ends, so about 6 weeks before O. Provincial CPI dates are proxies. | **Reasonable but not verified per series** |
| SWS hunger (1) | `sws_hunger` = mean of the production-series rounds of the latest fieldwork quarter with a round published before O | — | Verified per-round dates (file 2) | **Established** |
| Poverty incidence (1) | `poverty_incidence` | — | The stored column changes **once, at 2023-Q1**, for every province. Neither PSA release (2021 survey released 2022-08-15; 2023 survey released 2024-08) falls at 2023-Q1. | **Not establishable. Excluded** (§3). |

**Missing values:**

- `features_fused` contains no missing values in 2021–2025. It holds many exact zeros, because the pipeline zero-fills gaps. Imputed zeros cannot be told apart from true zeros without `feature_provenance.json`, which is not opened.
- Government features of 2021-Q1 rows need 2020-Q4, which lies outside the window. They are left **missing (NaN), not 0**. LightGBM handles them natively; logistic regression uses the training-median imputation.

## 2. Label (target) availability

**Label.** HIGH if S1 > 14.6, where S1 = H + 2D (the implemented Eq. 3 label; 14.6 is the recorded global median).

**When a label counts as published before O.** The label of quarter q is treated as published before O only if:

- q ≤ t−1, because provincial CPI for q is released about 3 weeks after q ends;
- **and** every production-series SWS round of q was published before O.

**Gaps.** Quarters without a production SWS round (2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3) have **no label**. They are never imputed.

| Label quarter group | HIGH at 14.6 |
|---|---|
| 2021 | 3/15 |
| 2022 | 4/15 |
| 2023 | 5/20 |
| 2024 | 18/20 |
| 2025 | 9/10 |

**The class balance shifts strongly over time.** The 14.6 threshold was computed over all 120 province-quarters of 2020–2025, so the label itself uses information from the whole period. That is the implemented definition, and it is not changed here. The eligible-data median is 14.345. No S1 value lies within 0.001 of 14.6.

## 3. Departures from the implementation (all disclosed)

| # | Implementation | E17 | Why |
|---|---|---|---|
| D1 | Training rows: "all rows whose target quarter precedes the test quarter" | **Only rows whose label was published before the origin** | The implemented rule lets labels that are not yet published (for example the label of quarter t at k = 1) into training. That breaks Rule 3, "No Look-Ahead". The implemented rule is reported as sensitivity **R0**. |
| D2 | `poverty_incidence` included "as published" | **Excluded** | The stored values do not follow the release dates (§1). R0 includes it. |
| D3 | Missing government lags and `sws_hunger` filled with 0 | **Left missing** | 0 is not a measured value |
| D4 | Data from 2020-Q1 | **From 2021-Q1** | Study window 2021–2026 (standing rule). R0 also uses 2021+, so it does not exactly reproduce the recorded 0.818. |
| D5 | SWS release dates from `timing_audit.py` (for example, 2025-Q4 recorded as released 2026-05-12) | **Verified per-round dates from E12** (2025-Q4 round published 2026-01-14) | The later, verified record. The two records disagree. |

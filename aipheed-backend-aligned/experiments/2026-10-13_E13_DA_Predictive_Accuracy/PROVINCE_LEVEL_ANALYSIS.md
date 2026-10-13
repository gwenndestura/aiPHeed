# Province-Level Analysis (E13)

**Sources:**

- `runs/20261013T022702Z/province_event_tables.csv`
- `metrics.json` → `results`, `external`

Each province has **11 test quarters** (2023-Q2..2025-Q4). Rows within a quarter are not independent: D sums to zero across the five provinces.

**Regional hunger (target A) has no provincial values,** so it does not appear here.

## 1. Provincial food inflation (B1): MAE by province, percentage points

| Province | Mean realized F | B1_cf | B1_regional | B1_ridge_F | F > 4% events | cf balanced accuracy |
|---|---|---|---|---|---|---|
| Batangas | 3.68 | 1.93 | 1.92 | 2.54 | 4 | 0.86 |
| Cavite | 3.68 | 2.24 | **1.95** | 2.49 | 3 | 0.65 |
| Laguna | 3.98 | **1.35** | 2.10 | 1.44 | 4 | 0.66 |
| Quezon | 4.66 | 4.22 | 4.57 | **3.31** | 5 | 0.47 |
| Rizal | 3.79 | 2.48 | **1.84** | 2.82 | 4 | 0.86 |

**Reading:**

- **Quezon is the hardest province by far.** Its food inflation moved differently from the other four (see §2).
- **No arm is best in every province.** Province-specific carry-forward beats the regional mean only in Laguna and Quezon.
- **For absolute food inflation, the provincial detail adds little.** Overall, B1_cf scores 2.44 and B1_regional 2.48.

## 2. Relative food-price pressure (B2): MAE by province

| Province | Mean realized D | B2_zero | B2_cf | B2_ridge_D | B2_ridge_DP | D > 0 events | Balanced accuracy (cf / ridge_DP) |
|---|---|---|---|---|---|---|---|
| Batangas | −0.28 | 1.11 | 1.07 | **1.01** | 1.05 | 4 | 0.86 / 0.73 |
| Cavite | −0.28 | 0.91 | 1.04 | **0.85** | 0.96 | 4 | 0.61 / 0.61 |
| Laguna | 0.02 | 0.84 | 0.99 | 0.81 | **0.81** | 6 | 0.47 / 0.55 |
| Quezon | **+0.70** | 2.73 | 2.47 | 2.26 | **2.21** | 6 | 0.73 / 0.73 |
| Rizal | −0.17 | 1.26 | 1.20 | 1.02 | **0.89** | 4 | 0.86 / 0.93 |

**Realized D by province** (`scored_rows.csv`) shows the ranking reversal behind the largest errors:

| Province | 2023-Q2..2024-Q1 | 2024-Q2..2025-Q1 | 2025-Q2..Q4 |
|---|---|---|---|
| Quezon | −3.3 to −2.3 (lowest) | **+3.6 to +5.2 (highest)** | +1.2 to −0.1 |
| Rizal | +0.6 to +2.3 | −0.4 to −2.1 | −2.0 to −0.1 |
| Batangas | +0.7 to +1.7 | −0.7 to −2.0 | −0.3 to −1.8 |
| Cavite | −0.2 to +1.1 | −0.8 to −2.1 | −0.5 to +0.7 |
| Laguna | −1.4 to +0.6 | −1.4 to +0.3 | +0.6 to +1.5 |

**Reading:**

- **The improvement of B2_ridge_DP over carry-forward is spread across provinces** (lower MAE in all five). It is largest in Rizal (−0.32) and Quezon (−0.26). It is small in Batangas (−0.03).
- **The model weights each province's own history negatively.** Its raw coefficients are D(T−2) × 0.74–1.06, minus 0.34–0.59 × the province's 2021..T−2 mean D, with the same sign in all 11 folds. The model expects a province that has run above the regional average to come back down. That fits the Quezon and Rizal reversals of 2021–2025. **It is a pattern of this period, not an established property of provincial food prices.**
- **In 2024-Q2 and 2024-Q3, every arm has errors of about 2 points or more.** The reversal was not visible at T−2.

## 3. Price pressure against household vulnerability (descriptive; n = 5 per year, no inference)

| Year | Province | Mean F | Mean D | Subsistence incidence, % (CV) | 2021 LGU poverty median, % |
|---|---|---|---|---|---|
| 2021 | Batangas | 5.65 | −0.34 | 0.6 (34.8) | 7.1 |
| | Cavite | 4.27 | −1.72 | 1.5 (31.6) | 4.3 |
| | Laguna | 6.28 | 0.30 | 1.5 (24.3) | 4.2 |
| | Quezon | 6.84 | 0.86 | **4.7 (17.3)** | **16.8** |
| | Rizal | 6.89 | 0.91 | 0.6 (34.2) | 3.5 |
| 2023 | Batangas | 8.39 | 1.12 | 0.8 (33.9) | — |
| | Cavite | 8.01 | 0.73 | 0.4 (53.3) | — |
| | Laguna | 6.32 | −0.96 | 0.8 (35.0) | — |
| | Quezon | 4.56 | **−2.71** | 0.5 (38.5) | — |
| | Rizal | 9.09 | 1.82 | 1.5 (24.5) | — |

**Spearman correlation between mean D (or mean F, which gives the same ranking within a year) and:**

| Comparison | ρ |
|---|---|
| Subsistence incidence, 2021 | −0.05 |
| Subsistence incidence, 2023 | +0.62 |
| 2021 LGU-poverty median | −0.30 |

**Reading:**

- **Relative food-price pressure does not track household vulnerability across provinces.** Quezon is the poorest province by both PSA measures in 2021. In 2023 it had the **lowest** relative price pressure.
- **The 2023 subsistence values are unreliable.** Four of five have CV above 30%, and their confidence intervals overlap almost completely. The +0.62 rests on Rizal's single reliable value.
- **These are n = 5 comparisons on income-based measures,** not food insecurity. They show only that D is a price signal and not a vulnerability signal. A provincial prioritization for DA would need both.
- The 2021 LGU poverty file holds only 16 LGU-specific values out of 142. The rest are province means.

## 4. What the province level can and cannot support

| Question | Answer |
|---|---|
| Which province's food prices rose faster than the regional average? | **Yes.** D is measured every quarter for all five provinces. |
| Which province's relative price pressure is expected next quarter? | **Weakly.** Mean Kendall τ is 0.40–0.45. The sign is right in about 70% of cases. 2024-Q2 shows that the ranking can reverse. |
| Which province has the most food insecurity, now or next quarter? | **Cannot be answered.** No provincial food-insecurity outcome exists. |
| City or municipal predictions | **Not supported.** No city or municipal outcome or price series exists in the project. None was created. |

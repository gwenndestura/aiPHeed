# E119 data cleaning report

**Built by** `runner/preprocess.py` under the frozen protocol (`E119_PREPROCESSING_PROTOCOL.md`, hash checked at every run). Raw inputs are read only. Their SHA-256 values are checked before and after the run (`out/manifest.json`).

## 1. What was cleaned

| Step | Rule applied | Result |
|---|---|---|
| Date restriction | Every series filtered to periods from 2021-01 / 2021-Q1 before any derived value is computed | 256 cleaned series. None has a pre-2021 period (automated check). |
| Province names | Cavite, Laguna, Batangas, Rizal, Quezon. Quezon City (NCR) excluded; Lucena (HUC) not merged into Quezon | 5 provinces in every provincial table |
| Coarser units | Region IV-A, Balance Luzon and national values kept under their own unit | No regional or national value appears in the provincial dataset (`E119_GEOGRAPHIC_ALIGNMENT_REPORT.csv`) |
| Monthly → quarterly | Prices: mean of the 3 published months, plus within-quarter CV (volatility). Rainfall: total (mm/day × days in month). Temperature: mean | A quarter with fewer than 3 published months is left missing, never a partial mean |
| Quarterly production | As reported. Fisheries and aquaculture use the published TOTAL row. Vegetables use top-level crop rows only (".." rows are sub-items). Livestock = sum of 4 animals | A first run summed TOTAL plus sub-items for aquaculture (double counting). Fixed. Aquaculture is now 30–65% of total fisheries. |
| Pre-2021 bases | YoY now drops every pre-2021 value before computing. The new test found that palay/corn/fisheries production and wholesale rice YoY for 2021 had used 2020 bases in a first run. | Fixed; a run check now stops if any computed change starts before 2022-Q1 |
| Zero bases | YoY where the base is 0 is left missing (not ±inf) | Affects a few production quarters |
| Annual indicators | V1, subsistence (2021, 2023), FIES 2023 food share and the owner's annual employment file stay annual in `E119_PROVINCIAL_ANNUAL_INDICATORS.csv` | Never spread into quarters |
| Commissioned SWS round | The 2025-Q1 Stratbase round is excluded (E114 non-commissioned series, as in E109) | — |
| Missing values | Never zero-filled, interpolated or imputed | Reason recorded per feature (`E119_MISSING_DATA_REPORT.csv`) |

## 2. Outliers (flagged, investigated, all kept)

Rule: a change larger than 6 robust SDs (MAD) of the series. **34 flags** (`out/outlier_flags.csv`). None was removed.

| Group | Flags | Reading |
|---|---|---|
| Quezon rice prices (wholesale 2025-Q3 to 2026-Q2; retail 2024-Q2, 2026-Q2) | 6 | Consistent with the 2024–25 rice price fall after the rice tariff cut and the later rebound. Treated as market movement (not verified against a second source). |
| Production YoY on small bases: Laguna corn 2025-Q2 +749%; Cavite corn 2025-Q3; Rizal aquaculture 2022-Q2; Quezon aquaculture 2024 | 8 | Very small base quarters. The level series are plausible, so the percentages are arithmetic, not errors. |
| Cavite and Laguna fisheries/aquaculture 2021-Q2 to 2022-Q4 | 9 | Large seasonal harvest swings, e.g. Cavite aquaculture 7,670 t then 66 t. Published values; not checked against a second source. |
| C4 Cavite 2022-Q3 | 1 | Follows from the fisheries YoY above |
| Temperature Q2 peaks (Cavite, Rizal) | 5 | Q2 is the hot season. Expected seasonal jump from Q1. |
| Volatility CV (Rizal rice 2023-Q3, Batangas tilapia 2021-Q4) | 2 | The CV of three months is noisy by nature |
| Chicken production Cavite 2025-Q4; farmgate palay Rizal 2026-Q1 | 2 | Single-quarter jumps; kept |
| N1 admitted articles Cavite 2024-Q3 (43) | 1 | A real spike in admitted articles (dated corpus); likely the 2024-Q3 typhoon and flooding coverage |

**Note for modeling.** Percentage changes on small production bases are extreme but real. A model should use a robust transform, such as a sign-preserving log or winsorizing *inside the training folds*. This preprocessing does not alter them.

## 3. Redundancy checks (provincial dataset)

| Pair | Rows | r |
|---|---|---|
| Bottom-30% food CPI YoY vs food CPI YoY | 110 | 0.94 (largely redundant) |
| Retail rice YoY vs wholesale rice YoY (A3) | 85 | 0.70 |
| Retail chicken YoY vs food CPI YoY | 90 | 0.44 |
| Farmgate palay YoY vs wholesale rice YoY | 85 | 0.43 |
| Typhoons within 100 km vs within 300 km (C2) | 110 | 0.38 |
| Aquaculture YoY vs C4 fisheries drop | 85 | −0.21 (expected sign; aquaculture is part of fisheries) |

## 4. What was not done

- No value was edited by hand.
- No release date was invented. Rule-based dates are labelled `rule_unverified`.
- Nothing before 2021 was used as a base: no YoY, anomaly, threshold or volatility.

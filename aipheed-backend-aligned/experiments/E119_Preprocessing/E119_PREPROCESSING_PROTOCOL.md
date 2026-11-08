# E119 preprocessing protocol (frozen 2026-10-31, before any dataset is built)

**Hash.** This file's SHA-256 goes in `runner/PROTOCOL_SHA256.txt`.

**Scope.** Data preprocessing only. No model is trained. Production, dashboard, raw files and FIRI v2 definitions are unchanged.

## 1. Organizing principle: the 12 FIRI v2 indicators

**Authoritative definitions.** `backend/app/ml/inference/firi.py`: `LABELS` and `DOMAIN_OF`. Five trigger domains (ADDENDUM_1):

| Domain | Indicators |
|---|---|
| Market / prices | A1, A2, A3 |
| Fish production | C4 |
| Climate | C1, C2, C3 |
| Employment | E1 |
| OFW remittances | E2 |

Other required inputs: N1 (news), V1 (poverty) and H1 (regional hunger).

**Mapping rules.**
- Every dataset is mapped to the indicator whose definition it matches, as **direct** or **supporting**.
- A dataset whose meaning matches no indicator is kept as **unassigned (domain support)**. Examples: rainfall and temperature, vegetable and livestock production.
- No dataset is forced into an indicator.

**FAO's four dimensions** are a secondary label only.

## 2. Date restriction

**Modeling observations start 2021-01-01.**
- Every derived statistic (YoY, anomalies, thresholds, volatility, lags) uses only observations from 2021 onward. So computed YoY features start in 2022.
- **Exception, stated explicitly:** YoY values *published by PSA* for 2021 months (CPI YoY) are official 2021 observations. They are not computed by this pipeline from 2020 data, so they are kept.
- A1/A2 use projection bases ≥ 2021-01 (E107 rule) and thresholds from published quarters since 2021-Q1 (corrected pipeline).

## 3. Cleaning and standardization

**Geography.**
- **Province names:** Cavite, Laguna, Batangas, Rizal, Quezon. Quezon City (NCR) is excluded; Lucena (HUC) is separate.
- **Coarser values stay coarse:** Region IV-A, Balance Luzon and national values remain at their own resolution and are never copied to provinces.

**Time.**
- **Monthly → quarterly:**
  - prices: quarterly mean of 3 published months, plus within-quarter coefficient of variation (volatility);
  - rainfall: quarterly total in mm (monthly mean mm/day × days);
  - temperature: quarterly mean.
- **Quarterly production:** original reported values.
- **Annual and static indicators:** stay annual, in their own table.

**Outliers.** Flagged where |change| exceeds 6 robust SDs (MAD) of the series. They are investigated, never removed.

**Missing values.** Never zero-filled, interpolated or imputed. Each missing value carries a reason.

## 4. Availability (point-in-time)

Each observation gets an availability date and a status:
- **verified:** a dated source precedes the issue;
- **rule_unverified:** a documented release rule only.

| Source | Rule | Status |
|---|---|---|
| CPI month m | day 10 of m+1 | verified where the release ledger has an archived PSA release |
| Retail / farmgate / wholesale prices, month m | day 15 of m+1 | rule |
| PSA production, quarter q | first day of quarter q+2 | rule |
| LFS month m | first day of m+3 | rule |
| ONI month m | day 10 of m+1 | rule |
| NASA POWER month m | first day of m+2 | rule; values may be revised |
| IBTrACS typhoons, quarter q | first day of q+1 | verified (real-time observation) |
| News (FSSI, GDELT), quarter q | first day of q+1 | verified (dated articles) |
| PAGASA ENSO items | issue date | verified |
| SWS rounds | published date | verified |
| Remittances | first dated report | verified where every needed report is dated before the issue; otherwise rule |
| Subsistence incidence | publication date | verified |
| V1 | 2025-07-01 | verified for later issues |
| Owner annual employment, year Y | 30 June of Y+1 | rule (no publication dates in the file) |

**As-of rule.** Origin t has issue O(t) = day 1 of quarter t+1. A feature takes its latest period whose availability date is strictly before O(t).

**Strict view.** Only `verified` values. **Provisional view:** both statuses.

## 5. Datasets

**A. Regional forecasting dataset.**
- **Rows:** origin t (2021-Q1 to 2026-Q3) × lead k ∈ {1, 2}.
- **Target:** SWS Balance Luzon Total Hunger of quarter t+k. Source: E114's non-commissioned series from SWS tables; the commissioned 2025-Q1 Stratbase round is excluded, as in E109.
- **Predictors:** at their own resolution (Region IV-A, Balance Luzon, national).
- **CALABARZON rainfall:** the mean of the five province-centroid points, labelled as a derived regional proxy.
- **Provincial values are not used as labels.**

**B. Provincial vulnerability dataset.**
- **Rows:** province × origin (2021-Q1 to 2026-Q3), as of each issue.
- **No food-insecurity label.**
- **Annual provincial indicators** (V1, subsistence incidence, FIES food share, annual employment) are a separate annual table.

**C. Unified 12-indicator dataset.**
- Long format: unit, resolution, origin, indicator, feature, value, observation period, availability date, status.
- National and regional values appear once, under their own unit.

## 6. Leakage checks (automated; the run stops on failure)

1. Every feature's observation period is before the target quarter.
2. Every feature's availability date is before the issue.
3. No target or target-derived value is a predictor. The SWS history uses only rounds published before the issue.
4. Every derived statistic uses only observations available at the issue and from 2021 onward.
5. No observation before 2021-01 enters any modeling file.
6. No imputation.
7. Raw inputs keep their SHA-256.

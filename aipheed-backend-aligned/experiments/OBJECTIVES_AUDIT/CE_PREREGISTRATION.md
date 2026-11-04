# C-E pre-registration: C-b + employment + OFW remittances (fixed before any fit, 2026-11-03)

**Purpose:** bring the two dashboard driver groups that C-b lacks (Employment, OFW Remittance) into the forecast,
with real data, and measure whether they help.
- **Development evidence;** the 17th historical attempt.
- **C-b stays the main model** unless C-E passes the adoption rule *and* the team and adviser approve. Serving C-E is
  a separate decision.

## Inputs added to C-b's 21 (23 in total)

| Name | Definition | Source | Cut-off at O(t) |
|---|---|---|---|
| `E1` (employment) | Change in the national unemployment rate: last three months to the quarter before t vs a year earlier (`hr_lib._e1`, already in the input table) | PSA Labor Force Survey (national) | Months published before O(t) (existing rule) |
| `E2` (OFW remittance) | −(YoY % change of personal transfers, quarter t−2 vs t−6): a remittance decline | IMF BOP `PHL.CD_T.D752_S1W.USD.Q` (`LEAD2_RELIABILITY_RESEARCH/y15…/data_acquired/remittances_quarterly_usd_mn.csv`), validated against BSP cash remittances (r = 0.997) | Quarter t−2 only (≥ 6 months after quarter end; Y15 rule, conservative vs BSP's ~3-month BOP lag) |

**Both are national**, the same for every province, so they cannot differentiate provinces.

**Missing values stay missing:** E1 is absent before 2006, E2 before 2000-Q3.

## Fit and evaluation

**Fit:** exactly as C-b: the same grid, inner selection, seed, walk-forward from 1998-Q3, stacked leads 1–8.

**Pre-checks:**
- the C-b refit reproduces stored C-b (≤ 1e-12);
- E2 is unchanged when remittance values for quarters ≥ t−1 are randomized (5 reps).

**Reported:**
- all metrics, R1–R7 and Algorithm 3;
- a 14-test Holm family (C-E × 7 baselines × 2 leads);
- paired Brier vs C-b;
- **SHAP share of E1 and E2 per forecast and on average**, whatever it is. No weight is forced.

## Gates

| Gate | Condition |
|---|---|
| G1 | All 14 comparisons significant |
| G2 | Brier < C-b at both leads, p < 0.10, accuracy not lower |
| G3 | R1–R7 at both leads |
| G4 | MRLT ≥ 2 |
| G5 | R7 fixed |

**Adoption:** G2 and G4, plus team and adviser approval.

**Even if adopted,** Employment and OFW bars on the dashboard show the model's measured SHAP: a forecast in which the
model did not use them shows 0%.
PLAN-SHA256: bde69c08820ece1d38ab6f6824384dbb20306117be1c733db4b4da99d6a9f10f

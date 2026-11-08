# Lead-2 error analysis (served model P0H0 = UNI-FINAL)

**Source.** Every Lead-2 row with all inputs and publication dates is in `out/lead2_cases.csv`, exported by `runner/posthoc.py cases`.

**Decision rule.** HIGH at P ≥ 0.50.

**Target.** T43c = [BL hunger(q) > 11.3] AND [province food YoY > food P60, or food − headline gap > gap P60]. The thresholds are the 2021–22 P60s; the code matches Chapter I (`ch1_lib.labels`, `e108_lib.ps_frame`, `e41_lib.e40_spec`).

**Rows.** 65 rows (13 target quarters × 5 provinces); 17 HIGH.

| | Predicted HIGH | Predicted LOW |
|---|---|---|
| **Observed HIGH** | TP 6 | **FN 11** |
| **Observed LOW** | FP 4 | TN 44 |

**What Lead 2 means in time.** The forecast is issued on the first day of quarter t+1 and targets quarter t+2. The newest SWS reading at issue is for quarter t−1 (true horizon 3 quarters). The newest CPI month is month 2 of quarter t (5–7 months before the target months).

## The 11 missed HIGH cases

| Issue date | Target | Province | Newest SWS at issue (published) | π_H | π_P | P | A1_food / A1_gap | Main cause | Could issue-time data have caught it? |
|---|---|---|---|---|---|---|---|---|---|
| 2023-07-01 | 2023-Q4 | Laguna | 2023-Q1 8.7 (2023-05-11) | 0.26 | 0.49 | 0.13 | −5.3 / −0.9 | Hunger onset 8.7 → 14.3, and a price condition the projection did not show | **No.** Both triggers came after the issue date (rice surge Aug–Sep 2023; India's export ban 20 Jul 2023). |
| 2023-07-01 | 2023-Q4 | Quezon | same | 0.26 | 0.49 | 0.13 | −7.7 / −0.9 | same | **No** |
| 2023-07-01 | 2023-Q4 | Batangas | same | 0.26 | 0.49 | 0.13 | −5.1 / −1.5 | same | **No** |
| 2024-01-01 | 2024-Q2 | Cavite | 2023-Q3 10.3 (2023-11-20) | 0.29 | 0.80 | 0.23 | −0.3 / +1.1 | **Hunger term only.** Price risk was flagged (rice CPI +11.7% YoY, world rice +35.9%). | **Partly.** The surge-signalling 2023-Q4 reading (14.3) was published 2024-01-22, **21 days after issue**. With the 1998+ hunger history (sample b), π_H = 0.61 → P = 0.49: still just below 0.50. |
| 2024-01-01 | 2024-Q2 | Laguna | same | 0.29 | 0.80 | 0.23 | −3.0 / +0.7 | same | Partly (as above) |
| 2024-01-01 | 2024-Q2 | Quezon | same | 0.29 | 0.68 | 0.20 | −3.0 / +1.7 | same | Partly |
| 2024-01-01 | 2024-Q2 | Batangas | same | 0.29 | 0.80 | 0.23 | −4.0 / +0.6 | same | Partly |
| 2024-04-01 | 2024-Q3 | Quezon | 2023-Q4 14.3 | 0.86 | 0.43 | 0.37 | −3.6 / **+0.6** | Price model; the structural gap projection was above its threshold | **Yes, plausibly.** The structural signal pointed to HIGH; the fitted model overrode it (Addendum 1 tests this). |
| 2024-07-01 | 2024-Q4 | Cavite | 2024-Q1 15.3 | 0.91 | 0.17 | 0.15 | −5.8 / −2.1 | Price condition arose after issue | **No.** The structural projection was clearly below threshold. The Q4 2024 food-price rise followed the Oct–Nov 2024 typhoons, after the issue date. |
| 2024-07-01 | 2024-Q4 | Laguna | same | 0.91 | 0.17 | 0.16 | −6.1 / −1.8 | same | **No** |
| 2026-01-01 | 2026-Q2 | Cavite | 2025-Q3 23.8 | 1.00 | 0.35 | 0.34 | −2.9 / −1.0 | Price condition arose after issue (rice deflation turned to inflation in 2026) | **No.** Rice CPI was −13% at issue. |

## Assessment

- **Hunger onset (7 rows: 2023-Q4 and 2024-Q2).** The latest-reading hunger term cannot exceed 0.50 here, which caps Lead-2 recall at 10/17 = 0.588.
  - 2023-Q4 had no warning in any issue-time input.
  - 2024-Q2 was 21 days of SWS publication delay away from being visible.
  - Only pre-2021 hunger history (sample b) lifts π_H above 0.5, and even then P stays below 0.50.
- **Price after the issue date (4 rows: 2023-Q4 counted above, 2024-Q4 ×2, 2026-Q2).** The price shock had not begun by the issue date; no issue-time input showed it.
- **Model override (1 row: 2024-Q3 Quezon).** This is the only miss where the issue-time structural signal was right and the fitted model was wrong.
- **Conclusion: at most 1–5 of the 11 misses were catchable with information available at issue time.**
  - 1 = the 2024-Q3 Quezon model override;
  - up to 4 more = the 2024-Q2 rows, but only with pre-2021 hunger history and a price probability ≥ 0.82.
  - The rest were caused by events after the issue date.
  - This is a data-information limit, not a tuning limit.

## False alarms (4 rows)

| Issue date | Target | Province | P | Observed |
|---|---|---|---|---|
| 2024-04-01 | 2024-Q3 | Laguna | 0.55 | Hunger HIGH, price LOW |
| 2025-01-01 | 2025-Q2 | Cavite | 0.64 | Hunger HIGH, price LOW |
| 2025-04-01 | 2025-Q3 | Cavite | 0.71 | Hunger HIGH, price LOW |
| 2026-01-01 | 2026-Q2 | Laguna | 0.58 | Hunger HIGH, price LOW |

All four are price-condition false alarms in quarters where hunger was HIGH.

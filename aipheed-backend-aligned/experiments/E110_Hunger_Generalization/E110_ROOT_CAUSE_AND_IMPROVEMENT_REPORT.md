# E110 Root cause and improvement report

**Starting point.**
- **Branch:** E109 `00937d0` → E110 `aiPHeed/e110-hunger-generalization`.
- **Window:** 2021 onward only.
- **Seals preserved:** E107 `246700a8…`, E108 `fbc8bf91…`, E109 `61bcc353…` (re-hashed by test).
- **Diagnosis:** `out/diagnosis.json` (`runner/diagnose_e109.py`), from E109 data and predictions; no model scored.

## 1. Why the latest SWS reading was hard to beat in E109 (verified)

| # | Root cause | Evidence |
|---|---|---|
| R1 | **"Lead 1" is really two quarters ahead of the latest reading.** SWS publishes a median of 29 days after the quarter ends (range −24 to 84 days), so at the issue date (day 1 of the quarter) the newest posted round is usually two quarters before the target. | 8 of 9 E109 Lead-1 rows had a gap of 2 quarters, 6 of 7 Lead-2 rows a gap of 3 |
| R2 | **A large part of each quarter-to-quarter change is survey noise.** | Changes: SD 4.56 points, mean absolute 3.89. The noise SD of a change is 2.9 (±4% rounds) to 4.3 (±6% rounds), i.e. **40–90% of the change variance**. Lag-1 autocorrelation of changes −0.45, the signature of noise. |
| R3 | **The level shifted, with no forewarning in the data.** | Mean 10.9% (2021-Q2–2023-Q3, SD 2.0) → surge to 25.3% (2024-Q4) → 20.0% in 2025–26 (SD 3.6, alternating 16–17 / 22–24). |
| R4 | **The 2025 respondent and design changes.** | Respondents changed from household heads to registered voters to adults. In 2025–26, March, April and September rounds are 1,500-sample (Balance Luzon n = 600, ±4%) and June and November are 1,200 (n = 300, ±6%). Design and season are confounded. |
| R5 | **Too few training and evaluation quarters.** | 20 outcome quarters; E109 had 8–16 training pairs and 9 / 7 / 6 / 5 evaluable quarters at Leads 1–4. |
| R6 | **The indicators carry little information about hunger changes.** | Full-sample correlations with the next change (descriptive, n = 17–18): price A1 −0.2, rice A3 +0.3, El Niño C1 +0.4, FSSI N1 −0.6 (Lead 2, few values). None is stable or causal. V1 is constant at the regional level. |

**Conclusion of the diagnosis.** The limits come from the target, the survey and the data volume, not from the choice of algorithm. A more flexible learner cannot fix R1–R5.

## 2. What E110 tried, and why

| Hypothesis | Change | Result (development evidence) |
|---|---|---|
| H1: learning hunger dynamics needs more data. Other SWS areas measure the same thing with the same timing. | Collected the in-window **SWS area series** (Metro Manila, Balance Luzon, Visayas, Mindanao; 23 rounds, 2021–2026) and verified each against SWS releases or reports of them (`data/sws_area_rounds.csv`). Evaluated on a 4-area panel. | Evaluation evidence rose from 9 to 10 quarters at Lead 1 (40 area-quarters) and from 7 to 8 at Lead 2 (32). It is still short, because every area needs 6 known quarters first. |
| H2: survey noise makes the last reading over-reactive; a noise-aware filter should help. | **LLR:** local-level filter with each round's **published** margin and state variance pooled over 4 areas. **COMB:** average of RW and LLR. | **Lead 1:** no gain (panel MAE RW 5.26, COMB 5.25, LLR 5.46). **Lead 2:** consistent average gain in all 4 areas (RW 6.12 → LLR 5.39; COMB p = 0.098), but it **fails generalization**: the smoothers lose 1–4 points during the 2024 surge and only win in 2025–26. |
| H3: national indicators (El Niño advisory, unemployment, remittances) explain hunger changes across areas. | **NAT-R:** pooled ridge on LLR residuals, C1, E1, E2, all 4 areas | **Clearly worse** (Lead-1 panel MAE 7.45 vs 5.26). These indicators add noise. |
| H4: the 12 FIRI families add information beyond the structural forecast (required LightGBM). | **LGBM-R / RIDGE-R:** residual on LLR, 13 columns, Balance Luzon | **Insufficient evidence:** training needs LLR forecasts at earlier origins, leaving 5 evaluable quarters at Lead 1 and 2 at Lead 2. LGBM-R 2.46 vs RW 2.11 at Lead 1 (5 quarters). |
| H5: the 2025 alternation is a design effect. | LLR residuals by round design, 2025–26, all areas | **Not consistent.** Balance Luzon (+2.5 vs −1.4) and Metro Manila (+2.8 vs −0.8) read higher in 1,500 rounds; Mindanao (−1.3 vs +3.4) and Visayas (−1.0 vs +0.8) the reverse. Inconclusive, and confounded with season. |

## 3. What improved and what did not

**Improved:**
1. **Data credibility.**
   - All 23 Balance Luzon values now match SWS (E109 checked 12).
   - Area data, sample sizes and margins are recorded per round.
   - The commissioned and registered-voter rounds are identified.
2. **Understanding.**
   - The publication-lag structure of "Lead 1" (R1).
   - The noise share (R2).
   - Why smoothing helps in calm periods but hurts during surges.
3. **Evidence breadth.** The method is now tested on 4 areas, not 1.

**Did not improve:** forecast skill beyond persistence at Lead 1, and any lead that generalizes. No indicator family demonstrably improves hunger forecasts.

## 4. Remaining constraints (data, not code)

- **Quarters:** only 20 outcome quarters from 2021; each lead loses 6–8 of them to the training requirement.
- **Geography:** one regional Balance Luzon value per quarter; no provincial or municipal hunger data.
- **Survey design:** the 2025 changes split the short series into two regimes.
- **Indicator coverage:**
  - FSSI-v3 is sparse;
  - remittances end in 2025-Q4;
  - V1 is constant over time;
  - the CALABARZON-specific families do not describe the other three SWS areas, so they cannot be pooled.

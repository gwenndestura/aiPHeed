# E58 final validation verdict

**Audit:** E59, 2026-10-18.
- Evidence is in this folder; scripts are in `runner/a1`–`a5`.
- Nothing frozen was changed. Nothing was committed, pushed, deployed or switched.

## 1. Verdicts

| Area | Verdict | Evidence (file) |
|---|---|---|
| Software functionality | **Supported** | Backend 402 passed / 18 skipped; frontend tsc + 45 vitest; E58 serving tests pass; local dashboard renders E58 warnings (E58 `tables/dashboard_review.json`) |
| Reproducibility | **Supported** | Every E57/E58 figure recomputed exactly; E56 re-executed at all 10 origins (diff 5e-13) (`E58_REPRODUCIBILITY_AUDIT.md`) |
| Forecast timing / no identified leakage | **Supported** | Truncation test identical at all 10 origins; all SWS rounds posted before issue; conservative CPI lag (`E58_TARGET_AND_DATA_VALIDITY.md` §3). Design-level dependence on the evaluation quarters is disclosed. |
| Accuracy against observed labels | **Partially supported** | 0.78 pooled (CI 0.70–0.86); 7/10 quarters ≥ 0.75. Development rows only. |
| Consistency across quarters | **Partially supported** | Quarter accuracy 0.6–1.0 (SD 0.15); three quarters at 0.6; two perfect quarters had no HIGH row (`E58_CROSS_QUARTER_EVALUATION.md`) |
| HIGH-risk detection | **Partially supported** | HIGH recall 0.778 (CI 0.50–1.00), precision 0.667; 4 misses, all price-driven |
| Rising-food-stress early warning | **Partially supported (narrow)** | 7/10 onsets vs E56 3/10, but all of the gain is one episode (2024-Q2). A three-week-later issue date gives E56 the same result (S1). The projection-only rule is equivalent. 6–8 months of lead before the outcome is observable. |
| Calibration / statistical uncertainty | **Not supported** (calibration); uncertainty quantified | CITL −0.10, slope 0.75. EW vs E56: quarter sign test p = 1.0, Brier CI includes 0 (`E58_GENERALIZATION_AND_SIGNIFICANCE.md`) |
| Generalizability | **Not supported** (Pending prospective) | One hunger regime; no untouched historical quarter; untested in a low-hunger regime |
| Superiority to required baselines | **Partially supported** | Beats all six SOP-Q3 baselines on 45 common rows (accuracy, balanced, Brier). Only the Brier advantage over majority / climatology excludes 0 under quarter bootstrap; the persistence advantage is not significant at quarter level. Not superior to E56 or the projection rule. |
| Target validity as food-insecurity risk | **Partially supported** | Chapter I-consistent SWS + PSA composite, but on all 50 evaluated rows it equals provincial food-price pressure; no provincial hunger or food-insecurity outcome; no FNRI anchor |
| Five triggers used as claimed | **Partially supported** | Market used throughout; climate, employment and OFW intermittently from 2025; fisheries marginal; fish-kill and NLP shares essentially empty (`E58_TRIGGER_IMPLEMENTATION_AUDIT.md`) |
| Compliance with Chapter I objectives | **Partially supported** | Obj 4 achieved on development data; Obj 1, 2, 3, 5 partial; lead-time evaluation missing (`E58_THESIS_OBJECTIVE_AUDIT.md`) |
| External validation by DA IV-A (and DEPDev IV-A per SOP Q5) | **Pending** | No respondent data exist; none were generated |

## 2. Final questions

| # | Question | Answer |
|---|---|---|
| 1 | Is E58 the model actually served by the dashboard? | **No.** The default is E38. E58 is served only with `AIPHEED_LEAD2_MODEL=e58`, in a local preview. Its commits are not pushed, so it is not deployed. |
| 2 | Does E58 predict the target required by the thesis? | **Partially.** It predicts a SWS + PSA composite risk indicator, as Chapter I describes. It is not the Eq. 3 additive form (which E38 serves), and not FNRI-anchored. On every evaluated row it equals provincial food-price pressure. |
| 3 | Is the forecast timing correct and free from identified leakage? | **Yes.** No future-data leakage was found at any of the 10 origins. The evaluation quarters did inform the design (disclosed). |
| 4 | Does E58 achieve ≥ 75% accuracy on the eligible cross-quarter evaluation? | **Yes**, 0.78 on 50 rows. The 95% CI (0.70–0.86) includes values below 75%, and these are development rows. |
| 5 | Is its accuracy reasonably consistent across quarters? | **Partially.** 7 of 10 quarters ≥ 0.75; the others are at 0.6. |
| 6 | Does it meaningfully identify both HIGH and LOW risk? | **Partially.** HIGH recall 0.778 and LOW recall 0.781 pooled. Within-quarter separation of provinces is weak in several quarters, and Cavite is at 0.5. |
| 7 | Does it detect rising food stress early enough to support planning? | **Partially.** Warnings come 6–8 months before outcomes are observable, and 7 of 10 onsets were warned. The improvement rests on one episode, and the three remaining misses are unforeseen price rises. |
| 8 | Does it outperform the required baselines on comparable observations? | **Partially.** It is higher than all six on 45 common rows. It is statistically supported only on Brier against majority / climatology, and it is not better than E56 or the projection rule. |
| 9 | Are its results statistically supported? | **No.** Apart from the narrow Brier advantage over the majority rule, no claimed improvement survives quarter-level testing. |
| 10 | Is its performance generalizable beyond the evaluation period? | **Pending.** It is not established: one hunger regime, and design-informed quarters. The frozen 2027 forecasts are the test. |
| 11 | Are all five trigger compositions implemented and used as claimed? | **Partially.** All are inputs and displayed. Only Market is materially used, and fish-kill and NLP signals are essentially empty. |
| 12 | Is there enough evidence to call E58 a validated food-insecurity risk forecasting model? | **No.** |
| 13 | Chapter I objectives | Obj 1 **partially**; Obj 2 **partially** (no lead-time study); Obj 3 **partially** (rankings built, forecasts not validated); Obj 4 **achieved on development data**; Obj 5 **partially** (dashboard built; ISO 25010 and FNRI face validity **pending**) |
| 14 | What still requires future outcomes or external validation? | 2027-Q1..Q4 SWS and CPI outcomes for the frozen forecasts and their EW levels; the DA IV-A ISO/IEC 25010 and post-survey evaluation (H4, H5); an FNRI/FIES face-validity comparison; a provincial food-insecurity outcome (CBMS or provincial FIES) to validate the target itself; a multi-lead evaluation for Objective 2.V |

## 3. Recommendation

**1. Retain E38 as the production default for now.**
- E38's own target (Eq. 3) is saturated, and against T43 it scores 0.175. So it is not a better forecaster.
- It is kept because switching requires authorization, and E58 is not validated.
- This is a holding position, not an endorsement of E38.

**2. Retain E58 as the experimental early-warning approach** (`AIPHEED_LEAD2_MODEL=e58`). Describe it accurately:
- a LightGBM forecast of a SWS + PSA food-insecurity risk indicator;
- whose evaluated skill is provincial food-price pressure under elevated regional hunger;
- with an EMERGING warning that keeps an outdated hunger reading from suppressing a price warning;
- development accuracy 0.78 on 10 quarters;
- not validated.

**3. Do not change the model now.** No candidate is supported over E56/E58 by quarter-level evidence. A change chosen from these same quarters would not be independent.

**Minimum defensible next steps** (nothing here was implemented):
1. **Score the frozen 2027-Q1 forecast and its EW levels** when the 2027-Q1 SWS round and March 2027 CPI are published. Continue each quarter with forecasts frozen at issue.
2. **Decide the issue date** (adviser). Issuing after each quarter's SWS release would give E56 alone the EW result (sensitivity S1) and make EMERGING less necessary.
3. **Add a lead-time study** (Objective 2.V): lead 1, 2 and 3 under the same rolling-origin protocol.
4. **Obtain a provincial food-insecurity outcome** (CBMS FIES or provincial FIES/NNS) and test the T43 proxy against it.
5. **Conduct the DA IV-A ISO/IEC 25010 evaluation.** Correct the SOP Q5 reference to DEPDev if DEPDev is no longer a participant.
6. **Review the Chapter I wording** that promises a "validated forecast target" and an FNRI-anchored label. This is a proposed text change for the author, not made here.

## Correction to question 1 (2026-10-18, added during E60)

The branch with E58 **was pushed** to origin (88d5266). The code default remains E38.

Whether the live Render service serves E58 depends on its `AIPHEED_LEAD2_MODEL` setting, which this audit cannot see.

**Revised answer to question 1:** *No by code default; live status unverified.*

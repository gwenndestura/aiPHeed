# E111 Thesis objective assessment and final answers

## Chapter I objectives (§1.5.2)

| Objective | Status | Evidence |
|---|---|---|
| 1. NLP pipeline (FSSI-v3, BERTopic) | Partially achieved | It runs. FSSI-v3 adds nothing measurable to hunger forecasts (FAM-N1, Holm p = 1.0). |
| 2 I–IV. LightGBM metrics | Partially achieved | Reported, regional. The required 12-family LightGBM does not beat the latest reading (4.04 vs 3.72). |
| 2 V. Furthest reliable horizon (walk-forward) | **Not demonstrated** | No lead passes the frozen rule. Near misses: Lead 1 ASYM (fails the falling-hunger check) and Lead 2 LLR (fails the ±4 BL bound). |
| 3. Municipal rankings from validated forecasts | Not achieved | No validated provincial or municipal hunger forecast exists |
| 4. Comparison with baselines | Achieved | The latest reading is the strongest baseline. Simple smoothing beats it in specific settings; no indicator model does. |
| 5. Dashboard, ISO 25010, FNRI | Not in scope | The dashboard is unchanged |

## The eight required answers

**1. What was corrected or improved from E110.**
- **Corrected:**
  - the DM test now uses Newey–West (Bartlett) variance; E110's Lead-2 "significant" COMB result becomes p = 0.12;
  - the noise-share claim is restated as a wide range (17–72% at ±4, 39–100%+ at ±6);
  - the "±6-point 80% band" is withdrawn (coverage was 50–65%);
  - eligibility no longer depends on one model, so 13 rather than 10 quarters are compared at Lead 1.
- **Improved:**
  - a per-issue-date horizon table (Lead 1 = true horizon 2);
  - surge-cost and coverage criteria;
  - an asymmetric forecast (ASYM) that reduces surge underprediction.

**2. Does any method genuinely outperform the latest reading?**
- **On these quarters, yes in two settings, but neither meets the full rule:**
  - ASYM at Lead 1 (4.44 vs 4.84, p = 0.002);
  - LLR at Lead 2 (4.83 vs 5.53, p = 0.058).
- **These are development results on quarters already examined.** ASYM was designed after seeing E110's surge pattern.

**3. Does the improvement generalize across quarters?**
- **Across periods and leave-one-quarter-out:** yes, for both.
- **Across directions:**
  - ASYM: no (worse when hunger falls);
  - LLR (Lead 2): yes, but not within the ±4 accuracy bound.
- **Beyond these quarters:** unknown until prospective scoring.

**4. Does any method detect sharp increases in hunger?** No.
- Every method misses 80–100% of sharp increases.
- ASYM reduces the average underprediction by about 1.5 points.
- No indicator anticipated the 2024 surge.

**5. Which indicator families add measurable predictive value?** None.
- All 12 single-family screens: Holm p = 1.0.
- National families (C1, E1, E2) worsened pooled forecasts (E110).
- LightGBM with all 12 families is worse than the latest reading.

**6. Maximum reliable lead time supported by the 2021+ evidence:** none established. No provisional lead either.

**7. Claims that remain unvalidated pending future SWS observations:**
- every forecast skill claim, including ASYM and LLR;
- interval coverage;
- any lead time.

The E107–E111 seals become scorable from SWS 2026-Q4.

**8. The simplest credible method for the thesis.**
- **Forecast:** the latest published SWS Balance Luzon reading as the outlook.
- **Labels on the outlook:**
  - its true horizon ("two quarters past the newest survey");
  - its empirical error (about 3.3–3.7 points at Lead 1);
  - an explicit note that intervals under-cover;
  - "not validated".
- **What to report alongside it:** smoothing (ASYM for asymmetric costs; LLR two quarters ahead) as promising exploratory alternatives to be confirmed prospectively, not as the adopted method.

## Suggested Chapter IV wording

> Hunger was measured by the SWS Total Hunger rate for Balance Luzon, with the other three SWS areas used to test generalization. Because SWS results are published after a delay, a forecast issued at the start of a quarter is made two quarters after the newest survey reading.
>
> Under walk-forward evaluation from 2023 to 2026, no method met the pre-specified reliability criteria at any horizon. Two simple smoothing rules outperformed the latest reading on average: one at one quarter ahead, which never forecast below the latest reading, and one at two quarters ahead. However, the first was worse when hunger fell, and the second's errors exceeded the survey's ±4-point margin.
>
> The twelve-indicator LightGBM model and every single indicator family failed to improve on the latest reading. All forecasts missed the sharp 2024 increase in hunger. A reliable forecasting horizon was therefore not established with 2021–2026 data. Sealed forecasts will allow prospective confirmation as new SWS rounds are published.

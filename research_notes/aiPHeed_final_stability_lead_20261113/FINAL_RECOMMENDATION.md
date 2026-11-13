# FINAL (RATE + MIND): recommendation (2026-11-13)

## Direct answers

1. **Did the improved FINAL pass the stability-across-rounds rule?**
   - **Yes, narrowly.** FINAL-ET passes Rule 7: 2021 HIGH recall is 2 of 4, exactly the 0.50 floor, and every other Rule 7 check passes.
   - The pass hangs on one province of a 4-HIGH round. Training perturbations move that round's recall between 0.50 and 1.00 (FINAL: 0.25–0.50). It is not a robust result.
2. **Did it keep acceptable precision and probability reliability?**
   - **Precision: yes.** 0.70 (≥ 0.60).
   - **Probability reliability: no.** Mean probability exceeds the HIGH rate by +0.103 (limit 0.10) and the Cox test rejects (p = 0.031), because 2021 now over-predicts (four new false alarms).
   - FINAL-ET is **6 of 7, not accepted**. FINAL stays 6 of 7 (fails stability).
3. **What is the maximum reliable forecast lead time?**
   - **None established**, for either model.
   - FINAL fails at Lead 1 (stability). FINAL-ET fails at Lead 1 (calibration); its passes at Leads 4–5 do not count, because Leads 1–3 fail.
   - FINAL beats the persistence, PSA-only, regression and news-only baselines on Brier at every lead (43/48 significant). It deteriorates from Lead 1 to Lead 6 (balanced accuracy 0.85 → 0.73, recall 0.80 → 0.68).
4. **Does the model genuinely use the five dashboard trigger groups?**
   - **No.** FINAL uses poverty and social vulnerability (about 56–77 % of gain) and market and prices (15–28 %).
   - Climate is selected only as static exposure measures and changes no forecast.
   - Employment enters only as a news index in 16 of 110 fits and changes no forecast.
   - OFW remittances are not an input.
   - Genuine provincial employment data exist only from a January 2022 release (usable prospectively). No provincial remittance series exists.
5. **Which research objectives are completed?**
   - **Completed:** 1 NLP pipeline (as specified, DA-validated); 3 geospatial prioritisation; 4 baseline comparison (retrospective).
   - **Partially completed:** 2 forecasting evaluation (no reliable lead); 5 deployment and evaluation (the dashboard serves E196; fixes uncommitted); the general objective.
   - See `RESEARCH_OBJECTIVE_COMPLETION_MATRIX.md`.
6. **Is the model validated for research use, prospective evaluation or deployment?**
   - **Research use: yes.** It is genuine-data only, leak-checked, reproducible, with documented limitations.
   - **Prospective evaluation: yes, recommended.** FINAL is already sealed for the next provincial round (`4ad9267f`). FINAL-ET can be sealed alongside it on your approval.
   - **Deployment: no.** No version passes all seven rules, no reliable lead is established, and nothing is independently validated. E196 remains production.

## Why it fails (one paragraph)

FINAL's anchors are refreshed to the latest released national survey round. RATE, however, measures elapsed time from the province's own (older) survey.

In the 2021 round, provinces last surveyed in 2015 were therefore projected to fall twice over. This condition never appears in training, because every training province's own survey is also the latest round.

Correcting the elapsed time (FINAL-ET) removes the double count but over-corrects the level in 2021. The training data cannot tell how much of the 2019→2021 change the anchor should carry. Within the round, no available input separates the high-prevalence provinces that improved from those that did not.

Every legitimate long-gap treatment so far trades calibration against stability on a 4-HIGH round:

| Model | Long-gap treatment | Calibration | Stability |
|---|---|---|---|
| FINAL | Linear in the own-survey gap | Pass | Fail |
| FINAL-SA | Capped at the training gap | Fail | Pass |
| FINAL-ET | Time since the latest round | Fail | Pass |

## Recommendation

**Keep FINAL research-only; do not deploy FINAL or FINAL-ET.**

| Status | What | Who decides |
|---|---|---|
| Recommended | Seal FINAL-ET's next-round forecasts beside FINAL's (no new data needed) | Your approval |
| Pending | Adopt the elapsed-time correction into FINAL's definition: a change to how RATE measures time | Your approval; the evidence for and against is in `FINAL_IMPROVEMENT_RESULTS.md` |

**Required before any deployment claim**

| # | Requirement | Purpose |
|---|---|---|
| 1 | An independent provincial HFIAS round (about 25 provinces, about 10 HIGH) scored against sealed forecasts | Establish Rules 3–7 and a reliable lead |
| 2 | Training data that contain stale-anchor provinces (a future round), or a documented decision on how RATE should treat them | Fix calibration and stability together |
| 3 | Provincial employment from PSA's annual provincial labour statistics (released 2022 onward), added prospectively; remittances stay national/regional unless a provincial source appears | Give employment provincial variation |
| 4 | Your decision on the dashboard's five bars against FINAL's actual inputs | The current bars describe E196 and overstate FINAL's use of climate, employment and remittances |
| 5 | About 600–1,000 accumulated forecasts | Test the originally proposed calibration limits |

**Untouched:** E196, its artifacts, all seals, FINAL, FINAL-SA and every earlier report. Nothing was committed or deployed. Work folder: `research_notes/aiPHeed_final_stability_lead_20261113/`.

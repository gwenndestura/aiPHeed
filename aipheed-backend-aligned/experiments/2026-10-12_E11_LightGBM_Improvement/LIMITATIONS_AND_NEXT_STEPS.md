# E11 Limitations and Next Steps

## Limitations

1. **Few independent observations.** 7 test quarters (about 7 regional observations) and 16 labelled quarters in total. Nested validation had only 1–8 inner quarters (1 in the rolling window), so configuration choices are unstable.
2. **Reused quarters.** The 7 test quarters were evaluated in E1–E9. E11's design was informed by E9's errors, so its results are **exploratory and not independent confirmation.**
3. **Class imbalance.** 33 HIGH / 2 LOW in the test period, both LOW in one province. Classification metrics (and the 75% target) cannot discriminate between models. ROC-AUC and PR-AUC are not meaningful.
4. **Constructed target.** S1 is not observed food insecurity, and its weight of 2 is unvalidated. Regional hunger is a Balance-Luzon estimate that covers more than CALABARZON.
5. **Proxy-dated inputs.** Provincial CPI and label dates are national release + 14 days (unverified); unemployment is schedule-dated.
6. **Revised vintages.** Current CPI values are used, not real-time vintages.
7. **Uncalibrated probabilities.** The calibration evidence threshold was never met.
8. **Excluded inputs** (news, rice, fuel, FX, climate, `food_cpi` level) were not tested. Their eligibility could not be established safely.
9. **No LGU-level outcomes.** City and municipal differences cannot be learned or validated.

## Most useful next steps (in order)

1. **Evaluate the sealed 2026-Q4 forecast when its outcome is published** (expected 2027), following the frozen protocol. It is the first evaluation on a quarter whose outcome was unseen at forecast time.
2. **Freeze one experimental residual-model forecast per new quarter, alongside the S1 rule.** Each new quarter is new independent evidence. With about 8 such quarters, the "≥ 8 blind quarters" bar for added value becomes reachable.
3. **Verify RSSO IV-A provincial CPI release dates.** Do this after the relevant outcomes are collected, to upgrade the proxy-dated status safely.
4. **Seek province-level food-insecurity data** (for example FIES or NNS provincial estimates) to validate the S1 target and its weight. This is the largest methodological gap.
5. **Re-examine news inputs only if** a relevance-checked, geocoded, timestamped corpus reaches adequate coverage, from sources that do not carry protected values.

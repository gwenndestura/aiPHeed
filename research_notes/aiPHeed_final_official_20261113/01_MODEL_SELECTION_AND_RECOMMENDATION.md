# 01 — Final model selection, justification and production-readiness recommendation (deliverables 1, 19)

## 1. Selection
**FINAL (RATE + MIND) is confirmed as the official aiPHeed food-insecurity risk model**, unchanged. This is the owner's choice of 2026-11-13, and the evidence supports keeping it rather than any of the locked variants (report 07 §5).

**Why the evidence supports FINAL:**
- **Thesis targets at one quarter ahead:** mean fold accuracy 86.1 %, F1 0.80 and AUC 0.898.
- **Maximum reliable lead time:** 5 quarters by thesis Algorithm 3.
- **Baselines:** significantly better than always-LOW, persistence, PSA-only, NLP-only and logistic regression (Brier, accuracy, macro F1, PR-AUC).
- **Generalisation:** forecasts for provinces the model never saw are nearly as accurate (0.847).
- **Candidates:** no locked variant improves the thesis metrics consistently. Choosing one now would be selection on the same 72 outcomes.

## 2. What changed in this study
1. **By-crop harvest inputs refreshed to current PSA quarters.** They were stale at 2023-Q4. This is a data-currency fix only; no history changed.
2. **Dashboard contributors rebuilt from the evidence:**
   - five non-overlapping groups, with harvests separated from weather;
   - a bar only when it moves that forecast by at least 1 point;
   - each bar's text states whether removing the group worsened past forecasts.
3. **The 2021 SE assumption** was replaced by a sensitivity analysis.
4. **Configuration frozen; 2027-Q1 to 2028-Q1 forecasts sealed** (`80b20aed…`).

## 3. Limitations that remain
- **HIGH-risk detection after long survey gaps is weak.** In 2021, 1 of 4 HIGH provinces was found; persistence found 4. The cause is the elapsed-time term being extrapolated beyond the training gaps. Every live CALABARZON forecast is also beyond the training gaps, and Laguna, Quezon and Rizal are flagged as low-confidence.
- **The evidence is retrospective.** It covers 72 province-rounds from 3 survey rounds, reused during development, and only 5 rows are CALABARZON, all LOW. No HIGH case exists in the target region to test.
- **Only two predictor groups have demonstrated out-of-sample value:** regional economy (regional resolution) and harvests. Food prices, weather, employment and news are context. Remittances have no input.
- **Ground truth:** published estimates only; no microdata; 2021 SEs unpublished.
- **Reproducibility:** the code is not committed.

## 4. Production-readiness recommendation

**Conditionally ready, as a decision-support risk screen for DA Region IV-A, not as a measured food-insecurity rate.** The conditions are:

| # | Condition | Who |
|---|---|---|
| 1 | Publish **Leads 1–2** (2027-Q1, 2027-Q2) as the operational horizon, the leads that clear every thesis target (§3.4.4). State MRLT = 5 as the Objective 3 result | Owner decision |
| 2 | Commit `aipheed_hcw/backend/app/hcw/` (incl. `final_engine.py` and the `inputs.py` fix), the preview scripts and these reports; pin the environment | Owner approval |
| 3 | Show the low-confidence flag wherever the survey gap exceeds the training range, and keep "risk, not a measured rate" wording | Done in the preview data |
| 4 | Replace E196 in production only after conditions 1–2 and owner/adviser sign-off | Owner |
| 5 | Score the seal once against the next eligible FNRI provincial HFIAS round; report it whatever the result | Pending data |

**Not ready for:** claims of independent validation, claims of reliable HIGH detection after long survey gaps, or causal interpretation of contributors.

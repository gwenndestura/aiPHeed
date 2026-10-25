# E109 Final recommendation

**Is the new model better?**
- On the right question, yes: E109 forecasts **experienced hunger itself** (SWS Balance Luzon), not price pressure.
- Its target data are re-verified against SWS, and a commissioned round and a real-time-vintage defect were corrected.
- On accuracy, **no**. LightGBM with all 12 indicators (Lead-1 MAE 4.04 points) does not beat the latest published SWS reading (3.72). No other model does either.

**What it genuinely forecasts.** The percentage of families in Balance Luzon (Luzon outside Metro Manila) that experienced involuntary hunger at least once in the past three months. One regional number per quarter, not provincial values.

**Supported lead time.** None is established.
- Lead 1 is not reliable: it does not beat persistence.
- Leads 2–4 have insufficient evidence (5–7 quarters).
- The latest reading is a usable one-quarter outlook. Its average error of 3.7 points is within the survey's ±4-point margin. It is still not a validated model.

**What remains unproven.**
- Any skill beyond persistence.
- Any provincial or LGU hunger forecast.
- Any binary HIGH/LOW reliability: the thresholds are research-defined, and the only informative one (> 20%) rests on 9 quarters.
- Any prospective confirmation.

**Production.** Unchanged. Integration requires your explicit authorization.

**Recommended next decisions (yours, not taken here):**
1. **Authorize or decline extending the SWS series before 2021** for evaluation only. It is the single change that would make the lead-time question answerable, but it conflicts with the study-window rule.
2. **Decide whether the dashboard should show** "latest SWS hunger reading + margin + validation status" instead of a risk probability. It would be a text and data change, not a design change.
3. **Score the sealed files** (E107, E108, E109) when SWS publishes 2026-Q4.

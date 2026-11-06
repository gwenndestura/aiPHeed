# E167 result: corrected E166, not accepted

Protocol: 5483ded4 (E165 gates unchanged). Code: `backend/app/e167/correct.py`.

**Lead 1:**
- 66.7 %, balanced accuracy 0.726, HIGH 23/25, false alarms 22, Brier 0.1562.
- Brier − E158: +0.022 [−0.014, +0.058]. McNemar 2 vs 7, p = 0.18.
- Bias +6.3.
- Real − shuffled inputs: +0.032 [+0.008, +0.058], so real inputs did worse.
- Consumption-only shuffle: +0.021 [+0.003, +0.043], so consumption did worse than shuffled.

**Lead 2:** 68.1 %.

**Gates:** F1 and F6 pass. **F2, F3, F4, F5, F7, F8 and F10 fail.**

**Why it got worse:**
- With the calibration choice and the round-held-out folds, the inner selection switched to ridge (2018/2019) and LightGBM (2021) with consumption.
- Those choices fit the training rounds but carried the national-level drift upward.
- Holding out a round inside training could not see the 2015→2018 fall at the 2018/2019 issues, which had only one training round.

**Decision:** E158 stays. E166 remains the strongest trustworthy candidate, not accepted. **Per the protocol, no further model experiment is run.** See `docs/FINAL_MODEL_REPORT.md`.

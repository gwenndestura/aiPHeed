# E83 deviations from PROTOCOL.md (sha256 3dddb90f…)

Each entry gives what changed, why, and when. Arms added after a result was seen are **post-hoc** and are labelled
that way in every table. They reuse the same 13 target quarters, so their results are exploratory. Validation of a
post-hoc arm can only come from the prospective seal.

## D1 — rice-policy event file restored (2026-10-21, before the first run)

- **What.** `E46_Rice_Policy/data/rice_policy_events.csv` was not on `final-system-v2`. It was restored unchanged from
  commit f731bfa.
- **Source.** The file was built by E46 from five official instruments: EO 39, EO 62, EO 93, EO 102 and DA DC 3.
- **Gap.** No 2026 policy event was added, so policy features after 2025-12 are incomplete.

## D2 — round 2, post-hoc (after the first Lead-2 run, 2026-10-21 08:15Z)

**Diagnosis from round 1** (`runs/20261021T081507Z`):

| Arm | Rows issued | Lead-2 accuracy | Balanced accuracy | Recall (HIGH) | Notes |
|---|---|---|---|---|---|
| S-SIM | 60 | 0.75 | 0.57 | 0.19 | under-calls HIGH |
| Learners | 25 | — | — | — | issued only from target 2024-Q4 on; they keep predicting HIGH after the 2025 regime change |

The misses cluster in three places:
- the 2023-Q4 and 2024-Q2 hunger surges;
- the rice-price spike of Aug–Sep 2023;
- the Q4 2024 typhoon-season jump in food prices.

The price paths use the mean of the last 12 monthly changes, so they ignore the calendar pattern of food prices.

**Hypotheses added (post-hoc):**

| Arm | Hypothesis |
|---|---|
| S-SIM-SEAS | Seasonal drift: each future month's mean change is that calendar month's mean change in earlier in-window years; noise comes from deseasonalised residuals. |
| S-SIM-THR, S-SIM-SEAS-THR | The decision threshold is chosen inside each origin. It maximises balanced accuracy on earlier origins whose targets were already labelled at O(t). It needs at least 5 HIGH and 5 LOW past rows; otherwise it is 0.5. The grid is 0.10 to 0.60 in steps of 0.05. |
| ST-LR | Stacked logistic regression (C = 1, unweighted) on logit(P hunger) and logit(P price) from S-SIM-SEAS. Fitted on earlier origins' pairs. Needs at least 6 label quarters and at least 3 HIGH. Otherwise it falls back to S-SIM-SEAS. |
| ST-LR-N2, ST-LR-N3 | ST-LR plus event-level news (N2: ev_net_prices, ev_net_climate, ev_net_all) or the E64 news (N3: n3_market_rw, n3_climate_rw, n3_fssi). This is the news ablation repeated on the structural model. |

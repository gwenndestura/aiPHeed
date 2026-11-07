# E172 protocol: LightGBM-only Lead-2 candidates (EXPLORATORY)

- **Written:** 2026-11-07, before any E172 code was run and before any E172 result existed.
- **Status:** exploratory. The 72 rows per lead were examined in E151-E171; the E168 error pattern and the E171 results were seen
  before this was written. No E172 result on these rows is confirmation; confirmation needs new survey rows or the 2027 outcomes.
- **Unchanged:** E166, E168, E169, E171 artifacts; the sealed 2027-Q1 forecast (28f2c918); the served model; the four modified
  service files; the target, HIGH line (score >= 50 / P(HIGH) >= 0.5), rows, leads, `app.e156.leads.evaluate` (C1-C6, effective n,
  interval). E170 has no artifacts (stopped at its feasibility check).
- **Final predictor:** LightGBM only. Other learners are not in the menu.

## 1. Verified before writing (from saved files)
E168 Lead 2: 55/72 (15 false HIGH, 2 false LOW; false-HIGH P(HIGH) 0.51-0.61). The survey anchor alone over-forecasts ENNS 2018/2019 by
+0.36/+0.29 logit; E168's LightGBM adjustment leaves +0.19/+0.11. The temperature shrink multiplies the score by lambda > 0, so it
never changes a class (it affects probabilities only). ENNS 2018/2019 forecasts train on one survey transition (NNS 2013 -> FNRI 2015).

## 2. Candidate menu (fixed now)
Stage 1 (anchor): E168's 8 configurations (anchors H, RP, OH, RSS x E168 LightGBM x GOV, FULL); the anchor of the best is kept.
Stage 2, with that anchor, every combination of:
- **Inputs:** GOV, FULL (E168), GOV_S (GOV + E171's SWS hunger trend inputs, published-before-issue only; national input labelled national).
- **Complexity (LightGBM settings; tree count chosen inside training rows from 100/300/600 as E168):**
  R0 = E168 (`app.e150.model.PARAMS`: 4 leaves, depth 2, min child 10, L2 5, row/column fraction 0.8, learning rate 0.02);
  R1 = stumps (2 leaves, depth 1, min child 20, L2 10); R2 = 3 leaves, depth 2, min child 20, L2 10;
  R3 = R0 with min child 30, L2 20; R4 = stumps, min child 40, L2 20, column fraction 0.5.
- **Lead use:** pooled over leads (E168) or **lead-exact** (only training rows with the forecast's own lead; all rows if fewer than 30).
- **Seed bagging (correctly applied this time):** R0 x GOV and FULL, pooled, mean of seeds 151-155.
Total: 8 + 30 + 2 = 40 LightGBM configurations. Monotone constraints as E168 (+1 for the SWS inputs, as E171).

## 3. Training-only selection (survey-round aware)
Score = weighted squared error on held-out training rows: forward in time over whole survey rounds when the training rows hold two or
more rounds; otherwise (ENNS 2018/2019 issues) region-grouped folds, as E168. Identity vs linear calibration chosen on the same folds
(cross-fitted). The lowest score wins; ties keep the simpler configuration (menu order). E168's anchor rule, temperature shrink, sd
and HIGH line are applied unchanged. Every configuration's training score is saved per issue.

## 4. Decision rule (fixed now)
E172 is a candidate for adoption review only if all hold: LightGBM; valid run (E168 reproduced in the same jobs, leakage control
< 1e-9); **C1-C6 pass at Lead 2 and at Lead 1**; Lead-2 Brier not significantly worse than E168 (paired 95 % interval low end <= 0);
and its training-only score is not worse than E168's configuration on the same folds in the majority of Lead-2 issues.
Even then: exploratory, not served, E168 stays the thesis model pending new survey rows or the 2027 outcomes.

## 5. Not allowed
Changing the menu, rule, threshold or rows after the lock; re-running; choosing anything on the 72 rows; serving E172.

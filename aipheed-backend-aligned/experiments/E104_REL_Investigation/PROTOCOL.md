# E104: REL (relative food-price burden). Pre-registered protocol

**Date:** 2026-10-23. **Branch:** `main` @ `0239273`. Production, E100–E103 files and every sealed prediction are read only and hash-checked before and after the run. Outputs go to `out/` only.
**Freezing:** this file and `PROSPECTIVE_CRITERIA.md` are hashed (`runner/PROTOCOL_SHA256.txt`) before any analysis below is run.

**Already examined (disclosed):** all E100–E103 results, including REL-only (Lead 2 Brier 0.136), which was found during E103's decomposition, i.e. **selected after seeing the outcomes**. Every retrospective result below is therefore **exploratory**. It can describe REL and form hypotheses; it cannot prove future performance. Only the prospective criteria (`PROSPECTIVE_CRITERIA.md`) can.

## Part A. Audit and reproduction (confirmatory of E103's arithmetic, not of REL's value)

A1. REL formula, source and base: re-derive REL for every province and origin from `cpi_full.parquet` (year ≥ 2021) and check equality with `e102_lib.indicators_at` (< 1e-12).
A2. Reproduce E103 REL-only and Served at Leads 1 and 2: regional values equal to `E103/out/regional_lead{1,2}.csv` (< 1e-9); Brier, paired mean difference, bootstrap CI and exact permutation p equal to `E103/out/results.json` (< 1e-12).
A3. **Selection-aware test.** E103 compared seven price-domain arms computable on all quarters (S-noA, FB2, FB2-noREL, FB2-noPERS, LVL-only, PERS-only, REL-only). Max-statistic sign-flip permutation: for each of the 2^n sign patterns, the most negative mean Brier difference vs Served across the seven arms; family-wise p = share of patterns at or below REL-only's observed mean difference. Reported at Leads 1 and 2.
A4. Relation to existing price indicators: Spearman of pREL with A1, A2, A3, pLVL, pPERS (province rows) and of regional REL with H_last, E1raw, A2raw.

## Part B. Exploratory: information beyond SWS, poverty and economic access

B1. Partial Spearman of regional REL at origin with hunger at t + L, controlling for H_last, and for H_last and E1raw (rank residuals).
B2. Index arms on Served's quarters, C3 walk-forward weights unless stated: REL-only (with H); REL-only-noH (no H domain, ≥ 3 domains, C3 weights fitted to earlier SWS outcomes); REL-only-noH-EQ (no H, equal weights: no SWS input and no SWS-fitted weights, **but designed after seeing outcomes**, so not fully independent); H1 alone.
B3. Poverty: V1 is constant over time; its interaction with REL cannot be tested against a regional outcome. Reported as not testable.

## Part C. Trained forecast of the hunger **level** (pre-registered here; first time scored)

A classification model cannot be judged on all-HIGH test quarters, but the hunger **level** varies within them (15.3–25.3%). Target: y = mean of all SWS rounds of quarter t + L (%). Training pair (t', y(t'+L)) used at origin t only if t' < t and every round of t' + L was posted before issue(t). Features from the E102 as-of regional features. Ridge regression (standardised features, alpha = 1.0), refitted at every origin, ≥ 8 training pairs.

| Model | Features |
|---|---|
| RW (persistence) | forecast = H_last |
| R0 | H_last |
| R1 | H_last, REL |
| R2 | H_last, REL, E1raw |
| R3 | H_last, LVL |
| R4 | REL, E1raw (no SWS input) |

Metrics on the common quarters where every model forecasts: RMSE, MAE, mean error, paired squared-error difference vs RW (bootstrap 95% CI, exact sign-flip permutation p), and the derived class (forecast > 11.3) with its confusion matrix. **Rule:** "REL improves the trained level forecast" only if R1 beats R0 **and** RW on squared error with permutation p < 0.05 at Lead 2; otherwise not demonstrated.

## Part D. Feature availability

For every feature group: source, geography, the as-of rule enforced in code at the issue date, the latest period available for the 2027-Q1 forecast, and whether the group can enter a trained model given the label count.

## Not done

No new data, no pre-2021 data, no tuning on any outcome, no change to served or sealed files, no claim of validated improvement.

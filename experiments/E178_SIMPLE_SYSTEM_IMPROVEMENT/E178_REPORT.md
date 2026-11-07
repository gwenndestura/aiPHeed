# E178: SIMPLE system improvement (2026-11-07)

## Outcome B: a technical improvement was identified; predictive improvement remains unverified
5-seed averaging of SIMPLE's LightGBM cuts seed instability by about 60 % on the untainted training rows. It does not improve
training-only Brier beyond noise, and it cannot be evaluated on independent data. Frozen SIMPLE, E168 and all seals are unchanged.

## 1. Data pipeline audit (156 untainted rows; `data_quality_audit.csv`, `feature_audit.csv`)
Correct, no action needed:
- No duplicate (province, survey, lead) rows; every province maps to a region and SWS area.
- Issue quarter before outcome quarter, and anchor survey before issue quarter, for every row; lead arithmetic consistent.
- Targets (FNRI 2015) and anchors (NNS 2013) are both HFIAS. No FIES or other instrument mixed in.
- No leakage found: inputs are built as of the issue quarter (`prov.add_inputs`, E154, E171 SWS published-before rule).

Limitations found:
1. **One time dimension of two values.** The rows are 78 provinces x 2 issue dates, so every national input (ONI,
   unemployment, remittances, national news, SWS national trend: 15 inputs) takes two values in lockstep with `lead` and carries
   one bit. Their effect cannot be learned from this data. Only province-level variation (CPI, climate, production, poverty,
   density) is learnable.
2. 4 GOV inputs are constant here (unemp_region, remit_q_yoy, gap_q, income_growth); Res2 drops them automatically.
3. CPI and production inputs are missing for 3 of 78 provinces (3.8 %); LightGBM handles missing values natively.
4. Latent code issue: `app/e151/prov.py` lines 118/124 fill news tone/share with 0.0 when a province has no news row, so
   "no articles" equals "neutral". It affects **0 of the 156 rows** and none of SIMPLE's inputs (GOV contains no news). It is
   reported, not changed (E168/production code is protected).

## 2. Feature engineering
No new features were added. With one survey transition, any engineered time feature (differences, lags, rolling statistics,
interactions with national series) either has two values or cannot be validated temporally, and E171 showed the one
trend-type addition (SWS) made LightGBM worse. Removing the degenerate inputs (K2) changed nothing: Brier 0.0827 vs 0.0825.

## 3. Temporal validation (`temporal_validation.csv`)
**Not possible.** Forward-in-time validation needs two untainted target rounds; only FNRI 2015 is untainted. Region folds measure
cross-sectional fit only, not temporal generalisation.

## 4. LightGBM training and stability (registered rule: `selection_rule.md`; results: `training_only_validation.csv`, `stability_analysis.csv`)
| Candidate | Accuracy (range over instances) | Brier | Mean score SD | Rows changing class | Rule decision |
|---|---|---|---|---|---|
| K0 SIMPLE, single seed | 0.782 (0.776-0.795) | 0.0825 | 0.0115 | 8 of 156 (5 seeds) | reference |
| **K1 SIMPLE, 5-seed average** | 0.795 (0.795-0.795) | 0.0836 | **0.0044** | **3 of 156** (3 ensembles) | stability only; predictive unverified |
| K2 degenerate inputs removed | 0.769 (0.769-0.795) | 0.0827 | 0.0116 | 9 | no improvement |
| K3 K1 + K2 | 0.789 | 0.0837 | 0.0040 | 6 | stability only |
| E168 settings (single / ensemble) | 0.744 / 0.750 | 0.0808 / 0.0820 | 0.0123 / 0.0056 | 3 / 2 | reference |

The noise threshold for Brier was 0.0018 (2 x the seed SD of K0). No candidate improves Brier by more than that.
Flip counts compare 3 ensemble instances with 5 single seeds, so the score SD (0.0044 vs 0.0115) is the fairer stability measure.

## 5. Answers
1. What was limited: one untainted survey transition with two issue dates, so national inputs are one bit and temporal validation is
   impossible; SIMPLE's single-seed LightGBM is seed-unstable (8 of 156 rows change class across seeds). Latent news zero-fill (0 rows).
2. What was improved: seed stability, by averaging 5 seeds (K1).
3. Effect: model stability, yes. Data quality: no fix needed for these rows. Predictive performance: not shown.
4. Algorithm: LightGBM throughout.
5. Training-only support: stability yes; predictive improvement no (within noise).
6. New candidate justified: only as "SIMPLE + 5-seed averaging" for stability. It is not adopted and not served.
7. Unverified: any predictive gain on new data, and temporal generalisation. Needs post-2021 provincial HFIAS rows.
8. E168, SIMPLE and sealed forecasts: unchanged (`PROTECTED_ARTIFACTS_CHECK.md`).
9. Git state and existing work: untouched; only `experiments/E178_SIMPLE_SYSTEM_IMPROVEMENT/` was added.

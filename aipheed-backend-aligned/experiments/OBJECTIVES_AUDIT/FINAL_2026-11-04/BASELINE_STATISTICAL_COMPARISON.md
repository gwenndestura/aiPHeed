# Baseline statistical comparison (C-E2 vs the 7 required baselines)

**Method (pre-registered, unchanged):**
- paired Brier difference (C-E2 − baseline; negative = C-E2 better);
- one-sided cluster bootstrap (seed 2036, B 5000);
- Holm correction over 14 tests (7 baselines × 2 leads), α = 0.05.

**Sample:** the same quarters, labels and leads for every pair. The news-only baselines use the news era (20 / 19
quarters), and C-E2 is scored on the same quarters. Source: `out/ce2_results.json` (reproduced byte-identically).

| Lead | Baseline | n | C-E2 Brier | Baseline Brier | Diff | 95% CI | p raw | p Holm | Effect d | Significant |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Persistence | 62 | 0.1875 | 0.3387 | −0.151 | −0.254..−0.054 | 0.0006 | 0.008 | 0.38 | ✅ |
| 1 | Logistic, combined (LOGIT) | 62 | 0.1875 | 0.1928 | −0.005 | −0.070..0.058 | 0.433 | 0.433 | 0.02 | ❌ |
| 1 | Logistic, government-only (PSA-only) | 62 | 0.1875 | 0.2082 | −0.021 | −0.073..0.029 | 0.208 | 0.416 | 0.10 | ❌ |
| 1 | Logistic, NLP-only | 20 | 0.2095 | 0.3531 | −0.144 | −0.261..−0.033 | 0.006 | 0.050 | 0.54 | ❌ (margin) |
| 1 | LightGBM, government-only | 62 | 0.1875 | 0.2327 | −0.045 | −0.070..−0.018 | 0.0008 | 0.010 | 0.44 | ✅ |
| 1 | LightGBM, NLP-only | 20 | 0.2095 | 0.3069 | −0.097 | −0.199..−0.006 | 0.017 | 0.102 | 0.43 | ❌ |
| 1 | Always-HIGH | 62 | 0.1875 | 0.3065 | −0.119 | −0.211..−0.030 | 0.005 | 0.050 | 0.33 | ❌ (margin) |
| 2 | Persistence | 62 | 0.1879 | 0.3387 | −0.151 | −0.252..−0.053 | 0.0004 | 0.006 | 0.38 | ✅ |
| 2 | Logistic, combined | 62 | 0.1879 | 0.2340 | −0.046 | −0.114..0.020 | 0.088 | 0.263 | 0.17 | ❌ |
| 2 | Logistic, government-only | 62 | 0.1879 | 0.2389 | −0.051 | −0.105..0.002 | 0.031 | 0.154 | 0.23 | ❌ |
| 2 | Logistic, NLP-only | 19 | 0.2196 | 0.4341 | −0.215 | −0.399..−0.036 | 0.007 | 0.050 | 0.51 | ❌ (margin) |
| 2 | LightGBM, government-only | 62 | 0.1879 | 0.2401 | −0.052 | −0.082..−0.022 | 0.0008 | 0.010 | 0.43 | ✅ |
| 2 | LightGBM, NLP-only | 19 | 0.2196 | 0.3096 | −0.090 | −0.205..0.015 | 0.049 | 0.197 | 0.36 | ❌ |
| 2 | Always-HIGH | 62 | 0.1879 | 0.3065 | −0.119 | −0.212..−0.031 | 0.005 | 0.050 | 0.33 | ❌ (margin) |

- **Effect d** is the mean gain divided by the SD of the per-quarter gain (`out/obj4_power.json`).
- **Climatology** (an extra reference, R5): diff −0.033 (p 0.049) at Lead 1 and −0.034 (p 0.041) at Lead 2.

## Result

- **All 14 differences favour C-E2.**
- **4 of 14 are significant** after Holm: persistence and government-only LightGBM, at both leads.
- **C-E2 does NOT beat all seven baselines** with statistical evidence.
- **Not proven at both leads:** logistic combined, logistic government-only, logistic NLP-only, LightGBM NLP-only,
  always-HIGH.

## Why some comparisons are not significant (Part 9B)

| Cause | Evidence |
|---|---|
| Sample size | 62 quarters (news-only baselines: 19–20). See `POWER_AND_SAMPLE_SIZE_ANALYSIS.md` |
| Small effect vs LOGIT at Lead 1 | Gain 0.005, d 0.02: practically negligible. On soft (sampling-probability) labels LOGIT is slightly better (0.122 vs 0.128) |
| Paired dependence | Both are wrong on the same 9 Lead-1 quarters; squared errors correlate 0.45 |
| Persistence dominance | The last SWS reading carries about 60% of SHAP in C-E2 and dominates LOGIT too |
| Temporal clustering | Lag-1 autocorrelation of the per-quarter gain is up to 0.55 (always-HIGH L2), which reduces the effective sample |
| Few regime changes | 13 label changes in 62 quarters; C-E2 is right on 6 |
| Holm margin | Three comparisons have p_Holm = 0.050 exactly, at the line but not below it |

**Unchanged:** no baseline, period, α or test was altered. The stored PSA-only defect (`OBJ4_BASELINE_VERIFICATION.md`
§2) is documented and does not change any conclusion.

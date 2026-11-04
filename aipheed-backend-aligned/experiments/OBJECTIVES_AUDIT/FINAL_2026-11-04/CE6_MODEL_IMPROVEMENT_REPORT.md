# C-E6 model improvement report (2026-11-04)

**Recommendation: CONTINUE DEVELOPMENT.**
- C-E6 is a real, pre-registered improvement on C-E2. Its Brier score is better (p 0.012 / 0.086), and 8 of 14
  baseline comparisons are significant (C-E2: 4).
- It does **not** pass R3/R7, and it does **not** beat all seven baselines.
- Not adopted. C-b stays the main model, and C-E2 stays the demo model. Nothing is committed, deployed or sealed.

## 1. Starting point (C-E2)

| | Accuracy | Balanced | Precision | Recall | F1 | AUC | Brier | Failed |
|---|---|---|---|---|---|---|---|---|
| Lead 1 | 0.774 | 0.690 | 0.796 | 0.907 | 0.848 | 0.715 | 0.1875 | R3, R7 |
| Lead 2 | 0.758 | 0.679 | 0.792 | 0.884 | 0.835 | 0.694 | 0.1879 | R3, R7 |

MRLT 3; 4 of 14 comparisons significant.

## 2. Root causes (`FORECASTING_FAILURE_ANALYSIS.md`)

- **LOW quarters are missed:** LOW recall is 0.47, from a history-driven HIGH bias.
- **Regime break:** 2015–2020 accuracy is 0.524. Every model fails that third.
- **Survey-label noise:** 13 of 62 labels are within SWS sampling error, and half of the Lead-1 errors fall on them.
- **Feature gap:** the inputs measure persistence and affordability. **No input measured food availability.**

## 3. Previous approaches (not repeated)

The table lists only the approaches this report screened; `EXPERIMENT_REGISTRY.md` has the full record.

| Approach | Attempt | Why it was insufficient |
|---|---|---|
| Latent state, survey-error weights | S1, C-w | One call changed; Brier n.s. |
| Regime / recency weighting | C-E5R | Worse (L1 0.661) |
| Past-only calibration | C-E5C | Worse (L1 0.613) |
| Per-lead models | C-E3 | Too few rows per model (L1 0.726) |
| Season feature | C-E4 | No gain |
| Reversal features | K3 | Failed R5/R7 |
| Dropping news | C-E2-NONEWS | News adds 0.001 |

## 4. New data sources investigated

| Source | Provenance | Coverage | Availability at O(t) | Independent? | Used |
|---|---|---|---|---|---|
| **PSA rice stocks inventory** (household, commercial, NFA) | OpenSTAT 2E/CS/0032E4ECNV0 (Y12 acquisition, sha 21c6670f…) | National, monthly, 1980-01..2026-09 | Stock month ≤ issue month − 4 (verified max lag 92 days); leakage check passed | **Yes**: food availability, not used for this target before | **Yes (C-E6)** |
| Regional rice stocks | OpenSTAT 2E/CS/0048E4ECNV1 | 2026 only | — | — | No: no history |
| Rice imports | OpenSTAT | 2015+ | — | — | No: too short |
| BSP cash remittances | FIRI_V2 audit | Quarterly | — | Overlaps IMF E2 | No: redundant |
| Fish-kill events | E87 derived | Sparse | — | — | No: event counts too sparse to test |
| FNRI FIES | FNRI | Regional, a few years | — | Different measure | No: face validity only |
| More SWS quarters | SWS | +4 per year | Prospective | Same target | **Only via the 2027 holdout** |

**Limitation:** OpenSTAT serves the current vintage only, so early stock values may be revised. This cannot be
quantified.

## 5. Improvement implemented: C-E6 = C-E2 + rice stocks

- **Pre-registration:** `OBJECTIVES_AUDIT/CE6_PREREGISTRATION.md`, PLAN-SHA256
  `6e07ee14ecfd7925561c20e7774593d15c69d1d0501f0ee5227854e604af5ac8`. Fixed before any fit; no variant tried after.
- **Features:**
  - `ST1` = year-on-year % change of total rice stocks;
  - `ST2` = year-on-year change of the NFA share (points).
- **Model:** the exact C-E2 procedure (25 inputs).

## 6. Final metrics (62 quarters)

| | Accuracy | Balanced | Precision | Recall | F1 | AUC | Brier | ECE | TP/FP/FN/TN | Failed |
|---|---|---|---|---|---|---|---|---|---|---|
| C-E6 Lead 1 | 0.774 | 0.690 | 0.796 | 0.907 | 0.848 | **0.720** | **0.1839** | 0.175 | 39/10/4/9 | R3, R7 |
| C-E6 Lead 2 | 0.758 | 0.679 | 0.792 | 0.884 | 0.835 | **0.695** | **0.1856** | 0.108 | 38/10/5/9 | R3, R7 |

**vs C-E2 (paired Brier):**

| | Diff | 95% CI | p |
|---|---|---|---|
| Lead 1 | **−0.0036** | −0.0071..−0.0005 | **0.012** |
| Lead 2 | **−0.0023** | −0.0058..0.0010 | **0.086** |

**vs C-b:** −0.0035 (p 0.37) at Lead 1 and +0.0019 (p 0.59) at Lead 2; 1–2 calls changed.

**SHAP:** supply carries 8.1–8.5% of SHAP on average (7.3% at the latest issue). Market 61–62%, employment 14–15%,
climate 9–10%, OFW 5%, fish 2%.

## 7–8. Seven-baseline comparison (Holm over 14; one-sided cluster bootstrap, seed 2036, B 5000)

| Baseline | L1 C-E6 / baseline Brier | Diff (95% CI) | p Holm | Proven | L2 C-E6 / baseline Brier | Diff (95% CI) | p Holm | Proven |
|---|---|---|---|---|---|---|---|---|
| Persistence | 0.184 / 0.339 | −0.155 (−0.258..−0.058) | 0.005 | ✅ | 0.186 / 0.339 | −0.153 (−0.253..−0.057) | 0.003 | ✅ |
| LGBM government-only | 0.184 / 0.233 | −0.049 (−0.074..−0.021) | 0.007 | ✅ | 0.186 / 0.240 | −0.055 (−0.085..−0.024) | 0.009 | ✅ |
| Logistic NLP-only (news era) | 0.199 / 0.353 | −0.154 (−0.274..−0.042) | **0.024** | ✅ new | 0.210 / 0.434 | −0.224 (−0.406..−0.049) | **0.034** | ✅ new |
| Always-HIGH | 0.184 / 0.307 | −0.123 (−0.214..−0.034) | **0.034** | ✅ new | 0.186 / 0.307 | −0.121 (−0.213..−0.033) | **0.034** | ✅ new |
| LGBM NLP-only (news era) | 0.199 / 0.307 | −0.108 (−0.209..−0.017) | 0.053 | ❌ by 0.003 | 0.210 / 0.310 | −0.099 (−0.214..0.005) | 0.129 | ❌ |
| Logistic government-only | 0.184 / 0.208 | −0.024 (−0.076..0.026) | 0.338 | ❌ | 0.186 / 0.239 | −0.053 (−0.107..0.000) | 0.128 | ❌ |
| Logistic combined | 0.184 / 0.193 | −0.009 (−0.073..0.054) | 0.388 | ❌ | 0.186 / 0.234 | −0.049 (−0.116..0.017) | 0.224 | ❌ |

**Result:**
- **8 of 14 are significant.** All 14 differences favour C-E6.
- **Proven at both leads:** 4 of 7 baselines.
- **Unproven:** logistic combined, logistic government-only, and LightGBM NLP-only.

## 9. R1–R7

| | R1 | R2 | R3 | R4 | R5 | R6 | R7 |
|---|---|---|---|---|---|---|---|
| Lead 1 | ✅ | ✅ 0.774 | ❌ 0.690 | ✅ | ✅ | ✅ | ❌ thirds 0.952 / 0.524 / 0.850 |
| Lead 2 | ✅ | ✅ 0.758 | ❌ 0.679 | ✅ | ✅ | ✅ | ❌ 0.952 / 0.524 / 0.800 |

**R3 and R7 do not move:** the stocks sharpen probabilities but change no HIGH/LOW call at either lead versus C-E2
(checked over 2010-Q1..2026-Q3).

## 10. Reliable horizon

Algorithm 3 gives **3 quarters** (as C-E2; C-b 2).

## 11. Leakage and reproducibility

- **Leakage:** stock months after (issue − 4) replaced with random values at all 113 origins, 5 times each: features
  unchanged (`out/ce6_checks.json`).
- **Labels:** known at O(t) only (`V.known_labels`), as C-E2.
- **Reproducible:** deterministic seed. `ce6_model.py features | fit | score` regenerates `out/ce6_*`.
- **Evidence integrity:**
  - The C-E6 score step first wrote to C-E2's results file name. It was detected immediately: C-E2's
    `ce2_results.json` was restored from the verified copy (SHA 13666bfd…, identical), and the path was fixed.
  - C-E2's fits were never touched.

## 12. Dashboard preservation

- **No frontend or backend application file was changed in this round.** 200/200 protected files are unchanged,
  including every file in `frontend/src`.
- **Dashboard and API tests:** 87 passed, 8 skipped (food-insecurity mode, config metadata, drivers, thesis system,
  API dashboard). Last full suite: 1,022 passed.
- **C-E6 is not served.** Serving it in the 8081 demo would need an export (`export_ce2.py` pattern). The new "supply"
  group would not be one of the five dashboard driver groups, so its 7–8% share would be outside the five bars.

## 13. Files created or modified (this round)

**Created:**
- `OBJECTIVES_AUDIT/CE6_PREREGISTRATION.md`;
- `runner/ce6_model.py`, `runner/obj4_feasibility.py`;
- `out/ce6_features.csv`, `ce6_checks.json`, `ce6_fits.csv`, `ce6_results.json`, `obj4_feasibility.json`;
- this report.

**Appended:** `NEW_MODEL/ALLBASE/REGISTRY.csv` (+2 rows; backup `backup/REGISTRY_before_CE6.csv`).

**Restored:** `out/ce2_results.json`, from the verified copy (identical hash).

## 14. Remaining limitations and data requirements

- **Feasibility (`out/obj4_feasibility.json`):**
  - Proving superiority over the logistic combined model at Lead 1 needs a Brier score of about **0.100 or lower** at
    α = 0.05 (0.061 at the strictest Holm step). C-E6 is at 0.184.
  - The **noise floor** is 0.051: the score of a perfect forecaster of true hunger, given SWS sampling error.
  - Some strict-step targets (always-HIGH Lead 2: 0.007) lie **below** that floor, which no model can reach.
- **The remaining gaps are evidence gaps, not model defects:**
  - LGBM-NLP Lead 1 is 0.003 short. More news-era quarters (2027+) may close it.
  - The two logistic baselines would need hundreds of quarters (or thousands for LOGIT at Lead 1) at the current
    effect sizes.
- **This is attempt 22 on the same 62 examined quarters.** The improvement over C-E2 is pre-registered and
  significant, but it is still development evidence. Independent confirmation needs the 2027 sealed holdout.
- **The rice stocks are national, current-vintage data,** and release dates before 2022 are unverified (bounded by
  the 4-month rule).

## 15. Recommendation

**CONTINUE DEVELOPMENT.**
- C-E6 is the best-evidenced candidate (best Brier, 8/14 significant, MRLT 3).
- It fails R3 and R7 and does not beat all seven baselines, so it does not meet the adoption criteria.

**Next steps (each needs your approval):**
1. Add C-E6, with C-E2 and C-b, to the prospective registry, and seal on 1–15 Jan 2027.
2. Optionally serve C-E6 in the 8081 demo.

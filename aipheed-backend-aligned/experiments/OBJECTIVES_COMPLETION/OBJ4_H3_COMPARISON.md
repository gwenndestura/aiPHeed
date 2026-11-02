# Objective 4 and H3: the proposed LightGBM against the baselines

> Objective 4: "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline
> approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline
> IV. Logistic regression baseline"
>
> H3: "The LightGBM model that combines news signals and government data will not outperform the six comparison
> models, naive persistence, three logistic regression variants (news-only, government data-only, and combined), and
> two LightGBM variants trained on only one data source at a time…"

**Status: Achieved (the comparison).** The proposed model is superior to some baselines, not all.

**Evidence status: development evidence.** Every quarter 2010–2026 was already examined (HISTORY_RETRAIN, IMPROVE_V2,
earlier experiments).

**Sources:**
- Objective 4: `IMPROVE_V2/RESULTS.md` §6.
- H3: `out/h3_results.json`, from `runner/h3.py`. The two single-source LightGBMs are defined in `H3_COMPARATORS.md`
  (SHA-256 `b700cb45…`, committed `57544f8` before fitting). They are **comparators only, never selected or sealed**.
- Fitting check: the same fitting path reproduced the IMPROVE_V2 reference to 1.1e-16 before the variants were used.

**Test:** Brier score difference (proposed minus comparator; negative = proposed better), one-sided paired cluster
bootstrap by target quarter (seed 2036, 5000 draws), **Holm-corrected** across the comparisons of each table and lead.
News-only comparators exist only from 2021, so they are compared on the news-era quarters (20 at Lead 1, 19 at Lead 2).
All others use the 62 quarters 2010–2026.

## 1. Objective 4: the four named baselines (plus always-HIGH), proposed model = REF

| Comparator | Lead 1 Brier (REF vs comparator) | diff | p | Holm p | Lead 2 Brier | diff | p | Holm p |
|---|---|---|---|---|---|---|---|---|
| I. Naive persistence | 0.188 vs 0.339 | −0.151 | 0.000 | **0.001** | 0.184 vs 0.339 | −0.155 | 0.000 | **0.001** |
| II. PSA-only (logistic) | 0.188 vs 0.208 | −0.021 | 0.256 | 0.511 | 0.184 vs 0.239 | −0.055 | 0.040 | 0.080 |
| III. NLP-only (logistic; 20 / 19 q) | 0.200 vs 0.353 | −0.153 | 0.002 | **0.008** | 0.207 vs 0.434 | −0.227 | 0.003 | **0.014** |
| IV. Logistic regression | 0.188 vs 0.193 | −0.005 | 0.440 | 0.511 | 0.184 vs 0.234 | −0.050 | 0.079 | 0.080 |
| Always-HIGH | 0.188 vs 0.306 | −0.119 | 0.009 | **0.028** | 0.184 vs 0.306 | −0.123 | 0.008 | **0.023** |

Accuracy, same quarters: REF 0.790 / 0.790; persistence 0.661 / 0.661; PSA-only 0.726 / 0.677; logistic regression
0.710 / 0.661; always-HIGH 0.694; NLP-only 0.450 / 0.421 (news era).

**Plainly:**
- **Superior** (Holm p < 0.05, both leads): naive persistence, NLP-only, always-HIGH.
- **Not shown superior:** PSA-only and logistic regression. Lower Brier at both leads, but Holm p 0.51 at Lead 1 and 0.08 at Lead 2.

## 2. H3: all six comparators

H3's "LightGBM that combines news signals and government data" is IMPROVE_V2 arm **REF+news**. The carried-forward
model **REF** uses SWS hunger history plus official indicators, with no news. Both are shown, each with its own Holm
correction across six comparisons.

**The comparators, as available:**
- **Logistic regressions:**
  - news-only = NLP-only;
  - government-only = PSA-only;
  - "combined" = LOGIT: SWS plus official indicators, **without news**. A news-plus-government logistic regression was not fitted (not approved), so H3's combined LR is matched only approximately.
- **Single-source LightGBMs:**
  - LGBM-GOV: official indicators only, no SWS;
  - LGBM-NLP: news only.

### Proposed = REF

| Comparator | Lead 1 diff | p | Holm p | Lead 2 diff | p | Holm p |
|---|---|---|---|---|---|---|
| Naive persistence | −0.151 | 0.000 | **0.001** | −0.155 | 0.000 | **0.001** |
| LR news-only (NLP-only) | −0.153 | 0.002 | **0.010** | −0.227 | 0.003 | **0.014** |
| LR government-only (PSA-only) | −0.021 | 0.256 | 0.511 | −0.055 | 0.040 | 0.080 |
| LR combined (LOGIT, no news) | −0.005 | 0.440 | 0.511 | −0.050 | 0.079 | 0.080 |
| **LGBM-GOV** | −0.045 | 0.004 | **0.014** | −0.056 | 0.002 | **0.010** |
| **LGBM-NLP** (20 / 19 q) | −0.107 | 0.003 | **0.014** | −0.103 | 0.020 | 0.061 |

### Proposed = REF+news (the literal "combined" LightGBM)

| Comparator | Lead 1 diff | p | Holm p | Lead 2 diff | p | Holm p |
|---|---|---|---|---|---|---|
| Naive persistence | −0.143 | 0.000 | **0.001** | −0.140 | 0.000 | **0.002** |
| LR news-only | −0.129 | 0.004 | **0.015** | −0.178 | 0.014 | 0.068 |
| LR government-only | −0.013 | 0.345 | 0.690 | −0.040 | 0.106 | 0.258 |
| LR combined (no news) | +0.002 | 0.521 | 0.690 | −0.035 | 0.166 | 0.258 |
| LGBM-GOV | −0.037 | 0.027 | 0.081 | −0.041 | 0.028 | 0.114 |
| LGBM-NLP | −0.083 | 0.003 | **0.014** | −0.054 | 0.086 | 0.258 |

### The two new comparators (all Objective-2 metrics)

| Model | Lead | Quarters | Acc | Bal | Prec | Rec | F1 | AUC | Brier | Fails | Fallback quarters |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LGBM-GOV | 1 | 62 | 0.677 | 0.562 | 0.725 | 0.860 | 0.787 | 0.535 | 0.233 | R2, R3, R5, R7 | 0 |
| LGBM-GOV | 2 | 62 | 0.597 | 0.474 | 0.680 | 0.791 | 0.731 | 0.506 | 0.240 | R2–R5, R7 | 0 |
| LGBM-NLP | 1 | 20 | 0.600 | 0.593 | 0.727 | 0.615 | 0.667 | 0.527 | 0.307 | R1–R5, R7 | 7 of 20 |
| LGBM-NLP | 2 | 19 | 0.526 | 0.536 | 0.667 | 0.500 | 0.571 | 0.476 | 0.310 | R1–R7 | 7 of 19 |

**Reading:**
- Official indicators alone, without the SWS hunger history, barely rank the quarters (AUC 0.51–0.53).
- News alone does no better, and in 7 quarters too few LOW examples existed to fit at all.
- The reference beats both single-source LightGBMs (Holm p ≤ 0.014, except LGBM-NLP at Lead 2: 0.061).

## 3. Verdict on H3

**H3 is not rejected** for either reading of the "proposed" model. The proposed LightGBM does not outperform all six comparators:

- **REF** beats persistence, LR news-only, LGBM-GOV and LGBM-NLP (Lead 1; at Lead 2, LGBM-NLP Holm p 0.061). It does **not** significantly beat LR government-only or LR combined.
- **REF+news** (literally news plus government) beats fewer: persistence, LR news-only (Lead 1) and LGBM-NLP (Lead 1). It does not significantly beat the government-only and combined logistic regressions, or LGBM-GOV.

**The useful finding:**
- The model's advantage comes from **combining the SWS hunger history with official indicators**, not from news.
- Adding news to the reference makes it weaker against the baselines, not stronger.

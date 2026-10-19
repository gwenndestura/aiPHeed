# E60 model selection and validation protocol (frozen before any E60 candidate is scored)

**Written:** 2026-10-18 on branch `e60-accuracy-optimization` (from 88d5266). Nothing is committed without the user's permission.
**Freeze:** the SHA-256 (LF) of this file is in `runner/PROTOCOL_SHA256.txt`, written before any candidate run. Forecasts are sealed before scoring (E57/E58 practice).

## 0. Evidence status

All 10 evaluable target quarters (2024-Q2..2026-Q3) were examined in E43–E59. So **no historical period is untouched by the project**.

**What E60 can offer:**
- a split that is untouched **by E60's own selection**: DEV vs TEST (section 3);
- rolling-origin forecasts that use only data published before each issue date.

The independent test remains the frozen 2027 forecasts.

## 1. Target

**Primary: T43** (E55 PROTOCOL section 2). It is named here as the **food-stress risk indicator**: regional SWS hunger above 11.3% **and** provincial PSA food-price pressure.

**What it actually measures** (`TARGET_VALIDITY_AND_DATA_GAPS.md`):
- On all 50 evaluation rows T43 = provincial food-price pressure (PS).
- 13 of its 18 HIGH rows are set by the food-minus-headline inflation gap alone.
- Results are reported as forecasts of this indicator. **They are not reported as food-insecurity prevalence.**

**Supporting labels:**
- training label of the price learner: PS (as in E56);
- events: ONSET (HIGH at the target while the latest known label was LOW) and RISEP (E58 definitions).

## 2. Horizon and timing

**Horizon:** issue at 00:00 on day 1 of quarter t+1 (O(t)), target t+2. Rolling origins t = 2023-Q4..2026-Q1 (50 rows). Operational origins: 2026-Q2 and 2026-Q3.

**Government inputs:** the E56 rules (E59 timing audit), unchanged.

**News inputs:**
- only articles whose publisher publication date is **before O(t)** (`published_ph < O(t)`);
- aggregation window: quarter t (the three months before O(t));
- the change feature compares quarter t with the mean of t−4..t−1;
- no article published on or after O(t) enters any feature, label or threshold.

**Leakage test:** news features rebuilt from a corpus truncated at O(t) must be identical.

## 3. Splits

| Split | Targets | Rows | HIGH | Use |
|---|---|---|---|---|
| **DEV** | 2024-Q2..2025-Q3 (6 quarters) | 30 | 17 | the **only** set used to choose among E60 candidates |
| **TEST** | 2025-Q4..2026-Q3 (4 quarters) | 20 | 1 | reported once, after the choice |

**TEST is uninformative about HIGH detection:** it has 1 HIGH row and 3 all-LOW quarters, and this is stated with every TEST figure. The full 50-row rolling-origin results are also reported.

**Inner tuning:** within each origin, by E56's nested forward-chaining log-loss on training targets ≤ t−1. Outer rows are never used.

## 4. News pipeline (fixed before features are built)

- **Corpus:** E31 store (8,320 titles) ∪ E60 trigger store (N2), deduplicated by `article_key`.
- **Relevance and trigger classifier v2:** a rule set developed **only on the DEV annotation half** (`NEWS_ANNOTATION_PROTOCOL.md`). Its rules are frozen with a sha256 before the EVAL annotation half is scored and before any news feature is built.
- **Province attribution:** the project geocoder on the title. The query province is **not** treated as attribution.

**News features, per province p and origin t (all as of O(t)):**

| Feature | Definition |
|---|---|
| `nz_<k>_share` (k = the five triggers) | relevant v2 articles of trigger k attributed to p in quarter t ÷ all relevant articles attributed to p in quarter t (0 when none; plus `nz_coverage` = that denominator) |
| `nz_<k>_chg` | log1p(count of k attributed to p in t) − log1p(mean count of k in t−4..t−1) |
| `nz_reg_<k>` | regional count of trigger-k relevant articles (all retrieved CALABARZON articles, deduplicated) in t, divided by the regional count of all relevant articles in t |
| `nz_events` | number of distinct relevant events attributed to p in t (near-duplicate titles merged) |

All counts are normalized by coverage (shares or changes), so that heavily covered provinces are not risky by construction.

## 5. Candidates

All candidates are rolling-origin, on identical rows, with the E56 structure P(HIGH) = P_hunger (I7) × P_price.

| ID | P_price learner | Inputs |
|---|---|---|
| **A** gov-only | E56-TUNED procedure (72 configurations, nested), news columns removed | government and economic indicators + CPI offset |
| **B** news-only | L2 logistic regression (C = 1.0, standardised, trained on as-of PS labels) | E60 news features only |
| **C** gov + news | E56-TUNED procedure | A's inputs + E60 news features (in the "all" feature set) |
| **D** gov + news + history | E56-TUNED procedure | C's inputs + `hist_ps_last` (PS of t−1, published before O(t)) and `hist_ps_share4` (PS share t−4..t−1) |
| E | E56 (sealed E57) | |
| F | E58-EW (sealed) | |
| G | price projection rule (sealed) | |
| H | persistence; majority class (always LOW) | |
| SOP-Q3 | the six thesis baselines, from the E55 baseline run | 45 rows only; they cannot forecast 2024-Q2 |

**Decisions:** HIGH forecast = P(HIGH) ≥ 0.5. **Warning** (E58-EW form) = P_price ≥ 0.5.

## 6. Final-candidate choice (one rule, DEV only)

- Among A, C and D, the final E60 candidate is the one with the **lowest DEV Brier of P(HIGH)**.
- If its DEV Brier is not lower than A's by at least 0.005, the simpler candidate is kept, in the order A, C, D.
- The final candidate is then compared with E56 and E58-EW on all 50 rows and on TEST.

## 7. Questions and criteria (fixed here)

**Q-news (does news add value):** C vs A, all 50 rows.
- Paired Brier difference of P(HIGH), with quarter-cluster bootstrap CI (4000 draws, seed 60).
- Quarter-level sign test on Brier.
- **News adds measurable value only if** both hold:
  - the CI upper bound is < 0;
  - ONSET recall of the C warning is ≥ A's.
- B vs majority class and climatology (Brier) shows whether news alone carries any signal.

**Q-improve (does the final candidate beat E58-EW):** all 50 rows, warning form. **Improved only if** all hold:
- accuracy ≥ EW's;
- balanced accuracy ≥ EW's;
- ONSET recall ≥ EW's;
- false-positive rate ≤ EW's + 0.05;
- paired Brier vs EW's P_price with CI upper bound < 0.

**75% goal:** pooled accuracy, and the number of quarters ≥ 0.75, are reported as found.

**Multiplicity:** three news-related candidates (B, C, D). Any "news helps" finding outside Q-news is labelled exploratory.

## 8. Not allowed

- Changing labels, thresholds, splits, the classifier rules or the candidates after the freeze.
- Choosing by TEST or by the 50-row results.
- Articles published on or after the issue date.
- Pre-2021 data; data after 2026-10-14.
- Fabricated articles or labels.

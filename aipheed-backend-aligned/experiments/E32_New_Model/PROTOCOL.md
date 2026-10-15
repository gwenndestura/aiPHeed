# E32 protocol: a new forecasting model built on the E31 improvements

**Status: FROZEN before any E32 candidate was fitted or scored.** The SHA-256 is in `runner/PROTOCOL_SHA256.txt`, and the git commit is recorded in the ledger.

**Written 2026-10-15** after only the descriptive diagnosis (`runs/e32_diagnosis.json`) and the rice-CPI acquisition.

**Model id:** `E32-<candidate>`. The served candidate, if any, is versioned `aiPHeed-E32.1`.

## 1. What E31 changed, and whether it reaches a model's inputs

| E31 change | Affects model inputs? | How E32 uses it |
|---|---|---|
| Validated news relevance (R1.1) and FSSI-v2 | **Yes** | Province and region news features |
| Verified SWS posting dates (2026) and September 2026 round | **Yes** | As-of availability of H; one more labelled quarter |
| PSA food CPI to September 2026 (D, Dnow) | **Yes** | D features through 2026-Q3 |
| Forecast/nowcast alignment rule | **Yes (timing)** | Forecast features use only quarter-t news for target t+k, with cutoff at the origin |
| Collector date limit | Yes (nothing after 2026-10-14) | Data window |
| Dashboard data layer, alerts, schema, NaN, PDF, migrations | **No** (software only) | Not claimed as a model improvement |

New in E32 (made possible by E31's acquisition route): provincial rice CPI YoY, PSA OpenStat 0012M4ACP23 code 5, 2021-01 to 2026-09.

## 2. Targets

- **Primary: T1 (approved Chapter I label).** S1 = H + 2D, HIGH if S1 > τ.
  - τ is the median S1 of the labelled quarters whose rounds were all posted before the origin (E23 rule, `pcf_engine.threshold_at`).
  - Each forecast is scored against its own origin's τ.
- **Secondary (exploratory, reported only):**
  - **TR "rising":** HIGH if S1(T) exceeds the S1 of the latest labelled quarter published at the origin, for the same province. Chapter I 1.2 asks to identify LGUs "where the risk of food insecurity is most likely to be rising".
  - **T2 price pressure:** D(T) > 0.

  Neither replaces T1. Any target change needs the adviser.

## 3. Origins, leads and periods

- **Origin and lead:**
  - Origin O(t) = 00:00 PHT on the first day of quarter t+1 (E25 convention). Lead k targets quarter t+k, for k = 1, 2.
  - Information is restricted to what was published before O(t):
    - SWS rounds by posting date (`rounds_at_origin`);
    - D up to t−1;
    - Dnow and rice months 1–2 of t;
    - news of quarter t published in t (the E31 FORECAST rule: evidence quarter = T−k).
- **Training pairs at O(t), lead k:** features as of O(t') and the label of t'+k, for t' + k ≤ t − 1, with every round of t'+k posted before O(t). There are no random splits.
- **Periods (chronological):**
  - **Selection:** lead-1 targets 2023-Q4 to 2025-Q4. These quarters have labels: 2023-Q4, 2024-Q1–Q4, 2025-Q1, 2025-Q4.
  - **Development test:** targets 2026-Q1, 2026-Q2, 2026-Q3. Each is scored once, after selection is fixed. These quarters were examined in earlier experiments, and 2026-Q3 in E31, so this is development evidence, not an unseen test.
  - **Final test (prospective):** 2026-Q4 (lead 1 from O(2026-Q3) = 2026-10-01) and 2027-Q1 (lead 2 from the same origin).
    - Predictions are frozen and committed in E32.
    - They are scored only after the SWS December 2026 round and the Q4 CPI are released.

## 4. Candidates (fixed list; nothing may be added after freezing)

**Feature vector X(t) for province p** (all as of O(t)):
- **hunger:**
  - `H_last` (mean of the latest posted quarter's rounds);
  - `H_gap` (quarters from the latest posted round to t+k);
  - `H_trend` (H_last minus the previous posted quarter's H);
  - `H_margin` = H_last − τ.
- **prices:**
  - `D_last` = D(t−1);
  - `Dnow` (months 1–2 of t);
  - `rice_rel` = province rice YoY minus the five-province mean, months 1–2 of t.
- **news (E31):**
  - `news_n` = log1p(validated articles, p, t);
  - `news_reg` = log1p(validated articles, region, t);
  - `news_direct_share`;
  - `fssi_v2` (missing → 0) with `fssi_missing`.
- **history:** `y_last` = label of the latest published quarter (at the current τ).

| Id | Model | Notes |
|---|---|---|
| **E32-PCFN** | PCF structure with news and rice. H: the PCF21 local-level filter; the level forecast is shifted by β·news_reg, where β comes from least squares of the round-to-round change on news_reg over past training pairs, shrunk ×0.5. D: OLS without intercept of D(t+k) on [D_last, Dnow, rice_rel, news_n]. Then P(S1 > τ) as in PCF21. | New engine; same probability law as PCF21 |
| **E32-LR** | L2 logistic regression on the standardized X (C = 1.0, class_weight=None). | — |
| **E32-LGBM** | LightGBM on X with fixed parameters: num_leaves 4, min_data_in_leaf 5, n_estimators 150, learning_rate 0.05, feature_fraction 0.8, bagging off, seed 32, deterministic. | No tuning |
| **E32-ENS** | Mean of E32-PCFN and calibrated persistence. | — |

**References**, on identical rows:
- PCF21 (same engine, recomputed on the E31 inputs);
- P45 (E25/extension predictions, common rows only);
- persistence (B1);
- calibrated persistence (B1p);
- climatology;
- always-HIGH (majority class).

## 5. Selection rule (applied once, on the selection period)

1. Among E32-PCFN, E32-LR, E32-LGBM and E32-ENS, choose the lowest mean per-date Brier at lead 1 (T1).
2. Ties within 0.005 go to the simpler model, in the order PCFN < LR < ENS < LGBM.

## 6. Acceptance criteria for serving the selected model instead of PCF21

All must hold on the development walk-forward, lead 1, T1, all dates (selection plus development test):

| # | Criterion |
|---|---|
| A1 | Mean per-date Brier below PCF21's |
| A2 | Mean per-date Brier no worse than persistence's |
| A3 | Accuracy ≥ 0.75 (the researcher's requirement) |
| A4 | Inference verified at the operational origin: all inputs available at 2026-10-01, the timing tests pass, and the API serves the prediction with provenance |

- If A1–A4 hold, it is served as `aiPHeed-E32.1`, labelled EXPERIMENTAL until prospective validation.
- Otherwise PCF21 stays served, and the selected model is frozen prospectively as a research candidate.
- **No criterion is a claim of validated skill.** A RELIABLE claim needs unseen quarters.

## 7. Reporting (all candidates and references, identical rows)

- **Metrics by lead and period:** n, dates, HIGH/LOW, accuracy, balanced accuracy, precision, recall, F1, ROC-AUC and PR-AUC (flagged UNSTABLE when the minority class has fewer than 5 rows), Brier, confusion matrix, ECE (3 bins).
- **Uncertainty:** date-bootstrap 95% CIs.
- **Paired tests:** exact sign-flip test of per-date Brier differences against PCF21, persistence and always-HIGH.
- **Breakdowns:** by quarter and by province (descriptive).
- **Training accuracy is never reported as forecasting accuracy.**

## 8. Integrity rules

- Seeds are fixed, and one run is repeated for byte-identity.
- The development test and the final test are never used to change features, parameters or the selection.
- Any deviation is written to `DEVIATIONS.md` with a reason.
- The news relevance metrics are article-classification results. They are never presented as forecasting accuracy.

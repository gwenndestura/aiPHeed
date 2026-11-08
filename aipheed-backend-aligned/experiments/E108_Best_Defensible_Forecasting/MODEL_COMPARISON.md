# E108 Deliverable D: model comparison report

**Evidence status.** Retrospective rolling-origin results. **Development evidence:** every evaluated quarter had been examined by earlier experiments, and the factored design was chosen after E107's diagnosis on the same quarters. Rules frozen before scoring (`PROTOCOL.md`, sha `fc3e42f9…`). Scored once, by commit `0040da6` (runner clean). Sources: `out/results.json`, `out/predictions_T43_lead{k}.csv`, `out/diagnostics.json`.

**Units.** T43 rows are province-quarters, but inference is by quarter (cluster bootstrap, quarter sign-flip tests). Each quarter's five provinces share one hunger value.

## 1. Lead 1: 65 rows, 13 quarters (2023-Q1..2026-Q3), 16 HIGH; always-LOW scores 0.754

| Model | Accuracy (cluster 95% CI) | Balanced | HIGH recall | LOW recall | Precision HIGH | AUC | Brier | False-alarm rate | Missed-HIGH rate |
|---|---|---|---|---|---|---|---|---|---|
| **F1 (primary: factored, 15-row leaves)** | **0.892 (0.79–0.99)** | 0.865 | 0.81 | 0.92 | 0.76 | 0.917 | **0.098** | 0.08 | 0.19 |
| F0 (factored, 5-row leaves) | 0.908 (0.80–0.99) | 0.876 | 0.81 | 0.94 | — | 0.885 | 0.106 | 0.06 | 0.19 |
| F2 (factored + structural prior) | 0.892 (0.77–1.00) | 0.865 | 0.81 | 0.92 | — | 0.944 | 0.105 | 0.08 | 0.19 |
| STRUCT (H1 × CPI projection, no learning) | 0.892 | — | — | — | — | — | 0.109 | — | — |
| PSA-only logistic × H1 (Obj. 4-II) | 0.892 | — | — | — | — | — | 0.116 | — | — |
| Logistic, all 12 × H1 (Obj. 4-IV) | 0.754 | — | — | — | — | — | 0.176 | — | — |
| NLP-only logistic × H1 (Obj. 4-III) | 0.708 | — | — | — | — | — | 0.208 | — | — |
| Climatology / majority | 0.754 | — | — | — | — | — | 0.208 | — | — |
| Persistence (Obj. 4-I) | 0.723 | — | — | — | — | — | 0.277 | — | — |
| E56, existing production LightGBM (50 rows) | 0.840 (F1 on the same rows 0.860) | — | — | — | — | — | 0.125 (F1 0.115) | — | — |
| E107 direct LightGBM (40 rows) | 0.750 (F1 on the same rows 0.900) | — | — | — | — | — | 0.183 (F1 0.084) | — | — |

F1 confusion matrix: TP 13, FP 4, FN 3, TN 45. "—" marks values not computed for that arm in this table; they are in `out/results.json`.

**Paired by quarter (F1 minus comparator, Brier summed per quarter; one-sided sign-flip p):**

| F1 vs | p |
|---|---|
| Persistence | 0.006 |
| NLP-only | 0.008 |
| LR-12 | 0.027 |
| E107 | 0.031 |
| Climatology | 0.064 |
| F0 | 0.19 |
| PSA-only | 0.24 |
| STRUCT | 0.33 |
| E56 | 0.37 |
| F2 | 0.38 |

**Reading.**
- F1 is clearly better than persistence, the NLP-only and all-12 logistic baselines, and E107.
- It is better than climatology at p = 0.064.
- It is **not distinguishable** from the no-learning CPI projection, the PSA-only logistic or E56.
- The Lead-1 skill comes from the price projection. LightGBM on all 12 indicators preserves that skill but does not add measurable skill on top.

**Calibration (F1, Lead 1).** Calibration-in-the-large is +0.06. Five bins (mean P → observed rate):

| Bin | Rows | Mean P | Observed |
|---|---|---|---|
| 0–0.2 | 38 | 0.11 | 0.08 |
| 0.2–0.4 | 9 | 0.31 | 0.00 |
| 0.4–0.6 | 1 | 0.42 | 0.00 |
| 0.6–0.8 | 12 | 0.72 | 0.75 |
| 0.8–1.0 | 5 | 0.87 | 0.80 |

Reasonable, given 65 rows.

**Quarter by quarter** (correct out of 5; HIGH = observed HIGH provinces; * = hunger at or below 11.3%):

| Quarter | HIGH | F1 | F0 | F2 | STRUCT | PSA-LR | Persistence | Climatology | E56 | E107 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2023-Q1* | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | — | — |
| 2023-Q2* | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | — | — |
| 2023-Q3* | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | — | — |
| 2023-Q4 | 3 | **2** | 2 | 2 | 2 | 2 | 2 | 2 | 2 | — |
| 2024-Q1 | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | — |
| 2024-Q2 | 4 | 5 | 5 | 5 | 4 | 4 | 4 | 1 | 4 | 1 |
| 2024-Q3 | 1 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 5 | 4 |
| 2024-Q4 | 3 | 5 | 5 | 5 | 5 | 3 | 4 | 2 | 3 | 2 |
| 2025-Q1 | 4 | 4 | 4 | 5 | 5 | 5 | 2 | 1 | 5 | 5 |
| 2025-Q4 | 0 | **3** | 4 | 2 | 4 | 5 | 1 | 5 | 4 | 4 |
| 2026-Q1 | 0 | 5 | 5 | 5 | 5 | 5 | 1 | 5 | 5 | 5 |
| 2026-Q2 | 1 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| 2026-Q3 | 0 | 5 | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 5 |

- **2023-Q4, hunger onset: missed.** The latest SWS round at the issue date (2023-Q2) was exactly 11.3%, so H1 = 0.50 and P ≤ 0.5.
- **2024-Q2, price onset: caught** in all 4 HIGH provinces.
- **2025-Q4: 2 false alarms.** Price pressure was expected, but disinflation came.

## 2. Leads 2–4

| | Lead 2 (55 rows, 11 q) | Lead 3 (45, 9) | Lead 4 (35, 7) |
|---|---|---|---|
| Always-LOW accuracy | 0.709 | 0.711 | 0.743 |
| F1 accuracy / balanced / HIGH recall / AUC / Brier | 0.691 / 0.616 / 0.44 / 0.557 / 0.231 | 0.622 / 0.529 / 0.31 / 0.703 / 0.193 | 0.600 / 0.404 / 0.00 / 0.137 / 0.289 |
| F0 | 0.709 / 0.666 / 0.56 / 0.557 / 0.249 | 0.689 / 0.644 / 0.54 / 0.721 / 0.189 | 0.400 / 0.306 / 0.11 / 0.156 / 0.305 |
| F2 | 0.691 / 0.616 / 0.44 / 0.574 / 0.233 | 0.644 / 0.544 / 0.31 / 0.721 / 0.202 | 0.514 / 0.382 / 0.11 / 0.248 / 0.311 |
| STRUCT accuracy / Brier | 0.709 / 0.230 | 0.600 / 0.212 | 0.514 / 0.273 |
| PSA-only × H1 | 0.691 / 0.238 | **0.756 / 0.145** | 0.343 / 0.348 |
| Climatology | 0.709 / 0.258 | 0.711 / 0.262 | 0.743 / 0.236 |
| Persistence | 0.582 / 0.418 | 0.444 / 0.556 | 0.543 / 0.457 |
| E56 (rows) | 0.725 / 0.216 (40) | 0.657 / 0.233 (35) | — |
| FIRI v2 (Lead 2 only) | 0.418 | — | — |

**Reading.**
- Beyond one quarter no model, learned or structural, beats "always LOW" on accuracy with useful HIGH detection.
- At Lead 2, F1's Brier is below persistence (p = 0.03) but not below climatology (p = 0.35).
- **2024-Q2 is missed at Lead 2** (1 of 5 correct). That onset is visible only one quarter ahead, from the latest prices.
- The CPI projection holds the latest index flat. Its information about the target quarter's prices fades after one quarter, and the other indicators do not replace it (section 4).

## 3. Regional SWS hunger (R): the observed outcome, one row per quarter

| Lead | Quarters (HIGH) | H1 accuracy / Brier | Persistence | Climatology | E107 regional LGBM | Level MAE, points (random walk / MA2 / mean) |
|---|---|---|---|---|---|---|
| 1 | 12 (10) | 0.833 / 0.083 | 0.833 / 0.167 | 0.500 / 0.307 | 0.583 / 0.272 | **3.33** / 4.24 / 5.81 |
| 2 | 11 (10) | 0.727 / 0.177 | 0.727 / 0.273 | 0.455 / 0.352 | 0.571 / 0.250 | **5.51** / 5.66 / 6.59 |
| 3 | 10 (10) | 0.800 / 0.170 | 0.600 / 0.400 | 0.400 / 0.389 | 0.000 / 0.316 | **6.14** / 6.69 / 7.26 |
| 4 | 9 (9) | 0.778 / 0.167 | 0.556 / 0.444 | 0.333 / 0.395 | 0.200 / 0.373 | **6.28** / 6.84 / 7.95 |

**Reading.**
- The latest reading (random walk) is the best level forecast at every lead.
- **Lead 1:** H1 has the same accuracy as persistence (R3 fails). Its Brier is lower but not significantly so (p = 0.25).
- **Leads 3–4:** every evaluated quarter is HIGH, so HIGH/LOW discrimination cannot be assessed.
- **Regional hunger is not forecastable beyond its latest published SWS round with these data.** A one-quarter error is about 3.3 points.

## 4. Indicator contribution (F1; full tables in `INDICATOR_AUDIT.md` §4)

- **A1, the price projection, is the only family with a clear, stable contribution.**
  - Removing affordability costs 0.21 accuracy at Lead 1 (p = 0.008).
  - Shuffling A1 raises Brier by 0.14.
- **The hunger outlook H1** adds +0.05 Brier at Lead 1 when shuffled.
- **E1 (unemployment)** adds a small, consistent +0.008.
- **Climate/harvest, vulnerability and news add nothing measurable.**
  - N1 and C1 are never used by any fitted tree.
  - The cause is coverage and variation (N1 is 83% missing; C1 is national 0/1).
- The model **does rely almost entirely on price information** for provincial differences. National inputs move every province together.

## 5. Practical early-warning value for DA (Lead 1, F1)

- **Warning time:** issued on day 1 of the quarter it describes, before any of that quarter's outcome is published. SWS rounds post about 10 days to 3.5 months after fieldwork (E13 outcome audit).
- **Detection:** 13 of 16 HIGH province-quarters detected (missed-HIGH rate 0.19). Price-driven onset caught (2024-Q2, 4/4); hunger-driven onset missed (2023-Q4).
- **False alarms:** 4 of 49 LOW rows (rate 0.08), two of them in 2025-Q4.
- **Variation:**
  - P differs across provinces within a quarter by SD 0.14 on average, which comes entirely from provincial price inputs.
  - Over time, P moves between about 0.06 and 0.79 (quarter means), so it is not stuck HIGH or LOW.
- **Explanations:** TreeSHAP of the price part, plus the regional hunger factor shown separately. The explanation is dominated by A1, so "why risk changed" will usually read as "projected food inflation versus the province's usual level".
- **Beyond one quarter** the forecasts carry no reliable warning (`MAX_LEAD_DECISION.md`).

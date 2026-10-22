# E95 protocol: root-cause correction of the unified LightGBM (frozen before scoring)

**Branch.** `e95-root-cause-breakthrough`, from `e94-final-unified-lgbm` (bf8a059). Production is unchanged.

**Freezing.** This file and `runner/run_e95.py` are hashed into `PROTOCOL.sha256` and committed before the run.

## 1. Target audit (traced from the code; descriptive)

**How T43 is built** (`e40_spec`, `labels_all`).

T43(p, q) = 1 when **both** hold:
1. **Hunger:** the regional SWS Balance Luzon hunger (mean of the quarter's posted rounds) is above **11.3%**, the
   P60 of 2021-Q1..2022-Q4.
2. **Price:** **either** province food YoY (the quarter mean of three monthly YoY) is above the province's P60 of
   2021–22, **or** food YoY minus headline YoY is above its P60.

**What the thresholds are.**

| Province | Food YoY P60 | Gap P60 |
|---|---|---|
| Cavite | 4.71 | 0.74 |
| Laguna | 6.05 | 0.61 |
| Quezon | 6.24 | −0.56 |
| Rizal | 7.10 | 0.92 |
| Batangas | 7.15 | 0.66 |

**Findings on the 65 evaluation rows:**
- The hunger condition is met on 76.9%.
- T43 equals the price condition on 78.5%. Since 2023-Q4, T43 is the price condition.
- The hunger part is **regional**: every province gets the same value, so provinces differ only through prices.
- The price condition has 5–9 transitions per province over 2022–2026, which makes it learnable.
- The hunger condition has one regime change.

**Verdict.**
- T43 is a **proxy**: provincial food-price pressure under elevated regional hunger.
- It is not a measure of household food insecurity, and it is **not redefined** here.
- The only measured food-insecurity outcome available every quarter is regional SWS involuntary hunger. It is
  evaluated below as a **separate research target**, with the same timing and leakage rules.

## 2. Root cause of the K = 1 false alarms (diagnosed before this protocol)

**What happened.** At the 2025-Q3 origin, the E93/E94 price component gave P(price condition) = 0.68–0.82 for Cavite,
Laguna and Batangas.
- At that origin, food YoY was 2–5 points **below** threshold, the gap was below threshold, and rice was deflating
  8–15%. Every current price signal pointed LOW.

**Why.** LightGBM contributions show **cumF4** (cumulative food YoY over the last four origins) adding +0.56..+0.73 and
dominating, together with the gap projection.
- cumF4 is a **regime-memory** feature: it remembers the 2023–24 inflation episode after inflation has ended.
- The price model learned "past inflation high → HIGH" from 16 label quarters containing one inflation episode.

**Disclosure.** This defect was found by inspecting 2025-Q4, which is in the confirmation block. Selection below uses
only the 2023–24 selection block. After E83–E94, the 2023–2026 quarters are development evidence only.

## 3. Arms (one framework; components fitted once per origin on pooled K = 1..4; K as input; news required)

The hunger component is the E93/E94 linear-tree LightGBM hunger-change regressor, unchanged in every arm. Only the
price component differs:

| Arm | Price component |
|---|---|
| **M-U95-BASE** | E94 M-U94 (must reproduce exactly) |
| **M-U95-PRUNE** | Same, without regime-memory features: cumF4, ENSO run, typhoon run, ENSO-run × rice, and the 2-origin news sums |
| **M-U95-CORE** | A parsimonious, monotone LightGBM on current state and target-quarter projections only. Features: K; food and gap relative to thresholds; base-effect and structural projections; momentum; 1-quarter changes; rice YoY, momentum and acceleration; **the ten news indicators**. Monotone increasing in the six "relative to threshold" features; min 10 rows per leaf; 80 trees. |

## 4. Selection, K, comparisons (rules unchanged)

**Selection.** Lowest mean Brier over K = 1..3 on targets 2023-Q1..2024-Q4. The confirmation block (2025-Q1..2026-Q3)
is reported separately.

**PASS.** The E83 rule at every K.

**Validated K.** The E91 rule: PASS and temporal generalization at every horizon 1..K.

**Comparisons.** E94/E93, E92, S-COV, persistence, climatology, always-LOW and all E83 baselines.

**Research target** (separate; never used for selection or PASS): regional SWS hunger > 11.3 at t+K, one row per
target quarter.
- The framework's hunger component is compared with hunger persistence, hunger climatology and always-HIGH.
- Accuracy, Brier, and Holm-adjusted per-quarter sign-flip tests are reported.

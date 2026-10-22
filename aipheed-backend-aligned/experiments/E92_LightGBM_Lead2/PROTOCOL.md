# E92 protocol: a LightGBM-only Lead-2 model (frozen before scoring)

**Request (2026-10-22).** "Improve the accuracy to lead 2 and make it a machine learning LightGBM."

**Branch.** `e92-lightgbm-lead2`, from `e91-unified-horizon-model`. Production is not touched.

**Freezing.** This file and `runner/run_e92.py` are hashed into `PROTOCOL.sha256` and committed before the run.

## 1. Why a new design is needed

The proposed LightGBM is trained directly on T43 labels and cannot forecast early rows at Lead 2: it needs at least
6 label quarters and 5 HIGH, so 40 of 65 rows went unissued. In the E83 hybrid, those rows came from the S-SIM
simulation. That simulation is not machine learning, and on its own LightGBM rows the hybrid scored 0.44 at Lead 2.

## 2. Design: every forecast probability comes from LightGBM

T43 = regional hunger > 11.3 **and** provincial price condition. The two parts are learned separately, so each has
far more training labels than T43 itself.

**Pooled horizons.** Training pairs from Leads 1, 2 and 3 are pooled, with the horizon k as an input (as in E91).

| Arm | Hunger part | Price part | Combination |
|---|---|---|---|
| **M-LGB-DEC** | LightGBM P(regional hunger > 11.3 at the target) | LightGBM P(price condition at the target), drivers only | product |
| **M-LGB-DEC-S** | as M-LGB-DEC | the same price model plus the structural simulation's mean food and gap projections as two engineered input features | product |
| **M-LGB-STACK** | — | — | direct LightGBM on pooled T43 labels, with hunger, price and projection features. Where it cannot be fitted (fewer than 6 label quarters or 5 HIGH), it issues M-LGB-DEC-S. |

**Hunger part.**
- One regional row per origin and horizon, labelled with the SWS hunger quarter posted before O(t).
- Features: horizon, last hunger level relative to 11.3, its last change and age, and regional means of rice
  inflation and momentum, unemployment change, underemployment, remittances, ENSO, typhoons and world rice.

**Price part.**
- One row per province, origin and horizon, labelled with the price condition (E40 food or gap thresholds), from CPI
  published by O(t). These labels exist every quarter from 2022-Q1.
- Features: food and gap relative to thresholds, momentum, base-effect projections, rice retail/wholesale, world
  prices and policy events.

**LightGBM settings.**
- 4 leaves, depth 2, 100 trees, learning rate 0.05, λ = 5.
- At least 5 rows per leaf (3 for the hunger part).
- Monotone increasing in the "relative to threshold" features (food, gap, projections, hunger level).

**When a part cannot be fitted yet.** The hunger part needs at least 8 rows with at least 2 of each class. The price
part needs at least 6 label quarters with at least 5 of each class. Otherwise the part outputs its own smoothed
training-label frequency, (positives + 0.5) / (n + 1), and the shares of origins with a fitted LightGBM are reported.

**Leakage guards.** Every label is known before O(t); features come from `d.cut(t)`; imputation uses training rows
only. Threshold 0.5.

## 3. Selection and evaluation (rules unchanged)

**Selection.** Lowest Lead-2 Brier on targets 2023-Q1..2024-Q4. Targets 2025-Q1..2026-Q3 are reported as confirmation.

**Rules.** The E83 PASS rule and the pre-set generalization criteria, at Lead 2. Leads 1 and 3 are reported for the
same model.

**Comparisons.** S-COV (0.800), S-SIM, HYB-GBA-SIM, E91 U-GB, and all E83 baselines.

**Promotion over S-COV (the current best Lead-2 model).** Requires all three:
1. more quarters won than lost;
2. a lower Brier;
3. HIGH recall at least as high.

**Disclosure.** All 13 target quarters were scored in earlier experiments; only the sealed quarters are unseen.

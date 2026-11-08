# E128 geographic and class bias audit

## Geographic

**Not performed, by design.**
- The only valid target is the SWS Balance Luzon regional estimate.
- No provincial or LGU label exists, so no provincial or LGU test labels were created. Copying the regional value would make 5 or 142 copies of one observation.

**Provincial and municipal generalization cannot be established from this target.**
- Any provincial display (dashboard, FIRI3) is a separate composite index, not a validated forecast of local food insecurity.

**Most predictors are not CALABARZON-specific either.**

| Coverage | Features |
|---|---|
| National | Unemployment and remittances; GDELT news; ONI |
| Basin-wide | Typhoon count (PAR) |
| Region IV-A | CPI, farmgate prices, production, NASA climate |
| Five provinces summed | aiPHeed news volume |

## Class (T1, all outer rows)

| Lead | Outer rows | HIGH / LOW | Majority-class (training) accuracy | LightGBM TP / FP / TN / FN | LightGBM HIGH recall | LOW recall | Persistence TP / FP / TN / FN |
|---|---|---|---|---|---|---|---|
| 1 | 13 | 11 / 2 | 0.62 | 6 / 0 / 2 / 5 | 0.55 | 1.00 | 9 / 0 / 2 / 2 |
| 2 | 8 | 8 / 0 | 0.38 | 7 / 0 / 0 / 1 | 0.88 | n/a | 8 / 0 / 0 / 0 |
| 3 | 7 | 7 / 0 | 0.57 | 6 / 0 / 0 / 1 | 0.86 | n/a | 7 / 0 / 0 / 0 |
| 4 | 6 | 6 / 0 | 0.67 | 0 / 0 / 0 / 6 | 0.00 | n/a | 6 / 0 / 0 / 0 |

**Majority-class accuracy below 0.5** (for example, Lead 2 at 0.38) happens because the training majority is often LOW (2021–23) while the outer targets are HIGH. That mismatch is the regime shift.

## Class (T4, sensitivity)

| Lead | HIGH / LOW | LightGBM TP / FP / TN / FN | HIGH recall | LOW recall | Balanced accuracy |
|---|---|---|---|---|---|
| 1 | 8 / 3 | 5 / 0 / 3 / 3 | 0.63 | 1.00 | 0.81 |
| 2 | 5 / 3 | 2 / 2 / 1 / 3 | 0.40 | 0.33 | 0.37 |
| 3 | 5 / 2 | 1 / 0 / 2 / 4 | 0.20 | 1.00 | 0.60 |
| 4 | 4 / 2 | 0 / 0 / 2 / 4 | 0.00 | 1.00 | 0.50 |

## Findings

**1. Class bias against the HIGH (food-insecure) class.**
- The learned models under-predict HIGH because their training years were mostly LOW.
- LightGBM misses 5 of 11 HIGH quarters at T1 Lead 1, and 6 of 6 at Lead 4.
- For an early-warning system this is the dangerous direction: **false negatives in the worst hunger quarters on record** (2025-Q3 23.8 %, 2026-Q1 22.4 %, 2026-Q3 23.6 % at Lead 4).

**2. Majority-class prediction.**
- LightGBM does not simply predict the training majority (it predicts HIGH at Leads 2–3).
- But it is not better than majority + persistence either (R4 fails at every lead).

**3. LOW-class evaluation is impossible beyond Lead 1 under T1** (0 LOW rows).

**4. `class_weight = balanced`** was available in the grid and was chosen inside folds. It did not remove the bias, which comes from the shift, not from weighting.

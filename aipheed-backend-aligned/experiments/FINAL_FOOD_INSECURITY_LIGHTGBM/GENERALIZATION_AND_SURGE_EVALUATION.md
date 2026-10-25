# Generalization and surge evaluation

**Evidence status**
- **Development evidence:** every 2021+ quarter had been seen in E107–E113.
- **Untouched evidence:** the 2003–2020 targets of the secondary arm, and the prospective seal.
- **Independence:** the 4 areas share national shocks, and E111 estimated about 2.1 effective areas per quarter. Overlapping leads are not independent either, so every test resamples whole target quarters.

Source: `out/results_general.json`.

## 1. Across periods (FIL, ELEVATED accuracy)

| Lead | Period | Rows | FIL | Persistence | MA2 | Logistic | FIL MAE | Persistence MAE |
|---|---|---|---|---|---|---|---|---|
| 1 | 2023 (early) | 4 | 0.50 | 0.50 | 0.50 | 0.50 | 2.29 | 2.92 |
| 1 | 2024 (surge) | 16 | **0.19** | **0.81** | 0.69 | 0.56 | 8.70 | 6.84 |
| 1 | 2025+ (recent) | 24 | 0.38 | 0.50 | 0.38 | 0.62 | 4.31 | 4.21 |
| 2 | 2024 | 16 | 0.31 | 0.69 | 0.31 | 0.44 | 9.50 | 8.49 |
| 2 | 2025+ | 24 | 0.46 | 0.46 | 0.54 | 0.42 | 5.07 | 4.31 |
| 3 | 2024 | 12 | 0.50 | 0.00 | 0.42 | 0.67 | 12.05 | 11.32 |
| 3 | 2025+ | 24 | 0.42 | 0.54 | 0.58 | 0.46 | 5.95 | 4.04 |
| 4 | 2024 | 8 | 0.62 | 0.00 | 0.50 | 1.00 | 15.47 | 14.39 |
| 4 | 2025+ | 24 | 0.46 | 0.54 | 0.58 | 0.33 | 5.54 | 3.89 |

**Lead-1 quarter by quarter** (correct out of 4 areas)

| Quarter | FIL | Persistence |
|---|---|---|
| 2023-Q4 | 2 | 2 |
| 2024-Q1 | 0 | 3 |
| 2024-Q2 | 1 | 3 |
| 2024-Q3 | 1 | 3 |
| 2024-Q4 | 1 | 4 |
| 2025-Q2 | 0 | 0 |
| 2025-Q3 | 2 | 2 |
| 2025-Q4 | 2 | 3 |
| 2026-Q1 | 2 | 2 |
| 2026-Q2 | 2 | 4 |
| 2026-Q3 | 1 | 1 |

**Performance is not stable.**
- FIL collapses in 2024: it expected hunger to fall back.
- No method is consistently good in 2025+, when hunger oscillated around 20%.
- Persistence does well in 2024 only because hunger kept rising.

**Long history, untouched 2003–2020.** FIL-LONG is flat across thirds, which is stability at chance level:

| Lead | Accuracy by third (early / middle / late) |
|---|---|
| 1 | 0.50 / 0.47 / 0.54 |
| 2 | 0.51 / 0.52 / 0.52 |
| 3 | 0.54 / 0.54 / 0.58 |
| 4 | 0.55 / 0.52 / 0.53 |

## 2. Across areas (Lead 1, 11 quarters each)

| Area | FIL | Persistence | Logistic | FIL MAE | Persistence MAE |
|---|---|---|---|---|---|
| BL (CALABARZON's area) | 0.09 | 0.82 | 0.73 | 5.13 | 3.77 |
| NCR | 0.36 | 0.45 | 0.73 | 4.60 | 3.05 |
| Visayas | 0.45 | 0.64 | 0.45 | 5.81 | 5.89 |
| Mindanao | 0.36 | 0.55 | 0.45 | 7.35 | 7.48 |

Persistence's 0.82 in BL comes from 8 of 11 Lead-1 quarters being ELEVATED during the 2024–26 rise. It is not a validated skill: at Leads 3–4 persistence scores 0.33–0.38 in BL.

## 3. Rising vs falling hunger (Lead 1)

| Direction | Rows | FIL | Persistence | FIL MAE | Persistence MAE |
|---|---|---|---|---|---|
| Rising | 30 | 0.23 | 0.67 | 6.59 | 5.44 |
| Falling or flat | 14 | 0.50 | 0.50 | 3.87 | 4.20 |

FIL is slightly better when hunger falls, and much worse when it rises. This is the mean-reversion bias in §1.

## 4. Sharp increases

**Definition:** the new reading exceeds the newest known reading by more than that reading's survey margin (E111 definition).

**2021+ (FIL)**

| Lead | Events | FIL flags ELEVATED | Persistence flags ELEVATED | FIL mean error (pp) | Persistence mean error (pp) |
|---|---|---|---|---|---|
| 1 | 10 | 2 / 10 | 4 / 10 | −11.0 | −10.5 |
| 2 | 13 | 5 / 13 | 5 / 13 | −11.2 | −10.6 |
| 3 | 13 | 7 / 13 | 0 / 13 | −11.4 | −11.5 |
| 4 | 10 | 6 / 10 | 0 / 10 | −13.3 | −13.1 |

The Lead-1 events are VIS 2024-Q1, NCR 2024-Q2, VIS and MIN 2024-Q3, BL, VIS and MIN 2024-Q4, BL 2025-Q3, MIN 2025-Q4 and VIS 2026-Q1.

**Untouched 2003–2020 (FIL-LONG)**

| Lead | Events | FIL-LONG flags ELEVATED | Persistence flags ELEVATED |
|---|---|---|---|
| 1 | 40 | 0.58 | 0.30 |
| 2 | 44 | 0.57 | 0.32 |
| 3 | 42 | 0.67 | 0.00 |
| 4 | 56 | 0.75 | 0.00 |

**Can sharp increases be anticipated? No.**
- Every method under-predicts the size of a surge by 10–13 points.
- FIL-LONG flags more surge quarters than persistence. But it flags ELEVATED in 40–46% of *all* quarters, with precision near the base rate (0.53 at Lead 1). These flags are not surge-specific warnings.
- Persistence, by construction, never calls a rise at long leads.
- No indicator family or news category anticipated the 2024 surge in a way that replicated (`NEWS_FEATURES_AND_CONTRIBUTION.md` §4).

## 5. By true horizon

At Lead k the newest SWS reading is usually k+1 quarters before the target: 136 of 152 rows. The exception is the 2025-07-01 issue (16 rows), when the April 2025 round was already published (27 June). Accuracy shows no pattern by true horizon beyond the lead pattern (`out/results_general.json` → `true_horizon`).

## 6. Conclusion

| Question | Answer |
|---|---|
| Does performance generalize across quarters? | **No** skill to generalize. FIL fails in the 2024 surge. FIL-LONG is stable but at chance on 70 untouched quarters. |
| Does it work in both rising and falling hunger? | FIL: no (0.23 rising, 0.50 falling). FIL-LONG: chance in both. |
| Does it anticipate sharp increases? | No |
| Is it independent confirmation? | The untouched 2003–2020 evaluation is the independent check, and it confirms the absence of a predictable signal. |

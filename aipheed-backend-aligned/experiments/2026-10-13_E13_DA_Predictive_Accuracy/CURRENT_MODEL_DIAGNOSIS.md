# Current Model Diagnosis: Why Almost Everything Is HIGH (E13)

**Data.** Realized S1, H and D for 2021–2025 (`metrics.json` → `diagnosis`). S1[p,t] = H[t] + 2 × D[p,t]; HIGH if S1 > τ0 = 10.84335.

**Scope.** The served dashboard model and its stored predictions were **not opened** (they are protected or carrier files). This diagnosis explains the label that the served model and the E9 models were trained to reproduce.

## 1. The pattern

| Period | HIGH / labelled rows | Share |
|---|---|---|
| 2021 | 8 / 15 | 53% |
| 2022 | 8 / 15 | 53% |
| 2023 | 11 / 20 | 55% |
| 2024 | 19 / 20 | 95% |
| 2025 (2 labelled quarters) | 10 / 10 | 100% |
| **E9–E12 test quarters** (2023-Q4..2025-Q1, 2025-Q4) | **33 / 35** | **94%** |

From 2024-Q2 onward **every** province-quarter is HIGH.

## 2. Cause 1: the threshold was fixed in a low-hunger period

- **How τ0 was set:** it is the median S1 of 2021-Q2..2023-Q2. In those quarters the **median regional hunger was 10.8%**, so τ0 sits almost exactly at the regional hunger level of that period.
- **What happened next:** in the test quarters the median regional hunger was **18.1%**. SWS Balance-Luzon hunger was 14.3% in 2023-Q4, then rose: 15.3, 19.6, 18.1, 25.3 and 24.0 (2025-Q1), and was 16.7 in 2025-Q4.
- **Result:** the rise is real, and it is measured independently of aiPHeed. Against a threshold anchored to 2021–2023, it makes the regional term H − τ0 large and positive for every province at once.

## 3. Cause 2: one regional value dominates five provincial labels

- **The arithmetic:** S1 − τ0 = (H − τ0) + 2D. The first term is the same for all five provinces. The second term is the only provincial part.

| Measure | All 80 rows | Test quarters |
|---|---|---|
| Mean \|H − τ0\| (regional term) | 4.37 | **8.20** |
| Mean \|2D\| (provincial term) | 2.92 | **2.84** |
| S1 HIGH/LOW equals the H-only call (H > τ0) | 76.3% | **94.3%** |

- **Why LOW became impossible:** a province is LOW only if D < (τ0 − H)/2. The table shows what that required:

| Quarter | H | D needed for LOW | Observed D range | LOW provinces |
|---|---|---|---|---|
| 2023-Q4 | 14.3 | < −1.73 | −2.39 to 1.74 | Quezon |
| 2024-Q1 | 15.3 | < −2.23 | −2.26 to 1.01 | Quezon |
| 2024-Q2 | 19.6 | < −4.38 | −1.39 to 3.57 | none |
| 2024-Q3 | 18.1 | < −3.63 | −2.10 to 4.20 | none |
| 2024-Q4 | 25.3 | < −7.23 | −1.67 to 4.60 | none |
| 2025-Q1 | 24.0 | < −6.58 | −2.11 to 5.22 | none |
| 2025-Q4 | 16.7 | < −2.93 | −1.82 to 1.45 | none |

  From 2024-Q2 onward, no province's relative food-price pressure came close to the level needed for LOW. **The label could not have been LOW for any province.**

## 4. Cause 3: trained models copy the label's base rate

- In E9, every model trained on S1, including LightGBM, gave probabilities of 0.98–0.99 from 2024-Q2 onward.
- The "always HIGH" rule scored 94.3% accuracy.
- Any model fitted to this label reproduces the dominant class. **More features or tuning cannot fix a label whose HIGH/LOW is set mostly by one regional value.**

## 5. Is "all HIGH" wrong?

**It cannot be shown to be wrong or right**, because there is no provincial food-insecurity outcome (see `OUTCOME_DATA_AUDIT.md`).

**What it does mean:**

1. **Relative to 2021–2023, regional hunger was higher in 2024–2025.** That part of the signal is real and independently measured.
2. **The label stopped distinguishing between provinces.** A label that is HIGH everywhere gives DA no basis for prioritizing one province over another.
3. **The provincial part (D) still differs every quarter.** In 2024–2025 Q1, Quezon's relative pressure was the highest (D = 3.6 to 5.2). This information is hidden by the combined label.

## 6. What does not fix it

| Idea | Why not |
|---|---|
| Re-anchor τ to a later period | The documented prospective τ = 14.345 would still give **30/35 HIGH** in the test quarters (information only, not evaluated), because H itself stays above it. A threshold chosen to produce a "balanced" share would be tuned to the label distribution, which the brief prohibits. |
| Change the SWS weight | E12 showed that the weight on H changes only the shared level, never the provincial ranking. |
| A different classifier or more features | The label, not the classifier, causes the pattern (§4) |

## 7. Diagnosis in one line

**The all-HIGH output is a property of the label, not a model failure:**

- a regional hunger rise, measured against a threshold set in a low-hunger period;
- the same regional value added to all five provinces;
- the result is a provincial label that, from 2024-Q2, restates the regional level.

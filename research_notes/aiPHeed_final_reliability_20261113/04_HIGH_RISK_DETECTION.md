# 04 — HIGH-risk detection report (Lead 1)

Evidence: `evidence/REL_HIGH_cases_L1.csv`, `REL_false_alarms_L1.csv`, `REL_by_region_L1.csv`, `REL_threshold_sensitivity.csv`.

## 1. Summary
- **HIGH found:** 20 of 25 (recall 0.80, 95 % CI [0.615, 0.947]).
- **Precision:** 0.80 (20 of 25 HIGH calls are correct). HIGH F1 = 0.80.

| Round | HIGH | Detected | Missed |
|---|---|---|---|
| 2018 | 8 | 8 | — |
| 2019 | 13 | 11 | Lanao del Norte (59.0 %, p 0.32); Misamis Oriental (54.8 %, p 0.38) |
| 2021 | 4 | **1** (Tawi-Tawi) | Agusan del Sur (57.9 %, p 0.41); Masbate (59.4 %, p 0.15); Occidental Mindoro (56.3 %, p 0.21) |

**False alarms (5):**
- 2018: Camarines Norte 44.1 %, Iloilo 48.7 %, Sorsogon 41.4 %.
- 2019: Quirino 32.4 %, Southern Leyte 44.3 %.

## 2. Why the misses happen (from the 11-13 root-cause studies; no new tuning)
- **2021:** the anchors were projected about 24 points down, through the anchor change plus the RATE term. The elapsed-time trend is counted twice: the anchor is refreshed to the latest round, but RATE multiplies by the own-survey gap of 24 quarters, which is longer than any training gap (≤ 20). The three missed provinces fell only 7–10 points, while their peers fell 18–34.
- **Lanao del Norte 2019:** displacement after the Marawi siege (about 139,700 people). The inputs carry no displacement information.
- **Misamis Oriental 2019:** the outcome is borderline (54.8 %, about 1.9 SE above 50). The cause is not established.

## 3. Comparison with persistence
- **Persistence:** 24 of 25 HIGH found (recall 0.96), but precision is only 0.48 (26 false alarms).
- **FINAL:** gives up 4 detections in exchange for 21 fewer false alarms.
- **In 2021,** persistence found all 4 HIGH provinces, while FINAL found 1. So FINAL is **not** a reliable HIGH detector when the survey gap is longer than anything in its training data.

## 4. Threshold sensitivity (reported only; the 0.50 cut-off is not moved)

| Cut-off | Accuracy | Precision | Recall | HIGH F1 | TP/FP/FN/TN |
|---|---|---|---|---|---|
| 0.30 | 0.764 | 0.605 | 0.92 | 0.730 | 23/15/2/32 |
| 0.40 | 0.792 | 0.656 | 0.84 | 0.737 | 21/11/4/36 |
| 0.45 | 0.806 | 0.690 | 0.80 | 0.741 | 20/9/5/38 |
| **0.50** | **0.861** | **0.800** | **0.80** | **0.800** | 20/5/5/42 |
| 0.55 | 0.847 | 0.792 | 0.76 | 0.776 | 19/5/6/42 |
| 0.60 | 0.861 | 0.826 | 0.76 | 0.792 | 19/4/6/43 |
| 0.65 | 0.792 | 0.813 | 0.52 | 0.634 | 13/3/12/44 |

- Results hold between 0.50 and 0.60. Above 0.60, recall collapses.
- No cut-off reaches 2021 recall above 2/4 without adding false alarms.
- Lowering the cut-off is post-test tuning and is **not** adopted.

## 5. Status
| Criterion | Result |
|---|---|
| HIGH recall ≥ 0.75 pooled | **PASS** (0.80) |
| HIGH recall ≥ 0.50 in every round | **FAIL** (2021: 0.25) |

With only 4 HIGH provinces in 2021, that round's recall is decided by one or two provinces. It cannot show either reliability or unreliability with confidence: the exact binomial 95 % CI for 1/4 is [0.006, 0.806].

# Forecast candidate comparison (62 verdict quarters, identical origins)

**Sources:** `out/obj4_table.json`, `out/ce5_results.json`, `out/ce2_results.json`, `S1_RESULTS.md`.

| Lead 1 | Accuracy | Balanced | Precision | Recall | F1 | AUC | Brier | Failed | MRLT |
|---|---|---|---|---|---|---|---|---|---|
| C-b (sealed main) | **0.790** | **0.717** | **0.812** | 0.907 | **0.857** | 0.702 | **0.1874** | R7 | 2 |
| S1 (Kalman) | 0.806 | 0.743 | 0.830 | 0.907 | 0.867 | 0.711 | 0.1871 | none | 2 |
| **C-E2 (demo)** | 0.774 | 0.690 | 0.796 | 0.907 | 0.848 | 0.715 | 0.1875 | R3, R7 | **3** |
| C-E2-NONEWS | 0.774 | 0.690 | 0.796 | 0.907 | 0.848 | 0.711 | 0.1889 | R3, R7 | 3 |
| C-E4 | 0.758 | 0.664 | 0.780 | 0.907 | 0.839 | 0.703 | 0.1921 | R3, R7 | 2 |
| C-E3 | 0.726 | 0.597 | 0.741 | 0.930 | 0.825 | 0.646 | 0.1980 | R2, R3, R7 | 0 |
| C-E5R | 0.661 | 0.594 | 0.750 | 0.767 | 0.759 | 0.659 | 0.2116 | R2–R5, R7 | 0 |
| C-E5C | 0.613 | 0.530 | 0.711 | 0.744 | 0.727 | 0.640 | 0.2224 | R2–R5, R7 | 0 |

| Lead 2 | Accuracy | Balanced | Precision | Recall | F1 | AUC | Brier | Failed |
|---|---|---|---|---|---|---|---|---|
| C-b | 0.790 | 0.717 | 0.812 | 0.907 | 0.857 | 0.704 | 0.1837 | R7 |
| S1 | 0.806 | 0.743 | 0.830 | 0.907 | 0.867 | 0.715 | 0.1805 | none |
| **C-E2** | 0.758 | 0.679 | 0.792 | 0.884 | 0.835 | 0.694 | 0.1879 | R3, R7 |
| C-E2-NONEWS | 0.758 | 0.679 | 0.792 | 0.884 | 0.835 | 0.693 | 0.1890 | R3, R7 |
| C-E4 | 0.758 | 0.679 | 0.792 | 0.884 | 0.835 | 0.692 | 0.1910 | R3, R7 |
| C-E3 | 0.645 | 0.568 | 0.733 | 0.767 | 0.750 | 0.652 | 0.2088 | R2–R5, R7 |
| C-E5R | 0.645 | 0.568 | 0.733 | 0.767 | 0.750 | 0.635 | 0.2148 | R2–R5, R7 |
| C-E5C | 0.597 | 0.533 | 0.714 | 0.698 | 0.706 | 0.623 | 0.2377 | R2–R5, R7 |

## Candidates vs C-b and C-E2 (paired Brier, one-sided bootstrap)

| | vs C-b L1 | vs C-b L2 | vs C-E2 L1 | vs C-E2 L2 |
|---|---|---|---|---|
| C-E2 | +0.0001 (p 0.51; CI −0.018..0.018) | +0.0042 (p 0.69; CI −0.014..0.022) | — | — |
| S1 | −0.0004 (p 0.46) | −0.0033 (p 0.22) | — | — |
| C-E5R | +0.0241 (p 0.93) | +0.0311 (p 0.99) | +0.0240 | +0.0269 |
| C-E5C | +0.0350 (p 0.95) | +0.0539 (p 1.00) | +0.0349 | +0.0497 |
| C-E2-NONEWS | +0.0015 | +0.0053 | +0.0014 | +0.0011 |

## Reading

- **No candidate improves on C-b with statistical support.**
- **S1** is the only one to pass R1–R7, and that rests on one forecast.
- **C-E2** has the longest reliable lead (3), but lower accuracy at Leads 1–2 than C-b.
- **C-b remains the main model.** Adopting C-E2 or S1 would need the pre-registered rule, plus team and adviser
  approval.

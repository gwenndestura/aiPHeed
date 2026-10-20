# E51: a stricter HIGH (trailing percentile instead of median), lead 1

Experiment only. Nothing served was changed.

- **Run:** `20261016T053009Z` (`E51_results.json`, `runs/…/predictions.csv`, `runner/e51_run.py`).
- **Threshold:** τ_q(t) is the q-th percentile of the published pooled S1 from 2021-Q1 to t−1 (the served publication filter). H_margin and y_last use the variant's τ.
- **Arms:** A is the served pipeline (E48-A1 pool + E49-C2). B is the E50-R4 paper blend.
- **Reproduction:** P50 reproduces E49-C2 exactly (accuracy 0.846, Brier 0.151, Q4 2026 0.778).

| Variant | HIGH share 2021-Q3..2026-Q3 | HIGH share 2024–26 | Arm | Acc. | Bal. acc. | AUC | Brier | BSS vs climatology | p ≥ 0.99 | Q4 2026 index |
|---|---|---|---|---|---|---|---|---|---|---|
| P50 (served) | 70.6% | 93.3% | A | 0.846 | 0.841 | 0.855 | 0.151 | 0.23 | 0 | 0.778 |
| P67 | 64.7% | 91.1% | A | 0.785 | 0.790 | 0.828 | 0.185 | 0.23 | 1 | 0.790 |
| P67 | | | B | 0.723 | 0.727 | 0.832 | 0.164 | 0.31 | 0 | 0.783 |
| P75 | 56.5% | 86.7% | A | 0.600 | 0.630 | 0.650 | 0.272 | 0.07 | 0 | 0.707 |
| P75 | | | B | 0.600 | 0.630 | 0.714 | 0.247 | 0.16 | 0 | 0.713 |

**Adoption rule (fixed before the run).** All of the following must hold:
- HIGH share of all labelled quarters between 25% and 60%
- HIGH share of 2024–26 at or below 75%
- AUC ≥ 0.80
- balanced accuracy ≥ 0.75
- Brier ≤ persistence
- Brier skill score > 0
- no test p ≥ 0.99

**Result: no variant passes, so E49-C2 (median) stays.**
- **Recent quarters stay HIGH.** Even at the 75th percentile, 87% of 2024–26 province-quarters are HIGH, because 2024–26 S1 sits in the top quarter of the 2021–26 history.
- **Stricter thresholds cost skill.** At P75 the model can no longer separate the classes (AUC 0.65–0.71).

The high recent index is a property of the data (hunger 17–24% in 2024–26 against about 10% in 2021–23), not of the threshold choice.

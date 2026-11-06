# Model comparison report

**Sample:** n = 72 per lead (about 46 effective). Intervals are region-cluster bootstraps with 2,000 draws.

## Lead 1
| | Always-LOW | Persistence | PSA-only | E158 | E164 (withdrawn) | E165 | **E166** | E167 |
|---|---|---|---|---|---|---|---|---|
| Accuracy | 65.3 % | 62.5 % | 55.6 % | 73.6 % | 79.2 % | 73.6 % | **76.4 %** | 66.7 % |
| Balanced accuracy | 0.50 | 0.70 | 0.65 | 0.76 | 0.81 | 0.77 | **0.80** | 0.73 |
| Macro F1 | 0.40 | 0.62 | 0.55 | 0.73 | 0.79 | 0.73 | **0.76** | 0.67 |
| HIGH recall (caught / 25) | 0 | 24 | 24 | 21 | 22 | 22 | **23** | 23 |
| False alarms | 0 | 26 | 31 | 15 | 12 | 16 | 15 | 22 |
| Brier | 0.335 | 0.213 | 0.228 | 0.134 | 0.122 | 0.121 | 0.125 | 0.156 |
| Within-region concordance | n/a | 0.70 | n/a | 0.60 | 0.725 | 0.70 | **0.75** | 0.65 |

## Lead 2
| | E158 | E166 | E167 |
|---|---|---|---|
| Accuracy | 73.6 % | **79.2 %** | 68.1 % |
| Balanced accuracy | 0.76 | **0.82** | 0.75 |
| HIGH caught / missed | 21 / 4 | **23 / 2** | 24 / 1 |
| False alarms | 15 | **13** | 22 |
| Brier | 0.137 | **0.125** | 0.153 |

## Paired comparisons with E158 (Lead 1)
| Candidate | Brier difference [95 %] | McNemar (only candidate right / only E158 right) | Verdict |
|---|---|---|---|
| E166 | −0.010 [−0.038, +0.020] | 7 / 5, p = 0.77 | Better point estimates, **not significant** |
| E165 | −0.013 [−0.036, +0.008] | 5 / 5, p = 1.00 | Equal |
| E167 | +0.022 [−0.014, +0.058] | 2 / 7, p = 0.18 | Worse |
| E158 vs persistence | −0.078, interval below 0 | n/a | **Significant** |

## By round (Lead 1)
| Round | E158 accuracy / Brier / bias | E166 accuracy / Brier / bias |
|---|---|---|
| 2018 (n = 22) | 63.6 % / 0.150 / +5.1 | **72.7 %** / **0.134** / +6.8 |
| 2019 (n = 25) | 68.0 % / 0.172 / +5.4 | **76.0 %** / **0.142** / +5.4 |
| 2021 (n = 25) | **88.0 %** / **0.083** / −1.5 | 80.0 % / 0.098 / −2.0 |

## CALABARZON (Lead 1, one row per province)
| Province (round) | Observed | E158 | E166 |
|---|---|---|---|
| Laguna 2018 | 26.2 | 35.5 | 35.1 |
| Quezon 2019 | 44.0 | 48.0 | 45.2 |
| Rizal 2019 | 39.1 | 42.7 | 37.5 |
| Batangas 2021 | 39.9 | 26.2 | 27.3 |
| Cavite 2021 | 35.5 | 29.3 | 27.3 |

- All 10 classifications are LOW and correct.
- **CALABARZON has no HIGH test case.**

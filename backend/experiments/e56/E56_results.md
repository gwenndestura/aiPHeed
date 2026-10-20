# E56: label definitions (Eq. 3 variants) with E53-A1, lead 1

Run `20261017T010108Z`. Experiment only; nothing served changes. S1 = H + 2D in every variant; only the HIGH rule changes, and every threshold uses only quarters published before the origin. Model, inputs, pool, seed, nested walk-forward and C2 shrinkage are identical to E53-A1 (no tuning). Scored on the 13 E53 development quarters (65 rows).

| Label | Rule |
|---|---|
| L0 | HIGH if S1 > median of all published quarters (served) |
| L1 | HIGH if S1 > median of the last 8 published quarters |
| L2 | HIGH if S1 > median of the last 4 published quarters |
| L3 | HIGH if S1 above the five-province median of the same quarter (D only) |

L0 reproduction of E53-A1: accuracy 0.785, balanced 0.836, AUC 0.880, Brier 0.150, Q4 2026 CALABARZON 0.789 (E53-A1: 0.785 / 0.836 / 0.880 / 0.150 / 0.789).

## 1. Label statistics

Each labelled province-quarter is labelled at its own lead-1 origin.

| Label | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | 2024–2026 | quarters all 5 HIGH | LOW rows in the 65 | labels differ from L0 |
|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0% | 47% | 55% | 95% | 90% | 93% | 93% | 6 of 17 | 12 | 0% |
| L1 | 0% | 47% | 55% | 100% | 70% | 87% | 89% | 6 of 17 | 14 | 5% |
| L2 | 0% | 47% | 65% | 95% | 50% | 47% | 69% | 4 of 17 | 21 | 15% |
| L3 | 40% | 40% | 40% | 40% | 40% | 40% | 40% | 0 of 19 | 39 | 38% |

## 2. E53-A1 retrained per label (65 rows)

| Label | Accuracy | Balanced | AUC | Brier | LOW caught | Persistence acc / bal | Always-majority (training) acc / bal | Majority (hindsight) acc |
|---|---|---|---|---|---|---|---|---|
| L0 | 0.785 | 0.836 | 0.880 | 0.150 | 11/12 | 0.877 / 0.860 | 0.738 / 0.775 | 0.815 (HIGH) |
| L1 | 0.723 | 0.694 | 0.754 | 0.210 | 9/14 | 0.769 / 0.723 | 0.677 / 0.665 | 0.785 (HIGH) |
| L2 | 0.569 | 0.520 | 0.652 | 0.265 | 8/21 | 0.785 / 0.791 | 0.646 / 0.527 | 0.677 (HIGH) |
| L3 | 0.723 | 0.705 | 0.764 | 0.190 | 31/39 | 0.631 / 0.615 | 0.600 / 0.500 | 0.600 (LOW) |

## 3. Q4 2026 forecast (origin 2026-10-01) and five-driver shares

| Label | CALABARZON | Cavite | Laguna | Batangas | Rizal | Quezon | τ | training HIGH share |
|---|---|---|---|---|---|---|---|---|
| L0 | 0.789 | 0.916 | 0.912 | 0.284 | 0.917 | 0.917 | 14.993 | 73% |
| L1 | 0.772 | 0.790 | 0.801 | 0.661 | 0.801 | 0.806 | 18.957 | 72% |
| L2 | 0.614 | 0.636 | 0.598 | 0.561 | 0.636 | 0.636 | 19.683 | 63% |
| L3 | 0.463 | 0.511 | 0.418 | 0.184 | 0.474 | 0.729 | – | 40% |

Five-driver shares, CALABARZON (%, of the five drivers):

| Label | market | climate | fish_kill | employment | ofw_remittance |
|---|---|---|---|---|---|
| L0 | 60 | 5 | 14 | 19 | 2 |
| L1 | 57 | 0 | 0 | 43 | 0 |
| L2 | 98 | 0 | 0 | 0 | 2 |
| L3 | 84 | 1 | 13 | 0 | 2 |

Per province:

| Label | Province | market | climate | fish_kill | employment | ofw_remittance |
|---|---|---|---|---|---|---|
| L0 | Cavite | 58 | 3 | 14 | 23 | 2 |
| L0 | Laguna | 51 | 9 | 18 | 19 | 3 |
| L0 | Batangas | 66 | 5 | 11 | 17 | 1 |
| L0 | Rizal | 57 | 7 | 15 | 19 | 2 |
| L0 | Quezon | 67 | 1 | 12 | 18 | 2 |
| L1 | Cavite | 16 | 0 | 0 | 84 | 0 |
| L1 | Laguna | 59 | 0 | 0 | 41 | 0 |
| L1 | Batangas | 67 | 0 | 0 | 33 | 0 |
| L1 | Rizal | 59 | 0 | 0 | 41 | 0 |
| L1 | Quezon | 59 | 0 | 0 | 41 | 0 |
| L2 | Cavite | 98 | 0 | 0 | 0 | 2 |
| L2 | Laguna | 87 | 0 | 0 | 0 | 13 |
| L2 | Batangas | 98 | 0 | 0 | 0 | 2 |
| L2 | Rizal | 98 | 0 | 0 | 0 | 2 |
| L2 | Quezon | 98 | 0 | 0 | 0 | 2 |
| L3 | Cavite | 82 | 0 | 13 | 0 | 5 |
| L3 | Laguna | 71 | 7 | 19 | 0 | 3 |
| L3 | Batangas | 98 | 0 | 1 | 0 | 1 |
| L3 | Rizal | 70 | 0 | 28 | 0 | 2 |
| L3 | Quezon | 94 | 0 | 4 | 0 | 2 |

## Adoption (rule fixed before results)

| Label | (a) HIGH share 2024–26 in 30–70% | (b) bal ≥ 0.75 and ≥ persistence | (c) AUC ≥ 0.75 | (d) keeps H | Eligible |
|---|---|---|---|---|---|
| L0 | **no** | **no** | yes | yes | **no** |
| L1 | **no** | **no** | yes | yes | **no** |
| L2 | yes | **no** | **no** | yes | **no** |
| L3 | yes | **no** | yes | **no** | **no** |

**Result: none eligible -> keep L0.** L0 is the incumbent and is not re-judged; L3 is reported only.

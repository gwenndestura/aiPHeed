# E121 FIRI3 weighting sensitivity

**Source.** `out/weighting_sensitivity.csv` and `out/leave_one_indicator_out.csv`. The approved method is **equal weights** and is unchanged. Alternatives are reported only.

**Rows compared:** provincial 75, regional 10.

**Columns:**
- **Flip:** the score changes side of 0.5.
- **Band Δ:** the band changes.

## 1. Alternative weights

| Variant | Provincial mean Δ | Provincial max Δ | Provincial flip | Provincial band Δ | Province-rank ρ | Regional mean Δ | Regional max Δ | Regional band Δ |
|---|---|---|---|---|---|---|---|---|
| Redundancy-adjusted (FIRI v2 rule C2) | 0.012 | 0.040 | 1.3% | 1.3% | 0.93 | 0.012 | 0.034 | 0% |
| Component-count | 0.042 | 0.109 | 17.3% | 18.7% | 0.75 | 0.042 | 0.146 | 20% |
| Feature-count | 0.041 | 0.129 | 16.0% | 18.7% | 0.76 | 0.045 | 0.135 | 20% |
| PCA first component (PC1 = 32%) | 0.045 | 0.187 | 21.3% | 26.7% | 0.86 | 0.065 | 0.135 | 30% |
| One indicator doubled (range over the 6) | 0.005–0.029 | 0.058–0.098 | 0–12% | 0–13% | 0.91–1.00 | 0–0.045 | 0–0.094 | 0–30% |
| One indicator halved (range) | 0.003–0.020 | 0.039–0.070 | 1–7% | 1–9% | 0.90–1.00 | 0–0.030 | 0–0.063 | 0–20% |
| Random Dirichlet(1), 300 draws (median) | 0.055 | 0.177 | 18.7% | 25.3% | 0.73 | 0.061 | 0.138 | 20% |

## 2. Removing one indicator

| Without | Provincial rows | Mean Δ | Max Δ | Band Δ | Province-rank ρ | Regional mean Δ | Regional band Δ |
|---|---|---|---|---|---|---|---|
| FMA | 21 | 0.035 | 0.076 | 14.3% | 0.97 | 0.055 | 20% |
| AFP | 21 | 0.011 | 0.031 | 4.8% | 1.00 | 0.036 | 20% |
| CEC | 21 | 0.022 | 0.051 | 19.0% | 0.93 | 0.030 | 10% |
| EHS | 25 | 0.027 | 0.090 | 8.0% | 0.90 | 0.068 | 30% |
| PSV | 71 | 0.015 | 0.105 | 1.4% | **0.77** | — | — |
| FIS | 75 | 0.007 | 0.088 | 1.3% | 0.97 | 0.044 | 20% |

**Row counts.** Removing an indicator leaves only the rows that remain computable: provincial rows with 5–6 indicators for FMA, AFP and CEC.

## 3. Reading

- **Equal weights are robust where the alternatives are reasonable.**
  - Redundancy-adjusted weights reproduce equal weights almost exactly (1.3% flips): the indicators are near-independent.
  - Doubling or halving one indicator moves scores by 0.03 on average.
- **The score level is robust; the band near 0.5 is not.** Arbitrary schemes (counts, PCA, random) move 16–27% of rows across a band boundary.
- **Regional scores are more weight-sensitive.** Only 10 quarters, with national EHS and FIS series that move sharply.
- **The province ranking depends mostly on PSV and EHS** (DI-1).

**Decision.** No change to the frozen equal weights.

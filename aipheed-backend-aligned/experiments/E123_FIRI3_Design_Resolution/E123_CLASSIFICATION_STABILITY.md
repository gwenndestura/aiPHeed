# E123 classification stability

**Source.** `out/classification_stability.csv`.

**What was tested.** The frozen chance bands (usual or below / above usual / elevated / high) applied without change. No threshold was searched or moved.

**What FIRI3 is.** A relative composite index: 0.5 = the 2021+ usual level. **It is not a calibrated probability of food insecurity.**

## Distribution

| | Provincial (75) | Regional (10) |
|---|---|---|
| Usual or below | 42 | 6 |
| Above usual | 30 | 4 |
| Elevated | 2 | 0 |
| High | 1 | 0 |
| Within one chance SD of 0.5 | **88%** | **70%** |

## Band changes under perturbation (share of computed rows)

| Perturbation | Provincial | Regional |
|---|---|---|
| Remove FMA | 16.0% | 20.0% |
| Remove AFP | 8.0% | 20.0% |
| Remove CEC | 16.0% | 10.0% |
| Remove EHS | **24.0%** | **30.0%** |
| Remove PSV | 1.3% | — (not regional) |
| Remove FIS | 2.7% | 20.0% |
| Redundancy-adjusted weights | 2.7% | 0% |
| Conditions 1/2 : structure 1/2 | 18.7% | 30.0% |
| Structure 2/3 : conditions 1/3 | 34.7% | 50.0% |
| Fixed common core vs overall | 1.3% | 22.2% |
| Cross-province core vs overall | 2.7% | — |

**Row counts.** Indicator removals compare only rows still computable without that indicator (provincial: 25 for FMA, AFP, CEC and EHS).

## Reading

- **Bands are stable under the comparability checks** (common core 1–3% provincial) and under redundancy-adjusted weights (3%).
- **Bands are unstable when a major indicator is removed** (8–24%) or **when the conditions/structure balance changes a lot** (19–35%). The regional bands are less stable, with only 10 quarters.
- **88% of provincial scores are within chance variation of 0.5.** "Above usual" therefore mostly means "near usual". Only 3 provincial scores (elevated 2, high 1) clearly exceed chance.

**Recommendation.** Report the band together with the leave-one-out range and the indicator set. Do not treat "above usual" as a risk signal on its own.

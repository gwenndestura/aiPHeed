# E123 weighting sensitivity

**Source.** `out/weighting_sensitivity.csv` and `out/weighting_by_quarter.csv`. The approved method is **equal weights** and is unchanged. SWS was not used.

**Rows compared:** 75 provincial, 10 regional.

**Columns:**
- **Rank ρ:** the mean Spearman correlation of the five-province ranking per quarter.
- **Same top:** the share of quarters with the same top province.

## Results

**Structure share under equal weights.** With equal indicator weights, current conditions (FMA, AFP, CEC, FIS) already get 4/6 of the weight and structure (EHS, PSV) gets 2/6.

| Variant | Provincial mean Δ | Provincial max Δ | Provincial band Δ | Rank ρ | Same top | Regional mean Δ | Regional band Δ |
|---|---|---|---|---|---|---|---|
| Redundancy-adjusted (E120 rule) | 0.012 | 0.039 | 2.7% | 0.95 | 87% | 0.012 | 0% |
| Conditions 1/2 : structure 1/2 | 0.033 | 0.071 | 18.7% | 0.92 | 87% | 0.045 | 30% |
| Structure 2/3 : conditions 1/3 | 0.069 | 0.152 | **34.7%** | 0.87 | 87% | 0.101 | 50% |
| One indicator ×2 (range) | 0.004–0.033 | 0.05–0.10 | 0–13% | 0.88–0.98 | 67–100% | 0–0.045 | 0–30% |
| One indicator ×0.5 (range) | 0.003–0.023 | 0.03–0.07 | 1–11% | 0.89–0.99 | 80–100% | 0–0.030 | 0–20% |
| Random Dirichlet(1), 300 draws (median) | 0.052 | 0.164 | 25.3% | 0.74 | 67% | 0.063 | 20% |

**Most weight-sensitive single indicator:** EHS. Doubling it gives rank ρ 0.88 and the same top province in only 67% of quarters.

## Stability across quarters

**Per-origin province ranks** (`out/weighting_by_quarter.csv`) under the two conditions/structure re-weightings:
- the ranks stay close in most quarters;
- most band changes occur in quarters where scores sit near 0.5.

## Conclusion

- **The score level is robust to reasonable weights.** Doubling or halving one indicator changes it by 0.003–0.03 on average.
- **The bands are not robust to large shifts in the conditions/structure balance.** Up to 35% of bands change.
- **The ranking is sensitive mainly to the weight on EHS.**

**No change to the equal weights is proposed.** The interpretability problem is handled by reporting the CCS and SVS separately (DI-1), not by re-weighting.

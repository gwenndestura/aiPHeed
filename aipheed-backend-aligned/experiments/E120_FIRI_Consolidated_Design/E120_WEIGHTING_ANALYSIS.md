# E120 weighting analysis

**Sources.** `runner/e120.py`. Results are in `out/sensitivity.csv`, and the weights in `out/summary.json`.

**Comparison basis.** Every variant is compared with **W1 (equal indicator weights)** on the provincial rows that both can compute (85 unit-origins, including regional rows where shown).

**Metrics:**
- mean and maximum absolute FIRI change;
- the share of rows whose side of 0.5 flips;
- the mean Spearman correlation of the five-province ranking per quarter.

## 1. Alternatives

| Variant | Weights (provincial) | Mean change | Max change | Class flips | Province-rank ρ | Assessment |
|---|---|---|---|---|---|---|
| **W1 equal (recommended)** | 1 each | — | — | — | — | Simple, reproducible; no indicator presumed more important; correct when indicators are near-independent and no outcome can identify weights |
| W2 component-count | AFP 5, FMA 4, CEC 3, others 1 | 0.042 | 0.146 | 17.6% | 0.75 | Rewards indicators with more components (more data, not more importance). AFP and FMA would dominate. |
| W3 feature-count (FIRI v2-style counting) | AFP 7, FMA 6, CEC 3, EHS 2, PSV 1, FIS 1 | 0.041 | 0.135 | 16.5% | 0.76 | Counts evidence by number of series: the double counting E119-R2 warned against |
| W4 redundancy-adjusted (FIRI v2 rule C2) | 0.64–0.98 | 0.012 | 0.040 | 1.2% | 0.93 | Nearly equal, because the indicator scores barely overlap. Adds complexity for almost no change. |
| W5 first principal component | FMA 0.44, AFP 0.41, EHS 0.10, CEC 0.05 (FIS, PSV too sparse: 0.25) | 0.047 | 0.187 | 21.2% | 0.86 | PC1 explains only 32%, and it ignores climate. A variance-driven weight is not an importance weight. |
| W6 random Dirichlet(1), 200 draws (median) | random | 0.056 | 0.184 | 18.8% | 0.74 | Bounds how much any arbitrary weighting could move scores |
| Evidence weights from SWS (FIRI v2 rule C3) | not computed | — | — | — | — | **Rejected in principle.** Weights learned from the regional target make the FIRI target-derived, so it cannot be a clean model predictor or be validated against SWS. |
| Expert (DA) weights | not available | — | — | — | — | Possible later: a pre-registered AHP or budget-allocation exercise with the DA IV-A respondents, reported with its spread |

## 2. Removing one indicator

| Without | Rows | Mean change | Max | Flips | Province-rank ρ |
|---|---|---|---|---|---|
| FMA | 31 | 0.041 | 0.090 | 16.1% | 0.97 |
| AFP | 31 | 0.019 | 0.078 | 6.5% | 1.00 |
| CEC | 31 | 0.025 | 0.062 | 12.9% | 0.93 |
| EHS | 35 | 0.039 | 0.142 | 14.3% | 0.90 |
| PSV | 81 | 0.013 | 0.105 | 1.2% | 0.77 |
| FIS | 85 | 0.011 | 0.107 | 2.4% | 0.97 |

**No single indicator dominates.**
- **The level of the FIRI** moves most without FMA or EHS.
- **The province ranking** moves most without PSV (ρ 0.77) or EHS (0.90). These are the two cross-province structural indicators, which carry most of the *between-province* difference. The dynamic indicators mostly carry the *over-time* difference.

## 3. Removing one feature (top effects)

| Without feature | Mean change | Max | Flips |
|---|---|---|---|
| EHS provincial unemployment | 0.023 | 0.075 | 11.8% |
| CEC heat | 0.018 | 0.060 | 10.6% |
| CEC cyclones 100 km | 0.016 | 0.043 | 8.2% |
| EHS underemployment | 0.023 | 0.075 | 8.2% |
| FMA wholesale rice | 0.019 | 0.056 | 7.1% |
| others | ≤ 0.020 | ≤ 0.107 | ≤ 5.9% |

**No feature removal moves the FIRI by more than 0.11.** The largest effects come from indicators with few features.

**Class flips (5–12%) mostly involve rows close to 0.5.** That is why the recommendation replaces the single 0.5 cut with chance bands.

## 4. Conclusion

**Recommended: W1, equal weights over the available indicators.** Inside each indicator, the components carry equal weight, with near-duplicates removed first.

1. **No outcome can identify weights at province level.** Using SWS would make the index target-derived.
2. **The indicator scores are nearly independent** (|ρ| ≤ 0.29 for every pair with at least 25 rows). Redundancy-adjusted weights reproduce equal weights almost exactly (1.2% flips).
3. **Weighting by component or feature counts, or by PCA, produces 17–21% flips.** That shows how much arbitrary weighting could change the reading. Equal weights avoid choosing among them.
4. **Equal weights are transparent to DA and LGU users**, and decompose exactly into each indicator's push above or below the usual level.

**Weights may change only through a pre-registered process:**
- an expert elicitation; or
- a validation against an outcome not used elsewhere, such as CBMS FIES.

Never by tuning to a desired share of HIGH.

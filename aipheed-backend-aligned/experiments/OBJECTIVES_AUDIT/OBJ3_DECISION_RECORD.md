# Objective 3: decisions for the adviser (evidence prepared; nothing changed in the served outputs)

Evidence:
- `OBJ3_SPATIAL_VALIDATION.md`;
- `out/obj3_spatial.json`;
- `out/obj3_lgu_rank_intervals.csv`;
- `out/obj3_lgu_served_vs_thesis_eq6.csv` (all 142 LGUs, both formulas).

Map, ranking table and API consistency in the C-b mode are covered by the existing backend test
`test_lgu_index_is_06_poverty_04_density_within_province_times_the_province_score`.

## D3.1 Province score formula

| | Formula | Effect |
|---|---|---|
| Thesis (Algorithm 5 / Eq. 6) | LGU risk = **province forecast probability** × vulnerability | With a regional forecast, all five provinces get the same probability; provinces differ only through their LGUs |
| Served (C-b mode) | Province score = regional P × province poverty / max province poverty; LGU risk = province score × vulnerability | Provinces are ordered by poverty; the class stays regional. **Not in the thesis** |

**Difference:** 41 of 142 LGUs move by more than 20 places in the region-wide rank (`obj3_lgu_served_vs_thesis_eq6.csv`).
Top 3 under Eq. 6: Taytay, Lipa, Bauan.

**Options:**
- (a) adopt the thesis Eq. 6 as written;
- (b) keep the served province factor and add it to Chapter III as a documented deviation, justified by the regional
  forecast;
- (c) report region-wide ranks only within province.

## D3.2 Direction and size of the density weight

- **Finding:** poverty and density are negatively correlated (Spearman −0.53); the 40% density weight lifts dense,
  lower-poverty towns.
- **Sensitivity** (Kendall τ vs served):
  - poverty-only 0.71;
  - (0.8, 0.2) 0.82;
  - density as protective 0.46.
- **Conceptual arguments:**
  - *For a positive density weight (exposure):* more people are affected per area; urban households depend on
    purchased food.
  - *Against:* density is not a hardship measure; in CALABARZON it marks urban, lower-poverty municipalities.

**Options:**
- (a) keep 0.6/0.4 as in the thesis and disclose the correlation;
- (b) change the weights, which needs a written rationale independent of the resulting ranks.

## D3.3 Uncertainty display

- Median 90% rank interval is 51 places.
- Recommendation: show rank bands (e.g. top 10 / 11–30 / rest) or intervals, with the SAE CV disclosure for the 25
  LGUs with CV > 20%.
- This is a display change and needs approval.

## D3.4 Data provenance items

| Item | Status | Decision |
|---|---|---|
| Lucena poverty value | From a different PSA table (2021 Table 2a, whole per cent) | Disclosed |
| Population density year | POPCEN 2024 vs the thesis's 2020 census | Adviser to confirm 2024 |

## Independent work completed (does not depend on these decisions)

- All 5 + 142 values recomputed from the source tables (exact).
- Completeness: 142 LGUs, no missing values.
- Sensitivity across six weightings.
- Monte Carlo rank intervals.
- Province-level face check against ENNS 2021.

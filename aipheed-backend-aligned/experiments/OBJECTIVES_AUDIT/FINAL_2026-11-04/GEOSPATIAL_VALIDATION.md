# Geospatial validation (Objective 3)

**Interpretation (kept on every output):** the outcome is regional SWS Balance Luzon hunger. Province and LGU numbers
are **vulnerability-weighted estimates**, not measured provincial or municipal hunger.

## Five provinces (C-E2 demo export, 85 rows = 17 quarters × 5)

| Check | Result |
|---|---|
| Score = regional P × PSA 2023 poverty weight (families) | ✅ every row (|diff| < 1e-5) |
| Weight normalization (÷ highest province) | ✅ Quezon 1.000, Rizal 0.812, Laguna 0.783, Batangas 0.710, Cavite 0.623 |
| Class from regional P only (HIGH at 0.50) | ✅ every row; the province score never changes it |
| One regional P per quarter | ✅ |
| Independent recomputation from the PSA source table | ✅ max diff 0.0 (`OBJ3_SPATIAL_VALIDATION.md`) |
| Reproducibility | ✅ the C-E2 export regenerated today; `rows.csv` byte-identical |

## 142 LGUs (`lgu_vulnerability.csv`)

| Check | Result |
|---|---|
| Coverage | ✅ 142/142: Quezon 41, Batangas 34, Laguna 30, Cavite 23, Rizal 14 |
| Duplicate codes / missing poverty, population, area | ✅ 0 / 0 / 0 / 0 |
| Sources and years | PSA 2021 city and municipal SAE (141); PSA 2021 Table 2a (Lucena, 1); population 2024 |
| Precision | 25 LGUs have SAE CV > 20% |
| Independent recomputation | ✅ max diff 1e-16 |
| Rank uncertainty (1,000 Monte Carlo draws over the SAE CVs) | Median 90% rank interval 51 places, max 98. A coarse prioritisation, best shown as bands |

## Weighting sensitivity (`out/obj3_exposure.json`, `out/obj3_spatial.json`)

| Method | Kendall τ vs served | Spearman vs poverty | Top-10 mean poverty | Median / max rank change | LGUs moving > 20 |
|---|---|---|---|---|---|
| Served: poverty 0.6 + density 0.4 | 1.00 | 0.65 | 19.3% | 0 / 0 | 0 |
| Poverty 0.8 + density 0.2 | 0.82 | 0.78 | — | — | — |
| Poverty only | 0.71 | 0.83 | 25.3% | 11 / 89 | 34 |
| Poverty 0.6 + poor people 0.4 | 0.69 | 0.79 | 22.8% | 10 / 62 | 41 |
| Density protective (0.6, −0.4) | 0.46 | 0.81 | — | — | — |
| Paper Eq. 6 (province score = P) | see `obj3_lgu_served_vs_thesis_eq6.csv` | — | — | 41 LGUs move > 20 | — |

**Regional-measurement uncertainty:** every LGU inherits one regional probability. Differences between LGUs come only
from PSA poverty and density, never from local hunger data.

## Status

- **Completed:** implementation, reproducibility, sensitivity and uncertainty.
- **Pending external action:** the density-weight decision (adviser, `LGU_WEIGHTING_ADVISER_DECISION.md`).
- **Blocked by data:** validation against municipal hunger outcomes (none exist).

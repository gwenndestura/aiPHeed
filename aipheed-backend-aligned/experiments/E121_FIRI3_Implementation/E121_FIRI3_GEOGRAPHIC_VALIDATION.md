# E121 FIRI3 geographic validation

**Source.** `out/geographic_comparable.csv`, `out/geographic_indicator_means.csv` and the leakage checks.

## 1. Separation (all pass)

**Provincial FIRI3:**
- features come only from provincial series (`series_unit = province`);
- units are exactly Cavite, Laguna, Batangas, Rizal and Quezon;
- no `_R` (regional or national) feature enters a provincial score.

**Regional FIRI3:**
- features come only from Region IV-A, the CALABARZON centroid proxy, or national (PHILIPPINES) series;
- each feature records its own unit, so national series (PAR cyclones, unemployment change, remittances, GDELT) are labelled national, not CALABARZON;
- the regional FIRI3 is a CALABARZON-level summary built partly from national evidence, and is named as such.

**Annual data:**
- poverty and annual employment keep their reference year (`period` = "2021", "2024", …);
- no quarterly values are created; the latest published year is carried as-of with that year shown.

**FIRI v2 has no regional index.** Regional FIRI3 rows carry no v2 value.

## 2. Comparable comparison (same indicator set in all five provinces)

**Comparable origins.** 11 origins (2023-Q1 to 2025-Q3) have all five provinces computed with an identical indicator set. 4 more origins have mixed sets and are excluded from this comparison.

| Province | Comparable origins | Mean FIRI3 | Mean rank (1 = highest) | Times highest | Times lowest |
|---|---|---|---|---|---|
| Batangas | 11 | 0.578 | 1.55 | 7 | 0 |
| Rizal | 11 | 0.535 | 2.64 | 0 | 0 |
| Quezon | 11 | 0.498 | 3.18 | 3 | 3 |
| Cavite | 11 | 0.489 | 3.27 | 1 | 2 |
| Laguna | 11 | 0.424 | 4.36 | 0 | 6 |

**Rank agreement across origins.** Kendall's W = 0.42: moderate.

**Mean indicator scores on the same 11 origins:**

| Province | AFP | CEC | EHS | FMA | PSV |
|---|---|---|---|---|---|
| Batangas | 0.538 | 0.497 | **0.759** | 0.512 | 0.5 |
| Cavite | 0.507 | 0.506 | 0.373 | 0.544 | 0.7 |
| Laguna | 0.533 | 0.497 | **0.277** | 0.405 | 0.1 |
| Quezon | 0.574 | 0.492 | 0.382 | 0.505 | 0.9 |
| Rizal | 0.437 | 0.495 | 0.709 | 0.506 | 0.3 |

**PSV** enters only at 2025-Q3, so here it is the one comparable origin.

## 3. Reading

- **Most of the provincial differences come from EHS and PSV.**
  - AFP, CEC and FMA differ by at most 0.14 between provinces (CEC by 0.01).
  - EHS spans 0.28–0.76.
- **Batangas ranks highest** mostly because of its annual underemployment (31–40%, owner file; DI-6). Laguna ranks lowest because of low unemployment and underemployment ranks and the lowest food-price pressure.
- **Quezon is the poorest province (PSV 0.9) but only third.** Its employment ranks are middling, and poverty enters only from 2025-Q3.
- **These are differences in the *evidence*, not validated differences in food insecurity.** No provincial outcome exists to check them, and part of the difference is the structural design choice described in DI-1.

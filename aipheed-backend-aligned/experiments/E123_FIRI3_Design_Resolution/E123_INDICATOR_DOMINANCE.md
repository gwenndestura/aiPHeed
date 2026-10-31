# E123 indicator dominance

**Source.** `out/indicator_dominance.csv`, run on FIRI3 v1.2.

**Rows.** 75 provincial and 10 regional computed scores. Column definitions:
- **Share:** wᵢSᵢ / FIRI3, the indicator's share of the score.
- **Push:** (Sᵢ − 0.5)/k, how far the indicator moves the score away from 0.5.
- **Between-province explained:** the share of the variance of FIRI3 across the five provinces (on origins with the same indicator set) attributable to the indicator.

## Provincial

| Indicator | Rows | Mean score (SD) | Range | Mean share (min–max) | Mean \|push\| | Between-province variance explained | Without it: mean Δ / band Δ / rank ρ |
|---|---|---|---|---|---|---|---|
| FMA | 75 | 0.445 (0.176) | 0.10–0.88 | 0.21 (0.04–0.47) | 0.033 | 0.215 | 0.035 / 16% / 0.94 |
| AFP | 75 | 0.497 (0.150) | 0.18–0.79 | 0.23 (0.09–0.45) | 0.028 | 0.049 | 0.013 / 8% / 0.94 |
| CEC | 75 | 0.485 (0.166) | 0.12–0.83 | 0.23 (0.05–0.48) | 0.032 | 0.009 | 0.020 / 16% / 0.94 |
| **EHS** | 75 | 0.500 (0.237) | 0.10–0.90 | 0.23 (0.06–0.39) | **0.048** | **0.667** | 0.042 / **24%** / **0.68** |
| PSV | 25 | 0.500 (0.289) | 0.10–0.90 | 0.20 (0.04–0.40) | 0.044 | 0.669 (1 origin) | 0.017 / 1% / 0.72 |
| FIS | 14 | 0.458 (0.196) | 0.14–0.70 | 0.18 (0.05–0.35) | 0.023 | — | 0.006 / 3% / 0.95 |

**Most affected rows:**
- **FMA:** Cavite 2023-Q1/Q2 (+0.09).
- **AFP:** Rizal 2024-Q2 (−0.07); Batangas 2024-Q3 (+0.07).
- **CEC:** all provinces at 2023-Q2 (−0.10).
- **EHS:** Laguna 2024-Q3/Q4 (−0.10); Cavite 2023-Q1 (+0.10).
- **PSV:** Laguna (−0.08), Quezon (+0.08).

## Regional

| Indicator | Rows | Mean score | Mean share | Without it: mean Δ / band Δ |
|---|---|---|---|---|
| FMA | 10 | 0.288 | 0.12 | 0.055 / 20% |
| AFP | 9 | 0.478 | 0.20 | 0.036 / 20% |
| CEC | 10 | 0.497 | 0.23 | 0.030 / 10% |
| **EHS** (national unemployment change, remittances) | 10 | **0.731** | **0.33** | 0.068 / **30%** |
| FIS | 10 | 0.325 | 0.15 | 0.044 / 20% |

## Reading

- **Over time, no indicator dominates the score level.** All six have similar mean shares (0.18–0.23 provincially).
- **Between provinces, EHS dominates.**
  - On the 11 origins with the same four indicators, EHS explains **67%** of the province-to-province differences, FMA 22%, AFP 5%, CEC 1%.
  - EHS and PSV are cross-province *ranks* of annual structural data, so they spread provinces 0.1–0.9 by construction. The dynamic indicators are percentiles against a pooled history, so their province means are close.
  - **The FIRI3 provincial ranking is therefore mainly a structural ranking.** This is why DI-1 adds the CCS: the CCS ranking changes with current conditions (Kendall W 0.10), while the SVS barely moves (0.95).
- **Regionally, EHS is the largest and most influential component.** Its national series were well above their 2021+ history in 2024–26.

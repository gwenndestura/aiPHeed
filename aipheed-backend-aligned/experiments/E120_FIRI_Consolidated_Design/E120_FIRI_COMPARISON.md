# E120 comparison: served FIRI v2 vs. proposed consolidated FIRI

**Basis:**
- FIRI v2 from `backend/data/thesis/firi2_history.csv`, read only: 95 rows (85 back-test, 10 forecast), matched on origin quarter and province;
- the proposed FIRI from `out/level3_firi_equal.csv`.

## 1. Structure

| | FIRI v2 (served) | Proposed (E120) |
|---|---|---|
| Inputs | 12 indicators in 6 code domains (A, V, C, E, N, H) | 34 scored features → 6 indicators (FMA, AFP, CEC, EHS, PSV, FIS) |
| Datasets used | 12 series | 25 datasets scored, 19 more as profile, context or alternative; all 54 E119-R2 datasets mapped |
| Regional hunger (SWS) | Inside the index (H1, domain H) | **Outside**: it is the target, shown beside the index |
| Model output inside | A1 = LightGBM price-pressure probability | None |
| National values in provincial scores | C1, C2, E1, E2, H1 identical for all provinces | None; national data only in the regional FIRI, or shown as context |
| Normalization | Percentile against earlier origins (≥ 8); V1 min-max over 5 provinces | Percentile against earlier available 2021+ observations (≥ 8); annual/structural: mid-rank among the 5 provinces |
| Weights | Walk-forward evidence weights from regional SWS, shrunk to equal (2026-Q3: A 0.35, C 1.84, H 1.46, V 0.35; E and N 0) | Equal over available indicators; components equal inside each indicator |
| Threshold | HIGH ≥ 0.50 (the historical middle) | Chance bands: usual / above usual / elevated / high, by number of indicators available |
| Completeness | ≥ 4 of 6 domains | ≥ 4 of 6 provincial, ≥ 4 of 5 regional |
| Structural data timing | V1 used at every origin (Amendment 1 deviation) | Poverty only from its 2025-07-01 publication rule (strict) |

## 2. Offline agreement (75 matched province-quarters, 15 origins)

| Measure | Value |
|---|---|
| Spearman (all matched rows) | **−0.30** |
| Mean Spearman of the five-province ranking per quarter | **−0.07** |
| Same side of 0.5 | 38.7% |
| FIRI v2 rows HIGH | 81.3% |
| Proposed rows ≥ 0.5 | 44.0% (bands: 42 usual or below, 30 above usual, 2 elevated, 1 high) |

## 3. Why they disagree

1. **FIRI v2 is driven by components that are the same in every province.**
   - The H domain (regional hunger) and C2 / C1 (national) carry most of the v2 weight: C 1.84 and H 1.46 at 2026-Q3.
   - Its level follows regional hunger, and its 81% HIGH share follows the high SWS readings.
   - The proposed index contains neither.
2. **The province ordering differs** (mean rank ρ −0.07):
   - v2 orders provinces mostly by V1, where density carries 40% of the weight, and by the provincial A/C indicators;
   - the proposed index orders them by provincial poverty, provincial employment and provincial prices and production.
3. **The proposed index is not a forecast of SWS**, and v2 was weighted toward SWS. Disagreement is expected and is not evidence that either is "wrong".

## 4. Which is more defensible

The proposed FIRI is more defensible on every criterion that can be checked without an outcome:

| Criterion | FIRI v2 | Proposed |
|---|---|---|
| Uses the available data | 12 series; 13 relevant datasets unused | All relevant datasets assigned; 25 scored |
| Separates evidence and outcome | No (H1 inside; SWS-derived weights) | Yes |
| Separates FIRI and model | No (A1 is a model output) | Yes |
| Geography | National values repeated across provinces | Provincial FIRI from provincial data only |
| Double counting | C2 ≈ national; A1 overlaps A2/A3 | Near-duplicates removed and measured; indicators near-independent |
| Weights | SWS-derived | Equal, robustness shown |
| Threshold meaning | 0.5 = middle, presented as HIGH | Chance bands with an explicit meaning |

**What the proposed FIRI does not have:** a validated link to provincial food insecurity. No provincial outcome exists. **Neither index is validated at province level.**

# E121 FIRI3 protocol (frozen 2026-10-31, before implementation)

**Hash.** This file's SHA-256 is in `runner/PROTOCOL_SHA256.txt` and in `firi3.PROTOCOL_SHA256`. Every run checks both.

**Source.** The E120 design at commit d7f6be5:
- `E120_FIRI_FRAMEWORK.md`
- `E120_INDICATOR_SCORE_METHODOLOGY.md`
- `E120_FIRI_AGGREGATION_METHODOLOGY.md`
- `E120_FEATURE_DICTIONARY.csv`

**Status.** FIRI3 is a candidate composite index. It is **not** a validated provincial food-insecurity prediction and **not** a probability. FIRI v2 (`firi.py`) stays the served index. Adopting FIRI3 needs owner approval.

## 1. Indicators

| Code | Name | Provincial | Regional |
|---|---|---|---|
| FMA | Food Market Accessibility and Affordability | yes | yes |
| AFP | Agricultural and Fisheries Production | yes | yes |
| CEC | Climate and Environmental Conditions | yes | yes |
| EHS | Employment and Household Economic Stability | yes | yes |
| PSV | Household Poverty and Social Vulnerability | yes | no (no regional series) |
| FIS | Food Insecurity Early-Warning Signals | yes | yes |

## 2. Scored features (34; exactly the E120 list)

Each feature has a code, indicator, component, scope (P = provincial, R = regional), series, series unit (none for P), direction, transform, normalization and E119-R2 dataset id.

### FMA

| Feature | Scope | Series | Component | Direction | Dataset |
|---|---|---|---|---|---|
| FMA_food_cpi | P | cpi_food_yoy_pct | food inflation | + | D01 |
| FMA_headline_cpi | P | cpi_headline_yoy_pct | cost of living | + | D02 |
| FMA_rice_wholesale | P | rice_wholesale_yoy_pct | rice price | + | D05 |
| FMA_chicken | P | retail_chicken_yoy_pct | protein prices | + | D08 |
| FMA_pork | P | retail_pork_yoy_pct | protein prices | + | D09 |
| FMA_tilapia | P | retail_tilapia_yoy_pct | protein prices | + | D10 |
| FMA_food_cpi_R | R | region_cpi_food_yoy_pct @ Region IV-A | food inflation | + | D03 |
| FMA_headline_cpi_R | R | region_cpi_headline_yoy_pct @ Region IV-A | cost of living | + | D03 |
| FMA_rice_R | R | farmgate_palay_yoy_pct @ Region IV-A | rice price | + | D07 |

### AFP

All production features have direction − (a fall in production raises risk).

| Feature | Scope | Series | Component | Dataset |
|---|---|---|---|---|
| AFP_palay | P | palay_production_yoy_pct | cereals | D20 |
| AFP_corn | P | corn_production_yoy_pct | cereals | D21 |
| AFP_vegetables | P | vegetables_only_production_yoy_pct | vegetables | D22 |
| AFP_rootcrops | P | rootcrops_only_production_yoy_pct | root crops | D23 |
| AFP_fisheries | P | fisheries_production_yoy_pct | fisheries | D24 |
| AFP_chicken | P | chicken_production_yoy_pct | poultry and livestock | D26 |
| AFP_livestock | P | livestock_production_yoy_pct | poultry and livestock | D27 |
| AFP_palay_R, AFP_corn_R, AFP_vegetables_R, AFP_rootcrops_R, AFP_fisheries_R | R | the same series @ Region IV-A | the same components | the same datasets |

### CEC

| Feature | Scope | Series | Component | Direction | Transform | Dataset |
|---|---|---|---|---|---|---|
| CEC_rain_departure | P | rainfall_anomaly_mm | rainfall | + | absolute value | D36 |
| CEC_heat | P | temperature_anomaly_c | temperature | + | — | D37 |
| CEC_cyclones_100km | P | typhoons_local_100km | cyclones | + | — | D33 |
| CEC_rain_departure_R | R | rainfall_anomaly_mm @ CALABARZON (mean of 5 province points) | rainfall | + | absolute value | D36 |
| CEC_heat_R | R | temperature_anomaly_c @ CALABARZON (mean of 5 province points) | temperature | + | — | D37 |
| CEC_cyclones_R | R | typhoons_PAR @ PHILIPPINES | cyclones | + | — | D34 |

### EHS

| Feature | Scope | Series | Component | Direction | Normalization | Dataset |
|---|---|---|---|---|---|---|
| EHS_unemployment_prov | P | provincial_unemployment_rate_pct_annual | employment | + | rank5 | D41 |
| EHS_underemployment_prov | P | provincial_underemployment_rate_pct_annual | employment | + | rank5 | D41 |
| EHS_unemployment_change_R | R | E1_unemployment_change_pp @ PHILIPPINES | employment | + | — | D40 |
| EHS_remittance_decline_R | R | E2_remittance_decline_pct @ PHILIPPINES | remittances | + | — | D42 |

### PSV

| Feature | Scope | Series | Component | Direction | Normalization | Dataset |
|---|---|---|---|---|---|---|
| PSV_poverty | P | poverty_incidence_popweighted_pct | poverty | + | rank5 | D50 |

### FIS

| Feature | Scope | Series | Component | Direction | Dataset |
|---|---|---|---|---|---|
| FIS_fssi | P | N1_fssi_v3 | local news | + | D60 |
| FIS_shortage_news_R | R | news_gdelt_shortage_share @ PHILIPPINES | national news | + | D62 |

**Defaults.** Normalization is the expanding percentile unless "rank5" is shown.

**Not scored.** Kept as profile, context or alternative with the E120 reasons, listed in `firi3.EXCLUDED`:
- bottom-30% CPI, retail rice, farmgate palay (provincial), vegetable and root-crop prices, farmgate hog;
- aquaculture;
- cyclones within 300 km, rainfall total, ENSO;
- unemployment level;
- GDELT agri-supply, jobs-income and assistance shares, article counts;
- subsistence incidence, FIES food share, density;
- **SWS hunger (the target);**
- the FIRI v2 A1 model output.

## 3. Level 1: feature value and score

1. **Origin and issue.** Origin quarter t runs from 2021-Q1. Issue O(t) = the first day of quarter t+1.
2. **Inputs.** Observations are (feature, unit, period, value, availability date, status, source). Rules:
   - Rows with a period before 2021-Q1 are **rejected** and counted.
   - Inputs whose series is SWS, hunger, H1 or FIRI are **refused**: the run stops.
3. **Dynamic feature, as of O(t).**
   - Take the unit's latest period with availability date < O(t).
   - If t − period > 3, the status is `stale` and the feature is not scored.
   - Aligned value x = direction × (|v| if transform = abs else v).
   - *Prior* = the aligned values of all scope units' observations available before O(t) with a period earlier than the current period.
   - If fewer than 8, the status is `insufficient_history`. Otherwise score = (#prior < x + 0.5·#prior = x) / #prior.
4. **rank5 feature, as of O(t).**
   - Take the latest reference year with availability date < O(t). That year must have all five provinces, else `incomplete_year`.
   - Score = (average rank of the aligned value − 0.5) / 5.
   - With no published year, the status is `unavailable_at_issue`.
5. **Availability dates for annual inputs:**
   - provincial unemployment and underemployment of year Y: Y+1-06-30 (rule);
   - poverty (SAE 2021): 2025-07-01 (the V1 rule);
   - annual values are never expanded into quarters.
6. **Missing values** are never 0 and never filled.

## 4. Level 2: components and indicators

- Component score = the mean of the scored features in the component.
- Indicator score = the mean of the scored components.
- An indicator is available only if its scored components are at least ⌈(components defined for that indicator and scope) / 2⌉.

## 5. Level 3: FIRI3

**Formula.** FIRI3 = the equal-weighted mean of the available indicator scores.

**Completeness.** It is computed only if at least ⌈2/3 × the indicators defined for the scope⌉ are available:
- provincial: 4 of 6;
- regional: 4 of 5.

Otherwise the status is `not_computable`.

**Scope.** The provincial FIRI3 uses provincial features only. The regional FIRI3 uses regional features only.

**Meaning.** 0.5 = the usual level. The score is relative, not a probability.

**Band.** With k available indicators, SD_k = √(1/12) / √k:

| Band | Rule |
|---|---|
| usual or below | FIRI3 < 0.5 |
| above usual | < 0.5 + SD_k |
| elevated | < 0.5 + 1.645·SD_k |
| high | otherwise |

**Reported with every score:**
- the indicators available and the indicators missing;
- the contributing features;
- the verification share: the share of contributing features with status `verified`;
- the leave-one-indicator-out range: the minimum and maximum mean after dropping each available indicator in turn (k ≥ 2).

## 6. Prospective snapshots

- Each origin's results are written once to `snapshots/<origin>/` with a SHA-256 manifest. An existing snapshot is never overwritten: the run stops if its content would differ.
- Snapshots for origins whose issue date passed before E121 are labelled `retrospective` (computed with the as-of rules from data available now).
- Later origins are labelled `prospective`.
- The served FIRI v2 value for the same origin and province is stored beside each snapshot, for comparison.
- SWS may be compared with the regional FIRI3 **descriptively** after its release. It is never used to change weights, rules or past snapshots.

## 7. Changes

Any change to sections 1–6 needs owner approval and a new protocol version. Defects found during implementation are recorded in `E121_DESIGN_ISSUES.md` and left unchanged until approved.

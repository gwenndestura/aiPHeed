# aiPHeed methodology decision record: target, geography and validation (2026-11-03)

This record settles what aiPHeed can measure, forecast and validate. It is based on the FI6, FI7 and FI8 evidence,
the repository's earlier data audits (E118, E129, E130) and PSA tables fetched on 2026-11-03. No new forecasting
experiment was run. References are in [RESEARCH_REVIEW.md](RESEARCH_REVIEW.md); every indicator's role is in
[DATA_DICTIONARY.csv](DATA_DICTIONARY.csv); coverage is in [DATA_AVAILABILITY_MATRIX.csv](DATA_AVAILABILITY_MATRIX.csv).

## 1. Geographic compatibility of SWS Balance Luzon and CALABARZON

| Fact | Evidence |
|---|---|
| What Balance Luzon is | SWS reports it as "Luzon outside Metro Manila". By PSA region that is CAR, I, II, III, IV-A, MIMAROPA and V |
| CALABARZON's weight | 17.0 M of 50.5 M people, **33.7 %**. Derived from PSA 2023 official poverty statistics as magnitude of the poor ÷ poverty incidence (`backend/data/fi5/raw/psa/psa_poor_population_magnitude_2018_2023.csv`, `psa_poverty_incidence_all_regions_2018_2023.csv`) |
| Sample | Balance Luzon samples of 300 / 600 / 1,080 adults per round in 2021–26. SWS publishes area margins only: ±6 / ±4 / ±3 points |
| Weighting | SWS weights the four area estimates to PSA population projections to form the national figure. It does not publish within-area (regional or provincial) allocation, counts, design effects or estimates |
| Microdata | Not public. Not obtained in this work |
| Comparability over time | Sample size varies by round. The respondent base changed in 2025 (household heads → adults). Rounds with ~600 Balance Luzon respondents read +3.6 points higher than their neighbours (p = 0.05; FI8). SWS states that its methodology is consistent; no survey-vehicle documentation was found |

**Implication.**
* If CALABARZON were allocated in proportion to its population, a round would contain roughly 100–360 CALABARZON
  respondents. A CALABARZON-only estimate would then carry roughly ±5–10 points of error. In any case SWS does not
  produce one, and nothing in the public data allows it to be computed.
* Two thirds of the Balance Luzon outcome comes from outside CALABARZON. Its movements can be driven by Central Luzon
  or Bicol while CALABARZON is unchanged.
* Training a model on CALABARZON-only predictors against that outcome, then presenting the result as CALABARZON or
  provincial hunger, is an ecological-inference error (Robinson, 1950). It assigns an aggregate's behaviour to a
  sub-unit it does not represent.

**Decision on the role of SWS Balance Luzon.**

| Possible role | Decision |
|---|---|
| 1. Direct training target for CALABARZON or its provinces | **Prohibited** |
| 2. Regional contextual indicator for CALABARZON | **Allowed**, labelled "Balance Luzon (includes CALABARZON, ~34 % of its population)" |
| 3. External regional validation benchmark for CALABARZON forecasts | **Not allowed** as a direct check, because of the geographic mismatch. It can be shown alongside as context |
| 4. Outcome of a separate Balance Luzon model | **Allowed**. This is what FI6/FI7/FI8 actually are: forecasts of Balance Luzon hunger, validated on Balance Luzon |
| 5. Primary target of a CALABARZON food-insecurity system | **Removed**. There is no valid quarterly CALABARZON or provincial outcome |

## 2. Comparison of food-related measures

| Measure | What it measures | Level | Frequency | History held | Role in aiPHeed |
|---|---|---|---|---|---|
| SWS involuntary hunger | % of families that experienced hunger with nothing to eat, past 3 months (severe-end experience) | 4 SWS areas incl. Balance Luzon | about quarterly | 1998-Q3–2026-Q3 | direct outcome **for Balance Luzon only** |
| FIES (FAO scale; DOST-FNRI ENNS/NNS) | experience-based moderate/severe food insecurity, 12-month reference (Cafiero et al., 2018) | national and regional; provincial only in some rounds (ENNS 2018–19 pooled, selected provinces; ENNS 2021: Batangas, Cavite, Lucena; NNS 2023 regional), per the repository record E118 | irregular | ≤ 3 points per province | **external validation benchmark**, periodic, cross-sectional only |
| PSA APIS hunger item | families that experienced hunger with nothing to eat, past 3 months | region (design-based) | about annual, non-FIES years | microdata on request (latest held by PSA: 2022) | potential **direct regional outcome** (CALABARZON); not held |
| PSA food threshold | minimum annual per-capita income to meet basic food needs, in pesos (cost of the food basket) | region, province | triennial official (2018/2021/2023; earlier 2006–2015 on the old method) | 2006–2023 | **affordability reference** (cost side) |
| PSA subsistence incidence | % of population whose income is below the food threshold (income-based food poverty) | region, province | triennial | 2006–2023 (break 2015→2018) | **structural vulnerability / affordability indicator**. Not experienced food insecurity |
| PSA poverty incidence | % below the poverty threshold (food + non-food) | region, province; city/municipal SAE 2021 | triennial; SAE irregular | 2006–2025 | **structural vulnerability** |
| PSA food CPI (food and non-alcoholic beverages) / food inflation | price level / YoY change of the food basket | region (provincial CPI exists from 2018) | monthly | 1994–2026-09 (regional) | **predictor / affordability pressure**. Rising prices are not food insecurity unless incomes lag |

**Update (2026-11-03, docs/fi_labels/ASSESSMENT.md):** the official values are now held.
* FIES-based moderate-or-severe household food insecurity, CALABARZON 2023: 19.1 % (95 % CI 17.0–21.1); national
  44.2 % (2019), 33.4 % (2021) and 31.4 % (2023), from PSA SDG 2.1.2.
* HFIAS 2015 for CALABARZON and all five provinces, with SE/CI (FNRI 2015 report).
* These are survey-date benchmarks on two different instruments. They are not a quarterly series.

**No official "PSA food-deprivation CPI" exists.** The term is not used.

**Defensible affordability indicator (design, not yet implemented).** The latest provincial food threshold, carried
forward with provincial food CPI to the issue month, compared with income-side indicators (poverty and subsistence
incidence, employment, remittances). This would be an affordability-pressure predictor. It must never be used as, or
validated against, a target built from the same inputs.

## 3. Target and validation architecture (decision)

| Option | Requirement | Available? | Decision |
|---|---|---|---|
| A. Provincial prevalence forecasting | repeated provincial outcomes, or a validated small-area-estimation model (household outcome microdata + census auxiliaries + shared variables + validation; Elbers et al., 2003; Molina & Rao, 2010; Fay & Herriot, 1979) | No. There are no household food-insecurity microdata with provincial identifiers in hand, and ≤ 3 FIES points per province | **Rejected** until FNRI/PSA microdata are obtained |
| B. Provincial risk indicators, labelled as risk (not prevalence), with periodic FIES benchmarks | provincial predictors with release dates (held); FIES benchmarks (published tables; few) | Yes for indicators. Benchmarks are cross-sectional and few | **Adopted for the provincial layer**, with no accuracy claim (there is no quarterly provincial outcome to measure accuracy against) |
| C. Hierarchical regional → provincial model | a regional outcome *of the same area* (CALABARZON) plus a model linking provincial predictors to it, with propagated uncertainty | No. The only quarterly outcome is Balance Luzon, which is not CALABARZON. Provincial splits would be fixed by the predictors themselves (circular) | **Rejected** now. Becomes feasible if the APIS CALABARZON series is obtained |

**Adopted architecture (two separated layers):**
1. **Balance Luzon hunger outlook (outcome-validated).**
   * This is FI6/FI7/FI8, unchanged: the target, walk-forward validation and baselines.
   * Its claims hold for Balance Luzon only.
   * Robustly, there is no reliable lead. The next-quarter outlook is provisional (FI8).
2. **CALABARZON province and LGU layer (risk and vulnerability, not validated as prevalence).**
   * Province figures: indicator-based risk and vulnerability, per domain.
   * LGU figures: vulnerability-adjusted priority (poverty × density ranks).
   * The Balance Luzon outlook may be shown as regional context, but never as a province value.

**Circular validation is prohibited.**
* Predictors (CPI, poverty, unemployment, news) are never used to build an outcome that then "validates" them.
* FIES and APIS are used only as outcomes or benchmarks, never as predictors.

## 4. Decision on the FI7/FI8 target construction

* **Decision: retain, restricted.** The FI6 target ("Balance Luzon hunger significantly above its five-year
  normal") is a valid experience-based food-insecurity target **for Balance Luzon**.
* **What is withdrawn:**
  * every wording that says or implies it measures CALABARZON or its provinces;
  * the wording "Balance Luzon covers all five provinces" as a justification for provincial use.
* **The LGU multiplier:** the regional probability in the LGU priority score stays only as a common scale factor,
  identical for every LGU. It carries no provincial information, and the documentation now says so.

## 5. What the FI8 upper bound does and does not rule out

**Rules out:** linear corrections of damped persistence, built from the 23 held government and news indicators,
improving the probability (Brier) of the Balance Luzon above-normal classification on the 62 next-quarter targets.
That holds even when the inputs are chosen by looking at the test quarters.

**Does not rule out:**
1. value for a *more precise or geographically matched outcome* (APIS CALABARZON, FIES), because the Balance Luzon
   noise and mismatch dilute any CALABARZON signal;
2. value for the continuous hunger level, or for later quarters as more data arrive;
3. non-linear effects beyond the FI7 LightGBM;
4. provincial differentiation, which no outcome can currently test.

## 6. Highest-value data acquisitions (they resolve the measurement problem; nothing else does)

| Rank | Source | What it would contribute | Level | Coverage | Access |
|---|---|---|---|---|---|
| 1 | **PSA APIS** hunger / food-insecurity items (microdata via the PSA Data Archive) | a direct, design-based **CALABARZON** outcome, about annual. It enables option C and regional validation | region (province only if the sample design supports it) | years of APIS rounds (non-FIES years) | formal request (PSA Data Archive / eFOI) |
| 2 | **DOST-FNRI ENNS/NNS FIES** household microdata with geographic identifiers | provincial FIES benchmarks and small-area estimation (option A) together with CPH 2020 auxiliaries | household → province | 2018–19, 2021, 2023 rounds | formal data request to FNRI |
| 3 | **SWS** round design notes / Balance Luzon microdata (SWS Data Archive) | test and correct the sample-size effect; estimate CALABARZON within Balance Luzon if the regional allocation is recorded | household → region | 2005+ | request / fee |
| 4 | PSA provincial food threshold and subsistence incidence, all rounds | affordability reference and vulnerability (already held for 2006–2023) | province | triennial | public (held) |

Broad requests for other datasets would not fix the outcome or the geographic mismatch, so none were made.

## 7. Implementation impact (what was corrected)

| Output | Problem | Correction |
|---|---|---|
| `/api/v1/fi7/forecast` (`backend/data/fi7/out/forecast.json`) | no explicit geographic scope | adds `geographic_scope` and `measurement_type` fields; the text names Balance Luzon (~34 % CALABARZON) |
| `backend/data/fi7/out/province_priority.csv`, `lgu_rankings.csv` (basis/status text) | "covers all 5 provinces" implied provincial relevance | replaced: the Balance Luzon outlook is a common regional scale factor; the province and LGU order comes from vulnerability; neither is a hunger measurement |
| `/api/v1/fi5`, `/fi6`, `/fi7` status strings | already say Balance Luzon and priority-not-measurement | fi7 string sharpened to name the ~34 % share and forbid provincial-accuracy readings |
| Approved dashboard (P0H4 price-pressure index, `app/ml/inference/ch1_system.py`) | already labelled "not a food-insecurity measurement" (`is_food_insecurity_measurement: False`) | **not changed**: changes to what DA sees need owner approval. The recommendation is that any "food insecurity" wording on the map be read as risk/price pressure, as the backend `indicator()` text already states |

## 8. Dashboard: what may be shown

| Category | May show | Source |
|---|---|---|
| Measured food-insecurity prevalence | only SWS Balance Luzon (regional, labelled), and FIES rounds where published | SWS releases; FNRI |
| Forecast food-insecurity risk | Balance Luzon next-quarter outlook, **provisional** | FI7/FI8 |
| Food affordability pressure | food CPI vs food threshold and income indicators, per province | PSA |
| Structural vulnerability | poverty, subsistence incidence, density | PSA |
| Uncertainty | label-flip probabilities, margins of error, the "provisional / indicative" status | FI6–FI8 |
| LGU priority (142) | vulnerability-adjusted ranking, "not measured municipal hunger" | FI5/FI7 |

# Objective 3: implementation audit and outcome-validation protocol (2026-11-04)

## 1. Implementation audit

**Script:** `runner/obj3_lgu_recompute.py`.
- Calls the served API in-process (default C-B6 export, 2027-Q1) against a temporary database.
- Recomputes every index independently with pandas.
- No model is run and no data file is changed.

| Check | Result |
|---|---|
| LGUs returned by the API | 142: Quezon 41, Batangas 34, Laguna 30, Cavite 23, Rizal 14 |
| Matched to the input table (`backend/data/foodinsecurity_engine_cb6/lgu_vulnerability.csv`) | 142 / 142 |
| Missing poverty, population or land area | 0 |
| Province weight = PSA 2023 family poverty / max (Quezon 6.9%) | max \|Δ\| 4.1e-7 (6-dp storage) |
| Province score = regional probability × weight | max \|Δ\| 1.0e-6 (6-dp storage) |
| LGU index = province score × (0.6 poverty_norm + 0.4 density_norm), min-max within province, clamp [0,1], 4 dp | **141 / 142 exact**. **Cardona (Rizal):** formula 0.4963, served 0.49. This is the intended display rule (`app/services/dashboard.py:_shown`): a value in [0.495, 0.5) is truncated so it never prints as "0.50" (HIGH); the exact value is kept internally. **Not a defect** |
| Within-province ranks follow the index | Yes |
| LGU colour | The province's class (all HIGH for 2027-Q1), as designed; the index orders LGUs, it does not classify them |
| Poverty precision | 25 LGUs have PSA SAE CV > 20% (low precision; flagged in the API provenance) |
| Lucena (HUC) | PSA Table 2a value (its own estimate), as documented |

- **No implementation defect found.**
- **Documentation note:** "LGU index = province score × vulnerability" is what is served. The province score already
  includes the poverty weight, so poverty enters at two levels (province weight and within-province norm). This is the
  approved method, stated in `lgu_audit.py`.

## 2. What these numbers are and are not

- **They are:** **vulnerability-weighted rankings** derived from a forecast (regional C-B6 served; the provincial
  C-B6D-E-X is not served) and PSA poverty (2021 SAE, 2023 provincial) and density (2024 population).
- **They are not:** observed or forecast food insecurity for any LGU. No LGU-level food-insecurity outcome exists.
- **Province check against Eq. 3 outcomes (2021–26, 5 provinces):** Spearman ρ −0.30 (p 0.62). Quezon has the highest
  weight but the fewest HIGH quarters. This is **not** validation; n = 5.

## 3. Missing outcome data (exact)

| Level | Needed | Possible source | Status |
|---|---|---|---|
| Province | A food-insecurity prevalence per province, ideally yearly | DOST-FNRI ENNS/NNS provincial FIES (2021: Batangas 29.7%, Cavite 31.7% only); PSA FIES provincial estimates if released | 2 of 5 provinces, one year |
| LGU | Any municipal or city food-insecurity measure | FNRI municipal estimates (none published); DSWD Listahanan or 4Ps food-poverty indicators (request); LGU nutrition reports (OPT Plus, NNC) | **None in hand** |
| Evaluator judgement (thesis H4) | DA Region IV-A evaluators' province ranks and LGU picks | Post-Survey Part F (`OBJ5_ISO25010_INSTRUMENT.md`) | **Prepared; 0 responses** |

## 4. Validation protocol (fixed now, to apply when the data exist)

1. **H4 (thesis), evaluator consistency:** per `OBJ5_ANALYSIS_PLAN.md` §5 (PLAN-SHA256 851ea697…, verified intact).
   - Spearman ρ between each evaluator's province ranking and aiPHeed's province ranking at the survey quarter.
   - Overlap between the evaluator's top-10 LGUs and aiPHeed's top-10, against the hypergeometric chance level.
2. **Province outcomes (when at least 3 provinces have FIES for the same year):** Spearman ρ between the province score
   at the quarter nearest the survey and the FIES prevalence; report n, ρ and the CIs of both sources.
3. **LGU outcomes (if a municipal measure is obtained):**
   - within each province, Spearman ρ between the LGU index and the measure;
   - pooled across provinces with a province-stratified permutation test (10,000 permutations, seed 2036);
   - report LGUs with PSA CV > 20% separately.
4. **Rule:** no ranking may be called "validated" unless 2 or 3 is significant at α = 0.05. H4 alone supports
   "consistent with evaluator judgement" only.

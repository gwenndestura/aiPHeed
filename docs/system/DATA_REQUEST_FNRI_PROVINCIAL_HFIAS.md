# Data needed to validate aiPHeed's provincial forecasts (draft; NOT sent; owner rule: no requests)

**Why these data are needed.**
* aiPHeed's provincial models were tested on every public provincial HFIAS round: 2013, 2015, 2018/2019.
* Their sealed predictions (E138–E142, `backend/data/registry/prospective_provincial.jsonl`) can be confirmed or
  rejected only against a provincial round **after 2019** that no model has seen.

**Holder.** DOST Food and Nutrition Research Institute (FNRI), Nutrition Assessment and Monitoring Division / ENNS
data release. Public channel: eNutrition (`enutrition.fnri.dost.gov.ph`), which is unreachable from this network.

## 1. Requested tables

**Priority 1: 2021 ENNS, provincial household food security (HFIAS).** These are the provinces in the 2021 rolling
replicate, the third replicate after 2018 and 2019. The 2018 monographs state that provinces were assigned to the
years 2018, 2019 and 2021.

| Field | Description |
|---|---|
| province | name, or PSGC code |
| survey year and fieldwork dates | first and last interview date, per province if available |
| n | respondent households |
| food_secure_pct, mild_pct, moderate_pct, severe_pct | HFIAS categories, Coates et al. 2007 scoring as in 2018/2019 |
| SE or 90 %/95 % CI | for each category, and for moderate-or-severe if available |
| national value of the same round | the same four categories, with SE |

**Priority 2: 2023 NNS (or later) with provincial HFIAS,** if provincial estimates exist. The public 2023 files are
regional.

**Priority 3: 2013 NNS design-based standard errors** for Appendix 33 (food security by province). E141 currently
approximates them with the 2015 design effect (3.17).

**Priority 4: ENNS 2018 and 2019 fieldwork months per province.** The monographs do not print them; E137–E142 assume
Q3.

## 2. What happens when the data arrive

1. Save as CSV in the format of `backend/data/registry/provincial_round_TEMPLATE.csv` (province, survey, year, p,
   se_p, ref, instrument).
2. Run `python -m app.registry.prospective_provincial score <file>`.
   * It scores every sealed model against the national base rate, persistence and the region's previous level on the
     same rows.
   * HFIAS rows count as confirmation. FIES rows count as agreement only.
3. **Confirmation rule, stated before the data exist:** on at least 20 provinces, the candidate's expected Brier
   score must be below persistence and below the region's previous level, with the 95 % cluster-bootstrap CI
   excluding 0, and AUC ≥ 0.75.

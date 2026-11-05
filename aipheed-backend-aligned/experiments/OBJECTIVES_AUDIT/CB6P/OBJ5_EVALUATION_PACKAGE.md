# Objective 5: evaluation package (prepared 2026-11-04; awaiting participants)

**Nothing here is a response, a rating or an approval.**

## 1. Materials (existing, verified)

| Item | File | Status |
|---|---|---|
| Questionnaire (ISO/IEC 25010, Parts A–G incl. consent RA 10173 and the H4 ranking task) | `../OBJ5_ISO25010_INSTRUMENT.md` | Draft for adviser review |
| Scoring and analysis plan (H4, H5) | `../OBJ5_ANALYSIS_PLAN.md` | Hashed, PLAN-SHA256 851ea697… (**verified intact 2026-11-04**) |
| Developer system tests | `../OBJ5_SYSTEM_TEST_CHECKLIST.md` | See §4 |
| FNRI face validity | `../OBJ5_FNRI_FACE_VALIDITY.md` | Adviser decision pending (§5) |

## 2. Participant instructions (to read aloud or paste into the form header)

1. You are evaluating aiPHeed, a research prototype that forecasts **food-insecurity risk** for CALABARZON. It is not an
   official DA classification.
2. Participation is voluntary and confidential (RA 10173). You may stop at any time. It takes about 20 minutes.
3. **Before opening aiPHeed:** answer Part F item 23, ranking the five provinces from your own knowledge.
4. Open the dashboard link given by the team. Use the map, a province panel, an LGU list and the report download.
5. Answer every statement from 1 (Strongly disagree) to 5 (Strongly agree), or "Not applicable" if you did not use that
   function.
6. Do not discuss your answers with other participants until the survey closes.

## 3. Administration protocol

**Pre-conditions (all required before the first response):**
- the adviser approves the instrument and the served model;
- the dashboard serves that model with real forecasts;
- the deployment is authorised.

**Respondents:**
- 50 DA Region IV-A personnel (purposive) for functional suitability and accuracy (thesis RQ5);
- **plus DEPDev Region IV-A personnel as usability evaluators** (thesis RQ5 names them).

> **Gap found:** the current instrument and analysis plan cover DA personnel only.
>
> **Proposal (needs adviser sign-off, and an analysis-plan addendum hashed before collection):**
> - DEPDev respondents complete Parts A, D (usability) and G;
> - their Part D is scored and reported as a separate group;
> - the hashed analysis plan is not edited.

**Collection:** one Google Form per group, with a timestamp and a responder ID (no names in the analysis file).
**Export:** CSV to `OBJECTIVES_AUDIT/obj5_responses/` (raw file kept read-only).

**Scoring:** exactly per `OBJ5_ANALYSIS_PLAN.md`:
- include a response only with consent and at least 80% of Likert items answered;
- per-characteristic mean, median and the share answering 4–5, with 95% bootstrap CIs;
- H5 and H4 decision rules as fixed there.

## 4. System verification (2026-11-04)

- `pytest tests/integration/test_foodinsecurity_mode.py tests/unit/test_cb6_auto.py tests/integration/test_cb6_auto_api.py
  tests/unit/test_cb6_auto_job.py` → **56 passed** (the 34 reported earlier plus the 22 auto-update job tests).
- **Alerts:** HIGH forecasts are staged as candidates that need human confirmation; nothing is sent automatically
  (Rule 7).
- **Note for evaluators:** the served model is C-B6 (regional; class identical for all provinces). The provincial
  C-B6D-E-X is development evidence and is not served.

## 5. DOST-FNRI face validation: what is needed

| Requirement | Status |
|---|---|
| NNS 2023 CALABARZON moderate/severe FIES 19.1% | Verified (`../OBJ5_FNRI_FACE_VALIDITY.md` §1) |
| NNS 2019 CALABARZON figure (named in Objective 5) | **Does not exist** (ENNS 2018–19 covered 2 provinces; FIES national only) |
| 2021 provincial FIES (Batangas 29.7%, Cavite 31.7%) | Verified; 2 provinces only |
| **Adviser:** approve the corrected wording (2021 provincial + 2023 regional + direction checks) | **Pending** |
| **When the 2025/2026 NNS is released:** compare its CALABARZON FIES direction with the sealed forecasts | Waiting for FNRI |

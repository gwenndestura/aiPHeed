# aiPHeed Post-Survey Questionnaire (ISO/IEC 25010)

**Who answers:** the 50 DA Region IV-A evaluators, after a guided session with the development dashboard.
**Format:** one Google Form.
**Scale for every rated item:** 5-point Likert.

| Rating | Meaning |
|---|---|
| 1 | Strongly disagree |
| 2 | Disagree |
| 3 | Neither agree nor disagree |
| 4 | Agree |
| 5 | Strongly agree |

The item codes below must be kept as the Google Form question titles' prefixes (for example, "FS1 – …"), so that `score_responses.py` can read the export.

## Part A. Respondent profile (closed-ended; not scored)

| Code | Question | Answer options |
|---|---|---|
| P1 | Office or unit within DA Region IV-A | free text |
| P2 | Years of work related to agriculture, food security or planning | <1 / 1–3 / 4–6 / 7–10 / >10 |
| P3 | How often do you use maps or dashboards in your work? | Never / Rarely / Monthly / Weekly / Daily |
| P4 | Provinces you are most familiar with | multi-select: Cavite, Laguna, Batangas, Rizal, Quezon |

## Part B. Functional suitability (ISO/IEC 25010)

| Code | Item |
|---|---|
| FS1 | The dashboard provides the functions I need to review quarterly food insecurity risk for CALABARZON (functional completeness). |
| FS2 | The forecast map, rankings, alerts and PDF report show the same quarter and the same values (functional correctness). |
| FS3 | The system clearly states when it does not have enough data to produce a forecast (functional correctness). |
| FS4 | The system's outputs are appropriate for anticipatory planning at DA Region IV-A (functional appropriateness). |
| FS5 | The explanation of the factors behind each forecast (SHAP drivers) helps me understand the result (functional appropriateness). |

## Part C. Accuracy (as perceived; the model's measured accuracy is reported separately in Chapter IV)

| Code | Item |
|---|---|
| AC1 | The province-level risk levels are consistent with my knowledge of conditions in CALABARZON. |
| AC2 | The forecast target quarter, supporting-news period and information cutoff are clearly stated and correct. |
| AC3 | The data-sufficiency warnings (LIMITED_SIGNAL, insufficient data) are shown where they should be. |
| AC4 | The reported evaluation results (accuracy, precision, recall, F1, ROC-AUC) are presented honestly and understandably. |

## Part D. Usability (ISO/IEC 25010)

| Code | Item |
|---|---|
| US1 | I can recognize what the dashboard is for when I first open it (appropriateness recognizability). |
| US2 | I learned to use the dashboard quickly (learnability). |
| US3 | It is easy to find a province's or a city/municipality's risk and its explanation (operability). |
| US4 | Downloading and reading the PDF report is straightforward (operability). |
| US5 | The interface is visually clear and pleasant to use (user interface aesthetics). |
| US6 | Text, colours and labels are readable for me (accessibility). |

## Part E. Municipal and city ranking consistency (Hypothesis 4)

The facilitator shows the ranking table for the evaluator's most familiar province (P4).

| Code | Item | Answer |
|---|---|---|
| RK1 | The order of cities and municipalities in this province matches my assessment of their relative food insecurity vulnerability. | Likert 1–5 |
| RK2 | Name the THREE cities/municipalities in this province you consider MOST vulnerable to food insecurity, most vulnerable first. Answer before viewing the ranking. | three LGU names (dropdown of the province's LGUs) |
| RK3 | Name the THREE you consider LEAST vulnerable. Answer before viewing the ranking. | three LGU names |
| RK4 | Which cities/municipalities, if any, look misplaced in the ranking, and why? | open-ended |

**Order matters.** RK2 and RK3 are asked **before** the ranking is shown (Form section break), so the evaluator's own assessment is independent of the system's.

## Part F. Open-ended (not scored)

| Code | Question |
|---|---|
| OE1 | What would make aiPHeed more useful for DA Region IV-A? |
| OE2 | Did anything in the dashboard or the report confuse you? |

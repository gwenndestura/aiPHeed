# aiPHeed post-testing questionnaire: DA Region IV-A evaluators (ISO/IEC 25010)

**Source.** Retargeted from `frontend/meeting-materials/aiPHeed_PostTesting_Questionnaire_Draft.docx`.

**Changes.** The draft named DOST Region IV-A and planned "~30 DOST + 20 general public". Chapter I specifies **50 DA
Region IV-A evaluators**, so:
- the respondent group, Section 1 options and Section 5 are rewritten for DA;
- items 1–15 keep their wording and numbering, so `E97_Validation_Completion/iso25010/item_map.json` and
  `score_iso25010.py` apply unchanged.

**Administer only on the model-integrated dashboard,** never on mock data. Record the dashboard version shown to
respondents: the git commit and `/api/v1/config` → `servingModel`.

## Informed consent

[Keep the consent text and the "Sgd. Full Name" digital-signature rule from the draft. Insert the student contact
e-mails before sending.]

## Section 1: Respondent profile

- Agency: DA Regional Field Office IV-A (required for inclusion in the Chapter I sample).
- Division or unit: ☐ Field Operations ☐ Planning, Monitoring and Evaluation ☐ Regional Agricultural and Fishery
  Information Section / ICT ☐ Research ☐ Other: ____
- Years in current role: ☐ < 1 ☐ 1–3 ☐ 4–10 ☐ 10+
- Familiarity with food-security data before today: ☐ None ☐ Basic ☐ Working knowledge ☐ Expert

## Sections 2–4: rating items

Scale: 1 = Strongly Disagree, 2 = Disagree, 3 = Neutral, 4 = Agree, 5 = Strongly Agree.

| # | Statement | Characteristic (scoring) |
|---|---|---|
| 1 | The province-level risk classifications (HIGH/LOW) shown by aiPHeed appear consistent with known conditions in CALABARZON. | Accuracy |
| 2 | The municipal/city risk rankings reflect realistic relative vulnerability across LGUs. | Accuracy |
| 3 | The SHAP-based explanations helped me understand why a forecast was classified as high or low risk. | Accuracy |
| 4 | The forecast lead time (how far ahead aiPHeed predicts) is useful for planning purposes. | Accuracy |
| 5 | The early-warning alerts would provide meaningful lead time for an actual intervention. | Accuracy |
| 6 | The dashboard provides all the functions needed to review food-insecurity risk (map, rankings, alerts, explanations, PDF export). | Functional suitability: completeness |
| 7 | The system performs its forecasting and reporting functions correctly, without visible errors. | Functional suitability: correctness |
| 8 | The admin/evaluator review workflow (PENDING → STAGED → PUBLISHED) is appropriate for ensuring human oversight before publication. | Functional suitability: appropriateness |
| 9 | The data-sufficiency flags (e.g., LIMITED_SIGNAL) gave me useful context about forecast confidence. | Functional suitability: appropriateness |
| 10 | I could quickly tell what the system is for and how it could help my work. | Usability: appropriateness recognizability |
| 11 | I could learn to use the dashboard's main features without much difficulty. | Usability: learnability |
| 12 | Navigating the map, time slider, and rankings table felt straightforward. | Usability: operability |
| 13 | The system helped prevent or clearly flagged potential mistakes. | Usability: user error protection |
| 14 | The dashboard's layout and visuals were clear and professional. | Usability: user interface aesthetics |
| 15 | The interface was usable regardless of my technical background. | Usability: accessibility |

## Section 5: Alignment with DA Region IV-A operations (reported separately, not scored)

16. aiPHeed's outputs could realistically support DA Region IV-A's food-security planning and intervention targeting.
17. The forecasts and alerts could be usefully shared with LGU agriculture and social welfare offices.
18. The explanations would be sufficient for technical review before a forecast is published.
19. Relying on public data only makes aiPHeed easier to adopt operationally.

## Section 6: Open-ended

[As in the draft, with "DOST Region IV-A" replaced by "DA Region IV-A".]

## Scoring (fixed before collection)

1. Export the responses to CSV with the columns `respondent_id,agency,q1..q15`. Use the template
   `E97_Validation_Completion/iso25010/response_template.csv`. Leave a cell blank when the item was not answered.
2. Run `py -3.13 score_iso25010.py responses.csv results.json`.
3. Per characteristic the script reports:
   - the weighted mean, SD and interpretation band;
   - favourable when the mean is ≥ 3.41;
   - status COMPLETE at 50 respondents, PARTIAL below 50.
4. Report only what the script outputs. Respondents whose agency is not DA Region IV-A are excluded from the Chapter I
   sample and reported separately.

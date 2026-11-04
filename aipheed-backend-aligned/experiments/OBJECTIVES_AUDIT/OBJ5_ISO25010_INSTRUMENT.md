# aiPHeed Post-Survey Questionnaire (ISO/IEC 25010), draft for review

**Respondents:** 50 DA Region IV-A personnel, purposive sampling (thesis §1.7, §3.7, H4, H5). One Google Form. Scale for
every rated item: 1 Strongly disagree, 2 Disagree, 3 Neutral, 4 Agree, 5 Strongly agree, plus "Not applicable".

**Version note:** item groups follow ISO/IEC 25010:2011 names as in the thesis. ISO/IEC 25010:2023 renames usability
"interaction capability" and adds safety; the mapping is given in the analysis plan.

**Administer only after** the dashboard serves the thesis model (`OBJ5_FRONTEND_ALIGNMENT_PLAN.md`), with real
forecasts.

## Part A. Consent and profile
- Consent statement (RA 10173; voluntary; confidential; about 20 minutes); "Sgd. Full Name".
- Office/division; position; years in DA; role (technical, planning, field, ICT/GIS, admin); prior use of food-security
  dashboards (none / some / regular).

## Part B. Functional suitability (system evaluators)
1. The dashboard shows forecasts for all five CALABARZON provinces and their cities and municipalities. *(completeness)*
2. The forecast map, rankings and alerts show the same values as the downloadable report. *(correctness)*
3. The forecast quarter, issue date and lead time are clearly stated for every forecast. *(correctness)*
4. The system distinguishes the measured SWS hunger figure from forecast and vulnerability-weighted values. *(correctness)*
5. The functions provided (map, rankings, explanations, alerts, report) are appropriate for DA planning. *(appropriateness)*
6. The early-warning alerts identify situations that would warrant DA attention. *(appropriateness)*
7. The review workflow (staged forecasts approved or rejected by an administrator) is appropriate before publication.

## Part C. Forecast accuracy and relevance (thesis H5 "accuracy")
8. The regional HIGH/LOW forecasts are consistent with my knowledge of recent food-insecurity conditions.
9. The stated model performance (accuracy, AUC, reliable lead time) is clearly explained.
10. The explanations of what drives each forecast (SHAP) are understandable.
11. The limitations (regional survey data, development evidence only, news influence) are clearly disclosed.

## Part D. Usability
12. I could quickly tell what the system is for. *(appropriateness recognizability)*
13. I could learn to use the main features without help. *(learnability)*
14. Navigating the map, quarter selector and rankings was easy. *(operability)*
15. The system prevents or warns about mistakes (e.g. confirmation before approving a forecast). *(user error protection)*
16. The interface is clear and visually organized. *(UI aesthetics)*
17. Text, colors and labels are readable, including for users with visual limitations. *(accessibility)*

## Part E. Performance efficiency, compatibility, reliability, security
18. Pages and maps load within an acceptable time. *(time behaviour)*
19. The PDF/CSV outputs can be used with the tools my office uses. *(interoperability)*
20. The system was available and worked without errors during my evaluation. *(availability / maturity)*
21. Access to administrative functions is restricted to authorized users. *(confidentiality)*
22. Administrative actions (approve, reject, alert confirmation) are recorded with who did them. *(accountability)*

*Maintainability and portability* are not rated by evaluators; they are assessed by the developers' technical tests
(`OBJ5_SYSTEM_TEST_CHECKLIST.md`).

## Part F. H4: LGU and province ranking task (not Likert)
23. Rank the five provinces from most (1) to least (5) vulnerable to food insecurity, from your professional knowledge,
    **before** viewing aiPHeed's ranking.
24. From the list of the 142 cities/municipalities (searchable), select up to 10 you consider most vulnerable.
25. After viewing aiPHeed's LGU rankings: "The municipal and city rankings reflect relative food-insecurity
    vulnerability across CALABARZON." (Likert)

## Part G. Open-ended
26. What was most useful? 27. What was difficult? 28. What should change before DA use? 29. Would you recommend DA
Region IV-A use aiPHeed? Why?

## Changes from the earlier draft (`frontend/meeting-materials/aiPHeed_PostTesting_Questionnaire_Draft.docx`)
- Respondents changed from DOST staff and the general public (~30) to **50 DA Region IV-A personnel**.
- Added performance efficiency, compatibility, reliability and security items, a disclosure item and the **H4
  ranking task**.
- The title's "DOST Region IV-A" is corrected to DA.

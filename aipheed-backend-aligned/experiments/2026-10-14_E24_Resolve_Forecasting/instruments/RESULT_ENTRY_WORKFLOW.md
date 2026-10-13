# Result-entry workflow (DA Region IV-A evaluation, H4/H5)

1. **Build the Google Form.**
   - Use `QUESTIONNAIRE.md`. Each question title starts with its code (FS1, AC1, US1, RK1, RK2_1…, P4…), matching `RESPONSE_EXPORT_TEMPLATE.csv` (headers only, no rows).
   - Section breaks: RK2/RK3 come before the ranking is shown.
2. **Before the first session,** hash and record:
   - the Form link;
   - the dashboard build (`dashboard_dev/dist-e24`);
   - the forecast record (content SHA-256);
   - the ranking file (`LGU_RANKING_VALIDATION.csv`).

   Do not change them during the evaluation window.
3. **Collect responses.** Run the sessions with `CONSENT_AND_FACILITATOR_GUIDE.md`. Responses are entered **only by the evaluators, in the Form**. Researchers never type, edit, add or "clean" responses.
4. **Export.** Download the Form's CSV export unchanged. Record its SHA-256 and keep the original file read-only.
5. **Score:**

   ```
   python instruments/score_responses.py <export.csv> --rankings LGU_RANKING_VALIDATION.csv --out h4_h5_results.json
   ```

   The scorer:
   - **refuses** a file without Forms' `Timestamp` column;
   - excludes rows without consent or with fewer than 80% of rated items answered (reported, never imputed);
   - applies the predeclared rules in `DECISION_RULES.md`.
6. **Report.** Report the counts of valid and excluded responses, then the H4/H5 decisions exactly as the scorer outputs them.
7. **Until step 5 runs on a genuine export, H4 and H5 remain "awaiting participant data".**

# Informed consent and facilitator guide

## Part 1. Informed consent (first section of the Google Form)

> **aiPHeed: A Geospatial Food Insecurity Forecasting System for DA Region IV-A Using NLP and Machine Learning**
> Researchers: Princess Gwenn A. Destura, Christina M. Esico, Angel Vhea P. Melindo. Adviser: Dr. Rolando B. Barrameda. De La Salle University – Dasmariñas.
>
> You are invited to evaluate a research prototype that estimates relative food insecurity risk for CALABARZON's provinces, cities and municipalities.
>
> **What you will do.** You will view a short demonstration and use the dashboard, then answer this form. It takes about 25–30 minutes.
>
> **About the outputs.** The system gives relative risk indicators only. They are not official food insecurity classifications and do not replace government assessments.
>
> **Voluntary participation.** Taking part is voluntary. You may skip any question or stop at any time without penalty.
>
> **Confidentiality.** Your answers are anonymous and reported only in aggregate. They are stored securely and handled under Republic Act No. 10173 (Data Privacy Act of 2012). Only the information needed for the study is collected.
>
> **Risks and benefits.** There is no foreseeable risk beyond ordinary computer use. Your feedback will improve the tool and inform the thesis.
>
> **Contact.** [researcher e-mail], [adviser e-mail].
>
> **CONSENT.** I have read the above and agree to take part. ( ) Yes ( ) No
> If you answer "No", the form ends.

## Part 2. Facilitator guide (for the researchers)

### Before the session

1. **Set up the dashboard.** Use the E25 development dashboard (`dashboard_dev/dist-e25`, page `/forecast-timeline`) on a projector and on the evaluators' devices. It reads the single E25 forecast record (content SHA-256 shown on the page).
2. **Record the versions.** In the session log, record:
   - the dashboard build;
   - the content SHA-256 of the forecast record;
   - the ranking file.
3. **Respect the evaluation window.** Do not change the system between sessions of the same evaluation window.
4. **Prepare the Form.** Confirm that it has a section break **before** RK2/RK3 and **after** them, so the ranking is shown only after RK2/RK3 are submitted.
5. **Prepare your script.** It must not suggest which answers are expected.

### Session (about 40 minutes)

| Step | Time | What to do |
|---|---|---|
| 1. Consent | 5 min | Read the consent text aloud; evaluators answer the CONSENT item. |
| 2. Demonstration | 10 min | Show the 2025-Q1 to 2027-Q1 timeline (back-test cells, sealed 'outcome pending' cells, the 2027-Q1 missing-inputs panel), the regional and provincial split, the 'indicative only' flags, the rankings and the PDF download. **State plainly that the 2027-Q1 forecast is not available yet, which inputs are missing, and that every forecast is indicative only (no lead is validated).** |
| 3. Hands-on | 10 min | Evaluators try three fixed tasks. **(a)** Find the supporting-news period. **(b)** Find their province's city/municipality ranking. **(c)** Download the PDF. Record, without helping, whether each task was completed. |
| 4. Questionnaire | 15 min | Parts A–F, in order. Answer only procedural questions. |

### After the session

1. Export the Form responses as CSV, keeping the item-code prefixes.
2. Run:

   ```
   python instruments/score_responses.py <export.csv> --rankings rankings/lgu_rankings_backtest_2026Q1.csv
   ```

   Use the ranking file that was actually shown.
3. Archive the CSV and the scorer output with their SHA-256 hashes.

**Never** edit, add or simulate responses.

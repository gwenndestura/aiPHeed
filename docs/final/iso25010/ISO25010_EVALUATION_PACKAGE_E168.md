# ISO/IEC 25010 software-quality evaluation of the aiPHeed dashboard (E168)

**What this package is.** Everything needed to run Objective 5's software-quality evaluation with DA Region IV-A evaluators:
- the instrument;
- instructions and the evaluator workflow;
- a response template;
- a scoring script;
- interpretation rules;
- a report template.

**Status (2026-11-07): ready to administer, not yet administered.** No evaluator responses exist. No result may be reported until real responses are entered into `responses_template.csv` and scored.

**What it is not.** This evaluates the *software*. It does not evaluate the *forecast model*. Model accuracy, lead time and baselines are reported separately: `docs/final/INDEPENDENT_COMPLIANCE_AUDIT_E168.md` and `FINAL_SYSTEM_REPORT_E168.md`.

## 1. Standard and characteristics

**Edition used.** ISO/IEC 25010:2023 (*Systems and software engineering — SQuaRE — Product quality model*), which has nine characteristics.

If the thesis cites the 2011 edition, use the right-hand column of the table. The mapping is one-to-one for eight characteristics, plus Safety, which is new in 2023.

| # | ISO/IEC 25010:2023 characteristic | Items | 2011 edition name |
|---|---|---|---|
| 1 | Functional suitability | FS1–FS3 | Functional suitability |
| 2 | Performance efficiency | PE1–PE2 | Performance efficiency |
| 3 | Compatibility | CO1–CO2 | Compatibility |
| 4 | Interaction capability | IC1–IC4 | Usability |
| 5 | Reliability | RE1–RE2 | Reliability |
| 6 | Security | SE1–SE2 | Security |
| 7 | Maintainability | MA1–MA2 (IT/MIS evaluators only) | Maintainability |
| 8 | Flexibility | FL1–FL2 | Portability |
| 9 | Safety | SA1–SA2 | (not in 2011) |

## 2. Evaluators and workflow

**Evaluators.** DA Region IV-A staff, as in the thesis sample (planning, monitoring and evaluation, and field programme staff). MA1–MA2 are answered only by IT/MIS staff; everyone else marks them "not applicable".

**Consent.** A verbal or written consent script is read first. No names are recorded. A respondent is identified only by a code (R01, R02, …) and their unit type.

**Session (about 35 minutes per evaluator):**

| Step | Minutes | What happens |
|---|---|---|
| 1 | 3 | Consent; explain that the tool is a student research system, not an official DA product |
| 2 | 15 | Task scenarios T1–T6 (section 3) on the public dashboard; the facilitator records success, time and errors on the observation sheet |
| 3 | 12 | Questionnaire (section 4) on paper or a form; 5-point scale |
| 4 | 5 | Open debrief questions (section 5) |

**Environment.** The evaluator uses their own office computer or phone, on the public URL. Record the browser and device in the response file (the Flexibility items depend on them).

## 3. Task scenarios (observation sheet)

| Task | Instruction to the evaluator | Correct outcome |
|---|---|---|
| T1 | Find the forecast risk class of Quezon for the next quarter. | Quezon, 2027-Q1, LOW (probability shown on the card) |
| T2 | Find which provinces are forecast HIGH three quarters ahead. | None (2027-Q3, all LOW) |
| T3 | Find the three highest-priority municipalities in Batangas. | Matches the ranking list for Batangas |
| T4 | Find what pushed Rizal's forecast up the most. | The largest bar on Rizal's explanation card |
| T5 | Find how accurate the forecast was in testing. | 75.0% one quarter ahead (About, or the landing page) |
| T6 | Download the report for Laguna. | A PDF opens or downloads |

Record per task: completed (yes or no), time in seconds, errors, and whether help was needed.

## 4. Questionnaire

**Scale:** 1 = strongly disagree, 2 = disagree, 3 = neutral, 4 = agree, 5 = strongly agree, NA = not applicable.

**1. Functional suitability**
- FS1. The dashboard provides the functions I need to monitor food-insecurity risk in CALABARZON.
- FS2. The forecast, map, ranking and explanations shown are consistent with one another.
- FS3. The municipal priority ranking is useful for choosing where programmes go first.

**2. Performance efficiency**
- PE1. Pages and maps load quickly enough for my work.
- PE2. Switching quarters or provinces responds without noticeable delay.

**3. Compatibility**
- CO1. The downloaded reports can be used in our own briefings and documents.
- CO2. The dashboard works alongside the other tools and browsers we use.

**4. Interaction capability**
- IC1. I could find what I needed without help.
- IC2. The labels clearly separate a forecast from a measured value.
- IC3. I understand what HIGH and LOW risk mean on this dashboard.
- IC4. The explanations of what moved a forecast are understandable.

**5. Reliability**
- RE1. The dashboard worked without errors during this session.
- RE2. When data were missing, the dashboard said so instead of showing a misleading value.

**6. Security**
- SE1. I am confident that only authorised staff can approve or reject forecasts.
- SE2. The dashboard does not expose personal or sensitive information.

**7. Maintainability (IT/MIS evaluators only)**
- MA1. Updating the data and forecasts each quarter appears manageable for our office.
- MA2. The documentation is sufficient for our staff to maintain the system.

**8. Flexibility**
- FL1. The dashboard works on the devices I use at work (computer and phone).
- FL2. The dashboard could be adapted to other regions or indicators.

**9. Safety**
- SA1. The dashboard warns clearly that its forecasts are not official classifications.
- SA2. The stated limitations would prevent me from over-relying on a single forecast.

**System Usability Scale (optional; Brooke 1996).** Items SUS1–SUS10 in their standard wording. Scored with the standard SUS formula.

## 5. Open debrief

1. What would you use this dashboard for in your unit?
2. What was confusing or missing?
3. What would make you trust or distrust a forecast shown here?

## 6. Data entry

Enter one row per evaluator in `responses_template.csv`:
- the respondent code and unit type;
- the device and browser;
- task results T1–T6;
- each item 1–5, or blank for not applicable;
- SUS1–SUS10 if used.

Do not enter anything that was not actually observed or answered.

## 7. Scoring and interpretation (fixed before data collection)

Run `python -m app.iso25010.score docs/final/iso25010/responses_template.csv`. It writes `iso25010_results.json` and `iso25010_results.md` beside the CSV.

**For each characteristic it reports:**
- n (excluding NA);
- mean and SD;
- the % agreeing (4 or 5);
- Cronbach's α (when n ≥ 5 and the characteristic has 2 or more items).

**Overall it reports:**
- the mean of the characteristic means;
- task completion rate and median time per task;
- the SUS score (0–100) if used.

**Interpretation of item and characteristic means:**

| Mean | Verbal interpretation |
|---|---|
| 4.21–5.00 | Strongly agree (very high quality) |
| 3.41–4.20 | Agree (high quality) |
| 2.61–3.40 | Neutral (moderate quality) |
| 1.81–2.60 | Disagree (low quality) |
| 1.00–1.80 | Strongly disagree (very low quality) |

**SUS interpretation (Bangor, Kortum and Miller 2009):** 68 is the average; 80.3 or higher is "excellent".

A characteristic is "acceptable" when its mean is ≥ 3.41 and at least 60% of evaluators agree. Both thresholds are fixed here, before any response exists.

## 8. Report template (fill only from `iso25010_results.md`)

> **Objective 5: Software-quality evaluation (ISO/IEC 25010:2023).** N = __ DA Region IV-A evaluators (__ planning, __ M&E, __ field, __ IT/MIS) evaluated the public aiPHeed dashboard between __ and __.
>
> Task completion was __% (median __ s per task).
>
> | Characteristic | n | Mean | SD | % agree | α | Interpretation |
> |---|---|---|---|---|---|---|
> | … | | | | | | |
>
> The overall mean was __ (__), and the SUS score was __.
>
> The lowest-rated characteristic was __ (__), mainly because __ (debrief).
>
> These ratings evaluate the software, not the accuracy of the forecasts, which is reported in section __.

## 9. External dependency

The evaluation requires DA Region IV-A to name the evaluators and schedule the sessions. Until then, this objective is **BLOCKED (awaiting evaluators)**, not completed.

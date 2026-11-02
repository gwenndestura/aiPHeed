# Objective 5: dashboard evaluation instrument, test checklist and FNRI face validity

> "To deploy a public geospatial dashboard presenting forecast maps and early-warning alerts, evaluate it under the
> ISO/IEC 25010 software quality model with DA Region IV-A evaluators, and validate its forecasts against DOST-FNRI
> NNS 2019 and 2023 CALABARZON prevalence figures as a face-validity anchor." (Chapter I §1.5.2)
>
> H5: "aiPHeed will not receive favorable functional suitability, accuracy, and usability ratings from DA Region IV-A
> evaluators under the ISO/IEC 25010 software quality model."

**Status: Partially achieved; waiting for evaluators.**

| Part | Status |
|---|---|
| Dashboard deployed | Yes, but it does not yet show the food-insecurity forecast (`DASHBOARD_PROPOSAL.md`, awaiting approval) |
| Instrument (this file) | Ready to use; supersedes the scenarios of `E114_Final_Run/E114_OBJECTIVE5_EVALUATION_PACKAGE.md`, which described an earlier outlook design |
| ISO/IEC 25010 evaluation | Needs DA Region IV-A evaluators |
| FNRI face validity | 2023 done with the verified figure (§D); 2019 not usable (different scale) |

**Use only after the approved dashboard changes are live.** The scenarios and test cases describe the food-insecurity
forecast display.

---

## A. ISO/IEC 25010 questionnaire (DA Region IV-A evaluators)

**Respondents:** DA Region IV-A staff (planned 50: planning and monitoring 10, program staff 25, field and LGU-facing
10, ICT and records 5). Items marked **ICT** are answered by ICT and records staff only. The others are answered by all.

**Scale (every item):** 1 = Strongly disagree, 2 = Disagree, 3 = Neither agree nor disagree, 4 = Agree,
5 = Strongly agree. "Cannot judge" is allowed and is excluded from that item's mean.

**Model version.** Characteristics and sub-characteristics follow **ISO/IEC 25010:2011**, the version named in Chapter I.
The 2023 revision renames *usability* to *interaction capability* and *portability* to *flexibility*, and adds *safety*.
Item S1 covers safety in the 2023 sense.

**Before the questionnaire, each respondent completes the task scenarios in Part C.**

### A1. Functional suitability

| # | Sub-characteristic | Item |
|---|---|---|
| FS1 | Functional completeness | The dashboard shows everything I need to know about next quarter's food-insecurity outlook for CALABARZON. |
| FS2 | Functional completeness | The dashboard shows which municipalities and cities to look at first. |
| FS3 | **Functional correctness ("accuracy")** | The forecast numbers shown match the information sources the dashboard cites (SWS, PSA). |
| FS4 | **Functional correctness ("accuracy")** | The dashboard states correctly how reliable the forecast is (its tested accuracy and its limits). |
| FS5 | **Functional correctness ("accuracy")** | Past forecasts are shown with what actually happened, so I can see how often the forecast was right. |
| FS6 | Functional appropriateness | The functions provided help me plan food-security interventions. |
| FS7 | Functional appropriateness | The early-warning label (HIGH or LOW) is useful for deciding where to pay attention. |

### A2. Performance efficiency

| # | Sub-characteristic | Item |
|---|---|---|
| PE1 | Time behaviour | Pages and the map load quickly enough for my work. |
| PE2 | Time behaviour | Changing the quarter or province updates the display without noticeable delay. |
| PE3 | Resource utilization | The dashboard runs well on the computer or phone I normally use at work. |
| PE4 | Capacity (**ICT**) | The dashboard stays responsive when several colleagues use it at the same time. |

### A3. Compatibility

| # | Sub-characteristic | Item |
|---|---|---|
| CO1 | Co-existence | The dashboard works alongside the other programs I use without problems. |
| CO2 | Interoperability | I can export or download information (PDF, table) in a form I can use in reports. |
| CO3 | Interoperability (**ICT**) | The data and outputs could be connected to other DA systems. |

### A4. Usability

| # | Sub-characteristic | Item |
|---|---|---|
| US1 | Appropriateness recognizability | I could quickly tell what the dashboard is for. |
| US2 | Appropriateness recognizability | I understand what the main number on the dashboard means. |
| US3 | Learnability | I learned to use the dashboard without help. |
| US4 | Learnability | The explanations (glossary, labels, notes) help me understand terms such as "lead", "experimental" and "priority ranking". |
| US5 | Operability | It is easy to move between quarters, provinces and municipalities. |
| US6 | User error protection | The dashboard makes it hard to misread a forecast as a measured fact. |
| US7 | User interface aesthetics | The layout, colours and map are pleasant and clear. |
| US8 | Accessibility | Text, colours and symbols are readable for me, including on a small screen. |

### A5. Reliability

| # | Sub-characteristic | Item |
|---|---|---|
| RE1 | Maturity | The dashboard worked without errors during my session. |
| RE2 | Availability | The dashboard was available whenever I tried to open it. |
| RE3 | Fault tolerance | When some data were missing, the dashboard said so clearly instead of failing. |
| RE4 | Recoverability (**ICT**) | After an error or reload, the dashboard returned to a usable state. |

### A6. Security

| # | Sub-characteristic | Item |
|---|---|---|
| SE1 | Confidentiality | The public dashboard shows no personal or confidential information. |
| SE2 | Integrity | I trust that the published numbers cannot be changed by unauthorized users. |
| SE3 | Accountability and authenticity | Each forecast states its source, issue date and version, so it can be traced. |
| SE4 | Non-repudiation (**ICT**) | Administrative actions are logged with who did them and when. |

### A7. Maintainability (**ICT**)

| # | Sub-characteristic | Item |
|---|---|---|
| MA1 | Modularity, reusability | The system's parts (data, model, dashboard) are separated so one can change without breaking the others. |
| MA2 | Analysability | When a number looks wrong, its source and calculation can be traced. |
| MA3 | Modifiability | New quarters of data can be added without redesigning the system. |
| MA4 | Testability | The system has tests that show whether it still works after a change. |

### A8. Portability (**ICT**)

| # | Sub-characteristic | Item |
|---|---|---|
| PO1 | Adaptability | The dashboard works in the common browsers and on mobile devices. |
| PO2 | Installability | The system could be installed on DA servers with the documentation provided. |
| PO3 | Replaceability | The dashboard could replace or complement the current way we monitor food security. |

### A9. Safety (2023 revision; all respondents)

| # | Item |
|---|---|
| S1 | The dashboard's warnings and limits ("experimental", "not a measured rate") are clear enough to prevent harmful decisions based on over-reading the forecast. |

### A10. Open questions

1. What would you use this dashboard for in your work?
2. What, if anything, was confusing or misleading?
3. What should be added or removed?

### Scoring and the H5 decision (fixed before data collection)

| Mean | Interpretation |
|---|---|
| 1.00–1.79 | Strongly disagree |
| 1.80–2.59 | Disagree |
| 2.60–3.39 | Neutral |
| 3.40–4.19 | Agree (favorable) |
| 4.20–5.00 | Strongly agree (favorable) |

- **Scores:** each respondent's score per characteristic is the mean of their answered items in it. Reported: n, mean, SD, median, and the share of respondents ≥ 4.
- **H5 targets** (named in H5):
  - **functional suitability** (FS1–FS7);
  - **accuracy** (functional correctness, FS3–FS5);
  - **usability** (US1–US8).
- **H5 is rejected** (ratings favorable) only if, for **all three**, the mean is ≥ 3.40 **and** a one-sided Wilcoxon signed-rank test against the neutral value 3 gives p < 0.05 after Holm correction across the three. The other characteristics are reported descriptively.
- **Reliability of the scale:** Cronbach's α per characteristic with ≥ 3 items. Report items with α < 0.70.
- Results are reported by respondent group as well as overall.

---

## B. LGU ranking exercise (H4, Post-Survey Questionnaire)

> H4: "The vulnerability-weighted spatial disaggregation of province-level forecasts will not produce municipal and
> city risk rankings that are consistent with DA Region IV-A evaluators' assessments of relative food insecurity
> vulnerability across CALABARZON…"

**Before showing the dashboard ranking:**
1. Each evaluator chooses the province they know best.
2. They receive that province's LGUs **in alphabetical order** (from `out/lgu_rankings_2027Q1.csv`, without scores).
3. They rate each LGU's relative food-insecurity vulnerability: 1 = among the least vulnerable … 5 = among the most vulnerable. "Don't know" is allowed.

**Analysis (fixed now):**
- For each province, Spearman ρ between the evaluators' mean rating per LGU and the dashboard's within-province vulnerability index (`vulnerability_index`; the forecast only scales it).
- Pooled test: the mean of the per-province ρ, weighted by the number of rated LGUs, with a permutation p-value (10,000 within-province shuffles, seed 2027).
- **H4 is rejected** (rankings consistent with evaluators) if the pooled ρ > 0 with permutation p < 0.05.
- Report ρ per province with n, and the top-5 overlap per province.

---

## C. Task scenarios (before the questionnaire; observed and scored)

Each task is scored success, partial or fail, with time to complete. The facilitator does not help.

| # | Task | Correct answer |
|---|---|---|
| T1 | "What is the probability that hunger in Balance Luzon will be high next quarter?" | The main number (for example 86%) and its target quarter |
| T2 | "Is this forecast proven reliable?" | "No. It is experimental: it passed 6 of 7 reliability rules but failed the stability rule." |
| T3 | "What was the latest measured hunger level, and when was it published?" | The latest SWS Balance Luzon reading and its publication date |
| T4 | "Does the forecast differ between Cavite and Quezon?" | "No. The forecast is regional; the same value applies to all provinces." |
| T5 | "Which municipality in Quezon has the highest measured food insecurity?" | "The dashboard does not measure that. It shows a priority ranking based on poverty and density." |
| T6 | "Which factors most influenced this forecast?" | Read the driver bars (SWS hunger history first) and their "influence, not cause" label |
| T7 | "Find a past quarter where the forecast was wrong." | Use the history table, which marks scored forecasts as right or wrong |
| T8 | "Did news about disasters rise this quarter?" | Read the news panel; news is context and did not improve the forecast |

---

## D. Test checklist for the dashboard (to run after the approved changes)

Each item is pass or fail, with a screenshot.

| # | Area | Test | Pass condition |
|---|---|---|---|
| D1 | Main number | Open the public dashboard | Shows P(SWS Balance Luzon hunger > 11.3%) for the next target quarter, the issue date and the lead |
| D2 | Experimental badge | Main card | An "Experimental: not yet a reliable forecast" badge is visible, with a link to the reliability result |
| D3 | Hunger level | Main card | Latest SWS Balance Luzon reading, its quarter and publication date; the 11.3% threshold shown |
| D4 | Regional scope | Province map | Map and text state the forecast is regional; no province shows a different forecast value |
| D5 | LGU table | Rankings | Header and every export carry "priority ranking, not a measured food-insecurity rate"; substitute poverty values flagged |
| D6 | History | Past forecasts | Scored forecasts show "Scored: right/wrong"; unscored ones show "Sealed: not yet scored"; **no forecast is labelled "Observed"** |
| D7 | Claims | Tour, About, PDF | **No statement that DA staff review forecasts** unless a documented review process exists |
| D8 | Drivers | SHAP bars | Group shares shown, `lead` excluded, labelled "relative model influence, not causes" |
| D9 | News | News panel | Labelled context; states news did not improve the forecast |
| D10 | Prices | Price panel | Labelled as inputs (drivers), not the forecast target |
| D11 | Data freshness | Footer or card | Newest SWS, CPI and news dates shown |
| D12 | Missing data | Simulate a missing input (test environment) | A clear "data not available" message; no zero shown as a value |
| D13 | Performance | First load on a 4G phone | Usable in under 5 s; quarter switch under 1 s |
| D14 | Browsers | Chrome, Edge, Firefox, Android Chrome | Same content, no layout break at 360 px width |
| D15 | Accessibility | Contrast checker; keyboard only | WCAG AA contrast; all controls reachable by keyboard |
| D16 | PDF export | Generate a report | Same labels as the dashboard; no "Reviewed by DA" stamp unless a review is documented |
| D17 | Backend tests | `pytest` in `backend/` | All pass |
| D18 | API | `GET` of the new forecast endpoint | Returns the sealed or issued forecast with issue date, lead, P, class, arm, plan SHA and reliability status |

---

## E. FNRI face validity

**Figure used (verified):**
- DOST-FNRI **2023 National Nutrition Survey**, Household and Food Security, regional map
  (https://enutrition.fnri.dost.gov.ph/images/nns-2023/2.%20Household%20&%20Food%20Security%20.pdf).
- **CALABARZON: 19.1%** of households with moderate to severe food insecurity (95% CI 17.0–21.1); Philippines 31.4%.
- Verified by the user from the official map, 2026-11-03.

**Context figure (documented, secondary):**
- 2025 update, **CALABARZON 22.6%**, Philippines 32.6%.
- Source: press reporting (explained.ph) of the DOST-FNRI 2025 update released 17 June 2026, as recorded in `backend/data/processed/nns_fies.parquet` (provenance "secondary_reporting").
- Replace it with the FNRI primary publication when obtained.

**Not used:** NNS 2019. The 2018–2019 food-insecurity component used HFIAS, a different scale from FIES.

**These are household prevalence figures.** The forecast target is a different measure: SWS involuntary hunger above 11.3% in Balance Luzon. The FNRI figures are used as context only, never as labels.

| Check | SWS (Balance Luzon) | Model | FNRI CALABARZON | Agrees? |
|---|---|---|---|---|
| Level, 2023 | mean of 2023 rounds 11.2% (Q4 14.3%) | Lead-1 forecasts LOW in Q1–Q3 (P 0.31–0.45), HIGH in Q4 (0.61) | 19.1% | Not comparable in level (different measures) |
| Region vs nation, 2023 | BL 11.2% vs national 10.7% (BL slightly **above**) | — | 19.1% vs 31.4% (CALABARZON well **below**) | **No**, but Balance Luzon covers all of Luzon outside Metro Manila, not only CALABARZON |
| Change 2023 → 2025 | 11.2% → 18.2% (up) | from mostly LOW (2023) to HIGH in every 2025 quarter | 19.1% → 22.6% (up; secondary) | **Yes**, all three rise |
| Region vs nation, 2025 | BL 18.2% vs national 19.6% (below) | — | 22.6% vs 32.6% (below) | Yes |

Data: `out/obj5_fnri_context.json`.

**Reading:**
- Two FNRI points cannot validate a quarterly forecast.
- They do show the direction the forecast and SWS show: food insecurity rose from 2023 to 2025.
- The 2023 region-vs-nation contrast disagrees, which is expected when Balance Luzon is wider than CALABARZON.
- This is a **face-validity anchor only**, as Chapter I words it.

---

## F. Dashboard changes needed to show the food-insecurity forecast

See `DASHBOARD_PROPOSAL.md` (Step 3, awaiting approval). Nothing in `frontend/` or `backend/` has been changed.

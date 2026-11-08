# Root cause and method decision

**Basis:**
- Chapter I as written in `THESIS 2 (11).pdf`; extract in `sources/chapter1_THESIS2_11_extract.txt`.
- The data files, and the E40–E114, FINAL and FINAL_OBJECTIVE_ACHIEVEMENT results.

**Written:** before any model in `FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` was scored.

## The ten questions, with the evidence

| # | Question | Finding | Evidence |
|---|---|---|---|
| 1 | Is the current target the thesis outcome? | **No.** | <ul><li>Chapter I §1.4: "The dependent variable is the binary food insecurity risk classification, either high or low, of a CALABARZON province in a given quarter."</li><li>§1.7: "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk."</li><li>The FINAL / FINAL_OBJECTIVE_ACHIEVEMENT target (ELEVATED) is **regional** (4 SWS areas), uses **SWS only**, and is "above the area's past-year average", a definition I introduced in FINAL. It is a hunger-change label, not the thesis's province risk class.</li><li>The label that follows Chapter I (T43: hunger condition AND province food-price condition) was set aside after E108.</li></ul> |
| 2 | Is ELEVATED unstable because its reference moves? | **Yes.** | <ul><li>The reference is a moving 4-quarter mean, so the same hunger level can be HIGH one quarter and LOW the next.</li><li>Two SWS rounds in the *same* quarter agree on ELEVATED only 3 times in 8, with a mean difference of 3.7 points (FINAL_OBJECTIVE_ACHIEVEMENT V1).</li><li>A validated simulation caps any forecaster at about 0.64 one quarter ahead (V2). The label is mostly sampling noise plus new shocks.</li></ul> |
| 3 | Is the baseline given the same information? | **Partly no.** | <ul><li>FIL-OA's latest-reading baseline is fair: it uses h_last at the issue date.</li><li>On the Chapter I target, E108's "persistence" used the last **complete** label (all SWS rounds published, quarter ≤ t−1). That is older than what is known at the issue date. Its Lead-1 accuracy, 0.723, was below always-LOW (0.754).</li><li>A fair baseline uses the newest SWS reading and the newest three published CPI months (PERSIST-SI, new here).</li></ul> |
| 4 | Do "75%" and the metric measure the same objective? | **No, in FINAL.** | <ul><li>Objective 2.I: "Accuracy, to measure overall correctness of high- and low-risk province-level classifications."</li><li>FINAL measured the accuracy of a regional change label, so 75% was applied to a different quantity.</li><li>On the province-level class, accuracy must be read against the majority class: T43c is HIGH in 19% of province-quarters, so always-LOW scores about 0.81.</li><li>75% alone is meaningless here. Balanced accuracy, recall and beating the majority class are required (protocol R3, R4, R6).</li></ul> |
| 5 | Is the sample large enough? | **Barely.** | <ul><li>23 SWS rounds; 20 labelled quarters × 5 provinces = 100 T43c rows, 19 HIGH.</li><li>Provinces share the hunger term and move together on prices, so the effective sample is closer to about 20 quarters.</li><li>FIL-OA fitted 27 columns to about 200 overlapping rows from about 15 independent quarters.</li><li>Every comparison here uses cluster bootstrap by quarter, and models use depth ≤ 2 with ≥ 15 rows per leaf.</li></ul> |
| 6 | Are SWS rounds comparable? | **Not fully, and the series was wrong.** | <ul><li>Margins range from ±3 to ±6.</li><li>The respondent base changed from household heads to adults in April 2025, with no bridge.</li><li>**Defect:** the T43 series (`backend/data/inputs/sws_rounds.csv`, `definition_A`) includes the commissioned Stratbase voter round (2025-Q1, BL 24.0) and **excludes** the regular 2025-Q2 rounds (17.0, 15.3) and 2025-Q3 round (23.8).</li><li>The served dashboard (`thesis_system._rounds`) uses the same filter. Every T43 result in E40–E108 used it.</li></ul> |
| 7 | Does lead numbering mean a real future? | **Not always.** | <ul><li>FINAL_OBJECTIVE_ACHIEVEMENT's "Lead 0" is the quarter that has already ended: a nowcast of an unpublished survey (true horizon 1), not advance warning.</li><li>Under the protocol here, Lead 1 is the quarter that starts on the issue date (ends 3 months later). SWS for it is published 1–3 months after it ends, so the warning before the official reading is 4–6 months.</li><li>Each row records the issue date, newest SWS and CPI, newest news and days to the target end.</li></ul> |
| 8 | Do families match their geography and dates? | **Not in FIL / FIL-OA.** | <ul><li>FIL averaged the provincial indicators to one regional value and gave the CALABARZON context to NCR, Visayas and Mindanao rows. The provincial information the thesis is about was thrown away.</li><li>On T43c, every family enters at its own level: provincial A1–A3, V1, C2–C4; national C1, E1, E2; regional H1 and news.</li><li>Publication cut-offs follow E107 (audited) plus the new columns' rules.</li></ul> |
| 9 | Do features predict the future or describe the present? | **Mostly describe the present.** | <ul><li>Hunger features describe the last survey. Reporting news tracks the present (concurrent ρ 0.66), not the future (FINAL).</li><li>The genuinely forward-looking information is the CPI **base effect**: next quarter's food YoY is partly fixed by last year's index, which is already known. E108's no-learning projection used it to reach 0.892 at Lead 1.</li><li>Price news led food-inflation *change* by about two quarters (E113, Holm p .016). This is the one pre-existing reason news could help, and it is tested here.</li></ul> |
| 10 | Which objectives can be met with existing data? | See the table below | |

**Objectives and what limits them (question 10)**

| Objective | Can it be achieved with existing data? |
|---|---|
| 1 (NLP pipeline) | Yes as a pipeline. Predictive value has to be shown. |
| 2 I–IV (province classification metrics) | Yes: the province-quarter class is computable from SWS + PSA, as §1.7 specifies. |
| 2 V (reliable horizon) | Yes, as a test. The answer depends on the data. |
| 3 (municipal rankings from validated province forecasts) | The ranking: yes, with SAE poverty and POPCEN density. "Validated" means validated province forecasts, which Objective 2 supplies. Hypothesis 4 judges ranking quality by **DA evaluators' assessments** (post-survey questionnaire), not by a municipal outcome, and that evaluation has not been held. |
| 4 (baselines) | Yes |
| 5 (dashboard, ISO 25010, FNRI face validity) | The dashboard and FNRI anchor: yes (FIES 2021/2023/2025 held). ISO 25010 with 50 DA evaluators: blocked by scheduling, not by data. |

## What was fundamentally wrong

1. **The work drifted away from the Chapter I target.** Province-quarter high/low risk, from SWS + PSA, was replaced by a regional hunger-change label. That label is noisy and was never the thesis's dependent variable. Every "75% impossible" conclusion from FINAL applies to that label, not to the thesis target.
2. **The Chapter I target had always been scored on a defective SWS series:** a commissioned round included, two regular rounds dropped.
3. **The persistence baseline on that target was not given the information available at the issue date,** so "beats persistence" claims were unfair in both directions.
4. **Horizon wording mixed nowcasts with forecasts.**

## Decision

| Element | Decision |
|---|---|
| Target | **T43c:** the Chapter I province-quarter risk class on the corrected SWS series. It uses the frozen E40 thresholds (hunger 11.3; province food and gap P60 of 2021–22), set on 2026-10-15 before any of this work. |
| Model | **CH1-LGBM** = P(hunger condition) × P(price condition). The price condition is one LightGBM on all 12 families, at their own geography. Risk is HIGH only if both conditions hold, as §1.7 combines them. |
| Baselines | Same-information persistence; climatology; always-LOW; E108's no-learning base-effect rule; Chapter I's six comparators |
| Horizon | Lead 1 = the quarter starting on the issue date; Lead 0 is reported as a nowcast only |
| News | Tested once, by a pre-specified hypothesis: price news helps at Leads 2–3 |
| Regional hunger | FIL-OA is kept as the direct-hunger evidence and is served alongside |

**Disclosure.** E108's results on the defective T43 series (0.892 at Lead 1) were known when this decision was made. The decision rests on the Chapter I wording, not on those numbers. The thresholds are not changed. Whatever T43c scores is reported.

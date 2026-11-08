# E109 Source and target audit

All facts below are from `sources/SOURCES_LOG.md` (S1–S8), written as each source was read on 2026-10-25.

## 1. Starting point

| Item | Value |
|---|---|
| Starting branch / commit | `aiPHeed/e108-best-defensible-forecasting` @ `b56d90e` (equal to origin) |
| E109 branch | `aiPHeed/e109-hunger-forecasting` |
| Working tree at start | clean, apart from two pre-existing untracked items (`docs/aiPHeed_Complete_System_Guide.docx`, `node_modules/`), left untouched |
| Sealed forecasts preserved | E107 `246700a8…`, E108 `fbc8bf91…` (re-hashed by test) |
| Outcome data | `backend/data/inputs/sws_rounds.csv` (sha `519416a1…`); E109 metadata `data/outcome_rounds.csv` (sha `a041e382…`) |
| Protocol | `PROTOCOL.md` sha `3d794793…` (frozen 03:57 UTC); `ADDENDUM_1.md` (real-time vintage), frozen before scoring |

## 2. Credible sources and what they measure

| Source | What it measures | Geography | Frequency | Coverage in project | Use in E109 |
|---|---|---|---|---|---|
| **SWS Social Weather Survey, hunger item** (S1–S6) | **Experienced hunger:** % of families that "experienced hunger and not have anything to eat" at least once in the past three months. Moderate = only once / a few times; Severe = often / always. | National and 4 areas; **Balance Luzon** = Luzon outside Metro Manila | ~quarterly (several rounds in 2025) | 23 non-commissioned rounds, 2021-Q2..2026-Q3 (20 quarters); 1 commissioned round | **Primary outcome** (regional) |
| **PSA official poverty statistics** (S7) | **Food poverty:** subsistence incidence = share of people whose per capita income is below the food threshold. Poverty incidence uses the full threshold. | National, regional, **provincial** | Triennial full-year (2018, 2021, 2023) | Subsistence incidence by province, 2021 and 2023, CV 17–62% (`psa_subsistence_population_2021_2023.csv`) | **Context only.** Two points, so it cannot serve as a quarterly target, and it is not interpolated. |
| **FAO Food Insecurity Experience Scale** (S8) | **Food insecurity** (experience-based severity; SDG 2.1.2 moderate + severe) | 2017 Gallup/FAO sample is national; the FNRI NNS module is regional | Single years | One press-reported CALABARZON value (FNRI NNS 2025: 22.6%); FAO 2017 microdata is national and before 2021 | **Not a target.** At most an external face-validity reference. |
| PSA "FIES" | **A different instrument:** Family Income and Expenditure Survey (income and expenditure) | — | Triennial | The World Bank catalog 5042 link supplied for E109 is in fact **FAO's Food Insecurity Experience Scale 2017**, not PSA's FIES | — |
| PSA CPI, rice, harvest, LFS; BSP; PAGASA; IBTrACS; news | **Food-price pressure and contributing risk factors** | Provincial or national | Monthly / quarterly | E107 registry | Predictors only |

**Access limits (disclosed).**
- PSA web and OpenStat pages refused automated access (HTTP 403). OpenStat showed a bot-verification page, which was not bypassed.
- The PSA provincial values in the project therefore come from the earlier E54 acquisition and were **not re-verified online in E109**.
- SWS PDFs could not be text-extracted. Their HTML releases and news reports of those releases were used instead.

## 3. The concepts are kept apart

1. **Experienced hunger:** SWS Total Hunger, the E109 outcome.
2. **Food insecurity:** FAO FIES moderate/severe, which is not available as a series for CALABARZON. Experienced hunger is its most severe dimension, not the whole concept.
3. **Food poverty:** PSA subsistence incidence, an income measure that is provincial and triennial.
4. **Food-price pressure:** CPI-based. It is an E109 predictor, never an outcome.
5. **Contributing risk factors:** climate, harvest, jobs, remittances, poverty, news. Predictors only.

## 4. Is there an official LOW/HIGH hunger threshold?

**No official SWS LOW/HIGH threshold for total hunger prevalence was found.** The releases read (S1, S2, S3, S5, S6) give:
- percentages;
- changes;
- "record-high" comparisons (for example, the 2020 national average of 21.1%);
- annual averages (2025 national 20.2%).

They give no classification of a prevalence level as low or high.

**SWS Moderate and Severe hunger are frequency categories** for families that did experience hunger ("only once/a few times" vs "often/always"). They are not thresholds on the total percentage.

**Does the thesis need a binary outcome?** Chapter I Objective 2 names classification metrics (accuracy, precision/recall, F1, AUC). E109 therefore:
- makes the **continuous hunger percentage the primary outcome**, with no threshold needed;
- reports binary readings as **research-defined** sensitivities, all fixed before scoring:

| Rule | HIGH if | Origin | Official? |
|---|---|---|---|
| B1 | hunger > 11.3% | E40: 60th percentile of 2021–22 Balance Luzon values (frozen 2026-10-15) | No, research-defined |
| B2 | hunger > 15.0% | round-number sensitivity | No |
| B3 | hunger > 20.0% | round-number sensitivity, near SWS's cited 2025 national average (20.2%) | No |
| B4 | rise > 4.0 points over the latest reading | SWS's published Balance Luzon sampling margin (±4%) | The margin is official; using it as a warning rule is research-defined |

Since 2023-Q4 Balance Luzon hunger has always exceeded 11.3% and 15%, so **B1 and B2 have only one class in every evaluation set**. Their accuracy is trivially 100% for any forecast that stays high, and they cannot measure skill.

## 5. Outcome-series decision (verified against SWS)

**Values checked.** 12 of the 24 project rounds were matched to SWS releases or to reports of them: 2023-Q2, 2023-Q3, 2024-Q3, 2024-Q4, 2025-Q1, both 2025-Q2 rounds, 2025-Q3, 2025-Q4, 2026-Q1, 2026-Q2 and 2026-Q3. **All 12 match.** The 2021–2023-Q1 and 2023-Q4–2024-Q2 rounds were not re-checked in E109; they were verified in E31.

**Two problems the E107/E108 series did not handle:**
1. **The March 2025 round (Balance Luzon 24.0%) is a commissioned Stratbase-SWS survey of 1,800 registered voters** (S5). E107/E108 kept it and dropped the April, June and September 2025 non-commissioned adult rounds (`definition_A`). E109's primary series uses **SWS's non-commissioned rounds** and excludes the commissioned one. Commissioned February and April-11 2025 rounds also exist and were never in the project file.
2. **The respondent base changed in 2025:** household heads until December 2024, registered voters from January to mid-April 2025, adults from late April 2025 (S1, S2). This is a break in the series. It is disclosed, and sensitivity S-HH (household-head rounds only) is too short to evaluate (3 quarters at Lead 1).

**The precision of a single Balance Luzon reading varies by round:**
- ±4% with 600 respondents (June 2023, September 2025, September 2026);
- ±5.7–6% with 300 (September 2023, June 2025);
- 900–1,080 respondents in some rounds (March 2025, December 2024).

A change of 4–6 points between two rounds can be pure sampling noise.

## 6. Geographic limitation

SWS publishes Balance Luzon, not Cavite, Laguna, Batangas, Rizal or Quezon.
- E109 forecasts **one regional series with one row per quarter**. It never replicates the value across provinces.
- **No provincial or municipal hunger accuracy can be claimed.**
- All 142 LGUs are given the status **"insufficient local evidence"**, shown alongside the regional forecast and their PSA SAE poverty as context (`backend/data/e109/lgu_status.json`).

## 7. Approaches compared

| Approach | Target | Level | Usable quarters | Verdict |
|---|---|---|---|---|
| **A: continuous hunger** | SWS Balance Luzon Total Hunger % | region | 20 (9 evaluable at Lead 1, 5–7 at Leads 2–4) | **Primary.** Forecasts the hunger outcome itself, with no invented threshold. |
| B: binary hunger | A with B1–B4 | region | same | Secondary. B1 and B2 are degenerate (one class); B3 and B4 have 3–4 HIGH quarters. |
| C: composite T43 (E108) | hunger > 11.3 AND provincial price pressure | province rows, regional hunger | 13 at Lead 1 | **Not the food-insecurity outcome.** Since 2023-Q4 its variation is entirely price pressure. Kept only as the E108 reference. |

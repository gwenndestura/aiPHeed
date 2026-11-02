# v6 Data requests (drafts: nothing sent, downloaded or requested)

Gate 2 found that no route reaches the 0.85 oracle filter at Lead 2 with the data held (`FEASIBILITY.md`). Sending any of these is your decision. Names, dates and signatures are left blank for you to fill in. Each request says what it can change and what it cannot.

| # | Request | Can change | Cannot change | Who acts |
|---|---|---|---|---|
| 1 | SWS round documentation | Replaces 8 assumed margins; settles whether real noise exceeds the binomial SE, without using scored outcomes; could justify a design-effect-adjusted tolerance | Does not forecast anything; does not create test quarters | You (reading public releases), or a letter |
| 2 | PSA regional quarterly LFS | The only untested leading-signal candidate. National unemployment change showed ρ ≈ 0.1, so a small gain is expected (INFERRED). | It would need to explain about 85 % of 3-quarter change variance to reach 75 % | You (download authorisation) |
| 3 | CBMS 2024 FIES | Provincial/LGU ground truth for 2024: the only route to a provincial claim | No Lead-2 test: one point in time | You and your adviser (formal request) |
| 4 | Verified release dates for E119 predictors | Replaces 512 rule-based availability cells with real dates | The predictors already failed out of sample, so a gain is unlikely (INFERRED) | You (lower priority) |
| 5 | DOST-FNRI ENNS regional FIES tables | Validation reference for Region IV-A | No quarterly series | You (request) |
| 6 | New SWS releases, 2026-Q4 onward | **The sealed confirmation set: the only thing that can test any claim** | — | Routine |

## Access steps

**1. SWS documentation.**
1. Open each release from the `source` column of `backend/data/forecasting/sws_area_rounds.csv`.
2. Copy the survey-background paragraph: fieldwork dates, sample size per area, margin of error.
3. Priority rounds are 2021-Q2 … 2023-Q1, whose margins are assumed. Also confirm the 2025-04-23/28 round, which is missing from the 14 Oct 2026 release tables.
4. Send letter A about design effects.

You would do the reading yourself, because web access to SWS is withheld in these sessions to protect the sealed quarters. **Note:** opening SWS pages can expose newer results. Open only the listed historical URLs.

**2. Regional LFS.**
1. In PSA OpenSTAT (openstat.psa.gov.ph), go to Labor and Employment → Labor Force Survey → regional quarterly tables. The exact table name was not checked (NOT VERIFIED).
2. Export 2021 onward as CSV.
3. Record each round's PSA press-release date from psa.gov.ph as its availability date.
4. Before testing, register it in a new pre-registration: it is a new hypothesis, and development results alone would not confirm it.

**3. CBMS 2024 FIES.** Letter B, to the PSA CBMS Service or the PSA Regional Statistical Services Office IV-A; or to each LGU's CBMS focal office. Expect a data-sharing agreement.

**5. FNRI.** Letter C. Published ENNS reports may already hold the regional tables; check those first.

**6. New SWS releases.** See `FINAL_REPORT.md`, "Keeping the confirmation test alive".

## Letter A: SWS, survey documentation

> [Date]
>
> Social Weather Stations
> Survey Data Library
>
> Dear [Name / Sir or Madam]:
>
> I am [name], a [degree] student at [university], writing my thesis on forecasting food insecurity in CALABARZON under the supervision of [adviser]. The study uses the published SWS involuntary hunger estimates for Metro Manila, Balance Luzon, Visayas and Mindanao from 2021 onward.
>
> To evaluate forecasts fairly against the precision of the survey, may I ask for the following:
>
> 1. the sample size and margin of error per study area for each national round from the second quarter of 2021 to the first quarter of 2023;
> 2. whether the published margins of error include a design effect and, if design effects are available for the hunger items by study area, the values or the appropriate way to cite them;
> 3. confirmation of the published figures for the round fielded on April 23–28, 2025.
>
> The information will be used only for this academic study and will be cited as you direct. I am happy to follow any data-use terms that apply.
>
> Respectfully,
> [Name, contact details]
> Noted by: [Adviser]

## Letter B: PSA, CBMS 2024 food-insecurity data

> [Date]
>
> [Name]
> [PSA CBMS Service / Regional Director, PSA Regional Statistical Services Office IV-A]
>
> Dear [Name / Sir or Madam]:
>
> I am [name], a [degree] student at [university], under the supervision of [adviser]. My thesis studies food insecurity in the CALABARZON region. No current official series measures it at provincial and municipal level, and the 2024 Community-Based Monitoring System appears to be the most direct source.
>
> May I request access to aggregated estimates from the 2024 CBMS, for the five CALABARZON provinces and their 142 cities and municipalities:
>
> 1. prevalence of food insecurity, from the CBMS food-insecurity items;
> 2. the number of households covered, and any available measure of precision or data-quality flags;
> 3. the questionnaire wording of those items and the release date of the data.
>
> Aggregated tables are enough; no household-level or identifying data are needed. The data will be used only as a validation reference for this academic study. I will comply with the Data Privacy Act of 2012 and any data-sharing agreement you require.
>
> Respectfully,
> [Name, contact details]
> Endorsed by: [Adviser, position, university]

The availability of FIES items in CBMS 2024 comes from earlier project documents, not from a PSA source checked here (NOT VERIFIED). The letter asks in terms that still work if the wording differs.

## Letter C: DOST-FNRI, regional food-insecurity tables

> [Date]
>
> [Name]
> Department of Science and Technology – Food and Nutrition Research Institute
>
> Dear [Name / Sir or Madam]:
>
> I am [name], a [degree] student at [university], under the supervision of [adviser], studying food insecurity in CALABARZON.
>
> May I request the Expanded National Nutrition Survey estimates of household food insecurity for Region IV-A and, where available, its provinces, for each survey round from 2021 onward, with sample sizes, measures of precision, the scale used and the publication date?
>
> The figures will be used only as a validation reference for this academic study and will be cited as you direct.
>
> Respectfully,
> [Name, contact details]
> Noted by: [Adviser]

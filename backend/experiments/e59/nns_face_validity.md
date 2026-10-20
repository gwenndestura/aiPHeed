# NNS face-validity anchor (Specific Objective 5)

Thesis (p.13): "validate its forecasts against DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures as a
face-validity anchor". Also p.51: "DOST-FNRI ENNS FIES prevalence from NNS 2021 and NNS 2023 will be retained as a
face-validity anchor confirming elevated food insecurity in CALABARZON per FAO SDG 2.1.2".

Read-only. Only official DOST-FNRI figures already in the repository are used: `backend/data/e22/nns_fies_verified.json`.
That file says the figures were "read from DOST-FNRI primary publications on 2026-10-13; values checked against the
rendered page, not only the PDF text layer". Nothing was estimated.

## Official figures available (FIES, moderate or severe household food insecurity, SDG 2.1.2)

| Area | Survey | Value | Interval | Source (exact) |
|---|---|---|---|---|
| **Region IV-A (CALABARZON)** | 2023 NNS | **19.1%** | 17.0-21.1 (95%) | DOST-FNRI, 2023 NNS infographic 2 "Household & Food Security", p.2 map "Prevalence of Moderate to Severe Household Food Insecurity, by Region: Philippines, 2023". https://enutrition.fnri.dost.gov.ph/images/nns-2023/2.%20Household%20&%20Food%20Security%20.pdf |
| Philippines | 2023 NNS | 31.4% | 30.7-32.1 (95%) | DOST-FNRI, 2024 National Nutrition Summit Part 1. https://enutrition.fnri.dost.gov.ph/uploads/2024%20National%20Nutrition%20Summit_Part%201.pdf |
| Philippines | 2018-2019 ENNS | 44.2% | – | same Summit deck, trend chart "moderate to severe food insecurity among households based on FIES: Philippines, 2019 to 2023" |
| Batangas | 2021 ENNS | 29.7% | 27.3-32.2 (90%) | DOST-FNRI, 2021 ENNS Provincial Dissemination - Batangas. https://enutrition.fnri.dost.gov.ph/uploads/2021%20ENNS%20PROVINCIAL%20DISSEMINATION%20-%20BATANGAS.pdf |
| Cavite | 2021 ENNS | 31.7% | 27.0-36.4 (90%) | DOST-FNRI, 2021 ENNS Provincial Dissemination - Cavite. https://enutrition.fnri.dost.gov.ph/uploads/2021%20ENNS%20PROVINCIAL%20DISSEMINATION%20-%20CAVITE.pdf |

**Not found** (recorded in the same file): a single-year 2019 CALABARZON regional FIES (the 2018-2019 ENNS was a rolling
sample covering 2 CALABARZON provinces in 2019); a 2021 CALABARZON regional FIES; 2021 decks for Laguna, Quezon and
Rizal; any 2018 or 2019 provincial deck. The project earlier removed unverifiable values (51.6% for 2023 and 50.9% for 2021).

## Comparison possible with these figures (2023 only)

| Quantity, 2023 | Value | Source |
|---|---|---|
| NNS 2023 FIES, CALABARZON | 19.1% (lowest of all regions; Philippines 31.4%) | above |
| SWS self-rated hunger (Balance Luzon), mean of the 4 definition-A rounds of 2023 | 11.15% | `backend/data/inputs/sws_rounds.csv` |
| Model, CALABARZON mean one-quarter-ahead probability, 2023-Q1..Q4 (20 province-quarters) | 0.469 (E49 and E53) | `data/e49/e49_record.json`, `data/e53/e53_record.json` (lead-1 backtests) |
| Observed label, 2023 (20 province-quarters) | 11 HIGH, 9 LOW | same records |

For context, later years:

| Year | SWS hunger (mean) | Model mean probability (E49 / E53) | Observed HIGH |
|---|---|---|---|
| 2024 | 19.58% | 0.538 / 0.521 | 19 of 20 |
| 2025 (Q1, Q4) | 20.35% | 0.860 / 0.825 | 9 of 10 |
| 2026 (Q1..Q4) | 21.10% | 0.867 / 0.833 | 14 of 15 |

## Reading (face validity, not a statistical test)

- **2023 is consistent.** NNS 2023 puts CALABARZON lowest of all regions (19.1% vs 31.4% nationally). In the same
  year the model is at its lowest (mean 0.469; 9 of 20 province-quarters observed LOW), and SWS hunger is at its
  2021-2023 level (about 11%). Both sources show 2023 as a relatively low-stress year for CALABARZON.
- **The 2024-2026 rise cannot be anchored.** The model's index and the observed HIGH share climb with SWS hunger
  (11% to about 20%), but there is no NNS/FIES figure after 2023 to confirm or contradict this.
- **The thesis's wording does not hold.** Section 3.4.2 calls the anchor one "confirming elevated food insecurity in
  CALABARZON". The verified 2023 figure shows the opposite: CALABARZON had the **lowest** prevalence nationally. A
  HIGH label means above the trailing median of CALABARZON's own history, not high by national standards.
- **One regional data point cannot validate a forecast statistically.** FIES (12-month household experience,
  biennial), SWS hunger (involuntary hunger in the past 3 months, Luzon-wide) and the model probability measure
  different things.

## What the researchers must provide to complete the thesis anchor (2019 and 2021)

Exact official figures, each with publication title, table or page, and URL. Do not estimate them.

1. **2019 CALABARZON (Region IV-A) prevalence of moderate or severe household food insecurity (FIES)**, single-year
   2019, from DOST-FNRI (2018-2019 Expanded NNS regional table). If DOST-FNRI only publishes a pooled 2018-2019
   regional estimate, provide that, with its years stated.
2. **2021 CALABARZON regional FIES (moderate or severe)** from the 2021 ENNS, if published at regional level.
   Otherwise confirm that only provincial decks exist (Batangas 29.7%, Cavite 31.7% are already verified).
3. **2021 provincial FIES for Laguna, Quezon and Rizal**, if any 2021 deck covered them (the known URLs return 404).
4. Optional, for any later year: an NNS/ENNS FIES figure for CALABARZON after 2023, to anchor the 2024-2026 rise.

Until these are provided, the anchor stands on the 2023 regional figure only, as reported above.

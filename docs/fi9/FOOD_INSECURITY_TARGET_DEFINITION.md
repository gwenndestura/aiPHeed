# Food-insecurity target definition (FI9, fixed 2026-11-03, before the FI9 evaluation)

Locked in `backend/data/fi9/out/PROTOCOL_LOCK.json` (sha256 `adc90414fa63…`). Code: `app/fi6/target.py`.

| Field | Definition |
|---|---|
| **Selected target** | Whether **SWS involuntary hunger in Balance Luzon** in the target quarter is **significantly above its five-year normal**: HIGH when hunger − (mean of the preceding 20 quarters) > the round's published margin of error. Numeric companion: the quarter's hunger level (%). |
| Original source | Social Weather Stations (SWS) Social Weather Survey releases (`backend/data/fi5/raw/sws/`, with release dates). |
| Geographic coverage | **Balance Luzon** = Luzon outside Metro Manila (CAR, I, II, III, IV-A, MIMAROPA, V). CALABARZON is ~34 % of its population. Regional only. |
| Survey instrument | Face-to-face (recently mixed-mode) national household survey; one question: "In the last three months, did your family experience hunger and not have anything to eat?" |
| Measurement | Experience-based, **directly measured** household hunger (% of families). |
| Reference period | Past three months before fieldwork; quarters with several rounds are averaged. |
| Scale | Binary HIGH/LOW for classification; percentage for the numeric forecast. |
| Available observations | 98 labelled quarters (2000-Q4 – 2026-Q3) once five years of history exist; 62 evaluation targets 2010-Q1 – 2026-Q3 (11 HIGH). |
| Missing observations | Quarters without an SWS survey (listed in MISSING_DATA_REPORT.md); left empty, never interpolated. |
| Comparability problems | Survey vehicle and mode changes; an alternating "sawtooth" between rounds (lag-1 autocorrelation of changes −0.56 vs −0.28 expected from sampling error, FI8); Balance Luzon ≠ CALABARZON. |
| Sampling uncertainty | Published MOE per round (±3 to ±6 pp for Balance Luzon; median ±6); each label carries a flip probability (`p_flip`); 5 of the 62 evaluated labels have p_flip > 0.25. |

## Why this target

Following the hierarchy in the directive (§4.1):

1. *Direct experience-based outcome with consistent definition and adequate coverage.* SWS hunger is the only
   direct food-insecurity measure with a repeated quarterly time series covering CALABARZON. It is measured
   independently of every predictor, so there is no circularity (§4.2).
2. *Comparable repeated provincial FNRI outcomes.* **Not available.** FNRI 2015 HFIAS gives one provincial wave. The
   ENNS provincial values in the owner workbook come from a secondary DEPDev document, cover one year per province
   (2018, 2019 or 2021) and appear to be on different scales. The 2023 FIES is regional only. See
   LABEL_COMPARABILITY_REPORT.md.
3. *Regional outcome with a clearly regional claim.* **Selected.** The claim is limited to Balance Luzon.
4. *Small-area estimation.* **Not possible now.** It needs household food-security microdata with survey design
   variables (FNRI public-use files). Those are blocked from this network and were not requested (directive).

## Claims the model may make

* It may say: "the next-quarter outlook for SWS hunger in Balance Luzon (which includes CALABARZON) is HIGH/LOW,
  with probability p and projected level x % (range a–b)".
* It may **not** say: provincial or municipal hunger, CALABARZON's own hunger rate, measured prevalence for any LGU,
  or that any domain *causes* the outlook.
* Province and LGU outputs are a **vulnerability-adjusted priority** (PSA poverty and density × the regional
  outlook), not food-insecurity measurements.

## Not used as targets

Food CPI, rice prices, subsistence or poverty incidence, unemployment, affordability or any composite of the
predictors. They are predictors or context only.

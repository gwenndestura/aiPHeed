# E129 Addendum 1: owner-designated validation data (2026-10-31)

## The owner's assignment (as given)

| Data source | Role in the study |
|---|---|
| PSA provincial subsistence incidence | Provincial food-deprivation reference |
| FNRI FIES | Household food insecurity reference |
| SWS Balance Luzon hunger | Regional hunger reference |
| PSA provincial food CPI | Forecasting predictor |

## Changes this makes to E129

1. **Provincial food CPI is a predictor, not a target.**
   - The E129 "layer 1" option, a forecast of provincial food-price pressure, is **not adopted**. It stays documented as an option only.
   - The CPI audit findings still hold for CPI as a predictor: 25 % province-specific variance; deviation autocorrelation 0.74 / 0.55 / 0.29 / −0.05 at Leads 1–4.
2. **The validation framework is now defined by the owner.** The three references are external checks of the provincial outputs, not training labels. None of them is used to fit a model.

## What each reference can validate

| Reference | Data held | Provincial points | Frequency | What it can test | What it cannot test |
|---|---|---|---|---|---|
| PSA subsistence incidence | 2021 and 2023, all 5 provinces (`backend/data/inputs/psa_subsistence_population_2021_2023.csv`; both published 2024-08-15) | 10 | Triennial | (a) Province ranking agreement in 2021 and 2023. (b) Direction of the 2021→2023 change per province. | Quarterly Lead 1–4 accuracy; R1 (10 quarters / 40 rows) |
| FNRI FIES (ENNS 2021) | Batangas 29.7 % [27.3–32.2], Cavite 31.7 % [27.0–36.4] (90 % CI) | 2 (+ Lucena) | One round | Agreement in level for 2 provinces | Ranking (the CIs overlap); any lead |
| FNRI FIES (2022 ENNS / CBMS 2024) | Not held (requests unsent) | Up to 5 / 142 LGUs | One round each | Ranking at province / LGU level | Quarterly leads |
| SWS Balance Luzon | 20 quarters 2021-Q2..2026-Q3 | 0 (regional) | Quarterly | Regional hunger forecast at Leads 1–4 (E128) | Any provincial difference |

## Subsistence incidence: which 2021→2023 changes exceed sampling error

**Method.** z = |Δ| / √(SE₂₀₂₁² + SE₂₀₂₃²), with SE = value × CV.

| Province | 2021 (CV) | 2023 (CV) | Δ | z | Real change? |
|---|---|---|---|---|---|
| Quezon (excl. Lucena) | 6.6 (17 %) | 0.9 (40 %) | −5.7 | 4.7 | **Yes, fall** |
| Rizal | 0.9 (34 %) | 2.6 (25 %) | +1.7 | 2.4 | **Yes, rise** |
| Cavite | 2.4 (29 %) | 0.8 (62 %) | −1.6 | 1.9 | Marginal |
| Laguna | 2.4 (24 %) | 1.3 (35 %) | −1.1 | 1.5 | No |
| Batangas | 1.0 (34 %) | 1.4 (34 %) | +0.4 | 0.7 | No |

So the subsistence reference gives **2 clear provincial movements** (Quezon down, Rizal up) and a 2021 and a 2023 cross-section of 5 provinces.

**Rank tests are weak with 5 provinces.** An exact one-sided Spearman needs ρ ≥ 0.9 (p ≈ 0.04) to be significant in one year.

## Consequence for the decision

**The classification stays PROVINCIAL TARGET NOT READY for supervised quarterly provincial forecasting.**
- The owner's references are valid **validation references**: measured food deprivation and food insecurity, by province.
- But they are 10 + 2 provincial points at triennial or one-off frequency.
- They can check whether the provincial outputs **rank and move like** measured deprivation. They cannot score quarterly Lead 1–4 forecasts, and they cannot serve as a training label.

**What E129 can now specify (no training)**
- A **provincial validation protocol** for any provincial output (FIRI3 or a future model), with:
  - V-S1: Spearman ranking vs subsistence 2021 and 2023, with outputs as of each year;
  - V-S2: direction agreement for Quezon and Rizal (the two real changes);
  - V-F1: consistency with FNRI FIES 2021 for Batangas and Cavite (and with CBMS / ENNS 2022 when obtained);
  - V-R: the regional SWS check (E128 rules).

  It is to be frozen in a separate protocol when the owner asks.
- **Rules:** the CPI-based predictors may be used; the references never enter training; no reference value is copied across provinces.

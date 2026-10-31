# E130 provincial target-validity audit (the gate before any training)

## Decision

**BLOCKED for quarterly provincial training.** No candidate target passes the frozen gate G1–G8 (protocol §1).

| Product | Status |
|---|---|
| Quarterly provincial food-insecurity model (LightGBM regression, Leads 1–4) | **Not authorized.** There is nothing quarterly and provincial to learn from or score against. |
| PFDR v1 (PSA provincial subsistence incidence) | **Valid as a survey-year provincial reference.** It passes G1, G2 and G4–G7, and fails G3 and G8. |

PFDR v1 supports cross-sectional and round-to-round checks and the E130 survey-year seal. It never supports a quarterly label.

**The gate was checked twice:**
- at the freeze (`out/gate.json`);
- after the new-data search (`out/gate_recheck.json`).

The search found that PSA has published a 2025 provincial round (candidate C12). It is not obtainable automatically, and with it there are still only 3 rounds, so **the result is unchanged**.

## Gate results

Each cell shows whether the candidate passes that criterion.

| Id | Candidate | G1 construct | G2 5 provinces | G3 ≥ 10 periods | G4 dated | G5 held | G6 not from predictors | G7 numeric ± SE | G8 quarterly Lead 2 | Fails |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | PSA subsistence incidence (PFDR v1) | yes | yes | no (2) | yes | yes | yes | yes | no | G3, G8 |
| C2 | FNRI ENNS 2021 FIES | yes | no (2) | no (1) | yes | yes | yes | yes | no | G2, G3, G8 |
| C3 | FNRI 2022 ENNS FIES | yes | no (unverified) | no (1) | yes | no | yes | yes | no | G2, G3, G5, G8 |
| C4 | CBMS 2024 FIES (142 LGUs) | yes | yes | no (1) | yes | no | yes | yes | no | G3, G5, G8 |
| C5 | SWS Balance Luzon hunger | yes | no (regional) | yes (20) | yes | yes | yes | yes | no | G2, G8 |
| C6 | SWS microdata with province codes | yes | yes (≈ 20–75 resp.) | yes | not established | no | yes | no (precision) | yes (in principle) | G4, G5, G7 |
| C7 | NNC Operation Timbang Plus | no (undernutrition) | yes | no (5) | yes | no | yes | no | no | G1, G3, G5, G7, G8 |
| C8 | PSA FIES 2023 food share | no (proxy) | yes | no (1) | no | yes | yes | no | no | G1, G3, G4, G7, G8 |
| C9 | Composite C1 + C2 (+ C8) | no (mixed) | no | no | yes | yes | yes | no | no | G1, G2, G3, G7, G8 |
| C10 | Provincial food CPI YoY | no (price) | yes | yes (23) | yes | yes | **no** (it is a predictor) | no | yes | G1, G6, G7 |
| C11 | FIRI3 / FIRI v2 scores | no (index) | yes | yes | yes | yes | **no** (built from predictors) | no | yes | G1, G6, G7 |
| C12 | PSA subsistence 2025 round (search) | yes | yes | no (3 rounds) | yes | **no** (bot check) | yes | yes | no | G3, G5, G8 |

## The eight validity questions (brief §2.4)

| Question | Answer |
|---|---|
| What does the score measure? | The share of the population whose per-capita income is below the provincial food threshold (the cost of a basket meeting minimum food needs) |
| Household food insecurity, food deprivation, or a constructed estimate? | **Measured food deprivation (income-based).** It is an official PSA measurement. It is not *experienced* food insecurity (FIES) and not an index built from predictors. |
| What official observations support it? | PSA FIES-based poverty statistics. **2021 and 2023 are held** (published 2024-08-15). **2025 is published** (released 2026-08-21, updated 2026-10) **but not held.** |
| How often is it observed? | Every two years (FIES survey years) |
| How many genuinely independent observations? | **10 held** (5 provinces × 2 rounds), giving **5 independent changes**. 15 values once the 2025 round is obtained. 0 quarterly. |
| Can it be evaluated at provincial level? | Yes, across provinces in a round and across rounds per province, with published CVs |
| Can it support quarterly forecasting? | **No.** One value per province every two years cannot label quarters, and spreading annual values over quarters would manufacture observations. |
| How can its values be independently validated? | Against FNRI FIES (Batangas, Cavite 2021; CIs overlap) and against CBMS 2024 LGU FIES (not held). The PSA food share of expenditure (2023) does **not** order provinces the same way (Spearman −0.20). |

## Keeping the four things apart

| Category | E130 examples | Used as |
|---|---|---|
| Measured household food insecurity | FNRI FIES; CBMS FIES; SWS hunger (regional) | Cross-checks (FNRI); regional reference (SWS); not held (CBMS) |
| Provincial food-deprivation measurement | PSA subsistence incidence (PFDR v1) | Survey-year reference and seal target |
| Constructed provincial risk score | FIRI3, FIRI v2 | Never a target (circular) |
| Food-price conditions | Provincial food CPI, retail and wholesale prices | Predictors only (owner) |

## What would make a quarterly provincial target valid

| Requirement | Why | Source that could meet it |
|---|---|---|
| A food-insecurity measure observed **separately for each province every quarter** | G2, G3, G8 | None exists. Options: SWS microdata with province codes (about 20–75 respondents per province-round, too noisy alone), or a new quarterly FIES-8 module |
| **At least 10 target quarters and 40 rows** (N1), and in practice **20–40 quarters** for a reliable pass (planning simulation, `E130_SCORE_AGREEMENT_ANALYSIS.md`) | N1, N2, N4 | Only prospective collection, from 2027 onward |
| A sampling SE about the size of the true quarter-to-quarter variation in provincial risk | Too precise and the 75 % tolerance is unreachable; too noisy and smoothing passes the rules without real forecasting | A designed survey, for example ≈ 300 households per province per quarter (SE ≈ 2.6 pp at 30 % prevalence) |
| Predictors that explain **≥ 50 %** of the true two-quarter change | The simulation's pass condition | Not shown for any trigger group so far. E79's best trigger variant explained 6 % of the regional direction of change. |

## Alternative for owner approval

`E130_FINAL_RECOMMENDATION.md` §3 sets out four alternatives (A–D). None of them claims a validated quarterly provincial forecast.

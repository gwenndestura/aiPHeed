# E116: why the FIRI indicators do not contribute, and what they can contribute

| | |
|---|---|
| Protocol | `PROTOCOL_E116.md`, frozen bcfa178 before any fit |
| Branch | `aiPHeed/e115-mean-reversion-prospective` (local only; E115 itself is suspended, no forecast issued) |
| Runner | `runner/run_e116.py`, seed 114 |
| Data | `runner/collect_regional.py` (PSA OpenSTAT, fetched 2026-10-30) |
| Outputs | `out/e116_results.json`, `out/e116_rows.csv` |
| Unchanged | served model, dashboard, API, map colours, E114 results |

**Analysis fix (disclosed).** The first scoring passed the error difference to E114's test helper with the wrong sign, which inverted the one-sided p-values and Holm values. It was found on reading the output. It was fixed and recomputed from the saved predictions with no refit (`run_e116.py --eval-only`; noted in `e116_results.json`). Point estimates, CIs, permutation and SHAP were unaffected.

## 1. Bottom line

**What the data show.**
- **Only one domain adds information on hunger itself.** With area-level data and an explicit test of each domain on the observed hunger outcome, only **fish production at Lead 1** passes the frozen rule. The gain is small: −0.77 MSE (90% CI −1.41 to −0.19), Holm p = 0.074, on a base MSE of about 27, and it has the same sign on the test period.
- **No domain adds information at Lead 2.**
- **Adding all domains does not beat hunger history alone** at either lead, in development or test.
- **Market prices helps strongly in 2021-2026 only:**
  - Lead 1: −6.7 MSE, Holm 0.019.
  - Lead 2: −5.9 MSE, Holm 0.025.
  - That period was inspected in earlier experiments, so this is a lead, not proof. It appears only in the recent inflation regime.

**Why the indicators fail on SWS hunger.**
1. **Survey noise.** The outcome is dominated by hunger's own dynamics and by survey noise (Balance Luzon ±4 pp).
2. **Resolution.** Several indicators exist only nationally (ONI, typhoons, unemployment, rice CPI) or only annually or recently (provincial employment, OFW, news, poverty).
3. **Data vintage.** Pre-2018 CPI is a 2018=100 back-cast, not the values published at the time.
4. **Overfitting.** Adding the domains halves training error (MSE 19.2 → 15.5) but leaves test error unchanged or worse.

**Recommendation (§6).** Keep all 12 indicators in the system, but say plainly what each does. The defensible forecasting claim is a regional hunger level outlook. Fish production adds a small Lead-1 gain. Market prices is a candidate driver in the current regime, to be confirmed on prospective quarters. No domain is claimed as a Lead-2 driver.

## 2. Phase 1: why the model leaned on SWS history

| Cause | Measured evidence |
|---|---|
| Target dynamics | Hunger history alone (V1) beats persistence by −7.6 MSE at Lead 2 in development, −4.9 in test, −11.5 in 2021-26. Permuting hunger history raises MSE by +21 (development) and +6.8 (test). This is mean reversion around a slowly moving level. |
| Resolution (E114) | E114 used national covariates: one value per quarter for all four areas. E116 replaced market, fish and palay with area-level series. Market, fish and palay inputs now vary between areas. Their test-period contribution is still not established. |
| Coverage | News exists only from 2018 (0% of development rows, 31% of test rows). OFW remittances exist only from 2021 in the repository; BSP blocks automated access (HTTP 403, not circumvented). Poverty has no dated time series. Owner-supplied provincial employment is annual, 2021-25. |
| Data vintage | CPI before 2018 is PSA's back-cast to 2018=100 (table 0012M4ACP28), not as published. Fisheries and palay values are final revisions. |
| Overfitting | Training vs test MSE (Lead 1+2): base 19.2 vs about 33; ALL5 15.5 vs about 35. The extra domains fit the training period better and the future worse. |
| Feature redundancy | ONI, typhoons, unemployment and rice CPI are national. Within any quarter they act like time markers shared by all four areas. |
| Target (T43c) | T43c's price component is computed from the same provincial CPI as A1/A2. A market "contribution" there would be the target predicting itself, so T43c was not used. |

## 3. Phase 2: can a broader food-insecurity target be supported?

| Candidate | What exists | Supports |
|---|---|---|
| SWS Total Hunger | 1998-2026, quarterly, 4 areas | **regional quarterly forecasting** (experienced hunger only) |
| FNRI FIES (ENNS 2021; NNS 2023) | ENNS 2021: Batangas, Cavite, Lucena. NNS 2023: Region IV-A 19.1% | cross-sectional validation of a provincial profile; not a time series |
| CBMS 2024 FIES | one 12-month window, barangay/municipal; not in the repository (request never sent) | cross-sectional validation |
| PSA subsistence incidence | provincial 2021 and 2023 | vulnerability profile; 2 observations per province |
| PSA FIES (Family Income and Expenditure Survey) 2023 | no food-insecurity items | not a target |
| Production statistics | fish, palay | predictors, not outcomes |

**Conclusion.** No official source gives a time-varying provincial food-insecurity outcome. The most defensible combination is:
- **regional quarterly hunger forecasting**, using SWS hunger by area;
- **a provincial vulnerability assessment**, with indicators as descriptors, validated cross-sectionally against FIES or CBMS where available.

No target was built from the predictors, and no regional reading was split into provincial outcomes.

## 4. Phase 3: the 12 FIRI indicators

| Code | Indicator | Domain | Long-history test (E116) | Geography | Coverage | Availability | Measured contribution (DEV → TEST) |
|---|---|---|---|---|---|---|---|
| A1 | food-price pressure | Market | area food CPI YoY, food-minus-headline, its change | area (unweighted regional mean) | 1995-2026 | day 10 after month | not established (L1 +1.4 → +2.2; L2 −0.3 → +1.2); **2021-26: −6.7 / −5.9** |
| A2 | headline inflation | Market | (in the food-minus-headline gap) | area | 1995+ | day 10 | as A1 |
| A3 | rice price | Market | national rice CPI YoY | national | 1995+ | day 10 | as A1 |
| C1 | El Niño | Climate | ONI, El Niño flag | national | 1950+ | day 10 | not established |
| C2 | typhoons | Climate | PAR count change | national | 1996+ | quarter end | not established |
| C3 | palay/corn drop | Climate | area palay YoY (t−1) | area (no NCR) | 1987+ | assumed t−1 | not established |
| C4 | fisheries drop | Fish | area fisheries YoY (t−1), its change | area | 1993+ | assumed t−1 | **adds information at Lead 1** (−0.77 → −0.16); a later lag gives test −1.10, p 0.031. Not at Lead 2. |
| E1 | unemployment | Employment | national unemployment change | national | 2005+ | m+3 | not established |
| E2 | OFW remittances | Remittances | **not testable**: no long series in the repository; BSP 403 | national | 2021+ only | — | unknown |
| N1 | news (FSSI) | other input | GDELT supply/assistance | national | 2018+ | quarter end | adds nothing (FULL vs ALL5: test +1.3) |
| V1 | poverty/density | other input | none time-varying | province | static | published 2024-25 | not representable |
| H1 | hunger outlook | target history | h_last, MR, d_last, staleness | area | 1998+ | SWS release | the only consistent source of skill |

**Domain additions (Δ MSE vs base, area-pooled, 90% quarter-block CI, Holm across 4):**

| Domain | L1 DEV | L1 TEST | L2 DEV | L2 TEST | L2 2021-26 (inspected) |
|---|---|---|---|---|---|
| Market | +1.41 [−1.21, +4.26] | +2.20 [+0.64, +3.88] | −0.27 [−3.11, +2.67] | +1.15 [−0.87, +3.06] | **−5.88 [−9.41, −2.71]**, Holm 0.025 |
| Fish | **−0.77 [−1.41, −0.19]**, Holm 0.074 | −0.16 [−1.02, +0.68] | −0.40 [−1.49, +0.61] | −0.22 [−1.09, +0.67] | +0.76 [−0.59, +2.18] |
| Climate | −0.45 [−1.84, +0.97] | +0.33 | −0.74 [−2.50, +0.99] | +1.75 [−1.09, +4.57] | +2.35 [+0.41, +4.77] |
| Employment | −0.31 [−1.40, +0.72] | +0.79 | +0.10 [−0.84, +1.07] | +0.56 | +1.33 |
| All domains (ALL5) | +0.20 | +2.68 | +0.40 | +1.99 | −1.23 |
| ALL5 + news (FULL) | +0.20 | +4.06 | +0.40 | +3.26 | +3.98 |

**Interactions.**
- **Products** (market × employment, fish × climate, climate × market) add nothing: |Δ| ≤ 0.6 in development and test. They slightly worsen 2021-26.
- **Unconstrained vs no-cross-domain LightGBM:** +0.2 to +0.7 in development, −0.1 to −0.2 in test. Cross-domain interactions carry no measurable signal.
- **Not testable:** price × poverty and employment × OFW, because the data do not exist over time.

**Inclusion vs SHAP vs contribution.**
- In the ALL5 model, market inputs receive a mean |SHAP| of 1.27, against 3.28 for hunger history. Yet permuting them *raises* error in development (+1.1) and *lowers* it in test (−0.4).
- **Large SHAP here is not predictive value.**

**Generalization.**
- **Leaving each area out:** ALL5 vs base is −1.9 (development) and +2.9 (test) at Lead 1, and −1.1 / +1.3 at Lead 2. Not established.
- **"Above usual" classification:** no domain set improves the Brier score over persistence (Lead 2 test: ALL5 0.257, base 0.249, persistence 0.243).
- **Simple models:** damped mean reversion beats every LightGBM variant in test (Lead 2: 27.0 vs 32.9-36.2), but not in development or 2021-26.

## 5. What would change these results

1. **A long OFW remittance series.** BSP OFW cash remittances, monthly from 1989: a manual download from bsp.gov.ph. Without it, the remittance domain cannot be evaluated at all.
2. **Release dates and as-published vintages** for CPI (pre-2018), fisheries and palay. These replace back-cast and revised values.
3. **Regional quarterly labour-force data** (PSA LFS by region). Employment is national-only on OpenSTAT; the owner's provincial file is annual for 2021-25. Saved in `data/owner/` with provenance. Not used here, because it arrived after the freeze.
4. **Prospective quarters** to confirm whether the 2021-26 market effect holds. That period cannot be used as independent evidence.
5. **A provincial outcome** (CBMS FIES, or repeated FNRI rounds) before any provincial forecasting claim.

## 6. Justified recommendation (nothing integrated)

1. **Keep all 12 indicators and five domains in the dashboard, labelled honestly:**
   - hunger history drives the regional outlook;
   - fish production adds a small Lead-1 improvement;
   - market prices is a *candidate* driver in the current regime;
   - climate, employment, news and poverty are monitored context with no established forecast value;
   - OFW is not yet testable.
2. **Forecasting claim:** a regional (Balance Luzon) hunger level outlook at Lead 1. Lead 2 is not supported by any domain.
3. **Provincial layer:** vulnerability and price-pressure profile, labelled as such. It could be validated cross-sectionally against FNRI or CBMS FIES.
4. **Next experiment (needs your go-ahead):**
   - a pre-registered model with base + fish + market, scored prospectively on new SWS rounds;
   - add OFW once the BSP series is supplied.

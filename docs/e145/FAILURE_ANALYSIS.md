# Why earlier aiPHeed methods kept failing

**Evidence base:** the experiment records E9 to E143, the FI5 to FI12 studies, and the C-B6 family. Each root cause below is tied to a measured result. Where the same number appears in several records, the latest locked record is cited.

## 1. What was tried

| Family | Experiments | Target | Best out-of-sample result | Why it stopped |
|---|---|---|---|---|
| Price-pressure indices | CH1, P0H4, P0H4-U, FORECAST_RESEARCH, LEAD2 series | Food-price risk | Lead 1 accuracy 0.914; Lead 2 0.800 | A food-price target, not food insecurity. Compliance audit 11-04 records this |
| Composite indices | FIRI v1, FIRI v2, FIRI3 (E120 to E127), PFI | Constructed index | FIRI v2 served live; PFI v1.0 rejected | The model learns its own proxy. FIRI v2 labels all five provinces HIGH |
| SWS hunger, one area | E9 to E17, E23 to E35, E109 to E113, FI5 to FI9, C-B6 (about 29 attempts) | Balance Luzon hunger, quarterly | C-B6 accuracy 0.806, with a 0.694 base rate; persistence probability Brier 0.199 against C-B6 0.183 not proven different | Regional target; same 62 quarters reused; no provincial skill |
| SWS change labels | FINAL_FI_LIGHTGBM, E96, E98 | Hunger above recent mean | 0.32 to 0.55 accuracy | Simulated ceiling 0.58 to 0.64, so 75 % is out of reach |
| SWS hunger, four areas with news | E144-P2 | Area hunger above its 20-quarter mean | Accuracy 0.633 at lead 1; ECE 0.246 | Fails calibration; always-HIGH scores 0.70; no news gain |
| Provincial HFIAS | hfias-1.0, E137 to E143 | Measured provincial HFIAS, relative to national | C4 accuracy 0.903, AUC 0.984 on decisive rows | Does not beat persistence or the region's previous level after Holm; skill is about place, not time |
| Other provincial routes | FI12, OPT-1 | Provincial outcomes | OPT-1 reliable to 3 years on stunting | Stunting is not food insecurity: validity check failed |

## 2. Root causes

### RC1. There is no province-quarter food-insecurity measurement

Across all years, CALABARZON has **13 measured HFIAS province-rounds** (NNS 2013: 5, FNRI 2015: 5, ENNS 2018: 1, ENNS 2019: 2) and **4 FIES province-rounds** (ENNS 2019: Quezon, Rizal; ENNS 2021: Batangas, Cavite), plus Lucena City 2021. HFIAS and FIES differ in items and recall (30 days against 12 months), so they are not one series.

**Correction:** an earlier version said the HFIAS series ends in 2019. FNRI's Heat Map shows HFIAS continued through ENNS 2021, so 2021 HFIAS rows exist for Batangas and Cavite. See `docs/e147/DATA_INVENTORY.md`.

The quarterly target the objectives ask for has never been observed for any province, so a direct province-quarter accuracy cannot be computed.

Every "province-quarter accuracy" in earlier work was accuracy on something else: a regional number, a proxy, or a survey round.

### RC2. In CALABARZON, the HIGH class has never been measured

Of the 13 rows, **0 are ELEVATED**, 8 are LOWER and 5 are not distinguishable from the national level (Quezon 2013, 2015 and 2019; Rizal 2013 and 2019). So:

* High-risk recall for CALABARZON is undefined.
* Always saying LOW is correct on every decisive CALABARZON row.
* Any model reporting recall on these provinces under a national reference has no positive case to detect.

FIES tells the same story. All 4 FIES province-rounds are below the national point estimate (Quezon 32.2 and Rizal 38.4 against 44.2 in 2019; Batangas 29.7 and Cavite 31.7 against 33.4 in 2021, with Cavite's interval including the national value). In 2023 CALABARZON is the lowest region, at 19.1 % against 31.4 %.

A caution on the owner workbook (`sheet_ENNS_Provincial.csv`): its 2018 and 2019 "moderate-to-severe" values are HFIAS *moderate only* (Laguna 18.3, Rizal 27.5, Quezon 30.3), while its 2021 values are FIES moderate-or-severe. The HFIAS moderate-or-severe values are 26.2, 39.1 and 44.0. The columns cannot be compared as printed.

This is why provincial accuracy looks high and means little here.

### RC3. Too few independent time points

The panel has 203 province-rounds, but only four survey rounds. Rolling evaluation has **three origins**. Provinces within a round share the round's national conditions, so a time signal is identified only by a handful of contrasts.

E144's link coefficient shows this directly. It passes its locked test (γ interval 0.14 to 0.40), but it is identified from **12 area-round cells**. Resampling those cells gives an interval of −0.04 to 0.59, and dropping single rounds or areas moves γ between 0.15 and 0.65.

### RC4. Literature gains rest on data of a different size

Balashankar et al. (2023) had about 1,160 districts, each classified 3 to 4 times a year for 11 years, against 203 provincial rows here. Foini et al. (2023) show skill depends on the number of past observations. Roughly two orders of magnitude separate aiPHeed from the settings where news helps.

The IPC phases in those studies are not direct measurements. They are analyst consensus classifications, and evaluations often score against the same system's later assessments (Bertetti et al., 2024). Those studies also lack an exact, frequent, directly measured label. What they have is a frequent, accepted, subnational classification, which has no equivalent for CALABARZON. Survey-based studies (Lentz et al., 2019; Zhou et al., 2021; Kopp et al., 2026) face aiPHeed's sparsity directly and validate only where a survey measured the outcome.

### RC5. "Where" was mistaken for "when"

* E140's LORO AUC of 0.96 falls to 0.70 within Luzon, because it mostly separates island groups.
* OPT-1 has an AUC near 0.96 but a change correlation of −0.06 to 0.21.
* Between-province differences persist, so any model with poverty or last-survey inputs looks strong on accuracy. On E144's end-to-end rows, persistence of the previous round reaches accuracy 0.863, against 0.853 for the full chain.

The literature shows the same trap. A no-change rule reaches about 76 % against 78 % for FEWS NET (Bertetti et al., 2024). Separating easy from hard cases is the point of Mueller and Rauh (2022).

### RC6. News was tested where it could not work

| Test | Result |
|---|---|
| FSSI in C-B6 | Changes 0 of 62 forecast calls |
| FI6-N, 7 features, in C-B6 | Worse: Brier +0.013 and +0.024 |
| FI6-N alone, lead 1 with complete news | Brier −0.0099, significant; no class changes; AUC 0.70 to 0.77 |
| CALABARZON shock signal | Worse; unrelated to hunger change (ρ −0.05) |
| Four-area Google News, E144 | No gain at any horizon; Holm-corrected, p from 0.20 to 0.55 |

Provincial news was never compared with a provincial outcome, because FSSI covered only 5 of the 78 surveyed provinces. E145 closes this gap. Also, sentiment accuracy has never been measured locally, since the owner ruled out the 200-article annotation sample.

### RC7. Lead time was defined inconsistently

CH1's "Lead 1" was the issue quarter, which made the real target quarter its Lead 2 (accuracy 0.769, recall 0.35). v13 forensics recorded that Lead k meant k + 1 quarters. Reported lead-time claims from those experiments do not match the convention in this mission.

### RC8. Test data was reused

The same 62 SWS quarters have seen about 29 model attempts. The 2019-20 out-of-time window is marked spent. Every HFIAS round has now been seen. The only remaining unbiased evidence is a round no model has seen, such as ENNS 2021 provincial decks, or sealed forecasts scored later.

### RC9. Some inputs carry no provincial or quarterly signal

* E1 and E2 are national, so they cannot separate provinces.
* Palay, CPI and climate features add little to measured HFIAS ("no feature explains the residual", E140).
* FI9-R and FI8 found survey noise blocks gains over persistence on SWS.

## 3. Answers to the mission's specific questions

| Question | Answer |
|---|---|
| Does the target represent food insecurity? | Price indices and FIRI do not. SWS hunger and HFIAS do |
| Is the target too disconnected from predictors? | For HFIAS levels no; for changes between rounds largely yes. 40 % of change variance is survey error (E143) |
| Is label frequency sufficient? | No (RC1, RC3) |
| Is temporal alignment wrong? | It was for CH1. E137 onward use release dates; survey fieldwork timing remains approximate |
| Is the forecast horizon wrongly defined? | Was, in CH1 (RC7). Fixed in E137 onward and here |
| Is validation too restrictive or invalid? | Neither. It is correct, but the data allow only three origins |
| Are observations too few? | Yes (RC3, RC4) |
| Does news processing lose information? | Partly. Excerpts only, and one main outlet |
| Is province information discarded? | Yes in every regional model, where province risk was regional risk times a weight |
| Are features redundant? | Yes. Poverty measures and last-survey values overlap |
| Do training and evaluation distributions differ? | Yes. SWS base rate rose from about 0.42 to 0.70 in 2022 onward, which breaks calibration; round shifts appear in HFIAS (53.8 to 42.8 reference) |
| Is the methodology structurally unable to reach the objectives? | With today's data, a verified province-quarter 75 % claim cannot be made under any method (RC1). See the final report |

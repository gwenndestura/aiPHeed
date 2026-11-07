# E180: target validity

## What E168 predicts (VERIFIED)
P(the province's share of households with **moderate or severe** food insecurity, DOST-FNRI HFIAS, is >= 50 % in the target quarter).
`app/e147/features.base_rows` calls `outcomes("insecure")`, but its values equal `mod_sev_pct` exactly (max |diff| 0.0) and differ from
"any food insecurity" by up to 26.7 points (LOW naming issue I14). HIGH prevalence in the label rounds: NNS 2013 69 %, FNRI 2015 69 %,
ENNS 2018 36 %, ENNS 2019 52 %; the 72 evaluation rows are 25 HIGH / 47 LOW.

## Is it food insecurity? Yes, at survey-round, province level
HFIAS is a direct household food-insecurity experience scale. This is a genuine food-insecurity target, **not** food prices, SWS hunger
or a composite. SWS Balance Luzon is **not** E168's target: it enters only the temperature-shrink step. Balance Luzon covers all of Luzon
outside Metro Manila and is not a CALABARZON or provincial measurement. The **frontend still describes the retired SWS/price target**
(I03); that text is incorrect for E168.

## What the target cannot support
- **No provincial-quarter ground truth.** Provincial HFIAS exists only for survey rounds (2013, 2015, 2018, 2019, 2021, with reference
  quarter Q3 assumed). The 16 dashboard quarters 2023-Q1 to 2026-Q4 are back-forecasts with no outcome; 2027-Q1 is sealed (28f2c918)
  and has no scheduled provincial HFIAS outcome.
- **Validation is survey-round-level.** 72 province-rounds per lead (22 + 25 + 25), about 45.5 effective after shared-error correction.
- **Comparability.** NNS 2013 and FNRI 2015 (anchors) and ENNS 2018-2021 are all HFIAS; FIES rows (2021 decks, 2023 NNS, 2025) are a
  different instrument and are correctly excluded from the target.

## Claims supported
"E168 forecasts, one to three quarters ahead, whether a province's HFIAS moderate-or-severe food insecurity will be at or above 50 %,
validated retrospectively on 72 DOST-FNRI province-rounds (2018-2021)."

## Claims to qualify or remove
- "Quarterly provincial food-insecurity forecasts" → qualify: quarterly issue, survey-round validation; between-survey quarters are unverified.
- Any SWS / price-pressure definition of the target on the dashboard → remove for E168.
- Municipal (LGU) values → a vulnerability-weighted ranking of the province probability (Algorithm 5), not municipal forecasts.

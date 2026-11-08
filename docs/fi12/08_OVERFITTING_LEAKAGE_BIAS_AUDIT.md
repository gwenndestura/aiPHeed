# Deliverable 8. Overfitting, leakage and bias audit

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

| # | Risk | Where | Finding | Impact |
|---|---|---|---|---|
| 1 | Publication year used as reference year | matching | Not done: reference years only; ENNS by province-specific year | — |
| 2 | Future information | matching, baselines | Every forecast issued before its target quarter (asserted); baselines use values available by 1 Jan of the reference year under a conservative rule | — |
| 3 | Regional SWS copied to provinces | P0H4 family | P0H4's hunger term is one Balance Luzon value for all provinces; provinces differ only through price | P0H4 cannot express provincial food-insecurity differences except through price |
| 4 | National series copied to provinces | FIRI C1, E1, E2, H1, N1 | No provincial variation | They cannot rank provinces |
| 5 | Contemporaneous poverty as a predictor of subsistence | baselines | Avoided: poverty and subsistence come from the same FIES; only prior waves are used | Using same-year poverty would leak the outcome |
| 6 | Workbook transcription | ENNS | 10 records secondary and unverified; compiled with an AI assistant; severe vs moderate-to-severe ρ −0.1 within one survey | ENNS treated as descriptive only |
| 7 | Instrument change | FNRI 2015 (HFIAS) vs later FIES | Severe 17–21 % (2015) vs 1.5–2.4 % (ENNS 2021) and 1.7 % (2023 regional) | Not comparable across waves; never pooled |
| 8 | Province definition | Quezon | PSA excludes Lucena; FNRI/ENNS unknown | Possible mismatch, unverified |
| 9 | Multiple comparisons | P0H4 family on PSA 2023 | ~40 model × lead cells on five values | Best p ≈ 0.07 expected by chance |
| 10 | Overfitting | level model L4 | Ridge trained on five rows is the worst level candidate | Confirms that a provincial model cannot be trained on these data |
| 11 | Selection on test data | all | Candidates, metrics and decision rules locked before scoring; one smoke test on randomised values only; no re-lock | — |
| 12 | Province bias | FI10 | Quezon (highest food poverty 2018/2021) has the lowest price pressure; price models systematically under-rank it | Price-driven maps under-prioritise the poorest province |
| 13 | FI10 configuration selected on a period including 2015 | FI10 | Selection used price labels to 2015, not FNRI labels | Small; disclosed |

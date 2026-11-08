# E106: simple aiPHeed methodology. Pre-registered protocol

**Date:** 2026-10-23. **Branch:** `aipheed/simple-methodology` from `main` @ `0239273`. Production code paths, E100–E105 artifacts and every sealed file are unchanged and hash-checked by the runner. New outputs: `backend/data/simple_method/`.
**Freezing:** this file is hashed (`runner/PROTOCOL_SHA256.txt`) before any model below is scored.
**Requirement basis:** Chapter I of `THESIS 2 (11).pdf` (13 Oct 2026): General Objective, Specific Objectives 1–5 (§1.5.2), Scope (§1.7). Chapter I sets no accuracy threshold; the 75% target comes from the user's brief and is reported as a target, not as a Chapter I criterion.

**Already examined (disclosed):** the served E56 / FIRI v2 results; E100–E104 (all retrospective quarters seen). **Development evidence only.** E105's protocol (frozen 12:41 UTC) was never scored; its MA2 and AR1D hunger models are scored here as pre-registered alternatives.

## 1. Target (Chapter I §1.7: SWS hunger and PSA food prices determine risk)

Province p, quarter q: **HIGH** if Balance Luzon SWS involuntary hunger (mean of all rounds of q) > 11.3% **and** the province's food price condition holds: food CPI YoY F(p, q) > the province's 2021–22 P60, or F(p, q) − headline YoY HL(p, q) > the province's 2021–22 P60 gap (the frozen E40 thresholds, `E40_SWS_CPI_Tiers/label_spec.json`). F from `backend/data/inputs/d_quarterly_panel.csv` (the served quarterly food YoY); HL from `backend/data/processed/cpi_full.parquet` (`year >= 2021`; the only headline series in the repository). A row is unlabelled when any part is missing (never LOW by default). Agreement with the served T43 labels (E58 record, 2024-Q2..2026-Q3) is reported.

## 2. Features at origin t (issue = day 1 of quarter t + 1), only published information

| Feature | Meaning | Source, rule |
|---|---|---|
| F_last | province food YoY, quarter t − 1 | d_quarterly_panel |
| RICE | wholesale rice YoY, t − 1 vs t − 5 | served FIRI history raw A3 |
| UNEMP | national unemployment-rate change | served A-history raw E1 |
| ELNINO | PAGASA El Niño alert/advisory in force (0/1) | served raw C1 |
| HARVEST | larger of the palay/corn production drops | served raw C3 |
| NEWS | FSSI-v3 of the province (missing if < 5 articles) | served raw N1 |
| H_last | latest SWS quarter value posted before the issue (all rounds) | sws_rounds.csv |

## 3. The method (primary, "SM")

P(HIGH) = **P_hunger** × **P_price**.
- **P_hunger** (regional, no training): 1 − Φ((11.3 − H_last) / σ), σ = RMSE of the same rule's earlier Lead-L errors posted before the issue (≥ 4, else 4.0).
- **P_price** (provincial): LightGBM classifier on the price condition of quarter t + L, features F_last, RICE, UNEMP, ELNINO, HARVEST, NEWS. Fixed configuration, not tuned: 100 trees, learning_rate 0.05, num_leaves 4, max_depth 2, min_child_samples 5, reg_lambda 5, deterministic, seed 106. Trained at every origin on rows (p, t′) whose price label for t′ + L is complete before the issue (t′ + L ≤ t − 1); fewer than 10 rows or one class → the training share.
- **Class:** HIGH if P(HIGH) ≥ 0.5. **Region:** mean of the five provinces. **LGU:** the existing ranking (`app.quarterly.lgu_audit.build_ranking`: province probability × (0.6 poverty + 0.4 density), within province). **Explanation:** TreeSHAP of P_price grouped by trigger (market: F_last, RICE; employment: UNEMP; climate: ELNINO, HARVEST; news: NEWS), with the hunger part shown separately.
- Lead 1 and Lead 2 (and Lead 3 for Objective 2-V) use the same procedure with L = 1, 2, 3.

## 4. Comparison arms (same rows)

| Arm | Definition |
|---|---|
| SM-1 | one LightGBM classifier directly on the target, all seven features, same configuration; training rows need the full target label known before the issue |
| SM[MA2], SM[AR1D] | SM with the E105 MA2 or AR1D hunger rule in place of persistence (E105 definitions) |
| E56 (production) | the served LightGBM's sealed P(HIGH) (`E63_Lead_Time_Study/sealed/predictions.csv`, E56_p), scored on this target |
| Persistence | the province's latest target label known at the issue (Objective 4-I) |
| PSA-only | logistic regression (L2, C = 1, standardised, training-window median imputation) on F_last, RICE, UNEMP (Objective 4-II) |
| NLP-only | logistic regression on NEWS and a NEWS-missing flag (Objective 4-III) |
| Logistic | logistic regression on all seven features (Objective 4-IV) |
| Majority, Climatology | training majority class; training HIGH share |

## 5. Evaluation

Rolling origin, expanding window. Evaluation targets: Lead 1 2023-Q4..2026-Q3, Lead 2 2024-Q2..2026-Q3, Lead 3 2024-Q3..2026-Q3 (the production model's sealed range), labelled rows only; every arm on the identical rows. Metrics: accuracy (Wilson CI), balanced accuracy, precision / recall / F1 for HIGH and LOW, AUC-ROC, Brier, confusion matrix, share predicted HIGH; per target quarter. Paired comparisons by quarter (sum of province Brier differences per quarter; bootstrap 95% CI over quarters, 2,000 draws, seed 2026; exact sign-flip permutation p). Secondary: regional mean P(HIGH) vs the regional SWS outcome (hunger > 11.3).

## 6. Decision rules (fixed now)

- **Reliable at lead L:** accuracy > 0.75, above Majority and Persistence, HIGH recall ≥ 0.5, LOW recall ≥ 0.5, AUC > 0.5, share predicted HIGH between 0.1 and 0.9. Furthest reliable lead = the largest L meeting it (Objective 2-V).
- **Hunger part:** persistence stays unless MA2 or AR1D gives a lower Lead-2 Brier with permutation p < 0.10.
- **SM vs SM-1:** SM is primary; SM-1 replaces it only if SM-1's Lead-2 Brier is lower with permutation p < 0.10.
- **Better than production:** Lead-2 Brier lower than E56 with permutation p < 0.10 and accuracy not lower.
- **Prospective:** seal SM's Lead-1 2026-Q4 and Lead-2 2026-Q4 / 2027-Q1 forecasts.

## 7. Not done

No pre-2021 data, no new data, no tuning, no synthetic outcomes, no change to the served FIRI / E56 code paths or the deployed configuration, no push.

# E91: one unified food-insecurity risk model with an empirically determined horizon K (report)

**Directive.** "E90: Develop One Unified Food Insecurity Forecasting Model With an Empirically Determined K-Quarter
Horizon". Numbered E91 because E90 already exists.

**Branch.** `e91-unified-horizon-model`, from `e90-advanced-optimization` (contains e89). Not pushed. The production
branch `final-system-v2` is unchanged.

**Evidence.**
- Protocol: `PROTOCOL.md` + `PROTOCOL.sha256`, frozen at 3207938 before scoring.
- Deviations D1–D4: `DEVIATIONS.md`. Code fixes only, all made before any metric was seen or with no effect on
  reported numbers.
- Pre-registered run: `runs/20261022T045201Z/` (`metrics.json`, `predictions_k{1..4}.csv`).
- Post-hoc round 2: `round2_posthoc.json`, `predictions_round2_k{K}.csv` in the same folder.
- Seal: `sealed/e91_prospective.csv`.
- Tests: `backend/tests/integration/test_e91_unified_model.py`.

## 1. Answer

| Question | Answer |
|---|---|
| One unified model | **Yes.** At every origin a single model is trained on the pooled training pairs of all horizons, with the horizon K as an input, and issues the K = 1..4 forecasts. No horizon has its own model or its own selection. |
| Pre-registered architecture | **U-GB**: a LightGBM layer, conditioned on K, boosted from the structural risk core (hunger random walk × component price simulation). Lowest mean Brier on the 2023–24 selection block. |
| Maximum validated horizon K | **K = 0: no horizon is validated.** No candidate, and none of the earlier models, passes the unchanged PASS rule at any K. The post-hoc variants also give K = 0. |
| Closest horizon | **K = 1.** The structural core and U-GB fail only one criterion there: their Brier improvement over persistence and climatology is not statistically significant across the 13 test quarters (Holm p = 0.15–0.17). |
| Food insecurity or price pressure | The target is T43, a **proxy**: regional SWS hunger above 11.3% and provincial food-price pressure. Results are proxy-target performance, not validated food-insecurity prediction. |

## 2. The unified model

**Structural core.** It gives P(regional hunger > 11.3%) times P(provincial price condition) for any K:
- **Hunger:** a random walk from the last posted SWS round, with spread growing with the gap.
- **Prices:** simulated monthly paths of eight CPI food subgroups, the food residual and the headline CPI, with
  world-rice pass-through.

**Candidates.** All issue every horizon from one fitted model per origin:

| Candidate | Description |
|---|---|
| U-STRUCT | The core alone |
| U-CAL | Logistic calibration of the core, conditioned on K |
| U-LR | Logistic regression on the core plus all driver groups |
| U-GB | LightGBM boosted from the core: K, core logits and driver groups |
| U-GB-RAW | LightGBM on K and the driver groups, without the core |
| U-LR-RICE | Diagnostic only, not selectable |

**Driver groups:**
- market and prices;
- climate stress;
- agricultural supply;
- employment and remittances;
- hunger history;
- poverty (PSA SAE 2021, as published);
- news (tested as an added group).

**Leakage guards.**
- Every feature comes from `d.cut(t)`.
- Pooled training labels are posted before the origin; tested on three origins.
- Imputation and scaling use training rows only.
- The 0.5 threshold is fixed; nothing is tuned on test quarters.

**Architecture selection** (frozen rule: mean Brier over K = 1..3 on targets 2023-Q1..2024-Q4):

| Candidate | U-GB | U-STRUCT | U-GB-RAW | U-LR | U-CAL |
|---|---|---|---|---|---|
| Selection Brier | **0.1653** | 0.1694 | 0.1902 | 0.2187 | 0.2235 |

## 3. Horizon evaluation (selected U-GB; 65 rows per K, 16 HIGH; unissued rows count as wrong)

| K | Accuracy | Balanced | HIGH precision / recall / F1 | TP / FP / FN / TN | Brier | Calibration-in-the-large | AUC | Holm p vs persistence / climatology / always-HIGH | Failed criteria | PASS |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.785 | 0.689 | 0.57 / 0.50 / 0.53 | 8 / 6 / 8 / 43 | 0.140 | −0.088 | 0.83 | 0.146 / 0.164 / 0.001 | Brier not significant | **No** |
| 2 | 0.738 | 0.574 | 0.44 / 0.25 / 0.32 | 4 / 5 / 12 / 44 | 0.190 | −0.068 | 0.58 | 0.059 / 0.311 / 0.004 | accuracy, balanced accuracy, Brier, recall | **No** |
| 3 | 0.723 | 0.543 | 0.38 / 0.19 / 0.25 | 3 / 5 / 13 / 44 | 0.169 | −0.045 | 0.76 | 0.007 / 0.165 / 0.003 | accuracy, Brier vs climatology, recall | **No** |
| 4 | — | — | — | not issued | — | — | — | — | not computable (see below) | **No** |

**Why K = 4 is not issued.** The year-on-year comparison quarter for a target four quarters ahead is the origin quarter
itself, which is not yet published at the forecast date. So the structural core cannot compute K = 4.
- U-GB-RAW, which does not use the core, issued only 25 of the 65 K = 4 rows. It reached 0.08 accuracy with
  unissued rows counted wrong, against 0.23 on the rows it issued.

**Structural core alone (U-STRUCT, the same model at every K):**

| K | Accuracy | Balanced | HIGH recall | TP / FP / FN | Brier | Holm p vs persistence / climatology | Failed criteria |
|---|---|---|---|---|---|---|---|
| 1 | 0.815 | 0.709 | 0.50 | 8 / 4 / 8 | 0.141 | 0.171 / 0.171 | Brier not significant |
| 2 | 0.800 | 0.636 | 0.31 | 5 / 2 / 11 | 0.177 | 0.066 / 0.232 | Brier vs climatology, recall |
| 3 | 0.754 | 0.542 | 0.12 | 2 / 2 / 14 | 0.147 | 0.008 / 0.075 | recall |
| 4 | not computable | | | | | | |

**Baselines** (accuracy / balanced accuracy / Brier):

| K | Persistence | Climatology | Always-LOW | B-STATE | PSA-only LR | NLP-only LR |
|---|---|---|---|---|---|---|
| 1 | 0.723 / 0.627 / 0.277 | 0.754 / 0.500 / 0.208 | 0.754 / 0.500 / 0.246 | 0.738 / 0.616 / 0.262 | issues 30/65 | issues 30/65 |
| 2 | 0.646 / 0.555 / 0.354 | 0.754 / 0.500 / 0.219 | 0.754 / 0.500 / 0.246 | 0.708 / 0.575 / 0.292 | issues 25/65 | issues 25/65 |
| 3 | 0.569 / 0.441 / 0.431 | 0.754 / 0.500 / 0.225 | 0.754 / 0.500 / 0.246 | 0.646 / 0.513 / 0.354 | issues 20/65 | issues 20/65 |
| 4 | 0.646 / 0.513 / 0.354 | 0.754 / 0.500 / 0.225 | 0.754 / 0.500 / 0.246 | 0.569 / 0.399 / 0.431 | issues 20/65 | issues 20/65 |

**Earlier separate-lead models** (experimental baselines only):
- **S-SIM:** K1 0.846 / Brier 0.118, K2 0.692, K3 0.492.
- **S-COV:** K1 0.815, K2 0.800 / 0.177, K3 0.754.

Neither passes at any K. The E89 baseline figures were reproduced exactly from the artifacts and are asserted in the
tests.

## 4. Generalization (pre-set criteria)

| Model, K | Correct-majority quarters | Early / late accuracy | Quarters vs persistence (W/L/T) | Accuracy 95% CI (quarter block) | Changing-risk rows | Verdict |
|---|---|---|---|---|---|---|
| U-GB, 1 | 77% | 0.80 / 0.76 | 3 / 3 / 7 | [0.646, 0.908] | 0.44 (n = 18) | Partially generalized |
| U-GB, 2 | 77% | 0.72 / 0.76 | 4 / 1 / 8 | [0.600, 0.877] | 0.39 (n = 23) | Partially generalized |
| U-GB, 3 | 69% | 0.78 / 0.64 | 4 / 1 / 8 | [0.538, 0.892] | 0.43 (n = 28) | Partially generalized |
| U-STRUCT, 1 | 85% | 0.80 / 0.84 | 4 / 3 / 6 | [0.677, 0.938] | 0.61 | Partially generalized (fails (c) only) |
| U-STRUCT, 2 | 85% | 0.75 / 0.88 | 5 / 1 / 7 | [0.662, 0.923] | 0.57 | Partially generalized |
| U-STRUCT, 3 | 77% | 0.72 / 0.80 | 5 / 1 / 7 | [0.600, 0.892] | 0.54 | Partially generalized |

**Selection block versus confirmation block.** U-GB won the 2023–24 selection block. On the 2025–26 confirmation block
it is worse than its own structural core:

| K | U-GB accuracy / Brier | U-STRUCT accuracy / Brier |
|---|---|---|
| 1 | 0.76 / 0.140 | 0.84 / 0.125 |
| 2 | 0.76 / 0.157 | 0.88 / 0.139 |
| 3 | 0.64 / 0.207 | 0.80 / 0.132 |

The learned layer does not carry over to later quarters.

**Provinces** (U-GB, K = 1):

| Province | Accuracy | HIGH caught |
|---|---|---|
| Rizal | 1.00 | — (no HIGH rows) |
| Laguna | 0.85 | 2/4 |
| Cavite | 0.77 | 2/4 |
| Batangas | 0.69 | 1/3 |
| Quezon | 0.62 | 3/5 |

Province accuracy SD is 0.15–0.18 and quarter accuracy SD 0.25–0.34 across K. Quezon has the most HIGH rows and the
most errors at every K.

## 5. Principal errors

1. **The two hunger onsets are missed at every K by every candidate:** 2023-Q4 (Laguna, Quezon, Batangas) and 2024-Q2
   (all four HIGH provinces). They make up 7 of U-GB's 8 missed HIGH at K = 1.
   - Hunger is one regional reading, so a crossing that the last posted reading does not show cannot be forecast.
   - E90 showed the 2023-Q4 onset was in no input. The 2024-Q2 onset had a rice-price signal, but no earlier surge
     to learn from in the 2021+ window.
2. **Persistence of high-risk episodes at K ≥ 2.** 2024-Q4 and 2025-Q1 are additionally missed. The random-walk core
   spreads probability as the horizon grows, so probabilities drift toward the 0.3–0.5 band and recall falls
   (0.50 → 0.25 → 0.19).
3. **Quezon false HIGH and missed HIGH:** price-condition errors. E89 showed they are not a stable, learnable
   province bias.
4. **Over-prediction in the middle bins** (calibration-in-the-large −0.05 to −0.09). For example, U-GB K = 1 rows
   with p in 0.4–0.6 were HIGH only 33% of the time.

## 6. What was tried, and driver contribution

**Unified learning.** Pooling all horizons roughly triples the training pairs per origin. Still, learned layers are
fitted at only 46–62% of origins, because 6 label quarters with 5 HIGH are needed.
- With fewer than 30 distinct label quarters, every learned layer except U-GB is worse than the core it starts from.
- U-CAL, U-LR and U-LR-RICE fall to 0.48–0.62 accuracy at K = 2–3.
- **Changing the algorithm does not create the missing information.**

**Driver ablation** (U-GB, change in Brier when a group is removed; negative = the group hurt):

| Group | K = 1 | K = 2 | K = 3 | Reading |
|---|---|---|---|---|
| Prices / market | **−0.006** | −0.000 | **−0.029** | Redundant with the core; adds noise |
| Climate stress | −0.000 | +0.000 | −0.001 | No contribution |
| Agricultural supply | +0.000 | +0.004 | +0.006 | Small, inconsistent |
| Employment / remittances | +0.000 | −0.002 | +0.011 | Small, inconsistent |
| Hunger history | +0.001 | +0.000 | −0.000 | Already in the core |
| Poverty | +0.000 | 0.000 | 0.000 | Static, published only from 2025; no contribution |
| News (added) | +0.006 | +0.000 | −0.003 | No reliable gain (as in E83 and E85) |

U-GB's Brier is 0.140 / 0.190 / 0.169 at K = 1 / 2 / 3.

**Post-hoc round 2** (protocol §7; cannot define the validated K):

| Variant | Description | K = 1 | K = 2 | K = 3 | Candidate K |
|---|---|---|---|---|---|
| U-GB-NOPRICE | U-GB without the price group | 0.831, recall 0.62, Brier 0.134, Holm 0.137 | 0.754, recall 0.31 | 0.800, Brier 0.140, Holm 0.007 / 0.054 / 0.003, recall 0.31 | 0 |
| U-HR | One pooled rice-led hunger drift across horizons | 0.800, Brier 0.137 | 0.815, recall 0.44, Brier 0.165 | 0.769, Brier 0.137, recall 0.25 | 0 |

- U-GB-NOPRICE fails only the Brier significance at K = 1, and only recall at K = 3.
- U-HR is selection-informed (E90).
- Both improve the probabilities a little, but neither satisfies PASS at any K.

## 7. Why no horizon passes, and what would be needed

| Horizon | Binding constraint |
|---|---|
| K = 1 | **Statistical power.** Accuracy (0.785–0.831), recall (≥ 0.50) and balanced accuracy pass. The Brier gain over persistence (≈ 0.136) and climatology (≈ 0.068) is real in size but not significant over 13 quarters, because most of it comes from a few quarters. |
| K ≥ 2 | **Missing leading information.** HIGH recall stays below 0.5 because the hunger condition cannot be anticipated from any available input once the horizon exceeds the last posted reading. |
| K = 4 | **Data timing.** The year-on-year base quarter is unpublished at the origin. |

**Better data, not a better algorithm.** Three conditions would be needed, all outside this study's deadline and
therefore limitations and future work:
1. a quarterly hunger or food-insecurity series for CALABARZON (SWS regional tabulation) instead of Balance Luzon;
2. a provincial food-insecurity outcome (FNRI provincial FIES, CBMS 2024) to validate against;
3. more evaluated quarters, beginning with the sealed 2026-Q4..2027-Q2.

## 8. Sealed forecasts

`sealed/e91_prospective.csv`:
- SHA-256 `f20d6d52ff2e513dcf011bbc032c83ab75d981d803efbb3a2c0c188b6c01720c`.
- U-GB from origin 2026-Q3 (data published by 2026-10-14) for 2026-Q4, 2027-Q1 and 2027-Q2. One model fitted on the
  pooled pairs posted before 2026-10-01.
- U-STRUCT equals S-COV at this origin and is already in the E84 seal.
- E83, E84 and E90 seals verified unchanged.

| Target | Cavite | Laguna | Quezon | Rizal | Batangas |
|---|---|---|---|---|---|
| 2026-Q4 (K1) | 0.15 | 0.00 | 0.22 | 0.01 | 0.04 |
| 2027-Q1 (K2) | 0.28 | 0.11 | 0.30 | 0.10 | 0.19 |
| 2027-Q2 (K3) | **0.51** | 0.48 | **0.51** | 0.40 | **0.57** |

Bold values are at or above 0.5 (HIGH).

**Expected evaluation dates** (usual SWS/PSA release lags): about February 2027 (2026-Q4), May 2027 (2027-Q1) and
August 2027 (2027-Q2).

## 9. Thesis-ready conclusion

> A single horizon-conditioned food-insecurity risk model was developed. At each forecast origin, one model is trained
> on the pooled training examples of all horizons, with the horizon as an input, and issues forecasts one to four
> quarters ahead. Under the study's unchanged pass criteria, applied to 13 walk-forward target quarters
> (2023-Q1–2026-Q3), **no forecasting horizon was validated (K = 0)**.
>
> At one quarter ahead, the model reached 78.5% accuracy, recall of 0.50 for high-risk cases, and a Brier score of
> 0.140, compared with 0.277 for persistence and 0.208 for climatology. Its accuracy, recall and balanced accuracy met
> the criteria, but its probability improvement over persistence and climatology was not statistically significant
> over 13 quarters. One quarter ahead is therefore the longest horizon with **promising but unvalidated** skill.
>
> At two and three quarters ahead, recall for high-risk cases fell to 0.25 and 0.19. Four quarters ahead could not be
> computed, because the year-on-year reference quarter is not yet published at the forecast date.
>
> The principal errors are the 2023-Q4 and 2024-Q2 regional hunger onsets, which no available indicator anticipated.
> Market, climate, employment, remittance, poverty and news indicators added no reliable predictive information beyond
> the structural risk core. The target is a proxy (regional SWS hunger combined with provincial food-price pressure),
> so these results describe proxy-target performance, not validated provincial food-insecurity prediction.
>
> Establishing a validated horizon requires a CALABARZON-level hunger or food-insecurity series, a provincial outcome
> measure, and the sealed prospective quarters (2026-Q4 to 2027-Q2).

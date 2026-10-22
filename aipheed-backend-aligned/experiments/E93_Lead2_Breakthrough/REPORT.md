# E93: breaking through the Lead-2 failure (report)

**Branch.** `e93-lead2-breakthrough`, from `e92-lightgbm-lead2`. Not pushed. Production unchanged. E92 results are
preserved and compared as they are.

**Evidence.**
- Protocol: `PROTOCOL.md`, frozen at 093ae6a before scoring.
- Run: `runs/20261022T060351Z/` (`metrics.json`, `predictions_k{1..4}.csv`).
- Oracle diagnostic: `oracle_decomposition.json` in the same folder. It uses outcomes and is not a forecast.
- Tests: `backend/tests/integration/test_e93_lead2_breakthrough.py`.
- Rows: 65 per K (13 target quarters 2023-Q1..2026-Q3 × 5 provinces, 16 HIGH, T43), the same targets at every K.

The 13 quarters were examined in earlier experiments, so they are **development evidence, not an independent test**.
Only the sealed 2026-Q4..2027-Q2 quarters are unseen.

## 1. Verified findings

| Finding | Evidence |
|---|---|
| **One unified, news-informed LightGBM framework was built and run for K = 1..4.** | At every origin, one hunger model and one price model are fitted on pooled horizons, with K as an input and the ten news indicators as required inputs. |
| **Pre-registered selection: M-U93-LINDIR.** Hunger part: linear-tree LightGBM regression of the hunger change. Price part: LightGBM classifier. Direction, acceleration and cumulative features; news. | Selection Brier (K = 1..3, targets 2023–24): LINDIR 0.1562 < LINDIR-W 0.1573 < DIR 0.1895. |
| **HIGH detection improved strongly at K = 1.** | 12/16 caught vs 5/16 for E92 DEC-S; balanced accuracy 0.814 vs 0.626. |
| **The 2024-Q2 onset is now caught one quarter ahead.** | 4/4 provinces at K = 1, against 0/4 for E92 DEC-S and S-COV. |
| **K = 2 was not solved.** | The best K = 2 arm (DIR) scores 0.769 and catches 3/16; LINDIR scores 0.692 and catches 5/16. |
| **Maximum validated K = 0.** | No arm passes the unchanged E83 rule at any K. |
| **K = 1 is one criterion short, in two different ways.** | LINDIR fails only Brier significance (Holm p 0.105 vs persistence, 0.177 vs climatology). DIR fails only recall (0.38), while its Brier passes all three significance tests (Holm 0.080 / 0.056 / 0.004). |
| **Direction features are what help.** | Without them (NODIR), K1 recall falls 0.94 → 0.50 and K2 recall 5/16 → 1/16. |
| **News adds no measurable predictive value.** | Removing all news (levels and changes) leaves K1 Brier at 0.168 vs 0.167 and lowers K2/K3 Brier (0.219 vs 0.228, 0.203 vs 0.229). News stays as a required input; its contribution is reported as is. |

## 2. Horizon table (unified model; unissued rows count as wrong; Holm p vs persistence / climatology / always-HIGH)

| K | Arm | Accuracy | Balanced | Precision / recall / F1 | TP / FP / FN / TN | Brier | Holm p | Failed criteria |
|---|---|---|---|---|---|---|---|---|
| 1 | **LINDIR (selected)** | **0.846** | **0.814** | 0.67 / **0.75** / 0.71 | 12 / 6 / 4 / 43 | 0.142 | 0.105 / 0.177 / 0.000 | Brier significance |
| 1 | DIR | 0.815 | 0.667 | 0.75 / 0.38 / 0.50 | 6 / 2 / 10 / 47 | **0.131** | 0.080 / 0.056 / 0.004 | recall |
| 1 | LINDIR-W | 0.785 | 0.836 | 0.54 / 0.94 / 0.68 | 15 / 13 / 1 / 36 | 0.167 | 0.195 / 0.311 | Brier significance |
| 1 | E92 DEC-S | 0.785 | 0.626 | 0.62 / 0.31 / 0.42 | 5 / 3 / 11 / 46 | 0.136 | 0.124 / 0.124 | balanced accuracy, Brier, recall |
| 1 | E92 LIN (post-hoc) | 0.815 | 0.751 | 0.62 / 0.62 / 0.62 | 10 / 6 / 6 / 43 | 0.124 | 0.084 / 0.118 | Brier significance |
| 1 | S-COV | 0.815 | 0.709 | 0.67 / 0.50 / 0.57 | 8 / 4 / 8 / 45 | 0.141 | 0.171 / 0.171 | Brier significance |
| 2 | LINDIR (selected) | 0.692 | 0.564 | 0.36 / 0.31 / 0.33 | 5 / 9 / 11 / 40 | 0.215 | 0.081 / 0.467 | accuracy, balanced accuracy, Brier, recall |
| 2 | DIR | 0.769 | 0.573 | 0.60 / 0.19 / 0.29 | 3 / 2 / 13 / 47 | 0.176 | 0.075 / 0.134 | balanced accuracy, Brier, recall |
| 2 | E92 DEC-S | 0.754 | 0.542 | 0.50 / 0.12 / 0.20 | 2 / 2 / 14 / 47 | 0.204 | 0.102 / 0.325 | balanced accuracy, Brier, recall |
| 2 | S-COV | 0.800 | 0.636 | 0.71 / 0.31 / 0.43 | 5 / 2 / 11 / 47 | 0.177 | 0.066 / 0.232 | Brier, recall |
| 3 | LINDIR (selected) | 0.646 | 0.513 | 0.27 / 0.25 / 0.26 | 4 / 11 / 12 / 38 | 0.191 | — | all |
| 3 | DIR | 0.769 | 0.531 | 1.00 / 0.06 / 0.12 | 1 / 0 / 15 / 49 | 0.163 | 0.005 / 0.005 / 0.005 | recall |
| 4 | LINDIR (selected) | 0.585 | 0.493 | 0.24 / 0.31 / 0.27 | 5 / 16 / 11 / 33 | 0.255 | — | all (E92 and S-COV cannot issue K = 4) |

**Baselines** (accuracy / Brier):

| K | Persistence | Always-LOW |
|---|---|---|
| 1 | 0.723 / 0.277 | 0.754 / 0.246 |
| 2 | 0.646 / 0.354 | 0.754 / 0.246 |
| 3 | 0.569 / 0.431 | 0.754 / 0.246 |
| 4 | 0.646 / 0.354 | 0.754 / 0.246 |

**Inner-validation choices** (training data only):
- Price-part class weight: 1 at 62–69% of origins, 4 at 23–31%.
- Hunger-part recency half-life: about half of the origins.

The weighted arm (LINDIR-W) trades precision for recall: at K = 1 it catches 15/16 HIGH with 13 false alarms.

## 3. Generalization (selected LINDIR)

| K | Correct-majority quarters | Early / late accuracy | Quarters vs persistence (W/L/T) | Sign-test p | Accuracy 95% CI (quarter block) | Changing-risk rows | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | 85% | 0.90 / 0.76 | 5 / 2 / 6 | 0.23 | [0.708, 0.954] | 0.56 | Partially generalized (fails (c) only) |
| 2 | 69% | 0.70 / 0.68 | 3 / 1 / 9 | — | [0.538, 0.831] | 0.30 | Partially generalized |

**Confirmation block** (2025-Q1..2026-Q3, after the selection block):

| K | LINDIR accuracy / Brier | DIR accuracy / Brier |
|---|---|---|
| 1 | 0.76 / 0.168 | 0.88 / 0.089 |
| 2 | 0.68 / 0.199 | 0.80 / 0.121 |

**Provinces** (K = 1, LINDIR):

| Province | Accuracy | HIGH caught |
|---|---|---|
| Rizal | 1.00 | — (no HIGH rows) |
| Cavite | 0.85 | 3/4 |
| Laguna | 0.85 | 3/4 |
| Quezon | 0.77 | 4/5 |
| Batangas | 0.77 | 2/3 |

**Missed HIGH at K = 1:** 2023-Q4 (3) and 2026-Q2 Cavite.

**False alarms at K = 1:** concentrated in 2025-Q4, 2026-Q2 and 2026-Q3, when hunger was high but food inflation fell.

**Calibration (K = 1).** Over-prediction in the 0.2–0.4 band (mean 0.27, observed 0.05); calibration-in-the-large
−0.14.

## 4. Why K = 2 still fails: the oracle decomposition (diagnostic, uses outcomes)

Each part of the model is replaced by the true outcome, one at a time. Parts are from the LINDIR-W run.

| K | Model | True hunger × model price | Model hunger × true price |
|---|---|---|---|
| 1 | 0.785; caught 15, false HIGH 13 | 0.785; caught 16, false HIGH 14 | **0.938**; caught 16, false HIGH 4 |
| 2 | 0.646; caught 5, false HIGH 12 | 0.631; caught 13, false HIGH 21 | 0.769; caught 6, false HIGH 5 |
| 3 | 0.615; caught 4 | 0.585; caught 14, false HIGH 25 | 0.815; caught 4, false HIGH 0 |

**At K = 1 the hunger part already works.** Against the regional SWS outcome (hunger > 11.3, 13 quarters) it scores
0.923 accuracy and Brier 0.078, against 0.846 and 0.154 for hunger persistence. The remaining K = 1 errors come from
the price part.

**At K = 2 both parts fail.**
- With true hunger, the price part produces 21 false alarms.
- With true prices, the hunger part still misses 10 of 16.
- The hunger part scores 0.615 against SWS hunger at K = 2 (persistence 0.692).

## 5. Why the onsets are missed: the data limit

| Cause | Evidence |
|---|---|
| **2023-Q4 is unforeseeable from the available data** at both K = 1 and K = 2. | Last hunger 8.7, rice YoY 0.2–7.6, no ENSO advisory, no news signal at the origin. |
| **2024-Q2 is learnable at K = 1 but not at K = 2.** | At K = 1 the origin already shows hunger 14.3 and rice rising. At K = 2 the origin shows hunger 10.3. The regressor has seen one prior rise, so its change estimate is too small to cross 11.3. |
| **Too few training examples.** | Inside the approved 2021+ window there is one regime change in hunger (2023-Q4). Before it, labels flicker around 11.3 within SWS sampling error (about ±2.5 points at 95% for an assumed Balance Luzon n ≈ 600). |
| **The target is a proxy.** | T43 multiplies a regional hunger condition by provincial price pressure. Since 2023-Q4, the hunger condition is always met, so T43 measures price pressure, and food inflation has moved against hunger (r = −0.61). |

## 6. Does it predict food insecurity or price pressure?

**Partly food insecurity, at K = 1 only.** The model's hunger part forecasts the regional SWS hunger condition one
quarter ahead better than persistence (13 quarters: accuracy 0.923 vs 0.846, Brier 0.078 vs 0.154). That is the only
food-insecurity outcome measured every quarter, and it is regional, not provincial.

**The province-level result is proxy performance.** It reflects provincial food-price pressure under high regional
hunger. It must not be presented as predicting measured household food insecurity in each province.

## 7. Outstanding data requirements (not acquirable within the deadline; future work)

| Priority | Data | What it would fix | Feasibility |
|---|---|---|---|
| 1 | **SWS hunger for CALABARZON** (Survey Data Library, by request and fee) | Replaces Balance Luzon; gives a regional series and noisy provincial readings | Request letter drafted (E87 C) |
| 2 | **More evaluated quarters** | The K = 1 significance gap is mostly a power problem: 13 quarters, gains concentrated in a few | Sealed 2026-Q4..2027-Q2 become available about Feb–Aug 2027 |
| 3 | **Provincial food-insecurity outcome:** FNRI provincial FIES, CBMS 2024 | Validates provincial rankings and calibrates provincial risk | Requests drafted (E87 A, B) |
| 4 | **Monthly or sub-quarterly hunger or food-access signal**, e.g., DSWD or LGU feeding-program caseloads | An earlier hunger signal for K = 2 | Not available in the repository; would need agency cooperation |

**Not done:** no observation was fabricated, no household condition was inferred from unrelated measures, and the
approved target was not redefined.

## 8. Thesis-ready conclusion

> A unified, news-informed LightGBM forecasting framework was developed. At each forecast date, one hunger-change model
> (linear-tree LightGBM) and one price-condition model (LightGBM) are trained on all horizons together, using
> direction, acceleration and cumulative indicator changes and the required news indicators, and they forecast one to
> four quarters ahead.
>
> One quarter ahead, the model reached 84.6% accuracy and 81.4% balanced accuracy, and detected 12 of 16 high-risk
> province-quarters, including all four provinces at the 2024-Q2 surge. The earlier LightGBM detected 5. It met three
> of the four reliability criteria. Its probability improvement over persistence was not statistically significant
> over 13 quarters (Holm p = 0.105), so **no horizon is validated under the unchanged criteria (K = 0)**.
>
> Two or more quarters ahead, detection of high-risk cases stayed below 0.5. An oracle analysis shows that both the
> hunger and the price components lack leading information at that range.
>
> News indicators did not add measurable predictive value. Changes in indicator direction did.
>
> The model's hunger component forecasts the regional SWS hunger condition one quarter ahead better than persistence,
> but provincial results reflect food-price pressure, not measured household food insecurity.
>
> Validating a horizon requires the sealed 2026-Q4–2027-Q2 outcomes and a CALABARZON-level hunger series.

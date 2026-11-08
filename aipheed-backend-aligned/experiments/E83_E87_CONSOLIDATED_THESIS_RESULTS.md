# aiPHeed E83–E87: consolidated thesis results

**Scope.** E83 (deep reconstruction), E84 (leading price information), E85 (GDELT events), E86 (affordability
indicator), E87 (outcome data and the five mandatory drivers).

| Item | Detail |
|---|---|
| Branch | `e84-objective-continuation` (E83 cut from `final-system-v2` at 7774e30; E83 commits b560c8a..17de2c6, also on `origin/e83-deep-research-reconstruction`; E84–E87 commits d2839bf..3df271c and this report) |
| Study window | 2021-01 .. data published by 2026-10-14 |
| Data-limit rule | No pre-2021 value. Nothing published after the authorised limit. |
| Date | 2026-10-21 |

Every number in this report was re-read from the committed run artifacts listed in Appendix A. Where an experiment
reports a figure on a subset of rows, the subset is named.

**Labels used throughout.**
- *Food-insecurity outcome:* a direct measurement of household hunger or food insecurity.
- *Proxy target (T43):* a constructed label that combines regional hunger with provincial food-price conditions.
- *Price/affordability:* the provincial food-price condition alone.

They are never mixed in one comparison.

---

## A. Executive summary

**Purpose.** E83–E87 tried to make aiPHeed forecast food-insecurity risk for the five CALABARZON provinces at least
two quarters ahead (Lead 2) with more than 75% accuracy (80% target), against the required baselines, using five
drivers: Market/Prices, Employment, Climate Stress, OFW Remittances, Fish Kill.

**What was investigated.**
1. The validity of the approved target, T43.
2. New leading data, all publication-dated:
   - PSA provincial CPI subgroups and weights;
   - IMF world staple prices;
   - publisher lead text (730 articles);
   - 58,576 GDELT event records;
   - a dated fish-kill event list;
   - FNRI food-insecurity (FIES) survey results.
3. Model families: structural simulations, a component price model, constrained LightGBM, regularised logistic
   regression, stacked and hybrid models.
4. Plain-language SHAP explanations.
5. The 142-LGU outputs.
6. A monthly refresh job.

**Strongest findings.**

1. **One quarter ahead (Lead 1), on the proxy target T43, the models are useful.**
   - The pre-registered structural simulation S-SIM reaches accuracy 0.846 on 65 forecasts over 13 quarters
     (balanced 0.751, HIGH recall 0.56, Brier 0.118), against persistence at 0.723 (Brier 0.277). Its Brier gain is
     not significant (Holm p = 0.105).
   - A hybrid chosen after seeing results (LightGBM where it can be fitted, S-SIM elsewhere) reaches 0.877 (balanced
     0.834, recall 0.75, Holm p = 0.098). It is exploratory.
2. **Two quarters ahead (Lead 2), nothing meets the requirement.**
   - Best T43 accuracy on all 65 rows: 0.738 (E87 HUN-RW), HIGH recall 0.38.
   - Always-LOW scores 0.754, so accuracy alone cannot show skill here.
3. **The provincial food-price condition is forecastable two quarters ahead (price/affordability scorecard).**
   - The component model S-COMP reaches 0.757 on 70 rows.
   - On the 50 rows also covered by the served LightGBM price indicator, it reaches 0.80 vs 0.78. The difference is
     not significant (p = 0.126, 10 quarters).
   - This is **not** a food-insecurity result.
4. **T43 has become a price-pressure label.**
   - Since 2023-Q4, regional hunger exceeded the 11.3% line in 10 of 10 quarters, so T43 equals the price condition
     on 100% of those rows.
   - Regional hunger and provincial food inflation were negatively correlated (r = −0.61).
5. **The binding constraint is two-quarter-ahead regional hunger.**
   - With perfect knowledge of hunger, S-COMP's Lead-2 T43 forecasts would catch 81% of HIGH cases.
   - No driver, news source or model improved on the latest posted SWS reading (E84, E85, E87).
6. **FNRI FIES surveys confirm, independently, that SWS hunger tracks regional food insecurity.**
   - CALABARZON household food insecurity was 19.1% in 2023 and 22.6% in 2025 (Batangas 29.7% and Cavite 31.7% in
     2021). These moved in the same direction as SWS.
   - Provincial or quarterly FIES data are not publicly available.

**What remains unmet.**
- A validated Lead-2 food-insecurity forecast above 75%.
- A provincial or municipal food-insecurity outcome.
- Measurable value from news.

**Meaning for DA IV-A.**
- aiPHeed can give a defensible current-quarter (Lead 1) warning on the proxy target.
- It can give a two-quarter outlook on food-price pressure, clearly labelled as such.
- It can give a transparent 142-LGU vulnerability ordering.
- It cannot yet claim to forecast household food insecurity two quarters ahead.

---

## B. Experiment-by-experiment findings

### E83 — Deep reconstruction (protocol sha 3dddb90f, frozen before results)

**Question.** Can a leakage-safe redesign, with lead-text news, five-driver features and several model families,
reach more than 75% on T43 at Lead 2?

**Data and design.**
- Target: T43 = SWS Balance Luzon hunger > 11.3% **and** (province food CPI YoY > P60, or food − headline YoY > P60),
  with thresholds frozen on 2021–22.
- Rows: 13 target quarters (2023-Q1..2026-Q3) × 5 provinces = 65 per lead; 16 HIGH (24.6%).
- Origins: O(t) is the first day of quarter t+1, with publication-timed inputs. Leads 0–3 were evaluated.
- Pass rule:
  1. accuracy > 0.75, with unissued rows counted as wrong;
  2. balanced accuracy > every baseline;
  3. Brier better than persistence, climatology and always-HIGH (sign-flip by date, Holm p < 0.10);
  4. HIGH recall ≥ 0.5.

**Results** (run 20261021T084802Z):

| Lead | Arm | Accuracy | Balanced | Recall (HIGH) | Brier | Note |
|---|---|---|---|---|---|---|
| 0 | B-STATE (current state) | 0.923 | 0.886 | 0.81 | 0.077 | nowcast baseline, best |
| 1 | S-SIM | 0.846 | 0.751 | 0.56 | 0.118 | misses only significance |
| 1 | S-SIM-THR (post-hoc D2) | 0.846 | 0.814 | 0.75 | 0.129 | fails significance |
| 1 | HYB-GBA-SIM (post-hoc D4) | **0.877** | 0.834 | 0.75 | 0.101 | passes; Holm p 0.098; exploratory |
| 2 | S-SIM | 0.692 (0.750 on 60 issued) | 0.522 | 0.19 | 0.276 | fail |
| 2 | S-SIM-THR | 0.708 | 0.575 | 0.31 | 0.271 | fail |
| 2 | HYB-GBA-SIM | 0.554 | 0.494 | 0.38 | 0.347 | fail |
| 3 | all arms | ≤ 0.600 | < 0.5 | ≤ 0.19 | — | fail |

**Lead-text news.** Recovered lawfully for 730 of 9,667 articles (87 of 695 relevant ones). The rest were blocked by
bot challenges, disallowed by robots.txt, or had no permitted way to resolve the publisher URL.

**News ablation (A–F).** No significant gain. LightGBM at Lead 1: +0.001 Brier, p = 0.50. A placebo with permuted
labels did as well as the real stack at Lead 2.

**Supports.**
- A Lead-1 proxy-target warning.
- The finding that T43 equals price pressure since 2023-Q4.

**Does not support.**
- Any Lead-2 claim.
- Any news-value claim.

**Decisions.**
- The served model is unchanged.
- Explanations were rewritten in plain English (backend text only).
- 25 LGUs whose PSA poverty estimate has CV > 20% are flagged as low-confidence.
- A monthly refresh job was added.
- Prospective seal 1331d498… covers 2026-Q4, 2027-Q1 and 2027-Q2.

### E84 — Leading price information (protocol sha db9827b5)

**Question.** Do provincial CPI subgroups (rice and seven others, with PSA 2018 weights) and IMF world staple prices
(used four months after the reference month) improve Lead 2?

**Model.** S-COMP projects each food subgroup with its own seasonal drift, adds world-rice pass-through to rice, and
aggregates with PSA weights.

**Results on T43** (run 20261021T093234Z):

| Lead | S-COMP | E83 S-SIM |
|---|---|---|
| 2 | 0.723 (0.783 on 60 issued); balanced 0.585, recall 0.31, Brier 0.250 | 0.692 |
| 3 | 0.600 (0.709 on 55 issued) | — |
| 1 | 0.815 | 0.846 |

**Price-condition scorecard (price/affordability, not food insecurity):**

| Lead | Rows | S-COMP | E83 S-SIM | S-COMP without world prices | Persistence |
|---|---|---|---|---|---|
| 2 | 70 | 0.757, Brier 0.176 | 0.714 | 0.686 | 0.631 |
| 3 | 65 | 0.785 | 0.646 | 0.723 | 0.583 |

**Oracle decomposition** (Lead 2, 60 issued rows):

| Scenario | Accuracy | Recall (HIGH) | Balanced |
|---|---|---|---|
| S-COMP as it is | 0.783 | 0.31 | 0.63 |
| Perfect regional hunger + S-COMP prices | 0.783 | 0.81 | 0.79 |
| Perfect prices + hunger random walk | 0.800 | 0.56 | 0.72 |

**Supports.** World prices add real leading information for affordability. The hunger component is the limit.

**Does not support.** A food-insecurity Lead-2 result.

**Decisions.**
- Seal ad402660… covers 2026-Q4 to 2027-Q2. S-COMP calls Quezon HIGH for 2027-Q1, while E83's S-SIM calls every
  province LOW.
- A data-source audit records the sources that cannot be reached: NDRRMC (bot challenge), ReliefWeb (registration
  needed), and WFP HungerMap, which is model-predicted for the Philippines.

### E85 — GDELT event signals (researcher-approved scan)

**Data.**
- 58,576 de-duplicated GDELT records (V1 columns, deviation D1), 2021-01-01 .. 2026-10-14.
- 0.543 TiB scanned on the free tier, so there was no charge.

**Question.** Do dated, full-text-derived event signals anticipate the hunger crossing?

**Results.**

| Lead | S-COMP + GDELT hunger component | S-COMP | Paired Brier |
|---|---|---|---|
| 2 | accuracy 0.646, recall 0.00, Brier 0.289 | 0.723 | −0.042 (worse) |
| 1 | 0.754 | 0.815 | −0.026 (worse; two-sided p 0.064) |

On the hunger outcome itself, GDELT scored 0.54 against persistence at 0.69 (mean absolute error 6.8 vs 5.0 points).

**Interpretation.** GDELT theme shares follow the typhoon calendar, not hunger.

**Decision.** Excluded from the active model.

### E86 — Affordability indicator

**Rows.** 50 rows, 10 quarters, 2024-Q2..2026-Q3: the price condition at Lead 2.

| Indicator | Accuracy | Brier | AUC |
|---|---|---|---|
| S-COMP | 0.80 | 0.159 | 0.84 |
| Served E56 LightGBM price indicator | 0.78 | 0.182 | 0.79 |

The paired gain has one-sided p = 0.126.

**Decision.** Not significant, so the served indicator is unchanged. The 0.80 is an **affordability/price** result,
not 80% food-insecurity forecasting.

### E87 — Outcome data and the five mandatory drivers (protocol frozen at f6572fe)

**Outcome data obtained** from public FNRI documents, with page citations
(`E87_Outcome_Gap/data_acquired/fnri_fies_observations.csv`):

| Year | Area | Moderate-to-severe FI | Severe | Basis |
|---|---|---|---|---|
| 2021 | Batangas | 29.7% (90% CI 27.3–32.2) | 1.5% | ENNS, households |
| 2021 | Cavite | 31.7% (27.0–36.4) | 2.4% | ENNS, households |
| 2021 | City of Lucena | 26.2% | 1.0% | ENNS, households |
| 2023 | CALABARZON | 19.1% (95% CI 16.9–21.3) | 1.7% | NNS, households |
| 2025 | CALABARZON | 22.6% | 1.6% | Updating Survey, population |

These measurements are annual, not quarterly.

**Requests drafted, not sent** (`DATA_REQUESTS.md`):
- A. PSA CBMS 2024 municipal items;
- B. FNRI provincial FIES for Laguna, Quezon and Rizal;
- C. SWS CALABARZON hunger microdata.

**Fish Kill.** 132 dated, de-duplicated news events, of which 11 are reported kills in CALABARZON. All are
news-reported and not BFAR-verified.

**Five-driver test of the hunger component** (Lead 2, T43, all 65 rows):

| Arm | Accuracy | Recall (HIGH) | Brier | Paired Brier vs random walk | Hunger accuracy (H-BIN) |
|---|---|---|---|---|---|
| Random walk (latest SWS reading) | 0.738 | 0.38 | 0.249 | — | 0.692 |
| + Market/Prices | 0.646 | 0.00 | 0.300 | −0.054 | 0.538 |
| + Employment | 0.631 | 0.00 | 0.294 | −0.049 | 0.538 |
| + Climate Stress | 0.708 | 0.19 | 0.249 | +0.000 (p 0.48) | 0.692 |
| + OFW Remittances | 0.646 | 0.00 | 0.296 | −0.051 | 0.538 |
| + Fish Kill | 0.646 | 0.00 | 0.282 | −0.036 | 0.538 |
| + all five | 0.677 | 0.12 | 0.259 | −0.010 (p 0.53) | 0.692 |

**Supports.**
- SWS face validity.
- All five drivers reach the pipeline and were tested.

**Does not support.** That any driver anticipates hunger two quarters ahead. Employment and OFW Remittances exist only
nationally.

---

## C. Consolidated performance comparison

The 65 T43 rows (13 quarters; 16 HIGH) are identical for every arm at each lead. Accuracy counts unissued rows as
wrong.

| Scorecard | Horizon | Arm | n / quarters | Accuracy | Balanced | Recall (HIGH) | Brier |
|---|---|---|---|---|---|---|---|
| Proxy target T43 | Lead 1 | B-PERSIST | 65 / 13 | 0.723 | 0.627 | 0.44 | 0.277 |
| | Lead 1 | B-CLIM / always-LOW | 65 / 13 | 0.754 | 0.500 | 0.00 | 0.208 / 0.246 |
| | Lead 1 | S-SIM (pre-registered) | 65 / 13 | 0.846 | 0.751 | 0.56 | 0.118 |
| | Lead 1 | HYB-GBA-SIM (post-hoc) | 65 / 13 | 0.877 | 0.834 | 0.75 | 0.101 |
| | Lead 2 | B-PERSIST | 65 / 13 | 0.646 | 0.555 | 0.38 | 0.354 |
| | Lead 2 | B-CLIM / always-LOW | 65 / 13 | 0.754 | 0.500 | 0.00 | 0.219 / 0.246 |
| | Lead 2 | S-COMP | 65 / 13 | 0.723 | 0.585 | 0.31 | 0.250 |
| | Lead 2 | HUN-RW (E87) | 65 / 13 | 0.738 | 0.616 | 0.38 | 0.249 |
| | Lead 2 | S-COMP + GDELT | 65 / 13 | 0.646 | 0.429 | 0.00 | 0.289 |
| Price/affordability condition | Lead 2 | S-COMP | 70 / 14 | 0.757 | 0.762 | 0.80 | 0.176 |
| | Lead 2 | S-COMP vs served E56 (E86 subset) | 50 / 10 | 0.80 vs 0.78 | 0.78 vs 0.78 | 0.72 vs 0.78 | 0.159 vs 0.182 |
| | Lead 3 | S-COMP | 65 / 13 | 0.785 | 0.776 | 0.73 | 0.172 |
| Food-insecurity outcome (regional SWS > 11.3%) | Lead 2 | persistence | 13 / 13 | 0.692 | — | — | — (MAE 5.03) |
| | Lead 2 | always-HIGH | 13 / 13 | 0.769 | — | — | — |
| | Lead 2 | GDELT ridge | 13 / 13 | 0.538 | — | — | — (MAE 6.85) |
| | Lead 2 | Market/Prices ridge (E87) | 13 / 13 | 0.538 | — | — | — (MAE 7.67) |

Province and LGU outputs are not evaluated against local outcomes, because none exist (see D8).

---

## D. Objective-by-objective assessment

| # | Objective | Status | Evidence | What remains necessary |
|---|---|---|---|---|
| 1 | Genuine food-insecurity target | **Partly met** | SWS hunger is a direct measure and is now face-validated by FNRI FIES (2021–2025). T43 since 2023-Q4 is a price-pressure label (E83 audit). | A provincial or municipal outcome (CBMS 2024, FNRI provincial FIES, SWS microdata), and an adviser decision on T43 |
| 2 | > 75% out-of-sample accuracy | **Partly met** | Lead 1: 0.846 (pre-registered) and 0.877 (post-hoc). Not at Lead 2. | Lead-2 evidence |
| 3 | 80% target | **Not met** at Lead 2. Partly met at Lead 1 (0.877, post-hoc). | E83 D4 | Prospective confirmation from seals 1331d498 and ad402660 |
| 4 | Validated Lead-2 forecasting | **Not met** | Best T43 Lead-2: 0.738, recall 0.38. Below always-LOW (0.754) and climatology's Brier. | A hunger signal that leads SWS, or more quarters |
| 5 | Beat required baselines | **Partly met** | Lead 1 beats persistence on every metric (Brier advantage borderline, Holm p 0.098–0.105). Lead 2 does not. | Prospective quarters |
| 6 | Five drivers integrated | **Partly met** | All five reach training and inference and were ablated (E83 groups, E87 exact five). Only Market/Prices carries signal. Employment and OFW are national. Fish Kill has 11 reported CALABARZON kills. | Provincial employment and remittance series. A BFAR-verified fish-kill record. |
| 7 | News/NLP incremental value | **Not met** | Lead text, event clusters and GDELT gave no gain (E83, E85). | Licensed full text, or a different outcome |
| 8 | Province and 142-LGU outputs | **Partly met** | 142/142 LGUs return a valid, labelled index and band. 25 low-precision flags. Derived, not locally validated. | CBMS 2024 for validation |
| 9 | Correct SHAP explanations | **Met** | TreeSHAP of the served LightGBM was reproduced independently (additivity 1e-16; probabilities within 5e-4). FIRI pushes sum exactly. Plain headline reasons match the push signs (tests). | — |
| 10 | Monthly refresh and dynamic quarters | **Partly met** | `run_monthly_refresh` is tested for success and failure. The E27 cycle seals before outcomes and advances only when READY. The scheduler is off by default in the deployment. | Enable and observe in production |
| 11 | Backend/frontend integration and deployment | **Partly met** | See §G: local suites and the API end-to-end check. The deployed service runs `final-system-v2`, not this branch. | Merge and redeploy after review |
| 12 | Reproducibility and tests | **Met** | Protocols are hashed before results. Runs, seals and provenance are committed. Test results are in §G. | — |

---

## E. Scientific interpretation

1. **The target.**
   - T43 was designed as a conjunction of regional hunger and provincial price pressure.
   - Because hunger stayed above its 2021–22 threshold from 2023-Q4 onward, the label lost its hunger content.
   - In 2025–26 it fell to LOW while measured hunger and FIES rose.
   - Any accuracy on T43 after 2023 is therefore largely accuracy on price pressure. This is a construct-validity
     finding, not a modelling failure.
2. **Forecastability.**
   - Two-quarter-ahead provincial price conditions are forecastable (0.76–0.79) from base effects, seasonal subgroup
     drift and world rice prices.
   - Regional hunger is not forecastable beyond its latest reading with these data. The 2023–24 surges were not
     preceded by any published driver.
   - This agrees with the literature: persistence is hard to beat, and skill decays with lead time (Westerveld et al.
     2021; Foini et al. 2023; Busker et al. 2024).
3. **Sample size.**
   - There are 13 independent target quarters per lead. One quarter moves accuracy by 7.7 points.
   - Sign-flip tests cannot reach p below 1/2^13.
   - Post-hoc arms reuse these quarters, so only the sealed prospective forecasts can validate them.
4. **GDELT.** Large volume did not mean useful signal. The theme mix tracks the typhoon calendar, and adding it made
   forecasts worse.
5. **S-COMP.** It is a better affordability forecaster in point estimates, but the evidence (p = 0.126 over 10
   quarters) does not justify replacing the served indicator.
6. **Local outputs.**
   - The 142 LGU values are province estimates re-weighted by PSA poverty and population density. FNRI shows poverty
     roughly doubles food-insecurity prevalence, which supports the weighting.
   - They are derived estimates, not locally validated forecasts.
7. **Operational implication.** An early-warning system for DA IV-A built on these data can issue:
   - a current-quarter proxy warning;
   - a two-quarter price-pressure outlook;
   - a vulnerability-based municipal ordering.

   Each must be labelled for what it is. A two-quarter food-insecurity forecast needs better outcome data.

---

## F. Final recommendations (ranked)

1. **Obtain a better-measured outcome** (highest impact). Send requests A–C (`E87_Outcome_Gap/DATA_REQUESTS.md`). SWS
   CALABARZON microdata (C) gives a regional quarterly series with no new collection.
2. **Score the sealed forecasts** when PSA and SWS publish 2026-Q4, 2027-Q1 and 2027-Q2 (seals 1331d498 and
   ad402660). This is the only unseen test of the Lead-1 hybrid and of S-COMP.
3. **Decide the target with the adviser.** Either keep T43 and report it as hunger-conditioned price pressure, or adopt
   regional hunger as the primary outcome with T43 secondary. The decision belongs to the adviser.
4. **Drivers.**
   - Seek provincial LFS and remittance series from PSA and BSP.
   - Seek BFAR fish-kill bulletins to verify the 11 news-reported kills.
   - OCR the CALABARZON wage orders to add a purchasing-power series.
5. **System.**
   - Merge `e84-objective-continuation` into the deployed branch after review.
   - Enable the monthly scheduler.
   - Keep S-COMP as a labelled affordability candidate.

---

## G. Verification performed for this report (2026-10-21)

All checks ran on branch `e84-objective-continuation` at the commit that adds this report.

| Check | Command or method | Result |
|---|---|---|
| Backend unit and integration tests | `python -m pytest -q` (backend/) | **556 passed, 18 skipped, 0 failed** |
| Frontend tests | `npx vitest run` | **74 passed (15 files)** |
| Frontend production build | `npm run build` | **Built** (one warning: chunk larger than 500 kB) |
| Frontend type check | `npx tsc --noEmit -p tsconfig.app.json` | **Fails**: type errors only in `src/data/mockData.ts` (mock objects lack `limitedSignal`, `articleCount`, `seriesMonitored`, `seriesNeedingReview`, `disaggregationLabel`). Pre-existing: last changed 2026-09-23; this branch changes no frontend file. The build is unaffected. |
| SHAP and prediction consistency | `tests/test_e83_served_shap.py`, `tests/test_e83_plain_explanations.py` | Pass. TreeSHAP additivity 1e-16. Served probabilities reproduced within 5e-4. FIRI pushes sum exactly. |
| Monthly refresh and failure handling | `tests/test_e83_monthly_refresh.py` | Pass. A failed step is logged and the other step still runs. |
| Lead-text extractor (robots, challenges, no full text, idempotent) | `tests/test_e83_lead_extractor.py` | Pass |
| End-to-end, production configuration | API started as `render.yaml` configures it (`AIPHEED_LEAD2_MODEL=thesis`, `AIPHEED_STRICT_MODEL=1`, scheduler off), port 8003 | See below |
| Live deployment | GET https://aipheed-api.onrender.com/api/v1/health (the host in `frontend/vercel.json`) | **Not verifiable.** HTTP 404 with `x-render-routing: no-server`: no Render service answers at that hostname. The deployment must be created, or the rewrite URL corrected, by the account owner. |

**End-to-end results (production configuration, local).**
- `/health` ok; `/readiness` ready; the strict artifact check passed at start-up.
- Indicator: `food_insecurity_risk_index` (FIRI v2).
- `/quarterly/forecast-period`: reference 2026-Q4, target 2027-Q1, cutoff 2026-12-31 23:59:59 PHT.
- `/provinces`: 5 provinces, quarter 2027-Q1.
- `/provinces/{id}/municipalities`: **142 of 142 LGUs**, 142 unique PSGC codes, 0 invalid rows. Bands: 138 low,
  4 high. Every row carries the "derived, not a measured municipal rate" label.
- `/explainability` for each province:
  - target 2027-Q1, issued 2026-10-01, serving mode thesis;
  - risk index Cavite 0.757, Laguna 0.803, Batangas 0.712, Rizal 0.725, Quezon 0.723;
  - every headline in the new plain form.
- `/news` and `/report/data`: HTTP 200.

---

## Appendix A — artifacts

| Experiment | Folder | Key artifacts |
|---|---|---|
| E83 | `E83_Deep_Reconstruction/` | PROTOCOL.md (+ sha), DEVIATIONS.md, REPORT.md, `runs/20261021T084802Z/RESULTS.json`, `predictions_d4_k*.csv`, `sealed/e83_prospective.csv` |
| E84 | `E84_Objective_Continuation/` | PROTOCOL.md, REPORT.md, DATA_SOURCES_AUDIT.md, `runs/20261021T093234Z/metrics.json`, `sealed/e84_prospective.csv` |
| E85 | `E85_GDELT_Events/` | PROTOCOL.md, DEVIATIONS.md, REPORT.md, query_job.json, `runs/20261021T101520Z/metrics.json` |
| E86 | `E86_Affordability_Indicator/` | REPORT.md (computed from the E57 sealed predictions and the E84 features) |
| E87 | `E87_Outcome_Gap/` | PROTOCOL.md, REPORT.md, DATA_REQUESTS.md, `data_acquired/fnri_fies_observations.csv`, `data_derived/fishkill_events.csv`, `runs/20261021T120748Z/metrics.json` |

**Kept local, by design (gitignored):**
- publisher lead paragraphs;
- raw GDELT rows;
- FNRI and NWPC PDFs;
- the GCP key.

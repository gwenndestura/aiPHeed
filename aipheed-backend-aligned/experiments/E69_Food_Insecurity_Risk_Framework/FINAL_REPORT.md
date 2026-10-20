# E69: rethinking aiPHeed from its scientific foundation

**Date:** 2026-10-20
**Branch:** `e69-food-insecurity-risk-framework`, from `resolve-e67-critical-failures` @ `9320db6` (verified equal to origin).
**Protocol:** `PROTOCOL.md`, frozen 2026-10-20T03:01:00Z before any E69 analysis (SHA-256 `5173fda5…`).

**Sealed forward outlook:** `sealed/outlook_forward.csv` (SHA-256 `e6b6266f…`), with the 2026-Q4 and 2027-Q1 regional hunger forecasts of every candidate and every provincial tier.

**Labels used in this report:**
- **Measured:** computed by an E69 runner, with its table named.
- **Assumption:** stated as such.
- **Recommendation:** marked as such.

---

## 1. Status of aiPHeed before E69

```
DATA (2021-Q1 .. 2026-10-14)
  PSA CPI food/headline, monthly, PROVINCE
  PSA wholesale rice, palay/corn, fisheries, PROVINCE
  SWS hunger, quarterly, REGION (Balance Luzon)
  PSA LFS, NATIONAL; BSP remittances (ends 2025-Q4), NATIONAL
  NOAA ONI, PAGASA advisories, NATIONAL; typhoons, PROVINCE
  News titles (Google News RSS), thin per province
  PSA SAE poverty 2021 (municipal), subsistence 2021/2023, PROVINCE
        |
        v
TARGET T43 = [regional hunger > 11.3%] AND [provincial food-price pressure]
             (= provincial price pressure on all 50 evaluated rows, E66/E68)
        |
        v
MODEL E56-TUNED LightGBM: P_price (CPI-projection offset + trees) x P_hunger (ridge), Lead-2
        |
        v
EVALUATION: 10 origins, 50 rows (all examined), acc 0.72, no correction better (E68)
        |
        v
API record (E58) -> e66 climate watch -> e67/e68 disclosures -> DASHBOARD (approved UI)
                                                               map = score colour
```

**Objectives 1–4 before E69:**

| Objective | Status |
|---|---|
| Obj 1 | pipeline built; no forecasting gain; corpus thin |
| Obj 2 I–IV | metrics reported (development evidence) |
| Obj 2 V | no reliable horizon |
| Obj 3 | 142-LGU ranking correct, but from unvalidated province forecasts |
| Obj 4 | baseline comparison done; Brier only |

**Principal scientific bottlenecks:**

| # | Bottleneck | Measured evidence |
|---|---|---|
| B1 | The target measures price pressure, not food insecurity | T43 = PS on 50/50 rows; hunger above the line in every quarter since 2024 |
| B2 | The only food-insecurity outcome is regional and noisy | SWS Balance Luzon, n = 300–600, margin ±4–6 pts; 2024–26 values alternate 25 → 17 → 24 → 17 → 22 → 17 → 24 |
| B3 | Few independent observations | 10 quarters; label ICC 0.29, so n_eff ≈ 23 of 50 rows (`out/r2_province_fusion.json`) |
| B4 | National inputs repeated across provinces | ENSO, employment, OFW and policy flags have zero cross-province variance (E68 `r2_trigger_variance.csv`) |
| B5 | No forward climate evidence that can be tested | one in-window El Niño, confounded with disinflation (E68); no dated PAGASA drought archive |
| B6 | Vulnerability measures too noisy to rank provinces | subsistence CVs of 17–62% |

---

## 2. What each source is: outcome, leading indicator, vulnerability or proxy

| Source | Geography / cadence | Role | Available at issue? | Notes |
|---|---|---|---|---|
| SWS hunger (Balance Luzon) | region / quarterly | **observed outcome** (involuntary hunger) | latest round posted 3–8 weeks after fieldwork | the only quarterly food-insecurity outcome; sampling noise ±4–6 pts |
| DOST-FNRI FIES | region / survey years | outcome anchor | 2023 only | cannot be a quarterly target |
| PSA subsistence incidence | province / 2021, 2023 | **vulnerability** (food poverty) | 2023 data published 2024-08-15 | CV 17–62%; not a quarterly outcome |
| PSA SAE poverty 2021 | municipal / one-off | vulnerability | yes | weights the LGU ranking (Obj 3) |
| PSA food and headline CPI | province / monthly | **leading indicator** (affordability hazard) | through month 2 of the origin quarter | carries the provincial skill |
| PSA bottom-30% CPI | province / monthly to 2026-06 | leading indicator for the poor | to 2026-06 only | r = 0.78–0.98 with the general CPI: largely redundant |
| Wholesale rice, palay/corn | province / quarterly | leading indicator, exposure | t − 1 | production YoY is the only local climate-exposure measure |
| Fisheries/aquaculture | province / quarterly | proxy (production) | t − 1 | not fish-kill events (no event series) |
| PSA LFS | national / monthly | context | t − 1 | the same for all provinces |
| BSP remittances | national / quarterly | context | ends 2025-Q4 | missing for 2026 |
| ENSO / PAGASA | national | **hazard** (warning signal) | dated advisories | one in-window episode |
| News | province / quarterly | warning context | published before issue | province shares mostly 0 |

---

## 3. Target alternatives and their validity

| Candidate | Concept | Feasible? | Verdict |
|---|---|---|---|
| Direct provincial food insecurity (CBMS, provincial FIES) | observed food insecurity | **No data** | infeasible now; this is the key data gap |
| Regional SWS hunger H(t+2) | observed food insecurity (region) | yes; 18 eligible Lead-2 quarters | **the only valid outcome target**; regional, noisy (E69 Scale 1) |
| T43 (approved) | price pressure under high hunger | yes | kept as the score's label; describes food-price pressure |
| T-AFF (E68) | affordability stress | yes | describes 2026 better; not forecastable (E68) |
| Poverty / subsistence | vulnerability | yes (static) | context only; not a quarterly outcome |
| Composite food-stress label | exploratory state | possible | **rejected as a training target.** Mixing an outcome (hunger) with its drivers (prices, climate) into one label would make "validation" circular. E69 instead keeps the outcome and the hazards separate and fuses them only in a decision-support tier |

**Answer to "what should the target represent?"** E69 separates three things that earlier work merged:

| Thing | E69 component |
|---|---|
| Observed food insecurity | regional SWS hunger, forecast in Scale 1 |
| Risk of future food insecurity | Scale 2 risk outlook: hunger outlook plus provincial hazards |
| Food affordability stress | the existing price-pressure score (T43) plus observed headline inflation |

**Limitation:** the study **cannot yet establish predictive accuracy for actual provincial food insecurity**, because no provincial outcome exists.

---

## 4. Candidate methodologies

| Approach | Identifiable with the available data? | Strengths | Failure modes | E69 decision |
|---|---|---|---|---|
| Direct supervised model on a provincial outcome | **no** (no outcome) | — | — | not possible |
| Direct model on the regional hunger outcome (R0–R5) | yes; 18 quarters | real outcome, independent of the predictors' sources | noise ±4–6 pts; one level shift (2024); ≤ 18 points | **evaluated (Scale 1)** |
| Hierarchical / multilevel (regional + provincial deviation) | partly | separates the shared trend from provincial signal | 5 provinces per quarter; ICC 0.29 | evaluated as a diagnostic: quarter-mean vs provincial model |
| Separate component models + evidence fusion | yes, as a rule | transparent; a LOW price score cannot hide hunger or climate evidence | not a probability; no provincial outcome to validate | **implemented (Scale 2)** |
| Simple / regularized statistical models | yes | stable | E66: an 11-input L2-LR was unstable; R3 AR1 and R5 OLS worse than RW | evaluated |
| Current LightGBM (E56-TUNED) | yes | province-specific price skill (within-quarter AUC 0.71) | price-only target | **kept as the affordability component and benchmark** |
| Persistence and domain baselines | yes | — | — | baselines throughout |

Deep or complex models were not fitted. At 18 regional points or about 23 effective provincial observations, they are not identifiable.

---

## 5. Selected methodology: a two-scale food-insecurity risk framework

**Scale 1: regional hunger outcome forecast.** The latest posted SWS reading (random walk, R0). It is selected because no candidate beat it (§6). It reports the expected level, an 80% interval and P(> 11.3%).

**Scale 2: provincial risk outlook (frozen rule).**

| Tier | Condition |
|---|---|
| ELEVATED | H and (A or (C and X)) |
| WATCH | H and C |
| NO ELEVATED SIGNAL | otherwise |
| INSUFFICIENT DATA | H unknown |

Components:
- **H:** regional hunger expected above 11.3%.
- **A:** affordability hazard (price-pressure score ≥ 0.5, or headline inflation above the province's usual 2021–22 level).
- **C:** PAGASA El Niño status in force.
- **X:** local palay or corn production down 10% or more.

The tier follows the IPC "convergence of evidence" logic: an outcome signal plus a hazard.

**Vulnerability** (subsistence, poverty) is shown with its sampling errors but is not in the tier.

**Why this framework fits the evidence best:**
1. It forecasts the one real outcome and reports honestly how well that can be done.
2. It keeps the provincial model for what it measurably does (provincial price pressure).
3. A LOW price score can no longer be read as LOW food-insecurity risk.
4. Every component is observable at the issue date and dated.
5. It claims no unvalidated probability.

**The score is unchanged.** The map colour, the probability and the 142-LGU ranks are the E58 record's. Changing the map colour to the tier would be an unapproved design and meaning change; this is listed as a decision.

---

## 6. Lead-2 evaluation results and uncertainty

### 6.1 Scale 1: regional hunger outcome (`tables/r1_scores_all_available.csv`, `r1_scores_common_origins.csv`, `r1_paired_vs_RW.csv`)

The rows cover 18 eligible quarters (targets 2022-Q2..2026-Q3), each one independent observation. No target was excluded. The common origins (all six models estimable) are 8 quarters.

| Model | Quarters | MAE (pts) | E1 correct | E1 recall elevated / not | E1 Brier | Sharp rises hit / false alarms |
|---|---|---|---|---|---|---|
| R0 latest reading | 18 | **3.88** | 12/18 (0.67) | 0.77 / 0.40 | 0.172 | 0/4 / 0 |
| R1 mean of last 4 | 18 | 3.88 | 11/18 | 0.69 / 0.40 | 0.181 | 0/4 / 0 |
| R2 mean of all posted | 18 | 5.10 | 11/18 | 0.69 / 0.40 | 0.211 | 0/4 / 0 |
| R3 AR(1) | 10 | 10.19 | 6/10 | — | 0.281 | 0/3 / 4 |
| R4 ridge (E56 hunger part) | 10 | 7.24 | 9/10 | — | 0.062 | 0/3 / 3 |
| R5 latest + regional food CPI | 8 | 10.44 | 6/8 | — | 0.182 | 0/2 / 4 |
| Always "above 11.3%" | 18 | — | 13/18 (0.72) | 1 / 0 | — | — |

**Context for these numbers:**
- **Noise floor:** survey noise alone gives an expected MAE of about 1.8 pts.
- **Paired against R0** (common 8 quarters): no model is better. R4 +2.8 (CI −0.0..+5.5); R3 and R5 are significantly worse.
- **Selected:** R0.
- **Post hoc (not used for selection):** R0 from all posted rounds, including non-approved, gives MAE 3.74 against 3.88. Through 2025 the approved-only rule left the hunger input three quarters stale (base 24.0 from 2025-Q1 until 2026-01).

**Reading:**
- Regional hunger two quarters ahead cannot be forecast better than its latest reading.
- The latest reading's error is about twice the survey noise.
- No method foresaw any of the four sharp rises.
- "Above 11.3%" at 0.67 is below the trivial always-above rule (0.72), because hunger has been above the line every quarter since 2024.

**The Lead-2 accuracy goal at regional level is not met in any meaningful sense.**

### 6.2 Province-level skill of the existing model (`tables/r2_province_skill.csv`)

| Reading | Correct / 50 | Brier | Within-quarter AUC |
|---|---|---|---|
| A0 (E56-TUNED, served) | 36 | 0.214 | 0.706 |
| A0 quarter mean | 32 | 0.230 | 0.5 |
| N1 / N1 quarter mean | 36 / 35 | 0.192 / 0.210 | 0.706 |
| K1 / K1 quarter mean | 38 / 35 | 0.206 / 0.226 | 0.706 |

**By the frozen rule, A0 has demonstrable province-specific skill:** 4 rows and 0.016 Brier better than its quarter mean. The provincial price signal is real. Label ICC is 0.29, so the 50 rows carry about 23 effective observations.

### 6.3 The > 75% Lead-2 goal

| Level | Result | Met? |
|---|---|---|
| Province (Chapter I Obj 2 I) | 0.72 (E68; no correction better; K1-EW 0.82 is post hoc) | **NOT MET** |
| Region (outcome) | 0.67 vs always-above 0.72 | **NOT MET** |

The goal **cannot be shown achievable** with the current data. What would settle it is listed in §9.

### 6.4 Scale-2 tier (descriptive; `tables/r2_tier_history.csv`, `r2_tier_by_year.csv`)

**Tier counts by target year:**

| Target year | ELEVATED | WATCH | NO ELEVATED SIGNAL |
|---|---|---|---|
| 2022 | 2 | 0 | 13 |
| 2023 | 7 | 0 | 13 |
| 2024 | 8 | 3 | 9 |
| 2025 | 11 | 0 | 9 |
| 2026 | 1 | 0 | 14 |

**Against the outcome and labels:**

| Tier | T43 HIGH rows | Rows where the regional outcome was elevated |
|---|---|---|
| ELEVATED | 10 of 29 | 20 of 29 |
| NO ELEVATED SIGNAL | 11 of 58 | 42 of 58 |

**Known weaknesses:**
- 2024-Q2: the input was stale hunger (10.3%), so the tier gave NO SIGNAL, while hunger was 19.6%.
- 2026-Q1 and Q2: hunger was 17–22%, but there was no affordability or climate hazard, so the tier gave NO SIGNAL. The rule deliberately requires converging evidence.

**The tier is not a forecast of hunger and is not validated.**

---

## 7. El Niño and climate exposure (2026-Q3 → Q4 → 2027-Q1)

**Causal chain, link by link, at the 2026-10-01 issue:**

| Link | Measurable? | Evidence | Per province |
|---|---|---|---|
| El Niño status / outlook | yes (dated) | PAGASA Climate Advisory 2026-09-23 and Advisory No. 5 (10-07, after issue) | national |
| Local rainfall / drought | **no** | no dated 2021–26 archive; rainfall file pre-2021 (excluded) | — |
| Production disruption | partly (observed t − 1) | palay / corn YoY 2026-Q2 | drop ≥ 10%: Cavite, Laguna, Batangas; Quezon palay +51%, corn −7%; Rizal none |
| Food prices | yes | projected food inflation for 2027-Q1 0.8–2.1%, below every HIGH line; no El Niño price effect estimable (2023–24 = disinflation, E68) | all five below the line |
| Purchasing power | partly | headline inflation at issue above its usual level | Laguna 6.9 (usual 4.7), Quezon 6.1 (5.1), Rizal 6.6 (6.1); Cavite 4.6, Batangas 4.4 below |
| Food access / hunger | yes (regional) | latest posted 17.3% (2026-Q2); outlook 17.3% (80% range 10.8–23.8), P(> 11.3%) = 0.88 | regional |

**Q3 → Q4 → Q1 drivers of the score** (E65–E68, unchanged): the CPI projection, the gap rule and the configuration switch.

**What changes in E69:** the outlook combines the hunger outlook with the province hazards.

| Target | Tier for all five provinces | Basis |
|---|---|---|
| 2026-Q4 | ELEVATED | Batangas: climate + exposure; the other four: affordability |
| 2027-Q1 | ELEVATED | Cavite and Batangas: climate + local exposure; Laguna, Quezon and Rizal: affordability, plus climate + exposure in Laguna |

**No fair historical climate backtest exists**, so no climate-enhanced accuracy is claimed.

---

## 8. Five trigger groups and news

| Group | What it measures | Resolution | Role | Missing / delays | Measured Lead-2 contribution | Confounding |
|---|---|---|---|---|---|---|
| Market / prices | CPI projection, food YoY, gap, rice, policy | province (policy national) | leading indicator | none at issue | the signal (offset); within-quarter AUC 0.71 | partly shared shocks (ICC 0.29) |
| Climate | ENSO observed, typhoons, palay/corn | province (ENSO national) | hazard / exposure | typhoon quarter incomplete (placeholder) | Δ Brier +0.005 when removed (n.s.) | ENSO is a time proxy |
| Fisheries | production YoY | province | proxy (not fish kills) | none | −0.004 (n.s.) | — |
| Employment | LFS unemployment | **national** | context | — | −0.003 (n.s.) | pure time proxy |
| OFW | BSP remittances, FX | **national** | context | remittances missing 2026 | −0.012 (n.s.); with employment −0.022 (CI < 0, rule not met) | pure time proxy |
| News | trigger shares | province | warning context | shares 0 in 46–100% of rows | −0.002 (n.s.); classification F1 0.83 ≠ forecasting gain | thin corpus |

**Why removing groups changed almost nothing:**
- The CPI projection offset carries the skill.
- The national groups can only shift whole quarters.
- The 10-quarter sample cannot resolve small effects.

The improved news pipeline stays a context layer (E64/E66/E68). Its classification quality does not translate into forecast skill.

---

## 9. Data gaps and the exact data needed

1. **A provincial or municipal food-insecurity outcome, quarterly or annual, 2021–2026.** Options: CBMS food-security items, provincial FIES (PSA), or DSWD/LGU caseloads. This is the only way to validate provincial food-insecurity forecasting, the > 75% goal included.
2. **SWS sample sizes per round** for Balance Luzon (partial in E27), to model survey noise properly; ideally SWS microdata or area splits.
3. **Prospective outcomes:**
   - 2026-Q4: SWS Q4 round (fieldwork Dec 2026), CPI Oct–Dec 2026;
   - 2027-Q1: SWS round and CPI.

   They score the E68 and E69 seals; at least 8–12 more quarters are needed before any reliability claim.
4. **Dated PAGASA dry-spell/drought assessments and ENSO outlooks, 2021–2026,** for a fair climate backtest.
5. **BSP 2026 remittances; provincial LFS** if published.
6. **Fish-kill event records** (BFAR) with dates.
7. **The Lucena poverty estimate** (HUC).

---

## 10. Objectives 1–4 compliance (Chapter I §1.5.2, verbatim)

| Obj | Intended outcome (exact wording) | Implemented | Evidence | Evaluation | Limitations | Status |
|---|---|---|---|---|---|---|
| 1 | "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus." | pipeline v3 (E64) | FSSI-v3, BERTopic panel | classifier P 0.92 / R 0.75 (AI-annotated); no forecast gain | thin, retrospective, titles only; no human validation; bias correction not validated | **Partially met** |
| 2 I–IV | "To evaluate the performance of the proposed LightGBM forecasting model using … Accuracy … Precision and Recall … F1-Score … AUC-ROC" | E56-TUNED, rolling origin | acc 0.72, prec 0.625, rec 0.556, F1 0.588, AUC 0.649; within-quarter AUC 0.71 | development evidence | rows examined; T43 = price pressure | **Met as an evaluation; performance not validated** |
| 2 V | "Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable" | E63 | leads 1–3: Brier 0.130 / 0.214 / 0.251 | no lead meets the rule | "reliable" undefined | **Unmet** |
| 3 | "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights." | 0.6/0.4 weighting, exact ranks | 142 LGUs, API = frontend (E68 browser) | ranking consistent | province forecasts not validated | **Partially met** |
| 4 | "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline" | E55/E66 baselines | Brier 0.178 vs 0.400 / 0.598 / 0.235 / 0.646 | better on Brier (examined rows); accuracy not above always-LOW | not on unseen data | **Partially met** |

**Working software vs validated science:** the system works end to end. Its forecasting performance for actual food insecurity is not validated.

---

## 11. Dashboard implementation and verification

**Serving mode `AIPHEED_LEAD2_MODEL=e69`** (opt-in; E38 default unchanged; no frontend file changed):
- **Numbers:** the score, colours and ranks equal e58/e68.
- **Added to the existing summary sentence:**
  - the province risk outlook, with its reasons and "A LOW food-price score above does not mean low food-insecurity risk";
  - the regional hunger outlook, with its interval and back-test;
  - the province-skill note and the goal status.
- **New optional API fields:** `summary.riskOutlook`, `regionalHungerOutlook`, `vulnerabilityProfile`.
- **Every e68 layer stays:** input status, affordability, El Niño finding, climate watch and model identity.

**Browser check** (2026-10-20, stack `aipheed-e69-stack`: API 8069, frontend 8099):
- Region panel: "Food-insecurity risk outlook: ELEVATED in Batangas, Cavite, Laguna, Quezon, Rizal", the regional hunger outlook and the common inputs.
- Quezon panel: "Food-insecurity risk outlook for Quezon: ELEVATED", the LOW-score sentence, the hunger outlook, the exploratory-score wording, input status and affordability.

**LGUs:** 142 unique, finite, risk level present (test); API = frontend for all 142 (E68 browser check, same ranks in e69).

**Explanations:** the SHAP-type bars remain the E56 TreeSHAP of the score. The tier is a rule and gets no SHAP; its reasons are listed in plain words.

---

## 12. Tests and GitHub

| Suite | Result (2026-10-20) |
|---|---|
| Backend full | **505 passed, 18 skipped, 0 failed** (`out/backend_full_suite.txt`); +10 E69 tests |
| Backend, committed tree only (E46 D-1 hunks swapped out, untracked D-1 test excluded, working files restored byte-identical) | **496 passed, 18 skipped, 0 failed** (`out/backend_committed_tree_suite.txt`) |
| Frontend vitest | 46/46 |
| Production build | passed |
| `tsc` | 6 errors, all pre-existing in `mockData.ts` |
| Browser end-to-end | passed (§11) |

**New tests in `tests/integration/test_e69_risk_framework.py`:**

| Area | Coverage |
|---|---|
| Protocol | frozen |
| Outcome | never filled |
| Leakage | information sets use only rounds posted before issue |
| Scale 1 | no model beats the latest reading; RW selected |
| Province skill | measured against the quarter mean |
| Tier rule | reproduced from its components; a climate hazard alone never gives ELEVATED |
| Seal | forward seal intact |
| Serving | e69 numbers = e58; outlook beside the score; LOW-score sentence; region view = province views; back-tests get no outlook; missing disclosure falls back to e68 |
| LGUs and default | 142 LGUs; E38 default |

**Branch and commit:** `out/commit_record.txt`.

---

## 13. Remaining failures and exact next steps

| Failure | Next step |
|---|---|
| No validated provincial food-insecurity forecast | obtain a provincial outcome (§9.1); then fit a direct model and test it prospectively |
| > 75% Lead-2 not met (province 0.72; region 0.67) | score the E68/E69 seals as 2026-Q4 and 2027-Q1 publish; accumulate ≥ 8 more quarters before any claim |
| Regional hunger is noise-dominated and unforecastable beyond persistence | obtain round sample sizes or microdata; model survey error explicitly |
| The tier requires converging evidence, so it can miss high hunger without an identified hazard (2026-Q1/Q2) and stale hunger (2024-Q2) | adviser decision: add a "high hunger alone" WATCH rule (pre-register before 2027-01-01); use all posted rounds (post-hoc MAE 3.74 vs 3.88) |
| No testable climate input | dated PAGASA archive (§9.4) |
| National employment/OFW inputs | build N1 (no national inputs) as the next record, sealed prospectively |
| Map colour shows the price score, not the outlook | adviser/user decision on whether the outlook may colour the map (a design and meaning change) |
| Production default E38 | user/adviser decision on making e69 the default |

**Demonstration** (from `backend/`):

```
set AIPHEED_LEAD2_MODEL=e69
venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
:: or API 8069 + approved frontend 8099:
venv\Scripts\python.exe -B ..\aipheed-backend-aligned\experiments\E69_Food_Insecurity_Risk_Framework\runner\serve_e69_stack.py
```

**Reproduce:**
- Run `r1_regional_hunger.py`, then `r2_province_fusion.py` (refuses to re-seal), then `r3_build_disclosure.py`.

**Preview or production (needs authorization; not done):**
- Set `AIPHEED_LEAD2_MODEL=e69` on a preview API.
- Set the frontend's `VITE_API_BASE_URL` to that API.

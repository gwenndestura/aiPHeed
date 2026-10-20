# E67: the best aiPHeed system for Objectives 1–4 at Lead-2

**Date:** 2026-10-20
**Branch:** `best-model-objectives-1-4-lead2` (new), created from `aiPHeed/best-model-methodology-review` @ `1ac3444` (`out/original_head.txt`).
**Protocol:** `PROTOCOL.md`, frozen at 2026-10-20T02:07:46Z before any E67 arm was scored (SHA-256 `7cb1afa8…`, checked by every runner and by a test).
**Evidence status:** every metric here is **development evidence**. All 50 Lead-2 evaluation rows (targets 2024-Q2..2026-Q3) had been examined by E56–E66 before E67. Nothing below is unseen-quarter evidence, and nothing is called validated.

> **Measured** = computed by an E67 runner from files in this repository; the table is named.
> **Assumption** = stated as such.
> **Recommendation** = marked "Recommendation".

---

## 1. Executive summary

**Selected system (unchanged numbers, new serving mode `AIPHEED_LEAD2_MODEL=e67`).** It has five separate layers:

| Layer | Component | Status |
|---|---|---|
| 1. Lead-2 forecast | E56-TUNED LightGBM, read with the E58 two-signal early warning | development evidence; not validated |
| 2. Regional hunger | latest SWS reading and P(hunger > 11.3%), shown as its own number | observed, regional only |
| 3. Climate Food-Stress Watch | the E66 rule-based El Niño hazard watch | not a model input; not a probability; not validated |
| 4. LGU priority | approved 0.6 poverty / 0.4 density weighting on exact ranks | relative prioritization |
| 5. E67 disclosure (new) | model identity per issue date; per-trigger-group coverage and missing-data status; the measured Lead-2 effect of each group; a plain explanation when a score is LOW under a climate watch | built only from E67 tables |

Throughout, E58-EW means the E58 two-signal early-warning reading, and CFSW means the Climate Food-Stress Watch.

**Why no new model was promoted.** Under the frozen rules, no candidate beats the E56 LightGBM:
- six trigger-group ablations;
- market-only;
- government-only and news-only arms;
- climate-aware arms;
- logistic regressions;
- transparent rules.

Removing any single trigger group changes Lead-2 Brier by −0.012 to +0.005, and every CI includes 0 (`tables/r3_trigger_group_effects.csv`). The simpler market-only model is statistically indistinguishable from the full model, which strengthens rather than weakens the case for a simple price-driven reading.

**The > 75% Lead-2 goal is NOT legitimately met** (`tables/r3_goal_test.csv`, pre-registered G1–G5):

| Reading | Correct / 50 | Accuracy (quarter-cluster 95% CI) | Balanced | Recall HIGH / LOW | Beats always-LOW? | Verdict |
|---|---|---|---|---|---|---|
| E56 P(HIGH) ≥ 0.5 (proposed model) | 36 | 0.72 (0.56–0.84) | 0.684 | 0.556 / 0.812 | no (Δ CI −0.06..+0.24) | goal not met |
| E58-EW (P_price ≥ 0.5) | **39** | **0.78** (0.70–0.86) | **0.780** | 0.778 / 0.781 | **no** (Δ CI −0.02..+0.32) | goal not met (G3 fails; also designed after seeing these rows, G4 = no) |
| Always LOW | 32 | 0.64 (0.44–0.84) | 0.500 | 0 / 1 | — | baseline |
| Persistence | 28 | 0.56 | 0.535 | 0.444 / 0.625 | — | baseline |

E58-EW passes the accuracy (G1) and class-balance (G2) criteria. Its advantage over always-LOW is **not distinguishable from zero** once quarters are treated as the unit of independence. Ten quarters, with 12 of 21 quarters sharing one label across all five provinces, cannot support it. The rule was also defined after E58 inspected E56's errors on these rows.

**El Niño.** The LOW scores for 2026-Q4 and 2027-Q1 are not a serving defect.
- **What drives the score:** the price part is driven by the CPI projection. Projected food inflation is 0.8–2.1% for 2027-Q1, against HIGH lines of 4.7–7.2%.
- **What the climate inputs contain:** observed ENSO, typhoons and production only. There is no forward PAGASA outlook and no rainfall or drought data.
- **What every ablation shows:** the 2027-Q1 price part stays at or below 0.18 with any group removed.

E67 therefore keeps the model number and the CFSW climate watch separate. In e67 mode the dashboard now states in plain words why a score is LOW while a watch is in force.

---

## 2. Thesis objectives addressed (Chapter I, verbatim)

Source: `E25_Reliable_Forecasts_2021_2026/thesis_source/CHAPTER_I_verbatim.txt`, extracted from `THESIS 2 (11).pdf` (sha256 `88dd0b62…`). On 2026-10-20 this was still the newest thesis file in Downloads; its hash was checked in this session.

| Obj | Chapter I wording (verbatim, abridged only at "…") | Required output | Data / method | Evaluation | Current status (evidence) | Gap |
|---|---|---|---|---|---|---|
| 1 | "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus." | FSSI and topic patterns per province-quarter | news corpus, XLM-R, BERTopic | pipeline produces the panel; quality of relevance and attribution | **Partially met.** `app/news/pipeline_v3.py` (E64) produces FSSI-v3 and BERTopic per province-quarter. E67 R2: the trigger shares the served model uses are 0 in 96–100% of rows for 4 of 5 groups. | Titles only, retrospective collection, AI-annotated labels; no human check; no forecasting gain (section 9) |
| 2 I–IV | "To evaluate the performance of the proposed LightGBM forecasting model using … Accuracy … Precision and Recall … F1-Score … AUC-ROC" | the four metric families for the LightGBM | rolling origin | the metrics themselves (Chapter I sets no threshold) | **Met as development evidence.** Lead-2: acc 0.72, precision 0.625, recall 0.556, F1 0.588, AUC 0.649 (`r3_goal_test.csv`) | Unseen quarters (the sealed 2026-Q4 and 2027-Q1 forecasts) |
| 2 V | "Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable" | multi-lead study and a furthest reliable horizon | walk-forward | a definition of "reliable" | **Not met.** E63/E66 leads 1–3: Brier 0.130 / 0.214 / 0.251; no lead meets the rule. "Reliable" is undefined in Chapter I. | Adviser definition; more quarters |
| 3 | "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights." | 142 LGU rankings | SAE 2021, POPCEN 2024 | consistency; DA evaluator check (H4) | **Partially met.** 142 LGUs, finite, correct province mapping, exact ranks (test). The province forecasts are **not validated**, which Obj 3 presupposes. | Validated province forecast; Lucena substitute source; DA check |
| 4 | "To compare the effectiveness of the proposed LightGBM forecasting model against … Naive persistence … PSA-only indicator … NLP-only sentiment … Logistic regression baseline" | comparison table | same rows, same target | paired Brier, quarter clusters | **Met as a comparison.** E56 Brier 0.178 vs 0.400 / 0.598 / 0.235 / 0.646 (E55/E66, 45 rows). Superiority is not established on accuracy (section 7). | Unseen quarters |

**Scope (§1.7) items relevant here:**
- "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk": T43 follows this.
- "City and municipal estimates … will not represent official food insecurity classifications": the API label states this.
- "Areas with limited news coverage will also be identified": `limitedSignal` / `dataStatus`.

**Discrepancies reported, not resolved by rewriting the objectives:**
1. **DEPDev IV-A.** The task brief names it as an intended user. Chapter I §1.7 names only "50 DA Region IV-A evaluators", and the user removed DEPDev on 2026-10-10. E67 targets DA IV-A only.
2. **News window.** §1.7 says news "from 2020 to 2025". The user's hard rule is 2021-Q1..2026 (no pre-2021 data), and the code follows the user's rule.
3. **Thresholds.** Chapter I sets no accuracy threshold. The > 75% Lead-2 goal is this task's requirement, so it is tested as such and is not presented as a Chapter I criterion.
4. **Objective 5.** The FNRI face-validity check belongs to Objective 5 and is outside this task.

---

## 3. Repository, branch and commits

| Item | Value |
|---|---|
| Starting branch / commit | `aiPHeed/best-model-methodology-review` @ `1ac3444`, in sync with origin (verified 2026-10-20 after `git fetch`) |
| New branch | `best-model-objectives-1-4-lead2` (`git switch -c`; no tree change) |
| Uncommitted work preserved | The E46 D-1 hunks of another session in `backend/app/api/v1/insights.py` and `e41_lead2.py`, and the untracked `backend/data/e46/*d1*` and `scripts/build_record_e46_d1.py` files. They stay uncommitted (`out/original_uncommitted.diff`); E67 commits only its own hunks of those two files. |
| Frozen evidence | E38–E66 sealed files, records and tables untouched. The E67 runners read them and write only under `E67_…/`, `backend/data/e67/`. |
| Commit / push | see section 17 |

**What is served:**
- **Production default** (`AIPHEED_LEAD2_MODEL` unset): E38. Unchanged.
- **Experimental opt-in modes:** e41…e66, plus the new e67.

---

## 4. Model and methodology comparison (Lead-2, same 50 rows, T43)

**Design:**
- **Rows:** the 10 E57 origins (issue 2024-01-01..2026-04-01), target = origin + 2, 5 provinces.
- **Data:** issue-date cutoffs (CPI through month 2 of the origin quarter; SWS rounds posted before issue; news published before issue).
- **Labels and scorer:** one label set (T43) and one scorer (`E66 runner/e66_lib.py`).
- **Refitting:** every learner refits at every origin on targets ≤ origin − 1.
- **Exclusions:** none of the eligible quarters. 2021–2023-Q3 targets are training-only, because the E57 eligibility rule requires ≥ 6 training quarters and ≥ 6 hunger pairs.

| Candidate | Family / features | Acc | Bal | Prec | Rec H | Rec L | F1 | Brier | AUC | FA | Miss | Onsets |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **E56-TUNED (A0, proposed)** | LightGBM, all 5 triggers + news + policy; nested config | 0.72 | 0.684 | 0.625 | 0.556 | 0.812 | 0.588 | 0.214 | 0.649 | 6 | 8 | 3/10 |
| E58-EW reading | same model, P_price ≥ 0.5 | **0.78** | **0.780** | 0.667 | 0.778 | 0.781 | 0.718 | **0.182** | 0.786 | 7 | 4 | **7/10** |
| CPI-projection rule (transparent) | projection vs threshold | 0.74 | 0.748 | 0.609 | 0.778 | 0.719 | 0.683 | 0.188 | 0.788 | 9 | 4 | 7/10 |
| X_climate (new) | A0 minus climate | 0.68 | 0.653 | 0.556 | 0.556 | 0.750 | 0.556 | 0.219 | 0.655 | 8 | 8 | 3/10 |
| X_fish (new) | A0 minus fish | 0.74 | 0.700 | 0.667 | 0.556 | 0.844 | 0.606 | 0.210 | 0.649 | 5 | 8 | 3/10 |
| X_employment (new) | A0 minus employment | 0.72 | 0.684 | 0.625 | 0.556 | 0.812 | 0.588 | 0.211 | 0.648 | 6 | 8 | 3/10 |
| X_ofw (new) | A0 minus OFW | 0.68 | 0.653 | 0.556 | 0.556 | 0.750 | 0.556 | 0.202 | 0.694 | 8 | 8 | 3/10 |
| X_news = government only (new) | A0 minus news | 0.74 | 0.700 | 0.667 | 0.556 | 0.844 | 0.606 | 0.212 | 0.658 | 5 | 8 | 3/10 |
| M_only (new) | market + rice policy only | 0.68 | 0.641 | 0.562 | 0.500 | 0.781 | 0.529 | 0.212 | 0.672 | 7 | 9 | 3/10 |
| E60-C gov + improved news (E66) | LightGBM | 0.74 | 0.675 | — | 0.444 | 0.906 | — | 0.215 | 0.649 | 3 | 10 | 3/10 |
| E60-D / E64-E gov + news + history (E66) | LightGBM | 0.68 / 0.74 | 0.63 / 0.70 | — | 0.444 / 0.556 | — | — | 0.223 / 0.211 | — | — | — | 3/10 |
| News-only LR (E60-B / E64-B, E66) | LR | 0.36 / 0.38 | 0.43 / 0.44 | — | 0.667 | 0.19 / 0.22 | — | 0.445 / 0.507 | 0.48 / 0.44 | 26 / 25 | 6 | — |
| E65 climate-aware B1–B3 (E66) | LightGBM + ENSO intensity / PAGASA status | 0.72–0.74 | 0.68–0.70 | — | 0.556 | — | — | 0.213–0.214 | 0.65 | — | — | 3/10 |
| N1 / N2 L2 logistic regression (E66) | LR | 0.44 / 0.68 | 0.47 / 0.67 | — | 0.556 / 0.611 | — | — | 0.335 / 0.228 | — | — | — | — |
| Persistence | last known label | 0.56 | 0.535 | 0.400 | 0.444 | 0.625 | 0.421 | 0.440 | 0.535 | 12 | 10 | 0/10 |
| Majority (always LOW) | — | 0.64 | 0.500 | — | 0 | 1 | 0 | 0.360 | 0.500 | 0 | 18 | 0/10 |
| Climatology / province climatology | training base rate | 0.64 | 0.500 | — | 0 | 1 | 0 | 0.304 / 0.293 | — | 0 | 18 | 0/10 |

Sources: `tables/r3_goal_test.csv`, `r3_confusion.csv`; rows marked "(E66)" are from E66 `tables/r1_metrics_50rows.csv`.

**Confusion matrices (TP / FP / FN / TN):**

| Reading | TP | FP | FN | TN |
|---|---|---|---|---|
| E56 | 10 | 6 | 8 | 26 |
| EW | 14 | 7 | 4 | 25 |
| CPI rule | 14 | 9 | 4 | 23 |
| Persistence | 8 | 12 | 10 | 20 |
| Majority | 0 | 0 | 18 | 32 |

**Why E56 stays the model:**
1. Chapter I names a LightGBM.
2. No alternative is better by the frozen paired-Brier rule (E66 F.2, E67 R3).
3. The simpler readings (market-only, CPI rule) are **not worse**, and that is reported. The CPI rule is the transparent benchmark.
4. Deep learning was not tried: with 30–60 training rows per origin it is not defensible (E66 F.8: even an 11-input L2-LR was unstable).

**What would change the choice:** a candidate that wins on the unseen 2026-Q4 and 2027-Q1 outcomes under the pre-registered rule.

---

## 5. Target validity

| Question | Answer (measured) | Source |
|---|---|---|
| Is regional SWS hunger used as a provincial proxy? | Yes. One Balance-Luzon series gates all five provinces. | E55 `t43_labels`; E66 D |
| Does T43 collapse into price pressure? | **Yes.** T43 = PS on 50/50 evaluation rows (asserted again in E67 `out/r3_goal.json`: `T43_eq_PS_rows` 50) and on 70/70 rows with hunger > 11.3%. | E66 r7, E67 r3 |
| Can elevated hunger coexist with a LOW label? | **Yes.** 2026-Q3: hunger 23.6%, headline 4.8–7.3%, all five provinces LOW (the food-minus-headline gap counts faster non-food inflation as relief). | E66 E.1, E62 |
| Can it represent climate production or affordability risk? | Only after it shows up in provincial food CPI; production and affordability are not in the label. | E65/E66 |
| Thresholds independent of predictions? | Yes. Province P60 of 2021–22 frozen in E40 before the Lead-2 models, and H = 11.3 is an adviser-set constant. None changed in E67. | E40 `label_spec.json` |
| Enough variation? | Weakly: 18 HIGH / 50. In the late regime (2025-Q4..2026-Q3), 1 HIGH in 20 rows; 12 of 21 quarters have one label for all provinces. | E66 D |
| Food insecurity or exploratory food stress? | **Exploratory provincial food-price pressure under a high-hunger regime.** No provincial food-insecurity outcome exists in the data (no CBMS or provincial FIES). | E54, E66 |

**Decision:** the original target T43 is preserved, and no new target was adopted. A PS-plus-separate-hunger declaration (E51/E66) would need adviser approval, and on the evaluated rows it would change no number. E67 therefore does not redefine anything.

**Evidence that would resolve this:** a provincial or municipal food-insecurity outcome (CBMS food-insecurity items, provincial FIES, DSWD/LGU caseloads), quarterly or at least annual, for 2021–2026.

---

## 6. Lead-2 evaluation results and uncertainty

- **Accuracy uncertainty** is reported two ways: Wilson (row-level, optimistic) and the **quarter-cluster bootstrap** (2,000 draws, seed 67; the honest interval). For E56 these are 0.583–0.825 and 0.56–0.84. For EW they are 0.648–0.872 and 0.70–0.86.
- **Accuracy minus always-LOW** (quarter-cluster): E56 −0.06..+0.24; EW −0.02..+0.32; CPI rule −0.10..+0.32.
- **Accuracy minus persistence:** E56 −0.02..+0.36; EW +0.02..+0.44. EW beats persistence on accuracy.
- **McNemar (exact, two-sided)** in wins/losses/p format: EW vs always-LOW 14/7/0.189; EW vs persistence 17/6/0.035; E56 vs always-LOW 10/6/0.454.
- **Calibration slope:** E56 0.55 (over-confident); EW 0.75; CPI rule 0.95.

**By quarter** (correct of 5; `r3_by_quarter.csv`):

| Target | HIGH | E56 | EW | Always LOW | Persistence |
|---|---|---|---|---|---|
| 2024-Q2 | 4 | 1 | 4 | 1 | 1 |
| 2024-Q3 | 1 | 3 | 3 | 4 | 3 |
| 2024-Q4 | 3 | 3 | 3 | 2 | 2 |
| 2025-Q1 | 4 | 4 | 4 | 1 | 5 |
| 2025-Q2 | 3 | 4 | 4 | 2 | 3 |
| 2025-Q3 | 2 | 3 | 3 | 3 | 4 |
| 2025-Q4 | 0 | 5 | 5 | 5 | 1 |
| 2026-Q1 | 0 | 5 | 5 | 5 | 2 |
| 2026-Q2 | 1 | 4 | 4 | 4 | 2 |
| 2026-Q3 | 0 | 4 | 4 | 5 | 5 |

EW's whole gain over E56 is 2024-Q2, where E56's hunger gate used a stale 10.3% reading.

**By province** (correct of 10; `r3_by_province.csv`):

| Province | HIGH | E56 | EW | Always LOW |
|---|---|---|---|---|
| Batangas | 3 | 7 | 8 | 7 |
| Cavite | 4 | 4 | 5 | 6 |
| Laguna | 5 | 7 | 8 | 5 |
| Quezon | 6 | 8 | 9 | 4 |
| Rizal | 0 | 10 | 9 | 10 |

Cavite remains the weakest: both models are worse than always-LOW there.

**Rising risk:**
- EW detects 7 of 10 onsets and E56 detects 3 of 10.
- False alarms: EW 7/32 = 0.22 and E56 6/32 = 0.19.

**Other horizons** (E63/E66, separate analysis, not used for Lead-2 claims):
- **Brier by lead:** lead 1 0.130 (acc 0.85), lead 2 0.214, lead 3 0.251.
- **Lead 4:** not computable.
- **Operational horizon:** stays at Lead-2 (`app/quarterly/target.py`; test).

---

## 7. Baseline comparisons (Objective 4)

| Comparison | Result | Rule outcome |
|---|---|---|
| E56 vs persistence (50 rows, Brier) | −0.226, CI below 0, 7/10 quarter wins | CI passes; sign test not significant |
| E56 vs climatology | −0.090, CI touches 0 | not better |
| E56 vs Chapter I baselines (45 rows, Brier) | 0.178 vs 0.400 (persistence), 0.598 (PSA-only LR), 0.235 (NLP-only LR), 0.646 (LR combined) | CI excludes 0 except vs NLP-only; no sign test significant |
| Accuracy vs always-LOW | not distinguishable for any model (section 6) | — |

Sources: E66 `r1_paired_vs_*.csv`, `r1_metrics_45rows_with_chapter1_baselines.csv`; E67 `r3_goal_test.csv`.

**Statement supported:** the LightGBM is **better than the four Chapter I baselines in probability quality** (Brier) on development rows. It is **not shown to be more accurate than always predicting LOW**.

---

## 8. El Niño and the climate inputs

**Sources (date-checked):**
- PAGASA El Niño Advisories No. 1–5, dated 2026-06-09, 07-06, 08-06, 09-07 and 10-07. Re-checked on 2026-10-20 at pagasa.dost.gov.ph; nothing after No. 5 (`sources/SOURCES.md`).
- The E65 press-release timeline, 2021–2026.
- **Issue-date discipline:** each forecast uses only items dated before its issue date (test `test_climate_statements_use_only_items_before_issue`, plus the E66 hazard tests).

**Per province** (`tables/r4_el_nino_trace.csv`, full inputs; extract):

| Province | Target (issue) | P(HIGH) | P_price | Food proj / HIGH line | Gap proj / line | P_price without climate | Max P_price over any ablation | Watch |
|---|---|---|---|---|---|---|---|---|
| Batangas | 2026-Q4 (07-01) | 0.019 | 0.019 | 2.39 / 7.15 | −1.92 / 0.66 | 0.066 | 0.104 | WATCH + EXPOSURE |
| Batangas | 2027-Q1 (10-01) | 0.043 | 0.044 | 0.75 / 7.15 | −2.51 / 0.66 | 0.039 | 0.060 | WATCH + EXPOSURE |
| Cavite | 2026-Q4 | 0.024 | 0.024 | 0.99 / 4.71 | −2.71 / 0.74 | 0.087 | 0.144 | WATCH + EXPOSURE |
| Cavite | 2027-Q1 | 0.109 | 0.113 | 1.03 / 4.71 | −2.53 / 0.74 | 0.100 | 0.148 | WATCH + EXPOSURE |
| Laguna | 2026-Q4 | 0.061 | 0.061 | 1.34 / 6.05 | −4.48 / 0.61 | 0.051 | 0.120 | WATCH + EXPOSURE |
| Laguna | 2027-Q1 | 0.070 | 0.073 | 0.86 / 6.05 | −2.42 / 0.61 | 0.059 | 0.089 | WATCH + EXPOSURE |
| Quezon | 2026-Q4 | 0.285 | 0.286 | 5.41 / 6.24 | −1.61 / −0.56 | 0.310 | 0.435 | WATCH + EXPOSURE |
| Quezon | 2027-Q1 | 0.146 | 0.152 | 2.08 / 6.24 | −2.58 / −0.56 | 0.125 | 0.182 | WATCH |
| Rizal | 2026-Q4 | 0.005 | 0.005 | 1.11 / 7.10 | −4.38 / 0.92 | 0.024 | 0.040 | WATCH |
| Rizal | 2027-Q1 | 0.050 | 0.052 | 1.67 / 7.10 | −2.55 / 0.92 | 0.046 | 0.069 | WATCH |

The 2026-Q3 back-test rows (issued 2026-04-01, before any El Niño Advisory) are in the CSV. Observed 2026-Q3 was LOW in all five provinces.

**Exact causes of the decline:**
- **2026-Q3 → Q4:**
  - **Price projection:** the CPI projection fell further below each line, and headline inflation outran food, which makes the gap more negative.
  - **Configuration switch:** configuration 68, selected only at that origin, used its climate trees to pull Cavite, Rizal and Batangas down. Removing climate raises those three to 0.024–0.087.
- **Q4 → 2027-Q1:** a switch back to configuration 23, whose trees split on climate (5), employment (20) and OFW (15) and not on market features. The market signal enters through the CPI-projection offset (`tables/r1_A0_group_attribution.csv`).

**Climate inputs:**
- **Not forward-looking:** observed ENSO phase at t−1/t−2, observed typhoons, palay/corn production at t−1.
- **Reach the final model:** yes (2027-Q1: 5 climate splits, mean |SHAP| 0.046 logit).
- **Influence:** small.
- **Not represented:**
  - PAGASA's forward outlook (strong to very strong, through H1 2027);
  - rainfall, dry spell and drought indicators (no in-window series; the provincial rainfall file holds pre-2021 rows and is refused under the study window);
  - expected rice and vegetable price effects.

**Missing / stale / imputed inputs:**
- Remittances are missing at both 2026 issues (NaN, never 0).
- The 2026-Q3 typhoon count was incomplete at the 09-09 fetch and is stored as 0. Treating it as unknown changes no price part and moves P(HIGH) by less than 0.002 (`r1_typhoon_nan_sensitivity_2027Q1.csv`).
- SWS: 2026-Q2 (17.3%) was the latest posted round at the 10-01 issue.

**Is there a material risk the model fails to represent?** Yes, as a hazard: PAGASA's official outlook plus hunger at 17–22% is a documented climate-stress condition. The CFSW therefore flags all five provinces for 2026-Q4 and 2027-Q1.

**Why there is no forced HIGH:**
- One El Niño episode (2023–24) exists in the window, so no validated mapping from the outlook to a provincial HIGH exists.
- **What would have to happen for HIGH:** E65 showed HIGH needs projected food inflation of 5.5–8%.

**How the dashboard separates the two:**
- The model score and the watch are separate.
- In e67 mode, each LOW-under-watch province gets the plain sentence "Why the score is LOW although a climate watch is in force: …", with its own projection and line.
- The sentence also states that El Niño price effects are not in the score.

---

## 9. News pipeline integration and ablation

| Check | Finding | Source |
|---|---|---|
| Is the E60/E64 improved news in the serving model? | **No** in e58/e66/e67: the served model uses the E40 keyword shares. Pipeline v3 is served only in e64 mode, where at the 2027-Q1 origin config 23 uses no news (forecast = E56). | E64, E66 G |
| Improved classification F1 (0.38 → 0.83) gives forecasting gain? | **No.** E60-C 0.215, E64-D 0.204 vs E56 0.214 Brier; no difference by rule. | E66 F |
| News removed entirely (X_news) | Brier 0.212 vs 0.214, CI −0.007..+0.002, effect not distinguishable from zero | E67 `r3_trigger_group_effects.csv` |
| News only | significantly worse (Brier 0.445 / 0.507) | E66 |
| Thin signal | news_market 0.96, news_fish_kill 0.98, news_employment 0.98, news_ofw 1.00 exact-zero share at the evaluation origins; news_n never 0 (so these are measured zeros, not missing) | E67 `r2_coverage_summary.csv` |
| Relevance, attribution, duplicates, language, dates | classifier v2 P 0.92 / R 0.75 (AI-annotated); province from title geocoding; de-syndication in v3; Filipino/English titles; quarter from PH publication date, 0 errors in E62 | E60/E62/E64 |
| Issue-date availability | news of quarter t used only for issues after t; 2,118 of 2,132 E60 articles were collected after their issue date, so past coverage at issue cannot be reproduced exactly | E60, E66 G |

**Decision:** news stays a context and explanation layer. It is not forced into the model.

**Remaining work:**
- prospective collection, so coverage at each issue date is real;
- a human-checked annotation sample;
- lead text (authorized by the user in E31, but not yet integrated into the forecast features).

---

## 10. Five trigger groups: coverage, contribution, effect

Sources: `tables/r2_coverage_summary.csv`, `r2_coverage_by_group.csv`, `r1_A0_group_attribution.csv`, `r3_trigger_group_effects.csv`.

| Group | What the model actually receives | Geography | Latest at the 2027-Q1 issue | Missing at issue | Exact-zero share (eval) | 2027-Q1 splits / mean abs SHAP | Δ Brier when removed (95% CI) | Effect |
|---|---|---|---|---|---|---|---|---|
| Market / prices | food & headline CPI projection (offset), food YoY, gap, wholesale rice, 4 rice-policy flags | province (policy national) | CPI 2026-08; rice 2026-Q2 | none | policy flags 0.7–1.0 (calendar zeros) | 0 / 0 (enters via the offset) | market-only vs all: −0.002 (−0.021..+0.012) | not distinguishable |
| Climate | ONI phase t−1/t−2, typhoons, palay/corn YoY, 2 interactions | province (ENSO national) | ENSO 2026-Q2; typhoons 2026-Q3 (incomplete); crops 2026-Q2 | none (typhoon incompleteness coded 0) | ENSO 0.6–0.7 (neutral = 0) | 5 / 0.046 | +0.005 (−0.006..+0.018) | not distinguishable |
| Fish kill | PSA fisheries and aquaculture production YoY (**no fish-kill event series exists**) | province | 2026-Q2 | none | 0 | 0 / 0 | −0.004 (−0.010..+0.001) | not distinguishable |
| Employment | PSA LFS unemployment and underemployment YoY | **national** | 2026-Q2 | none | 0 | 20 / 0.245 | −0.003 (−0.013..+0.003) | not distinguishable |
| OFW remittances | BSP cash remittances (USD, PHP), USD/PHP | **national** | remittances 2025-Q4 | **yes** (remittances NaN since 2026-Q2) | 0 | 15 / 0.097 | −0.012 (−0.033..+0.005) | not distinguishable |
| News (per trigger) | E40 keyword shares + count | province | 2026-Q3 articles | none | 0.46–1.00 | 0 / 0 | −0.002 (−0.007..+0.002) | not distinguishable |

**Missing-data handling:**
- Unobserved values are NaN, and LightGBM routes them to a learned missing branch. They are never zero-filled.
- The one exception is the incomplete-quarter typhoon count (D-E66-5). The sensitivity above shows it has no material effect.
- The dashboard now states, in the existing sentence field and the new `triggerCoverage` field, which inputs were missing at issue and that they are treated as unknown, not as no risk.

**Honest reading:**
- At Lead-2, on 50 development rows, no trigger group shows a measurable contribution.
- The model's skill is the CPI projection.
- The non-price groups' tree effects are small and unstable across origins (configuration 68 vs 23).

---

## 11. LGU prioritization checks

| Check | Result |
|---|---|
| Coverage | 142 unique LGUs; Batangas 34, Cavite 23, Laguna 30, Quezon 41, Rizal 14; every LGU in its own province (`test_all_142_lgus_finite_mapped_and_consistent`) |
| Values | finite, in [0, 1], risk level in the approved set; index = province score × vulnerability (within 6e-5, 4-dp rounding) |
| Ranks | e67 uses exact ranks: 0 ties, 142 distinct region ranks |
| API vs dashboard | Quezon panel lists 41 LGUs with the same indices as the API (browser check, section 12) |
| Sensitivity | within-province order is robust to a 0.5–0.7 poverty weight (Spearman 0.96–0.97), not to dropping either component (E66 r6) |
| Lucena | 1st of 41 with the stored substitute, 22nd at the province minimum; source unverified (D-E66-4) |

**Meaning** (unchanged, stated in the API label):
- Within a province, rank = vulnerability rank; only the across-province order moves with the forecast.
- The output is a **relative prioritization**: not a municipal forecast, not validated, not an official classification.
- Independent LGU outcome data are unavailable.

---

## 12. Dashboard integration and demonstration

**What e67 shows** (the approved frontend is unchanged: no file in `frontend/` is modified, and there are no new UI elements, colours or legends):

| Item | Where |
|---|---|
| Dynamic Lead-2 target (2027-Q1 when viewed 2026-10-20) | existing timeline and banner |
| Province scores and colours | existing map (all LOW) |
| LGU list and map colours | existing panel and map |
| Drivers | existing bars and the summary sentence |
| Issue date, target, model version | existing note, plus `summary.modelIdentity` (API) and the sentence |
| Data freshness and missing inputs | existing `dataStatusNote`, plus `summary.triggerCoverage` and the sentence |
| Climate watch | `summary.climateWatch` and the sentence |
| Why a score is LOW under a watch | the sentence |
| Mock data | the five components that import `mockData.ts` are not rendered in the dashboard (four are unused; `SidebarPeek` is imported but not rendered in `Admin.tsx`); no static values are shown as predictions |

**Browser verification** (2026-10-20, local stack `aipheed-e67-stack`: API 8067 with `AIPHEED_LEAD2_MODEL=e67`, frontend 8097):
- Q1 2027 Forecast; regional index 0.08; 5 LOW provinces.
- Quezon 0.15 with 41 coloured LGUs.
- The right panel's summary contains "Why the score is LOW although a climate watch is in force…" and "Model: E56 LightGBM … configuration 23".
- **Pre-existing console errors:** "Wrong magic number for PMTiles archive" from `basemap.pmtiles`. They affect only the basemap tiles; the province and LGU layers render.

**Run locally:**

```
# from backend/
set AIPHEED_LEAD2_MODEL=e67
venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
# or the one-process preview stack (API 8067 + approved frontend 8097):
venv\Scripts\python.exe -B ..\aipheed-backend-aligned\experiments\E67_Lead2_Best_Model_Objectives_1_4\runner\serve_e67_stack.py
```

---

## 13. Tests run and actual results (2026-10-20)

| Suite | Command | Result |
|---|---|---|
| Backend full | `venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests` | **482 passed, 18 skipped, 0 failed** (72 s; `out/backend_full_suite.txt`). Before E67 (E66): 468 / 18. The +14 are the new E67 tests. |
| Backend, committed tree only (working copies of `insights.py` / `e41_lead2.py` swapped for the staged versions, the untracked E46 D-1 test excluded, then restored byte-identical) | same command `--ignore=tests/integration/test_e46_d1_attribution.py` | **473 passed, 18 skipped, 0 failed** (`out/backend_committed_tree_suite.txt`); the 9 fewer are the uncommitted D-1 tests |
| E67 tests | `tests/integration/test_e67_lead2_best_model.py` | 14 passed |
| Frontend unit | `npx vitest run` | 46 / 46 passed |
| Frontend build | `npx vite build` | passed (chunk-size warning only) |
| Type check | `npx tsc --noEmit -p tsconfig.app.json` | 6 errors, all pre-existing in `src/data/mockData.ts` (unchanged since E62) |
| Browser end-to-end | manual-scripted check, section 12 | passed (PMTiles basemap errors pre-existing) |

**What the E67 tests cover:**

| Area | Coverage |
|---|---|
| Protocol | frozen before scoring |
| Reproduction | A0 reproduces the sealed E57 forecasts (5e-13); served record = A0 |
| Lead-2 horizon | Lead-2 everywhere; dynamic target with no stale forecast |
| Goal test | outcome reported honestly |
| Trigger effects | not distinguishable |
| Missing data | inputs not zero-filled; typhoon sensitivity; missing inputs read as unknown in the API |
| Disclosure | built from the E67 tables, with an integrity hash; an absent disclosure degrades to E66 |
| Numbers vs e58 | e67 numbers equal e58 |
| Default | production default unchanged |
| Model identity | per issue (configurations 23 and 68) |
| LOW-under-watch text | numbers match the record |
| Climate statements | only items before the issue date |
| LGUs | 142 finite, mapped, exact ranks |

---

## 14. Failures and unresolved limitations

| ID | Severity | Issue | Status |
|---|---|---|---|
| F-1 | High | **> 75% Lead-2 accuracy not legitimately met.** Best reading 0.78 (EW), not distinguishable from always-LOW (0.64) at the quarter level, and designed after seeing the rows | Unresolved: needs unseen quarters and more events |
| F-2 | High | Target = provincial price pressure (T43 ≡ PS on all evaluated rows); no provincial food-insecurity outcome | Disclosed; needs adviser decision + data (section 15) |
| F-3 | High | No forward climate input; El Niño risk represented only by the unvalidated CFSW | Disclosed; pre-registration needed before 2027-01-01 |
| F-4 | High | Objective 2 V: no reliable horizon; "reliable" undefined | Adviser definition |
| F-5 | Medium | Over-confident probabilities (slope 0.55) | Disclosed ("model score, not a tested probability") |
| F-6 | Medium | Configuration switching between origins (23 → 68 → 23) moves scores without data change | Disclosed; stable selection not better (E64) |
| F-7 | Medium | Remittances missing since 2026-Q2 (BSP file ends 2025-Q4); employment/OFW national only | Disclosed; BSP download needed |
| F-8 | Medium | News trigger shares almost always 0; the improved pipeline is not in the served model | Disclosed; prospective collection |
| F-9 | Medium | Lucena poverty substitute unverified | Disclosed in API |
| F-10 | Low | D-E66-5 typhoon incomplete quarter coded 0 (no material effect) | Fix in the next record build (NaN) |
| F-11 | Low | 6 pre-existing TypeScript errors in mock data; PMTiles basemap console errors | Unchanged (no frontend edits) |
| F-12 | Low | scikit-learn 1.7.2 pickles under 1.8.0 (warnings) | Unchanged |

---

## 15. Data needed to improve validation

1. **Provincial or municipal food-insecurity outcomes** 2021–2026: CBMS food items, provincial FIES, DSWD/LGU caseloads. This is the single most important item; without it the target stays price pressure.
2. **Unseen outcomes** for the sealed 2026-Q4 and 2027-Q1 forecasts: PSA CPI for Oct 2026 to Mar 2027, and SWS rounds for Q4 2026 and Q1 2027.
3. **BSP OF remittances** for 2026, and provincial employment (LFS provincial estimates) if published.
4. **In-window rainfall and drought indicators:** PAGASA dry-spell/drought assessments as dated documents (2021–2026), plus an archive of PAGASA ENSO outlooks with issue dates, so a forward climate input can be pre-registered and tested.
5. **A PSA HUC poverty estimate for Lucena,** or the documented source of the substitute.
6. **Prospectively collected news** with lead text, and a human-checked annotation sample.

---

## 16. Remaining work to satisfy the approved objectives

- **Obj 1:**
  - human validation of the relevance and FSSI labels;
  - prospective corpus;
  - an explicit decision on whether FSSI-v3 is a dashboard indicator only (current evidence) or a model input.
- **Obj 2:**
  - score the sealed 2026-Q4 and 2027-Q1 forecasts when outcomes are released;
  - adviser definition of "reliable";
  - re-run the multi-lead study with the new quarters.
- **Obj 3:** validated province forecasts (depends on Obj 2); DA evaluator check of the rankings; the Lucena source.
- **Obj 4:** repeat the baseline comparison on the unseen quarters with the same frozen rule.
- **Adviser decisions:**
  1. declare PS + separate hunger indicator vs keep T43 wording;
  2. accept the CFSW as a hazard watch;
  3. pre-register a forward climate input;
  4. exact ranks as the default;
  5. whether e67 becomes the default.

**Recommendation:** pre-register before 2027-01-01 (the next origin) a forward-climate arm that adds PAGASA advisory status and outlook strength at issue. It should be scored prospectively only.

---

## 17. Push, preview and deployment steps

| Step | Command | Done? |
|---|---|---|
| Fetch and verify the starting branch on origin | `git fetch origin`; `git ls-remote --heads origin aiPHeed/best-model-methodology-review` | **Done** (1ac3444, in sync) |
| Create the new branch | `git switch -c best-model-objectives-1-4-lead2` | **Done** |
| Commit E67 (own hunks only; E46 D-1 hunks stay uncommitted) | see `out/commit_record.txt` | see that file |
| Push | `git push -u origin best-model-objectives-1-4-lead2` | see `out/commit_record.txt` |
| Verify | `git ls-remote --heads origin best-model-objectives-1-4-lead2` must equal the local `git rev-parse HEAD` | see `out/commit_record.txt` |
| Local preview | section 12 | **Done** (browser check) |
| Preview deployment (needs authorization) | deploy this branch to a preview service with env `AIPHEED_LEAD2_MODEL=e67`; the frontend build needs `VITE_API_BASE_URL` set to that API | **Not done** (no authorization or access) |
| Production switch (needs user and adviser authorization) | set `AIPHEED_LEAD2_MODEL=e67` on the production API service after merging; no code change needed | **Not done**; production default stays E38 |

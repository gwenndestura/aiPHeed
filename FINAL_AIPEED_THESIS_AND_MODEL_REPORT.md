# aiPHeed: final thesis and model report

**Date:** 2026-10-20 · **Branch:** `final-aipheed-thesis-e72` · **Evidence folders:**
- `aipheed-backend-aligned/experiments/E70_Objectives_Completion` (model improvement attempt)
- `E71_Food_Insecurity_Dimensions` (dimensional target)
- `E72_Final_Thesis_System` (served-system audit and integration)
- Companion documents: `FOOD_INSECURITY_DIMENSIONAL_FRAMEWORK_AND_REDESIGN.md` (framework, evidence matrix, E71 detail), `FINAL_OBJECTIVES_COMPLETION_AND_MODEL_VALIDATION_REPORT.md` (E70 detail), `FINAL_IMPLEMENTATION_AND_TEST_REPORT.md`.

## Summary

aiPHeed now estimates an **exploratory, evidence-weighted food-insecurity risk index (FIRI v2)** for each CALABARZON province, two quarters ahead. It explains every estimate exactly along the food-security dimensions and keeps the observed regional hunger outcome visibly separate from the contributing factors.

**What it is not.** It is not a validated food-insecurity forecast at the provincial or municipal level, and no available data could make it one.

**The 80% Lead-2 goal is not independently supported:**

| Target | Lead-2 result | Why it does not count |
|---|---|---|
| Regional SWS hunger (the only direct outcome) | 16/17 quarters = 0.94 | Development quarters; regional only; not credibly better than always-elevated or the latest hunger reading |
| Provincial price-pressure label (T43) | 0.72 | A price label, not food insecurity |
| E71 outcome-free dimensional target | 0.64 | The index did not track the measured outcomes |

**Objectives 1–4:** none fully met (§9). Production is unchanged.

---

## 1. Audit of the project before the final changes

| Question | Verified finding |
|---|---|
| Production default | **E38** (`AIPHEED_LEAD2_MODEL` unset). Unchanged. |
| Thesis system | `AIPHEED_LEAD2_MODEL=thesis` (with `AIPHEED_STRICT_MODEL=1`) serves **FIRI v2** (pre-registered candidate C3, `FIRI2_PROTOCOL.md` frozen before scoring) as the province value. **E56-TUNED LightGBM** (food-price pressure, Lead 2) is one affordability indicator (A1) inside it. |
| Reuse of quarters | Every quarter 2021-Q1 … 2026-Q3 has been examined in more than 30 experiments (E38–E72). **No historical quarter is held-out evidence.** E70 tested 16 arms and E71 9 arms; all were pre-registered and none was promoted. |
| What each output represents | SWS hunger = direct outcome (regional). T43 / E56 = food-price pressure (access driver). FIR71 = outcome-free contributing-factor index (E71). FIRI v2 = integrated proxy risk index (contributing factors + vulnerability + regional outcome evidence). News FSSI = signal. LGU values = vulnerability-weighted prioritization. |
| Changes that improve the research system | Pre-registration, sealing, leakage tests, clean reproduction, the dimensional framework, the faithful explanation, and honest labels. |
| Changes that only improved scores on examined data | None adopted. The E58/E66 timing gains and E70 ablation highs (0.74) were not promoted. |

---

## 2. Food-insecurity framework

The framework follows the FAO definitions (World Food Summit 1996; Policy Brief 2006) and the four dimensions: availability, access, utilization and stability. HLPE (2020) adds agency and sustainability. Following IPC 3.1 and WFP CARI, **outcome evidence** (experienced hunger, FIES) is kept separate from **contributing factors** (dimensions, hazards, vulnerability). Vulnerability and shock exposure are cross-cutting, not interchangeable with the dimensions. Composite construction follows OECD/JRC (2008). Measurement principles follow Barrett (2010) and Upton, Cissé and Barrett (2016). Full text, the CALABARZON fit and the references are in the framework document §1.

**Safeguards adopted:**
- Prices inform **access** only.
- Production and fisheries inform **availability**.
- Typhoons and El Niño inform **stability**.
- Poverty and density are **vulnerability**.
- **Utilization is not observed** and is never imputed.
- Missing ≠ low risk.
- Regional outcomes stay regional.

---

## 3. Targets and their limitations

| Target | Definition | Finding |
|---|---|---|
| T43 | SWS hunger > 11.3 AND provincial food-price condition | **Collapses to price pressure** on 155/155 rows: the hunger gate is constant (always above 11.3 and every 2021–22-anchored threshold). Mostly driven by food-minus-headline. |
| DIRECT-R | SWS Balance Luzon hunger > 11.3 at the target quarter | The only direct outcome. Regional, 17 Lead-2 quarters; above the threshold in 12. |
| FIR71 (E71) | Mean of access, availability and stability scores (percentiles vs 2021–22); HIGH above the 2022 P60 | Does not collapse into price (equals the price condition on 48/90 rows). **Does not track outcomes:** ρ with SWS hunger −0.21 [−0.68, +0.35]; ρ with subsistence −0.40 / −0.87. |
| **FIRI v2 (served)** | Six domains vs their own earlier values, weighted walk-forward by agreement with earlier SWS rounds; HIGH at 0.50 | Mixed evidence (§5). Its outcome agreement is driven partly by its own regional hunger domain. |

**Conclusion.** No provincial target with repeated, measured food-insecurity outcomes exists in the data. The defensible output is a **named proxy risk index with exact dimensional explanation**, not a validated forecast.

---

## 4. Dimension-to-evidence matrix

The full matrix (source, level, coverage, delay, type, Lead-2 role, limitations, validation needed) is in the framework document §2.

Coverage by evidence group:
- **Market/prices:** access (province).
- **Climate:** stability (province typhoons; national ENSO/drought alerts).
- **Fisheries:** availability (volumes; fish-kill events not dated).
- **Employment:** access (national only).
- **Remittances:** access (national; 2026 missing).
- **Poverty/density:** vulnerability (static).
- **News:** signal (thin, English, retrospective).
- **Utilization:** none.

---

## 5. Final architecture and model selection

| Layer | Final implementation |
|---|---|
| Observed outcome | SWS regional hunger, latest published reading and its outlook (shown as regional, "no provincial figure exists") |
| Dimensions | FIRI v2 indicators re-grouped exactly by role (`app/ml/inference/dimensions.py`): ACCESS (A1–A3, E1, E2), AVAILABILITY (C3, C4), STABILITY (C1, C2), UTILIZATION (not observed) |
| Vulnerability | V1 poverty and density (index domain); poverty and density weights for LGU prioritization |
| Integrated estimate | **FIRI v2**, unchanged, named "exploratory proxy risk index" |
| Lead-2 forecast | FIRI v2 for target t+2 from information published before the issue date; E56 LightGBM inside A1 |
| Validation | E70 (T43), E71 (outcome-free index vs SWS / subsistence), E72 (FIRI v2 vs regional SWS) + sealed prospective forecasts |

**Why FIRI v2 is kept as the served estimate:**
1. It was pre-registered before scoring. Changing it again now would be another post-hoc choice on reused quarters.
2. It is the only candidate whose estimates agree with the measured outcome. Following IPC, it combines outcome evidence with contributing factors.
3. Its explanation is exactly additive and interpretable.
4. The alternatives failed:

| Alternative | Result |
|---|---|
| E56 LightGBM | Predicts price pressure only |
| FIR71 / DIMFUSE | Contributing factors alone did not track hunger |
| LR, PSA-only, NLP-only | No credible advantage |
| A1, A2, S0, ablations | Failed the pre-registered rules |

**Its main weakness, disclosed in the API, text and PDF:** observed regional hunger (H1) is both an input and the only validation outcome. Of the index's movement:

| Role | Share of movement |
|---|---|
| Access | 26% |
| Observed regional hunger | 27% |
| Stability | 22% |
| Vulnerability | 12% |
| Availability | 11% |
| News | 1% |

Regional hunger is the largest push in 38 of 64 HIGH rows. 17 HIGH rows would be LOW from the provincial evidence alone (`indexWithoutRegionalHunger`, diagnostic only).

---

## 6. Results

### 6.1 Direct outcome (regional SWS hunger > 11.3%), served FIRI v2 (E72 `out/regional_outcome.json`; development quarters)

| Lead | Quarters (above 11.3) | FIRI v2 | Always elevated | Hunger outlook alone (H1) | FIRI vs always: McNemar | FIRI vs H1: Δ Brier [95% CI] |
|---|---|---|---|---|---|---|
| 1 | 18 (13) | 16/18 = 0.889 [0.67, 0.97]; balanced 0.92 | 13/18 | 13/18 | 5/2, p 0.45 | +0.059 [+0.013, +0.100] (FIRI worse) |
| **2** | **17 (12)** | **16/17 = 0.941 [0.73, 0.99]**; balanced 0.96; LOW recall 5/5; Brier 0.189 | 12/17 | 12/17 | 5/1, p 0.22 | +0.027 [−0.072, +0.114] |
| 3 | 16 (12) | 13/16 = 0.812 | 12/16 | 12/16 | 4/3, p 1.0 | +0.044 [−0.040, +0.122] |

FIRI v2 credibly beats climatology at every lead (McNemar p ≤ 0.016). It does not beat always-elevated or the hunger reading.

### 6.2 Provincial price-pressure label T43: E56 LightGBM (E70 §6)

| Lead | Rows | Accuracy | Prec H | Rec H | F1 H | Bal | AUC | Brier | Cal. slope |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 60 | 0.850 [0.74, 0.92] | 0.833 | 0.714 | 0.769 | 0.819 | 0.901 | 0.130 | 0.97 |
| 2 | 50 | 0.720 [0.58, 0.83] | 0.625 | 0.556 | 0.588 | 0.684 | 0.649 | 0.214 | 0.55 |
| 3 | 45 | 0.622 | 0.400 | 0.429 | 0.414 | 0.569 | 0.620 | 0.251 | 0.25 |

- **Confusion matrix, Lead 2:** TP 10 / FP 6 / FN 8 / TN 26.
- **Per province** (correct of 10; HIGH found): Batangas 7 (1/3), Cavite 4 (1/4), Laguna 7 (3/5), Quezon 8 (5/6), Rizal 10 (no HIGH).
- **Per period:** 18/30 in 2024-Q2 … 2025-Q3 vs 18/20 in 2025-Q4 … 2026-Q3.

### 6.3 Outcome-free dimensional target FIR71 (E71 §6)

| Lead | Best arm | LightGBM | Persistence |
|---|---|---|---|
| 2 | DIMFUSE 29/45 = 0.644 (Brier 0.225; beats persistence, CI < 0) | 0.489 | 0.578 |
| 1 | PSA-only LR 0.691 | 0.491 | 0.545 |
| 3 | Persistence 0.650 | 0.350 | 0.650 |

**Reliable horizon:** none under the pre-set criterion, on any target.

---

## 7. Leakage, overfitting, bias, ablation, robustness

- **Leakage.** E57/E70 corruption tests (every value published after the issue date randomised) change no forecast (≤ 5e-13). Seals were made before labels were read. Clean `git archive` reproductions are byte-identical (E70, E71).
  - Not excludable by code: latest-vintage PSA data; retrospective news collection (687/695 headlines first seen after their issue date); research-level selection across more than 30 experiments.
- **Overfitting.**
  - Over-confidence from Lead 2 on (slope 0.55).
  - 9 configurations in 10 origins.
  - Accuracy falls with lead.
  - Winner's-curse risk on best-of-k figures (E70 0.74, E71 0.64). Neither was promoted.
- **Ablations.**
  - No evidence group adds measurable out-of-sample value to the price model. All removal CIs include 0.
  - Removing news makes no difference: E70 Δ −0.002; E71 Δ +0.002.
  - The CPI base-effect projection alone matches the LightGBM.
- **Bias.**
  - HIGH misses concentrate in Cavite, Batangas and the 2024-Q2 regime change.
  - News is skewed toward Cavite and Batangas. Rizal has 0 articles in 17/23 quarters. Filipino headlines: 7/695.
  - National and regional inputs are repeated across provinces (ICC 0.29–0.63; effective n ≈ 13–23).
  - Remittances are missing in 2026. The Lucena poverty value is an unverified substitute.
  - LGU colours read "lower" than their province (multiplicative display band; documented).
  - Missing inputs are reported as missing, never zero.
- **Robustness of FIR71:** threshold P50/P75, gap variant and leave-one-dimension-out agree 68–86/90.

---

## 8. Explanation validation

| Explained output | Method | Check |
|---|---|---|
| FIRI v2 (served) | Exact additive breakdown: indicator push = weight × (score − 0.5) / indicators in its domain; grouped into the five approved bars and, new in E72, into the food-security dimensions | Reconstruction ≤ 2e-6 on all 95 rows (stored rounding), ≤ 5e-4 through the API (4-dp index). `test_e72_dimensions.py` |
| E56 LightGBM (inside A1) | Exact TreeSHAP (LightGBM `pred_contrib`) | `test_e56_final_model.py::test_treeshap_reconstructs_and_note_is_e56` |

**Faithful labelling (backend text only, per the approved-design rule).**
- Factor-card and region-card texts now say the bars are "an additive breakdown of the FIRI v2 index … not TreeSHAP values".
- They also say the bars show how the index was formed, "not what causes food insecurity".
- The headline now reads "exploratory proxy risk index".

**Still for your decision.** The approved panel *headings* still read "SHAP". They were not changed, because the frontend design is approved and frozen.

**What each explanation carries:**
- the target quarter and issue date;
- raised/lowered factors with values, period and status (observed / missing / insufficient history / incomplete);
- the dimension of each factor;
- regional and national flags;
- missing evidence;
- "not a probability, not a measured rate".

**Browser check (2026-10-20).** The thesis API and dev UI agree for Batangas 2027-Q1: map 0.71 HIGH = API 0.712481; new card and headline text rendered; 34 LGUs drawn. The only console error is the known basemap PMTiles message.

---

## 9. Objectives (approved wording verbatim; Chapter I §1.5)

| # | Approved wording | Implemented | Tests | Measured result | Limitation | Status |
|---|---|---|---|---|---|---|
| 1 | "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus." | `pipeline_v3`, FSSI-v3, BERTopic, served; human-validation workflow (300 blind headlines, 2 annotator files, weighted P/R/F1 + κ scorer) | E70/E71 annotation tests (synthetic labels only), backend news tests | News adds no measurable forecast value | No human labels yet; bias correction has no reference; 7/695 Filipino; thin coverage | **PARTIALLY MET** |
| 2 | "To evaluate the performance of the proposed LightGBM forecasting model using the following metrics: I. Accuracy … II. Precision and Recall … III. F1-Score … IV. AUC-ROC … V. Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable" | All metrics, Leads 1–3, walk-forward, sealed, reproducible | E70/E71 seal, timing and decision tests; leakage tests | §6 | Its target is price pressure; no reliable horizon; development data only | **PARTIALLY MET** |
| 3 | "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights." | 142 LGUs, 0.6 poverty + 0.4 density, labelled relative prioritization | `obj3.py` (E72 re-run), thesis tests | 142/142 complete, finite, mapped, consistent; served values unchanged | Province forecasts not validated; no LGU outcome (CBMS) | **PARTIALLY MET** |
| 4 | "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline" | Identical rows, two-sided tests, Holm, cluster bootstrap | E70/E71 scorers | On T43: credibly better only than IV. On FIR71: better than none. | Small n; reused quarters; price label | **PARTIALLY MET** |

**Fully met: none.** **Not met: none outright.** Every objective has a working, tested implementation. Each lacks the validation evidence its wording requires.

---

## 10. The 80% target: honest account

- **Price label T43 (provincial, 50 rows):** 0.72.
- **Outcome-free dimensional target FIR71 (45 rows):** 0.64.
- **Direct regional outcome:** 0.94 (16/17). It is above 80%, but:
  1. the quarters were examined while FIRI v2 was designed;
  2. it is one regional value per quarter;
  3. it is not credibly better than always-elevated (12/17) or the latest hunger reading;
  4. its probabilistic score (Brier) is not better than the hunger reading.

**Verdict:** 80% Lead-2 accuracy is **not independently supported** on any defensible target. It must not be reported as achieved food-insecurity accuracy.

**Prospective test.** Forecasts are sealed for 2026-Q4 and 2027-Q1:

| Seal | Content | sha |
|---|---|---|
| E68 | — | 79aa6f2a |
| E69 | — | e6b6266f |
| FIRI2 | FIRI v2 | e2bef0b2 |
| E70 | R0, A1, A2, S0 | 31f73040 |
| E71 | FIR71 arms | 1e729585 |

Score them after PSA publishes Oct 2026–Mar 2027 data and SWS publishes the 2026-Q4/2027-Q1 rounds, without revising any prediction.

---

## 11. Limitations and next validation requirements

1. **No local outcome.** CBMS 2022/2024 FIES for the 142 LGUs (from LGUs / PSA RSSO IV-A) is the single most important acquisition.
2. **Provincial anchors.** FNRI NNS 2023 provincial FIES; the primary 2025 FIES table.
3. **Missing access drivers.** Provincial income and livelihood series (provincial LFS, DOLE, DSWD DROMIC).
4. **Utilization data.** OPT Plus, WASH.
5. **Fisheries.** Dated BFAR fish-kill advisories.
6. **Human labels** for the news sample.
7. **Prospective scoring** of every seal, and continued quarterly sealing. About 20 or more unseen quarters are needed for any accuracy claim.
8. **Decisions for you and your adviser:**
   - whether to remove H1 from FIRI v2, so that SWS becomes an independent validation outcome;
   - whether to rename the "SHAP" headings in thesis mode;
   - whether LGUs should be coloured by the province band.

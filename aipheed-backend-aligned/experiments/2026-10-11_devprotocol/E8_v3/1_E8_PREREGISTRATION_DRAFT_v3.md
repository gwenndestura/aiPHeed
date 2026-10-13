# E8 Pre-registration DRAFT v3: Historical-Simulation Comparison of Core, M6 and Carry-forward

**Status: DRAFT v3. NOT approved, NOT frozen, NOT executed.**

| Item | Value |
|---|---|
| Prepared | 2026-10-12 |
| Supersedes | E8 v1 and v2, both preserved unchanged as historical drafts |
| Companion documents (this folder) | `2_HISTORICAL_SIMULATION_AND_LEAKAGE_CHECKLIST.md`, `3_PROTECTED_DATA_ACCESS_CHECKLIST.md`, `4_SCHEDULED_TASK_REVIEW.md`, `5_APPROVAL_CHECKLIST.md`, `6_INTEGRITY_VERIFICATION_REPORT.md` |

**Not done:** no forecast, label, model fit, rescoring, outcome access, production change, served-model change or scheduled-task change.

**Changes from v2:**

1. **Historical simulation, not prospective forecasting** (§3). Both cutoffs have passed. Every input is classified as verified, unverified or excluded. Unverified inputs are excluded from leakage-safe claims.
2. **Exact file-level protected boundary** (§4 and checklist 3).
3. **Gross-failure margins are justified a priori** (§8.1) and apply **only if approved** (approval item A4).
4. **M6 stays served.** Core is a *provisional simpler alternative*: not validated, and not switched without separate approval (§9).
5. **Scheduled-task review** with a recommended action **awaiting approval**. No risk is accepted on your behalf (checklist 4).

---

## 1. What is forecast, and what is not validated

**The outcome is the Equation 3 stress indicator:**

- stress(p, T) = SWS Balance-Luzon hunger_T + 2 × (provincial food CPI YoY(p, T) − five-province mean_T);
- the event is stress > τ = 14.345, frozen from the 16 labelled quarters of 2021–2025 published before 2026-07-01.

**It is a constructed proxy.** E8 measures agreement with it. It does **not** validate food insecurity against an independent observed outcome, because none exists at province level.

**Required wording:**

- overall results: "forecasts the Equation 3 stress indicator";
- ranking results: "orders provinces by relative food-price pressure";
- **never** "predicts food insecurity".

## 2. Arms (fixed now; no tuning)

**Common LightGBM settings for A1–A4:**

- `num_leaves=4`, `min_child_samples=5`, 100 trees, `learning_rate=0.05`, seed 42;
- no class weights;
- monotone +1 on `sws_hunger` and `last_published_stress` only;
- NaN kept;
- training-only filter: drop a feature that is more than 50% missing or constant in training.

**Each arm is fitted as a classifier (event) and as a regressor (stress), with the same inputs.**

| Arm | Inputs | Role in E8 |
|---|---|---|
| **A1 Core** (provisional simpler alternative) | `sws_hunger`, `sws_change`, `last_published_stress` | Primary arm |
| **A2 Core + provincial government** | A1 + `cpi_rel`, `cpi_rel_lag1`, `cpi_dev`, `food_cpi`, `food_cpi_yoy` (+lag1, accel), `poverty_incidence`. **Rice price is excluded** pending the forward-fill fix (checklist 2, item C3). | Primary arm (added-value question) |
| **A3 M6 without news** | Training-only selection over core + subsets of {provincial government, national government}. National government is included only if approval A5-GN (ii) is given; otherwise the selection is over core + provincial government. Rice is included only under A5-rice (ii). | Primary arm |
| A4 M6 as served (with news) | Served configuration | Descriptive only, unless the news rule (§6) is met |
| **B1 Carry-forward stress** | Last published stress | Primary baseline |
| B2 Carry-forward provincial gap | Latest published `cpi_rel` | Ranking baseline |
| B3 Equation 3 origin rule | SWS input + 2 × `cpi_rel` | Overall and ranking baseline |
| B4 Regional-only | SWS input | Overall baseline. No ranking ability by construction. |
| B5 Always-HIGH, always-LOW | — | References |

## 3. Historical-simulation design

**Status:** the cutoffs, **2026-07-01** (target 2026-Q3) and **2026-10-01** (target 2026-Q4), are in the past. E8 forecasts are **historical simulations**: computed now, using only information that was **demonstrably** available before each cutoff.

| Rule | Requirement |
|---|---|
| H1 | A value is usable only if its **publication date is documented** and **strictly before** 00:00 Asia/Manila on the cutoff date. **A value is never inferred to have been available merely because it appears in a dataset.** |
| H2 | Each input is tagged **verified** (the registry records a dated primary or archived source; "verified-single" means one such source, counted as verified and disclosed), **unverified** (a proxy date or a schedule-based date) or **excluded** (unknown date). Checklist 2, §A, lists every input. |
| H3 | **Simulation validity status:** a simulation is "leakage-verified" only if **every** input and training label it uses is verified. Otherwise it is "proxy-dated (unverified)" and is **excluded from any claim of leakage-safe performance**. |
| H4 | **Expected status: both simulations are proxy-dated (unverified)** for every arm except B4. Provincial CPI release dates (RSSO IV-A) are unverified for every month, and every training label's availability depends on them. The margins are large (71–162 days), but **margin is not verification**. Approval item A3 would allow the RSSO dates to be verified. |
| H5 | **Training labels:** 2021-Q2 to 2025-Q4, 16 quarters, all published before C3. The latest, 2025-Q4, has a proxy date of 2026-01-20 (unverified). **No 2026 label is built.** This is a design restriction, not an availability fact: the 2026-Q1 label would have been computable by 2026-05-12 (SWS verified; provincial CPI proxy 2026-04-21). Excluding it keeps the exposed 2026 quarters out of training. As a result `last_published_stress` is the 2025-Q4 value at both cutoffs: less information than a real-time forecaster had, not more. Changing this needs approval A6. |
| H6 | **Inputs:** complete quarters only. Government series refer to T−2. SWS is the latest round with a documented publication date before the cutoff. **The September 2026 round and July–December 2026 CPI months are never inputs** (protected, §4). |
| H7 | **Feature engineering:** inputs come from an **allowlist-only prospective frame** (approval A5). No forward-fill. NaN kept. Rolling and lag features use only quarters before the row's own quarter. Checklist 2, §C, covers the known residual issues. |
| H8 | **Design choices:** all fixed from 2021–2025 data and earlier analyses, before any 2026-Q3/Q4 outcome existed or was seen. None uses blind-quarter information. Checklist 2, §D. |

## 4. Protected-data boundary (summary; file-level detail in checklist 3)

**Protected:** must not be opened, parsed, printed, aggregated or used until the forecasts for that quarter are frozen **and** outcome collection is separately approved (approval A9).

| # | Protected item |
|---|---|
| P1 | SWS hunger estimates from any round with fieldwork from 2026-07-01 to 2026-12-31 |
| P2 | Food CPI and food CPI YoY (provincial, regional, national) for reference months 2026-07 to 2026-12 |
| P3 | Files known to contain P1/P2 rows |
| P4 | Anything derived from P1/P2 |

**Also treated as protected (precaution):** files whose coverage **cannot be verified without reading content** ("potential carriers").

**Permitted on protected and potential-carrier files:** path, size, modification time, git commit metadata, and SHA-256 of the bytes. **Nothing else.**

**Disclosed earlier exposure (carried over from v2; nothing new in v3):**

- On 2026-10-11 one aggregate was printed from a P3 file: the 2026-Q1 to Q3 production `label_cpi` HIGH share, 0.93.
  - It mixes exposed Q1/Q2 rows with protected Q3 rows.
  - `label_cpi` is the production index-trend label, not Equation 3. The aggregate reveals no Equation 3 component, but it is weak information about 2026-Q3 CPI index levels.
  - It is disclosed and will not be used.
- The SWS March 2026 and June 2026 values and the January–June 2026 provincial CPI are **exposed, not protected**. They may be inputs where timing permits, never evaluation outcomes. The June 2026 round's publication date is unknown, so it is not an input (H1).

## 5. Evaluation split and exposure

| Set | Quarters | Exposure | Use |
|---|---|---|---|
| Training | Labels 2021-Q2 to 2025-Q4 (published before the cutoff) | — | Fitting only |
| Reused history | 2023-Q4, 2024-Q1–Q4, 2025-Q1, 2025-Q4 | Evaluated in E1–E7 | Excluded from every conclusion |
| Exposed, descriptive only | 2025-Q2, 2025-Q3 | **Both label components seen**: SWS values collected and reported 2026-10-09; the provincial component d was the E2 test target (2026-10-11) | Optional descriptive check; **never part of blind-test conclusions** |
| Exposed, descriptive only | 2026-Q1, 2026-Q2 | Outcomes in the production SWS table and the collected CPI | Optional descriptive check; excluded |
| **Blind** | **2026-Q3, 2026-Q4** | Protected | **The only basis for conclusions** |

**Basis for conclusions:** **two regional-quarter observations**, not ten independent provincial observations. Ranking evidence is 2 × 10 within-quarter province pairs, and those pairs are themselves dependent.

## 6. News sufficiency rule

**Definition.** A province-quarter is news-sufficient if it has at least 5 articles that are all of the following:

- rated relevant by XLM-RoBERTa;
- geocoded to the province;
- deduplicated by normalized title;
- with a parseable in-quarter publication date.

**News enters the primary comparison only if:**

1. at least 80% of 2021–2025 province-quarters are news-sufficient; **and**
2. all five provinces are news-sufficient in the news input quarter (T−1) of each blind simulation.

**Current status:** 0/100 (E7). News is excluded from the primary comparison, and A4 is descriptive only.

## 7. Two separate questions (never combined)

### 7.1 Overall stress forecasting

**What it is:** mostly the **shared regional level** (SWS_T accounts for about 65% of historical stress variance). It says nothing about individual provinces.

**Unit:** the quarter.

**Metrics:**

- **classifiers:** mean Brier over the five provinces, and HIGH / LOW / INSUFFICIENT counts;
- **regressors:** regional-level error |mean predicted stress − SWS_T|, and MAE.

### 7.2 Within-quarter provincial food-price ranking

**What it is:** only the provincial component d(p, T). **It is not a food-insecurity ranking.**

**Unit:** within-quarter pairs.

**Metrics:**

- concordant pairs out of 10 between each arm's score and the observed d (ties count ½);
- Kendall τ-b;
- whether the arm identified the top province.

**B4 and B5 have no ranking ability by construction.**

### 7.3 Reporting rules

| Rule | Detail |
|---|---|
| Per quarter only | Each blind quarter is reported separately |
| No inference | No pooled estimates, p-values, confidence intervals or bootstrap |
| Validity status | Every result carries the simulation-validity status from H3 |
| Threshold | **Fixed at 0.50.** Probabilities are **uncalibrated** and labelled as such. No score, threshold or calibration is fitted on any evaluation quarter. |

## 8. Permitted conclusions (only these)

### 8.1 Gross-failure detection

**These criteria apply only if approval A4 accepts the margins.** If they are not approved, gross failure is **not assessed** and only per-quarter values are reported.

An arm is flagged as a gross failure only if the condition holds in **both** blind quarters:

| Question | Proposed criterion | A-priori justification |
|---|---|---|
| Overall (classifier) | Quarter-mean Brier worse than B1 by **more than 0.10** | An uninformative forecast (p = 0.5 for every province) scores Brier 0.25. A shortfall of 0.10 is 40% of that uninformative score: a large deficit, not noise in a 5-row average. |
| Overall (regressor) | Regional-level error worse than B4 (SWS input) by **more than 6.0 stress points** | The quarter mean of stress equals the SWS value, so this error is an error in forecasting a survey estimate. The worst-case 95% sampling margin of a proportion is 1.96 × √(0.25 / n): **4.0 points at n = 600 and 5.7 points at n = 300.** A shortfall inside that band cannot be told apart from survey noise, so the margin is set at 6.0. Balance-Luzon sample sizes per round are **not verified here**. If they are larger, the margin is conservative. (v2 proposed 3.0; that is inside the sampling band, so v3 replaces it.) |
| Ranking | **3 or fewer** concordant pairs out of 10 | With 5 provinces, a random ordering gives ≤ 3 concordant pairs with probability 29/120 = 0.24 per quarter (Mahonian distribution), so about 0.06 in both quarters. The flag therefore marks orderings that are systematically inverted, which a random ranker would rarely produce twice. |

- **Otherwise the result is "no gross failure detected".** That does **not** mean good performance.
- **If A1 is flagged on overall:** "the core LightGBM did not beat persistence in either blind quarter".

### 8.2 Is added value demonstrated?

**Comparisons:**

- A2 vs A1 (provincial government indicators);
- A3 vs A1 (data-driven selection).

**Bar for "demonstrated":** better than A1 **and** the relevant carry-forward baseline in **every one of at least 8 blind quarters**.

**E8 has 2 blind quarters. Every added-value result is "not demonstrated".** E8 reports only whether the two quarters are consistent or inconsistent with added value. That is descriptive.

### 8.3 Not permitted

- Statistical superiority or significance.
- "Best model".
- Pooled province-row accuracy.
- Any food-insecurity claim.
- Any leakage-safe claim for a simulation that H3 marks unverified.

## 9. Model decisions

| Item | Rule |
|---|---|
| Served model | **M6 remains the served model** in the isolated backend through and after E8 |
| A1 Core | A **provisional simpler alternative**. Not validated. E8 cannot validate it (§8.2). |
| Switching | Any switch (M6 → A1 or another arm) needs **separate approval (A10)** after E8, citing only §8 conclusions. Nothing switches automatically. |
| Classification | Fixed at **0.50**: HIGH ≥ 0.50; LOW < 0.50; INSUFFICIENT_DATA if a required input is missing or stale |
| Probabilities | **Uncalibrated** and labelled as such |

## 10. Execution sequence (each step needs its own approval; see checklist 5)

| Step | Action | Approval |
|---|---|---|
| 1 | Protocol approval | A1 |
| 2 | Data checks and access controls | A2–A6 |
| 3 | Scheduled-task safeguard | A7 |
| 4 | Protocol freeze (hash), then label-free forecast generation (two runs for determinism), then forecast freeze (hash) | A8 |
| 5 | Outcome collection for a blind quarter, only after its forecasts are frozen | A9, separately per quarter |
| 6 | Evaluation report: per-quarter results, §8 conclusions, validity status | — |
| 7 | Any served-model decision | A10, separately |

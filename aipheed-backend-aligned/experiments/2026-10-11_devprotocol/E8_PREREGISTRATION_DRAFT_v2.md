# E8 Pre-registration (DRAFT v2 for review): Core vs M6 vs Carry-forward

**Status: DRAFT v2. NOT approved, NOT frozen, NOT run.**

| Item | Value |
|---|---|
| Prepared | 2026-10-12 |
| Supersedes | `E8_PREREGISTRATION_DRAFT.md` (v1, preserved unchanged) |
| Scope | Isolated development backend only |

**Not done:** no forecast, label, outcome access, scheduled-task change, rescoring or served-model change.

**Changes from v1:**

1. Exact forecast and information cutoff (§3).
2. Exact protected-data boundary (§4).
3. **2025-Q2/Q3 reclassified** from "secondary, partially blind" to "exposed: descriptive only, excluded from all conclusions" (§5).
4. Overall stress forecasting and provincial ranking are separate questions, with separate interpretations (§7).
5. Conclusions are limited to **gross-failure detection** and **whether added value is demonstrated**. No statistical superiority (§8).

---

## 1. What is being forecast, and what is not being validated

**The outcome is the Equation 3 stress indicator:**

- stress(p, T) = SWS Balance-Luzon hunger_T + 2 × (provincial food CPI YoY(p, T) − five-province mean_T);
- the event is stress > τ = 14.345 (frozen as of 2026-07-01).

**It is a constructed proxy:**

- its regional part is one SWS value for all of Luzon outside Metro Manila;
- its provincial part is relative food-price inflation.

**This evaluation measures agreement with that proxy. It does not validate food insecurity:** no independent, province-level food-insecurity outcome exists.

- Every result must be worded as "forecasts the Equation 3 stress indicator" (overall) or "orders provinces by relative food-price pressure" (ranking).
- **Never** as "predicts food insecurity" or "identifies food-insecure provinces".

## 2. Arms (fixed; no tuning)

**Common LightGBM settings for A1–A4:**

- `num_leaves=4`, `min_child_samples=5`, 100 trees, `learning_rate=0.05`, seed 42;
- no class weighting;
- monotone +1 on `sws_hunger` and `last_published_stress`, 0 elsewhere;
- NaN kept;
- training-only filter: drop a feature that is more than 50% missing or constant in training.

**Each arm is fitted as a classifier (event) and as a regressor (continuous stress), with the same inputs.**

| Arm | Inputs | Role |
|---|---|---|
| **A1 Core** | `sws_hunger`, `sws_change`, `last_published_stress` | Primary |
| **A2 Core + provincial government** | A1 + `cpi_rel`, `cpi_rel_lag1`, `cpi_dev`, `food_cpi`, `food_cpi_yoy`, `food_cpi_yoy_lag1`, `food_cpi_yoy_accel`, rice price (+lag, accel), `poverty_incidence` | Primary (added-value test, §8.2) |
| **A3 M6 without news** | Training-only selection over core + subsets of {provincial government, national government} | Primary |
| A4 M6 as served | Selection including news | Descriptive only, unless the news rule (§6) is met |
| **B1 Carry-forward stress** | Last published stress | Primary baseline (overall and ranking) |
| B2 Carry-forward provincial gap | Latest published `cpi_rel` | Ranking baseline |
| B3 Equation 3 origin rule | SWS input + 2 × `cpi_rel` | Overall and ranking baseline |
| B4 Regional-only | SWS input (all provinces tied) | Overall baseline. No ranking ability by construction. |
| B5 Always-HIGH, always-LOW | — | References |

## 3. Forecast cutoff (exact)

**Forecast target quarters:**

| Quarter | Origin |
|---|---|
| 2026-Q3 | **2026-07-01 00:00 Asia/Manila** |
| 2026-Q4 | **2026-10-01 00:00 Asia/Manila** |

**Usable information:** a value is usable for target T only if its **publication date is strictly before the origin date** (local date as recorded). Anything published on the origin date or later is excluded.

| Source type | Publication date used |
|---|---|
| Verified date | The verified date |
| Provincial CPI | The WD1 proxy: national release date + 14 days (verified for 2024-Q4 only) |
| National/regional series | Documented schedules (WD3) |
| **Unknown date** | **Excluded** (Rule L4) |

**Quarterly granularity only.**

- Inputs are complete-quarter values as defined in the development frame: government series refer to quarter T−2; SWS uses the latest round published before the origin.
- **Monthly values for a quarter that is not complete and published before the origin are not used**, even if some of its months were published earlier.

**Training labels:**

- Only Equation 3 labels **published before the origin** (Rule L1): 2021-Q2 to 2025-Q4, 16 quarters. The latest, 2025-Q4, was published 2026-01-20.
- **No 2026 label is ever built for training.**

**Inputs expected at each origin (to be confirmed by data checks; nothing opened yet):**

| Input | 2026-Q3 forecast (origin 2026-07-01) | 2026-Q4 forecast (origin 2026-10-01) |
|---|---|---|
| Last published stress | 2025-Q4 label (published 2026-01-20) | 2025-Q4 label |
| SWS input | March 2026 round (published 2026-05-12). Exposed value; legitimate input. | June 2026 round **only if** its publication date is verified as before 2026-10-01 (date-only check, D3). Otherwise the March 2026 round (3 quarters old; not stale). **The September 2026 round is never an input** (§4). |
| Provincial CPI (T−2) | 2026-Q1 (January–March 2026; collected 2026-10-09; national releases 2026-02-05 / 03-05 / 04-07 + 14 days) | 2026-Q2 (April–June 2026; last release 2026-07-07 + 14 = 2026-07-21) |
| Other government series | As available before the origin; NaN otherwise | Same |
| News | Excluded (§6) | Excluded |

**Issuance:** both origins have passed, so forecasts are **retrospective simulations** (Rule L6). They are computed after the origin from pre-origin information only, record their issue timestamp, and are **frozen** (written and SHA-256 hashed) before the protected boundary is opened (§4).

**Data snapshot:** inputs are read from files whose hashes are recorded at the freeze.

- `data/processed/*`: unchanged since 2026-10-11, verified 2026-10-12.
- `data/supplementary/collection_2026-10-09/*`: manifest-hashed.
- Values are the latest stored vintage. Revised series (ONI, typhoons, rainfall: WD2) are flagged and are not primary-arm inputs.

## 4. Protected-data boundary (exact)

**Protected:** these must not be opened, parsed, printed, aggregated or used until the forecasts for that quarter are frozen **and** outcome collection is separately authorized.

| # | Protected item |
|---|---|
| P1 | **SWS hunger estimates from any survey round with fieldwork from 2026-07-01 to 2026-12-31** (the September and December 2026 rounds, Stratbase-SWS or any other). This covers values, release pages, PDFs, news coverage, and any update of the SWS table in either backend. **The September 2026 round is excluded as an input for 2026-Q4 whatever its publication date**, because it is a component of the protected 2026-Q3 outcome. |
| P2 | **Food CPI and food CPI YoY for reference months July–December 2026** (provincial, regional or national; any source: PSA OpenStat, RSSO IV-A, news). July–September values are excluded as inputs for the 2026-Q4 forecast whatever their publication date. |
| P3 | **Files that contain P1/P2 rows**, including the known ones: `backend/data/processed/psa_indicators.parquet` (rows through 2026-Q4) and `backend/data/thesis/panel.parquet` (rows through 2026-Q3, including the derived `label_cpi`). Also any file that later acquires such rows (a pipeline run, a scheduled task, a fetch). |
| P4 | **Anything derived from P1/P2:** stress, Equation 3 labels, provincial deviations d, `label_cpi`, or features for targets 2026-Q3/Q4 or later that embed July–December 2026 values |

**Permitted on protected files:** file-level metadata only (path, size, modification time, SHA-256 of the bytes) to detect change. **No parsing.**

**Disclosed exposure:**

- On 2026-10-11 one aggregate was printed from P3: the 2026-Q1 to Q3 `label_cpi` HIGH share, 0.93. It mixes exposed Q1/Q2 rows with protected Q3 rows and reveals no Equation 3 component.
- A quarter list was printed.
- No values were viewed or used.

**Not protected, but exposed** (allowed as inputs where timing permits; never as evaluation outcomes):

- SWS March 2026 (22.4) and June 2026 (17.3) values;
- January–June 2026 provincial CPI (collected 2026-10-09).

## 5. Evaluation split and exposure status

| Set | Quarters | Exposure | Use |
|---|---|---|---|
| Training | Labels 2021-Q2 to 2025-Q4, as published before each origin | — | Fitting only |
| Reused history | 2023-Q4, 2024-Q1–Q4, 2025-Q1, 2025-Q4 | Evaluated in E1–E7 | **Excluded from every conclusion**; history only |
| **Exposed: descriptive only** | **2025-Q2, 2025-Q3** | **Both label components seen.** SWS: April 23–28 (17.0), June 25–29 (15.3) and September 24–30 (23.8) 2025 were collected, printed and reported (2026-10-09). Provincial component: d for these quarters was **the E2 test target**, scored and reported with its top provinces (2026-10-11). Their CPI also entered models as inputs. Equation 3 labels require adviser decision D3 (respondent composition) and authorization to build them. | Optional descriptive check only. **Excluded from gross-failure and added-value conclusions.** |
| Exposed: descriptive only | 2026-Q1, 2026-Q2 | Outcomes in the production SWS table and the collected CPI | Optional descriptive check; excluded from conclusions |
| **Blind (the only basis for conclusions)** | **2026-Q3, 2026-Q4** | Protected (§4) | Gross-failure detection and the added-value question |

**Basis for conclusions:** 2 quarters, i.e. **2 independent regional observations** and **20 within-quarter province pairs** (2 × 10, themselves dependent).

## 6. News sufficiency rule (pre-defined)

**Definition.** A province-quarter is news-sufficient if it has at least 5 articles that are all of the following:

- rated relevant by XLM-RoBERTa;
- geocoded to that province;
- deduplicated by normalized title;
- with a parseable publication date in the quarter.

**News may enter the primary comparison only if:**

1. at least 80% of 2021–2025 province-quarters are news-sufficient; **and**
2. all five provinces are news-sufficient in the news input quarter (T−1) of each blind forecast.

**Status:** 0 of 100 province-quarters are news-sufficient (E7 corpus audit; 2021–2025). News is excluded from the primary comparison. The rule is re-checked from article counts only (D7).

## 7. Two separate questions, two separate interpretations

These questions are **never combined** into one accuracy figure or one verdict.

### 7.1 Q-overall: does the arm forecast the stress indicator's level?

**What drives it:** mostly the **shared regional component** (SWS_T accounts for about 65% of historical stress variance). A good overall result means the arm tracked the regional hunger level, plus some provincial adjustment. **It is not evidence about any individual province.**

**Unit:** the quarter.

**Metrics per blind quarter:**

- **Classifier arms:** mean Brier score over the five provinces; HIGH / LOW / INSUFFICIENT counts.
- **Regressor arms:** **regional-level error** = |mean over provinces of predicted stress − SWS_T|, and the quarter MAE.

### 7.2 Q-ranking: does the arm order provinces by relative food-price pressure?

**What drives it:** **only the provincial component** d(p, T): the gap between a province's food inflation and the five-province mean. A good ranking result means the arm ordered relative food-price pressure. **It is not a food-insecurity ranking**, because no province-level hunger outcome exists.

**Unit:** within-quarter province pairs.

**Metrics per blind quarter:**

- concordant pairs out of 10 between the arm's score and observed d (ties count ½);
- Kendall τ-b;
- whether the arm identified the top province.

**Arms without ranking ability (B4 regional-only, B5) are reported as such.**

### 7.3 Reporting rules for both questions

| Rule | Detail |
|---|---|
| Per-quarter values only | The two quarters are reported separately, with no pooled average presented as an estimate |
| No inferential statistics | No p-values, confidence intervals, bootstrap or row-level tests |
| Probabilities | Uncalibrated. The threshold is fixed at 0.50; nothing is tuned to balance HIGH and LOW. |

## 8. Permitted conclusions (only these)

### 8.1 Gross-failure detection (per arm, per question)

| Question | An arm is flagged "gross failure" if, in **both** blind quarters: |
|---|---|
| Overall (classifier) | Its quarter-mean Brier score is worse than B1 carry-forward by **more than 0.10** |
| Overall (regressor) | Its regional-level error is worse than B4 regional-only (the SWS input) by **more than 3.0 stress points** |
| Ranking | It has **3 or fewer** concordant pairs out of 10 (systematic inversion), **or** at least 3 fewer concordant pairs than B2 carry-forward gap |

- **Otherwise the result is "no gross failure detected".** That does **not** mean the arm performs well.
- **If A1 is flagged on Q-overall:** "the core LightGBM did not beat persistence". LightGBM remains the primary model, and B1 is shown beside it as the benchmark.

### 8.2 Is added value demonstrated?

**Two comparisons are tested:**

- provincial government indicators: A2 vs A1;
- the data-driven selection: A3 vs A1.

**Bar for "demonstrated":** better than A1 **and** better than the relevant carry-forward baseline (B1 for overall; the better of B1/B2 for ranking) **in at least 8 blind quarters, in every one of them**.

**E8 has 2 blind quarters, so it cannot meet the bar. Every added-value result in E8 will be "not demonstrated".** The evaluation reports whether the 2 quarters are *consistent* or *inconsistent* with added value. That is descriptive only.

### 8.3 Not permitted

- Statistical superiority of any arm.
- "Best model", or any ranking of arms by small differences.
- Pooled accuracy over province rows.
- Any claim about food insecurity.

### 8.4 Served-model consequence

| Item | Rule |
|---|---|
| Default after E8 | **A1 Core**, chosen for parsimony (not for E1–E7 results) |
| Override | E8 cannot override the default; the §8.2 bar is unreachable |
| Gross failure | A gross-failure flag on A1 or A3 is reported, and serving that arm requires a separate decision |
| Switching from M6 | Requires your explicit approval after E8; nothing switches automatically |

## 9. Integrity controls

| Control | Detail |
|---|---|
| Sequence | Data checks → protocol freeze (hash) → label-free forecast generation (two runs for determinism) → hashing of forecasts → **only then** separately authorized outcome collection |
| No evaluation labels | No evaluation-quarter label exists before the freeze. Training access is limited to labels published before the origin. |
| Protected-boundary audit | At the freeze, record metadata/hashes (no parsing) of the P3 files and of every input file |
| Hash guard | Covers data, models, earlier runs, served artifacts and the frozen protocol, with the run's **own** folder excluded (E7 fix) |
| Production | No production, frontend, scheduler, scheduled-task or deployment change |

## 10. Data checks (to run after approval; none touches protected data)

| # | Check | Notes |
|---|---|---|
| D1 | Input hashes: `data/processed/*` and the supplementary collection match their records | Verified 2026-10-12: 100/100 |
| D2 | P3 file metadata recorded without parsing | — |
| D3 | June 2026 SWS publication **date only** (no value) | Needs authorization |
| D4 | Prospective input frame for targets 2026-Q3/Q4, built from the collected 2026-H1 CPI | Code change in the isolated backend; needs authorization |
| D5 | Quarterly food CPI YoY construction, recomputed on 2021–2025 only | — |
| D6 | C6 confirmation of the 2025 SWS rounds. June and September 2025 enter as **training-row inputs** (for targets 2025-Q3 to 2026-Q1). November 2025 is the 2025-Q4 **training label** and the base of the `sws_change` input at both 2026 origins. They are not direct SWS inputs at the 2026 origins. | Needs authorization |
| D7 | News sufficiency, from article counts only | — |
| D8 | Freshness and publication-date gating at each origin | — |
| D10 | Determinism (identical forecasts on two runs) | — |
| D11 | Scheduled-task risk (see unresolved decision U8) | — |
| D12 | Production untouched | Verified 2026-10-12; re-verify at freeze |

D9 (2025 secondary labels) is moved to the descriptive-only set; it needs decision U5.

## 11. Limits stated in advance

- **Two blind quarters:** two regional observations, so no arm can be shown better or worse except by gross failure.
- **Ranking:** 20 dependent province pairs.
- **Proxy dates and revised vintages** (WD1, WD2).
- **Respondent populations** changed in 2025 (D3).
- **Exposure:**
  - 2025-Q2/Q3 and 2026-Q1/Q2 are exposed;
  - P3 files exist on disk;
  - the daily scheduled tasks are active.
- **Equation 3 stress is not an observed food-insecurity outcome.**

## 12. Unresolved decisions (approval needed before execution)

| # | Decision | Owner | Blocks |
|---|---|---|---|
| U1 | Approve or amend this protocol (arms §2, cutoff §3, protected boundary §4, split §5, permitted conclusions §8) | Researcher / adviser | Everything |
| U2 | Authorize D3: verify the June 2026 SWS publication **date only** | Researcher | Choice of the 2026-Q4 SWS input |
| U3 | Authorize D4: build the prospective input frame from the collected 2026-H1 CPI (isolated code change) | Researcher | Forecast generation |
| U4 | Authorize D6/C6: manual confirmation of the 2025 SWS rounds | Researcher | Training-input integrity (recommended before the freeze) |
| U5 | Whether to build the descriptive-only 2025-Q2/Q3 labels. Requires adviser decision D3 (adult-population rounds) and label authorization. They can never support conclusions. | Adviser / researcher | Optional descriptive check only |
| U6 | Thresholds of the gross-failure rules: Brier margin 0.10, regional-level margin 3.0 points, ranking ≤ 3 pairs or ≥ 3 fewer than B2. Confirm or amend **before** the freeze. | Researcher / adviser | Conclusions §8.1 |
| U7 | Accept that "added value" cannot be demonstrated in E8 (bar: ≥ 8 blind quarters), and that the post-E8 default is A1 Core on parsimony grounds | Adviser | Served-model decision |
| U8 | **Scheduled tasks** `aipheed` and `aipheed-auditing`: open-ended daily sessions that could view or fetch protected data (P1/P2) before the freeze. Pause them, restrict their prompts, or accept the risk in writing. **Not changed.** | Researcher | Integrity of the blind quarters |
| U9 | Treatment of the P3 production files that already hold protected rows: confirm the "metadata only, never parse" rule; decide whether a production clean-up is wanted after E8. Production is not changed here. | Researcher | Integrity of the blind quarters |
| U10 | Timing: authorize the freeze (forecasts hashed), then, separately, outcome collection for 2026-Q3/Q4 once those outcomes are published | Researcher | Evaluation itself |
| U11 | Earlier items, unchanged by E8: production `label_cpi` and its 0.712 cutoff; the dashboard reference (τ0 vs 14.345); calibration; the production frontend not consuming the new endpoint | Adviser / researcher | Not E8 |

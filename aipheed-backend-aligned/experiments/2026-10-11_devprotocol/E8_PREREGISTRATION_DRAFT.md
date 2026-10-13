# E8 Pre-registration (DRAFT for review): Core vs M6 vs Carry-forward

**Status: DRAFT. NOT approved, NOT frozen, NOT run.**

| Item | Value |
|---|---|
| Prepared | 2026-10-12 |
| Basis | `INDICATOR_EVIDENCE_REPORT.md` (E7) |
| Scope | Isolated development backend `aipheed-backend-aligned/` only |

**Nothing in this document has been executed.** No forecast for the new evaluation has been generated, no label built, no outcome collected or viewed. The served model is unchanged (M6).

**After approval, the steps are:**

1. Run the data checks (§8).
2. Freeze and hash this protocol.
3. Generate and freeze the forecasts.
4. Collect outcomes under a separate authorization.

---

## 1. What this evaluation can and cannot show

**What it measures:** how well each arm forecasts the **Equation 3 stress indicator**:

- stress(p, T) = SWS Balance-Luzon hunger_T + 2 × (provincial food CPI YoY(p, T) − five-province mean_T);
- the event is stress > τ.

**This is a constructed proxy, not an observed food-insecurity outcome.**

- No province-level food-insecurity outcome exists in the project.
- The SWS component is one regional value (all of Luzon outside Metro Manila), shared by the five provinces.

**Every result must be worded as "forecasts the Equation 3 stress indicator".** It must never be worded as "predicts food insecurity".

**What it cannot establish:**

- superiority of any arm (§6.3);
- calibrated probabilities;
- province-level food insecurity;
- causal influence of any indicator.

## 2. Arms (all fixed now; no tuning)

**Common LightGBM settings for A1–A4:**

- `num_leaves=4`, `min_child_samples=5`, 100 trees, `learning_rate=0.05`, seed 42;
- no class weighting;
- monotone +1 on `sws_hunger` and `last_published_stress`, 0 elsewhere;
- NaN kept;
- training-only filter: drop a feature that is more than 50% missing or constant in the fold's training rows.

**Each LightGBM arm is fitted twice:** as a classifier for the event, and as a regressor for continuous stress, with the same inputs.

| Arm | Inputs | Role |
|---|---|---|
| **A1 Core** | R: `sws_hunger`, `sws_change`, `last_published_stress` | Primary |
| **A2 Core + provincial government** | R + GP: `cpi_rel`, `cpi_rel_lag1`, `cpi_dev`, `food_cpi`, `food_cpi_yoy`, `food_cpi_yoy_lag1`, `food_cpi_yoy_accel`, rice price (+lag, accel), `poverty_incidence` | Primary. Tests §5. |
| **A3 M6 without news** | Training-only group selection over R + subsets of {GP, GN} (E7 procedure, with N removed) | Primary |
| A4 M6 as served | Training-only selection over R + subsets of {GP, GN, N} | **Secondary, descriptive only**, unless the news-sufficiency rule (§4) is met. In that case A4 replaces A3 as primary. |
| **B1 Carry-forward stress** | Last published stress, per province. Event: > τ. Ranking by last stress. | Primary baseline |
| B2 Carry-forward provincial deviation | Latest published `cpi_rel` | Ranking baseline only |
| B3 Equation 3 origin rule | SWS input + 2 × `cpi_rel` | Baseline |
| B4 Regional-only | SWS input. All provinces tied. | Overall baseline only; it has no ranking ability by construction |
| B5 Always-HIGH, always-LOW | — | References |

## 3. Proposed evaluation split

| Set | Quarters | Status | Use |
|---|---|---|---|
| Training | Labels 2021-Q2 to 2025-Q4 (16 labelled quarters), each used only if published before the forecast origin (Rule L) | — | Model fitting only |
| **Excluded from all decisions** | 2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4 | Used in 7 earlier analyses (E1–E7) | Reported as history only. **Never used to select an arm.** |
| Disclosed checks (not counted) | 2026-Q1, 2026-Q2 | Outcomes already seen (SWS March and June 2026 in the production table) | Optional descriptive check, labelled "outcome exposed" |
| **Secondary: never evaluated** (needs authorization, §8 D9) | 2025-Q2, 2025-Q3 | No Equation 3 label exists yet. Possible labels from the collected 2025 SWS rounds (adults 18+): Q2 = mean of the April 23–28 and June 25–29 rounds; Q3 = September 24–30. **Those SWS values were seen during collection.** | Partially blind supporting evidence. **M6 and E6 forecasts for these quarters are already frozen** in the served artifacts (hashes recorded 2026-10-12). A1–A3 would be generated and hashed before any label is built. |
| **Primary confirmatory** | **2026-Q3, 2026-Q4** | Protected. Outcomes not collected and not viewed. | The only blind evaluation available inside the approved 2021–2026 window |

**Size:** 2 primary quarters (10 province rows, **2 independent regional observations**), plus up to 2 secondary quarters.

## 4. News sufficiency rule (pre-defined)

**Definition.** A province-quarter is "news-sufficient" if it has at least 5 articles that are all of the following:

- rated relevant by XLM-RoBERTa (`is_relevant`);
- geocoded to that province;
- deduplicated by normalized title;
- with a parseable publication date inside the quarter.

**News may enter the primary comparison only if both hold:**

1. at least **80%** of training-window province-quarters (2021–2025) are news-sufficient; **and**
2. for each primary forecast quarter T, **all five provinces** are news-sufficient in quarter T−1 (the news input quarter).

**Status at drafting:** 0 of 100 training-window province-quarters are news-sufficient (E7: only 36 relevant, province-geocoded articles in 2021–2025). **News is therefore excluded from the primary comparison.** A3 is primary and A4 is descriptive.

The rule is re-checked (D7) before freezing. The check counts articles only; it does not touch outcomes.

## 5. Do provincial government indicators add value?

**Two separate questions, both answered by A2 vs A1 and A2 vs B1/B2:**

1. **Overall:** does adding GP to the shared regional and persistence inputs reduce the overall forecast loss (§6.1)?
2. **Ranking:** does A2 order provinces within a quarter better than A1, and better than the carry-forward ordering (B1 stress, B2 `cpi_rel`)?

**GP "adds value" only if** A2 beats both A1 and the better of B1/B2 on ranking concordance in **every** evaluated quarter, with no loss in overall performance. Otherwise it is reported as "not demonstrated".

**With 2–4 quarters, a positive finding is descriptive only** (§6.3).

## 6. Information, outcomes, metrics and dependence

### 6.0 Forecast dates and information cutoffs

| Item | Rule |
|---|---|
| Origin | 00:00 Asia/Manila on the first day of T. 2026-Q3: 2026-07-01. 2026-Q4: 2026-10-01. 2025-Q2: 2025-04-01. 2025-Q3: 2025-07-01. |
| Inputs | Only values published strictly before the origin (Rule L). Unknown publication dates are excluded. Provincial CPI uses the WD1 proxy (national release + 14 days). Revised climate vintages are flagged (WD2). |
| SWS input for 2026-Q3 | March 2026 round (published 2026-05-12) |
| SWS input for 2026-Q4 | The June 2026 round **only if** its publication date is verified (date only, D3) as before 2026-10-01. Otherwise the March 2026 round, which is 3 quarters old and so still within the staleness limit. |
| Training labels | Published before the origin. For the 2026 origins: 2021-Q2 to 2025-Q4. **2026-Q1/Q2 are never labelled.** |
| Reference τ | **14.345**, frozen as of 2026-07-01 (16 quarters). The secondary 2025 quarters use the τ computed point-in-time at their own origins under the same frozen-reference rule; both are reported. |
| Timing | Forecasts are produced **after** the origins (Rule L6), using only pre-origin information, and **frozen and hashed before any outcome component is collected or viewed** |
| INSUFFICIENT_DATA | A required input (`last_published_stress`, `sws_hunger`) is missing; or the SWS input is older than 3 quarters; or there are fewer than 8 training quarters. Those rows are excluded from metrics and counted separately. |

### 6.1 Outcome labels (built only after the freeze, under a separate authorization)

**Inputs to the label:**

- SWS Balance-Luzon hunger: the mean of the rounds **fielded** in the quarter (adults 18+);
- provincial food CPI YoY: same construction as `psa_indicators` (D5).

**Derived values:**

- stress and the event (stress > 14.345);
- the decomposition: regional component SWS_T, and provincial component d(p, T) = provincial YoY − five-province mean.

**Edge case:** a quarter with no SWS round fielded has no label and is reported as unevaluable.

### 6.2 Metrics: overall performance and province ranking are kept separate

**The unit of analysis for overall performance is the quarter, not the province row.**

**Overall forecast performance (per quarter, then summarized across quarters):**

- **Classifier arms:**
  - Brier score and log loss, averaged over the quarter's five provinces;
  - counts of HIGH / LOW / INSUFFICIENT and the confusion matrix;
  - balanced accuracy only when both classes are present in that quarter (otherwise undefined).
- **Regressor arms:**
  - **regional-level error** = |mean over provinces of predicted stress − SWS_T| (one value per quarter);
  - MAE of stress per quarter.

**Province ranking (within each quarter):**

- Kendall τ-b between each arm's score and the observed provincial component d(p, T);
- concordant pairs out of 10 (ties count ½);
- whether the arm identified the top province.
- Ranking uses predicted probability (classifiers), predicted stress (regressors) or the baseline's score.

**Shared regional signal:**

- The five rows in a quarter share SWS_T, so they are **not** five independent outcomes.
- No statistic pools province rows as independent. There are no row-level p-values, no row-level confidence intervals, and no McNemar test.
- Quarter-cluster bootstrap is **not** used: with 2–4 quarters it is not meaningful.
- Per-quarter values and their range are reported instead.

### 6.3 Decision and model-selection rules (pre-specified)

1. **No superiority claim** is possible with fewer than 8 evaluated quarters. This evaluation has at most 4, so every comparison is reported as **descriptive**.
2. **Default served model after evaluation: A1 Core.** This is a parsimony choice (fewest inputs; regional hunger and persistence define the target). **It is not based on E1–E7 results.**
3. **Override for a more complex arm (A2 or A3):** only if it is better than A1 on **both** overall loss (quarter-mean Brier) **and** ranking (concordant pairs) in **every** evaluated quarter, **and** at least 8 quarters were evaluated. That last condition cannot be met inside the approved window, so the default stands.
4. **Gross-failure flag:**
   - if A1 is worse than B1 (carry-forward) on quarter-mean Brier by more than 0.05 in every evaluated quarter, the report states "the core LightGBM did not beat persistence". **LightGBM remains the primary model**, and B1 is shown beside it as the benchmark.
   - the same flag applies to A2 and A3.
5. **Switching the served model** from M6 to the selected arm requires your explicit approval after the evaluation. The protocol does not switch it automatically.

### 6.4 Threshold and probabilities

- **Fixed rules:** HIGH if final probability ≥ 0.50; LOW if < 0.50; INSUFFICIENT_DATA as in §6.0.
- **No adjustments:** no threshold, score or calibration adjustment is fitted on any evaluation quarter.
- **Calibration:** probabilities are reported as **uncalibrated**. No reliability claim is made; at most 20 province rows are far too few.

## 7. Integrity and leakage controls

| Control | Rule |
|---|---|
| Label vault | Training access only to labels published before the origin; **no evaluation-quarter label exists until after the freeze** |
| Freeze before outcomes | Forecasts for all arms are generated label-free, written, SHA-256 hashed and recorded **before** any outcome is collected. Outcome collection happens in a later, separately authorized step. |
| Hash guard | Protected files (data, models, all earlier runs, served artifacts, this protocol once frozen) hashed before and after, with the run's **own** folder explicitly excluded (fix of the E7 defect) |
| No 2026 outcome access | No access before the freeze. The production `backend/` data already contains 2026-Q3/Q4 CPI rows (reported 2026-10-11); they must not be opened (D2). |
| Production isolation | No production, frontend, scheduler or deployment change |

## 8. Required data checks (none run yet; all avoid protected outcomes)

| # | Check | Status / action |
|---|---|---|
| D1 | `labels.parquet` and `psa_indicators.parquet` hashes match the 2026-10-11 records | Verified 2026-10-12 (100/100 inputs unchanged). Re-verify at freeze. |
| D2 | The 2026-Q3/Q4 CPI rows in production `backend/data/processed/psa_indicators.parquet` and `data/thesis/panel.parquet` have not been opened. Treat them as a contamination risk. | Policy: never read. Record their hashes **without opening values** at freeze. |
| D3 | **June 2026 SWS publication date (date only; no value)** | Needs authorization. Without it, the 2026-Q4 forecast uses the March 2026 round. |
| D4 | **Inputs for the 2026 origins.** The development frame currently ends at target 2026-Q2. 2026-Q3/Q4 need 2026-Q1/Q2 provincial CPI (from `data/supplementary/collection_2026-10-09/`, collected and hashed). Other 2026 inputs (rice, labour, fuel) may be missing and would stay NaN. | Needs a code change in the isolated backend (prospective frame) **after approval** |
| D5 | Quarterly provincial food CPI YoY construction (mean of monthly YoY vs YoY of quarterly mean) matches `psa_indicators`, so collected outcomes are comparable | Code reading plus a 2021–2025 recomputation (no 2026 data) |
| D6 | C6: manual confirmation of the June, September and November 2025 SWS values and dates (inputs to the 2026 forecasts; November is the 2025-Q4 label) | Needs authorization |
| D7 | News sufficiency (§4): count per province-quarter for 2021–2025, and for input quarters 2026-Q2/Q3 | Article counts only. Expected result: excluded. |
| D8 | Freshness. SWS input age ≤ 3 quarters at each origin. CPI input published before each origin (2026 national release dates in `cpi_2026_release_dates.csv` + 14 days). | Computed at forecast time |
| D9 | Secondary quarters 2025-Q2/Q3: authorization to build Equation 3 labels from the collected adult-population rounds (adviser decision D3 on respondent composition) | Needs authorization; secondary only |
| D10 | Determinism. Every arm reproduces identical forecasts on a second run before hashing. | Built into the runner |
| D11 | **Scheduled tasks.** The two daily Claude sessions (`aipheed`, `aipheed-auditing`) are open-ended and ran on 2026-10-11 and 2026-10-12. They could view or fetch 2026 outcomes before the freeze. | **Recommend pausing both before the freeze (your decision; not changed)** |
| D12 | Production untouched: `backend/` hashes and git status | Verified at drafting (§9); re-verify at freeze |

## 9. Limits stated in advance

- **At most 4 evaluated quarters** (2 blind + 2 partially blind), so at most **4 independent regional observations**.
- **No winner can be declared** from this evaluation. It can only show gross failure or descriptive consistency.
- **Ranking** rests on 10 within-quarter pairs per quarter, among five provinces whose pairs are themselves dependent.
- **Exposure:**
  - the secondary quarters' SWS values were seen during collection;
  - 2026-Q1/Q2 outcomes are exposed;
  - the production 2026 CPI rows exist on disk.
- **Equation 3 stress ≠ food insecurity.** Validation against an independent observed outcome is **not possible** with the available data.

## 10. Approvals requested

1. Approve (or amend) this protocol, the split (§3), the arms (§2) and the decision rules (§6.3).
2. Authorize D3 (June 2026 SWS publication date only) and D4 (prospective input frame using the collected 2026-H1 CPI).
3. Decide D9 (secondary 2025-Q2/Q3 labels) and D6 (C6 verification).
4. Decide D11 (pause the scheduled tasks before the freeze).
5. Later, and separately: authorize outcome collection for 2026-Q3/Q4 **after** the forecasts are frozen.

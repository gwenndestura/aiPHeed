# Final Methodology Audit Before Model Execution (2026-10-11)

**Companion draft:** `experiments/2026-10-11_devprotocol/PREREGISTRATION_DRAFT_v3.md` (not frozen, not hashed).

**Preserved, unchanged:**

- `PREREGISTRATION_DRAFT.md` (v1)
- `PREREGISTRATION_DRAFT_v2.md`
- `docs/PREREGISTRATION_CONFLICT_RESOLUTION_2026-10-11.md`

**What was not done:**

- No model was trained or scored.
- No accuracy was computed, and nothing was tuned.
- No label was rebuilt or created.
- No SWS value was retrieved, and nothing about September or December 2026 was accessed.
- Production, the served models, the scheduler, `SCHEDULER_ENABLED`, frozen forecasts and the thesis are untouched.
- Nothing was committed, deployed, frozen or hashed.

**Read-only computations performed:**

- eligible training quarters, with the longest consecutive run, per fold;
- Clopper–Pearson arithmetic (no data involved);
- re-reading of the Chapter III text, `label_generator.py`, and the `backend/` scheduler and config.

---

## 1. C1: Target threshold

### 1.1 The approved definition

| Source | Statement |
|---|---|
| Chapter III, "Forecast Target Label" | "The global median threshold across all 120 province-quarter pairs will guarantee a balanced class split." |
| Equation 3 legend | "global_median(stress): median stress score across all 120 province-quarter pairs; guarantees a 50/50 class balance." |
| Chapter III, Rule 3 | "All **features** will derive exclusively from data available before the forecast period." The rule names features. It does not mention the label threshold. |
| `app/ml/features/label_generator.py` l.222–226 | `global_threshold = median(stress_score)` over **all labelled rows present when the code runs**; `label_stress = stress > global_threshold` |
| Window implementation | 14.345 = the median of the 80 labelled 2021–2025 rows |

### 1.2 Option A: the approved global threshold (14.345)

**Where the leak is.** 14.345 is computed partly from the stress scores of the evaluated quarters (2023-Q4 to 2025-Q4) and of quarters after them. On reused quarters, every component that needs the threshold therefore uses future information:

- the training labels, which carry the boundary's absolute location;
- `scale_pos_weight`, through those labels;
- the Equation 3 rule baseline;
- the carry-forward baseline.

**How large it is**, from earlier training-only medians, with no test labels involved:

- The medians knowable at the origins range from 10.82 to 14.11.
- At 14.345, only 22–48% of the training rows would be HIGH.
- The approved threshold therefore encodes the 2024–2025 high-hunger level, which was not knowable at the 2023–2024 origins.

**Can the approved target be evaluated without leakage, without changing its meaning?**

- **On the reused 2021–2025 quarters: no.**
  - Any forecaster of the event "stress > 14.345" must be given the constant 14.345, at training or at decision time. That constant is a function of the outcomes being forecast.
  - This applies to threshold-free alternatives too. For example, a regressor on stress that is then binarized at 14.345 still needs the constant, and it would also change the fixed model.
  - Removing the leak therefore requires a threshold not computed from the evaluated quarters, which changes the operational meaning of "HIGH".
- **On the protected 2026-Q3/Q4 quarters: yes.**
  - By the 2026-Q3 origin (2026-07-01), all 80 labelled 2021–2025 rows have been published.
  - 14.345 is therefore fully determined before either origin.
  - With 2026 rows never labelled, the approved threshold is leakage-free, and its meaning, "above the 2021–2025 median", is unchanged.
  - One residual difference remains: Chapter III's "all 120 pairs" would include the 2026 pairs. Those cannot enter a threshold without using the evaluated outcomes, so this deviation must be stated in any case.

### 1.3 Option B: a fold-specific threshold (τ_T)

**Meaning change:**

- "HIGH" becomes "stress above the median of all stress levels published by the forecast date".
- This is a **relative-to-record-to-date** event, not a fixed level.
- The stress formula is identical, and only the boundary moves.

**Arguments for it** (separate from merely avoiding the leak):

1. **Procedural fidelity.**
   - `label_generator.py` computes the median of the labelled rows that exist when it runs.
   - Replayed at an origin, as it would run in real-time operation, it can only see published labels.
   - τ_T is therefore what the approved procedure produces at each origin.
   - 14.345 is what that procedure produces only when run in 2026 with the full record.
2. **The forecasting objective.**
   - Chapter III's system is an anticipatory tool for DA 4A.
   - An operational system can never know a future-informed boundary.
   - A walk-forward evaluation that grants one does not measure the system that would be deployed.
3. **The balance property is kept where it matters for learning.** The training HIGH share at τ_T is 0.49–0.50 in every fold. Chapter III's stated purpose of the median ("guarantees a balanced class split") is met inside each training set.
4. **Consistency with Rule 3's intent.** Rule 3 is worded for features, but its rationale is "no look-ahead", and that applies equally to a label boundary that shapes training.

**Costs:**

| Cost | Effect |
|---|---|
| Not the literal Chapter III definition | Chapter III names "all 120 pairs". Needs adviser approval and a stated deviation. |
| Drift (C11) | τ_T rises from 10.82 to 14.11. The same stress level can be HIGH in one fold and LOW in a later one, so per-quarter results mean slightly different events. |
| Comparability (C10) | Every earlier accuracy used 14.345. A-origin numbers cannot be compared with them or with Chapter IV figures. |
| Test balance | The 50/50 balance is not guaranteed on test quarters. This is why v3 adds balanced accuracy, the test HIGH share, and always-HIGH/always-LOW reference rows. |
| Small threshold samples | τ_T comes from 40–75 rows (8–15 quarters, with the SWS component shared within each quarter). |

### 1.4 Other options considered

| Option | Why rejected |
|---|---|
| Hybrid: train at τ_T, score at 14.345 (or the reverse) | Two decision boundaries in one evaluation. Errors would mix definitional mismatch with forecasting error. |
| A fixed threshold chosen a priori | No external standard exists for this composite score. Choosing a value now, after the 2021–2025 data have been seen, is not a priori. It also needs adviser approval. |
| Freeze τ at the first origin (10.84) | Stale for later folds. Arbitrary anchoring to the first eligible fold. |
| Treat 14.345 as an "ex-post evaluation definition" only, but train at τ_T | This is the hybrid under another name. Rejected for the same reason. |

### 1.5 Recommendation

| Evaluation | Primary | Required alongside | Adviser approval needed? |
|---|---|---|---|
| **Exploratory development experiment (reused 2023-Q4 to 2025-Q4)** | **A-origin (Option B)**, applied consistently to training labels, test labels, baselines and class weights | A-global (Option A), labelled "uses the full-period threshold: not leakage-free" | **Yes.** It changes the operational meaning of the target in the reported analysis. |
| **Protected 2026-Q3/Q4 evaluation (future, separately authorized)** | **The approved threshold, 14.345, unchanged in meaning.** It is leakage-free there, and A-origin gives the same value. | none | Only for the stated deviation "median of the 80 labelled 2021–2025 pairs, not all 120 pairs" |

**Why the recommendation is split this way:**

- It was chosen on validity, Chapter III's procedure and purpose, and the forecasting objective. It was not chosen on leak avoidance alone.
- **The approved target definition is not abandoned.** It stays the target of the only evaluation that could support a final claim.
- The re-operationalization is confined to the exploratory analysis, where the approved threshold cannot be leakage-free.

**If the adviser declines:**

- A-global becomes the exploratory primary, with the leak disclosed beside every number.
- A-origin becomes the leakage-free sensitivity analysis.
- v3 §1.2 already specifies this fallback.

**The designation must be recorded before freezing.**

## 2. C3: 2023-Q3 and the minimum training window

### 2.1 What Chapter III states

| Location | Text |
|---|---|
| Algorithm 3 text | "a minimum training window of 8 quarters" |
| Architecture list | "minimum 8 training quarters, advancing one quarter per fold" |
| Input list | "minimum training window of 8 consecutive quarters" |

Algorithm 4 adds no separate minimum.

### 2.2 Eligible training quarters (development protocol, Rule L)

These counts were recomputed today from `eligible_training_quarters`.

| Target | Eligible | Longest consecutive run | Eligible set |
|---|---:|---:|---|
| 2023-Q3 | **7** | 4 | 2021-Q2, Q3, Q4; 2022-Q2, Q3, Q4; 2023-Q1 |
| 2023-Q4 | 8 | 5 | 2023-Q3's set plus 2023-Q2 |
| 2024-Q1 | 9 | 6 | |
| 2024-Q2 | 10 | 7 | |
| 2024-Q3 | 11 | 8 | |
| 2024-Q4 | 12 | 9 | |
| 2025-Q1 | 13 | 10 | 2021-Q2 to 2024-Q3, excluding 2022-Q1 |
| 2025-Q4 | 15 | 12 | 2021-Q2 to 2025-Q1, excluding 2022-Q1 |

**Under the strict protocol, every exploratory fold has 0 eligible quarters,** so the strict protocol cannot be run on these folds at all.

### 2.3 Recommendation

**Exclude 2023-Q3** from the primary analysis. It has 7 eligible quarters, so it fails the minimum under any reading. It is kept as sensitivity S5.

**Primary rule: "at least 8 eligible labelled quarters".**

- Under that reading, there are 7 test quarters and 35 rows.
- No fold in the window is ever consecutive across 2022-Q1, which has no label. The gap is a data gap, not a design choice.
- Under the literal "8 consecutive" reading, the first qualifying fold is 2024-Q3, giving 4 quarters and 20 rows. This is pre-registered as S6.
- **Adviser note required** on which reading governs.

### 2.4 Limits of 7 quarters × 5 provinces

1. **The rows are not independent.**
   - The SWS term is identical across the five provinces in a quarter.
   - The provinces differ only through the CPI-deviation term and province-specific inputs.
   - The effective sample size is close to 7.
2. **The intervals are coarse or optimistic.**
   - A quarter-cluster bootstrap over 7 clusters gives a coarse distribution.
   - Clopper–Pearson on 35 rows is optimistic.
   - Even so, the 95% lower bound exceeds 0.75 only with **at least 32/35 correct**. For example, 30/35 gives a lower bound of 0.70 and 28/35 gives 0.63.
3. **Comparisons with baselines have very low power.** Differences of a few rows between the models and the baselines are not statistically distinguishable.
4. **All 7 quarters are reused.** The results are exploratory development estimates, **never an independent final evaluation**.

## 3. C4–C11: Classification

| # | Issue | Before the exploratory run | Before a final claim | Treatment |
|---|---|---|---|---|
| C1 | Threshold design | **Must resolve:** the designation, primary or secondary | Approved 14.345 on 2026-Q3/Q4 | §1 |
| C3 | 2023-Q3 / minimum window | **Must resolve:** confirm the exclusion and the reading | — | §2 |
| C4 | SWS respondent population changes: household heads to December 2024; registered voters for the 2025-Q1 label (Stratbase, March 2025); adults 18+ from April 2025 (the 2025-Q4 label is November 2025, adults 18+) | Proceed with disclosure; per-quarter results make 2025-Q1/Q4 visible | **Must resolve (adviser D3):** whether labels from three populations form one target series | No alternative label is built |
| C5 | WD1 provincial-CPI proxy; WD2 revised climate inputs | Proceed: development protocol only, with S1/S2 | **Must resolve:** the 19 RSSO IV-A dates and point-in-time vintages, or the strict mask only. The strict protocol has 0–1 training quarters, so no strict claim is possible now. | Disclosed |
| C6 | The June, September and November 2025 SWS rounds are [V-single] | Proceed with the inputs flagged and S4 | **Must resolve:** manual confirmation (§4). November 2025 is also the **2025-Q4 label value** (16.7). | A mismatch voids the run (v3 §13.1) |
| C7 | The March 2026 SWS value is an exposed outcome | Not used | **Must disclose** in the protected evaluation, where it is a valid input (published 2026-05-12) | — |
| C8 | June 2026 SWS publication date unknown | Not relevant | **Must resolve** (date only) before the 2026-Q4 forecast is frozen; otherwise it is excluded under L4 | — |
| C9 | The `backend/` scheduler can retrain and promote the thesis-documented model on 2026-10-15 | Not blocking: nothing in `aipheed-backend-aligned/` is touched, and MODEL-A is refitted per fold | **Must resolve, time-critical:** before 2026-10-15 02:00 Asia/Manila | §5 |
| C10 | A-origin results are not comparable with earlier 14.345 accuracies | **Must resolve:** reporting language fixed in v3 §12 (done in the draft) | Not applicable: the final claim uses 14.345 | — |
| C11 | τ_T drifts from 10.8 to 14.1 | **Must resolve:** pre-specified reporting of τ for every fold (done in the draft) | Not applicable (fixed 14.345) | — |

## 4. C6: Exact manual verification steps (not performed)

**Perform these only when the researcher authorizes them.**

**Navigation constraint:**

- Navigate **only** to the four direct release URLs.
- Do not open the SWS home page, survey listings or search pages. They may display September or December 2026 headlines.

**The four release URLs:**

1. `sws.org.ph/social-weather-report-hunger-at-20-0-by-end-of-april-2025/` (already re-verified; control)
2. `…/hunger-falls-from-20-0-in-april-2025-to-16-1-in-june-2025/`
3. `…/hunger-rises-from-16-1-in-june-2025-to-22-0-in-september-2025/`
4. `…/hunger-eases-slightly-from-22-0-in-september-2025-to-20-1-in-november-2025/`

**Steps for each of releases 2–4:**

1. **Save the source.** Save the page (HTML or the linked media-release PDF). Record:
   - the URL;
   - the retrieval date and time;
   - the HTTP status;
   - the SHA-256 of the saved file.

   Save into a new folder, `data/supplementary/verification_<date>/`.
2. **Read the values.** Find the Balance-Luzon row, and record Moderate, Severe and Total. Check them against the expected values:

   | Release | Expected |
   |---|---|
   | June 2025 | 13.0 + 2.3 = 15.3 |
   | September 2025 | 17.2 + 6.6 = 23.8 |
   | November 2025 | Total 16.7, with components as stored in `sws_balance_luzon_2025_raw.csv` |

3. **Confirm the publication date** shown on the release (2025-08-15, 2025-11-05 and 2026-01-14). Cross-check each with an independent dated source:
   - the earliest Wayback capture, which must be on or after the date and close to it; or
   - same-day news coverage.

   Record which source was used.
4. **Record the context.** Note the survey field dates and the respondent population (expected: adults 18+).
5. **Get a second reading.** A second person, or the same person on a different day without the stored values visible, reads the same numbers. Record both readings.
6. **Write the comparison** to a new evidence CSV:

   | release | field | stored | read1 | read2 | match |
   |---|---|---|---|---|---|

   Never edit the original collection files.

**Outcomes:**

- **All match:** the date type changes from `verified-single` to `verified` in a **new** version of the registry.
- **Any mismatch:** stop. Record it. The experiment is re-specified under a new pre-registration.

## 5. C9: Scheduler risk and exact protective action (not applied)

### 5.1 Facts verified today, by reading code only

- `backend/app/main.py` starts `scheduler.start()` in the FastAPI lifespan.
- `scheduler.start()` returns early only if `settings.SCHEDULER_ENABLED` is false.
- `backend/app/config.py`:
  - `SCHEDULER_ENABLED: bool = True`;
  - cron `"0 2 15 1,4,7,10 *"`, Asia/Manila;
  - pydantic-settings with `env_file=".env"`, resolved **relative to the server's working directory**.
- `backend/.env` and `.env.example` contain **no** `SCHEDULER_ENABLED` entry, so the default `True` applies.
- The job uses `misfire_grace_time = 6 h`. A server that starts between 02:00 and 08:00 on 2026-10-15 still fires the job.
- The scheduled job runs `python -m app.tasks.quarterly_pipeline --trigger scheduled --run-id …` **without `--no-promote`**.
  - `--no-promote` therefore protects only manual CLI runs, **not the scheduled run**.
  - `POST /api/v1/admin/pipeline/run` uses the same path, so it also promotes.
- If the candidate meets the Algorithm 4 targets, the run replaces `backend/models/thesis_food_insecurity_model.joblib` (archiving the previous one). It also upserts PSA, rice and news data.

### 5.2 Exact action (researcher's decision; not applied)

**Option 1.** Add this line to `backend/.env`, and start the server from `backend/`:

```
SCHEDULER_ENABLED=false
```

**Option 2.** Set the variable in the launching shell. Environment variables take precedence over `.env`:

```bash
SCHEDULER_ENABLED=false uvicorn app.main:app
```

Run this from `backend/`.

**Option 3.** Do not run the `backend/` server between 2026-10-15 02:00 and 08:00 Asia/Manila.

**Verification:**

- The startup log shows `scheduler: disabled (SCHEDULER_ENABLED=false)`.
- `GET /api/v1/admin/pipeline` reports `"enabled": false`.

## 6. Blockers to a defensible accuracy claim

1. **No unused labelled quarter exists in 2021–2025.** The only possible final evaluation is the protected 2026-Q3/Q4 set, at most 10 rows. Even 10/10 gives a 95% lower bound of 0.69. **It cannot establish 75%** under any rule; it can only give a point estimate with an interval.
2. **The C1 leak** affects every earlier accuracy on 2021–2025 quarters, including the 72.5% figures. The exploratory A-origin analysis has not been run.
3. **C4/D3:** labels mix three respondent populations.
4. **C5:** the strict protocol has 0–1 eligible training quarters; real-time validity rests on the WD1 proxy and WD2 revised inputs.
5. **C6:** three [V-single] SWS values, one of which is a label.
6. **C8:** the June 2026 publication date is unknown.
7. **C9:** the served model may change on 2026-10-15.
8. **Exploratory evidence is limited:** 7 reused quarters, an effective sample size near 7, and at least 32/35 needed for even an optimistic interval to clear 0.75.

## 7. Unresolved decisions

| # | Decision | Who |
|---|---|---|
| 1 | C1 designation: A-origin primary for the exploratory run (recommended) and 14.345 for the protected run (recommended) | Adviser |
| 2 | C3: confirm excluding 2023-Q3; "8 eligible" vs "8 consecutive" | Researcher, with an adviser note |
| 3 | C4/D3: respondent-population composition | Adviser |
| 4 | C6: authorize the manual verification (§4) | Researcher |
| 5 | C9: `SCHEDULER_ENABLED` before 2026-10-15 02:00 | Researcher |
| 6 | Freeze and hash v3, then authorize the run | Researcher |
| 7 | Adviser confirmation of WD1, WD2 and WD5 (D1a, D2, D4) | Adviser |

## 8. Thesis statements affected

See v3 §14. If A-origin is approved for the exploratory analysis, the following would need revision or a stated deviation:

- Chapter III's "Forecast Target Label" paragraph;
- the Equation 3 legend ("all 120 province-quarter pairs; guarantees a 50/50 class balance");
- the summary sentence ("thresholded at the global median to yield a balanced binary HIGH/LOW target");
- the Algorithm 3/4 input wording ("120 rows … 24 quarters"; "8 consecutive quarters");
- §3.4.4's targets, as applied to the exploratory analysis;
- every Chapter IV statement reporting results at 14.345.

**Even if A-origin is not adopted,** the "all 120 pairs" wording already needs a stated deviation, because only 80 pairs are labelled and the 2026 pairs cannot enter a leakage-free threshold. **Nothing in the thesis has been edited.**

## 9. Files and tests

**Created:**

- `experiments/2026-10-11_devprotocol/PREREGISTRATION_DRAFT_v3.md`
- `docs/FINAL_METHODOLOGY_AUDIT_2026-10-11.md`

**Modified:** none.

**Tests:** see the final summary of this task.

# Pre-Run Audit and Scheduler Review (2026-10-11)

**Scope:** an inspection only.

**What was not done:**

- No model was trained, scored or tuned, and no accuracy was computed.
- No label was rebuilt or created.
- No SWS value was collected or browsed. Nothing about September or December 2026 was accessed, searched for or inferred.
- No `.env` file, environment variable, production code, scheduled job, served model or deployment setting was changed.
- Nothing was committed, deployed, frozen or hashed as a pre-registration.

**Preserved, unchanged:** all earlier reports and drafts, including v1–v3 and `FINAL_METHODOLOGY_AUDIT_2026-10-11.md`. Corrections to them are recorded in §5, not edited in.

**Read-only computations:**

- training eligibility (development and strict) per fold;
- Clopper–Pearson and effective-sample-size arithmetic (no outcome data);
- the scheduler's next fire time, from the configured crontab;
- SHA-256 baselines of the files the pipeline can write.

---

## 1. Phase 1: Scheduler protection assessment

### 1.1 Findings

Production backend: `C:\Users\admin\aipheed\backend\`.

| # | Question | Finding | Evidence |
|---|---|---|---|
| 1 | When can the job run on 2026-10-15? | **02:00 Asia/Manila (= 2026-10-14 18:00 UTC)**, and only if a `backend/` API process is running at that moment. See the notes below the table. | `config.py`: `PIPELINE_CRON="0 2 15 1,4,7,10 *"`, `PIPELINE_TIMEZONE="Asia/Manila"`. APScheduler 3.11.2 computes the next fire as `2026-10-15 02:00+08:00`. `scheduler.py`: `misfire_grace_time=6*3600`, `coalesce=True`, in-memory job store. |
| 2 | Does `SCHEDULER_ENABLED` default to `True`? | **Yes.** It is not set anywhere. | `config.py:53` `SCHEDULER_ENABLED: bool = True`. `backend/.env` holds 11 keys, none of them `SCHEDULER_*` or `PIPELINE_*` (key names only were read). Unset in the process, user and machine environment. No root `.env` exists. |
| 3 | Can it promote a candidate and replace the served model? | **Yes, if the candidate's holdout F1 ≥ 0.75 and AUC ≥ 0.80.** See "What a run does" below. | `quarterly_pipeline.py` `stage_retrain`, `promote`. `train_thesis_blend.py:154`. `scheduler.py` `run_now`, `publish`. |
| 4 | Does any startup script, deployment config or environment variable override it? | **No override found.** See "Override search" below. | §1.1 searches |
| 5 | Is `SCHEDULER_ENABLED=false` sufficient? | **It stops the cron job, but it is not sufficient on its own.** See §1.2. | |

**Notes on question 1 (when the job can run):**

- A process started **after** 02:00 does not catch up. The job's next run is then computed from the start time, so it becomes 2027-01-15.
- The 6-hour grace applies only to a process that was **already running** but could not fire on time, for example a machine asleep at 02:00 that wakes before 08:00.

**What a run does (question 3):**

- The scheduled command is `python -m app.tasks.quarterly_pipeline --trigger scheduled --run-id …`. It passes **no `--no-promote`**.
- `stage_retrain` trains a candidate into `models/candidates/`.
- `promote()` copies the served `models/thesis_food_insecurity_model.joblib` to `models/archive/`, then atomically replaces it.
- `publish()` (scheduler.py) then:
  - clears the serving caches, so the new model is used on the next request;
  - stages the latest quarter's province forecasts for DA review.

**Override search (question 4):**

- No Procfile, Dockerfile, docker-compose, render, fly, railway, service or batch file exists for the API.
- `.claude/launch.json` starts only the **aligned** API (`aipheed-backend-aligned`), not `backend/`.
- The README instructs `uvicorn app.main:app --reload`, run from `backend/`.
- No Windows Scheduled Task refers to aipheed, uvicorn or python.
- No uvicorn process is running now.

**What a run changes even when nothing is promoted:**

| Stage | Effect |
|---|---|
| 1. government | Upserts `data/processed/psa_indicators.parquet` and `psa_rice_prices.parquet` with OpenStat data **through the run date**. On 2026-10-15 this would bring **July–September 2026 provincial food CPI** (one component of the protected 2026-Q3 outcome) into the project's data. |
| 2. news | Appends to `corpus_geocoded.parquet` and the review list |
| 3. nlp_features | Rebuilds the FSSI |
| 4. panel | Rebuilds `data/thesis/panel.parquet` |
| 5. retrain | Trains a candidate |
| publish | Stages forecasts and reloads caches in the running API |

### 1.2 Disabling the scheduler vs disabling promotion

| | Disable the **scheduler** (`SCHEDULER_ENABLED=false`) | Disable **promotion** only |
|---|---|---|
| Stops the 2026-10-15 cron run | Yes, if the setting is actually loaded (see below) | No: the run still happens |
| Protects the served model | Yes, from the cron run | Yes |
| Prevents data upserts, panel rebuild and staged forecasts | Yes, from the cron run | **No.** Stages 1–4 and publish still run, including the 2026-Q3 CPI pull. |
| Stops a manual admin run (`POST /api/v1/admin/pipeline/run`) | **No.** `start_in_background` does not check `SCHEDULER_ENABLED`, and that path also promotes. | — |
| Stops a manual CLI run | No | Only the CLI's own `--no-promote` |
| Available without a code change? | **Yes** (configuration) | **No.** There is no setting. Only the CLI flag exists; the scheduled command hard-codes promotion. Making it configurable would need a production code change. |

**The setting has a loading pitfall.**

- `Settings` reads `env_file=".env"` relative to the **process's working directory**.
- If the API is started from any directory other than `backend/` (for example with `--app-dir backend` from the repo root), `backend/.env` is **not read**. The default `True` then applies silently.
- An environment variable set in the launching shell works regardless of the working directory.

**`.env` file facts:**

- `backend/.env` is git-ignored (`backend/.gitignore:10`), so the change would be local to this machine.
- The file currently ends with a newline, so appending a line is safe.

### 1.3 Recommended minimal protective action (NOT applied; awaiting your authorization)

**Step A.** Append one line to `C:\Users\admin\aipheed\backend\.env`:

```
SCHEDULER_ENABLED=false
```

**Step B.** Always start the `backend/` API from inside `backend/`, as the README instructs. For extra safety, also set the variable in the launching shell, which works from any directory. PowerShell:

```powershell
$env:SCHEDULER_ENABLED = 'false'
```

**Operating rule:** do not call `POST /api/v1/admin/pipeline/run`, and do not run `python -m app.tasks.quarterly_pipeline`, until the evaluation decisions are settled. If a run is ever needed, use `--no-promote --skip government` (the CLI only).

**Verification after applying:**

1. **Offline, from `backend/`:**

   ```bash
   venv/Scripts/python.exe -c "from app.config import settings; print(settings.SCHEDULER_ENABLED)"
   ```

   It must print `False`.
2. **At server start:** the log line `scheduler: disabled (SCHEDULER_ENABLED=false)`.
3. **While the server runs:** `GET /api/v1/admin/pipeline` (admin token) returns `"enabled": false, "nextRun": null`.
4. **After 2026-10-15:** the hashes match the baseline below. `models/archive/`, `models/candidates/` and `data/pipeline_runs/` still do not exist.

**Baseline recorded today** (SHA-256 and modified time):

| File | SHA-256 | Modified |
|---|---|---|
| `models/thesis_food_insecurity_model.joblib` | `cbab63f867e8f51fe0b93c99d8bdba3ace52a83d69dd77884763a69b9bc79dda` | 2026-10-06 20:16 |
| `data/thesis/panel.parquet` | `49af3ee17abe3facac558e4fa8f9dbbe7f51effc2be5639daa92655c83bf9742` | 2026-10-10 21:18 |
| `data/processed/psa_indicators.parquet` | `305ac1b34a0d1f2440b48d261d85469c4bce3f7c6f9d65b2cadf00cb5f2f7b9f` | 2026-10-06 20:16 |
| `data/processed/psa_rice_prices.parquet` | `c1e3cecd253caae2c716486513746c77974e881aae899a50bd37118f9fed93ed` | 2026-09-09 11:14 |
| `data/processed/corpus_geocoded.parquet` | `ebce1199014dd8ebcbd27675acbe4cfc088d404985fed9d1d00343076164261e` | 2026-09-03 00:56 |
| `data/processed/calabarzon_food_insecurity_dataset.parquet` | `a93055d6054272b3d3828fd94ce9be0c77994a15f2379e8f5d2179968e4e496f` | 2026-09-01 13:55 |

`models/candidates/`, `models/archive/` and `data/pipeline_runs/` do not exist, so **no pipeline run has ever completed on this machine.**

### 1.4 The aligned backend's own scheduler

This was not covered by the earlier reports.

- `aipheed-backend-aligned/app/tasks/scheduler.py` also starts from its FastAPI lifespan.
- It fires at 03:00 Asia/Manila on the 15th of January, April, July and October.
- If enabled, it would retrain and overwrite `models/lgbm_best.pkl`.
- **It is off by default.** It runs only if `AIPHEED_ENABLE_SCHEDULER=1`, and that variable is unset in the process, user and machine environment.
- **No action is needed. Do not set that variable.**
- `launch.json`'s "aipheed-api-aligned" configuration does not set it.

## 2. Phase 2: Existing 2025 SWS evidence

Sources inspected (local files only):

- `data/supplementary/collection_2026-10-09/`: the raw CSV, the verification CSV, `COLLECTION_MANIFEST.json` and the README;
- `evidence/2026-10-11_collection_audit/`: `sws_2025_round_table.csv` and `hash_verification.csv`;
- `app/ml/corpus/sws_hunger_fetcher.py`;
- `docs/PUBLICATION_DATES_AND_RULE_L_2026-10-09.md`, `DATA_COLLECTION_REPORT_2026-10-09.md`, `COLLECTION_AUDIT_AND_RULE_L_ELIGIBILITY_2026-10-11.md`.

All 6 manifest hashes match (`hash_verification.csv`).

### 2.1 Per-round results

| Item | April 23–28, 2025 | June 25–29, 2025 | September 24–30, 2025 | November 24–30, 2025 |
|---|---|---|---|---|
| Balance-Luzon value (moderate + severe) | 17.0 (13.9 + 3.1) | 15.3 (13.0 + 2.3) | 23.8 (17.2 + 6.6) | 16.7 (12.7 + 4.0) |
| Arithmetic | Exact | Exact | Exact | Exact |
| Role | Supplementary input only | Supplementary input only | Supplementary input only | **Production table + 2025-Q4 label (definition A)** |
| Source URL (recorded) | sws.org.ph `…hunger-at-20-0-by-end-of-april-2025/` | `…hunger-falls-from-20-0-in-april-2025-to-16-1-in-june-2025/` | `…hunger-rises-from-16-1-in-june-2025-to-22-0-in-september-2025/` | Verification file: `…hunger-eases-slightly-from-22-0-in-september-2025-to-20-1-in-november-2025/`. **Production table: a different, later release** (§2.2 item 1) |
| Archived or saved source | Wayback capture 2025-12-26 of `ART-20250627174857` (independently read on 2026-10-11) | **None.** Raw HTML not saved; Wayback unavailable on 2026-10-09 | **None** (same) | **None** saved |
| Publication date | 2025-06-27 | 2025-08-15 | 2025-11-05 | 2026-01-14 |
| How the date was verified | Posted date on the live page **and** the archived dateline "Jun 27, 2025 05:48:57 PM" | Posted date, from one restricted read of the page | Posted date, from one restricted read | SWS listing "posted Jan 14, 2026" [L], the release page's posted date, **and** dated news coverage (GMA, Inquirer Plus; URLs in `PUBLICATION_DATES…md` l.164) |
| Respondents | Adults 18+ [V]. The archived text states the change: household heads until December 2024, registered voters January to April 11–15, 2025, adults from April 23–28, 2025. | "Adults 18+" (single read) | "Adults 18+" (single read) | "Adults 18+ (1,200 adults)" |
| Sample and sampling error | 1,500 nationwide; 600 in Balance Luzon; ±4% | 1,200 nationwide; ±6% (Balance-Luzon n not recorded) | 1,500 nationwide; ±4% (Balance-Luzon n not recorded) | 1,200 adults; Balance-Luzon error **not recorded** |
| **Independently confirmed?** | **Value and date: yes.** Two separate reads of two copies (live and archived). | **No.** One read. The value is restated in the September release, but that release was read in the same session, through the same channel, by the same extraction step. **The date has no second source.** | **No.** Same situation as June; the value is restated in the November release. **The date has no second source.** | **Date: yes** (SWS listing + news + page). **Value: effectively yes.** It was read from two different SWS releases on different days: the later release when the table was rebuilt (2026-09-23), and the November release itself on 2026-10-09. **No copy is saved, so there is no byte-level audit trail.** |

### 2.2 Inconsistencies found

1. **November 2025: source attribution mismatch** (documentation only; the value agrees).
   - The production table (`sws_hunger_fetcher.py` l.216–218) cites the **later** SWS release, whose subject is the following (2026) round, as its source for 16.7.
   - The verification file cites the November release itself.
   - The later release cannot evidence the 2026-01-14 publication date. This is why the date was first recorded as a 2026-05-12 upper bound.
   - **Action:** in any later corrected table, cite the November release for value and date. The production file was not edited.
2. **Status labels disagree across documents.**

   | Round | Label | Where |
   |---|---|---|
   | November 2025 | "VERIFIED on release page" | `sws_existing_value_verification.csv` |
   | November 2025 | "[V-single] + news" | `sws_2025_round_table.csv` |
   | November 2025 | "[L]" plus news | `PUBLICATION_DATES…md` |
   | June and September 2025 | "[L]" | `READINESS_REPORT_2026-10-09.md` l.225 |
   | June and September 2025 | "[V-single]" | Later documents |

   Recommended consolidated status:
   - **April: V.**
   - **November: date V (multi-source); value V (two releases, no saved copy).**
   - **June and September: V-single (value and date).**
3. **Possible undisclosed prior-round figures.**
   - `COLLECTION_AUDIT…2026-10-11.md` l.52 records the April release's "moderate 16.5→13.9, severe 4.0→3.1".
   - The prior-round severe figure, 4.0, does **not** match the stored March 15–20, 2025 round (moderate 16.5, severe 7.4).
   - If those prior-round figures belong to the **April 11–15, 2025** registered-voter round, then that round's components *are* recorded in a project document. That would contradict the statement "value … NOT recorded".
   - This cannot be resolved from local evidence. **It is flagged, not interpreted.** The figures are not used anywhere.
4. **SWS round naming vs calendar quarter.**
   - SWS calls the April 23–28 round "First Quarter 2025", but the project files it under 2025-Q2 (the fieldwork quarter, per the fetcher's convention).
   - This is consistent, but it must be stated wherever "Q1 2025" appears, because definition A's 2025-Q1 label is the separate **March 15–20 Stratbase** round.
5. **Precision differs between rounds.**
   - June 2025 has 1,200 respondents nationwide and ±6% error, against ±4% for April and September.
   - The November Balance-Luzon error is not recorded.
   - A ±6% sampling error is larger than many quarter-to-quarter changes in the series. This is relevant to C4 and to the interpretation of any single quarter's label.
6. **Respondent population** for June and September rests on the single read. Only April has the explicit SWS statement on record.

### 2.3 What remains unverified

| Item | Status |
|---|---|
| June 2025 value and posted date (2025-08-15) | V-single |
| September 2025 value and posted date (2025-11-05) | V-single |
| June and September respondent population and Balance-Luzon sampling errors | V-single |
| Saved source copies with hashes for June, September and November | None exist |
| Identity of the April release's prior-round figures (§2.2 item 3) | Unresolved |
| November Balance-Luzon sampling error | Not recorded |

The manual steps in `FINAL_METHODOLOGY_AUDIT_2026-10-11.md` §4 cover all of these. They were **not performed**.

## 3. Phase 3: Evaluation readiness re-check

### 3.1 Eligibility and the test-quarter list (recomputed today)

| Target | Development | Strict |
|---|---:|---:|
| 2023-Q3 | 7 | 0 |
| 2023-Q4 | 8 | 0 |
| 2024-Q1 | 9 | 0 |
| 2024-Q2 | 10 | 0 |
| 2024-Q3 | 11 | 0 |
| 2024-Q4 | 12 | 0 |
| 2025-Q1 | 13 | 0 |
| 2025-Q4 | 15 | **1** |

**What this confirms:**

- The development counts match v3 and `eligibility_snapshot.csv`.
- The proposed test list (2023-Q4, 2024-Q1–Q4, 2025-Q1, 2025-Q4) is the set of labelled quarters from 2023-Q4 to 2025-Q4 with at least 8 eligible training quarters. 2025-Q2 and 2025-Q3 have no definition-A label.
- **All 12 MODEL-A inputs are inside the development mask.** 9 of them are inside the strict mask.

### 3.2 Interval arithmetic: checked, with its assumptions

**Clopper–Pearson exact 95% lower bounds:**

| Correct / rows | 95% lower bound |
|---|---:|
| 32/35 | 0.769 |
| 31/35 | 0.733 |
| 30/35 | 0.697 |
| 28/35 | 0.631 |
| 10/10 | 0.692 |
| 7/7 | 0.590 |
| 6/7 | 0.421 |

The v3 statements are correct: at least 32/35 is needed to clear 0.75, and 10 rows can never clear it.

**Assumption:** these bounds treat the 35 rows as **independent Bernoulli trials with a common accuracy.**

**Why rows are not independent:**

1. **Shared hunger outcome.**
   - The SWS term of Equation 3 is the single Balance-Luzon value, the same for all five provinces in a quarter.
   - The provinces differ only through 2 × the provincial CPI deviation.
   - The deviation has a cross-province mean of zero by construction, so the five labels in a quarter are tied to one regional number.
2. **Shared inputs.** Most predictors (SWS input, national series, climate) are common within a quarter.
3. **Shared threshold.** Under A-origin, τ_T is common to the fold.
4. **Errors cluster.** One wrong regional reading tends to produce several wrong rows at once.

**What this means for the effective sample size:**

- With an intra-quarter error correlation ρ, n_eff ≈ 35 / (1 + 4ρ).

  | ρ | 0 | 0.25 | 0.5 | 0.75 | 1 |
  |---|---:|---:|---:|---:|---:|
  | n_eff | 35 | 17.5 | 11.7 | 8.8 | 7 |

- **At the quarter level (n = 7), even a perfect 7/7 gives a lower bound of only 0.59.**
- The Clopper–Pearson interval on 35 rows is therefore an **optimistic, lower-limit statement of uncertainty**.
- The quarter-cluster bootstrap is the more honest headline, but with only 7 clusters its percentile intervals tend to be too narrow.
- **Neither can support a 75% claim.** The protected 2026-Q3/Q4 set is about 2 effective units.

### 3.3 Earlier results that used a global threshold

| Study (docs/) | Threshold | Basis |
|---|---|---|
| `OPTIMIZATION_REPORT_2026-10-08`, `MODEL_B2_ROBUSTNESS_REPORT_2026-10-08`, `RELIABILITY_REVIEW_2026-10-08`, `METHODOLOGY_REVIEW_2026-10-08` | **14.6** | Global median over the 95 labelled 2020–2025 rows |
| `OVERFITTING_AUDIT_MODEL_B2_2026-10-09`, `GENERALIZATION_STUDY_2026-10-09`, `IMPROVEMENT_STUDY_2026-10-09` | **14.6** | Same; 55 of the 95 rows are from the test period |
| `WINDOW_2021_2026_STUDY_2026-10-09`, `ORIGIN_INFORMATION_STUDY_2026-10-09`, `DATA_AND_EVALUATION_DESIGN_AUDIT_2026-10-09` (including the rule-L 72.5% figures) | **14.345** | Global median over the 80 labelled 2021–2025 rows. The window study also ran 14.6 as a sensitivity. |

**Why none of them establishes leakage-free performance:**

1. **The threshold includes the evaluated quarters' own stress scores and later ones.** It decides which training rows are HIGH, the Equation 3 rule baseline and carry-forward, and the class weights. The class boundary was therefore known from the future.
2. **Most of them also predate Rule L.** Training labels were used before publication, and the inputs used older timing rules.
3. **All of them reused the same quarters** and were selected or compared after results were seen.

**The `backend/` served model is a separate case.**

- It is trained on `label_cpi` (Equation 4), described in `label_generator.py:394` as a rolling 24-quarter mean + 1σ rule, not a global median.
- Its reported metrics (walk-forward 0.884 and holdout 1.0) are therefore **not** affected by the C1 leak.
- **They are also not Equation 3 results.** Whether its rolling window is strictly backward-looking was not checked here.

**Disclosure required for C1.**

- A **training-only median** variant has already been run and reported once. The overfitting, generalization and improvement studies report 70.9% (MODEL-B2) and 72.7% (P), with thresholds of 12.1–14.3, on the 2020–2025 window before Rule L.
- The researcher and I have therefore **already seen a result of a design close to A-origin**.
- The C1 recommendation was based on validity arguments, but it is **not fully result-blind**. This must be disclosed in the pre-registration before freezing (§6, item 4).
- Those numbers come from a different window, different eligibility and different timing. They are not a preview of the v3 result.

### 3.4 Exploratory analysis vs a final thesis accuracy claim

| Requirement | Exploratory run (v3) | Final thesis accuracy claim |
|---|---|---|
| Evaluated quarters | Reused 2023-Q4 to 2025-Q4 allowed, labelled exploratory | Never used before and never seen. Only 2026-Q3/Q4 qualify. |
| Threshold | C1 designation recorded before the run | Approved 14.345, fixed before the outcomes; no 2026 rows in the threshold |
| Input dates | Development protocol (WD1 proxy, WD2 revised) allowed, disclosed | Verified dates and point-in-time vintages, or the strict mask only |
| SWS values | V-single allowed, with S4 | June, September and November 2025 confirmed (C6); C8 resolved |
| Label population | Disclosed (C4) | Adviser decision D3 |
| Forecast freezing | Pre-registration frozen and hashed before the run | Forecasts frozen and hashed **before** any outcome component is seen: the 2026-Q3/Q4 SWS **and** the July–December 2026 provincial CPI |
| Sample size | Any, with honest intervals | Must be adequate. ≤ 10 rows cannot establish 75%, so the claim can only be a point estimate with an interval. |
| Served system | Not involved | Model version pinned (C9 settled) |
| Approvals | Researcher authorization; adviser for C1 (or the fallback) | Adviser approval of the target definition, D3, and WD1/WD2/WD5 |

### 3.5 Who decides what

**Target-definition decisions: adviser approval required.**

- C1: whether the origin-relative threshold may be the exploratory primary analysis.
- The wording "median of the 80 labelled 2021–2025 pairs" in place of "all 120 pairs".
- C4/D3: whether rounds from three respondent populations form one label series.
- The reading of "8 consecutive quarters" in Algorithm 3 (an interpretation of Chapter III).
- Confirmation of WD1, WD2 and WD5 for any reported claim.

**Operational decisions: the project team.**

- The scheduler setting (§1.3).
- Whether and when to perform the C6 manual verification.
- Correcting documentation, such as the November source attribution and status labels, in **new** files.
- Writing and reviewing the experiment runner.
- When to freeze and hash.
- Authorizing the run.
- The timing of any separately authorized protected-evaluation collection.

## 4. Outstanding decisions, owners and deadlines

| # | Decision | Owner | Deadline |
|---|---|---|---|
| 1 | Apply `SCHEDULER_ENABLED=false` (§1.3) or explicitly accept the risk | Researcher | **Before 2026-10-15 02:00 Asia/Manila**, and before any `backend/` server start from now on |
| 2 | Do not trigger manual pipeline runs (admin endpoint or CLI) | Team | Until evaluation decisions are settled |
| 3 | C1: exploratory primary design | Adviser | Before the v3 freeze |
| 4 | Add the disclosure of the earlier training-only-median result (§3.3) to the pre-registration (as v4 or an addendum) | Researcher | Before the freeze |
| 5 | C3: "8 eligible" vs "8 consecutive" | Researcher, with an adviser note | Before the freeze |
| 6 | C4/D3: label population composition | Adviser | Before any final claim |
| 7 | C6: manual SWS verification, and resolution of §2.2 item 3 | Researcher (authorization) | Before any final claim. Recommended before the exploratory run, because November 2025 is a label. |
| 8 | C8: the June 2026 SWS publication date (date only) | Researcher (authorization) | Before the 2026-Q4 forecast freeze |
| 9 | Protected 2026-Q3/Q4 freeze | Researcher (separate authorization) | **Before any 2026-Q3 outcome component is seen.** The September 2026 SWS release date was not looked up. The July–September 2026 CPI is likely already public, so it must not be fetched; the scheduler's government stage would fetch it (§1.1). |
| 10 | WD1/WD2/WD5 confirmation | Adviser | Before any final claim |

## 5. Corrections to earlier reports

Earlier files are not edited; the corrections are recorded here.

1. **`FINAL_METHODOLOGY_AUDIT_2026-10-11.md` §5.1** said "a server that starts between 02:00 and 08:00 on 2026-10-15 still fires the job". **That is wrong.** With the in-memory job store, a process started after 02:00 schedules the next run for 2027-01-15. The grace window applies only to a process already running at 02:00.
2. **The same report, §2.2,** said "under the strict protocol, every exploratory fold has 0 eligible quarters". **2025-Q4 has 1** (2024-Q4).
3. **The same report (C10, §1.3) and `PREREGISTRATION_CONFLICT_RESOLUTION_2026-10-11.md` (C10)** said every earlier accuracy used 14.345. **The 2026-10-08/09 studies used 14.6.** One family of studies also reported a training-only-median variant (§3.3).
4. **Earlier summaries** described the scheduler issue as `backend/` only. The aligned backend has its own scheduler, but it is disabled by default (§1.4).
5. **The same report, §5.1,** said only that the admin endpoint "also promotes". It should also say that the endpoint is **not** blocked by `SCHEDULER_ENABLED=false` (§1.2).

## 6. Checklist before model execution

**Before the exploratory development run:**

- [ ] 1. The scheduler protection is applied and verified (§1.3), or the risk is explicitly accepted in writing.
- [ ] 2. The C1 designation is recorded: adviser approval of A-origin, or the fallback (A-global primary, labelled leaky).
- [ ] 3. The C3 reading is recorded.
- [ ] 4. The prior training-only-median exposure is disclosed in the pre-registration (v4 or an addendum; v3 preserved).
- [ ] 5. The experiment runner script is written, implementing v3 §3 and the §11 runtime assertions. It is reviewed without being run, and its SHA-256 is included in the freeze. **It does not exist yet.**
- [ ] 6. The baseline hashes of the aligned `data/processed/*`, `models/*` and `sws_hunger_fetcher.py` are recorded at freeze time.
- [ ] 7. The full test suite passes (175 expected), plus any tests for the runner.
- [ ] 8. The pre-registration is frozen and hashed with your authorization.
- [ ] 9. You explicitly authorize the run.
- [ ] 10. Recommended: C6 is verified first, because the November 2025 value is the 2025-Q4 label.

**Additionally, before any final thesis accuracy claim:**

- [ ] 11. Adviser decisions on D3, the threshold wording, and WD1/WD2/WD5.
- [ ] 12. C6 complete, with saved and hashed source copies; §2.2 item 3 resolved.
- [ ] 13. C8 complete.
- [ ] 14. The protected 2026-Q3/Q4 forecasts are frozen and hashed before any outcome component (SWS or provincial CPI) is seen, under a separately authorized protocol.
- [ ] 15. The served model version is pinned and recorded.
- [ ] 16. The claim is stated as a point estimate with an interval. **No 75% claim is possible from ≤ 10 rows or 7 reused quarters.**

## 7. Tests

**Not needed for this audit.** No code was changed. The suite was last run in this session (175 passed), and no code has changed since.

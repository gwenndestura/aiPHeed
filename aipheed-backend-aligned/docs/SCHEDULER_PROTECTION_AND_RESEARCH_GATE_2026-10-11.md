# Scheduler Protection Check and Research Gate (2026-10-11)

**Scope:** read-only inspection.

**What was not done:**

- No backend was started, no pipeline was run, and no endpoint was called.
- No setting, code, model, dataset or forecast was changed.
- No model was trained or scored, and no accuracy was computed.
- No SWS value was retrieved, and nothing about September or December 2026 was accessed.
- Nothing was committed or deployed.

**Earlier reports:** preserved unchanged.

---

## Phase 1: Is the scheduler protection reliable?

### 1.1 How the production backend (`backend/`) is normally started

| Path found | Working directory | Is `backend/.env` loaded? |
|---|---|---|
| Root `README.md` "Run the API": `cd aiPHeed/backend` (l.18), then `uvicorn app.main:app --reload` (l.48) | `backend/` | **Yes**: scheduler off |
| `backend/` integration tests: `with TestClient(app)` (`test_api_admin.py:67`, `conftest.py`). This **runs the app lifespan**, so it calls `scheduler.start()`. | Wherever pytest is launched. The README says `python -m pytest tests -q` from `backend/`. | Yes from `backend/`. **From the repo root, no**: a scheduler would start inside the test process for the length of the test run. It could only fire if the tests happened to be running at 02:00 on the 15th. |
| `.claude/launch.json` "aipheed-api-aligned" | `aipheed-backend-aligned/` | Not applicable. It starts the **aligned** API, whose scheduler is off unless `AIPHEED_ENABLE_SCHEDULER=1` (unset). It does not start `backend/`. |

**Not found:**

- No startup path exists in a Procfile, Dockerfile, compose file, Render, Fly or Railway config, a systemd or `.bat` file, `.vscode/`, the frontend `package.json` scripts, a Vite proxy, the Windows Startup folder or the HKCU Run key.
- Nothing is listening on port 8000 now.
- The frontend never calls `/admin/pipeline/run`.

**Conclusion:** every **documented** way of starting `backend/` uses `backend/` as the working directory, so the protection holds.

**The undocumented risk:** starting it from the repo root, for example `uvicorn app.main:app --app-dir backend`, or an IDE or agent choosing its own folder. Confirmed earlier today:

- from the repo root, `settings.SCHEDULER_ENABLED` reads **True**;
- from `backend/`, it reads **False**.

### 1.2 Could anything automatic call the pipeline?

| Mechanism | Finding |
|---|---|
| Windows Task Scheduler | No enabled task refers to aipheed, uvicorn, python, curl or port 8000 |
| Session crons (CronList) | None |
| `backend/` cron job | Disabled by `.env` when started from `backend/` |
| Aligned-backend scheduler | Off: `AIPHEED_ENABLE_SCHEDULER` is unset |
| Tests | `test_manual_run_is_refused_while_one_is_in_progress` posts to `/admin/pipeline/run`, but only while a temporary lock is held, so it always gets 409 and **never starts a run**. Pipeline unit tests replace every stage with stubs and use temporary directories. |
| **Claude Desktop scheduled tasks** | **Two are enabled and run every day in this project. See below.** |

**The two scheduled tasks:**

| Task | Schedule | Prompt (summary) | Runs |
|---|---|---|---|
| `aipheed` | 09:03 daily | Review, audit and check deeply that everything is working correctly | 73 runs; the latest started 2026-10-11 10:16 UTC and was still "running" |
| `aipheed-auditing` | 15:03 daily | Check deeply that the methodology and data are correct and that the sources are credible | 80 runs; the latest started 2026-10-11 10:16 UTC and was still "running" |

**Why they matter:**

- They are not hard-wired to call the pipeline. But they are **unattended, open-ended agent sessions with no restrictions** in their prompts.
- Such a session could start `backend/` from any folder, run the pipeline CLI or admin endpoint, "fix" settings or code, or download data.
- The auditing task asks for source checks. That invites browsing sws.org.ph and PSA, which could expose **September 2026 SWS** results or **July–September 2026 provincial CPI**, both components of the protected 2026-Q3 outcome.
- Neither fires at 02:00, so neither can trigger the 2026-10-15 cron. Their risk is to direct pipeline runs, configuration changes and protected-outcome exposure.
- Recent completed runs lasted a few seconds each, so they appear to have done little. Their content was not inspected.

### 1.3 Remaining protection gaps

1. **Working-directory dependence.** The `.env` file is only read when the server starts from `backend/`.
2. **The manual pipeline paths are not blocked.** `POST /api/v1/admin/pipeline/run` and `python -m app.tasks.quarterly_pipeline` ignore `SCHEDULER_ENABLED`. Either can retrain, promote, and download 2026 data. **They must not be triggered.**
3. **Unrestricted daily agent sessions** (§1.2).
4. **Tests launched from the repo root** would start an in-process scheduler (minor).

### 1.4 Smallest safe improvements (not applied; each needs your authorization)

**For gap 1, choose one.**

**(a) Configuration only, no code change.** Set a persistent user environment variable. Environment variables override `.env` regardless of the working directory. PowerShell, run once:

```powershell
[Environment]::SetEnvironmentVariable('SCHEDULER_ENABLED', 'false', 'User')
```

- It applies to processes started **after** it is set. Restart terminals, the IDE and the Claude app.
- It also covers tests run from the root. The tests that need the scheduler monkeypatch the setting themselves.
- **Verify** from the repo root, without starting anything:

  ```bash
  PYTHONPATH=backend backend/venv/Scripts/python.exe -c "from app.config import settings; print(settings.SCHEDULER_ENABLED)"
  ```

  It must print `False`.

**(b) A one-line code change.** In `backend/app/config.py`, anchor the `.env` path to the package location:

```python
env_file=str(Path(__file__).resolve().parents[1] / ".env")
```

This also needs `from pathlib import Path`. It makes every setting in `.env` load from any folder. It is a production code change, so run the `backend/` test suite afterwards.

**Recommendation:** (a) now, because it is reversible and involves no code. (b) can follow later as a permanent fix.

**For gap 2 (optional code change):** add a guard in `scheduler.start_in_background` that refuses a manual run while a new setting, for example `PIPELINE_MANUAL_RUNS_ENABLED=false`, is set. `test_api_admin.py` would need a matching test. Until then, rely on the operating rule: **do not trigger it.**

**For gap 3 (your decision; no change made):** do one of the following until the protected 2026-Q3/Q4 forecasts are frozen:

- pause `aipheed` and `aipheed-auditing` (toggle them off in the Claude app's scheduled-tasks panel); or
- add explicit restrictions to their prompts:
  - no starting servers;
  - no pipeline, training or data downloads;
  - no browsing SWS or PSA pages for 2026 results;
  - no editing of `.env` or code.

---

## Phase 2: Research gate (outstanding items before model execution)

**Sources:**

- `PREREGISTRATION_DRAFT_v3.md`
- `FINAL_METHODOLOGY_AUDIT_2026-10-11.md`
- `PRE_RUN_AUDIT_AND_SCHEDULER_REVIEW_2026-10-11.md`

**Key:** **E** = must be resolved before the exploratory run. **F** = must be resolved before any final thesis accuracy claim.

| # | Item | Status now | Needed | Owner | Gate |
|---|---|---|---|---|---|
| 1 | **Threshold definition (C1)** | v3 recommends: origin-relative τ_T as the exploratory primary, with 14.345 (labelled leaky) as secondary; the approved 14.345 for the protected 2026-Q3/Q4 evaluation | Adviser approves A-origin, or the fallback is recorded (14.345 primary, labelled not leakage-free). Adviser accepts the wording "median of the 80 labelled 2021–2025 pairs" in place of "all 120 pairs". | **Adviser** | E (designation); F (wording) |
| 2 | **Minimum training window (C3)** | 2023-Q3 has 7 eligible quarters and is excluded under any reading. Primary: "at least 8 eligible", giving 7 test quarters (35 rows). Literal "8 consecutive" (S6): first fold 2024-Q3, giving 4 quarters (20 rows). | A recorded reading | Researcher, with an adviser note | E |
| 3 | **Earlier 70.9% training-only-threshold result** | Reported in the overfitting, generalization and improvement studies: 70.9% MODEL-B2, 72.7% P; thresholds 12.1–14.3; 2020–2025 window, before Rule L. **The C1 choice is therefore not result-blind.** | Disclosure added to the pre-registration as v4 or an addendum (v3 preserved): what was seen, when, and why the design differs | Researcher | E |
| 4 | **2025 SWS source verification (C6)** | April V. November date V, value V from two releases but no saved copy. **June and September are V-single** for value, date, population and sampling error. November's production citation points to a later release. The April release's prior-round figures are unidentified. | Manual verification with saved, hashed copies, navigating only to the four direct URLs. Correct the citation and status labels in **new** files. | Researcher (authorization) | F; **recommended before E**, because November 2025 is the 2025-Q4 label |
| 5 | **Publication-date eligibility (Rule L)** | Development protocol: WD1 provincial-CPI proxy (national + 14 days) and WD2 revised climate inputs. Strict protocol: 0 training quarters for 2023-Q4 to 2025-Q1, and 1 for 2025-Q4. June 2026 SWS date unknown (C8). | E: proceed with the development protocol, disclosed. F: the 19 RSSO IV-A provincial dates and point-in-time vintages (or the strict mask only); C8 date; adviser confirmation of WD1, WD2 and WD5. | Researcher / Adviser | E (disclosure); F |
| 6 | **Protected forecast freeze** | 2026-Q3/Q4 are protected, and their origins (2026-07-01, 2026-10-01) have passed, so the forecasts are retrospective (L6). No 2026 row may enter the threshold or the training data. | Separate authorization. Forecasts frozen and hashed **before any outcome component is seen**: the September and December 2026 SWS **and** the July–December 2026 provincial CPI. The scheduler, manual pipeline and agent sessions (Phase 1) must not fetch them first. Pin the served model version. | Researcher | F |
| 7 | **Reused quarters and limits on claims** | All 2023-Q4 to 2025-Q4 test quarters were used before. Rows within a quarter share the SWS value, so n_eff ≈ 7. Even 7/7 gives a 95% lower bound of 0.59. 35 rows need ≥ 32 correct even under independence. 10 protected rows can never clear 0.75 (10/10 gives 0.69). | Every result labelled "exploratory development estimate on 7 reused quarters". Quarter-cluster bootstrap as the headline interval, with Clopper–Pearson labelled optimistic. **No 75% claim from any of these sets.** | Researcher | E and F |
| 8 | **Respondent population (C4/D3)** | Labels mix household heads, registered voters (2025-Q1) and adults 18+ (2025-Q4) | Adviser decision | **Adviser** | F (disclosed for E) |
| 9 | **Execution prerequisites** | The runner script does not exist | Write the runner (v3 §3 and §11 assertions) and review it **without running it**. Record hashes. Tests pass. Freeze and hash the pre-registration. **Explicit run authorization.** | Researcher | E |

### Decisions needed before modelling

1. **Adviser:**
   - C1 designation and the "80 labelled pairs" wording (item 1);
   - D3 (item 8);
   - WD1, WD2 and WD5 (item 5).
2. **Researcher:**
   - the C3 reading (item 2);
   - the content of the 70.9% disclosure (item 3);
   - whether to verify the 2025 SWS rounds before the exploratory run (item 4);
   - authorization to write the runner (item 9);
   - the freeze, then the run.
3. **Researcher, protection:**
   - gap 1 fix (a) or (b);
   - what to do about the two daily scheduled tasks (gap 3);
   - **continue not to trigger the manual pipeline** (gap 2).

**Stopping here.**

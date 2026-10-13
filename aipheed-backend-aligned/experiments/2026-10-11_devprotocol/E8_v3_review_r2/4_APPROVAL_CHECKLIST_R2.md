# Approval Checklist, Revision r2

**Status: 2026-10-12. Nothing in §2 is approved. Nothing in §2 has been executed.** This supersedes neither `E8_v3/5_APPROVAL_CHECKLIST.md` nor `E8_v3_review/3_APPROVAL_CHECKLIST_REVIEW.md`; both are preserved. Mapping to the older IDs is shown where one exists.

## 1. Actions already authorized (record, not recommendation)

| Action | Authorized | Status |
|---|---|---|
| Append `SCHEDULER_ENABLED=false` to `backend/.env` | 2026-10-11 | Done. Line present (count-only check, 2026-10-12). |
| E1–E7 isolated runs and the served-artifact wiring in the isolated backend | 2026-10-11/12 (earlier turns) | Done; artifacts hash-verified |
| Planning and review documents in `aipheed-backend-aligned/experiments/2026-10-11_devprotocol/` | Each documentation request | Done; this folder |

**Not authorized:**

- disabling tasks or stopping sessions;
- building or running tests;
- any repository action;
- evaluation, calibration or rescoring;
- any production change, commit, push or deployment.

## 2. Decisions awaiting approval

**Column meanings:**

| Column | Meaning |
|---|---|
| **Rev.** | Reversible |
| **Thesis** | Is it needed for the thesis? "Required" means for the stated thesis component only. |
| **Recommendation** | Kept separate from the decision column |

### 2.1 Scheduled tasks and their sessions

| ID | Purpose | Exact action | Data that could be touched | Prerequisites | Rev. | Thesis | Recommendation | Decision needed |
|---|---|---|---|---|---|---|---|---|
| SA-1 | Stop daily runs that can read protected files and search the web | `update_scheduled_task(taskId="aipheed", enabled=false)`; `update_scheduled_task(taskId="aipheed-auditing", enabled=false)` | Task configuration only | None | **Yes** (re-enable) | Not required; protects the evaluation | **Recommended before 2026-10-13 09:02 local** | Approve or decline. If declined, state that you accept risks R1–R5. |
| SA-2 | Interrupt the two stalled sessions (any pending prompt is discarded) | `stop_session` on `local_f3c4b65e-be65-409f-a1c9-1e29c11d1321` and `local_918f3167-4ff0-47f4-bc3b-115ea28d8055`; **transcripts not opened** | None (interrupts a turn; the session stays open and idle) | None | Partly (the interrupted turn is not resumed) | Not required | Recommended with SA-1 | Approve or decline |
| SA-3 | Close the sessions fully | `archive_session` on the same two IDs | None | SA-2 | Yes (unarchive) | Not required | Optional | Approve or decline |
| SA-4 | Defence in depth | Add `deny` rules (protected paths, `WebSearch`, `WebFetch`) to `.claude/settings.local.json` | Persistent configuration; also affects your sessions | None | Yes | Not required | Optional. Note that `Bash` can bypass `Read` rules. | Approve or decline |

### 2.2 Isolated synthetic-data tests

| ID | Purpose | Exact action | Data that could be touched | Prerequisites | Rev. | Thesis | Recommendation | Decision needed |
|---|---|---|---|---|---|---|---|---|
| T-1 | Make tests independent of protected and carrier files | Write a deterministic synthetic-fixture generator, a path-redirect fixture, a session-wide deny-list guard and a `real_data` marker (risk map §3) in `aipheed-backend-aligned/tests/`. **Existing tests not edited** unless T-1b is approved. | Synthetic data only. New files in the isolated `tests/`. | None | Yes (new files) | Required for **trustworthy regression testing** | Recommended | Approve or decline |
| T-1b | Point the 11 carrier-loading tests at the fixture | Edit those test files to use the fixture, or mark them `real_data` | Test code only | T-1 | Yes | Same | Recommended after T-1 | Approve or decline |
| T-2 | Run **only** the synthetic tests | `pytest -m "not real_data"` under the guard, in the isolated backend | Synthetic fixtures. The guard fails any test that touches the deny-list. | T-1 (+T-1b) | Yes (no writes beyond pytest cache) | Same | Recommended | Approve or decline |

### 2.3 Repository exposure investigation and remediation

| ID | Purpose | Exact action | Data that could be touched | Prerequisites | Rev. | Thesis | Recommendation | Decision needed |
|---|---|---|---|---|---|---|---|---|
| RP-1 | Learn visibility, forks and collaborators | `gh repo view gwenndestura/aiPHeed --json visibility,isFork,forkCount`; you check collaborators in GitHub settings | Repository metadata (network, read-only); **no file content** | None | Yes (read-only) | Not required | Recommended | Approve, or do it yourself |
| RP-2 | Establish whether origin still holds eee269b | `git ls-remote origin refs/heads/backend+frontend` (lists the ref hash only; downloads no objects) | Remote ref metadata | None | Yes | Not required | Optional | Approve or decline |
| RP-3 | Ask the collaborators (Christina Esico; the owner, gwenndestura) not to open the affected paths until outcome collection | A message from you (Claude does not send it) | None | None | — | Not required | Recommended | Yours to send |
| RP-4 | Restrict access if the repository is public | Owner changes visibility to private and reviews collaborators | Repository settings | RP-1 | Yes | Not required | Recommended **if public** | Owner's decision |
| RP-5 | History cleanup | `git filter-repo` removing the affected paths, force-push, collaborators re-clone, GitHub cache purge | All branches. Breaks commit IDs used in integrity records. | RP-1, RP-4, the owner and collaborators | **No** | Not required | **Not recommended** for a blinding concern | Approve or decline (owner) |

### 2.4 Test suite

| ID | Purpose | Exact action | Data that could be touched | Prerequisites | Rev. | Thesis | Recommendation | Decision needed |
|---|---|---|---|---|---|---|---|---|
| TS-1 | Full isolated-backend regression run | `pytest` in `aipheed-backend-aligned` **with the guard active**; `real_data` tests only if TS-1b is approved | Allowlist candidates; served artifacts. With TS-1b: carriers in memory. | T-1, T-1b | Yes | Required for software quality | After T-2 | Approve or decline |
| TS-1b | Run the `real_data` tests | As above, including the marked tests | **Carriers** (`sws_hunger`, corpus) in memory; a failing assertion could print values | TS-1; the evaluation frozen (EV-5) or you accept the risk | No (if values are printed) | Not required | **Defer until after EV-5** | Approve or decline |
| TS-2 | Production backend tests | `pytest` in `backend/` under the guard, after tracing `app.main` imports | Possibly P3 via imports (not fully traced) | T-1 guard; import trace | Yes | Required if the thesis documents production (S6) | After the trace | Approve or decline |
| TS-3 | Frontend checks | `npm run lint`, type-check, `vitest run`, `vite build` in `frontend/`; **no live API** | Source code only | None | Yes | Required for software quality | Recommended | Approve or decline |

### 2.5 Model evaluation and calibration

| ID | Old ID | Purpose | Exact action | Data that could be touched | Prerequisites | Rev. | Thesis | Recommendation | Decision needed |
|---|---|---|---|---|---|---|---|---|---|
| EV-1 | A1 | Adopt the protocol | Approve an E8 protocol text that incorporates review r2 (R1–R9), and record its SHA-256 | None | Text written (not yet) | Yes until EV-5 | Required for any evaluation chapter | Recommended | Approve the text when written |
| EV-2 | A4 | Gross-failure margins | Approve G-P (0.35), G-S (6.0), G-R (≤ 3/10) as **single-quarter indications** | None | EV-1 | Yes until outcomes are seen | Optional | Recommended | Approve, modify or decline |
| EV-3 | new | 2026-H1 food CPI index level | (1) drop `food_cpi` level from A2/A3; or (2) date-limited OpenStat collection, January–June 2026 | (2): web; exposed 2026-H1 only | EV-1 | (1) yes; (2) yes | Required before EV-5 | **(1)** | Choose (1) or (2) |
| EV-4 | A5 | Build the allowlist-only frame | Frame code + manifest + tests (synthetic) in the isolated backend; build from allowlisted files under the guard | Allowlisted files | EV-1, EV-3, T-1 | Yes | Required | — | Approve or decline |
| EV-4b | A6 | 2026-Q1 label | Use or exclude (default: exclude) | Exposed 2026-Q1 data | EV-1 | Yes | Optional | Exclude | Decide |
| EV-5 | A8 | Generate and freeze forecasts for C3 and C4 | As in A8. **Must finish before any Q4 outcome is published (R2, Q4-b).** | Allowlisted inputs | EV-1 to EV-4b; SA-1 decided | **No** in substance | Required for any Q4 evaluation | **Time-critical** | Approve or decline |
| EV-6 | A9-Q4 | Collect the Q4 outcome | Primary-source collection after release (expected 2027) | **P1/P2 for Q4** | EV-5 freeze re-verified | **No** | Required for a Q4 result | When available | Approve then |
| EV-7 | A9-Q3 | Collect the Q3 outcome (exposure-qualified, descriptive) | Primary-source collection | **P1/P2 for Q3** | EV-5 | **No** | Optional (descriptive only) | Defer until after EV-5 | Approve or decline |
| EV-8 | A3a/c | Verify release dates | RSSO IV-A and SWS dates | Web, which may show P1/P2 | **After EV-6/EV-7** | No | Needed only for a "verified" label | After the outcomes | Approve later |
| CAL-1 | B5 | Calibration | Keep "uncalibrated" (default), or calibrate on training-only folds; **no evaluation-quarter data** | Training data | EV-5 report | Yes | Optional | Keep uncalibrated | Decide |
| MD-1 | A10 | Served-model decision | Keep M6 (default) or switch | Served artifacts | E8 report; S6 decision | Yes | Optional | Keep M6 | Decide after the report |

### 2.6 Dashboard rescoring

| ID | Purpose | Exact action | Data that could be touched | Prerequisites | Rev. | Thesis | Recommendation | Decision needed |
|---|---|---|---|---|---|---|---|---|
| DB-1 | Change served classifications (e.g., τ 10.843 → 14.345, or calibration) | Rebuild the served artifacts and assessment outputs in the isolated backend | Served artifacts; inputs ≤ 2026-Q2 | MD-1 / CAL-1 decision | Yes (earlier artifacts kept) | Not required | **Not proposed** | Decide only if MD-1/CAL-1 change outputs |

### 2.7 Production changes and deployment (all remain unauthorized)

| ID | Purpose | Exact action | Data that could be touched | Prerequisites | Rev. | Thesis | Recommendation | Decision needed |
|---|---|---|---|---|---|---|---|---|
| PR-1 | Fix production code or tests | Edits in `backend/` or `frontend/` | Production code; possibly P3 via runs | TS-2 / TS-3 results; S6 | Yes (git) | Required only if the thesis documents production | After S6 | Decide per change |
| PR-2 | Re-enable or run the production pipeline | Change `.env` or run `quarterly_pipeline` | **Fetches P2** into production | After EV-6 | No (data acquired) | Not required | **Keep disabled** | Decide after E8 |
| PR-3 | Commit | `git commit` of named files | Repository | Reviewed diff | Yes (until push) | Required for release | Later | Per commit |
| PR-4 | Push or merge | `git push` / merge | **Remote (publishing)** | PR-3; RP-1 | No (once published) | Required for release | Later | Per push |
| PR-5 | Deploy | Deployment of backend or frontend | Public service | PR-4 | Partly | Required for release only | Later | Per deployment |

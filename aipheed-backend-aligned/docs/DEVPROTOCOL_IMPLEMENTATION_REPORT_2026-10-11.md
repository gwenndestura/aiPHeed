# Development-Protocol Implementation Report (2026-10-11)

**Authorized scope:** an experimental module, unit tests, the inclusion of the three collected 2025 SWS rounds as inputs, and a draft pre-registration.

- **Not done:** no model was trained or scored, no accuracy was computed, and no hyperparameter was tuned. No label was rebuilt and no existing data changed. The scheduler, `SCHEDULER_ENABLED`, production, frozen forecasts, the protected protocol, the thesis and earlier reports are untouched. Nothing was committed or deployed.
- **Not accessed:** no September or December 2026 SWS result.

## New files

| Path | Purpose |
|---|---|
| `scripts/supplementary/devprotocol_rule_l.py` | Experimental module (outside `app/`): SWS round registry with publication dates; refined Rule L label timing; development frame; protocol masks; eligibility table |
| `tests/unit/test_devprotocol_rule_l.py` | 16 unit tests |
| `experiments/2026-10-11_devprotocol/PREREGISTRATION_DRAFT.md` | Draft pre-registration (not frozen) |
| `experiments/2026-10-11_devprotocol/eligibility_snapshot.csv` | Per-target training eligibility (development and strict) and the SWS input used |
| `experiments/2026-10-11_devprotocol/sws_round_registry_dates_only.csv` | Every SWS round: publication date, date type, source, label membership (no values) |
| `docs/DEVPROTOCOL_IMPLEMENTATION_REPORT_2026-10-11.md` | This report |

## What the module implements

| Rule | Implementation |
|---|---|
| **Date types** | Every date is `verified`, `verified-single`, `proxy` (WD1), `schedule` (WD3) or `unknown`. Unknown is never treated as available (L4). |
| **SWS inputs** | 23 rounds: 20 from the production table, read only, up to `SWS_COVERAGE_END = (2026, 2)`, plus 3 supplementary 2025 rounds. The latest round published before the origin is selected **per round**. June 2026 (date unknown) is excluded. The supplementary rounds are inputs only (`in_label_definition_A = False`). |
| **Label timing (L1)** | The later of the last contributing SWS round and the final-month provincial CPI date. That CPI date is verified only for 2024-Q4; otherwise it is the national release + 14 days (proxy), or a schedule where no national date is documented. 2021 labels are not before 2022-02-04 (WD5). Under the strict protocol, proxy- or schedule-dated labels are ineligible. |
| **Inputs** | Built on the corrected window frame (K1–K4, rule W, strict timing). CPI inputs follow WD1/WD5. Other families follow documented schedules (WD3). Retail rice is excluded. Unavailable values are NaN. |
| **Masks** | Development: 49 of 51 inputs. Strict: 22 of 51. Read from `evidence/2026-10-11_working_decisions/feature_eligibility_by_protocol.csv`. |

## Test results

- **New tests:** 16/16 passed (`tests/unit/test_devprotocol_rule_l.py`).
- **Full suite:** **175 passed, 0 failed** (159 earlier + 16 new).

The tests cover:

- **Date eligibility:** SWS inputs published before the origin; unknown-date rounds excluded; supplementary rounds used at the 2025-Q3, 2025-Q4 and 2026-Q1 origins.
- **Label timing:** every training label published before the origin; the two-round 2022-Q2 label waits for its second round; 2021 labels not before rebasing; the 2024-Q4 label waits for its CPI; the 2025-Q1 label date is the proxy.
- **Verified vs proxy dates:** they stay distinguishable, and the strict protocol keeps only the 2024-Q4 label.
- **Missing values:** NaN, not zero (CPI before 2022-02-04; SWS before the first round).
- **Revised inputs:** development only.
- **Retail rice:** excluded from both masks and from the frame.
- **Mask sizes:** 49 and 22.
- **No protected outcome present, and no production file changed** (hashes before and after).

## Eligibility, reproduced by the module (`eligibility_snapshot.csv`)

| Exploratory target | Training quarters (development) | Strict | SWS input used (published; type; source) |
|---|---:|---:|---|
| 2023-Q3 | 7 | 0 | Mar 2023 (2023-05-11; verified; production) |
| 2023-Q4 | 8 | 0 | Jun 2023 (2023-08-02) |
| 2024-Q1 | 9 | 0 | Sep 2023 (2023-11-20) |
| 2024-Q2 | 10 | 0 | Dec 2023 (2024-01-22) |
| 2024-Q3 | 11 | 0 | Mar 2024 (2024-04-30) |
| 2024-Q4 | 12 | 0 | Jun 2024 (2024-07-23) |
| 2025-Q1 | 13 | 0 | **Sep 2024 (2024-10-17)**, corrected from the earlier studies' Jun 2024 |
| 2025-Q4 | 15 | 1 | **Jun 2025 (2025-08-15; verified-single; supplementary)**, previously the stale Mar 2025 |

These match the earlier audit tables exactly.

## Remaining blockers

**Before any experiment:**

1. **Your authorization** to freeze the pre-registration (hash it) and run it.
2. **Decide C3:** whether to keep the 2023-Q3 fold with 7 training quarters. This must be settled before running.

**For specific parts:**

3. **C1/C2:** the threshold policy for the sensitivity labels (needed for S3), plus authorization to build those labels.
4. **Manual confirmation** of the June, September and November 2025 SWS values and dates ([V-single]). They are used as inputs, flagged.

**For any strict or final claim:**

5. The 19 provincial (RSSO IV-A) CPI dates and the official release calendars.
6. A separately authorized protected 2026-Q3/Q4 freeze-then-collect procedure. It yields at most a point estimate on ≤ 10 rows, which cannot establish 75% accuracy.

**Outside this work:**

7. The `backend/` scheduler run on 2026-10-15 could replace the served thesis model. `SCHEDULER_ENABLED` was not changed; that decision is yours.

**Next step (awaiting explicit authorization):** freeze the pre-registration (after deciding C3) and run the exploratory development experiment as specified, reporting every result as exploratory.

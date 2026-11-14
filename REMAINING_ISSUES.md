# Remaining Issues

- **Branch:** `aiPHeed/final-model-completion-20261113`
- **Date:** 14 November 2026

These items are not resolved by the audit. Because of them, the system is **not declared complete or deployment-ready**.

## Blocking: owner decisions

| ID | Item | Why it is open | What resolves it |
|---|---|---|---|
| R1 | ~~The served 2026-Q4 issue used October CPI and September LFS published after its 1 November cut-off (audit C1).~~ **RESOLVED 2026-11-14.** | Owner chose the monthly rule (data update and forecast on the 10th). 2026-Q4 is kept, marked superseded; the 10 November 2026 issue (`2026-11`) is active and identical in value. | `Q4_2026_FORECAST_CORRECTION_REPORT.md` |
| R2 | ~~FINAL is not the registered production model.~~ **RESOLVED 2026-11-14.** | Owner approved in chat: production with the every-round rule (R1) waived; recorded in `data/registry/registry.json` and `approvals/final-rate-mind-1.0.json`. | — |
| R3 | **Deployed by pushing `main` (Render auto-deploy, Vercel).** | Verified before the push by starting the committed tree exactly as the Render container does (strict mode, fresh database, all migrations): it serves FINAL; the end-to-end trace passes 34/34 against it. The frozen model file had to be committed: it was git-ignored by `*.pkl`. Render cannot run the monthly data stage (raw news archive, OpenVINO scorer); there the 10 December cycle will report the forecast as not yet updated until the issue is built on the data PC and pushed. | Check the live site after Render finishes; build monthly issues on the data PC. |

## Known limitations (documented, not defects of this audit's scope)

| ID | Item |
|---|---|
| L1 | **Validation is thin.** Retrospective validation covers 72 province-rounds over 3 FNRI rounds, also used during development. 2021 HIGH recall is 1 of 4. No lead passes every single round. Only Leads 1–2 are served. |
| L2 | **Poverty and vulnerability are not used by the current forecast.** The live input screen did not select them, and the locked study (`bb63c891`) found no arm that replaces FINAL. They rank towns and are shown only when a forecast uses them. |
| L3 | **Dead frontend code.** The components `NextQuarterOutlook` and `ProvincialOutlook`, and the hooks `useFinalEvaluation`, `useFinalRiskRows`, `useFinalArchive` and `useAudit`, are never rendered or called; they read admin-only `/fi9`, `/fi10` and `/final/archive`. They are left in place: removal is a clean-up, not a correction. |
| L4 | **Stale column in the town base table.** `lgus_next_quarter.csv` has a stale `vulnerability` column (up to 0.096 off 0.6 × poverty percentile + 0.4 × density percentile). It is not read: the served ranking recomputes from the percentile columns. |
| L5 | **Misleading field name.** Served rows carry the share in a field named `probability` (P(HIGH) is in `p_high`). Every consumer reads it correctly, but the name invites errors. Renaming touches E168 and Setup H code paths shared with other branches. |
| L6 | **File-based scheduler lock.** Two app instances on separate disks could both start a cycle. The ledger refuses a second record of the same key and the DB mirror is insert-only and unique, so records are not duplicated, but work could be. |
| L7a | **Monthly cadence not separately validated.** FINAL was validated with issues on the 1st of each quarter's second month; issues on the 10th of other months have not been validated separately (`serving.json → cadence_caveat`). |
| L7b | **The 10 Nov 2026 issue has no news from 1–9 Nov** (not collected; news inputs are those of 1 Aug–31 Oct, as stated). |
| L7 | **Raw news data is not in git.** The stories-read list (`news_used.json`) and the full data stage need git-ignored raw news files (`backend/data/e151/raw`, `e155/raw/sunstar.parquet`). On a server without them, the issue builds without the list and the news panel falls back to the 49-story province-tagged feed. |
| L8 | **ONI context.** The El Niño context sentence uses the newest ONI (Aug–Oct 2026, released ~10 Nov). It is context only, not a model input, and says so. |
| L9 | **Rounded Lucena figure.** Lucena's 2021 poverty figure (10%) is published by PSA to the whole percent only (stated on its card). |
| L10 | **Pre-existing backend test failures.** 22 tests failed before this work. They are mostly protocol hash-locks of earlier experiments (E125–E144, HFIAS, FI9n/x) whose files changed after locking, plus `test_e168_regenerate::test_outlook_reports_origin_and_threshold`, which expects the E168 artifact's old 2026-10-01 cut-off. None tests FINAL. See `DEEP_TEST_RESULTS.md`. |
| L11 | **Lenient refresh rule elsewhere.** The E168 monthly refresh (Windows task "aiPHeed monthly refresh") still uses its lenient refresh-day rule for E168's own artifact. It should be disabled once FINAL is production. Registering the FINAL Windows task is also pending owner approval. |

## Tests that assume E168/E196 is the served model (after the merge with main, 2026-11-14)

The full backend suite on the merged tree: **1705 passed, 100 failed**. Re-running the 100 with `main`'s registry (E196 as
production): 57 pass and 11 skip, so **68 fail only because production is now FINAL**. Of the 32 that fail either way:
- 23 are the known pre-existing failures (protocol locks, "production untouched", E144, FI9n/x, HFIAS, two-folder path test, a
  git-ignored NOAA file);
- 2 (`test_e119r2_framework`, `test_e120_firi_design`) failed only because the registry was swapped during that diagnostic run;
- 7 assert E168/E196 serving or E178 provenance: `test_e168_dashboard` (4), `test_final_audit::test_e168_lead_horizon_and_owner_approval`,
  and `test_e178_*` (3). The E178 checks also no longer hold for E196 because the 10 Nov 2026 panel rebuild (Q4 2026 correction)
  changed inputs that E196's issue was hashed against.

None of them exercises the FINAL serving path (FINAL tests 55/55, accounts 52/52, frontend 106/106, deploy emulation 34/34).
**Open:** mark the E168/E196-serving tests to skip when another model is production, or retire them (a test-suite change, not done here).

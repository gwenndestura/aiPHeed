# Remaining Issues

- **Branch:** `aiPHeed/final-model-completion-20261113`
- **Date:** 14 November 2026

These items are not resolved by the audit. Because of them, the system is **not declared complete or deployment-ready**.

## Blocking: owner decisions

| ID | Item | Why it is open | What resolves it |
|---|---|---|---|
| R1 | **The served 2026-Q4 issue used October CPI and September LFS published after its 1 November cut-off (audit C1).** | Issues are immutable. Re-issuing needs a strict panel rebuild and a recorded withdrawal of the current issue, which rewrites shared panel files and changes a published forecast. Impact bound: ≤ 1.9 points per province; every class stays LOW. | Owner choice: **(a)** keep it, with the disclosure now shown on every surface; or **(b)** withdraw it (`history.record_withdrawal`), rebuild the panels strictly and re-issue 2026-Q4. Future issues are already strict and guarded. |
| R2 | **FINAL is not the registered production model.** | Promotion with the every-round waiver was refused by the automated permission check. It needs the owner's explicit approval (REALTIME report §11). Until then the live site (aipheed.vercel.app) serves E196. | The owner runs the §11 command or approves it in chat. |
| R3 | **Not deployed or tested on Render/Vercel.** | This branch has not been deployed. The audit ran on the local preview (API 8975, web 8097). Render free cannot run the full data stage (OpenVINO news scorer, archives). | Deploy after R2. Run the trace script against the deployed API (`python ../research_notes/audit_20261114/trace_end_to_end.py https://<host>/api/v1`). |

## Known limitations (documented, not defects of this audit's scope)

| ID | Item |
|---|---|
| L1 | **Validation is thin.** Retrospective validation covers 72 province-rounds over 3 FNRI rounds, also used during development. 2021 HIGH recall is 1 of 4. No lead passes every single round. Only Leads 1–2 are served. |
| L2 | **Poverty and vulnerability are not used by the current forecast.** The live input screen did not select them, and the locked study (`bb63c891`) found no arm that replaces FINAL. They rank towns and are shown only when a forecast uses them. |
| L3 | **Dead frontend code.** The components `NextQuarterOutlook` and `ProvincialOutlook`, and the hooks `useFinalEvaluation`, `useFinalRiskRows`, `useFinalArchive` and `useAudit`, are never rendered or called; they read admin-only `/fi9`, `/fi10` and `/final/archive`. They are left in place: removal is a clean-up, not a correction. |
| L4 | **Stale column in the town base table.** `lgus_next_quarter.csv` has a stale `vulnerability` column (up to 0.096 off 0.6 × poverty percentile + 0.4 × density percentile). It is not read: the served ranking recomputes from the percentile columns. |
| L5 | **Misleading field name.** Served rows carry the share in a field named `probability` (P(HIGH) is in `p_high`). Every consumer reads it correctly, but the name invites errors. Renaming touches E168 and Setup H code paths shared with other branches. |
| L6 | **File-based scheduler lock.** Two app instances on separate disks could both start a cycle. The ledger refuses a second record of the same key and the DB mirror is insert-only and unique, so records are not duplicated, but work could be. |
| L7 | **Raw news data is not in git.** The stories-read list (`news_used.json`) and the full data stage need git-ignored raw news files (`backend/data/e151/raw`, `e155/raw/sunstar.parquet`). On a server without them, the issue builds without the list and the news panel falls back to the 49-story province-tagged feed. |
| L8 | **ONI context.** The El Niño context sentence uses the newest ONI (Aug–Oct 2026, released ~10 Nov). It is context only, not a model input, and says so. |
| L9 | **Rounded Lucena figure.** Lucena's 2021 poverty figure (10%) is published by PSA to the whole percent only (stated on its card). |
| L10 | **Pre-existing backend test failures.** 22 tests failed before this work. They are mostly protocol hash-locks of earlier experiments (E125–E144, HFIAS, FI9n/x) whose files changed after locking, plus `test_e168_regenerate::test_outlook_reports_origin_and_threshold`, which expects the E168 artifact's old 2026-10-01 cut-off. None tests FINAL. See `DEEP_TEST_RESULTS.md`. |
| L11 | **Lenient refresh rule elsewhere.** The E168 monthly refresh (Windows task "aiPHeed monthly refresh") still uses its lenient refresh-day rule for E168's own artifact. It should be disabled once FINAL is production. Registering the FINAL Windows task is also pending owner approval. |

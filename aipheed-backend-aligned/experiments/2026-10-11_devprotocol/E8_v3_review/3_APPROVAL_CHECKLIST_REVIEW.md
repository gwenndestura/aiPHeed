# Approval Checklist Review

**Status: review only, 2026-10-12. Nothing was approved or executed.** Item IDs follow `E8_v3/5_APPROVAL_CHECKLIST.md`; "§" references point to that file or to the consistency review (`1_E8_V3_CONSISTENCY_REVIEW.md`, IDs such as C1 and L1).

**Column meanings:**

| Column | Meaning |
|---|---|
| **Reversible?** | Can the action be undone without lasting effect? Seeing protected data, or freezing a forecast that is then compared with outcomes, cannot be undone in information terms. |
| **Needed: software** | Needed to finish a working, tested backend and frontend |
| **Needed: thesis evaluation** | Needed for a blind-quarter evaluation section |
| **Postpone?** | Can it wait without blocking documentation or software-quality work? |

## 1. Item-by-item review

| ID | Exact action authorized | Files or data it could access or modify | Prerequisites | Reversible? | Needed: software | Needed: thesis evaluation | Postpone? |
|---|---|---|---|---|---|---|---|
| **A1** Protocol approval | Designate the v3 protocol as the plan of record. No code, data access or execution. | None. (Recommended: also record its SHA-256 at approval; review S1.) | The decisions in review §4 (C1, L1, O1–O3, G1) should be settled first, probably as a v4 text | Yes before A8. After A8, changing it is a recorded deviation. | No | **Yes** | **Yes.** Docs and software work do not depend on it. Exposure risk grows with time, so do not postpone indefinitely. |
| **A2** Access controls X1–X4 | Write allowlist loader, deny-list guard, hash-only utility and post-run comparison code, plus unit tests on synthetic fixtures, in `aipheed-backend-aligned/` | Creates new code and test files in the isolated backend. Hashes deny-listed files (bytes only). | A1 | Yes (new files only) | No. But the guard is **also useful for regression testing** (stage 7). | **Yes** | Yes for docs. Stage 7 benefits if A2 comes first (see §3). |
| **A3a** Provincial CPI release dates, 2021-01 to 2026-06 | (i) You look up the dates and give only dates; or (ii) Claude reads archived snapshots captured before 2026-08-01, dates only | Web pages that can also show July–December 2026 CPI (P2) | A1 | **No** if a protected value is seen | No | No. The default "unverified" is acceptable with labelling. | **Yes.** **Recommended: defer until after A9-Q3/Q4.** Once outcomes are collected the exposure risk is gone, and the validity label can be upgraded retroactively. |
| **A3b** 2023 poverty release date | Same routes; date only | PSA poverty pages (not protected) | A1 | Yes (not protected) | No | No (affects A2/A3 validity labels only) | Yes |
| **A3c** June 2026 SWS publication date | Same routes; snapshots before 2026-09-01 only | SWS pages and news that can show the September 2026 round (P1) | A1 | **No** if a protected value is seen | No | No. The default "unknown, excluded" is acceptable. | Yes. **Recommended: leave unknown.** Verifying it after the C4 forecast is frozen cannot change that forecast. |
| **A4** Gross-failure margins | Apply the three margins in the evaluation report | None | A1. Also resolve O2 (probabilities for stress-type baselines), O1/G2 (ties) and G1 (single-quarter fallback) first. | Yes until A9. After outcomes are seen, the margins must not change. | No | Needed **only** if gross failure is to be assessed | Yes, until A8 |
| **A5** Allowlist-only frame | Write the frame code and its input manifest (path + SHA-256) in the isolated backend. Build the frame from allowlisted files only. | **Reads:** aligned `labels.parquet`, `psa_indicators.parquet`, `features_fused.parquet` (all previously documented to end at 2025-Q4), the 2026-H1 collection (exposed), SWS code registry, release-date CSVs. **Writes:** new code, manifest, tests. | A1, A2. Decide C4 (`food_cpi` level has no allowlisted 2026 source). | Yes (new files only) | No | **Yes** | Yes for docs |
| **A5-rice** | (i) Exclude rice everywhere (default); or (ii) fix the 3 forward-filled cells, unit-tested | Aligned `psa_indicators.parquet` (allowlisted); new code | A5 | Yes | No | No | Yes |
| **A5-GN** | (i) Drop national series from A3 (default); or (ii) column-projected, row-filtered read (≤ 2026-Q2) of named columns from named source files | (ii): source tables with **unknown coverage**, which may hold CPI-related columns | A5 | (i) yes; (ii) **no** if a protected value were materialized | No | No | Yes |
| **A6** 2026-Q1 label | Build the 2026-Q1 Equation 3 label from exposed data; add it to training and `last_published_stress` | Exposed March 2026 SWS and January–March 2026 provincial CPI (from the 2026-H1 collection) | A1, A5 | Yes before A8 | No | No (default "exclude" is valid) | Yes, until A8 |
| **A7 (7a)** Scheduled-task safeguard | Disable `aipheed` and `aipheed-auditing`; stop sessions `local_f3c4b65e…` and `local_918f3167…` without reading their transcripts | Task configuration only; no data | None | Disable: **yes**. Stop: **partly** (in-progress runs end). | No | Indirectly: it protects the blind quarters | **This is the time-sensitive item.** Postponing does not block docs or software work, but leaves risks R1–R5 open (brief §4). Your decision. |
| **A7 (7b)** | Change both prompts; add deny rules | Task prompts; `.claude/settings.local.json` (persistent) | None | Yes | No | Indirectly | Same as 7a |
| **A7 (7c)** | Keep `SCHEDULER_ENABLED=false`; do not start the production backend or run the pipeline | None (already in place) | None | — | **Interacts with stage 7.** Production backend regression tests or a manual start would need care (see §3). | Indirectly | No action needed |
| **A7-X6** | Add deny rules for protected paths, `WebSearch`, `WebFetch` | `.claude/settings.local.json` (persistent; also affects your own sessions) | None | Yes | No. It may obstruct legitimate work (e.g. web lookups for documentation). | Indirectly | Yes. It overlaps 7b(ii); review S4. |
| **A8** Generate and freeze forecasts | Record protocol and code hashes. Run the A5 frame under the A2 guard twice. Fit A1–A4 on 2021-Q2 to 2025-Q4 labels. Forecast 2026-Q3 (C3) and 2026-Q4 (C4). Check determinism. Write forecasts and manifest, set read-only. Compare deny-list hashes before and after. | **Reads:** allowlisted inputs. **Writes:** a new run folder under `experiments/`. | A1, A2, A5 and its sub-choices; **decisions** recorded on A4, A6, A7 (review S2) | **No in substance.** The files can be deleted, but a second generation would be a recorded protocol deviation. | No | **Yes** | Yes for docs and software. Exposure risk grows the longer it waits. |
| **A9-Q3** Collect the 2026-Q3 outcome | Collect from primary sources: SWS round(s) with fieldwork July–September 2026, and July–September 2026 provincial food CPI YoY. Compute stress, d, event and ranking. Score the frozen forecasts. | **P1 and P2 for 2026-Q3** (web or PSA/SWS sources). Writes new outcome and score files. | A8 complete; freeze hashes re-verified immediately before | **No** (protected data becomes known) | No | **Yes** | Yes, until the releases exist. **Their dates were not looked up.** |
| **A9-Q4** Collect the 2026-Q4 outcome | Same for October–December 2026 | **P1 and P2 for 2026-Q4** | A8 complete | **No** | No | Yes, for two-quarter conclusions. **Expected only in 2027** (review G1). | Necessarily postponed |
| **A10** Served-model decision | Any change to the isolated backend's served model | `data/revised/*` served artifacts, assessment service configuration | E8 report. Resolve S6 (which system the thesis documents). | Yes (earlier artifacts preserved) | Only if a change is wanted. **M6 stays served by default.** | No | Yes |
| **A11** Descriptive check on exposed quarters | Build 2026-Q1/Q2 labels and score arms on exposed quarters, descriptive only | Exposed SWS and CPI; new files | A8. Its design must be fixed first (review L2). | Yes | No | No | Yes |
| **A12** Read a carrier file | A specific key-filtered read, named in advance | Carrier contents | — | **No** | No | No | **Recommended: never** |

## 2. What can be postponed without blocking documentation and software-quality work

**All E8 items, A1–A6 and A8–A12, can be postponed** without blocking documentation, code review or the isolated-backend test suite. None of that work needs E8 approvals.

Two caveats:

1. **A7 is time-sensitive in a different sense.** Postponing it blocks nothing, but it is the only item whose delay *increases* risk: the next runs are on 2026-10-13.
2. **Delaying A8 increases the window for accidental exposure.** Historical simulations are timeless in principle, but every day before the forecast freeze is another day in which a blind outcome could be seen in a transcript, a news item or a web search. Once forecasts are frozen, later exposure no longer contaminates them.

## 3. Gaps: actions on the roadmap that no current approval item covers

These are not in `5_APPROVAL_CHECKLIST.md`. They would need their own approvals (proposed IDs B1–B8):

| Proposed ID | Action | Why it needs approval | Data risk |
|---|---|---|---|
| B1 | Run the **isolated-backend** test suite (`aipheed-backend-aligned/tests`, 23 test files) | It is execution. **Code check in this review:** `test_devprotocol_rule_l`, `test_e2_relative_cpi` and `test_exploratory_runner` call `development_frame()`; `test_improvement_corrections` calls `corrected_features()` / `corrected_frame()` and iterates frame `sws_hunger` values. These paths load the aligned **`sws_hunger.parquet` and `corpus_geocoded.parquet` (carriers)** into memory. A failing assertion could print values. | **Medium.** The earlier full run (288 passed, 2026-10-12) already loaded these files, and nothing was printed on pass. Before re-running: deselect those four files, run them under the A2 guard, or first confirm the carriers hold no 2026-H2 rows (which would itself be content access, A12). |
| B2 | Run the **production backend** test suite (7 test files) | Execution in production | **Not fully assessed.** Code check: `test_api_admin` uses a temporary database (`tmp_path`); `test_quarterly_pipeline` references production data paths (whether it reads them was not traced). `backend/tests/conftest.py` imports `app.main`. `app/main.py` itself has no direct model or parquet load (grep), but the modules it imports were not traced. The memory index records 6/102 failing as of 2026-10-07 (not re-verified). Run only under the A2 guard or after tracing every data access. |
| B3 | Run frontend type-check, lint, build and tests | Execution. It reads source only, unless tests hit a live API. | Low. **The API must not be served from the production backend** with protected rows exposed. |
| B4 | Fix failing tests or code in **production `backend/` or the frontend** | Modifies production, which is currently prohibited | Depends on the change |
| B5 | Calibration decision (keep "uncalibrated", or calibrate on training-only folds) | Changes served probabilities or labels | No evaluation-quarter data may be used |
| B6 | Dashboard rescoring (if B5 or A10 changes outputs) | Changes served outputs. Rescoring is prohibited until approved. | None beyond its inputs |
| B7 | Thesis-text changes (Chapter 3/4 methods and results) | Your document, your decision | None |
| B8 | Commit, push, merge or deploy | Prohibited until approved. The protected-row files are **already** on the remote (review P9), which itself deserves a decision. | Publishing |

## 4. Corrections to the approval checklist (to make in a later revision, not now)

1. **A8 prerequisites:** say "decision recorded" for A4, A6 and A7, and say whether A8 is allowed while the tasks remain enabled (review S2).
2. **A1:** add "record the protocol's SHA-256 at approval" (review S1).
3. **A3a/A3c:** add the option "defer until after A9", which removes the exposure risk.
4. **A9-Q4:** define the round by fieldwork window, not "December" (review L4). Add the single-quarter fallback (G1).
5. **A11:** define the origins, or limit it to 2026-Q1/Q2 (L2).
6. **A7:** state that stopping sessions is only partly reversible (T1). Merge A7-X6 with 7b(ii) (S4).
7. **Add B1–B8** above, or record that they are out of E8's scope and governed separately.

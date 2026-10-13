# E8 v3: Approval Checklist

**Status: DRAFT, 2026-10-12. No item below is approved. No item has been executed.**

**How approval works:**

- Each item is a separate approval. Approving one authorizes **only the exact action in its row**.
- **Protocol approval (A1), forecast generation and freezing (A8) and outcome collection (A9) are distinct approvals.** A9 is also split by quarter.
- Where an item has a default, the default applies only when you choose it. Nothing is assumed approved by silence.

| ID | Decision | Exact action it authorizes | Data it could touch | Separate approval? | Prerequisites | If not approved |
|---|---|---|---|---|---|---|
| **A1** | Approve the E8 v3 protocol text (`1_E8_PREREGISTRATION_DRAFT_v3.md`) as the governing plan | Marks v3 as the plan of record. **Authorizes no code, data access or execution.** | None | Yes | — | v3 stays a draft; nothing proceeds |
| **A2** | Build the access controls X1–X4 (checklist 3, §3) | Write allowlist-loader, deny-list-guard, hash-only and post-run-comparison code, with unit tests on **synthetic fixtures**, in `aipheed-backend-aligned/` only | Hashes of deny-listed files (bytes, not content). No data rows. | Yes | A1 | No E8 execution is possible (A8 requires A2) |
| **A3a** | Verify RSSO IV-A provincial food CPI release dates, 2021-01 to 2026-06 | Choose **one**: (i) you look up the dates yourself and give me only the dates; (ii) Claude reads **archived snapshots captured before 2026-08-01** of RSSO IV-A or PSA release pages and records **dates only** | Web pages that may also list July–December 2026 CPI (**P2**). Option (ii) limits this to snapshots that predate those releases. | Yes, per option | A1 | **Default: unverified.** All model-arm results stay "proxy-dated (unverified)". |
| **A3b** | Verify the 2023 provincial poverty release date (A2/A3 input) | Same choice of routes; date only | PSA poverty release pages (not protected) | Yes | A1 | Poverty stays unverified; affects A2/A3 only |
| **A3c** | Establish the June 2026 SWS round's publication date | Same routes, snapshots captured **before 2026-09-01** only | SWS pages and news, which may show the **September 2026 round (P1)** | Yes | A1 | **Recommended default: leave unknown.** The June round stays excluded; the C4 SWS input stays the March round (age 3, at the staleness limit). |
| **A4** | Accept the gross-failure margins (protocol §8.1): Brier +0.10 vs B1; regional error +6.0 points vs B4; ≤ 3/10 concordant pairs | Apply these criteria in the evaluation report | None | Yes | A1 | Gross failure is **not assessed**; only per-quarter values are reported |
| **A5** | Build the **allowlist-only E8 input frame** | Write the frame code and its input manifest (path + SHA-256) in `aipheed-backend-aligned/`. The manifest lists: aligned `labels.parquet`, `psa_indicators.parquet`, `features_fused.parquet`; `data/supplementary/collection_2026-10-09/*` (2026-H1 CPI, SWS 2025 rounds); the SWS code registry; the CPI release-date evidence CSVs. **Excluded:** `cpi_full.parquet`, `sws_hunger.parquet`, news and corpus files, and every production file. | Allowlisted files only, with hashes verified before reading | Yes | A1, A2 | E8 cannot run; the existing development frame is **not** an acceptable substitute (checklist 2, C7) |
| **A5-rice** | Rice price | Choose: (i) **exclude rice from every arm (default)**; or (ii) fix the 3 residual forward-filled cells (code change, unit-tested) and allow rice in A3's pool | Aligned `psa_indicators.parquet` (allowlisted) | Yes | A5 | Rice excluded |
| **A5-GN** | National and regional series for A3 (2026-Q1/Q2 values are not in the allowlist-candidate files, which end at 2025-Q4) | Choose: (i) **drop GN from A3's selection pool (default)**; or (ii) a column-projected, row-filtered read (quarters ≤ 2026-Q2) of the named GN columns, with each source file named in the manifest **before** any read | (ii): source tables with unknown coverage, possibly including CPI-related columns. Projection by name keeps other columns unread. | Yes | A5 | A3 = selection over core + provincial government only |
| **A6** | Use the 2026-Q1 label (exposed, not protected) | Build the 2026-Q1 Equation 3 label from the exposed March 2026 SWS round and January–March 2026 provincial CPI. Add it to training and `last_published_stress` at C3 and C4. | Exposed 2026-Q1 SWS and CPI values | Yes | A1, A5 | **Default: excluded** (H5); `last_published_stress` = 2025-Q4 at both cutoffs |
| **A7** | Scheduled-task safeguard (checklist 4, §5) | Choose: **7a (recommended)**: disable `aipheed` and `aipheed-auditing` (`update_scheduled_task enabled=false`) and stop sessions `local_f3c4b65e…` and `local_918f3167…` without reading their transcripts; **7b**: change both prompts and add the project deny rules X6; **7c**: keep the production APScheduler disabled (already in place; no change) | Task configuration and, for 7b, `.claude/settings.local.json`. No data. | Yes; **7a and 7b separately** | — | Tasks keep running daily; the next runs are 2026-10-13 09:02 and 15:02 local. **Risks R1–R5 stay open and are not accepted by this document.** |
| **A7-X6** | Project permission deny rules as defence in depth, independent of 7a/7b | Add `deny` entries for protected paths, `WebSearch` and `WebFetch` to `.claude/settings.local.json` for the blind period | Persistent configuration (also affects your own sessions in this project) | Yes | — | No deny rules |
| **A8** | **Generate and freeze the blind forecasts** | (1) Record the SHA-256 of the approved protocol files and the E8 code. (2) Run the frame (A5) under the guard (A2) twice, fitting A1–A4 on labels 2021-Q2 to 2025-Q4 and forecasting **2026-Q3 (C3) and 2026-Q4 (C4)**. (3) Check that the two runs are identical. (4) Write forecasts and a manifest, set them read-only, and compare the deny-list hashes before and after. **No outcome or 2026 label is read or built.** | Allowlisted inputs only | Yes; **distinct from A1 and A9** | A1, A2, A4 (or its rejection), A5 with its sub-choices, A6, A7 | No forecasts exist; E8 cannot be evaluated |
| **A9-Q3** | **Collect the 2026-Q3 outcome** | Collect, from primary sources: the SWS round(s) with fieldwork July–September 2026 (Balance Luzon hunger), and July–September 2026 provincial food CPI YoY for the five provinces. Compute Q3 stress, d, the event at τ = 14.345 and the ranking. Score the frozen forecasts. **Production P3 files are not used as the outcome source.** | **P1 and P2 for 2026-Q3** | Yes; **per quarter** | A8 complete, with the freeze hashes re-verified immediately before | Q3 stays blind |
| **A9-Q4** | **Collect the 2026-Q4 outcome** | Same for October–December 2026. Available only after the December 2026 CPI and SWS releases, expected in 2027. **The target quarter stays inside the 2021–2026 window.** | **P1 and P2 for 2026-Q4** | Yes | A8 complete; A9-Q3 is not required | Q4 stays blind |
| **A10** | Served-model decision | Any change to the served model in the isolated backend (M6 → A1 or another arm), based only on the protocol §8 conclusions | Served artifacts | Yes | E8 report | **M6 stays served.** Core stays a provisional, unvalidated alternative. |
| **A11** | Optional descriptive check on exposed quarters (2025-Q2, 2025-Q3, 2026-Q1, 2026-Q2) | Build their labels and score the arms on them, reported as **descriptive only**, never as evidence | Exposed (not protected) SWS and CPI values | Yes | A8 | Not done |
| **A12** | Any read of a potential-carrier file (e.g. aligned `cpi_full.parquet`) | A specific key-filtered read, named in advance | A carrier's contents | Yes, per file | — | **Default and recommendation: none.** E8 does not need any carrier. |

## Standing rules that need no approval and that no approval above relaxes

- LightGBM is the primary model family.
- The threshold is fixed at 0.50; probabilities are reported as uncalibrated.
- INSUFFICIENT_DATA applies when a required input is missing or stale.
- Missing values stay NaN, never zero.
- No threshold or score is tuned to a HIGH/LOW distribution.
- The study window is 2021–2026.
- There are no commits, pushes, merges or deployments.
- Production `backend/`, the frontend, served models, existing forecasts and earlier artifacts are not modified.
- Equation 3 stress is not presented as validated food insecurity.
- No claim of 75% accuracy or of adviser approval.

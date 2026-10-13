# E8 v3 Consistency Review

**Status: review only, 2026-10-12. The six E8 v3 documents were not edited.** Their hashes are unchanged (see `5_INTEGRITY_REPORT.md`). E8 v1 and v2 are unchanged.

**Documents reviewed (folder `E8_v3/`):**

| Short name | File |
|---|---|
| **P** | `1_E8_PREREGISTRATION_DRAFT_v3.md` |
| **L** | `2_HISTORICAL_SIMULATION_AND_LEAKAGE_CHECKLIST.md` |
| **D** | `3_PROTECTED_DATA_ACCESS_CHECKLIST.md` |
| **S** | `4_SCHEDULED_TASK_REVIEW.md` |
| **A** | `5_APPROVAL_CHECKLIST.md` |
| **I** | `6_INTEGRITY_VERIFICATION_REPORT.md` |

**Evidence codes used below:**

| Code | Meaning |
|---|---|
| **V** | Verified in this review with a permitted operation: reading code, reading this project's own records, git metadata, file metadata, hashes, or column headers and sample-size fields of *exposed* (not protected) 2025/2026-H1 files |
| **T** | Comparison of document text only |
| **R** | Rests on earlier session records or the memory index; **not re-verified** |

No protected or potential-carrier file was opened. No transcript was read.

---

## 1. Agreement summary

| Topic | Verdict | Main issues |
|---|---|---|
| Historical-simulation dates and permitted inputs | **Conflict** | C1 (H1 vs H2–H4), C2 (H8 false), C4 (`food_cpi` level has no allowlisted 2026 source), C5 (rice) |
| Protected-data boundaries | **Partly consistent** | P1 (overclaim: "no forecast exists"), P2 (HEAD-equality preamble overclaims), P5 (`list_task_runs` summaries), P9 (protected-row files already on the remote), P11 (the test suite loads carriers) |
| Training-label availability and date evidence | **Partly consistent** | L1 (τ statistic undefined; served M6 uses a different τ), L2 (A11 on training quarters), L5 (sample sizes are recorded) |
| Overall stress forecasting vs provincial ranking | **Consistent in principle, under-specified** | O1 (ranking score source), O2 (B1/B3/B4 have no probabilities for Brier), O3 (INSUFFICIENT rows) |
| Evaluation limits and gross-failure criteria | **Consistent, with a timing gap** | G1 (both-quarter rule vs 2026-Q4 outcome expected in 2027), G2 (ties vs the 29/120 null) |
| Separate approvals: protocol, forecast freeze, outcome collection | **Consistent on separation, gaps in sequencing** | S1 (no protocol hash at A1), S2 (A8 prerequisites), S3 (A3 ordering), S6 (which system the thesis documents) |

---

## 2. Discrepancies

**Severity:**

- **High:** blocks a correct execution, or makes a claim that is false.
- **Medium:** an ambiguity or contradiction that must be resolved before A8.
- **Low:** wording or completeness.

### 2.1 Historical-simulation dates and permitted inputs

| ID | Sev. | Where | Finding | Ev. |
|---|---|---|---|---|
| **C1** | **High** | P §3 intro and H1 vs P H2, H3, H4; L "Status terms", §A, §F | **The availability rule contradicts itself.** P §3 says only information "**demonstrably** available" is used, and H1 says a value is usable "only if its publication date is documented". But H2–H4 and L §A plan to *use* proxy-dated and schedule-dated inputs, flagged "unverified". Read literally, H1 removes every provincial-CPI input, every training label except possibly 2024-Q4, all national-series inputs and poverty, so no model arm could be trained. Your instruction (mark unverified, exclude from leakage-safe claims) matches H2–H4, not H1. | T |
| **C2** | **High** | P H8; L §D row 1 | **H8 is factually wrong.** It says design choices were fixed "before any 2026-Q3/Q4 outcome existed or was seen". In fact: (a) the design was fixed on 2026-10-11/12, after 2026-Q3 ended; (b) July–August 2026 CPI had already been released and may sit in carrier files; (c) P §4 itself discloses that a `label_cpi` aggregate including 2026-Q3 rows was printed on 2026-10-11. L §D row 1 says Q3/Q4 outcomes "did not exist in any file used by this session". That cannot be verified: E1–E7 loaded the aligned `sws_hunger.parquet` (a carrier per D §2.2) through the development frame (L §C7). | T, V (frame lineage in code) |
| C3 | Medium | P H4 vs L §A | P H4 gives the margin range as "71–162 days". L §A lists 71, 72, 162 and 254 days, plus about 22 months for poverty. | T |
| **C4** | Medium | P §2 (A2 inputs); L §A row A4; A, A5 | **No allowlisted 2026 source for the A2 input `food_cpi` (index level).** The 2026-H1 collection file has only `food_cpi_yoy_pct_raw` (column header checked), and the other allowlist candidates end at 2025-Q4. `food_cpi` for the 2026-Q1 and 2026-Q2 input rows would therefore be NaN at both cutoffs. No document addresses this. | V (header only) |
| **C5** | Medium | L §A row A8 vs L §C3, A (A5-rice), P §2 (A3) | L §A row A8 labels rice "excluded from A2; **available to A3**". Its own status column says "Excluded", and L §C3, A5-rice (default: exclude from every arm) and P §2 (A3 only under A5-rice option ii) all say rice is excluded unless approved. | T |
| C6 | Low | L §A row A7 vs A (A5-GN) | L §A row A7 presents 2026-Q1/Q2 national-series values as A3 inputs. A5-GN says those values are not in the allowlist-candidate files and that the default drops national series. L does not state the condition. | T |
| C7 | Low | P H4 vs L §F | L §F omits A4 (descriptive) and B5 (no inputs). P H4 says "every arm except B4". | T |
| C8 | Low | P H6 vs L §A row A1 | The C4 SWS input is 3 quarters old, exactly at the staleness limit. This is disclosed only in L and A (A3c), not in P. The code treats only age > 3 as stale (`revised_trainer.insufficiency`: `age > R.SWS_MAX_AGE_QUARTERS`), so L is correct. | V |
| C9 | Low | P §1, H5; L B1 | "16 labelled quarters" out of the 19 calendar quarters 2021-Q2 to 2025-Q4. The three missing quarters are not named in any document. | T |

### 2.2 Protected-data boundaries

| ID | Sev. | Where | Finding | Ev. |
|---|---|---|---|---|
| **P1** | Medium | L §E row E1 | **Overclaim:** "No forecast exists for 2026-Q3/Q4." What was checked: the isolated served artifacts (latest target 2025-Q4; I row 16). The 2026-10-09 frozen files rest on earlier records (I row 17). Production `final_predictions.parquet`, the production model (trained on a panel documented through 2026-Q3) and other P4 carriers were not, and must not be, inspected. I row 17 is properly hedged; L E1 is not. | T |
| **P2** | Medium | D §2.1 preamble; I row 8 | D says "All tracked files below have a working copy equal to the git HEAD blob, checked 2026-10-12". At the time only 16 files were checked, and I row 8 points to "the list in checklist 3, §2.1", which is longer. The seven JSON result files were not checked, and `mlflow.db` is listed under the preamble but is untracked. **Resolved in this review:** all seven JSON files are tracked and equal to the index; `mlflow.db` is untracked and git-ignored. | V |
| P3 | Low | D §2.1 (`label_distribution.json`) | The last-commit column shows "—". The actual last commit is e0f9eb2, 2026-09-06. | V |
| P4 | Low | D §2.3 vs L §E9 | D says "18 .docx, 2 .html, 1 folder"; L says "42 files". The current count is **42 files**: 20 .docx, 2 .html, 6 .png, 6 .svg, 6 .py, 1 .js, 1 .sh. D counted top-level entries only. | V |
| **P5** | Medium | D §1 (prohibited operations); S "Sources" | **Gap.** S lists `list_task_runs` as a source. That tool can return a one-line summary written inside each run, which is transcript-derived and so a potential carrier. No summary field was returned on 2026-10-12, but D §1 neither prohibits nor restricts the tool. **This review did not call `list_task_runs`.** | T |
| P6 | Low | D §2.1 ("no info after X") | The bound used the git *author* date. A content bound should use the *committer* date. **Checked in this review:** the two dates are identical for every listed file, so the conclusions stand. | V |
| P7 | Medium | D §2.4; S §3, R6 | Both say the production scheduler runs "only inside a started backend" and rate R6 low "while … the stopped backend hold". **v3 never checked whether a backend was running.** **Checked in this review (18:26 local):** no `python`, `uvicorn` or pipeline process was running. This holds only at that moment. | V |
| P8 | Low | P §4 P3 vs D §2.1 | P defines P3 as files "known to contain P1/P2 rows". D's own note on `psa_indicators.parquet` says its 2026-Q3/Q4 rows are "partial or placeholder of unknown provenance". Both files are protected either way, so the practical effect is nil, but the wording overstates what is known. | T |
| **P9** | Medium | D, S R4 (missing) | **Not mentioned anywhere:** the commit holding the protected-row files (eee269b: `psa_indicators.parquet`, `panel.parquet`, the production model) is already on the remote (`refs/remotes/origin/backend+frontend` = eee269b, fetched 2026-10-06). S R4 says "the files are already tracked", which understates this: they are already pushed. Commands such as `git show origin/backend+frontend:<path>` are content access and belong on D §1's prohibited list. | V (git refs) |
| **P11** | Medium | D §3 (X1/X2 scope), L §C7, A (no test item) | **The test suite is a carrier path that no document covers.** D's controls cover only "the E8 process". In the isolated backend, four test files (`test_devprotocol_rule_l`, `test_e2_relative_cpi`, `test_exploratory_runner`, `test_improvement_corrections`) build the development frame, which loads the aligned `sws_hunger.parquet` and `corpus_geocoded.parquet` (carriers) into memory. `test_improvement_corrections` iterates frame `sws_hunger` values, and a failing assertion could print them. The earlier full run (288 passed, 2026-10-12) already did this without printing. | V (code grep) |
| P10 | Low | I §5 | I says "No configuration was changed". After I was written, a memory note (`memory/e8_v3_blind_boundary.md`) and a `MEMORY.md` index line were added. They are outside the project and not system configuration, but I does not disclose them. | T (this session's own action) |

### 2.3 Training-label availability and publication-date evidence

| ID | Sev. | Where | Finding | Ev. |
|---|---|---|---|---|
| **L1** | Medium | P §1, §2 (A4), §9; L B4; A (A4, A8) | **The τ definition is incomplete, and the served model uses a different τ.** (a) No document states that τ is the **median** stress of the labels published before the as-of date (`risk_score_v2.reference_threshold`). (b) The served M6 artifacts use **τ = 10.843 (as of 2023-10-01)** (served meta `tau`, `tau_as_of`), while E8 scores the event at **τ = 14.345**. P §2 defines A4 as "M6 as served (served configuration)", so A4's event definition does not match E8's outcome unless A4 is refitted at 14.345. Undecided. (c) The E6 manifest tags 14.345 as "leakage-affected" for retrospective scoring. That does not apply to the blind quarters, but no document explains the tag. | V (code and meta) |
| L2 | Medium | P §5 vs A (A11) | 2025-Q2 and 2025-Q3 are both "exposed, descriptive only" (P §5) and **training labels** for the C3 and C4 models (P H5). A11 ("build their labels and score the arms") is undefined for them: scoring the C3/C4 models on their own training quarters is in-sample, and their labels already exist. A11 needs separate walk-forward origins or must be limited to 2026-Q1/Q2. | T |
| L3 | Low | L B2 | "SWS dates are verified or verified-single for the rounds used" was not re-verified in this review. By construction, the registry returns no label when an SWS date is unknown (`label_published` returns "unknown SWS date"). | V (code), R (dates) |
| L4 | Low | A (A9-Q4) | A9-Q4 assumes a "December 2026" SWS round. P1 is defined by fieldwork window (2026-10-01 to 12-31), and the 2025-Q4 round was a *November* round. | T |
| **L5** | Medium | P §8.1 (regressor margin) | P says Balance-Luzon sample sizes are "not verified here". The existing exposed file `sws_balance_luzon_2025_raw.csv` records them for the 2025 rounds: April 2025 has 600 Balance-Luzon respondents (±4%); June 2025 is 1,200 nationwide (±6%); September 2025 is 1,500 nationwide (±4%). That supports the 6.0-point margin, which equals the ±6% rounds. Sample sizes for the blind-quarter rounds are unknown (protected period). | V (sample fields only; no hunger values read) |

### 2.4 Overall stress forecasting vs provincial food-price ranking

| ID | Sev. | Where | Finding | Ev. |
|---|---|---|---|---|
| **O1** | Medium | P §7.2, §8.1 (ranking) | **The ranking score source is not specified.** It could be the classifier probability or the regressor's predicted stress. Shallow trees (`num_leaves=4`) can give tied probabilities. Ties count ½, but the 29/120 null in §8.1 assumes untied orderings. | T |
| **O2** | Medium | P §2, §7.1, §8.1 (overall, classifier) | **B1, B3 and B4 output stress values, not probabilities**, yet the classifier criterion compares Brier against B1. No conversion is defined (for example, 1 if stress > τ, else 0). | T |
| O3 | Low | P §7.1 | How INSUFFICIENT_DATA rows enter the five-province mean Brier is unspecified: excluded, or scored. | T |
| O4 | Low | P §7.1 | "SWS_T accounts for about 65% of historical stress variance" rests on an earlier analysis. | R |

Separating the two questions is consistent across P §7, P §8.3, L and A. **No document combines them.** (T)

### 2.5 Evaluation limits and gross-failure criteria

| ID | Sev. | Where | Finding | Ev. |
|---|---|---|---|---|
| **G1** | Medium | P §8.1 vs A (A9-Q4) | **Timing gap.** Gross failure requires the condition in **both** blind quarters. A9-Q4 says the 2026-Q4 outcome is expected only in 2027. P has no fallback if the thesis must be finalized with one blind quarter. The release dates of the September 2026 SWS round and of September 2026 provincial CPI are also unknown, and were deliberately not looked up. | T |
| G2 | Low | P §8.1 (ranking) | The null probability 29/120 assumes no ties and independence between the two quarters. | T |
| — | — | P §8.2, §8.3; A | Consistent: added value is "not demonstrated" with fewer than 8 blind quarters; no superiority or significance claims; the exposed 2025 quarters are descriptive only. | T |
| — | — | P §8.1; A (A4) | Consistent: gross-failure margins apply only if A4 approves them; otherwise gross failure is not assessed. | T |

### 2.6 Separate approval requirements

| ID | Sev. | Where | Finding | Ev. |
|---|---|---|---|---|
| — | — | A header, A1, A8, A9-Q3, A9-Q4 | Consistent: protocol approval (A1), forecast generation and freeze (A8) and outcome collection (A9, per quarter) are separate approvals. | T |
| **S1** | Medium | P §10 step 4 vs A (A1) | The protocol hash is recorded only at A8. Between A1 and A8 the approved text could change with no frozen record. A protocol hash at A1 would close this gap. A8 also bundles **generation** with **freezing**. That is defensible, because forecasts are never inspected before the freeze, but it is a design choice you should confirm. | T |
| **S2** | Medium | A (A8 prerequisites) vs A (A7 "if not approved"), P §10 | A8 lists A7 as a prerequisite, but it is unclear whether A8 needs 7a specifically, any A7 option, or only a recorded decision. A4 and A6 have defaults, so they need a recorded *decision*, not an *approval*. The wording mixes the two. | T |
| S3 | Low | P §10 step 2 vs A (A8) | P §10 groups A2–A6 (including A3, date verification) before generation. A8's prerequisites omit A3, since its default "unverified" is acceptable. | T |
| S4 | Low | A (A7 option 7b(ii) vs A7-X6) | Two approval routes exist for the same configuration change (deny rules). | T |
| S5 | Low | P §9 vs A (A10) | P says "M6 remains the served model … **through and after** E8", while A10 allows a switch after E8. | T |
| **S6** | Medium | P §9; A (A10); all documents | **Scope of "served model".** P and A refer to M6 served by the *isolated* backend. The memory index records that the thesis documents the **production `backend/`** (your choice on 2026-10-09). Production serves a different model (`thesis_food_insecurity_model.joblib`) with a different label (`label_cpi`). No document says how E8 results relate to the system the thesis describes. | R |

### 2.7 Scheduled-task review, internal

| ID | Sev. | Where | Finding | Ev. |
|---|---|---|---|---|
| T1 | Medium | S §5 (7a "Reversible: Yes") | Disabling is reversible. **Stopping** the two sessions ends their in-progress runs and discards any pending prompt. Whether a stopped session can be resumed was not verified. 7a is only partly reversible. | T |
| T2 | Low | S §1 ("Next run 09:02 local") | Run metadata seen on 2026-10-12: the last five `aipheed` runs started at 12:44, 16:10, 16:41, 18:16 and 20:44 local, none at 09:00. Four of the five `aipheed-auditing` runs started in the same second as an `aipheed` run; one, on 10-09, started on schedule at 15:02. This is consistent with missed runs being launched as catch-ups when the app opens, so a run may start whenever the app is next open after the scheduled time. This is an inference from metadata. | V (metadata seen 2026-10-12), inference |
| T3 | Low | S §2 | S assumes the scheduled sessions apply the project's `.claude/settings.local.json`. That is expected for sessions in that folder but was not observed. Their permission mode is unknown. | T |
| T4 | Low | S §1 ("unchanged since May 2026") | Based on mtime only. Hashes are now recorded in the brief. | V |

### 2.8 Integrity report

| ID | Sev. | Where | Finding | Ev. |
|---|---|---|---|---|
| I1 | Low | I §3 (supplementary collection "not via its own manifest") | **Resolved in this review:** all 6 files match `COLLECTION_MANIFEST.json`. | V |
| I2 | Low | I §5 | See P10 (memory note not disclosed). | T |

---

## 3. Items checked and found consistent

| Item | Ev. |
|---|---|
| Event rule "stress > τ" is strict (`risk_score_v2.classify`: HIGH if `v > threshold`) | V |
| Probability cutoff 0.50; HIGH ≥ 0.50 (`PROBABILITY_CUTOFF`, `classify_probability`), as stated in P §9 and A | V |
| Monotone +1 on `sws_hunger` and `last_published_stress` (`revised_trainer.MONOTONE = [1, 1, 0, …]`; `datadriven_trainer` `MONOTONE_UP`) | V |
| Training-only filter (more than 50% missing or constant) is implemented in the M6 trainer (`datadriven_trainer`, lines 14 and 60–64). A1/A2 code for E8 is not written yet. | V |
| M6 group selection uses inner log loss; the regressor reuses the selected groups (`select_groups`, `regress_quarter`) | V |
| The protected SWS quarters are asserted absent in the registry (`PROTECTED = {"2026-Q3", "2026-Q4"}`; `SWS_COVERAGE_END = (2026, 2)`) | V |
| The current frame path does not call the only `cpi_full` reader on the supplementary path (`generalization_study.data_audit`). The other `cpi_full` references are in fetch, refresh and feature-matrix code. | V (call graph partially traced) |
| Proxy-date rule: provincial date = national + 14 days (`PROXY_DAYS = 14`); 2018-base rebase date 2022-02-04 | V |
| Reused quarters in P §5 match the E5 configuration (`test_quarters`: 2023-Q4 to 2025-Q1, plus 2025-Q4) | V |

## 4. Unresolved assumptions to settle before A8

1. Whether H1 adopts the flag-and-use rule (C1).
2. The A4 event threshold: refit at 14.345, or descriptive at 10.843 (L1).
3. The source for `food_cpi` (index level) in 2026-H1 inputs, or dropping it from A2 (C4).
4. Probability conversion for the stress-type baselines (O2), and the ranking score source (O1).
5. The handling of INSUFFICIENT_DATA rows in Brier (O3).
6. The single-quarter fallback for gross failure, and the thesis deadline relative to the 2026-Q4 outcome (G1).
7. Which system the thesis reports (S6).
8. The A11 design (L2).
9. A protocol hash at A1 (S1).
10. Whether `list_task_runs` and `git show origin/...` are added to the prohibited operations (P5, P9).
11. How tests that build the development frame are guarded or deselected (P11).

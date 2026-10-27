# LEAD2_OPTIMIZATION Addendum 2: controlled comparison, calibration, threshold, acceptance (hashed before the Addendum-1 results were seen)

**When.** 2026-10-27, while the Addendum-1 leakage audit was still running. No Addendum-1 metric had been printed or read.

**Already known when this was written:**
- the frozen-run results (`out/results.json`);
- the Lead-2 error analysis (`LEAD2_ERROR_ANALYSIS.md`);
- the E1 investigation (`out/e1_investigation.txt`);
- the target verification (`out/target_verification.txt`).

Every quarter 2021–2026-Q3 has been seen. Everything here is **development evidence**.

## 1. Candidates (identical evaluation rows)

**Common rules.** All candidates are scored on the same rows: the UNI-FINAL evaluation rows (eligible origins × leads 1–15 with a T43c label), with the same target, issue-date cut-offs and baselines. The price condition (π_P vs observed price) and the combined proxy (π_H × π_P vs T43c) are reported separately.

| Id | Candidate | Adoptable |
|---|---|---|
| A | P0H0: served UNI-FINAL | yes (incumbent) |
| B | P5H0: A1-only structural projection | **no** (omits 11 families; diagnostic) |
| C | P4H0, P6H0: Addendum 1 (structural prior + corrections) | yes |
| D | **P7H0**: structural prior + strongly regularised corrections from all 12 families. Grid: depth 1 (2 leaves), learning rate 0.05, trees {10, 25, 50, 100}, min child 25, L2 10, L1 1, colsample 0.7, class weight none; inner chronological validation as before. | yes |
| E | **P8H0**: the same regularised grid **without** the prior, on all 12 families (U2 columns) | yes |
| F1 | **Calibration** of the adopted candidate's π_P. Platt scaling (logistic on logit π_P) fitted on that origin's **inner-fold out-of-sample** predictions only. Used only if it lowers the Lead-2 development Brier. | as a modifier |
| F2 | **Decision threshold τ**, research only. Per lead, chosen on development rows (targets ≤ 2024-Q4) to maximise balanced accuracy over {0.20, 0.25, …, 0.50}; ties go to the higher τ. Applied unchanged to the later block. | reported, **not served**: the approved dashboard rule is 0.50 |

**Hunger term.** H0 for every adoptable candidate. The sample-b H2 versions are reported for A, C, D and E as sensitivity only.

## 2. Selection (replaces the selection lines of Addendum 1)

- **Adopted candidate:** the lowest **Lead-2 development Brier** on T43c (targets ≤ 2024-Q4) among A, C (P4H0, P6H0), D and E.
- **Ties** within 0.0005 go to the earlier candidate in the order A, P4H0, P6H0, D, E.
- **Then F1:** calibration is applied if it lowers that Brier.

## 3. Acceptance criteria (fixed now)

**Per lead, on all evaluation rows.** R1–R7 (FINAL_THESIS_OBJECTIVES §7), unchanged, at the 0.50 rule:

| Rule | Requirement |
|---|---|
| R1 | ≥ 10 quarters and ≥ 40 rows |
| R2 | Accuracy ≥ 0.75 |
| R3 | Balanced accuracy ≥ 0.70 |
| R4 | Beats always-LOW and persistence |
| R5 | Brier below persistence and climatology (one-sided cluster bootstrap p < .10) |
| R6 | Precision and recall ≥ 0.60 |
| R7 | Thirds ≥ 0.60 and leave-one-quarter-out min ≥ 0.70 |

The maximum reliable lead is the run of consecutive passing leads from Lead 1.

**Later-block check.** The later block is 2025-Q2..2026-Q3 (6 quarters, 30 rows per lead). Required: accuracy ≥ 0.75, recall ≥ 0.60 (if it has ≥ 5 HIGH rows), and accuracy > always-LOW on the same rows.
- This block was seen in earlier experiments, so it is **not untouched**.
- It is also too small for R1 (6 quarters).

**The surge block** (targets 2023-Q4..2024-Q4) is reported separately.

**Verdict categories (decided now):**

| Verdict | When |
|---|---|
| **Reliable** | R1–R7 pass at that lead **and** the later-block check passes **and** the sealed prospective forecasts pass on untouched outcomes (SWS 2026-Q4 onward). No untouched outcome exists before SWS 2026-Q4 (about Jan 2027), so this verdict **cannot be issued today** at any lead. |
| **Promising but not yet verified** | R1–R7 pass and the later-block check passes, but no untouched outcome exists yet. For Lead 1 this is also what "reliable" has meant in earlier reports. |
| **Not reliable** | R1–R7 or the later-block check fails |

## 4. Post-hoc analyses of the adopted candidate (cannot change the adoption)

| Analysis | Design |
|---|---|
| (a) News ablation | All news columns removed and refitted |
| (b) Shuffled-news control | 20 refits with the news columns permuted across issue dates (seed 2029). Permutation p = share of shuffles with Lead-k Brier ≤ the real one. |
| (c) Family ablation | Each of the 12 families removed in turn, refitted; Holm across families × leads 1–3 |
| (d) Calibration bins | Reliability by bin |
| (e) Blocks | 2023, 2024, 2025, 2026; household-head vs adult SWS respondent base (before / from 2025-Q2); rising vs falling hunger |
| (f) Leave-one-quarter-out | Accuracy |

## 5. Serving

The adopted candidate replaces UNI-FINAL on the dashboard only if the PROTOCOL_LEAD2 §4 serve rule holds:
- reliable at Lead 1 under R1–R7;
- maximum reliable lead ≥ 1;
- Lead-1 Brier not worse than UNI-FINAL at one-sided p < .10.

**Exported artefact.** The served artefact must reproduce the evaluated Lead-1 probabilities exactly.

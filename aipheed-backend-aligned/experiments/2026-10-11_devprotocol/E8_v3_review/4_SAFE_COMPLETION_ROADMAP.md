# Safe Completion Roadmap

**Status: plan only, 2026-10-12. No stage has started.** Every stage that executes code, touches data, changes configuration or publishes anything needs your explicit approval. Item IDs refer to `E8_v3/5_APPROVAL_CHECKLIST.md` (A-items) and `3_APPROVAL_CHECKLIST_REVIEW.md` §3 (proposed B-items).

## What the evidence supports so far (no promises beyond it)

| Evidence | Source | Implication |
|---|---|---|
| 75% accuracy not achieved; persistence beats the model; AUC target fails | Memory index (earlier sessions). **Not re-verified.** | **This roadmap does not expect the accuracy requirement to be met.** E8 is not designed to show it. |
| E1–E7: the core model (M1) is best or tied; provincial CPI gap is the only signal that ranks provinces (ρ ≈ 0.4); news and national series do not help; M6's selection is unstable; nothing beyond non-inferiority shown | This session's run reports (manifests hash-verified) | Evaluation claims stay at "no gross failure detected" or "did not beat persistence", per quarter |
| E8 has two blind quarters; the 2026-Q4 outcome is expected only in 2027 | E8 v3 protocol and approval checklist | Added value cannot be demonstrated. **The thesis may have to report 2026-Q3 only** (review G1). |
| All model-arm simulations are proxy-dated (unverified) | Leakage checklist §F | No leakage-safe performance claim for model arms |

## Critical path and timing

1. **Stage 1 (A7 decision)** is time-sensitive. The scheduled tasks run again on 2026-10-13.
2. **Stages 2 → 3 → 4 (forecast freeze)** should follow without long gaps. Every day before the freeze is exposure risk for the blind quarters; after the freeze, later exposure cannot contaminate the forecasts.
3. **Stages 7 and 8 (drafting)** can run in parallel with stages 2–4, subject to the B-approvals.
4. **Stage 4's evaluation** waits on external releases for 2026-Q3. Their dates were deliberately not looked up.

---

## Stage 1: Data-access safety

| | |
|---|---|
| **Entry** | None; can start once you decide |
| **Deliverables** | (1) A7 decision recorded: 7a recommended, or your explicit acceptance of R1–R5. (2) Access controls X1–X4 built in the isolated backend with synthetic-fixture tests (A2). (3) Prohibited-operations list extended with `list_task_runs` summaries, `git show origin/...` / `git cat-file` on remote refs, and test runs that build the development frame (review P5, P9, P11). (4) Decision on how carrier-loading tests are run: deselected, guarded, or accepted (B1). (5) Fixed rule: re-hash the 55-file baseline before and after every later stage. |
| **Exit** | Scheduled-task decision recorded. Guard tests pass. All 55 baseline hashes unchanged. No backend or pipeline process running unless approved. `SCHEDULER_ENABLED=false` still present. |

## Stage 2: Evaluation protocol approval

| | |
|---|---|
| **Entry** | Stage 1 exit, or at minimum the A7 decision recorded |
| **Deliverables** | (1) **E8 v4** as new files (v1–v3 kept unchanged), resolving: C1 (availability rule: flag-and-use); C2 (correct H8 and L §D); C3–C7; L1 (τ statistic stated; A4 refitted at 14.345 or reported descriptively at 10.843); L2 (A11 design); O1–O3 (ranking score, baseline probabilities, INSUFFICIENT_DATA rows); G1 (single-quarter fallback); S1–S6. (2) Decisions recorded on A4 (margins) and A6 (2026-Q1 label). (3) A1 approval **plus** the protocol's SHA-256 recorded at approval. |
| **Exit** | A1 approved and hashed. Every open decision is resolved or explicitly deferred to its stated default. |

## Stage 3: Historical-input verification

| | |
|---|---|
| **Entry** | A1 approved; A2 controls in place; A5 approved with its sub-choices (rice, national series) and the `food_cpi`-level decision (review C4) |
| **Deliverables** | (1) Allowlist manifest (path + SHA-256) and frame code with tests, in the isolated backend. (2) Per-cutoff input-availability table (verified / proxy / schedule / unknown) derived from the code registry and release-date files, with no data values. (3) A validity label for each arm and cutoff. (4) A3 decision. **Recommended: defer web date checks until after A9**, which removes the exposure risk; the validity labels can then be upgraded retroactively. |
| **Exit** | Under the guard, the frame builds from allowlisted files only. Every input is tagged. Deny-list hashes unchanged. No 2026 label built (unless A6 approved for 2026-Q1). |

## Stage 4: Authorized forecast freezing and evaluation

| | |
|---|---|
| **Entry** | **A8 approved**, with prerequisites A1, A2, A5 and recorded decisions on A4, A6, A7 |
| **Deliverables** | (1) Frozen 2026-Q3 and 2026-Q4 forecasts with a manifest, a determinism check (two identical runs) and a before/after deny-list comparison. (2) After the releases exist: **A9-Q3 approved**, Q3 outcome collected from primary sources (not from production files), and a Q3 evaluation report with overall and ranking results reported separately, validity labels and no inference. (3) Later: A9-Q4 and the Q4 report, or a written single-quarter scope statement. |
| **Exit** | Freeze hashes re-verified before each outcome collection. Q3 report issued. Gross failure assessed only under A4 and only with both quarters (or under the v4 fallback). |
| **No promise** | Possible results include "no gross failure detected" or "the core LightGBM did not beat persistence". Neither is a success claim. |

## Stage 5: Final model decision

| | |
|---|---|
| **Entry** | At least the Q3 report. Review S6 resolved (which system the thesis documents: production `backend/` or the isolated backend). |
| **Deliverables** | Decision memo: **keep M6 served (default)**, or an A10 switch whose rationale is limited to E8 §8 conclusions (simplicity, no gross failure, non-inferiority). LightGBM stays the primary model family. Core is described as a provisional simpler alternative unless E8 says otherwise; it cannot be "validated" by two quarters. |
| **Exit** | Decision recorded. Served artifacts unchanged unless A10 approved, with earlier artifacts preserved. |

## Stage 6: Calibration and scoring decisions

| | |
|---|---|
| **Entry** | Stage 5 decision |
| **Deliverables** | (1) B5: keep the "uncalibrated" label (default), or calibrate on training-only folds. About 16 labelled quarters make any calibration estimate unstable; state this. (2) Confirm the fixed 0.50 cutoff, the INSUFFICIENT_DATA rules and SWS staleness (age > 3 quarters). (3) B6: rescore the dashboard **only** if outputs change, and only with approval. |
| **Exit** | Decisions documented. Classification-rule unit tests pass. No score, threshold or calibration fitted on any evaluation quarter or tuned to a HIGH/LOW distribution. |

## Stage 7: Backend and frontend regression testing

| | |
|---|---|
| **Entry** | A2 guard available. B1, B2 and B3 approved. Data access of production tests traced (`test_quarterly_pipeline`, modules imported by `app.main`). |
| **Deliverables** | (1) Isolated-backend suite results, with the four frame-building tests guarded or deselected (P11). Last recorded result: 288 passed, earlier on 2026-10-12. (2) Production suite results under the guard. The memory index records 6/102 failing as of 2026-10-07; not re-verified. (3) Frontend lint, type-check, build and `vitest` results, with no live API pointed at a backend exposing protected rows. (4) Failure list with causes. Fixes only under B4. |
| **Exit** | Suites pass, or every failure is documented with a decision. Deny-list hashes unchanged. No production or frontend change without approval. |

## Stage 8: Thesis documentation and release readiness

| | |
|---|---|
| **Entry** | Stages 4–7 complete, or explicitly scoped out in writing |
| **Deliverables** | (1) S6 reconciliation: one consistent description of the system the thesis evaluates. (2) Chapter 3/4 text: E1–E8 methods; per-quarter results; limits (proxy-dated inputs, two blind quarters, Equation 3 is a constructed proxy and not validated food insecurity, disclosed exposures, M6 selection instability). No 75% claim unless the evidence supports it; no adviser-approval claim. (3) Release checklist (B8: commit, push, merge, deploy each separately approved), including a decision on the protected-row files already on the remote. |
| **Exit** | Your review complete. Release actions approved individually. Integrity re-check (baseline, manifests, served meta) passes on the release candidate. |

---

## Stages that need no E8 approval (can proceed once their own B-approval is given)

- **Stage 7:** regression testing (B1–B3; B4 for fixes).
- **Stage 8 drafting:** thesis text (B7). The E8 results section waits for stage 4.
- **Stage 1 deliverables (2)–(5):** code and documentation only (A2 for the guard code).

# Completion Roadmap, Revision r2

**Status: 2026-10-12. Plan only.** Every step that executes code, touches data, changes configuration or publishes needs the approval named in `4_APPROVAL_CHECKLIST_R2.md`. Order: **containment, then verification, then protocol, then (only if defensible) evaluation.** Production and release work stays unauthorized.

**No accuracy target is promised.**

- Earlier records say the 75% target was not reached and that persistence beat the model (memory index; not re-verified).
- E1–E7 showed nothing beyond non-inferiority.
- If the data cannot support a defensible test, the evaluation is **not** carried out, and the thesis says so.

---

## Phase 1: Immediate safety decisions (today, before 2026-10-13 09:02 local)

| | |
|---|---|
| Decisions | SA-1 (disable both tasks), SA-2 (interrupt the stalled sessions), optionally SA-3 and SA-4. If declined, record that you accept risks R1–R5. |
| Entry | None |
| Deliverable | Before and after status from `list_scheduled_tasks` and `get_session` |
| Exit | Decision recorded. `SCHEDULER_ENABLED=false` still present. No backend or pipeline process running. |
| Why first | It is the only open item whose delay *increases* risk, and Q4's blindness (R2, Q4-c) depends on it |

## Phase 2: Test isolation and verification

| | |
|---|---|
| Entry | Phase 1 decision recorded; T-1 approved |
| Steps | (1) T-1: synthetic fixture, path redirect, deny-list guard, `real_data` marker. (2) T-1b: point the 11 carrier-loading tests at the fixture or mark them. (3) T-2: run the synthetic tests only. (4) TS-3: frontend checks (no live API). (5) Trace the data access of `backend/app/main.py` imports before any TS-2. |
| Deliverables | Guard and fixture code with unit tests. A test run report. A list of tests still needing real data. |
| Exit | Synthetic suite passes, or failures are documented. The guard demonstrably blocks deny-listed paths (a guard self-test on a dummy path). The 55-file baseline is unchanged. |
| Deferred | TS-1b (`real_data` tests) until after the Q4 freeze (EV-5) |

## Phase 3: Repository access investigation

| | |
|---|---|
| Entry | Any time; independent of phase 2 |
| Steps | RP-1 (visibility, forks, collaborators: read-only); optional RP-2 (`git ls-remote`, ref only); RP-3 (you message the collaborators); RP-4 if public (owner) |
| Deliverable | An addendum to the exposure assessment that records the answers |
| Exit | Visibility and collaborator boundaries known; access restricted if needed. **RP-5 (history rewrite) is not on the plan** unless you and the owner decide otherwise. |

## Phase 4: E8 protocol corrections

| | |
|---|---|
| Entry | Phase 1 decision recorded |
| Steps | (1) Write the corrected protocol text as new files, incorporating review r2 R1–R9 and the carried items (C2, C5, C6, L2, P1). Earlier versions stay unchanged. (2) EV-3: decide the CPI index level (recommended: drop `food_cpi` level). (3) EV-2: margins as single-quarter indications. (4) EV-4b: the 2026-Q1 label (default: exclude). (5) S6: which system the thesis documents. (6) EV-1: approve, and record the SHA-256. |
| Exit | Protocol approved and hashed. Every open decision resolved or explicitly deferred to its default. |
| Time constraint | Phases 4 → 6 must finish **before any Q4 outcome is published** (R2, Q4-b). The first release dates are unknown, and October CPI is expected in early November under PSA's documented practice. **If the window passes, Q4 becomes exposure-qualified and the evaluation reverts to descriptive only.** That is acceptable; it must not be rushed into an invalid freeze. |

## Phase 5: Input frame (prerequisite for any evaluation)

| | |
|---|---|
| Entry | EV-1, EV-3, T-1 complete; EV-4 approved |
| Steps | Build the allowlist-only frame and its manifest; tag every input (verified, estimated, uncited, excluded); synthetic-fixture tests |
| Exit | Frame builds from allowlisted files only, under the guard. No 2026 label built (unless EV-4b). Baseline unchanged. |

## Phase 6: Future evaluation (only with approvals and safeguards in place)

| Step | Approval | Condition |
|---|---|---|
| Generate and freeze C3/C4 forecasts | EV-5 | Phases 1, 4, 5 done; must be before the first Q4 release |
| Collect Q4 outcome; report as in R9 | EV-6 | After release (expected 2027); freeze hashes re-verified |
| Collect Q3 outcome; exposure-qualified, descriptive only | EV-7 | Optional; after EV-5 |
| Verify release dates (status upgrade only) | EV-8 | After EV-6/EV-7 |
| Calibration decision | CAL-1 | After the report; training-only data |
| Served-model decision | MD-1 | After the report; M6 stays by default |

**Stop rule.** If the Q4 conditions (R2) cannot be met or evidenced, Phase 6 produces **no evaluation claim**. The thesis reports the frozen forecasts (if any), the reasons, and the limits.

## Phase 7: Production and release (unauthorized; listed for completeness)

PR-1 to PR-5 and DB-1 each need separate approval. Their prerequisites:

- the S6 decision (which system the thesis documents);
- TS-2/TS-3 results;
- RP-1 (before any push);
- for PR-2 (pipeline): completion of E8 outcome collection.

## Work that can proceed in parallel without E8 approvals

**Thesis drafting** of methods, limitations, the disclosures (R8), and E1–E7 results. This is your document, and it needs no data access.

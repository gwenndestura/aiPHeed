# E26 final report: the root cause of unreliable forecasts, and the data needed to resolve it

**Date:** 2026-10-14.

**Scope:**

- 2021-Q1…2026-Q2 authorized data only.
- The approved Chapter I target (S1 = H + 2D > τ, reading A) and criteria C1–C9 are **unchanged**.
- The E25 seal is **unchanged** (451 E25 files re-verified, including the 3 seal files).
- E26 created **no new seal or forecast**.

## Bottom line

**The goal is not met, and it cannot be met with the authorized data.** No model has been shown to beat the strongest applicable baseline on valid unseen observations. The cause is **not code**:

1. The approved label is dominated by **one regional, noisy, random-walk-like survey series**. Persistence is close to optimal for it.
2. The expanding-median threshold makes the evaluation quarters **almost all HIGH**.
3. The provincial part of the label is a **transient constructed price indicator**, and **no local food-insecurity outcome** exists in the authorized data.
4. **Too few independent quarters** exist, and they accrue at one per quarter.

**Simulated chance of meeting the brief's success standard by 2031** (beat persistence, calibrated persistence, always-HIGH and climatology on unseen quarters):

| Forecaster | Accuracy | Brier |
|---|---|---|
| Correctly specified model, status-quo information | **0.0003** | 0.009 |
| Same model with a leading signal of correlation 0.9 | 0.012 | 0.059 |

**What can change this** is external:

- a **measured local outcome** (CBMS 2022/2024 FIES for the 142 LGUs) for local validation, available as soon as it is released and authorized;
- **verified SWS sample sizes**;
- **years of authorized prospective outcomes** under an approved claim rule (A1/A3).

---

## 1. Root cause, quantified (`ROOT_CAUSE_ANALYSIS.md`)

| Cause | Evidence |
|---|---|
| One regional series | 18 labelled quarters. 1 regional outcome series. 0 provincial food-insecurity outcomes. **68%** of label variance is the regional H, shared by all five provinces. |
| Threshold → almost all HIGH | Lead 1: 37 HIGH / **3 LOW** on 8 dates (lead 2: 33/2; lead 3: 23/2), against 45/90 LOW at the full-sample median. Accuracy > 75% is automatic: persistence scores 0.83–0.89 and always-HIGH 0.91–0.94. |
| Noisy random walk | Innovation sd 2.70 pp per quarter. Sampling noise is **29%** of the variance of round-to-round changes at n = 600 and **58%** at n = 300 (per-round n unverified). |
| Timing | At the origin, the quarter-t round is unpublished. A **timely regional reading** lowers the PCF21 Brier score to about 0.08 at leads 1–3 and anticipates 2–3 label changes (lead 2: p = 0.031 against persistence with the same label information; exploratory). Once the quarter-t label is also known, persistence catches up (lead 2 Brier 0.086; PCF21's margin p = 0.43). |
| Transient provincial part; no local outcome | Between-province variance of long-run D means = **0.00**. AR(1) φ = 0.73, so a deviation halves in about 2.2 quarters. D is constructed, not a food-insecurity measurement. |
| Few unseen quarters | P(evaluable) is 0.42 by 2028, 0.74 by 2029 and 0.83 by 2031. P(A1 accuracy claim by 2031) is 0.030 for a correctly specified model and 0.125 with a ρ = 0.9 signal. The frozen e-process gives 0.000 in every scenario. |

## 2. What is necessary to anticipate changes beyond naive persistence

| Lever | What E26 shows | Needed |
|---|---|---|
| **Outcome data** | The binding constraint. Local units are needed to validate local risk; regional quarters accrue too slowly. | O1 CBMS (142 LGUs) for local validation. O6 prospective outcomes for C9. O2–O4 for face validity (`MISSING_OBSERVATIONS_SPEC.md`). |
| **Predictive signals** | No authorized input anticipates regional hunger changes (E25: news, government indicators, regional inflation, label history). The months 1–2 CPI reading adds nothing to T1 (VOI). Even a ρ = 0.9 signal leaves a claim unlikely by 2031. | DROMIC/NDRRMC, bottom-30% CPI and provincial LFS can be tested once authorized (O7). Expect Brier and usefulness gains, not a claim. |
| **Target improvements** | The approved target is kept. The binary threshold label discards the size of hunger changes, and its provincial part is constructed. | **Adviser decisions** (`ADVISER_APPROVAL_REQUEST.md` R3): two-layer presentation; auxiliary SWS area series; a CALABARZON-specific H; a continuous score for H. None is applied. |
| **Modeling changes** | Persistence is near-optimal for a random walk, so no model change can be expected to beat it on accuracy with the same information. The one justified specification fix is per-round survey noise. | Verified per-round SWS n (O5a). The engine is ready (F2). |

**Why E26 fitted no new forecasting model.** Every 2021–2026-Q2 quarter has already been examined. Fitting or selecting another model on them would be repeated tuning on the test set, and the diagnostics above show that no authorized information supports anticipation. The E25 comparison of **all required baselines on identical chronological rows** stands:

- the six Chapter I baselines;
- calibrated persistence;
- always-HIGH;
- climatology.

## 3. Official sources: provenance and timing (`SOURCE_INVESTIGATION.md`)

| Source | Role | Status |
|---|---|---|
| SWS | Current outcome | Method **read** (PIDS SERP-P, AJAD 2024): 3-month reference period; four areas only; raw datasets open to academic researchers. Sample sizes known only from search summaries (300 → 600 for Balance Luzon within the window; unverified). |
| CBMS 2022/2024 | Local FIES outcome | FIES indicator and LGU/barangay tabulation **read** (PSA deck, PSAI 2024). The 2022 participant list is blocked (403). Data are held by the LGUs; turnover during 2025. |
| NNS 2023 (FIES) | Provincial outcome | Design known from search summaries only: 117 domains, about 384 households each. The official overview is image-only. |
| ENNS 2021 round (HFIAS) | Provincial outcome | Rolling design **read**: 2021 round fieldwork Jul 2021–Jun 2022. Which CALABARZON domains fall in it is not established. The public file mixes 2018/2019, so it is refused unless supplied as an extract. |
| PSA subsistence incidence | Official food-poverty outcome | 2021/2023 provincial figures known from search summaries only |
| DROMIC/NDRRMC, LFS, bottom-30% CPI | Signals | Search summaries only. Bottom-30% CPI is the logged contamination source. |

**No official quarterly food-insecurity outcome exists below the SWS area level.** Local outcomes can validate the **cross-sectional ordering** and **two-wave changes**. They cannot add quarterly evaluation dates.

## 4. Exactly which missing observations would enable a valid evaluation

| Evaluation | Missing observations | When valid |
|---|---|---|
| **Local risk** (Objective 3 rankings; SOP Q4 evidence beside H4) | O1: CBMS 2024 (and 2022) moderate-or-severe FIES % per city/municipality for the 142 LGUs (≥ about 75), with households assessed, source document, publication or turnover date, FIES method and LGU consent | As soon as authorized. 142 LGUs give power 0.97 to detect ρ = 0.3. |
| **Unseen quarters** (C9) | O6: for each target quarter from 2026-Q4, the SWS production round with its publication-date evidence and the three months of provincial food CPI with release dates. Plus a seal before each outcome, every quarter. | First A1 look at the end of 2029 at the earliest (P(evaluable) 0.74). Needs adviser approval of A1/A3. |
| **Correct survey-noise weighting** | O5(a): Balance Luzon n for every 2021–2026-Q2 production round | Immediate |
| **Face validity at province level** (Objective 5) | O2 NNS 2023 provincial FIES; O3 ENNS 2021-round HFIAS; O4 PSA subsistence 2021/2023 | Face validity only: 5 units need Spearman ≥ 0.9 for p < 0.05 |

## 5. Implemented and tested in E26

| Item | Where | Tests |
|---|---|---|
| Root-cause diagnostics: budget, signal-to-noise, VOI with B1/B1p/PCF21/PCF21_NOW/oracle on identical rows | `runner/root_cause.py` → `runs/root_cause.json`, `runs/voi_predictions.csv` | Rows identical across sets and models; one outcome per row |
| Horizon simulation: frozen e-process, A1, A3 and A2 scenarios | `runner/horizon.py` → `runs/horizon.json`, `docs/HORIZON.md` | Reproducible byte for byte |
| Prospective ledger: hash chain, SEAL / OUTCOME / NO_OUTCOME / LOOK, origin matching, A1 single look, A3 references, import of existing seals | `backend_dev/app/quarterly/ledger.py` | 18 tests, incl. type-I error of the sign-flip and e-process under the null, tamper detection, a second look refused, and the look time not choosable |
| E25 seal registered (no new forecast) | `runs/ledger/T1_A.jsonl` (22 seals), `T2.jsonl` (12); `runs/ledger/status.json` | Chains verify; forecasts hash = E25 seal; original seal time kept |
| Outcome and signal adapters (refuse, never filter) | `backend_dev/app/quarterly/outcomes.py` | 8 tests |
| Local validation and attribution | `backend_dev/app/quarterly/local_validation.py` | Detection, attribution, CI coverage |
| Two-layer output; constructed-indicator labels; per-round SWS n | `backend_dev/app/quarterly/pcf_engine.py` | Layer tests; quarterly transition regression; per-round n regression |
| Local-validation power design | `runner/local_power.py` → `runs/local_power.json` | Reproducible |

**38 tests pass** (`TEST_RESULTS.md`). All outputs are reproducible (`runs/reproducibility.json`).

## 6. Evaluation integrity

- **Identical chronological rows:** every VOI model and information set is scored on the same (lead, origin, province) rows (tested).
- **No leakage:**
  - Every input passes the E26 guard: pinned SHA-256, read-time filters, and no protected 2026-H2 file.
  - I1/I3/IO are labelled hypothetical or oracle information sets, not forecasts.
- **No repeated tuning:** E26 selects no model, threshold, feature or target. The protocol and amendments are hashed (`runner/PROTOCOL_SHA256.txt`).
- **Sealed forecasts preserved:**
  - `runs/e25_unchanged.json`: 451 of 451 E25 files match, including the 3 seal files.
  - E26 created no new seal (`docs/CONTAMINATION_LOG.md`).
- **Mistakes and deviations:** all disclosed (`BUG_FIXES.md`), including two rule breaches of my own (M4, M5).

## 7. Against the success standard

- **Not met.** E25 is the only evidence on the approved target, and it is development evidence: PCF21 ties persistence on accuracy (0.875). Its pooled Brier gain (p = 0.027) does not survive Holm (0.082). Always-HIGH has the best Brier at lead 1.
- **Unseen observations: none yet.** No sealed target has an authorized outcome.
- **Accuracy above 75% is not evidence.** It is automatic on these quarters.

## 8. Remaining external dependencies

| # | Dependency | Who | Exactly what | Unblocks |
|---|---|---|---|---|
| 1 | CBMS LGU FIES aggregates | Researcher → LGUs / PSA RSSO IV-A | O1 file + SHA-256 + consent | Local validation (R2 approval to count it) |
| 2 | SWS per-round sample sizes; March/June 2026 publication dates | Researcher (SWS releases) | O5(a)(b) | Correct noise weighting; earlier usable origins |
| 3 | Prospective outcomes, each quarter | Researcher (SWS, PSA) | O6, from 2026-Q4 | C9 via the ledger |
| 4 | A quarterly seal before each outcome | Researcher authorizes the cycle inputs (E25 A1–A2) | One seal per cycle, with no gaps | Accrual of unseen dates |
| 5 | Adviser approvals | Adviser | R1 (A1), A3, R2, R3 options, R4 (NNS 2019), E25 P1–P9 | A valid claim rule; counting local evidence |
| 6 | NNS 2023 provincial FIES; ENNS 2021-round extract; PSA subsistence tables | Researcher → FNRI / PSA (FOI if needed) | O2–O4 | Objective 5 face validity in window |
| 7 | Signals (DROMIC, bottom-30% CPI, LFS) | Researcher | O7, authorized period only | A test for anticipatory signal |
| 8 | PSA 2021 municipal SAE | Researcher | O8 | Replaces 126 poverty substitutes |
| 9 | 50 DA Region IV-A evaluators | Researcher | E25 instruments | H4, H5 |
| 10 | Operational ledger location | Researcher | A decision; the production backend was not modified | Live prospective scoring |

## 9. What the thesis may and must not claim (E26 additions)

**May claim:**

- The binding limits are the target's structure and the data, quantified as in section 1.
- A timely regional reading has information value on development quarters (exploratory).
- The provincial price term has no detectable persistent provincial component.
- A prospective, hash-chained, single-look evaluation is implemented and the E25 seal is registered in it.
- A local validation is ready and needs CBMS data.

**Must not claim:**

- that aiPHeed anticipates food-insecurity changes or distinguishes local risk;
- that any lead is reliable;
- generalization to unseen quarters;
- that the price-pressure indicator measures food insecurity;
- that accuracy above 75% shows skill;
- anything from NNS 2019 or other pre-2021 data.

## 10. Chapter I requirements preserved

- **Unchanged:** the target, the label rule, C1–C9, the objectives, the SOP and the hypotheses.
- **Approvals pending:** A1 and A3 (claim rule and success standard), R2 (local evidence) and R3 (target options).
- **No substitutes:** CBMS or FNRI evidence never replaces the DA evaluators (H4/H5). NNS 2019 is not used (R4).

## Deliverables

| File | Content |
|---|---|
| `ROOT_CAUSE_ANALYSIS.md` | Causes 1–6 with numbers, and what removes each |
| `SOURCE_INVESTIGATION.md` | Sources S1–S10: provenance, timing, access, verification level |
| `MISSING_OBSERVATIONS_SPEC.md` | O1–O8: exact files, coverage, evidence, what each makes valid |
| `ADVISER_APPROVAL_REQUEST.md` | R1–R5 and researcher decisions |
| `FROZEN_ANALYSIS_PROTOCOL.md`, `PROTOCOL_AMENDMENT_A1.md`, `_A2.md`, `_A3.md` | Frozen rules; hashes in `runner/PROTOCOL_SHA256.txt` |
| `docs/HORIZON.md`, `docs/CONTAMINATION_LOG.md`, `docs/CONTAMINATION_LOG_ADDENDUM.md` | Horizon table; exposure log |
| `BUG_FIXES.md`, `TEST_RESULTS.md`, `REPRODUCE.md`, `README.md` | Mistakes and deviations; tests; commands; index |
| `runs/` | `root_cause.json`, `voi_predictions.csv`, `horizon.json`, `local_power.json`, `reproducibility.json`, `e25_unchanged.json`, `ledger/` |
| `E26_FILES_SHA256.txt` | SHA-256 of every E26 file except itself |

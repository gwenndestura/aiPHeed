# NEW_MODEL, Phase 1: research and repository audit (no training, no experiments, no production change)

**Written:** 2026-11-03.

**Status:** **not committed**: you asked for no commit without authorization.

**Sources read:**
- the thesis, `THESIS 2 (18).pdf` (newest, 30 Oct 2026, 73 pages): Chapter I §1.3–1.5 and Chapter III pp. 30–67;
- the repository at branch `aiPHeed/system-fixes`;
- the 81 experiment folders under `aipheed-backend-aligned/experiments/`.

## 1. Repository state

| Item | Finding |
|---|---|
| Branch | `aiPHeed/system-fixes`, 63 commits ahead of and 3 behind `origin/aiPHeed/system-fixes`. Nothing was pushed in this work. `main` is untouched |
| Working tree | Clean except one tracked cache file (`E107…/__pycache__/e107_lib.cpython-313.pyc`) and this new, uncommitted folder |
| **Deployed model** | `render.yaml` and `backend/Dockerfile` set `AIPHEED_LEAD2_MODEL=thesis`, `AIPHEED_STRICT_MODEL=1`, and **no** `AIPHEED_MAP_MODEL`, so production serves **FIRI v2** (an index, not a forecast of a measured outcome) |
| Other serving modes | `ch1` (P0H4 hybrid) and `foodinsecurity` (REF+news, Option C). Both exist, are non-default, and are switched by environment variables |
| Experiment registry | **No single registry exists.** Each folder documents its own plan, hashes and results (protocol-first since about E85). `backend/app/quarterly/registry.py` is a data-source registry, not an experiment registry |

## 2. What the paper requires (verified in the PDF)

| Item | Paper text (page) | Note |
|---|---|---|
| **Data** | 120 rows = 5 provinces × 24 quarters (p. 42); news 2021–2025 / 2020–2025, and 120 vs 135 rows, conflict (C4) | 24 quarters is the whole study window |
| **Target, Eq. 3** | stress(p,t) = **SWS regional hunger(t) + 2 × (food CPI YoY(p,t) − cross-province mean(t))**; HIGH if above the **global median of all 120 pairs**, "guarantees a 50/50 class balance" (pp. 51–52) | See conflicts K1 and K2 |
| FNRI | ENNS FIES "retained as a face-validity anchor … not used in label generation" (p. 51); Obj 5 names NNS 2019 and 2023, Ch 3 names 2021 and 2023 (C1) | |
| **Algorithm 3** | k = 1..8; expanding walk-forward, gap k, **minimum training window 8 quarters**; default LightGBM; stop when mean fold accuracy < 75%; output Maximum Reliable Lead Time (pp. 41–42) | Applies to one model per lead |
| **Algorithm 4** | 100-trial Optuna TPE on 9 hyperparameters at the fixed gap k = MRLT; weighted F1 objective; evaluated **once on the last four holdout quarters, never exposed to Optuna**; accept if **F1 ≥ 0.75 and AUC ≥ 0.80** (pp. 43–44) | The paper applies Algorithm 4 **at k = MRLT only**, not at every lead |
| **Algorithm 5 / Rule 4** | Municipal index = **validated** province probability × (0.6 poverty_norm + 0.4 density_norm), with disaggregation label and data-sufficiency flag (p. 46) | |
| §3.4.4 | Unvalidated configurations "will not be published" (pp. 57–58) | |
| **R1–R7** | **Not in the paper.** They are the project's frozen reliability rule (`FINAL_THESIS_OBJECTIVES/FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` §7), applied since FINAL_*; verified against their code in `SENIOR_REVIEW/AUDIT.md` D1–D2 | Stricter than the paper. Keep, and say so |

## 3. Evidence already in the repository (what has been tried, with results)

All of this is **development evidence**: every scored quarter was examined during development.

| Line | Target | Best result | Verdict |
|---|---|---|---|
| **Paper pipeline as written** (E99, reproduced byte-identically in `PAPER_ALIGNED/E99_REPRODUCTION.md`) | Eq. 3, global median, 12 features, 24 quarters | Algorithm 3 Lead 1 mean fold accuracy **0.30** (persistence 0.70), so **MRLT = 0**. Algorithm 4 (report only) on 2025-Q4..2026-Q3: accuracy 0.45, weighted F1 **0.53**, AUC **0.61** | Fails both gates |
| **P0H4 hybrid** (`ch1` mode; `PAPER_ALIGNED/P0H4_EVIDENCE.md`) | Province class = regional hunger condition **and** provincial food-price condition | Lead 1: accuracy 0.843, **all R1–R7 pass** (14 quarters, 70 rows). Lead 2: 0.769, fails R3, R5, R6 (caught 6 of 17 HIGH). MRLT 2 (75% rule), 1 (R1–R7) | Lead 1 only. The province differences come from the **price** condition |
| **REF / REF+news** (IMPROVE_V2, OPTION_1; `foodinsecurity` mode) | Regional SWS Balance Luzon hunger > 11.3%, 62 labelled quarters 2010–2026, walk-forward from 1998 | REF: Lead 1 = Lead 2 accuracy 0.790, AUC 0.70, fails **R7** only. REF+news: 0.758, AUC 0.69, fails **R3, R5, R7**. MRLT 2 (75% rule), 0 (R1–R7) | Both leads pass the 75% rule; neither passes R1–R7 |
| **Rescue attempts** (RELIABLE_L12, RELIABLE_NEWINFO, OLD_NEWS) | Same regional target | Per-origin threshold: 0 calls changed. 0.5 REF + 0.5 persistence: fails R2/R3/R7. + CHIRPS rainfall: calls identical to REF. + GDELT 2015–2026: fails R5 and R7; one call changed, to the wrong class | All failed; attempts declared closed |
| **Bug audit** (SENIOR_REVIEW) | — | 13 PASS, 4 NOTE, **no bug**; R1–R7 reproduced independently | Failures are real |
| **Root diagnosis** (RELIABLE_NEWINFO Step 0) | — | 8 of the 9 errors in 2015–2020 are readings within SWS's ±5.7-point sampling error of 11.3%; R7's middle third is 12/21 | See K4 |
| **NLP** (E85, OPTION_1, OLD_NEWS, `OBJECTIVES_STATUS.md`) | — | News is 2.8% of SHAP. REF+news is **worse** than REF (Brier +0.008 / +0.015, p 0.82 / 0.96). GDELT history to 2015 did not help. Only 17% of province-quarters have ≥ 5 province-tagged articles. BERTopic topics are mostly place names | No measured predictive value |
| **Objective 4 / H3** (OPTION_1 §4) | — | REF+news beats persistence (Holm p 0.001) and NLP-only; it does **not** significantly beat the government-only logistic regression, the combined logistic regression or the government-only LightGBM | H3 not rejected |
| Earlier families (E13–E114, FINAL_*, LEAD2_*, FIRI_*) | Various: S1 = H + 2D, FIRI index, price conditions | Lead-1 passes appear mostly where the target carried a **price** component; Lead 2 consistently failed or was experimental | Documented in each folder |

## 4. Methodological conflicts (for you and your adviser; none resolved silently)

| # | Conflict | Evidence | Consequence |
|---|---|---|---|
| **K1** | **No measured provincial food-insecurity outcome exists.** SWS reports Balance Luzon only. FNRI and PSA FIES are regional and every 2–3 years. CBMS 2024 is one LGU-level cross-section (`MORE_SOURCES/SOURCES.md`) | Eq. 3 gives every province the **same** hunger term in a quarter, so **province differences in the label come only from food-CPI deviation** | "Genuine province-level food-insecurity classification" (Objective 3, master prompt §1) **is not supported by the data**. Any province-level class is either regional hunger copied to five provinces, or hunger plus a **price** condition. This is the price-dominance the master prompt warns about |
| **K2** | **Eq. 3's global median looks ahead** (it uses all 120 pairs, including future quarters), and "guarantees 50/50" by construction | p. 52; STEP0_REQUIREMENTS C7 | Conflicts with your no-leakage rule 5. Eq. 3 cannot be used as written; an origin-specific median changes the class balance (mostly LOW in 2021–23, mostly HIGH in 2024–26) |
| **K3** | **24 quarters with one regime switch** (the paper's window) | E99: Eq. 3 HIGH in 2/15, 3/15 and 2/20 rows in 2021–2023, mostly HIGH from 2024 | 8-quarter minimum windows are nearly one-class; this is why the paper pipeline scored 0.30. Only the regional SWS series has a long history (1998+) |
| **K4** | **R7 fails for a structural reason** | 300-respondent BL area, ±5.7 points; the 2015–2020 readings cross 11.3% nine times in 21 quarters | No input tried changes it. It is a property of the target and its fixed threshold |
| **K5** | **No blind holdout remains.** Algorithm 4's "last four quarters never exposed" (2025-Q4..2026-Q3) were used by E99 and then examined by dozens of experiments | Every folder since E99 scores them | A Lead-1/Lead-2 holdout gate (master prompt §4) **cannot be honestly run on existing quarters**. The only blind data are sealed **2027+** forecasts: four quarters exist from about early 2028 (`SENIOR_REVIEW/PROSPECTIVE_PLAN.md`) |
| **K6** | **Holdout AUC ≥ 0.80 at both leads** (master prompt §4, §9) | The paper requires it only at k = MRLT. No model on any target has reached AUC 0.80 in walk-forward (best about 0.75: the RELIABLE_NEWINFO blend) | Very unlikely with the current data; reported, not chased |
| **K7** | **The NLP objective vs the evidence** | K-table row "NLP" above | The title's "Using NLP" is met as a pipeline (Obj 1). Its **predictive** contribution is nil. It must be reported as such, not retained to "claim AI" (master prompt §2) |
| **K8** | **Optuna 100 trials on 24 quarters** | Overfitting risk; the project used a fixed 8-setting grid with chronological inner selection | An Algorithm 4 deviation already disclosed in CH3_AMENDMENT; keep it disclosed |
| **K9** | **"Validated" forecasts for LGU rankings** (Obj 3, Rule 4, §3.4.4) | No model passes all gates at both leads | The paper's own rule says LGU rankings should not be published as validated. Today they are shown labelled as priority rankings |
| **K10** | **Open paper contradictions** C1 (FNRI years), C3 (DEPDev), C4 (window and row counts), C5 (45 vs 12 features), C6 (single LightGBM vs blend), C8 (CPI_dev definition), C13 (density year), C18–C19 (Eq. 4, Rule 7 threshold) | `PAPER_ALIGNED/STEP0_REQUIREMENTS.md` §B | Adviser decisions, still open |
| **K11** | **R1–R7 are not in the paper** | §2 above | Use them as written (master prompt §5), but present them as the project's stricter rule, beside the paper's Algorithm 3/4 gates |

## 5. Research alignment matrix (proposed activities × objectives)

| Proposed activity (Phases 2–6) | Obj 1 NLP | Obj 2 accuracy, MRLT | Obj 3 province / LGU | Obj 4 baselines | Obj 5 system, FNRI |
|---|---|---|---|---|---|
| A. Target decision memo (K1–K3), with Ch I/III amendments for adviser approval | | ● defines y | ● decides what "province-level" means | ● | ● FNRI role |
| B. Unified experiment registry of the ~80 existing experiments (ID, target, features, window, leads, metrics, R1–R7, failure reason, hashes) | ● | ● | ● | ● | ● reproducibility |
| C. Root-cause write-up separating proven from assumed causes (Phase 2) | ● | ● | ● | | |
| D. One pre-registered final evaluation of the chosen model: Algorithm 3 at Leads 1–8, both leads reported separately, R1–R7, calibration, by-period, by-province where defined | | ● | ● | | |
| E. Six-comparator Objective 4 / H3 table for the chosen model, with Holm correction (exists for REF+news; repeat for the final choice) | ● | | | ● | |
| F. NLP ablation report (exists: REF vs REF+news, GDELT) consolidated as the Objective 1 answer | ● | | | ● | |
| G. SHAP by group, lead and period, from stored rows | ● | ● | ● | | ● dashboard explanations |
| H. Algorithm 4 blind holdout = the **first four sealed prospective quarters (2027-Q1..Q4)**, scored once, pre-registered now | | ● | ● | | ● |
| I. Spatial outputs gated on validation status (labels already disclose vulnerability weighting) | | | ● | | ● |

## 6. Proposed development direction (for your approval; nothing started)

**1. Decide the target first (activity A).** The data allow three honest options:

| Option | Target | Pros | Cons |
|---|---|---|---|
| **(i) Regional food insecurity** (REF family; Option C in CH3_AMENDMENT) | BL hunger > 11.3% | A measured outcome; 62 labelled quarters; Leads 1–2 at 0.79 | No province-level classification. Obj 3 and RQ2 need amending |
| (ii) Eq. 3 with an origin-specific median | As the paper, without the leak | Paper-faithful | Province differences are price only. 24 quarters; scored 0.30 |
| (iii) Hybrid (P0H4) | Hunger condition **and** provincial price condition | Province classes; Lead 1 passes R1–R7 | Province signal is a price forecast; Lead 2 fails |

**My recommendation: (i).** It is the only target that measures food insecurity rather than prices. Its consequences for Chapters I and III are already drafted (CH3_AMENDMENT §9.1, Option C).

**2. Treat development data as exhausted.**
- Further searching for a configuration that passes R1–R7 on 2010–2026 would be selection on known outcomes (master prompt §8).
- Instead, pre-register **one** final evaluation (activity D), and make the **first four sealed 2027 quarters the Algorithm 4 blind holdout** (activity H).

**3. Build the experiment registry (activity B).** This makes every past result traceable, including the failed ones.

**4. Report honestly where the acceptance gate (master prompt §9) cannot be met with today's data:**
- Lead 1 and Lead 2 both passing R1–R7: not achieved (K4);
- a blind holdout: not available until 2028 (K5);
- holdout AUC ≥ 0.80: not reached so far (K6).

**5. New model work only where a genuinely new, justified idea exists.**
- **Measurement-error-aware labels** using SWS's published sampling error. It needs a new sealed plan and is still development evidence.
- **OCTA as a second hunger measurement from 2022.** It is prospective only.

I do not recommend more input-hunting.

**Stop.** Phase 2 waits for your decisions:
- the target option (i/ii/iii);
- whether to adopt the 2027 sealed quarters as the Algorithm 4 holdout;
- whether to build the registry;
- whether either new idea in item 5 is wanted;
- whether this folder may be committed.

# Objective completion matrix (2026-11-04)

**Legend:**
- **Done:** completed with evidence.
- **Partial:** evaluated, with targets or validation not met.
- **Blocked:** needs human input or external data.

| # | Objective (Ch. I 1.5.2) | Status | Evidence | What is still required (and from whom) |
|---|---|---|---|---|
| 1 | NLP: XLM-RoBERTa FSSI + BERTopic, validated | **Blocked** | Pipeline runs; BERTopic temporal evaluation (`FINAL_2026-11-04/BERTOPIC_TEMPORAL_VALIDATION.md`); annotation tooling selftest passes | **Annotators:** label 300 headlines × 2 (currently 0 / 300). Then kappa, XLM-R relevance/stress accuracy, FSSI validation |
| 2-I..IV | Accuracy, precision/recall, F1, AUC-ROC | **Partial** | Provincial C-B6D-E-X, 250 rows, Lead 1: acc 0.772, P 0.821, R 0.863, F1 0.841, AUC 0.739 (CI 0.62–0.86). Regional C-B6 on measured hunger: acc 0.806 | AUC ≥ 0.80 not met. Prospective data from 2027 |
| 2-V | Lead time (walk-forward) | **Partial (Lead 2 improvement attempted, failed; bottleneck = regional hunger at 2 quarters)** | Provincial: Algorithm 3 = 1 quarter (C-B6D-E-X on B-ext); R1–R7 pass at Lead 1 only. Regional C-B6: 2 quarters | Lead 2 provincial accuracy 0.736 < 0.75 |
| — | Food-insecurity focus (not price) | **Done (regional), partial (provincial)** | Regional: price-only fails (acc 0.66 / 0.60), full model significantly better (p 0.024 / 0.001), hunger 58% of SHAP. Provincial: price terms 43–51% by Eq. 3 construction; hunger part 0.74 vs measured hunger | A measured provincial food-insecurity target (FNRI/PSA FIES) |
| 3 | Province and 142-LGU rankings | **Partial: implemented and verified; not validated** | Recomputation exact (5 + 142); inputs complete; 25 LGUs low-precision (CV > 20%) | **No LGU outcome data exists.** Province rank vs Eq. 3 outcomes ρ −0.30 (n = 5, n.s.). **Adviser:** weights decision. Rankings are vulnerability, not observed food insecurity |
| 4 | Baselines: persistence, PSA-only, NLP-only, LOGIT | **Done (comparison); superiority partial** | Identical rows per comparison; results by model below | Prospective data for the remaining comparisons |
| 5 | Dashboard, alerts, ISO/IEC 25010, FNRI | **Partial** | Backend 56/56 tests (2026-11-04: the 34 food-insecurity / auto-update tests plus 22 job tests); HIGH alerts need human confirmation; ISO instrument and analysis plan prepared (`OBJ5_ISO25010_INSTRUMENT.md`, `OBJ5_ANALYSIS_PLAN.md`); FNRI 2023 regional 19.1% and 2021 provincial (2) direction consistent | **DA personnel:** 50 ISO/IEC 25010 responses. **Adviser:** FNRI wording (no 2019 regional figure). **Team:** deployment authorization |

**Objective 4 superiority, by model (corrected wording 2026-11-04; the numbers are unchanged from the source JSONs):**

| Model | Source | Significant (Holm) | Not significant |
|---|---|---|---|
| Regional C-B6 | `../out/cb6_results.json` | 9 of 14 comparisons | logistic regression and others (see source) |
| C-B6D-E-X, B-ext | `out/fi_provincial_results.json` | PERSIST-X (both leads) | CLIM-X, C-B6-R, PO-P-X, NP-P-X |
| C-B6D-E-X, B-old (2021+) | `out/cb6d_results.json` (C-B6D-E) | NLP-only (both leads), PSA-only (Lead 2) | persistence, LOGIT, C-B6P2, C-B6-R |
| C-B6D-E-XH, B-ext | `out/xh_results.json` | PERSIST-X (both); LOGIT-NLP-P (Lead 1); LOGIT-COMB-P, LOGIT-GOV-P (Lead 2) | C-B6D-E-X, CLIM-X, PSA-only-P-X; LOGIT-COMB/GOV (Lead 1) |

**The provincial logistic regression variants (thesis RQ3)** were compared only for C-B6D-E-XH on B-ext, not for
C-B6D-E-X.

## Model status

| Model | Level | Target | Status |
|---|---|---|---|
| C-B6 | Regional | Measured BL hunger > 11.3% | **Served main model** (team decision; adviser pending) |
| C-B6P2 | Province | Eq. 3 (2021+) | Local demo; failed pre-registered rule |
| C-B6D-E | Province | Eq. 3 (2021+) | Development; R4/R5/R7 fail |
| **C-B6D-E-X** | Province | Eq. 3 (2013+) | **Strongest provincial candidate:** passes R1–R7 at Lead 1 only; Lead 2 0.736 (fails R2/R3); sealed prospectively (2c1ff50a…); not served |
| C-B6D-E-X2 | Province | Eq. 3 (2013+) | Pre-registered Lead 2 fix; **failed** (L1 0.712, L2 0.664); kept as evidence |
| C-B6D-E-XA | Province | Eq. 3 (2013+) | + province crop/fisheries shocks; no gain (L1 0.772, L2 0.728); not adopted (`PROVINCIAL_NONPRICE_EVIDENCE.md`) |
| C-B6D-E-XH | Province | Eq. 3 (2013+) | Paper-aligned H1/N1 momentum. L1 R1–R7 pass, best L1 AUC 0.767 / Brier 0.173; L2 0.708 fails R2/R3; not adopted (rule); sealed 1709044f… |

## Alignment with the paper (latest attempt)

- **Unchanged:** Eq. 3, the objectives and the variable families (H1, N1, E1, E2 constructions only).
- **Baselines:** RQ3 logistic variants (combined, government-only, NLP-only) now included.
- **Open deviation (adviser):** the 11.0 cut-off instead of the paper's all-period median.
- **RQ2 / H2 answer on current data:** the furthest reliable provincial lead is 1 quarter.

## Status by category (2026-11-04, final for this session)

### Completed and verified

- **Eq. 3 verification:**
  - D sums to 0 across the provinces each quarter;
  - S = H + 2D exactly;
  - THR recomputes to 11.0.
- **Provincial forecasting (C-B6D-E-X):**
  - five distinct province forecasts;
  - Lead 1 R1–R7 pass (B-ext, 250 rows);
  - Algorithm 3 = 1 quarter.
- **All metrics recomputed independently:** sklearn, AUC bootstrap CIs, Holm, Algorithm 3 (max \|Δ\| 1.1e-16).
- **Food-insecurity focus (regional):** price-only fails; hunger history drives the forecast.
- **Baseline comparisons** on identical rows (Objective 4, table above).
- **Objective 3 implementation** recomputed against the API: 141/142 exact; Cardona's 0.49 is the intended display rule
  (`OBJ3_VALIDATION_PROTOCOL.md` §1).
- **Backend tests:** 56/56 pass.

### Implemented but not validated

- **Province and 142-LGU vulnerability rankings:** no observed provincial or LGU outcome (`OBJ3_VALIDATION_PROTOCOL.md`).
- **Provincial forecast on untouched data:** sealed (2c1ff50a…, 1709044f…); scored after the SWS 2026-Q4 / 2027-Q1
  releases.
- **AUC target:**
  - C-B6D-E-X Lead 1 AUC 0.739 (95% CI 0.62–0.86) against the 0.80 target;
  - Lead 2 0.711 (CI 0.58–0.82);
  - not tuned further on the same rows, by rule.
- **Lead 2:** not reliable (accuracy 0.736, balanced 0.674), with the cause documented.

### Prepared and awaiting human participation

- **Objective 1:** 300-headline annotation.
  - The sheets are identical for A and B and match commit 2d762ab.
  - The system outputs are sealed (SHA-256 f8e668d4…).
  - Workflow fixed in `annotation/ANNOTATION_GUIDE.md`. Labels: **0 / 300**.
- **Objective 5:** the ISO/IEC 25010 questionnaire, participant instructions, administration protocol and scoring plan
  (`OBJ5_EVALUATION_PACKAGE.md`). Responses: **0 / 50**.
- **H4:** evaluator ranking task (Part F). Responses: **0**.

### Blocked by unavailable data or adviser approval

| Blocker | Needed from |
|---|---|
| The 11.0 Eq. 3 cut-off (the paper says the all-period median) | Adviser |
| The issue-date rule that makes Lead 2 a three-quarter hunger horizon (SWS publishes about 59 days after quarter end) | Adviser, if Lead 2 is to change |
| The DEPDev usability arm (RQ5 names DEPDev; the instrument covers DA only) | Adviser, plus a hashed analysis-plan addendum |
| The FNRI wording (no 2019 regional figure exists) | Adviser |
| Provincial / LGU food-insecurity outcomes (PSA provincial subsistence incidence exists only for 2018/2021/2023, CV up to 59%; Eq. 3 provincial term does not track it, p 0.39) | FNRI, PSA, DSWD, LGUs |
| Whether to amend Eq. 3 with a province food-poverty term | Adviser |
| The main-model decision and deployment authorisation | Team and adviser |

**No objective is marked complete without proof.**

# C-E2 improvement and objective completion report (2026-11-04)

**Scope:** the master execution prompt of 2026-11-04. All work is local, backend research only.
- Nothing is committed, pushed, merged or deployed.
- C-b (sealed 67baec66) remains the main model.
- No frontend file, seal, ledger, production model or configuration was changed (§15).

**Bottom line:**
- C-E2 reproduces exactly.
- The two pre-registered fixes for R3/R7 (C-E5R, C-E5C) **failed**: both are clearly worse.
- No candidate beats all seven baselines with statistical evidence. The remaining gap is a sample-size limit, not a
  bug (§10).
- **Objectives 2 and 3:** completed.
- **Objectives 1 and 4:** partial, with exact blockers.
- **Objective 5:** backend readiness is completed; the evaluation itself is pending (questionnaire ongoing).

---

## 1. C-E2 reproduction

- **Pre-registration:** `CE2_PREREGISTRATION.md`, SHA-256 a1b469da… verified by `ce2_model.check()`.
- **Refit from scratch** (`ce2_model.py fit` and `score`): `out/ce2_fits.csv` and `out/ce2_results.json` are
  **byte-identical** to the stored copies (`out/repro_2026-11-04/`; SHA-256 c078aa27… and 13666bfd…).
- **Reproduced metrics:** every figure in §2 of the prompt.
- **Defect found and fixed (my own, earlier today):** `ce4_model.py` wrote its outputs to the C-E3 file names, so C-E3's
  evidence had been overwritten.
  - The paths were corrected.
  - C-E3 and C-E4 were refitted (deterministic) and now have their own files. Their figures equal those first
    reported.

## 2. Experiment registry and plan hashes

All rows are appended to `NEW_MODEL/ALLBASE/REGISTRY.csv`. The 17 earlier rows are unchanged (checked against
`backup/REGISTRY_before_2026-11-04.csv`).

| Attempt | Plan | SHA-256 | Result |
|---|---|---|---|
| C-E (17th) | CE_PREREGISTRATION.md | bde69c08… | Not adopted |
| C-E2 (18th) | CE2_PREREGISTRATION.md | a1b469da… | Not adopted; served in the local demo |
| C-E3 (19th): one model per lead | CE3_PREREGISTRATION.md | 34b1c1f9… | Failed (L1 0.726, L2 0.645, MRLT 0) |
| C-E4 (20th): + target season | CE4_PREREGISTRATION.md | 95a9cc61… | Failed (R3, R7; no gain) |
| C-E5 (21st): C-E5R, C-E5C, C-E2-NONEWS | CE5_PREREGISTRATION.md | 2ab41820… | C-E5R and C-E5C failed; ablation reported |

## 3. Why C-E2 fails R3 and R7 (`runner/obj2_diagnostics.py` → `out/obj2_diagnostics.json`, read only)

| Third (Lead 1) | Share HIGH | C-E2 accuracy | C-E2 LOW recall | C-b | LOGIT | Persistence |
|---|---|---|---|---|---|---|
| 2010-Q1..2015-Q1 | 0.95 | 0.952 | 0 of 1 | 0.952 | 1.000 | 0.905 |
| 2015-Q2..2020-Q4 | 0.48 | **0.524** | 0.36 | 0.571 | 0.381 | 0.429 |
| 2021-Q2..2026-Q3 | 0.65 | 0.850 | 0.71 | 0.850 | 0.750 | 0.650 |

**Causes, in order of evidence:**
1. **Regime change (R7).** Hunger fell below the line often in 2015–2020, after a mostly-HIGH history. Every model
   fails that third, including LOGIT and persistence. This is a property of the data, not of C-E2.
2. **HIGH bias (R3).** The mean probability on LOW quarters is 0.60 (0.73 on HIGH), and LOW recall is 0.47.
3. **Survey uncertainty.** 9 of 14 Lead-1 errors are within 2 points of 11.3%. On label changes, C-E2 is right on only
   6 of 13 quarters; on repeats it is right on 0.857.
4. **Calibration:** forecasts of 0.5–0.7 came true in 87% of cases, so the model is under-confident there.

## 4. Objective 2: the pre-registered fixes (`runner/ce5_model.py` → `out/ce5_results.json`)

| Lead 1 / Lead 2 | Accuracy | Balanced | AUC | Brier | Failed | MRLT |
|---|---|---|---|---|---|---|
| C-E2 | 0.774 / 0.758 | 0.690 / 0.679 | 0.715 / 0.694 | 0.1875 / 0.1879 | R3, R7 | 3 |
| C-E5R (recency weighting, half-life 16 quarters) | 0.661 / 0.645 | 0.594 / 0.568 | 0.659 / 0.635 | 0.2116 / 0.2148 | R2–R5, R7 | 0 |
| C-E5C (past-only Platt, last 24) | 0.613 / 0.597 | 0.530 / 0.533 | 0.640 / 0.623 | 0.2224 / 0.2377 | R2–R5, R7 | 0 |

- **Both hypotheses are rejected.** Middle-third LOW recall fell (C-E5R 0.27 / 0.18; C-E5C 0.18) instead of rising.
- **Why:**
  - Down-weighting the long history leaves too few effective rows.
  - Recalibrating on 24 recent quarters over-reacts to swings that do not persist.
- **No further variants were tried.** More attempts on the same 62 quarters would be fitting the noise.
- **Adoption (pre-registered rule): none passes.** C-E2 stays the best development candidate.

## 5. Objective 1: NLP contribution (C-E2-NONEWS ablation, same origins)

| | Lead 1 Brier | Lead 2 Brier | Classifications changed |
|---|---|---|---|
| C-E2 | 0.1875 | 0.1879 | — |
| C-E2 without news (`z_N1R`) | 0.1889 | 0.1890 | **0 of 62** at both leads |

- **The news input improves Brier by 0.0014 / 0.0011.** That is below the pre-registered 0.005 materiality line and
  changes no forecast. H5N is confirmed.
- **Gov-only vs NLP-only vs combined (`out/obj4_table.json`):**
  - LGBM-GOV: Brier 0.233 / 0.240.
  - LGBM-NLP (news era, n 20/19): 0.307 / 0.310.
  - Combined (C-E2): 0.188 / 0.188.
  - The combined model is best, but the gain comes from SWS hunger and the price inputs, not from news.
- **Prior Objective 1 evidence stands (`OBJ1_NLP_RESULTS.md`):**
  - real XLM-RoBERTa inference and the issue-date cut verified;
  - issue-date-safe BERTopic refitted at 19 origins (`out/obj1_topics.json`);
  - topics are not eligible as features;
  - no early-warning value (`out/obj1_earlywarning.json`).
- **Blocker:** the 300-headline human validation set is prepared but **not labelled** (`annotation/`). Relevance,
  sentiment and geocoding accuracy cannot be measured until two team members label it. No labels were generated.

## 6. Objective 3: geospatial outputs (C-E2 demo export)

**Five provinces (live check):**
- 85 rows (17 quarters × 5).
- Score = P × weight on every row.
- Class from P only on every row.
- One regional P per quarter.
- PSA 2023 weights: Quezon 1.000, Rizal 0.812, Laguna 0.783, Batangas 0.710, Cavite 0.623.

**142 LGUs:**
- Quezon 41, Batangas 34, Laguna 30, Cavite 23, Rizal 14.
- No duplicate codes; no missing poverty, population or area.
- Sources: 141 from PSA 2021 SAE, 1 from PSA 2021 Table 2a.
- 25 have CV > 20%.
- Recomputed independently: max difference 0.0 (province) and 1e-16 (LGU) (`OBJ3_SPATIAL_VALIDATION.md`).

**Density question (`runner/obj3_exposure.py` → `out/obj3_exposure.json`; poverty vs density Spearman −0.53):**

| Weighting | Kendall τ vs served | Top-10 mean poverty | Top-10 LGUs below their province's median poverty |
|---|---|---|---|
| Served: poverty 0.6 + density 0.4 | 1.00 | 19.3% | 1 (Lucena) |
| Poverty only | 0.71 | **25.3%** | 0 |
| Poverty 0.6 + poor-people count 0.4 (exposure) | 0.69 | 22.8% | 1 |
| Two separate dimensions (vulnerability rank, exposure rank) | τ between them 0.15 | — | — |

- **Finding:** region-wide, the density term lifts dense LGUs with about 10–12% poverty (Taytay #1, Lipa #2,
  Antipolo, Lucena, Bauan) above rural Quezon LGUs with about 25%. They are poorer than their own province's median,
  except Lucena, but less poor than those Quezon LGUs. Their high ranks come from the density term (min-max within the
  province gives the densest LGU the full 0.4), not from poverty.
- An exposure term (number of poor people) keeps urban exposure while ranking poorer LGUs higher.
- **Adviser decision D3.2** (`OBJ3_DECISION_RECORD.md`): nothing was changed in the served index.
- **Uncertainty:** the median 90% rank interval is 51 places (1,000 Monte Carlo draws over the SAE CVs), so ranks are a
  coarse prioritisation.
- **Labelling:** these are vulnerability-weighted estimates, not measured municipal hunger.

## 7. Objective 4: baselines (identical quarters, labels and leads; `out/obj4_table.json`, `out/ce2_results.json`)

| Lead 1 (62 q) | Accuracy | Balanced | AUC | Brier | C-E2 Brier diff | p (one-sided) | p Holm (14) | Significant |
|---|---|---|---|---|---|---|---|---|
| **C-E2** | **0.774** | 0.690 | 0.715 | **0.1875** | — | — | — | — |
| Persistence | 0.661 | 0.594 | 0.594 | 0.3387 | −0.151 | 0.001 | 0.008 | ✅ |
| LGBM-GOV | 0.677 | 0.562 | 0.535 | 0.2327 | −0.045 | 0.001 | 0.010 | ✅ |
| NLP-only (news era, 20) | 0.450 | 0.478 | 0.390 | 0.3531 | −0.144 | 0.006 | 0.050 | ❌ by the margin |
| Always-high | 0.694 | 0.500 | — | 0.3065 | −0.119 | 0.005 | 0.050 | ❌ by the margin |
| LGBM-NLP (news era, 20) | 0.600 | 0.593 | 0.527 | 0.3069 | −0.097 | 0.017 | 0.102 | ❌ |
| PSA-only | 0.726 | 0.582 | 0.633 | 0.2082 | −0.021 | 0.208 | 0.416 | ❌ |
| LOGIT (combined) | 0.710 | 0.629 | **0.759** | 0.1928 | −0.005 | 0.433 | 0.433 | ❌ |

**Lead 2 (Brier diff, p Holm):**
- Persistence −0.151 (0.006) ✅
- LGBM-GOV −0.052 (0.010) ✅
- NLP-only −0.215 (0.050) ❌
- Always-high −0.119 (0.050) ❌
- PSA-only −0.051 (0.154) ❌
- LOGIT −0.046 (0.263) ❌
- LGBM-NLP −0.090 (0.197) ❌

**C-E2 has the lowest Brier and the highest accuracy of all eight at both leads.** It is significantly better in **4 of
14** comparisons, and it **does not beat all baselines**.

**Why it is not significantly better than LOGIT (prompt §9D):**
- **Sample size (main cause).** At Lead 1 the mean Brier gain is 0.0053 with a per-quarter SD of 0.26. Detecting it at
  p < 0.05 needs about **6,500 quarters**. At Lead 2 (gain 0.046) it needs about **89 quarters**; 62 exist.
- **Shared errors.** Both models are wrong on the same 9 Lead-1 quarters (C-E2 is wrong on 14, LOGIT on 18). The
  squared errors correlate at 0.45. Both are dominated by the latest SWS reading.
- **Ranking:** LOGIT has a higher AUC at Lead 1 (0.759 vs 0.715). It ranks quarters better but is worse calibrated at
  the 0.50 line.
- **Overfitting:** not the cause. Grid averaging is already regularised, and the recency and calibration variants,
  which add flexibility, made things worse.

**Baselines unchanged.** The PSA-only defect in `hr_lib.logit` (`OBJ4_BASELINE_VERIFICATION.md` §2) is still
documented, not fixed: `hr_lib` is shared with sealed evidence, and it changes no conclusion.

## 8. Algorithm 3 (75% rule; accuracy by lead 1..8)

| Model | Accuracy at leads 1..8 | MRLT |
|---|---|---|
| C-b | (sealed record) | 2 |
| C-E2 | 0.774, 0.758, 0.758, 0.645, … | **3** |
| C-E2-NONEWS | 0.774, 0.758, 0.758, 0.645, … | 3 |
| C-E3 / C-E4 / C-E5R / C-E5C | — | 0 / 2 / 0 / 0 |

**Algorithm 4** (2027 holdout) cannot run until 2027 SWS rounds are published, and C-E2 has no sealed forecast.

## 9. Objective 5: backend technical readiness (questionnaire untouched)

| Check | Result |
|---|---|
| Model identification | `/api/v1/final/risk/evaluation` returns model ALLBASE-CE2, plan SHA a1b469da…, MRLT 3, served leads [2] |
| Traceability | Every row carries its issue date, origin, lead, the inputs used and SHAP; the plan hash is in the evaluation |
| Error handling | Unknown quarter or province → 404; invalid scope → 422; no 500 errors in the current log |
| Response time (local) | Config 0.06 s; explainability 0.29–0.33 s |
| Full backend suite | 1017 passed, 18 skipped (§14) |
| **Defect found (not fixed: backend app file outside research scope)** | `/api/v1/config` → `indicator.horizon` and `caveat` hold **fixed C-b text** (MRLT 2, "Lead 1 = that quarter", R7 0.57). In the C-E2 demo they contradict the served evaluation (MRLT 3, Lead 2 only). Fix: build the text from `evaluation.json`; needs your approval |
| Needs evaluator responses | All ISO/IEC 25010 characteristics, and FNRI face validity by DA personnel |
| Needs adviser / stakeholder | Which build the survey evaluates (`OBJ5_EVALUATION_READINESS.md` §1), D3.1/D3.2, adoption of any candidate |

## 10. Multisource contribution (C-E2, mean |SHAP| share, Lead 2)

| Group | Share | Kind | Coverage / limits |
|---|---|---|---|
| SWS hunger (h_last, change, mean4, true_h) | 59.6% | Direct food-insecurity indicator | Balance Luzon only, quarterly since 1998 |
| World prices (Pink Sheet) | 21.1% | Affordability (global) | Monthly; national pass-through |
| Food and headline CPI | 6.0% | Affordability (regional) | PSA Region IV-A |
| Employment (E1) | 3.9% | Socioeconomic | National LFS, not provincial |
| Climate (ONI) | 2.9% | Agricultural stress | National/global |
| Rice prices | 2.7% | Affordability | Regional |
| OFW remittances (E2) | 1.2% | Socioeconomic | National IMF BOP |
| Crops (palay/corn) | 1.2% | Agricultural stress | PSA |
| Fisheries | 1.0% | Fisheries stress | PSA |
| News FSSI | 0.4% | Contextual NLP | 2021 onward only; §5 |

The system stays multisource, but most of its skill comes from persistence of the hunger series plus prices.

## 11–13. Detailed evidence

- **Objective 1:** `OBJ1_NLP_RESULTS.md`, `out/obj1_*.json`, `annotation/`.
- **Objective 3:** `OBJ3_SPATIAL_VALIDATION.md`, `OBJ3_DECISION_RECORD.md`, `out/obj3_*.{json,csv}`.
- **Objective 5:** `OBJ5_*.md`.

## 14. Backend test results

`python -m pytest -q tests` (backend): **1017 passed, 18 skipped**. No regressions.

## 15. Protected-file integrity

- **Before:** `integrity/protected_before_2026-11-04.sha256`, 200 files:
  - C-b seals and `backend/seals/LEDGER.md`;
  - `backend/data/ledger`, all `SEAL_LEDGER.md` files and `SENIOR_REVIEW/prospective`;
  - the C-b export `backend/data/foodinsecurity_engine`, `backend/models` and `ALLBASE/out`;
  - `render.yaml`, `backend/Dockerfile`, every file in `frontend/src`;
  - the thesis PDFs.
- **After:** `integrity/protected_after_check_2026-11-04.txt`. **All 200 match.**
- **Git:** the tracked-file changes are the same set as at the start of the task; none were added.

## 16. Files created or changed by this task

| File | Change |
|---|---|
| `CE5_PREREGISTRATION.md` (829b58d2…) | New; plan hash 2ab41820… |
| `runner/ce5_model.py`, `obj2_diagnostics.py`, `obj3_exposure.py`, `obj4_table.py` | New |
| `runner/ce4_model.py` | Output paths corrected (the C-E3 overwrite) |
| `out/ce5_fits.csv`, `ce5_results.json`, `obj2_diagnostics.json`, `obj3_exposure.json`, `obj4_table.json` | New |
| `out/ce3_*`, `out/ce4_*` | Regenerated / new (deterministic) |
| `out/repro_2026-11-04/` | Copies of the original C-E2 outputs |
| `NEW_MODEL/ALLBASE/REGISTRY.csv` | 14 rows appended (backup in `backup/`) |
| `integrity/` | Hash manifest and check |

**Earlier today (previous requests; listed for completeness):**
- `runner/export_ce2.py`;
- `backend/data/foodinsecurity_engine_ce2/`;
- `backend/app/ml/inference/foodinsecurity_system.py` ("relative" driver view);
- `backend/app/schemas/public.py` (`probabilityPricePressure` optional; backup in `backup/frontend_2026-11-03/`).

## 17. Objective completion matrix

| Objective | Implemented and tested | Exact evidence | Status |
|---|---|---|---|
| 1. NLP | XLM-RoBERTa outputs verified; issue-date-safe BERTopic at 19 origins; FSSI in C-E2; ablation | Brier gain 0.0014 / 0.0011, 0 calls changed; topics NPMI too low to use | **Partial.** Blocker: human labels for the 300 headlines; the NLP signal has no material predictive value |
| 2. Forecasting | Walk-forward LightGBM, all metrics, R1–R7, Algorithm 3; diagnosis; 2 pre-registered fixes | C-E2 acc 0.774 / 0.758, AUC 0.715 / 0.694, Brier 0.188 / 0.188, MRLT 3; fails R3, R7 | **Completed** as an evaluation (MRLT found). R3/R7 remain limitations: regime change and survey noise |
| 3. Geospatial | 5 provinces and 142 LGUs recomputed; sensitivity; exposure alternative; Monte Carlo | Max diff 0; 142/142 complete; τ 0.69–0.71 for alternatives; 90% rank width 51 | **Completed.** The weighting choice (D3.2) is the adviser's |
| 4. Baselines | All 7 + CLIM on identical quarters; paired Brier, bootstrap, Holm; LOGIT gap analysis | Best Brier and accuracy of all; significant 4/14; vs LOGIT p 0.43 / 0.26 | **Partial.** Comparison complete; "beats all" not supported. Needs about 89 quarters at Lead 2, or prospective 2027 evidence |
| 5. System | Backend readiness checks, 1017 tests | §9 | **Backend completed; evaluation pending** (questionnaire ongoing). One config-text defect awaits approval |

## Recommended next steps (each needs your approval)

1. **Fix `/api/v1/config`** so the horizon and caveat text come from the served `evaluation.json`. Small backend app
   change, plus a test.
2. **Seal C-E2's 2027-Q1 forecast** in the prospective registry before 15 Jan 2027. Algorithm 4 is the only route to
   evidence the panel cannot call "examined during development". This touches the seal ledger.
3. **Team labels the 300 headlines** (`annotation/ANNOTATION_GUIDE.md`) to complete Objective 1's NLP accuracy.
4. **Adviser decides D3.2.** The evidence favours poverty-only or poverty + poor-people exposure over density.
5. **Thesis wording for Objective 4:** "C-E2 had the lowest Brier score and highest accuracy of all baselines at both
   leads, and was significantly better than persistence and the government-data LightGBM after Holm correction; the
   differences from logistic regression, PSA-only, always-high and the news-only models were not significant with 62
   quarters."

# FINAL-ETMIX: verified implementation and root causes of its weaknesses (Part 3)

## 1. What FINAL-ETMIX is (verified in code and by exact re-runs, 2026-11-13)

| Element | Implementation | Verified how |
|---|---|---|
| Base fit | FINAL (RATE + MIND): research `aiPHeed_hcw_final_optimization_20261112/scripts/engine_final.py`, `fit_predict(..., rate="lin", miss="mind", cw="balanced")`; backend port `aipheed_hcw/backend/app/hcw/final_engine.py` | 110/110 fits refitted in this study reproduce the stored FINAL and FINAL-ET probabilities to < 1e-15. The backend port reproduces the sealed mixture to < 1e-9 (`tests/unit/test_etmix.py`) |
| Target | y = logit(HFIAS moderate + severe share); HIGH when ≥ 50 %; q = Φ(y ÷ SE) carries survey error | Code |
| Survey anchor | H / OH / RSS: national level of the **latest released** round + shrunk provincial deviation; chosen per fit by inner error. Rounds usable 6 quarters after their reference quarter | Code; `stale_q` test |
| RATE | Model learns (y − anchor) ÷ (g ÷ g₀); forecast = anchor + (g ÷ g₀) × rate | Code |
| Elapsed-time mixture | Same fitted model predicts each row with g = own-survey gap and with s = quarters since the latest released round; p = ½(p_g + p_s); HIGH at 0.50 | `scripts/contrib_jobs.py`; `app/hcw/etmix.py` |
| Missing data (MIND) | Training-median fill + 0/1 missing flag for inputs with gaps in training | Code |
| Inputs | 77 candidates (4 feature sets). Inside each fit: top 25 by \|Spearman\| with the training residual, pruned at ρ > 0.95. Fixed monotone signs. Fish and remittance families dropped by design | `FINAL_ETMIX_INPUT_FEATURE_AUDIT.md` |
| Selection, hyperparameters, calibration | Inner GroupKFold by region on training rows only: 3 anchors × 4 feature sets × 16 settings; calibration raw / linear / Platt by inner Brier (raw chosen in every fit) | Code; fit metadata `parts/META__*.json` |
| Origin availability | Training outcomes released by the origin only; inputs as of the origin (as-of price centring); news windows close before the issue date | Existing leakage tests; `train_gap_equals_staleness` = true in all 110 fits |
| Sealed forecasts | ENNS 2022, 78 provinces, Leads 1–2, sha256 `71ebe142` | Hash re-verified; unchanged |

**Documentation versus code.**
- **Naming:** "FINAL-MIX" in the locked protocol and seal JSON is FINAL-ETMIX. It is distinct from the 11-12 anchor-averaging FINAL-MIX.
- **Old docstring:** the backend `final_engine.py` docstring says FINAL "fails rules 3 and 4". That refers to the 11-12 forward-fold protocol; the later standalone protocol gives 6/7. It is a historical statement, kept unchanged.

## 2. Survey-anchor and elapsed-time logic

| Question | Finding | Evidence |
|---|---|---|
| Are training and inference temporally consistent? | In **every training row**, g = s: each training province's own survey is also the latest released round | All 110 fits (`train_gap_equals_staleness`); `../aiPHeed_final_stability_lead_20261113/evidence/D4_gap_vs_staleness_by_fold_lead.csv` |
| Where do g and s differ? | Only in 2021 test rows at Leads 1–6: g = 24 versus s = 8 (Leads 1–2) or 12 (Leads 3–6). Also in the live issue: g = 22–34 versus s = 22 for CALABARZON | D4; live artifact |
| Is elapsed time double-counted? | **Under hypothesis g, yes.** The anchor is refreshed to the latest round (which already contains the national change), and RATE then multiplies by the full own-survey gap. Under s, no. ETMIX averages the two, halving the possible double count | `../aiPHeed_final_standalone_20261113` (2021 high anchors projected −23.6 points versus −9.4 in training) |
| Can the data choose between g and s? | **No.** g = s in all training rows, so no training-only procedure can identify the right one. The equal mixture is the non-informative treatment. It was not tuned on outcomes, but it was **designed after seeing** both components' results (disclosed in the protocol) | Protocol `a365da1f` §1–2 |
| Long gaps | Test gaps (12 / 16 / 24) always exceed the longest gap seen in that fold's training (8 / 8 / 20). The live issue is worse: g up to 34 quarters (Laguna, last surveyed 2018) | D4; live rows |
| Does spread widen with the gap? | Only through the residual-scale regression on training gaps. It cannot be tested beyond the trained range | D5 |

## 3. Why HIGH provinces are missed or falsely flagged (Lead 1: 4 misses, 6 false alarms)

| Cause | Rows | Evidence | Fixable now? |
|---|---|---|---|
| **C1 Unobserved shocks.** Marawi displacement (about 140,000 people, 2017) is not a model input | Lanao del Norte 2019 (p 0.32) | `../aiPHeed_final_rootcause_20261113` | Only prospectively. A DROMIC displacement series needs compiling and owner approval |
| **C2 Borderline outcome / survey noise.** The observed value lies within 1 SE of 50 %; 38 of 72 anchors lie within 1.96 SE of the line | Misamis Oriental 2019 (54.8 %, p 0.38) | Survey-data report | No. Irreducible label noise (about 3.6 of 72 labels expected wrong) |
| **C3 Stale anchors with province-specific trends.** Masbate and Occidental Mindoro (2015 anchors 65–68 %) fell only 7–10 points while their peers fell 18–34; no input separates them | Masbate, Occ. Mindoro 2021 (p 0.26, 0.30) | Root-cause 11-13 | No genuine provincial input found |
| **C4 Round-level national trend not visible at the origin.** 2015→2018 fell faster than any training transition: mean p 0.55 versus rate 0.36 in 2018 | Camarines Norte, Iloilo, Sorsogon 2018 | `evidence/ETMIX_lead_results.json` (by round) | No input available at the origin carries it (SWS hunger was tested on 11-11, no gain) |
| **C5 Weak provincial differentiation among high-anchor provinces.** Raising one 2021 HIGH lifts LOW neighbours too | Quirino, S. Leyte 2019; Sarangani 2021 | 2021 AUROC 0.87 | Structural |
| **C6 Regional rather than provincial information.** The largest learned driver (regional GRDP relative to the national mean) is identical for every province of a region. It explains **between-region** differences, not within-region ones | All | `FINAL_ETMIX_CONTRIBUTOR_IMPORTANCE_REPORT.md` | Provincial GRDP is not published by PSA for these years |
| **C7 Small sample.** 25 HIGH in total, 4 in 2021: one province moves 2021 recall by 0.25 | 2021 verdicts | Training perturbation 0.25–1.00 | Only more survey rounds |

**What ETMIX changes relative to FINAL (Lead 1):**
- It recovers Agusan del Sur 2021 (FINAL 0.41 → ETMIX 0.54).
- It adds one false alarm, Sarangani (0.44 → 0.55).
- It has no effect outside 2021 Leads 1–6.
- Net retrospective effect: HIGH recall 0.80 → 0.84, precision 0.80 → 0.78, Brier +0.004 (n.s.).

## 4. Probability reliability (supplementary)
- **Ranking.** Probabilities rank risk well: AUC 0.90 at Lead 1; no HIGH below p 0.2; all 7 rows above 0.9 are HIGH.
- **Calibration.** Consistent with calibration at n = 72 (ECE 0.11 below the null 95 % limit of 0.16; Cox p = 0.10). Mean over-prediction is +0.07, driven by 2018.
- **Threshold.** Classification is stable for cut-offs 0.45–0.60.
- **Interpretation.** Probabilities support a relative-risk reading with a 0.5 decision rule. They should not be read as precise absolute probabilities.

## 5. Temporal and geographic consistency
- **Across rounds (Lead 1):** accuracy 0.86 / 0.84 / 0.88; balanced accuracy 0.89 / 0.84 / **0.73** (2021 is the weak round).
- **Across leads:** stable to Lead 4, deteriorating from Lead 5.
- **Across provinces:** 62 of 72 province-rounds are classified correctly at Lead 1. 47 of 72 are correct at every lead they have. Errors concentrate in Mindanao conflict-affected areas (2019) and in Bicol / MIMAROPA stale-anchor provinces (2021) (`evidence/ETMIX_province_by_lead.csv`).
- **CALABARZON:** all 5 province-rounds are correct at every lead (all LOW).

## 6. What was corrected in this study, and what was not
- **Corrected:**
  - The contributor evidence, now computed for ETMIX itself (two hypotheses, five seeds, exact SHAP, permutation, withholding, retraining).
  - Input geography labels for the 17 added inputs, which were blank in the 7-of-7 inventory.
  - A backend implementation of ETMIX with exact explanations (`app/hcw/etmix.py`).
- **Not changed:** the model. No weakness was found that can be fixed with genuine data available at the origin without tuning on the 72 reused outcomes (`FINAL_ETMIX_OPTIMIZATION_REPORT.md`).

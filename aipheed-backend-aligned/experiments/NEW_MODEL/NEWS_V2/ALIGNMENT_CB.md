# C-b against the five objectives, RQ1–RQ5 and H1–H5

**Written:** 2026-11-03. C-b is exactly as in `PLAN.md`: no tuning, no new candidate, no production or frontend change.

**Status:** not committed (no authorization). Development evidence throughout.

**Correction (same day, on re-check).** The first version of this table marked Objectives 1, 2 and 3 as met. That
overstated them. The re-check found:
- **C-b is effectively REF.** Its probability equals REF's in 66 of 67 quarters at each lead (max |Δp| 0.005), and 0
  calls differ. The FSSI input is in the model, but it changes nothing.
- **Objective 1** is recorded as *partially achieved* in `OBJECTIVES_COMPLETION/OBJ1_NLP_PIPELINE.md`.
- **Objective 2's acceptance step (Algorithm 4: F1 ≥ 0.75 and AUC ≥ 0.80 on a blind holdout) is not met.** It is
  untestable until 2027, and the development AUC is 0.70.
- **Objective 3 asks for *validated* province-level forecasts.** C-b is validated only under Algorithm 3 and is
  regional.

The table below is corrected accordingly.

**New evidence produced for this alignment** (`runner/align_cb.py`):
- the full SHAP of C-b (the refit equals the stored C-b, max |Δp| = 1.1e-16);
- the Objective 4 / H3 comparisons with Holm;
- the province and LGU outputs for the 2026-10-01 issue;
- a seal of C-b's 2026-10-01 forecasts;
- a prospective protocol addendum (`PROSPECTIVE_ADDENDUM_CB.md`, SHA-256 `fc110575…966c`), effective on adoption.

## 1. Objective by objective

| Objective | What the paper asks | C-b evidence | Status |
|---|---|---|---|
| **Focus** | Forecast food insecurity, not prices | Target: SWS BL involuntary hunger > 11.3% (a direct food-insecurity measure). Prices, production, climate and news are predictors only | **Met** |
| **1 NLP** | Two-tier pipeline (zero-shot XLM-RoBERTa Filipino-English + BERTopic) producing the bias-corrected FSSI and latent risk patterns **per province-quarter** | The pipeline exists end to end and produces both outputs per province-quarter (`OBJECTIVES_COMPLETION/OBJ1_NLP_PIPELINE.md`: 9,667 headlines, 695 relevant, FSSI-v3 with bias weight, BERTopic). **C-b uses the paper's FSSI** as its news input (as an anomaly, which removes corpus-growth drift). Its SHAP share is **0.0–0.1%** | **Partially achieved.** The pipeline and its outputs exist, but province-quarter coverage is thin (17% of province-quarters have ≥ 5 tagged articles), and the FSSI input makes **no difference** to C-b's forecasts (identical to REF in 66 of 67 quarters) |
| **2 I–IV** | Accuracy, precision/recall, F1, AUC | Lead 1 and Lead 2 each: accuracy **0.790**, precision 0.812, recall 0.907, F1 **0.857**, AUC 0.702 / 0.704, Brier 0.187 / 0.184 (62 quarters) | **Met** (measured and reported for both leads) |
| **2 V** | Walk-forward, Maximum Reliable Lead Time (Algorithm 3) | Leads 1–8 accuracy 0.790, 0.790, 0.726, … → **MRLT = 2** (Lead 1 and Lead 2 pass the 75% rule) | **Met** under the paper's rule. The project's stricter R1–R7: **R7 fails at both leads** (2015–2020 third 12/21). C-b was chosen after seeing development results, which favours it |
| Algorithm 4 | Blind holdout F1 ≥ 0.75, AUC ≥ 0.80 | The paper's holdout quarters were examined before, so not blind. Addendum CB fixes the first four sealed 2027 quarters as the blind holdout | **Not met / untestable now.** Earliest test about 2028; the development AUC (0.70) is already below 0.80 |
| **3** | Province-level forecasts → LGU rankings (poverty 60%, density 40%) | 2026-10-01 issue: regional P 0.8595 HIGH. Province scores (poverty-weighted): Quezon 0.860, Rizal 0.698, Laguna 0.673, Batangas 0.610, Cavite 0.536. **142 LGU ranks** by 0.6 × poverty + 0.4 × density within province × province score, each labelled "vulnerability-weighted, not a measured municipal rate" (`out/cb_lgu_2026-10-01.csv`) | **Partially, and only with the Option C wording.** The outputs exist and are labelled. But the forecast is regional (SWS has no provincial data), and it is "validated" only under Algorithm 3: it fails R7 and Algorithm 4 is untested. As written, the paper's Rule 4 / §3.4.4 would not allow the LGU rankings to be published as validated |
| **4** | Proposed model vs persistence, PSA-only, NLP-only, logistic regression | See §2 | **Met** (compared). C-b is significantly better than persistence and NLP-only at both leads, **not** than PSA-only or LOGIT |
| **5** | Dashboard, maps, SHAP, early warning, human review; ISO/IEC 25010 by DA; FNRI face validity | Backend modes, Rule 1 (staging), Rule 7 (staged alerts) and FNRI 2023 (19.1%) exist. **The served food-insecurity mode runs REF+news, not C-b**: switching needs a backend export change (not done, your approval). ISO/IEC 25010 needs the 50 DA evaluators | **Partly**: one backend switch (yours to approve) and the evaluation (respondents) remain |

## 2. Objective 4 and H3 (Brier: C-b minus the comparator; Holm within each table and lead; one-sided cluster bootstrap)

| Comparator | Lead 1 diff (Holm p) | Lead 2 diff (Holm p) |
|---|---|---|
| Naive persistence | **−0.151 (0.001)** | **−0.155 (0.001)** |
| PSA-only (logistic) | −0.021 (0.510) | −0.055 (0.079) |
| NLP-only (logistic; news era) | **−0.153 (0.008)** | **−0.228 (0.014)** |
| Logistic regression (combined) | −0.005 (0.510) | −0.050 (0.079) |
| Always-HIGH | **−0.119 (0.028)** | **−0.123 (0.023)** |
| *H3 extra:* LightGBM government-only | **−0.045 (0.014)** | **−0.056 (0.010)** |
| *H3 extra:* LightGBM NLP-only (news era) | **−0.107 (0.014)** | −0.103 (0.061) |

**H3 is not rejected.** C-b is not significantly better than all six (the logistic regressions remain). It beats more
comparators than REF+news did, which never beat the government-only LightGBM.

## 3. RQ1–RQ5 and H1–H5

| | C-b answer | Status |
|---|---|---|
| **RQ1 / H1** strongest predictors (SHAP) | Hunger history 64.7%, world prices 22.4%, food and headline prices 6.3%, rice 2.8%, ONI 2.0%, crops and fisheries about 1% each, typhoons 0.1%, **news (FSSI) 0.0%**. The hunger share falls from 80% (2010–15) to 49% (2021–26) as world prices rise | Answered; **H1 not rejected** (neither FSSI nor food CPI deviation is among the strongest) |
| **RQ2 / H2** reliable lead time | 2 quarters (Algorithm 3); 0 under R1–R7 | Answered; **H2 rejected** under the paper's rule, not under R1–R7 |
| **RQ3 / H3** vs six comparators | §2 | Answered; **H3 not rejected** |
| RQ4 / H4 LGU rankings vs DA evaluators | Rankings produced and labelled; CBMS 2024 could add a measured check | **Waiting for DA evaluators** |
| RQ5 / H5 ISO/IEC 25010 | — | **Waiting for respondents** |

## 4. What cannot be made "aligned" by code, and why

| Gap | Why no code can close it | Who closes it |
|---|---|---|
| Province-level **measured** food insecurity | SWS reports Balance Luzon only; no provincial hunger series exists. Copying the regional value and calling it provincial would be fabrication | Adviser: approve the Option C wording (CH3_AMENDMENT §2.1 / §9.1) |
| NLP improving the forecast | Tested in four constructions (REF+news, C-a, C-b, GDELT): none adds measurable value | Report it honestly as an evaluated, negative result. That is still a valid answer to Objective 1 and RQ1 |
| R7 at both leads | The 2015–2020 hunger readings sit within SWS's sampling error of the line | The prospective record (40 quarters, about 2037) |
| Blind holdout F1/AUC | No unseen quarters exist before 2027 | The sealed 2027 quarters (about 2028) |
| ISO/IEC 25010, RQ4/H4 | Needs DA evaluators | Data collection |

## 5. Done on 2026-11-03 (your instruction: "make C-b the main model")

- **Adoption recorded.** `PAPER_ALIGNED/CH3_AMENDMENT.md` top section: the team decision, pending adviser confirmation.
- **Backend (Objective 5).** The `foodinsecurity` mode now serves C-b (`FOOD_INSECURITY_SYSTEM/PLAN.md` revision 4,
  SHA-256 `fba5236e…f090`): served texts state the NLP input's zero effect; mode tests 27/27; full suite 1014 passed,
  18 skipped. The FIRI v2 default and the frontend are unchanged.
- **Prospective scripts.** C-b is the main model, and REF+news and REF are sealed beside it. The C-b and OPTION_1 seals
  are verified by reference. The sealing replay reproduces C-b exactly from the rebuilt inputs (Δp = 0.0); the dry-run
  harness passes 11/11. New script hashes are appended to `SENIOR_REVIEW/prospective/SEAL_LEDGER.md`.
- **Still open:** the adviser's confirmation; the 2027 blind holdout; the ISO/IEC 25010 respondents; provincial data
  (does not exist).

## 5a. Original to-do list (kept for the record)

1. **Adoption.** The team and adviser adopt C-b as the main model. It did not pass the fixed "improvement" rule at
   Lead 1, so this is a recorded decision, not a test result.
2. **Commit.** Authorize committing NEW_MODEL, including the C-b seal and Addendum CB.
3. **Backend switch (Objective 5).** Export C-b instead of REF+news in the non-default `foodinsecurity` mode.
   - No frontend change and no change to the default (FIRI v2).
   - The same Option C display, with every C-b text field updated (news share about 0%).
   - Tests and the full suite.
4. **Prospective scripts.** Add C-b to the prospective scripts before 2027-01-01 (Addendum CB).
5. **Adviser wording.** The Chapter I/III Option C amendments and the open paper contradictions.

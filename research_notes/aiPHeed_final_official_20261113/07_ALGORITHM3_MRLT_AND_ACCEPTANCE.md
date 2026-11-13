# 07 — Thesis Algorithm 3: maximum reliable lead time, Leads 1–8 (deliverables 9, 10, 11; candidate comparison = deliverable 7 of the brief's list)

Script: `scripts/algorithm3.py`, which uses the existing 110 walk-forward fits with no refit and the threshold fixed at 0.50.
Evidence: `evidence/A3_leads.csv`, `A3_folds.csv`, `A3_mrlt.json`.

**Rule:** the rule is applied as the thesis states it (THESIS 2, Chapter III Section 3.4, Algorithm 3; transcribed in `aipheed_e145/docs/final/THESIS_MRLT_EVIDENCE_E168.md`):
- walk-forward expanding window;
- forecast gap = k quarters;
- at least 8 training quarters;
- mean fold accuracy ≥ 75 %;
- stop at the first failing k.

The G1–G9 framework is **not** used here.

## 1. How the procedure maps to the data
- **Folds:** a fold is a survey round. Food-insecurity outcomes exist only when FNRI measured a province, and no quarterly labels are manufactured.
- **Fold contents:**
  - Fold 2018: trained on FNRI 2015; 22 test provinces.
  - Fold 2019: trained on FNRI 2015 (ENNS 2018 was not yet released at the origin); 25 provinces.
  - Fold 2021: trained on 2015 + 2018 + 2019 at Leads 1–2, and on 2015 + 2018 at Leads 3–6 (2019 not yet released); 25 provinces.
  - At Leads 7–8 the 2018 fold cannot exist (it would need an origin before the 2015 release), so 2 folds remain.
- **Expanding window:** each later origin adds every round released by then.
- **Gap:** the origin is k quarters before the survey reference quarter (Q3).
- **Minimum 8 quarters:** the HFIAS history at the origin (from NNS 2013 Q3) is 14–31 quarters in every fold (`A3_folds.csv`).
- **Leakage check:** 0 violations in 110 fits (`aiPHeed_final_reliability_20261113/evidence/LEAK_origin_check.json`).

## 2. MRLT table

| Lead | Fold 2018 | Fold 2019 | Fold 2021 | Mean fold accuracy | ≥ 75 % | Result |
|---|---|---|---|---|---|---|
| 1 | 86.4 % | 84.0 % | 88.0 % | **86.1 %** | yes | PASS |
| 2 | 81.8 % | 84.0 % | 88.0 % | **84.6 %** | yes | PASS |
| 3 | 81.8 % | 80.0 % | 84.0 % | **81.9 %** | yes | PASS |
| 4 | 81.8 % | 84.0 % | 80.0 % | **81.9 %** | yes | PASS |
| 5 | 77.3 % | 80.0 % | 80.0 % | **79.1 %** | yes | PASS |
| 6 | 68.2 % | 76.0 % | 80.0 % | **74.7 %** | no | **FAIL: first failing horizon** |
| 7 | — | 72.0 % | 68.0 % | 70.0 % | no | FAIL (not reached by Algorithm 3) |
| 8 | — | 80.0 % | 68.0 % | 74.0 % | no | FAIL (not reached) |

- Passing / failing folds by lead: L1–L5 3/0; L6 2/1; L7 0/2; L8 1/1.
- **First failing horizon: Lead 6.**
- **Maximum Reliable Lead Time = 5 quarters.**
- Persistence's mean fold accuracy is 62.4 % at Leads 1–6.

**Why accuracy falls at longer horizons:**
- Fewer rounds are released at earlier origins: 2021 Leads 3–6 lose the 2019 round, and Leads 7–8 lose 2018 as well.
- Longer extrapolation of the time term.
- Older input values.
- The 2018 fold drops to 68.2 % at Lead 6.

## 3. Algorithm 4 acceptance targets (F1 ≥ 0.75, AUC-ROC ≥ 0.80) at every lead

| Lead | Pooled accuracy | Precision (HIGH) | Recall (HIGH) | F1 (HIGH) | F1 ≥ 0.75 | Weighted F1 | Macro F1 | AUC-ROC | AUC ≥ 0.80 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.861 | 0.800 | 0.80 | **0.800** | PASS | 0.861 | 0.847 | 0.898 | PASS |
| 2 | 0.847 | 0.769 | 0.80 | **0.784** | PASS | 0.848 | 0.833 | 0.899 | PASS |
| 3 | 0.819 | 0.731 | 0.76 | **0.745** | **FAIL** | 0.820 | 0.803 | 0.883 | PASS |
| 4 | 0.819 | 0.714 | 0.80 | **0.755** | PASS | 0.822 | 0.806 | 0.885 | PASS |
| 5 | 0.792 | 0.679 | 0.76 | **0.717** | **FAIL** | 0.794 | 0.776 | 0.874 | PASS |
| 6 | 0.750 | 0.630 | 0.68 | 0.654 | FAIL | 0.752 | 0.729 | 0.866 | PASS |
| 7 | 0.700 | 0.545 | 0.71 | 0.615 | FAIL | 0.707 | 0.685 | 0.815 | PASS |
| 8 | 0.740 | 0.583 | 0.82 | 0.683 | FAIL | 0.747 | 0.731 | 0.818 | PASS |

**One-quarter-ahead (Lead 1):** meets every thesis target: mean fold accuracy 86.1 %, F1 0.800 and AUC 0.898.

**Discrepancy, reported as the brief requires:**
- The accuracy rule gives MRLT = 5.
- But F1 (HIGH) misses 0.75 at Lead 3 (0.745, one province short) and at Lead 5 (0.717).
- Section 3.4.4 says a lead or configuration that does not clear these thresholds is not published.
- **Leads 1–2 are therefore the longest contiguous span clearing all thesis targets.** Lead 4 also clears them, but sits after the Lead-3 failure.
- **Recommendation:** publish Leads 1–2 as the operational horizon; state MRLT = 5 as the Objective 3 result; mark Leads 3–5 as accuracy-reliable but below the F1 target. This is the owner's decision (see report 01).

## 4. Why Lead 3 passed the supplementary G1–G9 gates while Leads 1, 2, 4 and 5 did not
- At Lead 3 the 2021 fold is trained on 2015 + 2018 only, a different training composition from Leads 1–2. One more 2021 HIGH province crosses 0.50 (2/4, against 1/4 at the other leads).
- The difference is **one province**, and the supplementary gate's per-round recall ≥ 0.50 rule turns on it.
- That does not make Lead 3 a better horizon. Its F1 (0.745) is below the thesis target.

## 5. Candidate comparison (stored predictions of the candidates already locked on 11-13; none fitted or scored anew)

| Model | MRLT (Algorithm 3) | L1 mean fold acc | L1 F1 | L1 AUC | L1 2021 recall | L1 Brier | Weakness addressed | Trade-off |
|---|---|---|---|---|---|---|---|---|
| **FINAL** | **5** | 86.1 % | 0.800 | 0.898 | 1/4 | 0.123 | — | — |
| FINAL-ETMIX (protocol `a365da1f`) | 5 | 86.1 % | 0.808 | 0.903 | 2/4 | 0.127 | Long-gap time term (averages own-gap and since-latest-round) | Brier worse; F1 also fails at L3/L5; L2 2021 1/4 |
| FINAL-ET (protocol `c5e76bd5`) | ≥ 3 (L1–3 stored) | 82.1 % | 0.764 | 0.904 | 2/4 | 0.137 | Same | 2021 accuracy 76 % (4 new false alarms); calibration failed (11-13) |
| FINAL-SA (PROTOCOL_SA `15202d27`) | ≥ 3 (L1–3 stored) | 81.6 % | 0.772 | 0.909 | 1/4 | 0.132 | Caps RATE at the longest training gap | 2018 fold 72.7 %; precision 0.69 |

Source: `evidence/CAND_algorithm3_by_lead.csv`.

**Decision:**
- No candidate improves the thesis metrics consistently, and each was designed after seeing these 72 outcomes.
- **FINAL is kept unchanged.**
- Testing a long-gap correction properly needs a protocol locked before the next survey round, with the result scored prospectively.

## 6. Addendum (2026-11-13): Lead-3 F1 investigation
- **Cause:** the Lead-3 F1 shortfall (0.745) comes from provinces at the 0.50 line, sitting on a seasonal farmgate-price data gap that affects only 1 October origins.
- **Correction tested:** a pre-registered one-quarter carry-forward (`../aiPHeed_final_lead3_cf_20261113/PROTOCOL_CF.md`, sha `054239a1`).
- **Effect on Lead 3:** F1 is unchanged at 0.745.
- **Side effects:** Lead 4 F1 falls to 0.741, Lead 5 accuracy falls to 75.9 %, and Brier gets worse.
- **Decision:** not adopted. MRLT stays 5; Leads 1–2 remain the publishable span. See `RESULT_CF.md`.

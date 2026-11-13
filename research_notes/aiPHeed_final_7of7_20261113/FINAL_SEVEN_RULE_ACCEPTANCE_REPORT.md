# Seven standalone rules (PROTOCOL_SA, sha 15202d27, unchanged): acceptance status

## Status definitions
- **PASS:** established by admissible evidence: checks that do not depend on reused outcomes, or results on reused rows for a model fixed before those rows were scored.
- **FAIL:** established failure.
- **INSUFFICIENT EVIDENCE:** the only evidence is inadmissible (a model designed after its components' results on these rows were known), or the sample cannot establish the rule.

**Lead 1 is primary.** Numbers are the five-seed mean on the 72 reused province-rounds (25 HIGH, 47 LOW). Rule 6 is applied in its locked n < 600 form; the originally proposed form (ECE ≤ 0.05, slope 0.80–1.20, logit intercept within ±0.10) fails for every model and is untestable at n = 72.

| Rule | FINAL | FINAL-SA | FINAL-ET | **FINAL-ETMIX (latest candidate)** |
|---|---|---|---|---|
| 1 Data integrity | PASS (10/10 checks) | PASS | PASS | **PASS**: same rows and inputs; the mixture reads no outcome |
| 2 Forecast validity | PASS | PASS | PASS | **PASS**: origin, target, release and RATE/MIND checks; s uses the release rule only |
| 3 Balanced accuracy / AUROC ≥ 0.70 | PASS 0.847 / 0.898 | PASS 0.822 / 0.908 | PASS 0.824 / 0.904 | **INSUFFICIENT EVIDENCE.** Retrospective 0.856 [0.76, 0.94] / 0.903 |
| 4 HIGH recall ≥ 0.80 | PASS 0.80 (20/25) | PASS 0.92 | PASS 0.84 | **INSUFFICIENT EVIDENCE.** Retrospective 0.84 [0.68, 0.96] |
| 5 Precision ≥ 0.60 | PASS 0.80 | PASS 0.64 | PASS 0.70 | **INSUFFICIENT EVIDENCE.** Retrospective 0.78 [0.61, 0.93] |
| 6 Probability reliability | PASS (ECE 0.080 ≤ 0.152; +0.046; Cox 0.41) | FAIL (Cox 0.036) | FAIL (+0.103; Cox 0.031) | **INSUFFICIENT EVIDENCE.** Retrospective ECE 0.111 ≤ 0.162; mean p − rate +0.074; Cox p 0.104; BSS 0.57 |
| 7 Stability and reproducibility | FAIL (2021 recall 1/4) | PASS | PASS | **INSUFFICIENT EVIDENCE.** Retrospective: rounds 0.89 / 0.84 / 0.73 balanced accuracy, recall 1.00 / 0.85 / 0.50; worst seed 0.836; reproducible (deterministic combination of verified fits). 7e/7g inherited from FINAL and FINAL-ET (no severe change) |
| **Verdict** | **6 of 7: REJECTED** | **6 of 7: REJECTED** | **6 of 7: REJECTED** | **2 PASS, 5 INSUFFICIENT EVIDENCE: NOT ACCEPTED; gate UNVERIFIED** |

## Why FINAL-ETMIX is not marked PASS on Rules 3–7
1. **It was designed after its components were scored.** The protocol (`FINAL_7_OF_7_IMPROVEMENT_PROTOCOL.md`, sha `a365da1f`) records, before computing, the prediction that it would pass retrospectively. A retrospective pass is therefore expected by construction and tests nothing.
2. **The rows are reused.** About 45 configurations of this lineage have now been examined on them.
3. **The sample cannot establish Rule 7c robustly.** The 2021 round has 4 HIGH provinces, and a 90 % training subsample moves its recall between 0.25 and 1.00 (`../aiPHeed_final_stability_lead_20261113/evidence/R7_et_sensitivity.json`).
4. **Rule 6 has low power at n = 72.** A perfectly calibrated model has a median ECE of 0.11. A pass means only "no evidence of miscalibration".

## What turns INSUFFICIENT EVIDENCE into PASS or FAIL
- **Score the sealed ENNS 2022 forecasts** (`evidence/sealed_enns2022_final_mix.json`, sha `71ebe142`; 78 provinces, Leads 1–2) against the round's provincial HFIAS once obtained. Apply Rules 3–7 exactly as locked.
- **Size of that test:** 53 of the 78 provinces are stale-anchor cases, the exact condition FINAL-ETMIX was built for. FINAL and FINAL-ETMIX disagree on 3 Lead 1 classes; FINAL-ET disagrees on more.
- **If ENNS 2022 stays unobtainable:** the same code forecasts the next provincial HFIAS round from its own origin. Seal it before release; the protocol and code hashes fix the method.

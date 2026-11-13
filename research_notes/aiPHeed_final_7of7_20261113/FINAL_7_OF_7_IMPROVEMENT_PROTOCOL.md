# FINAL 7-of-7 improvement protocol (locked 2026-11-13, before the candidate below is computed)

**Acceptance rules:** PROTOCOL_SA (`../aiPHeed_final_standalone_20261113/PROTOCOL_SA.md`, sha `15202d27`), **unchanged**. Rule 6 is applied in its locked n < 600 form; the originally proposed form is also reported. The decision mapping is unchanged.

**Preserved and not modified:** FINAL, FINAL-SA, FINAL-ET, E196, all seals and earlier reports.

## 1. Why a new candidate cannot be validated on the 72 rows

Evidence: `evidence/C1_round_calibration_by_arm.csv` and the earlier reports.

**Every arm over-predicts the 2018 round by about +0.19** (mean probability minus HIGH rate). The 2018 fold trains only on the slow 2013→2015 change, while 2015→2018 fell fast. Calibration in the large passes pooled only if 2021 does not over-predict as well.

**In 2021 the model cannot rank the high-anchor provinces well enough** (2021 AUROC 0.86–0.88). Any change that catches a second 2021 HIGH province lifts LOW provinces too:

| Model | 2021 mean p − rate | 2021 HIGH recall | Pooled calibration |
|---|---|---|---|
| FINAL | −0.006 | 1/4 | Pass |
| FINAL-ET | +0.156 | 2/4 | Fail |

**The elapsed time RATE should use for stale anchors cannot be learned from training rows.** Every training province's own survey is also the latest released round (`../aiPHeed_final_stability_lead_20261113/evidence/D4_*`). Two hypotheses therefore fit the training data equally well:
- **(g) own-survey gap:** FINAL;
- **(s) time since the latest released round:** FINAL-ET.

**The obvious information sources are exhausted.** Genuine trend information available at the origin (SWS regional hunger) was already tested on these rows on 11 November and did not help. No untried genuine provincial source exists for the gap (`FINAL_FIVE_TRIGGER_GROUP_AUDIT.md`).

**Consequence.** Any new candidate is a function of information whose effect on these 72 rows is already known. **Its retrospective score cannot count as acceptance evidence, whatever it is.**

## 2. Candidate FINAL-MIX (the only candidate)

### Rule
Equal-weight mixture of the predictive distributions under the two elapsed-time hypotheses:

> p_MIX = ½ · p(g) + ½ · p(s)

- p(g) is FINAL's probability; p(s) is FINAL-ET's (same fitted model, test elapsed time = s).
- HIGH when p_MIX ≥ 0.50.
- Seeds 168, 1, 2, 3, 4 are averaged.
- No parameter is estimated from any outcome.
- Where s = g (all training rows; the 2018 and 2019 test rows; 2021 at Leads 7–8), FINAL-MIX equals FINAL exactly.

### Justification (outcome-free)
- When two mechanistic hypotheses are equally consistent with all training data, equal-prior model averaging is the standard non-informative treatment.
- The mixture also widens the predictive distribution exactly where the hypotheses disagree (stale anchors). This is the missing "uncertainty grows with anchor age" component; FINAL's gap-scaled spread does not grow in the 2021 fold.

### Recorded prediction (made before computing; from the already-scored components)
At Lead 1, FINAL-MIX should:
- find Agusan del Sur (about ½(0.41 + 0.67) = 0.54);
- raise one 2021 false alarm (Sarangani, about 0.55);
- keep Masbate and Occidental Mindoro missed;
- give pooled mean p − rate of about +0.07.

It may therefore **pass all seven rules retrospectively**. This prediction is recorded so that a retrospective 7 of 7 cannot be mistaken for evidence: the design was fixed knowing its components' behaviour on these rows.

## 3. What counts

| Evidence | Status |
|---|---|
| Retrospective (72 reused rows; Leads 1–8 walk-forward) | Computed and reported in full, labelled **inadmissible for acceptance** |
| Prospective (the gate) | FINAL-MIX and its components are **sealed now** for ENNS 2022, every province, Leads 1–2, with the existing seal construction (`seal_candidates_enns2022.py`; FINAL must reproduce its existing sealed rows exactly). When a provincial HFIAS round with these provinces becomes available, PROTOCOL_SA Rules 3–7 are applied to the sealed forecasts. Leads 1–2 give the first admissible maximum-lead evidence |
| **Acceptance gate** | **UNVERIFIED** until that round is scored. A retrospective 7/7 is reported as "7/7 retrospective, inadmissible", never as "accepted" or "validated" |

## 4. Maximum reliable lead
- Same rule as before (`../aiPHeed_final_stability_lead_20261113/FINAL_IMPROVEMENT_PROTOCOL.md` section 3): every lead from 1 up must pass all criteria on at least 2 rounds with at least 10 HIGH and 10 LOW.
- Retrospective results are reported for FINAL, FINAL-ET and FINAL-MIX, labelled.
- **The admissible maximum reliable lead is "not established"** until sealed forecasts are scored.

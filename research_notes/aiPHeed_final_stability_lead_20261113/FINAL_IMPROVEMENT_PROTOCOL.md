# FINAL improvement and maximum-reliable-lead protocol (locked 2026-11-13, before any candidate fit or Lead 4–8 FINAL score)

**Acceptance rules:** PROTOCOL_SA (`aiPHeed_final_standalone_20261113/PROTOCOL_SA.md`, sha `15202d27`), **unchanged**. Rule 6 uses the n < 600 form locked there; the originally proposed form is also reported.

**Baseline:** FINAL as stored. It is reproduced exactly: 45 of 45 fits identical, 0.0 difference (`aiPHeed_final_standalone_20261113/evidence/R7a_reproduction.json`). FINAL and FINAL-SA files are preserved and not modified.

## 1. Candidate FINAL-ET (elapsed-time correction). The only candidate.

### Hypothesis
RATE scales the learned per-quarter change by `gap_q`, the quarters since the **province's own** survey. The three anchors (H, OH, RSS: `app/e160/arms.py`, `app/e163/model.py`) are, however, "national level of the **latest released round** + the province's shrunk deviation".

When a newer round that did not survey the province has been released, the anchor already carries the national change to that round. RATE then applies the full own-survey gap on top of it, counting the trend twice. RSS also discounts the ageing deviation itself (Kalman time step).

### Evidence (training-only or outcome-free)
- `D4_gap_vs_staleness_by_fold_lead.csv`: in **every training row of every fold-lead**, the province's own survey is the latest released round (gap = staleness).
- They differ **only** in the ENNS 2021 test rows at Leads 1–6: gap 24 against staleness 8 (L1–L2) or 12 (L3–L6). This forecast condition never occurs in training.
- `aiPHeed_final_standalone_20261113/evidence/D3_anchor_vs_rate_outcome_free.json`: at the 2021 Lead 1 origin, the anchors alone move high-anchor provinces about −12 points and RATE adds about −12 more. Training provinces of that level fell −9.4 points (`D1`).
- In 2018 and 2019 the two quantities coincide, so FINAL is unaffected there.

### Exact change
For **test rows only**, `gap_q` is replaced by the staleness s = target quarter − reference quarter of the latest survey round released at the origin (the pipeline's 6-quarter release rule). s therefore enters, exactly where `gap_q` did:
- the RATE multiplier;
- the gap-scaled predictive spread (`A4.scale`);
- the `gap_q` input.

Everything else is unchanged:
- **Training rows:** unchanged (s = gap in all of them), so every fitted model, selection, calibration choice and threshold is identical to FINAL.
- **Class rule:** p ≥ 0.50 (FINAL's).
- **Not changed:** seeds, MIND, class weights, anchors and inputs.

### Status
A research candidate. Changing FINAL's definition of elapsed time requires **owner approval** before any adoption. The candidate files are separate; FINAL is preserved.

### Not done, on purpose
- no threshold, class-weight, calibration or feature change;
- no province-specific rule;
- no use of the 72 outcomes to choose anything;
- no second candidate;
- FINAL-SA is a diagnostic reference only.

## 2. Scoring the candidate

- Scored **once**. PROTOCOL_SA Rules 1–7 at Lead 1 (primary); Leads 2–3 reported.
- Labelled **retrospective, reused 72 rows**. FINAL-ET differs from FINAL only in the ENNS 2021 rows at Leads 1–6.
- **Rule 7, reported in addition and not part of acceptance** (the locked rule is not extended):
  - **(g) Training perturbation:** three refits per round at Lead 1, seed 168, each on a random 90 % of training provinces (random seeds 1, 2, 3). "Severe" if balanced accuracy changes by more than 0.10.
  - **Seed spread:** reported.
- **Decision mapping (PROTOCOL_SA section 4):**

  | Evidence | Verdict |
  |---|---|
  | 7 of 7 on reused rows | CONDITIONALLY ACCEPT at most |
  | Any rule fails | REJECT as a reliable standalone forecaster |

## 3. Maximum reliable lead (walk-forward, expanding window)

### Folds
The cached rolling-origin folds:
- ENNS 2018: Leads 1–6;
- ENNS 2019: Leads 1–8;
- ENNS 2021: Leads 1–8.

For each fold and lead:
- the origin is the survey's reference quarter minus the lead;
- training contains only outcomes released (reference + 6 quarters) on or before that origin;
- every input is as of the origin;
- all preprocessing, selection, calibration and thresholds are refitted inside the fold;
- five seeds are averaged.

### Evaluation set per lead
- Leads 1–6: three rounds (72 province-rounds).
- Leads 7–8: two rounds (2019 and 2021; 50 province-rounds).

### A lead L is RELIABLE when all of the following hold on its evaluation set
- **Minimum data:** at least 2 rounds, at least 10 HIGH and at least 10 LOW.
- **Rule 3:** balanced accuracy ≥ 0.70 and AUROC ≥ 0.70.
- **Rule 4:** HIGH recall ≥ 0.80.
- **Rule 5:** HIGH precision ≥ 0.60.
- **Rule 6** (locked n < 600 form):
  - 6a: ECE within the 95th percentile of perfect calibration;
  - 6b: |mean p − rate| ≤ 0.10;
  - 6c: Cox p ≥ 0.05;
  - 6d: Brier skill > 0.
- **Rule 7:**
  - 7b: worst-seed balanced accuracy ≥ 0.70;
  - 7c: every round with at least 4 HIGH and 4 LOW has balanced accuracy ≥ 0.60 **and** HIGH recall ≥ 0.50.

Rules 1, 2 and 7a are checked once for the whole model; Rule 2 alignment is checked at every lead.

### Decision
- The **maximum reliable lead** is the largest L such that **every** lead 1…L is reliable.
- If Lead 1 is not reliable, **no reliable lead is established**.
- A lead with too few observations is "not evaluable", never "reliable".

### Reported but not used for the decision
- **Baselines** (same rows):
  - latest-survey persistence (`PERS`, E158 label table);
  - training-rate climatology;
  - always-LOW.
- **Survey-anchor gap versus lead.** In this design each round has a single test gap (12, 16, 24), so the gap effect is confounded with the round. It is reported, not separated.

### Which model is studied
FINAL (baseline) and FINAL-ET.
- The candidate's lead result counts only if FINAL-ET itself passes the Rule 7 requirements at Lead 1.
- Otherwise the maximum reliable lead is reported for FINAL, with FINAL-ET shown alongside.

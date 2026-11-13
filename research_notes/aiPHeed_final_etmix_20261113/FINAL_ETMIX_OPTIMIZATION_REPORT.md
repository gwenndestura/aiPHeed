# FINAL-ETMIX: input and procedure optimization review (Part 6)

**Decision: no change to FINAL-ETMIX is accepted. The model stays exactly as locked (protocol `a365da1f`) and sealed (`71ebe142`).**

This is a reasoned outcome, not an omission. The only outcomes available to judge a change are the 72 province-rounds already reused about 45 times. Any change chosen with them would be optimized on locked evaluation outcomes (rules 5–6 of the brief). It would also invalidate the sealed prospective test, which is the one admissible path to validation.

## 1. What is already optimized inside every walk-forward fold (training rows only)

| Lever | How ETMIX handles it | Uses held-out outcomes? |
|---|---|---|
| Feature usefulness | Top 25 inputs by \|Spearman\| with the training residual, per fit | No |
| Redundancy | Pairs with ρ > 0.95 pruned, per fit | No |
| Missingness | MIND: training-median fill + 0/1 flag for inputs with training gaps | No (inputs only) |
| Temporal alignment | As-of inputs; anchors and labels from rounds released by the origin (6-quarter lag) | No |
| Model complexity / regularization / hyperparameters | 16-setting grid (leaves 3 or 7, min child 10 or 40, L2 5 or 20, 150 or 400 trees; learning rate 0.02) × 3 anchors × 4 feature sets, chosen by inner GroupKFold-by-region weighted error | No |
| Class imbalance | Balanced HIGH/LOW weights × survey-precision weights | No |
| Calibration | Raw / linear / Platt by inner Brier (raw chosen in 110/110 fits of this study) | No |
| Threshold | Fixed at 0.50 by protocol (HFIAS 50 % line) | No |
| Survey anchor | H / OH / RSS chosen by inner error | No |
| Elapsed time | Equal mixture of g and s (non-informative; g = s in all training rows) | No |

## 2. Candidate changes examined, and why each was not adopted

| Candidate change | Evidence | Decision |
|---|---|---|
| Remove inert groups (climate, employment, news) for parsimony | Withholding, permutation and retraining show ≈ 0 effect (`FINAL_ETMIX_CONTRIBUTOR_IMPORTANCE_REPORT.md`) | **Not adopted.** Removing them changes no forecast class, so no gain. The selection step already excludes them in most fits. A changed candidate set would also break comparability with the seal. They are reported as contextual instead |
| Add inputs (displacement, provincial employment, SWS hunger) | Displacement: no compiled series (DROMIC from 2014, needs owner approval). Provincial LFS only from 2022 (prospective only). SWS hunger tested 11-11, no gain | **Not adopted.** Nothing genuine and available at the 2018–2021 origins |
| Class weights off / other schemes | FINAL-CW 11-12: training never chose balanced in the 2018/19 folds; the forward score fell | **Not adopted** (already examined) |
| Cap elapsed-time extrapolation (FINAL-SA) | 11-13 standalone: recall 0.92 but calibration failed (mean p +0.10, Cox p 0.036) | **Not adopted** |
| Training-tuned threshold | FINAL-SA's training-OOF threshold failed calibration; ETMIX's sensitivity is flat over 0.45–0.60 | **Not adopted.** 0.50 kept |
| Synthetic augmentation | Owner prohibits it; six earlier studies found no gain | **Prohibited** |
| Re-weight the mixture (≠ ½) | No training information identifies the weight (g = s in training) | **Not adopted.** Any other weight would be tuned on the 72 outcomes |

## 3. What would justify a future change
1. **An outcome not yet seen:** score the sealed ENNS 2022 forecasts first. Any change made afterwards must then be re-sealed before the next round.
2. **New genuine inputs** that exist at the origin, added under a newly locked protocol and sealed prospectively:
   - provincial LFS employment (2022+);
   - a DROMIC displacement series with release dates.
3. **A larger outcome set** (more HIGH provinces) before calibration-level tuning.

## 4. Reproducible record
- **Accepted changes to the model:** none.
- **Changes to code:**
  - The backend implementation `app/hcw/etmix.py` reproduces the protocol (test `test_etmix_reproduces_sealed_protocol_forecasts_and_explanations_are_exact`).
  - The evaluation scripts in `scripts/`.
- **Seals and earlier records:** untouched (sha256 re-verified: `71ebe142…`).

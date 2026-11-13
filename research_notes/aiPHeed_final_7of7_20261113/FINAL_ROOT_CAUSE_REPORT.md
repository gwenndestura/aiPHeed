# FINAL: verified architecture and root causes of the seven-rule failures

## 1. Exact current system (verified in code and by exact re-runs)

| Element | Implementation |
|---|---|
| Version | FINAL (RATE + MIND), `final-rate-mind-1.0-experimental`. Research engine `aiPHeed_hcw_final_optimization_20261112/scripts/engine_final.py`; project port `app/hcw/final_engine.py` (H_cw branch, not served) |
| Call | `fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")`; seeds 168, 1, 2, 3, 4; mean probability |
| Target and label | y = logit(FNRI HFIAS moderate+severe prevalence). HIGH when ≥ 50 %. q = Φ(y ÷ SE) carries survey uncertainty (assumed 3.0-point SE for 2021) |
| Anchors | H, OH, RSS = national level of the **latest released** round + shrunk province deviation; chosen per fit by inner error. Rounds usable 6 quarters after reference |
| RATE | Target (y − anchor) ÷ (gap ÷ g₀). Prediction = anchor + (gap ÷ g₀) × LightGBM rate. Gap = **own-survey** gap |
| MIND | Training-median fill + missing flags for inputs gappy in training |
| Inputs | 77 candidates in 4 feature sets. Top 25 by Spearman correlation with the residual, pruned at ρ > 0.95, inside each fit. Monotone constraints. Remittance and fish families dropped by design (`DROP`) |
| Weights, calibration, cut-off | Balanced class × survey-precision weights. Probability Φ(mu ÷ sd), sd from gap-regressed inner residuals. Raw / linear / Platt chosen by inner Brier (raw every time). HIGH at 0.50 |
| Inner validation | GroupKFold by region on training rows; 3 anchors × 4 feature sets × 16 settings |
| Walk-forward | Each ENNS round is a fold; origin = target − lead; expanding training of released rounds |
| Reproduction | 45/45 and 110/110 fits identical; 26/26 pipeline as-of, leakage and reproduction tests pass |
| Locked rules | PROTOCOL_SA `15202d27` (thresholds unchanged) |

Selected inputs per fit, gain and geography: `FINAL_INPUT_FEATURE_AUDIT.md`.

## 2. Root causes

| # | Cause | Evidence | Rules affected |
|---|---|---|---|
| R1 | **Stale-anchor double counting.** Anchors refresh to the latest round, while RATE scales by the older own-survey gap. Happens only in 2021 test rows at Leads 1–6; never in training, so the right elapsed time cannot be learned | `FINAL_SURVEY_ANCHOR_AND_LONG_GAP_ANALYSIS.md`; D3, D4 | 7c (FINAL); 4 |
| R2 | **Round-specific national trends not observable at the origin.** 2015→2018 fell much faster than the training period, so every variant over-predicts 2018 (+0.19) and uses up the calibration tolerance | D1; C1 | 6 (variants) |
| R3 | **Weak within-round ranking among high-anchor provinces** (2021 AUROC 0.86–0.88). Raising the level to catch HIGH provinces also raises LOW provinces | C1 | The 6-versus-7 trade-off |
| R4 | **Information gaps.** The largest driver is *regional* GRDP (constant within a region). Employment is national and inert; climate inert; remittances absent; displacement unobserved | Input audit; G1–G2 | 4, 7c |
| R5 | **Gap extrapolation in every fold;** spread does not widen with the gap | D4, D5 | 6, 7 |
| R6 | **Insufficient sample.** 25 HIGH in total, 4 in 2021: Rule 7c is decided by one province (training perturbation: 2021 recall 0.25–1.00). Rule 6's proposed limits need 600–1,000 forecasts | `P0_*`; `R7_et_sensitivity.json` | 6, 7 |
| R7 | **Reused rows.** About 45 configurations examined on the same 72 outcomes; no unseen provincial round | Experiment register | All row-based rules |

## 3. What was corrected
- **The elapsed-time ambiguity (R1) is resolved with a training-justified rule,** an equal mixture of the two hypotheses (FINAL-ETMIX), and sealed for ENNS 2022 (`71ebe142`).
- **The trigger-group evidence is corrected:** the regional accounts were separated out, and the `vu_tc_*` and remittance facts fixed.
- **A future-forecast risk-flag scheme is defined** (S, G, C, X, D), outcome-free.

## 4. Still open
- R2 and R3: no verified period-trend input; no input separating 2021-type provinces.
- R4: provincial employment exists only from 2022; no provincial remittances; displacement series not compiled.
- R6 and R7: only new provincial survey outcomes resolve these.

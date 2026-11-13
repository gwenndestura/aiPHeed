# PROTOCOL_REL — FINAL public-data reliability gates (written 2026-11-13, before this study's new computations)

Model under test: FINAL (RATE + MIND), `app/hcw/final_engine.py` in `C:\Users\admin\aipheed_hcw` (= engine_final.fit_predict,
rate='lin', miss='mind', cw='balanced'). No retraining, re-tuning, threshold change or synthetic data. Cut-off fixed at p >= 0.50.

Honesty statement written before computation: the 72 Lead-1 province-rounds (ENNS 2018/2019/2021) have been scored many times
during development (11-11 to 11-13). Every result below is therefore RETROSPECTIVE. Per-fold predictions are computationally
leakage-free (the test round's outcome is not used in its fit), but the researcher has seen these outcomes. No gate passed here
can be called independent validation; that requires an untouched round (the sealed ENNS2022 forecasts, seal 4ad9267f).

## Gates per lead L (all must hold; thresholds copied from the thesis objective, the 11-11 robust rule and PROTOCOL_SA Rule 6/7)
| id | criterion | source |
|---|---|---|
| G1 | accuracy >= 0.75 (pooled, 5-seed mean probability) | thesis Objective 2 |
| G2 | accuracy beats always-LOW: paired bootstrap 95 % CI of (acc_FINAL - acc_LOW) > 0 | brief §3 |
| G3 | HIGH recall >= 0.75 pooled AND >= 0.50 in every test round | robust rule / PROTOCOL_SA R7 |
| G4 | HIGH precision >= 0.60 and HIGH F1 >= 0.70 | brief §3 (new, fixed here) |
| G5 | balanced accuracy >= 0.75 and macro F1 >= 0.75 | brief §3 (new, fixed here) |
| G6 | calibration consistency: abs(mean p - observed rate) <= 0.10 AND Cox recalibration test p >= 0.05 | PROTOCOL_SA R6 (consistency form) |
| G7 | Brier significantly lower than persistence AND than always-LOW climatology (training HIGH share) (95 % CI < 0) | robust rule / brief §3 |
| G8 | PR-AUC >= persistence PR-AUC | brief §3 (new) |
| G9 | stability: every seed accuracy >= 0.75 AND every round accuracy >= 0.70 | robust rule |

Maximum reliable lead = largest L such that every lead 1..L passes G1-G9 (contiguous). Leads 1-5 are evaluated.

## Stability tests (L1; reported, gate G10 applies to the model as a whole)
- G10a survey-round sensitivity: refit with one TRAINING round removed (where >= 2 training rounds exist): accuracy >= 0.70.
- G10b province generalisation: refit with the test provinces' own training rows removed (unseen provinces): accuracy >= 0.70 and HIGH recall >= 0.50.
- G10c bootstrap: province-cluster bootstrap 95 % CI lower bound of accuracy >= 0.65 (above the always-LOW rate 47/72).
- Threshold sensitivity 0.30-0.70: reported only; the cut-off is not moved.

## Contributors (Section 6)
A group "genuinely improves out-of-sample forecasting" only if retraining without it worsens L1 Brier with a 95 % CI above 0.
Groups: market & prices, climate stress, employment, OFW remittances, poverty & social vulnerability (dashboard), plus the
meaning-based groups FINAL actually uses. No group is forced to have importance.

## Freezing
Freeze + new 2027-Q1..2028-Q1 seal ONLY if G1-G10 pass at least at Lead 1. Otherwise nothing is frozen as validated; the
existing ENNS2022 seals remain the prospective test.

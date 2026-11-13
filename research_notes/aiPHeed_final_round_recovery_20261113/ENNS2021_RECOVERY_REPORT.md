# ENNS 2021 failure: investigation, solutions tested, per-round results (2026-11-13)

- **Protocol:** `PROTOCOL_RR.md`, sha256 `3d749389…`. It was written before the new candidate was computed.
- **Scripts:** `scripts/rr_eval.py` (per-round evaluation of every candidate) and `scripts/rr_limits.py` (limit diagnostics).
- **Evidence:** `evidence/RR_per_round.csv`, `RR_verdict.json`, `RR_oracle_threshold_2021.csv`, `RR_separability_2021.csv`.

## 1. Root cause of the 2021 failure

| Question | Finding |
|---|---|
| Why is 2021 HIGH detection low? | 2021 is the only round where every province's last survey was 24 quarters old, longer than any gap in training (8–20). FINAL's elapsed-time term then extrapolates a decline of about 19 points on average; the real decline was about 13. The four HIGH provinces (2015 levels 65–73 %) fell only 7–11 points and were pushed under 0.50 |
| Does the elapsed-time feature extrapolate unreliably? | **Yes.** The time term is −0.48 logit in 2021, against −0.19 and −0.25 in 2018 and 2019. Replacing it with time since the latest released round (ET) or averaging the two (ETMIX) recovers 2 of 4 |
| Training-round composition? | It affects stability: dropping one training round moves 2021 recall between 1/4 and 3/4, with up to 8 class changes. That is too unstable to rely on |
| Patterns that work in 2018/2019 but not 2021? | **Yes.** In 2018/19, provinces with high earlier levels mostly stayed high, so the model and persistence both work. In 2021, four LOW provinces that started just as high (Negros Occidental, Negros Oriental, North Cotabato, Sarangani: 2015 persistence p ≥ 0.90) fell 18–34 points, while the four HIGH ones fell 7–11 |
| Feature importance or missing data? | No 2021-specific missing-data problem in the decisive inputs. The 2021 fits did not select GRDP or poverty; factor contributions to the misses are below 0.1 logit |
| Class imbalance? | No. 2021 training was 52 % HIGH, with balanced class weights |
| Calibration or threshold? | **No.** See §4: even the best threshold chosen on the 2021 outcomes cannot meet the targets |
| Model design, data limits or forecasting setup? | **Mainly a data limit, made worse by model design.** The time-term extrapolation is a design issue and is partly fixable. But separating the high-starting provinces that improved from those that did not needs information that no public input available before the 2021 forecast contains |

## 2. Solutions implemented and tested (each targets the root cause; no setting chosen from 2021 outcomes)

| Candidate | What it changes | Why |
|---|---|---|
| C1 FINAL-ET | Elapsed time = quarters since the latest released round | Removes the double count of the decline |
| C2 FINAL-SA | Time multiplier capped at the longest training gap | No extrapolation beyond training support |
| C3 FINAL-ETMIX | Average of FINAL and ET probabilities | Hedge between the two elapsed-time definitions |
| C4 FINAL-CF | One-quarter carry-forward of local prices | Seasonal data gap |
| C5 STACK (new) | Combination of FINAL and persistence; weight learned only from earlier released rounds' out-of-sample forecasts (2018 + 2019 for the 2021 fold) | Persistence caught all four 2021 HIGH provinces |
| C6 STACK-ET (new) | Same, with ET | Same |

**Learned stacking weight:** 1.00 at every lead, i.e. pure FINAL. On the earlier rounds, persistence only made forecasts worse, so a training-only combination gives it no weight.

## 3. Before and after, Lead 1, every round (TP/FP/FN/TN; ✓ = all 8 targets met)

| Model | 2018 (8 HIGH / 22) | 2019 (13 / 25) | 2021 (4 / 25) | Pooled |
|---|---|---|---|---|
| **FINAL (before)** | ✓ R 1.00, P 0.73, F1 0.84, BA 0.89, Acc 0.86 (8/3/0/11) | ✓ R 0.85, P 0.85, F1 0.85, BA 0.84, Acc 0.84 (11/2/2/10) | ✗ **R 0.25**, P 1.00, **F1 0.40, BA 0.63**, Acc 0.88 (1/0/3/21) | ✓ R 0.80, P 0.80, F1 0.80 |
| C1 ET | ✓ same as FINAL | ✓ same | ✗ R 0.50, **P 0.33**, F1 0.40, BA 0.66, Acc 0.76 (2/4/2/17) | R 0.84, P 0.70, F1 0.76 |
| C2 SA | ✗ P 0.57, Acc 0.73 (8/6/0/8) | ✓ R 1.00, P 0.77 | ✗ R 0.25 (1/0/3/21) | P 0.69 ✗ |
| C3 ETMIX | ✓ same | ✓ same | ✗ R 0.50, P 0.67, F1 0.57, BA 0.73, Acc 0.88 (2/1/2/20) | R 0.84, P 0.78, F1 0.81 |
| C4 CF | ✓ | ✓ | ✗ R 0.25 (1/0/3/21) | R 0.80, P 0.80 |
| C5 STACK | ✓ (= FINAL) | ✓ (= FINAL) | ✗ R 0.25 (1/0/3/21) | = FINAL |
| C6 STACK-ET | ✓ | ✓ | ✗ R 0.50, P 0.33 (2/4/2/17) | = ET |
| Persistence | ✗ P 0.47, Acc 0.59 | ✓ | ✗ P 0.25, F1 0.40, Acc 0.52 (4/12/0/9) | ✗ |

Brier, ROC-AUC and PR-AUC pass for every candidate in every round. Detail is in `RR_per_round.csv`, which also covers Leads 2 and 3.

**Verdict under PROTOCOL_RR:**
- **No candidate meets all eight targets in every round.**
- The best on 2021 is ETMIX: 2 of 4 HIGH found, 1 false alarm, 2018/2019 unchanged. It still fails recall (0.50) and F1 (0.57) in 2021.
- **FINAL is kept unchanged.**

## 4. Why the targets cannot be met in 2021 with the available data

**Oracle threshold test (`RR_oracle_threshold_2021.csv`).** For each model, the cut-off was chosen *using the 2021 answers*, which is forbidden in practice. It is shown only to prove the limit:

| Model | 2021 ROC-AUC | Best achievable on 2021 itself | Meets recall, precision, F1, BA, accuracy targets? |
|---|---|---|---|
| FINAL | 0.857 | 4 TP / 6 FP (P 0.40, F1 0.57) | **No** |
| ET | 0.881 | 2 TP / 0 FP (R 0.50, F1 0.67) | **No** |
| ETMIX | 0.869 | 4 TP / 6 FP (F1 0.57) | **No** |
| Persistence | 0.899 | 4 TP / 5 FP (F1 0.62) | **No** |

- Every model ranks some LOW provinces above some HIGH ones in 2021. Masbate (FINAL p 0.15) sits below Sarangani, North Cotabato, Leyte and Negros Occidental.
- **No threshold, recalibration or class weighting can fix a ranking problem.**

**Separability (`RR_separability_2021.csv`).**
- Of 48 model inputs available at the 2021 forecast date, none orders the four HIGH provinces above the four high-starting LOW ones. The best has AUC 0.81 on just 8 provinces.
- Several of the best-separating directions are implausible (higher subsistence incidence → *less* risk).
- **The information that distinguishes these provinces is not in the public inputs available before the forecast.**

## 5. Baseline comparison (Lead 1)
- **FINAL vs persistence:** FINAL is better on pooled Brier (0.123 vs 0.253), F1, precision, BA and accuracy.
- **Persistence's strength and weakness:** it finds all 4 HIGH provinces in 2021, but with 12 false alarms (precision 0.25).
- **Always-LOW:** FINAL beats it on every class-balanced metric.

## 6. Stability (FINAL)
- **Seeds:** at Lead 1, every seed passes all 8 pooled targets (accuracy 0.847–0.861; recall 0.76–0.80).
- **Training-round removal (2021 fold):**
  - without 2015: recall 1/4;
  - without 2018: recall 3/4, but precision 0.33;
  - without 2019: recall 2/4.

  2021 HIGH detection is **not stable**.
- **Candidates:** they fail at Lead 1, so no stability tests were added. Their stored seed results are in the 11-13 study folders.

## 7. Leakage checks
- **Origins:** across 110 FINAL fits, every training round was released before its forecast origin (6-quarter lag) and the test round was never in training. 0 violations (`../aiPHeed_final_reliability_20261113/evidence/LEAK_origin_check.json`).
- **Stacking weights:** learned only from rounds whose outcomes were released before the 2021 origin (2018 and 2019).
- **Labels:** no synthetic labels; no threshold learned from evaluation outcomes. The oracle in §4 is a diagnostic only.

## 8. Remaining limitations and what would resolve them

| Limitation | What would resolve it |
|---|---|
| Only one long-gap round (2021) exists, with 4 HIGH provinces, so the model cannot learn long-gap behaviour and 2021 recall is decided by 1–2 provinces | Another FNRI provincial HFIAS round (any year after 2021) that can be scored against the sealed forecasts |
| No public pre-forecast input separates high-burden provinces that improved strongly (2015→2021) from those that did not | Candidate provincial-change data, each needing its own protocol and a prospective test: DSWD 4Ps/social-pension coverage expansion by province, DROMIC displacement, provincial COVID-period labour data (PSA provincial LFS starts in 2022, so prospective use only) |
| Elapsed-time extrapolation | ETMIX/ET reduce it (2/4). To adopt one, lock it now, seal its forecasts next to FINAL's, and score both on the next round |
| Evaluation data reused during development | Independent validation is still required: score sealed forecasts `80b20aed…` (FINAL) on the next eligible survey |

## 9. Final answer to the brief's acceptance criteria

| Criterion | Status |
|---|---|
| All 8 targets in every round | **NOT MET** (2021 fails recall, F1, BA; no candidate fixes it) |
| ENNS 2021 HIGH-detection failure resolved | **NOT RESOLVED.** Best defensible candidate: 2/4 |
| 2018 and 2019 retain performance | Met (FINAL, ET, ETMIX) |
| Outperforms baselines | Met (pooled) |
| Stable across rounds and seeds | Seeds: met. Rounds: **not met** for HIGH detection |
| One-quarter-ahead supported out-of-sample | Met retrospectively (chronological, leakage-free) |
| No leakage or synthetic labels | Met |

**Conclusion:**
- The 2021 failure cannot be resolved with the public data available before the 2021 forecast date.
- Forcing it, by tuning on 2021, by thresholds, or by keeping whichever variant happens to catch 3 of 4, would be overfitting to 4 provinces. The oracle test shows that even that cannot meet every target.
- FINAL remains the model: it passes all eight targets in 2018 and 2019 and pooled.
- The 2021 long-gap weakness is documented as an unresolved limitation, and HIGH-risk detection after long survey gaps remains unvalidated until a new FNRI provincial HFIAS round is available.

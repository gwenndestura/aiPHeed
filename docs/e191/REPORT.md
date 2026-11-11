# E191 report: exhaustive synthetic-data search for E184 (local only, not committed)

**Sources.**
- Protocol: `docs/e191/PROTOCOL.md`, with its SHA-256 logged before the run.
- Code: `backend/app/e191/` (`gens.py`, `run.py`).
- Outputs: `backend/data/e191/out/` (`results.json`, `configs.csv`, `quality.csv`, `arm_rows.csv`, `shuffle_rows.csv`,
  frames, run log, hashes).
- Runtime: 26 minutes, 16:23–16:49.

## 1. Setup checks
- **No leakage.** For every origin, the corrupted-unreleased frames have identical training rows, test inputs and test
  anchors. Only the test rows' own (corrupted) outcome label differs, and it is never used as an input.
- **Reproduction.** E168 (`none`) reproduces exactly (0.0 at all 432 rows).
  - **E184 (`e184`) reproduces exactly at each job's first lead.**
  - **Deviation.** Leads that share a training frame were run as one job, with the synthetic random stream named after
    the job's first lead. At the other leads the E184 arm is therefore a fresh random draw: same method, different
    random numbers, with |Δp| ≤ 0.077.
  - All E191 comparisons use the same stream for E184 and every candidate, so they are fair. The official stored E184 is
    also shown.
- **Training-frame groups.** ENNS2021 Leads 1–2 | ENNS2021 Leads 3–6 | ENNS2019 Leads 1–6 | ENNS2018 Leads 1–6.

## 2. Generators tested (Stage 2, 50/50)

Ordered by mean outer accuracy at Leads 1–3. This table is descriptive: none of these numbers was used for selection.

| Generator | Family | L1 | L2 | L3 | FA (L1/L2/L3) | Mean Brier | BH q (vs E184) | Inner-CV vs `e184` (SE units, 2018 / 2019 / 2021) |
|---|---|---|---|---|---|---|---|---|
| corrnoise | feature | 77.8 | 79.2 | 77.8 | 12/11/12 | **0.1205** | 1.0 | +0.40 / +0.60 / +1.03 |
| e184 (same stream) | baseline | 76.4 | 77.8 | 77.8 | 13/11/12 | 0.1231 | – | 0 |
| traj | temporal | 76.4 | 76.4 | 79.2 | 13/13/12 | 0.1250 | 1.0 | **−0.96 / −0.35 / −0.20** |
| boot_row | bootstrap | 77.8 | 76.4 | 75.0 | 14/14/14 | 0.1256 | 1.0 | +0.45 / 0.00 / +2.47 |
| none (= E168) | baseline | 75.0 | 77.8 | 75.0 | 15/13/14 | 0.1268 | 1.0 | +0.10 / −0.07 / +1.72 |
| classw | weighting | 72.2 | 77.8 | 77.8 | 15/12/12 | 0.1234 | 0.97 | +0.98 / +0.94 / +1.49 |
| bsmote | minority | 75.0 | 75.0 | 77.8 | 14/14/13 | 0.1239 | 1.0 | +1.60 / +1.21 / +1.09 |
| vae (pilot) | multivariate | 77.8 | 77.8 | 72.2 | 14/13/15 | 0.1274 | 0.93 | +2.80 / +1.50 / +0.18 |
| boot_prov | bootstrap | 75.0 | 76.4 | 75.0 | 15/14/14 | 0.1273 | 1.0 | −0.31 / +0.40 / +2.26 |
| kmsmote | minority | 73.6 | 76.4 | 76.4 | 14/13/13 | 0.1238 | 1.0 | +1.13 / +2.05 / +1.29 |
| mixup | feature | 76.4 | 73.6 | 75.0 | 14/15/14 | 0.1263 | 1.0 | +1.55 / +1.96 / +1.15 |
| adasyn | minority | 73.6 | 75.0 | 76.4 | 15/13/13 | 0.1238 | 1.0 | +1.43 / +1.50 / +1.27 |
| svmsmote | minority | 75.0 | 75.0 | 75.0 | 15/14/14 | 0.1266 | 1.0 | +1.39 / +1.22 / +0.63 |
| boot_class | bootstrap | 72.2 | 76.4 | 75.0 | 17/13/14 | 0.1270 | 1.0 | +0.75 / +1.17 / +2.51 |
| copula | multivariate | 72.2 | 75.0 | 76.4 | 17/15/14 | 0.1292 | 1.0 | +0.02 / +0.65 / +0.49 |
| smote | minority | 72.2 | 75.0 | 75.0 | 15/13/14 | 0.1287 | 1.0 | +1.57 / +1.35 / +1.48 |
| gmm | multivariate | 72.2 | 72.2 | 75.0 | 17/16/14 | 0.1337 | 0.93 | +0.31 / +1.06 / +0.21 |
| hard | boundary | 70.8 | 69.4 | 69.4 | 19/20/20 | 0.1422 | 0.80 | +0.48 / +1.19 / +0.49 |
| undersample | bootstrap | 69.4 | 69.4 | 70.8 | 20/20/19 | 0.1471 | 0.80 | +1.57 / +1.35 / +1.66 |
| kde | multivariate | 68.1 | 69.4 | 70.8 | 21/19/18 | 0.1430 | 0.80 | +1.11 / −0.49 / −0.34 |
| gauss | multivariate | 66.7 | 69.4 | 70.8 | 21/19/18 | 0.1437 | 0.80 | +1.04 / +0.34 / +0.28 |
| hybrid | weighting | 66.7 | 66.7 | 65.3 | 22/22/23 | 0.1462 | 0.80 | +1.55 / +1.78 / −0.21 |

- **Rejected without running:**
  - CTGAN: 156–532 rows, too few to train a GAN.
  - Block, circular and stationary bootstrap: at most 4 changes per province.
  - Focal loss: the model is a regression.
  - SMOTENC: there are no categorical inputs.
  - XGBoost: CatBoost was used instead.

## 3. Synthetic-data quality (final fit, seed 17901, mean over jobs)
- **Exact copies.** The bootstraps are exact copies of real rows (100 % duplicates) by design. Mixup has 9 % exact and
  31 % near copies (λ near 0 or 1).
- **Distribution fit.** Copula and the bootstraps fit the marginal distributions best (median KS 0.05–0.07).
  - Borderline-SMOTE, KMeans-SMOTE and the VAE fit worst (KS 0.16–0.17; max W1 0.53–0.63 SD).
  - The VAE fits poorly on 156–532 rows, as expected.
- **Class flips.** Only the jitter-type generators (e184, traj, corrnoise, hard) produce flips (11–19 %), by design.
  They follow the survey's sampling error.
- **HIGH share.** Combined HIGH share is 0.53–0.62 for every generator.

## 4. Nested arms (each chosen per job on training rows only)

The official stored E184 is the reference.

| Model / generator | Ratio | L1 | L2 | L3 | False alarms | Brier (L1/L2/L3) | Reliability |
|---|---|---|---|---|---|---|---|
| E168 | 0 % | 75.0 | 77.8 | 75.0 | 15/13/14 | .1230/.1221/.1352 | Baseline |
| **E184 (official)** | 50/50 | **76.4** | **79.2** | **77.8** | 13/11/12 | .1211/.1185/.1258 | Reproduces exactly; no leakage |
| E184 (same-stream re-draw) | 50/50 | 76.4 | 77.8 | 77.8 | 13/11/12 | .1211/.1192/.1290 | A fresh random draw |
| Best bootstrap | 50 % | 73.6 | 76.4 | 75.0 | 15/14/14 | .1235/.1244/.1354 | Worse |
| Best temporal (traj) | 50–70 % | 76.4 | 80.6 | 80.6 | 13/11/11 | .1226/.1225/.1301 | Brier worse at every lead; Leads 5–6: 72.2 / 73.6 % |
| Best minority | 50 % | 73.6 | 77.8 | 77.8 | 14/11/12 | .1200/.1211/.1305 | Worse at L1 |
| Best multivariate | 40–80 % | 70.8 | 73.6 | 75.0 | 17/15/14 | .1294/.1330/.1341 | Worse |
| Best boundary (hard) | 50 % | 70.8 | 69.4 | 69.4 | 19/20/20 | .1398/.1386/.1482 | Much worse |
| Best feature-space (corrnoise) | 50 % | 77.8 | 79.2 | 77.8 | 12/11/12 | .1188/.1165/.1263 | Best in the outer data; training-side ranked it below e184 |
| Best weighting | 50–80 % | 72.2 | 79.2 | 77.8 | 15/11/12 | .1224/.1203/.1268 | Worse at L1 |
| Best ratio | 40–80 % | 76.4 | 75.0 | 76.4 | 13/14/13 | .1252/.1277/.1265 | Worse |
| Best combination | 60–80 % | 76.4 | 77.8 | 75.0 | 14/12/13 | .1215/.1218/.1240 | Mixed |
| Best model (RF / CatBoost) | – | 75.0 | 75.0 | 77.8 | 14/14/12 | .1218/.1214/.1259 | Worse |
| **E191 (final nested pick)** | per job | 77.8 | 76.4 | 76.4 | 12/12/13 | .1228/.1235/.1287 | **Fails the rule** |

### E191's picks
- ENNS2021 Leads 1–2: `kde@1.5`.
- ENNS2021 Leads 3–6: `e184@4|cat6`.
- ENNS2019: kept `e184` (one-SE rule).
- ENNS2018: `e184@1.5`.

### E191 against E184 (same stream)
- **McNemar:** 1 vs 0, 0 vs 1 and 0 vs 1 discordant pairs; Holm p = 1.0.
- **Brier difference:**
  - L1: +0.0017 [−0.003, +0.007];
  - L2: +0.0043 [−0.001, +0.010];
  - L3: −0.0002 [−0.007, +0.008].

### Full metrics, E191
| Lead | Accuracy [95 % CI] | Balanced accuracy | Precision | Recall | Specificity | F1 | FP / FN | Brier | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 77.8 % [66.9, 85.8] | .792 | .636 | .84 | .745 | .724 | 12 / 4 | .1228 | .882 | .836 |
| 2 | 76.4 % [65.4, 84.7] | .772 | .625 | .80 | .745 | .702 | 12 / 5 | .1235 | .886 | .841 |
| 3 | 76.4 % [65.4, 84.7] | .782 | .618 | .84 | .723 | .712 | 13 / 4 | .1287 | .876 | .817 |

### Controls and seed sensitivity
- **Shuffled triggers (Lead 1).** Shuffled accuracy is 83.3 %. E191 − shuffled Brier = +0.0034 [−0.009, +0.018]. The
  trigger inputs still add no demonstrable signal.
- **Single-seed accuracy (5 synthetic draws).**
  - E184 L1: 73.6–79.2 % (spread 5.6 points), L2: 75.0–79.2 %, L3: 76.4–80.6 %.
  - E191 L1: 73.6–77.8 %.
  - **The random draw alone moves accuracy by 3–6 points, more than any generator difference.**

## 5. Answers
1. **Best generator by training-side evidence: `traj` (trajectory-consistent jitter).** It is the only generator better
   than E184's jitter in inner CV at all three origins, but by less than 1 SE each time.
   - Best by outer test: `corrnoise`.
   - Neither is significantly better than E184.
2. **Best ratio: no consistent one.** The training-side choices were 1.5, 2.33, 4 and 1.0 depending on the origin. The
   nested best-ratio arm was worse than 50/50 (76.4 / 75.0 / 76.4).
3. **Best combination:** `kde+hybrid`, `copula+hybrid`, `kde+traj` and `boot_prov+e184` (all at 1.5–4). The arm scores
   76.4 / 77.8 / 75.0, not better.
4. **Lead 1:** `corrnoise`, `boot_row` and the VAE reach 77.8 % (+1 province).
5. **Lead 2:** nested `traj` reaches 80.6 % (+1 province).
6. **Lead 3:** nested `traj` reaches 80.6 % (+2 provinces).
7. **Fewer false alarms:** `corrnoise` (12/11/12) and nested `traj` (13/11/11), at most one fewer than E184.
8. **Better Brier:** `corrnoise` at Leads 1–2 (.1188 / .1165 against .1211 / .1185). Not significant.
9. **Ineffective or harmful:** class weights + synthetic (`hybrid`), `undersample`, `hard`, `gauss`, `kde` and `gmm`.
   Each raises false alarms to 18–23. Methods that rebalance classes or over-weight hard or boundary rows push the model
   to over-call HIGH. SMOTE-family methods, copula, the VAE and mixup were neutral to worse.
10. **Statistically meaningful: no.** No arm or generator has Holm or BH p < 0.05, and no Brier CI lies entirely below
    zero. Every gain is within the 3–6-point spread that comes from the random draw alone.
11. **Suitable to replace E184: no.** The final nested candidate (E191) fails the pre-registered rule: lower accuracy at
    Leads 2–3, more false alarms at Leads 2–3 and worse Brier. **E184 stays.**

## 6. Conclusion
- **Scope of the search.** About 22 generators × ratios × combinations × 4 model families were searched with fully
  nested selection.
- **E184 is still the best defensible model.** No synthetic-data strategy improves it reliably.
- **The two closest candidates,** for a sealed future test only:
  - trajectory-consistent jitter: the best training-side evidence; 80.6 % at Leads 2–3, but only 76.4 % at Lead 1;
  - correlation-preserving noise: the best outer Brier.
  They could be fixed now and checked on the ENNS 2022 provincial labels when DOST-FNRI releases them.
- **Why the search cannot do better.** Synthetic data reshapes information already in the training rows. The remaining
  errors come from the 2018/2019 origins having one prior survey transition, and from provincial changes that no input
  signals (E189 audit and the error-recovery analysis).

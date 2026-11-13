# 05 — Stability and maximum reliable lead

Scripts: `scripts/rel_eval.py`, `scripts/stab_jobs.py` (40 new refits), `scripts/stab_eval.py`.
Evidence: `evidence/REL_summary_by_lead.csv`, `REL_gates_by_lead.csv`, `REL_by_seed.csv`, `STAB_round_and_province_refits.csv`, `STAB_summary.json`, `run_stab.log`.
Gates: `PROTOCOL_REL.md` (sha256 `1efdf5a4…`, written before these computations).

## 1. Leads 1–5

| Lead | Accuracy | Province-cluster 95 % CI | Precision | Recall | HIGH F1 | Macro F1 | BA | PR-AUC | Brier | mean p − rate | Cox p | 2021 recall | Worst seed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.861 | [0.778, 0.931] | 0.800 | 0.80 | 0.800 | 0.847 | 0.847 | 0.846 | 0.123 | +0.046 | 0.41 | 1/4 | 0.847 |
| 2 | 0.847 | [0.764, 0.917] | 0.769 | 0.80 | 0.784 | 0.833 | 0.836 | 0.855 | 0.123 | +0.043 | 0.57 | 1/4 | 0.847 |
| 3 | 0.819 | [0.722, 0.903] | 0.731 | 0.76 | 0.745 | 0.803 | 0.806 | 0.775 | 0.133 | +0.041 | 0.52 | 2/4 | 0.792 |
| 4 | 0.819 | [0.722, 0.903] | 0.714 | 0.80 | 0.755 | 0.806 | 0.815 | 0.775 | 0.135 | +0.053 | 0.32 | 1/4 | 0.806 |
| 5 | 0.792 | [0.694, 0.875] | 0.679 | 0.76 | 0.717 | 0.776 | 0.784 | 0.815 | 0.138 | +0.045 | 0.47 | 1/4 | **0.736** |

## 2. Gates per lead

| Lead | G1 acc | G2 > always-LOW | G3 HIGH recall (pooled + each round) | G4 prec/F1 | G5 BA/macro-F1 | G6 calibration | G7 Brier vs PERS + CLIM | G8 PR-AUC | G9 seeds/rounds | All |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | PASS | PASS | **FAIL** (2021 1/4) | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** |
| 2 | PASS | PASS | **FAIL** (2021 1/4) | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** |
| 3 | PASS | PASS | PASS (2021 2/4) | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 4 | PASS | PASS | **FAIL** (2021 1/4) | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** |
| 5 | PASS | **FAIL** (CI lower bound 0.000) | **FAIL** | PASS | PASS | PASS | PASS | PASS | **FAIL** (seed 4 0.736) | **FAIL** |

### Maximum reliable lead under PROTOCOL_REL: **0 (none)**
- Lead 1 already fails G3.
- Lead 3 passes alone, but the rule is contiguous. Lead 3's 2021 result (2/4) differs from Leads 1–2 (1/4) by a single province, so it is noise, not a longer horizon of skill.

### Under the earlier, weaker rules (no per-round HIGH requirement)
- The 11-11 robust rule gives **max lead 4**: mean fold accuracy, Brier vs persistence, every seed, every round and both recalls all pass at Leads 1–4, and Lead 5 fails on seed 4.
- Thesis Algorithm 3 (mean fold accuracy ≥ 75 %) gives **max lead 5**.
- These reproduce the 11-13 completion audit. **The difference from this report's result of 0 is caused entirely by the 2021 HIGH-recall requirement.**

## 3. Seeds
- Lead-1 accuracy is 0.847–0.861 over the five seeds; PR-AUC is 0.832–0.850.
- Seed noise is small at Leads 1–2 and grows by Lead 5 (0.736–0.806).

## 4. Survey-round sensitivity (G10a; new refits; Lead 1, 5 seeds)

| Fold | Training round removed | Training rows | Accuracy | HIGH recall | Precision | Class flips vs the full fit |
|---|---|---|---|---|---|---|
| 2021 | FNRI 2015 | 376 of 532 | 0.88 | 1/4 | 1.00 | 0 |
| 2021 | ENNS 2018 | 356 of 532 | 0.72 | 3/4 | 0.33 | **8** |
| 2021 | ENNS 2019 | 332 of 532 | 0.84 | 2/4 | 0.50 | 3 |
| 2019 | ENNS 2018 | 156 of 156 | — | — | — | No-op: 2018 was not released at the 2019 origin |
| 2019 | FNRI 2015 | 0 | — | — | — | **Not executable:** no training rows left (failure kept in `run_stab.log`) |

- G10a (accuracy ≥ 0.70 in every executable refit) **PASSES** (lowest 0.72).
- The HIGH calls are **not stable.** Removing one training round moves 2021 recall between 1/4 and 3/4 and creates up to 8 class changes in 25 provinces. The 2021 forecasts depend on which earlier rounds the model has seen.

## 5. Province generalisation (G10b; new refits)
The test provinces' own survey rows were removed from training, so the model never saw those provinces.

| Fold | Accuracy | HIGH recall | Precision | Flips vs full |
|---|---|---|---|---|
| 2018 | 0.864 | 7/8 | 0.778 | 4 |
| 2019 | 0.800 | 11/13 | 0.786 | 3 |
| 2021 | 0.880 | 1/4 | 1.000 | 0 |
| Pooled | **0.847** | 0.76 | 0.792 | 7 |

The full-fit pooled result on the same rows is 0.861 / 0.80 / 0.80. **G10b PASSES**: FINAL generalises to unseen provinces with little loss.

## 6. Bootstrap (G10c)
- Province-cluster bootstrap of Lead-1 accuracy: 95 % CI [0.778, 0.931]. The lower bound is above 0.65 (the always-LOW rate), so G10c **PASSES**.
- The HIGH-recall CI is wide: [0.615, 0.947].

## 7. Threshold sensitivity
See `04_HIGH_RISK_DETECTION.md` §4. Results are stable between 0.50 and 0.60 and fall apart above 0.60.

## 8. Failed experiments preserved
- `run_stab.log` holds the 5 non-executable "2019 without 2015" fits.
- All earlier failed FINAL variants (FINAL-SA, FINAL-ET, ETMIX, CW, SYN, MIX) are kept in their 11-12/11-13 folders, and none was re-scored here.

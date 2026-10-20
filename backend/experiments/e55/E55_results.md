# E55: E53-A1 at lead 2 (next calendar quarter)

Experiment only. Nothing in `backend/app`, `backend/data` or `frontend` was changed; AIPHEED_MAX_LEAD and AIPHEED_RECORD are unchanged.

- **Run:** `20261016T122641Z` (`E55_results.json`, `runs/…/predictions.csv`, `runner/e55_run.py`).

## Setup

- **Model:** the E53-A1 inputs (E36's 13 + five trigger proportions + five cond_*), pool COMPACT_T5_C / COMB_T5_C × G1/G4/G3/G2, seed 36, E36 nested rule, E49-C2 shrinkage fitted on earlier eligible dates only.
- **Walk-forward:** E37's lead-k procedure at k = 2 (target F = origin quarter + 2).
- **cond_\* timing:** data quarter F−3, the latest complete quarter published before the origin, ranked against strictly earlier quarters.
- **Refit check:** the refit at every origin matches the walk-forward exactly (max |Δp| = 0).
- **Rows:** labels equal E38's on all 55 rows (11 target quarters 2023-Q3..2026-Q3; 49 HIGH / 6 LOW).

## Results (identical 55 rows)

| Model | Accuracy | Bal. acc. | AUC | Brier | LOW caught | HIGH caught |
|---|---|---|---|---|---|---|
| **E55** (E53-A1 lead 2 + C2) | 0.673 | 0.670 | **0.811** | 0.214 | **4/6** | 33/49 |
| E55 raw (no C2) | 0.655 | 0.660 | 0.787 | 0.243 | 4/6 | 32/49 |
| E38 (stored, own threshold) | 0.709 | 0.544 | 0.655 | 0.200 | 2/6 | 37/49 |
| Persistence | **0.800** | **0.741** | 0.741 | 0.200 | 4/6 | 40/49 |
| (Always-HIGH, for reference) | 0.891 | 0.500 | 0.500 | 0.109 | 0/6 | 49/49 |

| E55 vs | McNemar (E55 only / ref only correct) | p | p Holm | Per-date Brier difference (E55 − ref) | Sign-flip p | p Holm |
|---|---|---|---|---|---|---|
| E38 | 7 / 9 | 0.80 | 0.80 | +0.015 | 0.80 | 1.00 |
| Persistence | 6 / 13 | 0.17 | 0.33 | +0.014 | 0.84 | 1.00 |

Training accuracy at the 2027-Q1 origin: 0.943 raw, 0.757 after C2 (a = 0.3).

## Adoption (rule fixed before the run)

| Accuracy ≥ 0.75 | Balanced accuracy ≥ 0.75 | Brier ≤ persistence (0.200) | LOW caught ≥ 3/6 | Result |
|---|---|---|---|---|
| ✗ 0.673 | ✗ 0.670 | ✗ 0.214 | ✓ 4/6 | **not eligible** |

## 2027-Q1 forecast (origin 2026-10-01): PREVIEW, not served

- **Q4 configuration:** COMPACT_T5_C × G1 (one-split trees).
- **Identical provinces:** Cavite, Laguna, Quezon and Rizal receive identical values, because their inputs fall on the same side of every split.
- **cond_\* inputs (data quarter 2026-Q2):** the same as E53's Q4 2026 serving values.

| Area | Index (C2) | Raw | Five drivers (Market / Climate / Fish / Employment / OFW) | With Other |
|---|---|---|---|---|
| **CALABARZON** | **0.798** | | 75 / 0 / 2 / 22 / 1 | 63 / 0 / 1 / 19 / 1, Other 16 |
| Cavite, Laguna, Quezon, Rizal (each) | 0.820 | 0.983 | 73 / 0 / 2 / 24 / 1 | 61 / 1 / 1 / 20 / 1, Other 16 |
| Batangas | 0.709 | 0.614 | 79 / 1 / 1 / 18 / 1 | 69 / 0 / 1 / 16 / 1, Other 13 |

Largest inputs: cond_market (+0.62; Batangas −0.96), cond_employment (+0.49, national), D_last, Dnow, H_margin.

## Verdict

**Not eligible.** E55 catches more LOW quarters than E38 (4/6 vs 2/6) and has a higher AUC (0.81 vs 0.65). But its accuracy (0.673) and balanced accuracy (0.670) are below 0.75, and its Brier score (0.214) is worse than persistence (0.200). No difference with E38 or persistence is significant. No further tuning.

# E172 results: E168 plus the training out-of-fold decision cutoff

- **Protocol:** `docs/e172/PROTOCOL.md` (blob 91d28950, commit c25e0b71), locked before this run.
- **Code:** `backend/app/e172/cutoff.py`.
- **Outputs:** `backend/data/e172/out/rows.csv` and `results.json`.

**Replication check:** E172's test probabilities equal E168's exactly at every lead (largest difference 0.0). The cutoff is the only change.

## Cutoffs chosen on training rows only
| Lead | ENNS 2018 | ENNS 2019 | ENNS 2021 |
|---|---|---|---|
| 1–2 | 0.30 | 0.30 | 0.475 |
| 3–6 | 0.30 | 0.30 | 0.425 |
| 7–8 | – | 0.30 | 0.30 |

The training rows favoured a **lower** cutoff than 0.5. On test rows this produced more false HIGH alarms.

## Mean fold accuracy (thesis Algorithm 3)
| Lead | E172 | E168 (cutoff 0.5) | Persistence |
|---|---|---|---|
| 1 | **63.3 %** | 74.7 % | 62.4 % |
| 2 | 64.7 % | 77.4 % | 62.4 % |
| 3 | 62.0 % | 74.5 % | 62.4 % |
| 4 | 66.0 % | 72.8 % | 62.4 % |
| 5 | 64.7 % | 71.3 % | 62.4 % |
| 6 | 64.7 % | 68.5 % | 62.4 % |
| 7 | 48.0 % | 70.0 % | 64.0 % |
| 8 | 48.0 % | 66.0 % | 64.0 % |

**At Lead 1:**
- **E172:** precision 0.489, recall 0.92, F1 (HIGH) 0.639, weighted F1 0.639, AUC 0.891.
- **E168:** F1 0.710, weighted F1 0.756.

## Decision (rule fixed in the protocol)
- **Maximum Reliable Lead Time under Algorithm 3:**
  - E172: 0
  - E168: 0
  - persistence: 0
- **E168 stays.** The thesis decision-cutoff step, applied with training rows only, lowers accuracy by about 11 points at Lead 1.

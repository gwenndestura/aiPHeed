# E184: E168 with synthetic training data balanced 50/50. Report

## Status: **passes the owner's deployment rule. Not staged and not deployed (owner: "do not deploy it yet"). E168 stays in production.**

E184 is E168's selection plus one synthetic training row per real row, at equal weight. The synthetic rows are made by
jitter of 0.5 × input SD near the 50 % line, with HIGH and LOW kept balanced, and the forecast is the mean of seeds
17901–17905 (`docs/e184/PROTOCOL.md`, committed `ac08d87` before any output). The 72 real rows per lead have been read by
earlier experiments, so these scores are not independent evidence. The ENNS 2022 seal is.

## Accuracy at the three served leads (72 real provincial forecasts each)

| Lead | Model | Accuracy | Balanced acc. | HIGH precision | HIGH recall | Macro-F1 | AUC | Brier | Cal. slope |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Persistence | 62.5 % | 70.3 % | 0.480 | 0.96 | 0.624 | 0.827 | 0.2128 | 0.71 |
| 1 | E168 | 75.0 % | 78.0 % | 0.595 | **0.88** | 0.745 | 0.891 | 0.1230 | 0.76 |
| 1 | **E184** | **76.4 %** | **78.2 %** | **0.618** | 0.84 | **0.756** | 0.891 | **0.1211** | **0.82** |
| 2 | Persistence | 62.5 % | 70.3 % | 0.480 | 0.96 | 0.624 | 0.827 | 0.2128 | 0.71 |
| 2 | E168 | 77.8 % | 80.2 % | 0.629 | **0.88** | 0.771 | **0.893** | 0.1221 | 0.71 |
| 2 | **E184** | **79.2 %** | **80.3 %** | **0.656** | 0.84 | **0.782** | 0.890 | **0.1185** | **0.77** |
| 3 | Persistence | 62.5 % | 70.3 % | 0.480 | 0.96 | 0.624 | 0.827 | 0.213 | 0.71 |
| 3 | E168 | 75.0 % | 77.1 % | 0.600 | 0.84 | 0.700 | 0.873 | 0.1352 | 0.70 |
| 3 | **E184** | **77.8 %** | **79.2 %** | **0.636** | 0.84 | **0.769** | **0.889** | **0.1258** | **0.77** |

- **Confusion (E184).** It catches 21 of 25 HIGH provinces at every lead. E168 catches 22, 22 and 21. E184 raises fewer
  false alarms: 13 / 11 / 12, against E168's 15 / 13 / 14.
- **Against persistence.** E184's Brier score is significantly lower at every lead:

  | Lead | Brier difference vs persistence |
  |---|---|
  | 1 | −0.092 [−0.147, −0.046] |
  | 2 | −0.094 [−0.148, −0.049] |
  | 3 | −0.087 [−0.136, −0.047] |

- **Against E168:**

  | Lead | Brier difference vs E168 | McNemar (E184 only right / E168 only right) |
  |---|---|---|
  | 1 | −0.0019 [−0.0107, +0.0061] | 3 / 2, p = 1.0 |
  | 2 | −0.0036 [−0.0101, +0.0028] | 3 / 2, p = 1.0 |
  | 3 | **−0.0094 [−0.0165, −0.0029]** | 2 / 0, p = 0.5 |

  Only the Lead 3 Brier difference is significant.

## Checks
| Check | Result |
|---|---|
| Owner's deployment rule: ≥ 75 % and Brier CI vs persistence < 0 at Leads 1, 2 and 3 | ✅ all six conditions |
| Leakage (corrupted unreleased rounds) | ✅ 0.0 |
| E184 equals E181's recorded forecasts for the same setting | ✅ max \|Δp\| 2.2 × 10⁻¹⁶ |
| E168 part equals the stored E168 rows (Leads 1–3) | ✅ 0.0 |
| Strict "better than E168" rule (Brier CI < 0 at Leads 1 and 2, beats shuffled) | ❌ |
| Beats its shuffled-trigger control | ❌ +0.0013 [−0.0123, +0.0182] |

**The shuffled-trigger result is the same caveat as E182.**
- E184 with the trigger inputs scrambled across provinces scores about as well as E184 (Brier 0.1198 against 0.1211).
- Its small gains over E168 therefore cannot be credited to better use of the inputs. They are best read as a slight
  smoothing of the probabilities.
- The model's skill comes from the survey baseline.

## ENNS 2022 seal
- **File:** `backend/data/e184/out/sealed_enns2022.json`.
  - SHA-256 `c4785694a6b7d04baf09c32bd0e4fdf92ad0c74815f8c460d6375aff58308a09`.
  - 156 forecasts, every province × Leads 1–2.
- **E168 check.** The E168 part matches E168's seal to its rounding.
- **Discriminating rows.** E184 calls 31 provinces HIGH against E168's 29 and changes the class on 4. ENNS 2022 will
  decide between them on those rows.

## Deployment (on hold)
These steps are prepared, tested, and **not run**.

1. `python -m app.e184.serve stage` would:
   - write E184's live forecast for the production issue (2027-Q1 to Q3, with driver bars and data-completeness flags)
     to `backend/data/e184/issues/`;
   - register E184 in the registry as a candidate with its gate record.
2. Then the owner promotes it with `python -m app.e184.serve promote --approver "<name>"` and restarts the backend.
3. Rollback: `python -m app.e184.serve rollback --approver "<name>"`.

Tests (`tests/unit/test_e184_deploy.py`) show two things:
- with E168 in production, the dashboard is unchanged;
- after a simulated promotion, the dashboard, outlook, strict check and accuracy texts show E184, and the monthly E168
  refresh no longer promotes over it.

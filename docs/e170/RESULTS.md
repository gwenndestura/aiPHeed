# E170 results: retrospective run (once, as locked) — NOT ACCEPTED

**Run details:**
- Protocol: `docs/e170/PROTOCOL.md` (blob ef63fe67, commit 9526e8bc).
- Code: `backend/app/e170/model.py`.
- Rows: `data/e170/out/all_rows.csv`.
- Gates: `data/e170/out/results.json`.

**Pooled set:** retrospective rows only. **No qualifying prospective provincial HFIAS outcomes exist yet.**

## Decision: **NOT ACCEPTED. E158 stays in production.**
| Requirement (protocol 3.4–3.5) | Result |
|---|---|
| C1–C6 at Lead 1, pooled | ❌ C1, C2, C3 and C5 fail; C4 ✅ (slope 0.59–1.02), C6 ✅ |
| Leakage ≤ 1e-9 | ✅ 0.0 |
| Real inputs no worse than shuffled (CI upper bound ≤ 0.005) | ❌ +0.006 [−0.0014, +0.0146] |

**Maximum reliable lead: 0.**

## Lead 1 against the earlier models (n = 72)
| | Correct | Accuracy | Brier | Bias by round (2018 / 2019 / 2021, points) |
|---|---|---|---|---|
| E158 (production) | 53 | 73.6 % | 0.134 | — |
| E168 LightGBM-only | 54 | 75.0 % | 0.123 | +6.8 / +3.9 / −1.3 |
| **E170 two-part** | **47** | **65.3 %** | **0.178** | **+9.2 / +6.3 / +6.9** |

**Leads 2–8:** 62.5–65.3 % at Leads 2–6 and 58 % at Leads 7–8 (n = 50). C4 passes at every lead. C1 fails at every lead.

## Why it failed (diagnosis after the run; it changes nothing in E170)
| Round | Level source at origin | Level used | Observed round mean |
|---|---|---|---|
| ENNS 2018 | HFIAS 2015 round | 55.8 % | 47.4 % |
| ENNS 2019 | HFIAS 2015 round | 56.3 % | 49.2 % |
| ENNS 2021 | HFIAS 2019 round | 48.1 % | 41.6 % |

- **E170 holds the regional level fixed at the newest survey round.** Food insecurity **fell between every pair of rounds** from 2015 to 2021, so a held level is too high every time. The result is +6 to +9 points of bias in all three rounds, including 2021.
- **E168 partly tracked that downward drift.** Its LightGBM change model could use market and price timing; that was the one group with a demonstrated contribution. E170 lets LightGBM model only the provincial **deviation**, which removed exactly that signal.
- **The calibration problem is solved:** C4 passes because the provincial deviations are well scaled (within-round slope 0.84–1.03). **The accuracy problem got worse.**
- **The FIES bridge did not take part in any retrospective round.** No regional FIES had been published before any origin. It is used only in the 2027-Q1 seal.

## What C1 now needs
Pooled with this retrospective (47/72), C1 would need **96 new provinces at 80 %, 64 at 85 %, or 48 at 90 %**. That is not realistic, so **E170 cannot reach acceptance through the prospective route either.**

## Lesson for any successor (would need a new, separately locked protocol)
The level must not be held. It needs a **forecast of level change**, from time-level signals, especially market and prices, as E168 used. That would keep E170's well-calibrated provincial deviation and E168's level-drift tracking.

E170's own constants and rules are **not** changed. Under protocol section 4, the successor would be a new experiment, with its retrospective reported as **informed by E170's result**.

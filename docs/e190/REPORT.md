# E190 results: truly class-balanced synthetic data (local only, not committed)

Protocol: `docs/e190/PROTOCOL.md`, whose SHA-256 was logged before the run. Outputs are in `backend/data/e190/out/`.
The E184 arm re-run here equals the stored E184 rows at all six leads (maximum |Δp| = 0).

## Realised balance (final fits, mean over the 5 draws)
| Arm | ENNS2018 / 2019 origin: real + synthetic HIGH share | ENNS2021 origin |
|---|---|---|
| E184 | 60.7 % / 60.5 % | 53.1 % |
| E190a (parity allocation) | 57.5 % / 57.2 % (class flips undo part of the parity) | 52.4 % |
| E190b (parity + label-preserving) | **50.0 % / 50.0 %** | **50.0 %** |

E190b folded 37–56 class flips per final fit.

## Accuracy (72 real rows per lead) and false alarms / misses
| Lead | E184 | E190a | E190b |
|---|---|---|---|
| 1 | **76.4 %** (13 FA / 4 miss) | 75.0 % (14 / 4) | 73.6 % (17 / 2) |
| 2 | **79.2 %** (11 / 4) | 77.8 % (13 / 3) | 70.8 % (19 / 2) |
| 3 | **77.8 %** (12 / 4) | 77.8 % (12 / 4) | 73.6 % (17 / 2) |
| 4 | **77.8 %** (12 / 4) | 77.8 % (12 / 4) | 70.8 % (18 / 3) |
| 5 | **75.0 %** (12 / 6) | 72.2 % (15 / 5) | 68.1 % (20 / 3) |
| 6 | **76.4 %** (12 / 5) | 72.2 % (15 / 5) | 72.2 % (16 / 4) |

## Brier against E184 [95 % region-cluster CI]
- **E190a:** worse or equal at every lead except Lead 4 (−0.0002). Significantly worse at Lead 3:
  +0.0041 [+0.0004, +0.0081].
- **E190b:** significantly worse at Leads 1–5. Examples:
  - Lead 1: +0.0112 [+0.0009, +0.0213];
  - Lead 2: +0.0180 [+0.0017, +0.0326].

## Decision (as fixed): neither variant meets the rule; **E184 stays**

## What this shows
- **Exact class balance makes E184 worse, not better.** Forcing 50 % HIGH in training and stopping copies from crossing
  the line raised false alarms (11–13 → 16–20) and reduced misses only slightly (4 → 2–3).
- **Why.**
  - The model forecasts a continuous level, the change from the last survey, and HIGH is just that level ≥ 50 %, so
    class counts are the wrong lever.
  - Folding the outcomes pushes synthetic outcomes away from the 50 % line. The model then learns larger changes than
    really happen.
  - The class flips in E184's jitter are realistic: survey sampling error genuinely blurs the line, and keeping them
    helps.
- **What the over-calling of HIGH on the test rounds reflects** (E189 audit): a period shift (falling food insecurity
  in 2018–2021), not the class mix of the training rows.

# E188 results: 20 synthetic draws (E188a) and survey-noise synthetic rows (E188b)

Run once, following `docs/e188/PROTOCOL.md` (committed before any output; code `e544c15`). The E184 arm re-run here
matches the stored E184 rows exactly at every lead (maximum |Δp| = 0). Nothing was staged or deployed.

## Accuracy (72 real outer rows per lead)

| Lead | Persistence | **E184** | E188a (20 draws) | E188b (survey-noise) |
|---|---|---|---|---|
| 1 | 62.5 % | **76.4 %** | 77.8 % | 76.4 % |
| 2 | 62.5 % | **79.2 %** | **80.6 %** | 77.8 % |
| 3 | 62.5 % | **77.8 %** | 79.2 % | 76.4 % |
| 4 | 62.5 % | **77.8 %** | 76.4 % | 76.4 % |
| 5 | 62.5 % | **75.0 %** | 72.2 % (fails the owner rule) | 75.0 % |
| 6 | 62.5 % | **76.4 %** | 77.8 % | 73.6 % (fails the owner rule) |

## Brier against E184 (negative = better) [95 % region-cluster CI]

| Lead | E188a − E184 | E188b − E184 |
|---|---|---|
| 1 | −0.0012 [−0.0028, +0.0006] | −0.0026 [−0.0070, +0.0018] |
| 2 | −0.0002 [−0.0016, +0.0013] | −0.0009 [−0.0049, +0.0024] |
| 3 | +0.0003 [−0.0020, +0.0022] | +0.0039 [−0.0001, +0.0083] |
| 4 | +0.0002 [−0.0015, +0.0019] | +0.0037 [−0.0009, +0.0082] |
| 5 | +0.0018 [−0.0008, +0.0041] | +0.0008 [−0.0043, +0.0059] |
| 6 | +0.0023 [−0.0013, +0.0065] | +0.0036 [−0.0021, +0.0100] |

- **McNemar tests against E184:** p ≥ 0.5 at every lead.
- **Size of the differences:** the two variants and E184 differ by 0–3 provinces per lead.

## Decision (as fixed): **neither variant meets the rule; E184 stays**
- **E188a** is better at Leads 1–3, with 80.6 % at Lead 2, the first lead at or above 80 %. It is worse at Leads 4–5:
  at Lead 5 it is 72.2 % and fails the owner rule. None of the differences is significant.
- **E188b** removes the artificial input noise. It is slightly better in Brier at Leads 1–2 and worse at Leads 3–6.
  Real input variation therefore helps more than it hurts.
- **What this means.** Averaging more synthetic draws mainly moves the forecasts of the 1–3 provinces nearest the
  50 % line. The resulting gain or loss of one or two provinces per lead is within noise.
- **E188a at Lead 2 does not show that the model reaches 80 %.** It is one province above E184 at one lead, and it
  comes with a loss at Leads 4–5.

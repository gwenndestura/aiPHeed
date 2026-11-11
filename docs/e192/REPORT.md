# E192 results: trajectory-consistent, correlation-preserving synthetic rows (local only, not committed)

**Sources.** Protocol: `docs/e192/PROTOCOL.md`, whose SHA-256 was logged before the run. Outputs are in
`backend/data/e192/out/`. Each (survey, lead) ran as its own job. **E184 reproduces exactly (maximum |Δp| = 0).**

## Accuracy, false alarms and Brier (72 real rows per lead)
| Lead | E184 | traj (E191's generator, re-run per lead) | E192 (trajcorr, 5 draws) | E192_20 (trajcorr, 20 draws) |
|---|---|---|---|---|
| 1 | **76.4 %** (FA 13, B .1211) | 76.4 % (13, .1224) | 75.0 % (15, .1226) | 75.0 % (14, .1222) |
| 2 | **79.2 %** (11, .1185) | 75.0 % (15, .1225) | 76.4 % (13, .1181) | 79.2 % (12, .1203) |
| 3 | 77.8 % (12, .1258) | **81.9 %** (10, .1253) | 77.8 % (12, .1307) | 77.8 % (12, .1274) |
| 4 | **77.8 %** (12, .1261) | 76.4 % (13, .1300) | 75.0 % (13, .1287) | 76.4 % (12, .1283) |
| 5 | **75.0 %** (12, .1281) | 75.0 % (12, .1292) | 70.8 % (15, .1348) | 72.2 % (14, .1308) |
| 6 | 76.4 % (12, .1286) | 76.4 % (12, .1308) | 77.8 % (11, .1312) | 77.8 % (11, .1315) |

- **Significance.** No McNemar test against E184 has p < 0.05.
- **Brier differences that are significant are against E192.** E192 is significantly worse than E184 at Lead 3
  (+0.0049 [+0.0008, +0.0088]) and Lead 5 (+0.0067 [+0.0012, +0.0122]). E192_20 is significantly worse at Lead 4
  (+0.0021 [+0.0002, +0.0042]).
- **Owner rule.** E192 and E192_20 fail it at Lead 5.

## Decision (as fixed): **neither E192 arm meets the rule; E184 stays**

## What this shows
- **Correlation-preserving trajectory noise did not fix the weaknesses.** Probabilities got worse, not better.
- **The draw-noise test settles the "80.6 %" question.** The same `traj` generator gave:
  - in E191 (lead-sharing stream): **76.4 / 80.6 / 80.6 %**;
  - here (per-lead stream): **76.4 / 75.0 / 81.9 %**.
  The method is identical; only the random numbers changed. Lead 2 moved 5.6 points, so E191's 80.6 % at Lead 2 was
  the luck of one random draw, not a better generator.
- **The 72-row test cannot separate any of these generators from E184.** Their differences are within the variation
  that comes from the random draw alone.

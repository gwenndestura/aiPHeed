# E194 results: E184 averaged over the top-5 configurations (local only, not committed)

**Sources.** Protocol: `docs/e194/PROTOCOL.md`, whose SHA-256 was logged before the run. Outputs are in
`backend/data/e194/out/`.

**Reproduction.** Configuration 1 with draws 17901–17905 equals E184 (maximum |Δp| = 2e-16).

## Accuracy (false alarms / misses, Brier)
| Lead | E184 (official) | E184 converged (E193) | **E194 (top-5 average)** | E194_k3 |
|---|---|---|---|---|
| 1 | 76.4 % (13/4, .1211) | 76.4 % (13/4, .1200) | **77.8 %** (12/4, .1191) | 76.4 % (13/4, .1192) |
| 2 | 79.2 % (11/4, .1185) | 80.6 % (11/3, .1187) | **80.6 %** (11/3, .1188) | 80.6 % (11/3, .1184) |
| 3 | 77.8 % (12/4, .1258) | 77.8 % (12/4, .1274) | **79.2 %** (12/3, .1255) | 79.2 % (12/3, .1258) |
| 4 | 77.8 % (12/4, .1261) | 76.4 % (12/5, .1269) | 76.4 % (12/5, .1252) | 76.4 % (12/5, .1256) |
| 5 | 75.0 % (12/6, .1281) | 73.6 % (13/6, .1279) | 73.6 % (14/5, .1295) | 70.8 % (15/6, .1298) |
| 6 | 76.4 % (12/5, .1286) | 77.8 % (11/5, .1311) | 76.4 % (12/5, .1300) | 76.4 % (12/5, .1304) |

- **Against E184 converged:** McNemar p = 1.0 at every lead. Every Brier CI includes 0. Examples:
  - L1: −0.0009 [−0.0031, +0.0015];
  - L3: −0.0018 [−0.0048, +0.0014].

## Decision (as fixed): **E194 does not meet the rule; E184 stays**
- **Where it fails.** Lead 6 accuracy is 1 province lower (76.4 against 77.8 %), and Brier is higher at Leads 2
  (+0.0001), 5 and 6.

## What it shows
- **Leads 1–3 (the leads the dashboard serves).** E194 is the best result so far: 77.8 / 80.6 / 79.2 %.
  - Accuracy is ≥ converged E184 at all three, and Brier is lower at Leads 1 and 3.
  - The gain is +1 province at Lead 1 and +1 at Lead 3, which is not statistically significant.
- **80 % target.** Leads 1 and 3 are still short: 56 and 57 of the 58 needed.
- **Method.** Averaging configurations is a principled variance reduction, and it is the most stable improvement
  observed. It still does not pass the six-lead rule fixed in advance. Treating it as preferred because of the Lead 1–3
  results would be a post-hoc change of rule.

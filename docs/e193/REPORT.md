# E193 results: E184 with converged synthetic averaging (100 draws) (local only, not committed)

**Sources.** Protocol: `docs/e193/PROTOCOL.md`, whose SHA-256 was logged before the run. Outputs are in
`backend/data/e193/out/`.

**Reproduction.** The first 5 draws equal stored E184 (maximum |Δp| = 2e-16).

## Adopted, as pre-registered, as "E184 (converged)"
| Lead | E184 (5 draws) | **E184 converged (100 draws)** | False alarms / misses (converged) | Brier 5 → 100 draws | Owner rule (converged) |
|---|---|---|---|---|---|
| 1 | 76.4 % | **76.4 %** | 13 / 4 | .1211 → .1200 | pass |
| 2 | 79.2 % | **80.6 %** | 11 / 3 | .1185 → .1187 | pass |
| 3 | 77.8 % | **77.8 %** | 12 / 4 | .1258 → .1274 | pass |
| 4 | 77.8 % | 76.4 % | 12 / 5 | .1261 → .1269 | pass |
| 5 | 75.0 % | **73.6 %** | 13 / 6 | .1281 → .1279 | **fail** |
| 6 | 76.4 % | 77.8 % | 11 / 5 | .1286 → .1311 | pass |

- **Against the 5-draw E184,** no McNemar p is below 1.0 and every Brier CI includes 0. The two are statistically the
  same model, estimated with less noise.
- **Served horizon.** Under the converged estimate it is **4 quarters** (Lead 5 fails), against 6 in E187's 5-draw
  result.

## Convergence (accuracy of the running mean)
| Lead | 5 | 10 | 20 | 50 | 100 draws |
|---|---|---|---|---|---|
| 1 | 76.4 | 77.8 | 77.8 | 76.4 | 76.4 |
| 2 | 79.2 | 80.6 | 80.6 | 80.6 | 80.6 |
| 3 | 77.8 | 80.6 | 79.2 | 77.8 | 77.8 |

## How much luck is in one result
| Lead | Single draw: mean (min–max) | 20 independent 5-draw results: mean ± SD (min–max) |
|---|---|---|
| 1 | 76.9 % (68.1–81.9) | 76.9 ± 1.7 % (72.2–79.2) |
| 2 | 78.4 % (73.6–81.9) | 78.6 ± 1.5 % (75.0–81.9) |
| 3 | 77.8 % (72.2–83.3) | 77.8 ± 1.4 % (75.0–80.6) |

- **The official E184 is typical, not lucky.** Its 76.4 / 79.2 / 77.8 % is within 0.5 points of the mean of 20 5-draw
  replications.
- **Other 5-draw replications reach 79–82 %** at single leads. This is why single "80 %" results from earlier
  experiments did not hold up.

## Conclusion
- **E184's expected accuracy:** about **76.5–77 % at Lead 1, 79–80.6 % at Lead 2, and 78 % at Lead 3.**
- **Only Lead 2 reaches 80 %** after convergence.
- **Leads 1 and 3 settle below 80 %.** The cause is the information in the data (E189 audit), not noise from the random
  draws.

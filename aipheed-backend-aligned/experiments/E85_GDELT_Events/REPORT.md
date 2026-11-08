# E85 — GDELT event signals (report)

**Data.** GDELT GKG (V1 themes, locations and counts; deviation D1), 2021-01-01 .. 2026-10-14.
- 58,576 unique CALABARZON food-shock records, about 1,500–4,600 per quarter.
- Query job eb74ffe2…, 0.543 TiB scanned on the free tier; the project has no billing account, so nothing was
  charged.
- Raw rows are local only (`backend/data/gdelt_e85/`, gitignored). The aggregated features are in `runs/`.

**Result** (run `runs/20261021T101520Z`; same E83/E84 rows and rule): **no gain, measurable harm.**

| Lead | S-COMP-G (with GDELT hunger component) | S-COMP (E84) | Paired Brier, S-COMP-G − S-COMP |
|---|---|---|---|
| 1 | acc 0.754, recall 0.19, Brier 0.167 | 0.815, 0.50, 0.141 | −0.026 (worse; two-sided p 0.064) |
| 2 | acc 0.646, recall 0.00, Brier 0.289 | 0.723, 0.31, 0.250 | −0.042 (worse) |
| 3 | acc 0.569, recall 0.00 | 0.600, 0.12 | −0.008 |

**Learners with GDELT** (M-LR-G, M-GB-G) still issue only 20–30 rows. Their issued-row accuracy at Lead 2 is
0.36–0.44.

**Hunger outcomes at Lead 2** (13 quarters):

| Outcome | Persistence | Always-HIGH | GDELT model |
|---|---|---|---|
| H-BIN | 0.69 | 0.77 | 0.54 |
| H-RISE | — | — | 0.38 (prevalence 0.54) |

- Mean absolute error for H-BIN: GDELT 6.8 vs persistence 5.0.

**Why it fails.**
- The GDELT family shares follow the typhoon calendar: disaster share is 0.5+ in Q3/Q4 and about 0.2 in Q1/Q2.
  Tone moves with it.
- That seasonal pattern does not track SWS hunger, which rose through 2024 and stayed high in 2025–26 regardless of
  season.
- With 6–15 training pairs, the ridge fits noise. These are the same failure signatures as the E73 news check.

**Verdict.** Under the pre-registered rule, GDELT event signals add no predictive value for T43 or for regional
hunger at Leads 1–3. They are not used.

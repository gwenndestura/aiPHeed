# E85 protocol: GDELT event signals for the two-quarter forecast (frozen before the query result is seen)

Branch `e84-objective-continuation`. The researcher approved the GDELT BigQuery scan on 2026-10-21, capped at
maximum_bytes_billed = 1.2e12. This file is hashed and committed before the query runs.

## 1. Question

E84 showed that regional hunger crossing 11.3% two quarters ahead is the binding constraint at Lead 2. Its oracle
bound was HIGH recall 0.81 with S-COMP prices.

**Question:** do dated, full-text-derived event signals (GDELT GKG 2.1) available at the issue date anticipate that
crossing, or the T43 label itself?

## 2. Data

- **Query:** `runner/gdelt_query.sql`, unchanged.
  - Partitions 2021-01-01 .. 2026-10-14 only.
  - Records with a Philippine location naming a CALABARZON province or the region.
  - Food-shock themes.
- **Raw rows** stay local (`backend/data/gdelt_e85/`, gitignored). Aggregated features are committed.
- **Timing.** A record counts at O(t) only if its GKG DATE (publication or crawl time, UTC) is before O(t) − 1 day.
  The day is a safety margin.
- **Duplicates.** One record per DocumentIdentifier is kept, the earliest.

## 3. Features (fixed now)

Each article is assigned theme families by its V2Themes:

| Family | Themes |
|---|---|
| PRICE | ECON_INFLATION, ECON_PRICE*, TAX_FOODSTAPLES*, FOOD_STAPLE*, SHORTAGE |
| FOODSEC | FOOD_SECURITY, HUNGER, MALNUTRITION, FAMINE |
| DISASTER | NATURAL_DISASTER*, FLOOD, TYPHOON, STORM, DROUGHT, EL_NINO |
| AGRI | AGRICULTURE, CROP*, FISH* |
| LIVELIHOOD | UNEMPLOY*, POVERTY, REMITTANCE |
| RESPONSE | AID, RELIEF, HUMANITARIAN |

Each article is assigned to a province when it names a province or its capital, and to the REGION always.

| Feature (per region, and per province) | Definition |
|---|---|
| g_share_{family} | the family's share of all retrieved articles in quarter t before O(t) |
| g_logn | log1p of the article count |
| g_tone | mean V2Tone of the DISASTER, FOODSEC and PRICE articles |
| g_affected | log1p of the summed AFFECT, EVACUATE and KILL counts in V2Counts |
| g_d_* | change of each share against quarter t−1 |

Province values are shrunk to the region with κ = 20 articles.

## 4. Arms (on the E83/E84 evaluation rows, Leads 1–3; Lead 2 primary)

### Primary

**S-COMP-G.** The S-COMP price component (E84, unchanged) times a GDELT hunger component.
- The hunger component is a ridge regression (α = 1, standardised) of H(t'+k) on H_last plus the regional g_share_*,
  g_tone, g_affected and g_d_* features.
- It is fitted on origins t' whose target round was posted before O(t), with at least 8 pairs; otherwise it uses the
  random walk.
- P(H > 11.3) = Φ((Ĥ − 11.3) / s), with s = max(the random-walk sd for the gap, the training RMSE).
- p = P(H > 11.3) × S-COMP P(price).

### Secondary

| Arm | Description |
|---|---|
| M-GB-G, M-LR-G | E84 learner features plus the province GDELT features |
| H-GDELT | the GDELT hunger component alone, scored on H-BIN and H-RISE (regional, 13 quarters) against persistence and always-HIGH |

## 5. Rules

- The E83 PASS rule applies unchanged. Success requires Lead 2 or beyond.
- **News value** is claimed only if S-COMP-G beats S-COMP on paired per-date Brier (sign-flip, one-sided p < 0.10)
  **and** improves Lead-2 HIGH recall.
- **Prospective seal** of S-COMP-G for 2026-Q4, 2027-Q1 and 2027-Q2 from origin 2026-Q3.

# E84 — continuation toward the two-quarter objective (report)

**Branch.** `e84-objective-continuation`.

**Evidence.**
- Protocol: `PROTOCOL.md` (sha256 db9827b5…, commit d2839bf), frozen before any score.
- Run: `runs/20261021T093234Z/`. It uses the same 65 rows per lead and the same baselines and pass rule as E83's
  final run.

## 1. Verdict

**The mandatory objective (Lead 2 or beyond, > 75% with discrimination, beating the baselines) is still not met.**

| Lead | Best arm | Accuracy (unissued = wrong) | Accuracy (issued) | Balanced accuracy | HIGH recall | Brier | Pass |
|---|---|---|---|---|---|---|---|
| 2 | S-COMP (new) | 0.723 | 0.783 (60) | 0.585 | 0.31 | 0.250 | no |
| 2 | E83 S-SIM | 0.692 | 0.750 (60) | 0.522 | 0.19 | 0.276 | no |
| 2 | always-LOW | 0.754 | — | 0.500 | 0 | 0.246 | baseline |
| 3 | S-COMP | 0.600 | 0.709 (55) | 0.440 | 0.12 | 0.296 | no |
| 1 | HYB-W (pre-registered here) | 0.831 | 0.831 | 0.740 | 0.56 | 0.117 | **passes**, but Lead 1 does not satisfy the objective |

## 2. What E84 changed and what it showed

**New information** (Priority 2). All of it was fetched with 2021+ rows only, and each input's publication lag is
verified in `DATA_SOURCES_AUDIT.md`:
- PSA provincial CPI subgroups: rice, corn, meat, fish, oils, fruits, vegetables, sugar;
- PSA 2018 weights;
- IMF world staple prices via FRED, used only four months after the reference month.

**New architecture.** S-COMP projects each food subgroup with its own seasonal drift and aggregates with PSA's own
weights. Rice gets an in-origin pass-through from world rice prices in pesos.

**It does improve the price channel** (diagnostic on the price condition alone, 75 rows):

| Lead | S-COMP | E83 structural | S-COMP without world prices | Persistence |
|---|---|---|---|---|
| 2 | **0.757**, Brier 0.176 | 0.714, Brier 0.199 | 0.686 | 0.631 |
| 3 | **0.785** | 0.646 | 0.723 | 0.583 |

World prices add real leading information about affordability. This is the first input in E40–E84 that improves
the two-quarter price forecast.

**It does not fix T43 at Lead 2, because of hunger.** Oracle decomposition at Lead 2 (60 issued rows):

| Scenario | Accuracy | HIGH recall | Balanced accuracy |
|---|---|---|---|
| S-COMP as it is | 0.783 | 0.31 | 0.63 |
| Perfect regional hunger knowledge + S-COMP prices | 0.783 | **0.81** | **0.79** |
| Perfect price knowledge + hunger random walk | 0.800 | 0.56 | 0.72 |

The binding constraint is whether Balance Luzon hunger crosses 11.3% two quarters ahead:
- the 2023-Q4 and 2024-Q2 surges from 9–10% to 14–20%;
- one survey series, about 22 rounds;
- nothing published monthly that tracks it.

**Learners** (LR and LightGBM with the new features) still fail after the 2025 regime change. They issue only 25–30
rows at Leads 1–2.

**Alternative outcomes** (regional, 13 quarters, Lead 2):

| Outcome | Persistence | Always-HIGH | Ridge (lagged rice inflation + world food) |
|---|---|---|---|
| H-BIN | 0.69 | 0.77 | 0.57 (7 rows) |
| H-RISE | — | always-no 0.46 | 0.71 (7 rows) |

Seven rows cannot support any claim.

## 3. Priority 1 and 3 — data (details in `DATA_SOURCES_AUDIT.md`)

**No legitimate provincial or higher-frequency food-insecurity outcome exists in public sources for 2021–26.**
- WFP HungerMap marks the Philippines "PREDICTED" (a model output).
- PSA FIES is income poverty, collected every three years.
- CBMS 2024 is the only real local outcome, and it is not public.

**The news sources that would give lawful full text or structured events are blocked or need the researcher's action:**

| Source | Status |
|---|---|
| NDRRMC | Cloudflare challenge |
| ReliefWeb API | Needs a registered appname; robots.txt disallows the API host |
| GDELT GKG | About 1 TB raw, or BigQuery billing on the researcher's GCP project |
| Major publishers | Bot challenges, robots disallow, or no permitted route |

None was bypassed.

## 4. System

- **Nothing served was changed.** No arm passed at Lead 2, so the served model stays (the E83/E84 selection rule).
- **E83 improvements remain intact on this branch:**
  - SHAP reproduction tests;
  - the plain-language headline;
  - the 142-LGU outputs and the low-precision flags;
  - the monthly refresh;
  - the archives and seals.
- **The S-COMP price component is a candidate replacement** for the affordability indicator (A1) in FIRI. Serving it
  would change the published index, so it needs the researcher's decision and a FIRI re-evaluation.

## 5. Prospective test

`sealed/e84_prospective.csv` (sha256 ad402660…) holds S-COMP and S-COMP-THR forecasts from origin 2026-10-01 for:
- 2026-Q4 (Lead 1);
- 2027-Q1 (Lead 2);
- 2027-Q2 (Lead 3).

S-COMP projects food inflation rising again and calls Quezon HIGH in 2027-Q1. E83's S-SIM calls every province LOW.
The published 2027-Q1 CPI and SWS data will decide between them.

## 6. What could still move Lead 2 (each needs the researcher)

1. **A hunger signal that leads the SWS survey**, i.e. higher-frequency hunger or food-consumption data for Balance
   Luzon or CALABARZON. Candidates: DSWD/WFP monitoring, OCTA rounds as they accumulate, CBMS 2024.
2. **ReliefWeb API registration and/or approval of GDELT BigQuery costs**, for dated, full-text event signals
   (typhoon damage, crop losses, assistance) to test against hunger rises.
3. **A target decision by the adviser.** Since 2023-Q4, T43 has been price pressure (E83 audit). The price channel is
   now forecastable at 0.76–0.79 two to three quarters ahead. Hunger is not.

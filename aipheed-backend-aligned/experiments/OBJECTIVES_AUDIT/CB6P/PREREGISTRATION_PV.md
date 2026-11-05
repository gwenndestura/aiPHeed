# PV pre-registration: province-specific non-price evidence (fixed 2026-11-05, before any score or fit on these data)

**Development evidence.** C-B6D-E-X, its fits and all earlier results are unchanged references.

## Diagnosis (why provinces currently differ only through prices)

- Eq. 3 (Ch. III) is S = H + 2D.
- H is SWS Balance Luzon hunger, one value per quarter for all provinces.
- D is the province's food-CPI deviation, the only province-specific term.
- Any forecast of the Eq. 3 label can therefore differ across provinces only through what predicts D.
- **Changing what makes provinces differ in the target requires changing Eq. 3: an adviser decision, not made here.**

## New data (`data/raw_prov/`, PSA OpenSTAT, fetched 2026-11-05, SHA-256 in `FETCH_LOG.json`)

| Data | Table | Geography | Period |
|---|---|---|---|
| Palay + corn production (t) | `2E/CS/0012E4EVCP0` | 5 provinces | quarterly 1987–2026 |
| Fisheries production (t) | `2E/FS/0132E4GVFP1` | 5 provinces | quarterly 1980–2026 |
| Subsistence (food-poverty) incidence among families, with CV | `1F/FY/0051F3DF030` | 5 provinces | 2018, 2021, 2023 |
| Poverty incidence among families | `1F/FY/0011F3DF010` | 5 provinces | 2018, 2021, 2023 |

**Not available at province level** (checked): LFS employment (national only on OpenSTAT), OFW remittances (BSP
national), quarterly provincial food-insecurity prevalence.

## Part V: independent provincial validation (no fitting)

- **Outcomes:** PSA provincial subsistence incidence and poverty incidence among families, Y ∈ {2018, 2021, 2023},
  15 province-years.
  - **Disclosed:** subsistence CVs are 17–59% (low precision).
- **Signals compared, each as a province-year mean over the four quarters of Y:**
  - **V1:** the realised Eq. 3 provincial term 2D (spliced CPI, `fi_provincial.py`). Does Eq. 3's provincial part track
    measured provincial food poverty?
  - **V2:** C-B6D-E-X Lead 1 probability (`out/fi_provincial_fits.csv`).
  - **V3:** C-B6D-E-XA Lead 1 probability (Part A).
- **Statistics:**
  - within-year Spearman ρ (n = 5 each);
  - a pooled statistic = the mean of the three within-year ρ, with a permutation p-value (provinces permuted within
    each year, 10,000 permutations, seed 2036, one-sided ρ > 0);
  - for each outcome separately.
- **Reading:** "consistent with measured provincial food poverty" only if the pooled p < 0.05. Otherwise "not shown".
  Low power is stated.

## Part A: candidate C-B6D-E-XA (province non-price supply shocks in the provincial term)

- **Exactly C-B6D-E-X** (C-B6E regional part, spliced D1, THR 11.0, origins, leads, combination), except the D model:
  D̂ = b1·D1 + b2·PC + b3·FI.
- **PC** = the province's palay + corn production year-on-year % change at quarter t − 1, minus the five-province mean
  of that change.
- **FI** = the same construction for total fisheries production.
- **Both:**
  - winsorised to [−100, 100];
  - NaN set to 0 (no information);
  - available at O(t) because quarter t − 1 ended three months before the issue date and PSA quarterly estimates are
    released within about six weeks (disclosed assumption).
- **Coefficients:** least squares through the origin on the past pairs (as in C-B6D-E-X); σ_D = the residual RMSE; the
  same fallbacks.
- **Leakage check:** recompute PC and FI after deleting all production quarters > t − 1; the values must be unchanged.
- **Evaluation:** B-ext (250 rows, q ≥ 2013-Q1), Leads 1 and 2; all metrics, AUC 95% CI, frozen R1–R7, Algorithm 3.
- **Paired Brier (quarter-cluster bootstrap, one-sided), Holm over 6:** XA vs C-B6D-E-X, PERSIST-X, CLIM-X;
  Leads 1 and 2.
- **Contribution:** the share of |b2·PC| + |b3·FI| in |D̂|, and in the provincial index 2D̂/s.

## Decision rules (fixed)

- **XA adopted as the provincial candidate only if all of these hold:**
  - R1–R7 pass at Lead 1;
  - Brier < C-B6D-E-X at Leads 1 and 2 with one-sided p < 0.10;
  - the non-price share of D̂ ≥ 20% on average.
- **Part V is reported whatever the result; it decides nothing automatically.** A negative V1 is evidence for the adviser
  that Eq. 3's provincial term does not track measured provincial food poverty.
- **No further variant on these data.**
PLAN-SHA256: 632f495d1c540cec89486c5a0e85ab4e01a58e396aa040cc839d5412d21c4fae

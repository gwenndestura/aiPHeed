# E130 calibration and uncertainty

## 1. Uncertainty in the reference itself

PFDR values carry PSA sampling error (`E130_TARGET_UNCERTAINTY_AUDIT.md`):
- CVs of 17–62 %;
- SEs of 0.31–1.15 pp;
- 90 % intervals 1.0–3.8 pp wide.

**Every comparison keeps that error.** The tolerance is the reference's 90 % interval, and change tests use both rounds' SEs.

## 2. Model error versus measurement error

The observed miss is (forecast − truth) − (reference − truth). With independent errors:

E[miss²] = E[model error²] + SE_ref²

**Three consequences:**
- A perfect forecast still misses by SE_ref on average.
- A prediction interval for the *observed* reference must add SE_next to the forecast's own uncertainty.
- A model can look better than raw persistence on a noisy reference purely by smoothing. The frozen N4 therefore also requires beating climatology (DEVIATIONS V1).

## 3. The sealed survey-year intervals

The 90 % prediction interval is

pred ± 1.645 √(s²_change + SE_next²)

with s²_change = 7.15 pp², the 2021→2023 true-change variance net of sampling error, and SE_next taken equal to the 2023 SE.

**The intervals are wide:** half-widths of 4.4–4.5 pp, and every lower bound truncated at 0. Over two years, provincial food deprivation moved by up to 5.7 pp (Quezon), and nothing in the data narrows that.

**Interpreting coverage.** With five provinces and these widths, coverage will very likely be 5/5. That says little: these are honest, uninformative intervals, not a calibrated model.

## 4. Uncertainty by province

- **Widest:** Rizal (SE 0.64 in 2023) and Cavite (CV 62 %).
- **Narrowest:** Quezon 2023 (SE 0.36).

In 2021 Quezon was the noisiest in absolute terms (SE 1.15).

## 5. Growth with horizon

| Level | What the data show |
|---|---|
| Regional quarterly (SWS, E80 / E128) | Persistence error grows with the information horizon. At the quarter-start issue the dashboard's Lead 2 is 3 quarters past the newest SWS reading (19 of 21 rows); after the mid-quarter release it is 2. |
| Provincial survey-year | One step is two years, with true-change SD ≈ 2.7 pp. There is no shorter provincial step to measure. |
| Planning model | For a stable quarterly AR(1), persistence error variance grows as 2(1 − ρʰ) + 2SE², so each extra quarter of horizon adds error until ρʰ ≈ 0 |

## 6. Calibration checks for a future run (protocol §8, N7)

- 80 % intervals from training-only residuals (split-conformal within the expanding window), widened by the reference SE.
- Coverage must fall between 0.70 and 0.90 at every lead.
- Residuals are reported by province and by lead.

**None of this could be run here:** there are no out-of-sample provincial rows.

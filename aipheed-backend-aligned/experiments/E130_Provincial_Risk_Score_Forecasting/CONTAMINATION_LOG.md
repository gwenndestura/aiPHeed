# E130 contamination log

## X1 · 2026-10-31, search S1 (after the freeze)

**What was seen.** The search-engine summary for the PSA 2025 full-year poverty query showed these values:
- national poverty incidence among families, 2025: 6.4 %;
- population, 2025: 9.7 % (secondary report);
- every region decreased significantly from 2023 to 2025;
- no province above 30 % poverty incidence in 2025;
- national subsistence incidence 2023: 2.7 % of families and 4.3 % of the population.

**Effect on the seal: none.**
- The survey-year seal (`sealed/E130_SURVEY_YEAR_SEAL.csv`, sha256 `94a08cd1…`) was frozen and committed (`b58c48e`) before the search.
- No provincial subsistence value for any of the five provinces was seen before acquisition.
- The national and regional poverty values are context, not seal targets.

**Effect on later work.** Any forecast of the 2025 round made after this point would know that poverty fell nationally between 2023 and 2025. E130 therefore makes **no new 2025 forecast**. Only the sealed forecasts are scored.

## X2 · 2026-10-31, search S3 (after the freeze)

**What was seen.** 2025 provincial **poverty incidence among families**: Quezon 8 %, Laguna 3.1 %, Rizal 2.7 %, Cavite 1.2 %, Batangas 0.9 %; CALABARZON 2.7 % (5.3 % in 2023).

**Effect.** Not a seal target: the seal targets subsistence incidence among the population. The values are correlated with the targets, though, so **no forecast of 2025 provincial values may be made or revised after this point**. The frozen seal (`94a08cd1…`, committed `b58c48e`) is the only 2025 forecast E130 scores.

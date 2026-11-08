# Deliverable 12. Production adoption decision

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

**Decision: the current production model stays unchanged. No challenger is eligible.**

- P0H4 remains served. It is the best-validated model **for its own target (T43c, Lead 1)**. The provincial outcomes do not
  validate it as a provincial food-insecurity forecaster: it can be matched to one five-province wave of food poverty
  (2023), where its agreement is not significant, and its provincial signal (price pressure) is negatively related to
  provincial food poverty in the only multi-wave test.
- No other model performs better on any provincial outcome. FI10 is worse than every positive baseline on food poverty.
- Nothing was changed in production: P0H4 artifacts, predictions, dashboard leads, map and indicators are untouched;
  FI12 writes only `backend/data/fi12/` and `docs/fi12/`.

**Recommended wording changes (owner decision, not made):**
- The welcome tour and map legend should not say the map forecasts food insecurity "in each CALABARZON province". A
  defensible wording: "regional hunger outlook combined with each province's food-price pressure".
- Show the dated FNRI 2015, ENNS and PSA food-poverty values as provincial references with their source and year.

**Rollback:** not applicable; nothing was deployed. To remove FI12, delete `backend/app/fi12`, `backend/data/fi12`,
`docs/fi12` and `backend/tests/unit/test_fi12.py`.

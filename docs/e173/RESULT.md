# E173 result (2026-11-07): insufficient independent evidence

- SIMPLE frozen: config SHA-256 `ad38a0f17f51b8917ce93840150818bd037bd20f86ece08b588f08029136424e` (`data/e173/out/simple_config.json`).
- Independent data: none. FNRI Heat Map API (124 areas) has no provincial round after 2021; 2023 NNS is regional and FIES only.
- Sealed prospective forecasts (`data/e173/out/sealed_prospective.json`, written once): SIMPLE and E168, all 78 panel provinces,
  Lead 1 (2027-Q1) and Lead 2 (2027-Q2), issued as of 2026-10-01. Leakage control 0.0; E168 reproduces its served 2027-Q1 (0.0).
  The two models give the same HIGH/LOW class for every province at both leads (7 HIGH each).
- Decision under protocol section 4: **insufficient independent evidence**. SIMPLE is neither adopted nor rejected; E168 stays the
  thesis model. The test runs once, when DOST-FNRI publishes the next provincial HFIAS round (>= 40 provinces).

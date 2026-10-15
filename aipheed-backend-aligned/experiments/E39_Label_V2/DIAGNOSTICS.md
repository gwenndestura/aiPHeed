# E39 diagnostics: Food Price Pressure (exploratory)

Labels only, no model. Nothing here changed the frozen specification (4% fixed).

- Labelled dates, A and B: 23 (2021-Q1..2026-Q3). The quarters missing for SWS (2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3) all have CPI-based values.
- Labelled dates, C (regional hunger): 19.
- D1 HIGH overall: 54/115 (47.0%). By year: 2021 14/20, 2022 10/20, 2023 17/20, 2024 5/20, 2025 3/20, 2026 5/15
- D2 dates with at least one HIGH province: 16; with none: 7 (2021-Q4, 2022-Q1, 2024-Q1, 2025-Q2, 2025-Q3, 2025-Q4, 2026-Q1).
- D3 mixed dates: 11; all five HIGH: 5 (2021-Q1, 2021-Q3, 2022-Q4, 2023-Q1, 2023-Q3).
- D4 recomputation: 100 rows vs the PSA published quarter means, max diff 3.3e-09; labels reproduced: True.
- D5 sensitivity (information only): 3pct: HIGH share 60.9%, dates with HIGH 19, kappa vs 4% 0.73; 5pct: HIGH share 34.8%, dates with HIGH 14, kappa vs 4% 0.75
- D6 context only: mean food inflation by province {'Rizal': 5.146, 'Quezon': 4.606, 'Batangas': 4.43, 'Laguna': 4.364, 'Cavite': 4.264}; PSA 2021 poverty {'Quezon': 19.65, 'Cavite': 9.91, 'Batangas': 8.79, 'Rizal': 7.06, 'Laguna': 6.04}; Spearman 0.00 (n = 5). NNS 2023 FIES 19.1% is a different construct; no validation is claimed.
- D7 v1 vs v2: agreement 52.9% on 85 rows. v1 HIGH follows regional hunger above a lagging median (shared by all provinces); v2 HIGH follows each province's own food inflation above 4%. They disagree when hunger is high while food inflation is low (2024-2026) and when food inflation is high while hunger is near its median (2022-2023).
- D8 each label uses only its own quarter's published CPI (and, for C, its own posted rounds); the only constant is 4.0 (BSP target ceiling); no reference window, no fitted anchor

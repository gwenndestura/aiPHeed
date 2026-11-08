# E108 Deliverable A: root-cause report (why E107 fails)

**Written before any E108 model was scored.** Numbers come from `out/diagnosis.json` (`runner/diagnose_e107.py`), from E107's stored outputs and from the data. No E108 model output existed when this was written.

## 1. Verified facts (Phase 1 inventory)

| Question | Verified answer | Evidence |
|---|---|---|
| Target of the production LightGBM (E56) | **PS**, provincial food-price pressure (food CPI YoY > P60, or food − headline > gap P60), two quarters ahead. It is multiplied by a regional hunger component (I7) to give P(T43). The served dashboard number is FIRI v2, where the LightGBM output is indicator A1 only. | `e56_lib.PriceLGB2.fit` (`y = fit["PS"]`); `thesis_system.firi_for` |
| Target of E107 | **T43** directly: HIGH iff SWS Balance Luzon hunger > 11.3 AND PS. R (hunger > 11.3, regional) was the outcome check. | `E107/PROTOCOL.md` §2 |
| The 12 indicator families | FIRI v2 A1, A2, A3, V1, C1, C2, C3, C4, E1, E2, N1, H1 (`firi.LABELS`) | E107 test `test_all_twelve_families_are_model_columns` (re-run: 51/51 pass) |
| How they enter E107 | 13 columns; A1 as the CPI base-effect projection minus the province threshold (2 columns) | `e107_lib.INVENTORY` |
| Dashboard/FIRI-only use | In E107 none; all 12 are model columns. In production, V1, C1, N1 and H1 are FIRI-only, and A1 is the model's own output. | E107 `AUDIT.md` §2 |
| Independent target observations | **19 SWS outcome quarters** (production rounds). T43: 95 province-quarter rows, 18 HIGH. PS: 115 rows over 23 quarters, 52 HIGH (CPI exists for 2021-Q1, 2022-Q1, 2025-Q2 and 2025-Q3, which have no SWS round). | `diagnosis.json` → `counts` |
| Provincial vs regional/national observations | Provincial: CPI-based PS and the price part of T43. Regional: SWS hunger, which is one value per quarter repeated for five provinces. | — |
| Indicators that repeat one value across provinces | **C1, E1, E2, H1** (max 1 distinct value per origin). C2 varies (≤ 3). The rest vary by province. V1 varies by province but never over time. | `diagnosis.json` → `variation` |
| Data available at each issue date | CPI through month 2 of *t*; SWS rounds posted before O(*t*); production, LFS, remittances and rice through *t* − 1; typhoons through *t*; PAGASA items and headlines before O(*t*). Verified by E107 future-perturbation tests. E1 was spot-checked against raw LFS at four origins and matches exactly. | `diagnosis.json` → `e1_alignment_checks` |
| Quarters that influenced development | **All outcome quarters through 2026-Q3** (E38–E107). E107's final block was untouched only within E107. | E107 `AUDIT.md`, `EXPERIMENT_REPORT.md` |
| Untouched / exploratory / retrospective / prospective | No untouched historical quarter exists. All E108 retrospective results are development evidence. The only prospective tests are the sealed E107 forecasts (`246700a8…`, not opened) and the E108 seal to be written. | — |

## 2. Why E107 fails: verified defects vs hypotheses

**V1, verified: the direct learner is taught that price pressure means LOW.**
- T43 is an AND of a regional condition (hunger) and a provincial condition (price). From 2021-Q3 to 2023-Q3, hunger was at or below 11.3%, so **24 province-quarters with price pressure are labelled LOW**.
- In E107's training sets these are 58–83% of all price-pressure rows (24 of 29 at the first Lead-1 origin, 24 of 41 at the last).
- The price projection therefore separates T43 classes only weakly in training (AUC 0.57–0.82). On PS labels it separates them strongly (0.92–0.95 at Lead 1).
- The learner has to discover the AND interaction from 2–6 HIGH quarters. It cannot.

**V2, verified: national series become period markers.**
- At the first Lead-2 origin the national unemployment change E1 separates the training classes with AUC 0.96, while the price projection reaches only 0.57.
- E1, E2, C1 and H1 have one value per quarter. With 5-row minimum leaves, one leaf can be a single quarter, so the tree can isolate the 2023-24 HIGH quarters by their national values.
- On PS labels, the same national series have AUC 0.20–0.64 (mostly below 0.5). They do not mark the PS classes.
- This explains why E107 called 15 of 20 LOW rows HIGH at Lead 2 (`e107_behaviour`).

**V3, verified: N1 cannot contribute, because of coverage, not alignment.**
- FSSI-v3 is missing for 83% of province-origins.
- E107 training sets hold only **2–14 non-missing N1 rows**.
- A split on N1 with 5-row leaves on both sides is therefore almost impossible, and its zero importance is a data-coverage fact.
- It is not evidence that news carries no information, and not a timing bug (E107 as-of tests pass).

**V4, verified: eligibility wasted evaluable quarters.** The direct learner needed 5 HIGH T43 rows, which exist only from 2023-Q4, so Leads 2–4 had only 4–5 evaluable quarters. PS labels exist for every complete CPI quarter, so a model of the price part can be trained from 2022.

**H1, hypothesis, not a defect: the reliability rule's G3 block is degenerate.** The last four quarters hold 1 HIGH row in 20, so "always LOW" has the best Brier score there. This is a property of the 2025–26 disinflation period. E108 keeps the rule unchanged (no relaxation) and reports G3 as it falls.

**H2, hypothesis: the regional hunger series is not forecastable beyond its latest reading.** It is consistent with E69/E76/E107 (persistence and H1 beat every model on R). E108 tests it again with level forecasts.

**No leakage defect was found.** The E107 future-perturbation, split-integrity and as-of tests all pass on re-run (51/51).

## 3. Target and data limitations that no code change can remove

1. **No measured provincial food-insecurity outcome exists in the project.** T43 is a constructed composite risk proxy. Its observed food-insecurity component (SWS) is regional, Balance Luzon (Luzon outside Metro Manila), not CALABARZON only.
2. **Hunger exceeded 11.3% in every outcome quarter from 2023-Q4 to 2026-Q3.**
   - In that period T43 = PS row for row, so discrimination there is price-pressure discrimination.
   - Before 2023-Q4, T43 is LOW whenever hunger was low, which is easy to forecast by hunger persistence.
   - E108 therefore adds a criterion on the hunger-elevated quarters (G4) so that easy LOW quarters cannot carry the verdict.
3. **19 outcome quarters** (23 for PS). Any horizon has at most 9–14 evaluable quarters, so confidence intervals stay wide.
4. **Disputed SWS rounds** (2025-Q2, 2025-Q3). Production rounds stay primary; all-round labels are a sensitivity analysis.
5. **Revisions and vintages** are not reconstructed. Real-time validation is not claimed.

## 4. What E108 changes, and why (each change answers a verified defect)

| Defect | Change in E108 | Kept fixed |
|---|---|---|
| V1 contradictory labels | **Factor the AND rule** as P(T43) = P(hunger > 11.3 at *t* + *k*) × P(PS at *t* + *k*). LightGBM learns the provincial price part from PS labels, which agree with the price signal. The hunger part is H1, the served regional outlook. | Target T43, its thresholds and production rounds |
| V2 period markers | **Minimum leaf of 15 rows** (three quarters of five provinces), so no leaf can isolate one or two quarters through a national value | All 12 families, 13 columns, the same 8-configuration grid |
| V3 N1 coverage | None possible without new data. Reported as a limitation. | N1 stays in the model |
| V4 eligibility | Eligibility depends on the PS training labels the model actually uses | The same minimum counts (6 quarters, 5 HIGH, 5 LOW rows) |

Remaining constraints are data constraints (sections 3.1–3.4), not implementation defects.

# Final execution summary (2026-11-04)

**Scope:** the master research and implementation prompt, Phases A–G.
- Local only. Nothing committed, pushed, merged, deployed or sealed.
- C-b (67baec66) is still the main model.
- 200 protected files unchanged.

## What was done

| Phase | Work | Result |
|---|---|---|
| A. Reproduce | C-E2 refit from scratch; hashes; registry | Byte-identical outputs; all 10 plan hashes verified |
| B. Backend | `/api/v1/config` derived from the served evaluation; FIRI identity bug fixed in `servingModel` and `modelPerformance`; `why_not_longer` fixed | C-E2 demo reports MRLT 3 and model ALLBASE-CE2; +5 tests; 1,022 passed |
| C. NLP | Annotation v2 (adjudication, κ, F1, confusion, sentiment); FSSI redundancy analysis | Ready for 2 annotators. FSSI: 10 labelled quarters, ρ 0.45 n.s., redundant with prices (ρ 0.78) |
| D. Geospatial | 5 provinces and 142 LGUs re-verified; poverty-only, exposure and two-dimension alternatives; adviser brief | Density lifts less-poor urban LGUs; decision left to the adviser |
| E. Forecasting | Error-level dataset; survey-label uncertainty; hypothesis screen | 13/62 labels are within SWS sampling noise, and half of the Lead-1 errors are on them. No new fit is justified |
| F. Baselines | Full 14-test table with CIs and effect sizes; power analysis | 4/14 significant; "beats all" unreachable at current effects (LOGIT L1 needs about 19,000 quarters) |
| G. Validation | Full tests, integrity, seal dry runs | 1,022 passed / 18 skipped; 200/200 protected OK; both seal dry runs replay exactly; ledger untouched |

## Defects found and fixed

1. `/api/v1/config` horizon and caveat were hard-coded C-b text (wrong for C-E2).
2. `servingModel` and `modelPerformance` reported FIRI v2 in food-insecurity mode (wrong for both C-b and C-E2).
3. `why_not_longer` assumed Lead 3.
4. (Earlier today) the C-E4 runner overwrote C-E3's outputs.

## Not achieved (and why)

- **R3 / R7:** label noise near 11.3%, one regime change, and 21 quarters per third. Five pre-registered fixes failed.
- **Beat all seven baselines:** 4 of 14 significant. The effects against the logistic models are too small for 62
  quarters.
- **NLP predictive value:** no material gain.

## Data acquisition (Part 11)

| Source | Publisher | Scope / time | Compatible with the target? | Status |
|---|---|---|---|---|
| Further SWS hunger rounds (2027+) | SWS | Balance Luzon, quarterly | ✅ Same target | **The only route to new independent labels:** about 4 per year, through the sealed holdout |
| SWS Metro Manila, Visayas and Mindanao | SWS | Other areas, 1998+ | ❌ Different geography. Already used as training rows (pooled table), not as evaluation labels | Do not pool as BL evidence |
| BL rounds 1998–2009 | SWS | Same target | ✅ Target compatible | Labels exist. The baselines LOGIT, PSA-only and LGBM-GOV start 2009-Q4, and the prompt forbids changing the evaluation period. **A separately pre-registered secondary window would need your approval** |
| DOST-FNRI ENNS food insecurity (FIES) | DOST-FNRI | Regional (2023: CALABARZON 19.1%); provincial availability unverified | ⚠️ Different measure, not quarterly | Face validity only; could validate the LGU or province ranking if provincial tables can be obtained |
| PSA LFS, CPI, crops, fisheries; IMF BOP | PSA / IMF | National or regional, monthly or quarterly | Predictors, not labels | Already used; adding more predictors does not add labels |
| News archives before 2021 | Outlets / GDELT | National | Predictor | Could extend the FSSI backwards (more news-era quarters for the NLP baselines). **Licensing and access unverified** |

## Needs your explicit approval

1. **Seal C-E2** for the 2027-01-01 issue: add it to the prospective registry, then seal between 1 and 15 Jan 2027.
2. **Commit** the changes listed in `CHANGED_FILE_INVENTORY.md`.
3. **A pre-registered 1998–2009 secondary evaluation**, reported separately; it does not replace the primary.

## Needs others

- **Two team members:** label the 300 headlines.
- **Adviser:** D3.1 and D3.2; adoption of C-E2 or S1.
- **50 DA evaluators:** the ISO/IEC 25010 survey (ongoing, untouched).

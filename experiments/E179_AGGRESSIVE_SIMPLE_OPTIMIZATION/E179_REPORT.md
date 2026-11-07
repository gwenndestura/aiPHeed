# E179: broad LightGBM optimisation of SIMPLE (EXPLORATORY, test-informed comparison disclosed) (2026-11-07)

## What was run
44 LightGBM configurations at every issue (ENNS 2018 / 2019 / 2021 × Leads 1-3), each with E168's anchors (chosen per issue on
training rows), temperature shrink and HIGH line; `candidate_registry.csv` lists them (8 complexity settings R0-R7 × 5 input sets
GOV / FULL / GOV_S / GOV_A [+ previous survey level] / GOV_AX [+ previous level + price × climate × production interactions], plus four
5-seed ensembles). Forecasts in `all_rows.csv`; scoring by `score.py` with the unchanged `app.e156.leads.evaluate`.
Leakage control for the training-selected model: randomising future survey rounds and SWS changed no output (0.0).

## Results (Lead 2 unless noted; `experiment_results.csv`, `evaluation_comparison.csv`)
| Model | How chosen | L1 | L2 | L3 | L2 C1-C6 | L2 Brier | L2 AUC |
|---|---|---|---|---|---|---|---|
| E168 (served) | pre-registered | 56 | 55 | 54 | 5/6 | 0.137 | 0.887 |
| SIMPLE (E172) | post hoc subset | 56 | 59 | 57 | 6/6 | 0.144 | 0.874 |
| **E179 TS** | **training-only selection among the 44** | 52 | 54 | 55 | 5/6 | 0.146 | 0.875 |
| E179 TS + training-only threshold | training only | 50 | 51 | 52 | 5/6 | 0.146 | 0.873 |
| **E179 BEST72 = R2 / GOV / single seed** | **best Lead-2 count of 44 on the 72 rows (test-informed)** | 57 | **59** | 57 | **6/6 (also L1, L3)** | **0.136** | **0.894** |
| All 44 configurations | — | | 50-59 (median 56) | | | | |

## Answers
1. **Highest Lead-2 accuracy:** R2 / GOV / single seed (3 leaves, depth 2, min child 20, L2 10; official inputs): 59/72 = 81.9 %.
2. **Exceeds SIMPLE's 59/72?** No: it equals it.
3. **All six criteria?** Yes, at Leads 1, 2 and 3.
4. **Brier improved?** Yes vs E168 (0.136 vs 0.137, marginal) and vs SIMPLE (0.144).
5. **ROC-AUC improved?** Yes: 0.894 vs E168 0.887 and SIMPLE 0.874.
6. **More stable?** Seed averaging changes 2-5 of 216 classes (`stability_analysis.csv`); the single-seed configuration is not unstable.
7. **What produced it:** lower complexity (3 leaves, larger minimum leaf, stronger L2) on official inputs only, at every issue; the extra
   features (previous survey level, interactions, SWS trend) did not help.
8. **Selected using the previously inspected outcomes?** **Yes.** It is the best of 44 configurations scored on the same 72 rows. The
   training-only selection among the same 44 (TS) chose differently and scored 54/72, below E168.
9. **Exploratory or validated?** **Exploratory.** With a median of 56/72 across 44 configurations, the top score of 59 includes selection
   optimism; no independent rows exist to confirm it (E174).
10. **Replace SIMPLE / E168?** Not on this evidence. R2 / GOV is the clearest **hypothesis** so far (it is SIMPLE's 2018/2019 choice
    applied at every issue, with better probabilities than SIMPLE). The defensible next step is to freeze it and score it once, beside E168
    and SIMPLE, on the next DOST-FNRI provincial round (the E173 / E174 mechanism).

Most promising remaining approach: a pre-registered "R2 / GOV at every issue" model tested prospectively; training-only selection
cannot find it today because only one untainted survey transition exists before 2018.

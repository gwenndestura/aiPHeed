# 12 — Updated PASS/FAIL assessment (deliverable 18)

**Primary criteria are the thesis criteria.** The G1–G9 gates of `../aiPHeed_final_reliability_20261113/10_PASS_FAIL_ASSESSMENT.md` are kept as supplementary diagnostics only.

## A. Thesis criteria

| Criterion (thesis) | Result | Status |
|---|---|---|
| Algorithm 3: mean fold accuracy ≥ 75 %, sequential from Lead 1 | L1 86.1, L2 84.6, L3 81.9, L4 81.9, L5 79.1, **L6 74.7** | **MRLT = 5** |
| One-quarter-ahead (Lead 1) accuracy rule | 86.1 % | PASS |
| Algorithm 4: F1 ≥ 0.75 | L1 0.800, L2 0.784, L3 **0.745**, L4 0.755, L5 **0.717** | PASS at L1, L2, L4; **FAIL at L3, L5** |
| Algorithm 4: AUC-ROC ≥ 0.80 | 0.815–0.899 at all 8 leads | PASS |
| §3.4.4 publication rule (all thresholds cleared) | Contiguous Leads 1–2 | Leads 1–2 publishable; Leads 3–5 not under a strict reading |
| Better than persistence | Mean fold accuracy 86.1 % vs 62.4 %; Brier significant | PASS |

## B. Brief requirements

| Requirement | Status |
|---|---|
| FINAL kept as the selected baseline; evidence preserved; nothing overwritten | PASS |
| ENNS 2022 not used | PASS. The earlier comparisons that used the 2022 forecast table were withdrawn (report 05 §4) |
| Public data only; no fabricated labels; no quarterly labels | PASS |
| Root cause of each weakness identified | PASS (report 06): long-gap extrapolation (2021); displacement and regional-resolution limits (2019) |
| Corrections evidence-based and adopted only when supported | PASS. No model change adopted. Data-currency fix for harvest inputs. Candidates compared (report 07 §5) |
| 2021 SE assumption corrected | PASS (sensitivity; conclusions unchanged) |
| Household microdata, weights, 2021 SEs from FNRI | **UNAVAILABLE** (not public) |
| Stability: seeds, rounds, provinces, bootstrap, threshold | PASS for overall accuracy. **FAIL for stable HIGH detection** (round removal moves 2021 recall from 1/4 to 3/4) |
| HIGH-risk detection | Pooled 20/25 (0.80) PASS. **2021 round 1/4 FAIL** |
| Contributor groups evaluated by out-of-sample tests | PASS. 2 predictive groups, 3 contextual, remittance needs data |
| Dashboard shows only evidence-supported contributors | PASS in the preview |
| Methodology references verified | PASS: 6 verified online; others standard (marked K) |
| Frozen config + hashes + sealed future forecasts | PASS (`80b20aed…`) |
| Code reproducible from version control | **FAIL** (untracked; needs owner approval to commit) |
| Independent prospective validation | **NOT ESTABLISHED.** Pending an eligible FNRI provincial HFIAS round |

## C. Supplementary G1–G9 (unchanged; diagnostic only)
- Lead 1 fails G3 (2021 HIGH recall).
- That framework's maximum lead is 0.
- It does not determine the MRLT.

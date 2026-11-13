# FINAL: recommendation (2026-11-13)

## Direct answers

1. **What caused the failures?**
   - Stale-anchor double counting: anchors refresh to the latest round, while RATE scales by the older own-survey gap.
   - Round-specific national trends invisible at the origin, so every variant over-predicts 2018.
   - Weak within-round ranking in 2021.
   - Inputs that are regional or inert where provincial information is needed.
   - A sample too small to settle Rules 6 and 7: 25 HIGH in total, 4 in 2021.
   - See `FINAL_ROOT_CAUSE_REPORT.md`.
2. **What was corrected?**
   - The elapsed-time ambiguity now has a training-justified treatment, FINAL-ETMIX: an equal mixture of the two elapsed-time hypotheses, locked `a365da1f`, sealed for ENNS 2022 (`71ebe142`, 78 provinces, Leads 1–2).
   - The input and trigger-group evidence was rebuilt: regional accounts separated; typhoon and remittance facts corrected.
   - Outcome-free risk flags (S, G, C, X, D) are defined for future forecasts.
3. **What remains unresolved?**
   - No verified period-trend or displacement input.
   - Provincial employment only from 2022; no provincial remittances.
   - No unseen provincial survey round.
4. **Does a candidate genuinely pass all seven rules?**
   - **No admissible 7/7 exists.**
   - **FINAL, FINAL-SA and FINAL-ET are each 6 of 7.** FINAL fails stability; the other two fail calibration.
   - **FINAL-ETMIX: Rules 1–2 PASS; Rules 3–7 INSUFFICIENT EVIDENCE.**
     - Its retrospective 7/7 on the reused rows was predicted in its protocol before computing and is inadmissible.
     - The gate is **unverified** until its sealed forecasts are scored.
5. **What is the maximum reliable lead?**
   - **None established** on admissible evidence.
   - Retrospectively, FINAL-ETMIX reaches Lead 1; this is inadmissible.
   - FINAL deteriorates from Lead 1 to Lead 6 (balanced accuracy 0.85 → 0.73).
6. **Which dashboard groups does the model justify?** Four:

   | Group | Note |
   |---|---|
   | Regional economy (PSA GRDP per capita and consumption) | **Regional, not provincial** |
   | Market and prices | |
   | Poverty and social vulnerability | |
   | Agriculture and fish production | |

   Climate, employment, OFW remittances and news are **not** supported as forecast triggers for FINAL. See `FINAL_DASHBOARD_TRIGGER_GROUP_RECOMMENDATION.md`. Not implemented.
7. **Suitability**

   | Use | FINAL | FINAL-ETMIX |
   |---|---|---|
   | Research | Yes | Yes |
   | Prospective evaluation | Yes (sealed) | **Yes (sealed)** |
   | Deployment | **No** | **No** |

   E196 remains production. No candidate was integrated into the dashboard.
8. **What genuine data are needed?**

   | # | Data | Why |
   |---|---|---|
   | 1 | Provincial HFIAS outcomes for the sealed ENNS 2022 provinces, or for the next provincial round forecast from sealed origins | Scores Rules 3–7 and Leads 1–2 admissibly. 53 of its 78 provinces are stale-anchor cases, a direct test of the correction |
   | 2 | At least about 10 HIGH provinces per future round, and about 600–1,000 accumulated forecasts | For Rule 7c to be robust, and for the originally proposed calibration limits |
   | 3 | Provincial employment from PSA's annual provincial labour statistics (2022 onward), added prospectively | Gives employment real provincial variation |
   | 4 | A compiled DSWD DROMIC / Protection Cluster displacement series from 2014, with release dates and missing kept missing | Prospective input and risk flag D (your approval) |

## Shortest valid path to an admissible 7/7
1. **Obtain the provincial HFIAS (moderate+severe) results** for any provinces covered by the sealed ENNS 2022 forecasts, or the next provincial round.
2. **Score the sealed FINAL, FINAL-ET and FINAL-ETMIX forecasts once** under PROTOCOL_SA as locked.
3. **If FINAL-ETMIX passes 7/7 there, it is the first admissible acceptance.** If it fails, the failure is real and is reported as such.

## Files
- **This folder (`research_notes/aiPHeed_final_7of7_20261113/`):** the 10 reports, the protocol (+ `.sha256`), `scripts/`, `parts_mix*/`, `ablation/`, `evidence/` (seal + sha, lead and ablation results, inventory) and `HASHES.sha256`.
- **Index of the 7-of-7 brief's file names:** `INDEX.md`.

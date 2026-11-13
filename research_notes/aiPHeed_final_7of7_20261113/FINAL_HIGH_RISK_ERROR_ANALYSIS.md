# FINAL: the five missed HIGH provinces

**Sources:** survey tables (`../aiPHeed_final_rootcause_20261113/evidence/RC_*`), anchor and RATE decomposition (`D3`), and the 12–13 November information reports. No label or feature was changed for any province.

| Province (round, gap) | Survey facts (2015 anchor ± SE → outcome) | Documented cause | Mechanism in FINAL | Hypotheses (not established) | FINAL → FINAL-ET → FINAL-ETMIX (Lead 1) |
|---|---|---|---|---|---|
| **Lanao del Norte** (2019, 16) | 55.6 ± 4.4 → 59.0 (stayed HIGH while the national rate fell) | **Marawi displacement 2017:** about 139,700 displaced hosted (DSWD/Protection Cluster, 30 June 2017; before the 2019 origin) | No input observes displacement. RATE extrapolates 16 quarters against an 8-quarter training gap | Mindanao-wide martial law 2017–19 | 0.32 → 0.32 → 0.32 (missed; not a stale anchor) |
| **Misamis Oriental** (2019, 16) | 54.1 ± 5.7 → 54.8 | **None.** About 18,000 displaced is too few to explain it | Same extrapolation; the anchor is 0.7 SE above the cut-off and the outcome about 2 SE above | Survey noise near the cut-off | 0.38 → 0.38 → 0.38 (missed) |
| **Masbate** (2021, 24) | 68.3 ± 5.9 → 59.4 (fell 9 points; peers 18–34) | **None** | Stale anchor: −12 points from the anchor + −12 from RATE (double count) | Persistent structural poverty; island-economy shocks in 2020–21 | 0.15 → 0.37 → 0.26 (missed) |
| **Occidental Mindoro** (2021, 24) | 66.7 ± 5.9 → 56.3 | **None** | Same double count | Rainfall since anchor +2.6 SD (already an input, inert) | 0.21 → 0.39 → 0.30 (missed) |
| **Agusan del Sur** (2021, 24) | 64.7 ± 4.4 → 57.9 | **None** | Same double count | Conflict-related displacement (Caraga), unverified | 0.41 → 0.67 → **0.54 (found)** |

## Error categories

| Category | Cases | Status |
|---|---|---|
| Stale-anchor double count | 2021 (three) | **Documented mechanism** (code + outcome-free decomposition) |
| Gap beyond training support | All five | Documented |
| Unobserved displacement | Lanao del Norte | **Documented event;** its effect on the model is a hypothesis |
| Measurement near the cut-off | Misamis Oriental | Documented: outcome about 2 SE above 50 %, anchor 0.7 SE |
| Agricultural / environmental | Occidental Mindoro (rainfall) | **Hypothesis only**; the input exists and does not move forecasts |

## A generalizable way to flag comparable future situations (outcome-free, no province rule)

Flag a forecast as **"low-confidence"** when any of the following holds. All are computable at the origin:

| Flag | Condition | Basis |
|---|---|---|
| **S** | Stale anchor (own-survey gap > time since the latest round) | Double-count risk |
| **G** | Gap beyond the longest training gap | Extrapolation |
| **C** | Anchor within 1.96 SE of 50 % | Class decided by survey noise |
| **X** | Any selected input more than 3 SD outside its training range | Covariate shift; e.g. 2021 employment, COVID |
| **D** | A documented conflict or disaster displacement since the anchor survey | Prospective; needs the displacement series compiled, with your approval |

In the sealed 2022 set, **53 of 78 provinces carry flag S** and **31 carry flag G** (gap 28). The flags are a reporting device. They do not change any forecast.

# IMPROVE_V2_LEADS: Algorithm 3 beyond Lead 2 (reference model REF)

**What was run.** The IMPROVE_V2 REF walk-forward, unchanged, storing forecast leads 1–15 instead of 1–2
(`runner/run_leads.py`). It uses the same pooled table (`IMPROVE_V2/out/table_pooled.csv`, read only), the same training
rows, eligibility rule, eight-setting grid, inner chronological selection, LightGBM settings and seed. No tuning. The
IMPROVE_V2 PLAN hash and the HISTORY_RETRAIN data hashes were checked before fitting (`out/checks_leads.json`).
IMPROVE_V2 itself is imported read only, and none of its outputs were written.

**Reproduction (checked before scoring).** Every stored IMPROVE_V2 forecast at Leads 1–2 is reproduced **bit for bit**:
REF 226 of 226 rows, PERSIST 138 of 138, CLIM 138 of 138. The maximum absolute difference is 0.0, and the selected
configuration is identical at every origin.

**One necessary extension.** IMPROVE_V2 computed the PERSIST and CLIM baselines only at origins 2009-Q3 onward, which
covers Leads 1–2. At Lead k, the 2010-Q1 target comes from origin 2010-Q1 − k, so the baselines are computed here,
with the same definitions, from origin 2006-Q2 (26 extra rows each at Leads 1–2, none of them in IMPROVE_V2).

**Rule.** Algorithm 3: mean walk-forward accuracy ≥ 0.75, starting at Lead 1 and stopping at the first failing lead.
Each origin is one fold with one forecast per lead, so mean fold accuracy equals accuracy over the target quarters.
Target quarters are 2010-Q1 to 2026-Q3 (62 labelled quarters at every lead). R1–R7 are the frozen implementation
(`hr_lib.evaluate`).

## Result

**Maximum Reliable Lead Time = 2 quarters.** Lead 3 is the first lead below 0.75 (0.726).

| Lead | Accuracy | Algorithm 3 | Persistence accuracy | Balanced accuracy | Brier | AUC | TP/FP/FN/TN | R1–R7 failed |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.790 | pass | 0.661 | 0.717 | 0.188 | 0.702 | 39/9/4/10 | R7 |
| 2 | 0.790 | pass | 0.661 | 0.717 | 0.184 | 0.704 | 39/9/4/10 | R7 |
| **3** | **0.726** | **fail: stop** | 0.661 | 0.641 | 0.196 | 0.685 | 37/11/6/8 | R2, R3, R5, R7 |

**R7 per lead** (each third ≥ 0.60 and leave-one-quarter-out minimum ≥ 0.70):

| Lead | Thirds (2010–15, 2015–20, 2020–26) | LOQO minimum | R7 |
|---|---|---|---|
| 1 | 0.952, **0.571**, 0.850 | 0.787 | fail |
| 2 | 0.952, **0.571**, 0.850 | 0.787 | fail |
| 3 | 0.952, **0.476**, 0.750 | 0.721 | fail |

**Other rules at Lead 3.** R1 pass (62 quarters). R2 fail (0.726). R3 fail (balanced 0.641 < 0.70). R4 pass (above
always-LOW 0.306 and persistence 0.661). R5 fail: better than persistence (Brier −0.142, p < 0.001), but not
significantly better than climatology (−0.028, p = 0.138). R6 pass (precision 0.771, recall 0.860).

**Leads 4–15 (beyond the stopping point; recorded, not part of Algorithm 3).** Accuracy ranges from 0.597 to 0.677,
and every lead fails R2, R3, R5 and R7. From Lead 5 onward several leads are also at or below persistence (R4). The
full table is in `out/summary_leads.md`.

**Evidence status.** Development evidence: these quarters were examined during development.

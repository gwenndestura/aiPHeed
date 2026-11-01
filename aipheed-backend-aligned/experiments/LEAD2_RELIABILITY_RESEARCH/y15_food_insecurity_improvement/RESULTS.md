# Y15 results: improving the Lead-2 food-insecurity forecast

**Target:** TFI-2, observed BL hunger > 11.3% at Lead 2 (`OBJECTIVE.md`).

**Plan:** `EXPERIMENT_PLAN.md`, SHA-256 `3aecc30c87de2c8501e6380c957ef2cd2563745a550a22fb681c6960ed31e4b1`, frozen 2026-10-29T14:01:19Z, before any Investigation C candidate was scored.

**Data:** `DATA_AUDIT.md`.

**Reproduce** (from `runner/`):

```
python -B warmup_audit.py   # Investigation A (read-only audit of the served FIRI history)
python -B acquire_imf.py    # Investigation B data (IMF BOP; re-download changes hashes)
python -B run.py            # Investigation C: development gate, then the 17 official targets
```

**Disclosed deviations (none changed a scored result):**

1. **Warm-up audit.** The first run of `warmup_audit.py` stopped on a too-strict parity tolerance. The CSV stores F2 to 4 decimals, so 1e-6 was too tight; it is now 1e-4. T6 (descriptive) was added before the outputs were read.
2. **Candidate naming.** The first run of `run.py` stopped before scoring anything, on a name clash: the plan IDs C1–C5 equal the climate-indicator names C1–C4. The candidates are named FIRIR, SCREEN, KAL, CONT and REMIT in code, mapping to plan IDs C1–C5. Without the fix, the screening step would have read the FIRI-R index in place of the El Niño indicator.

## Investigation A: did the climate-domain warm-up create artificial separation?

**Yes, for 2 of the 5 LOW quarters.**

**The trace (stored history, read-only):**

- At the first three LOW targets (2022-Q3, 2022-Q4, 2023-Q1), only C1 (El Niño alert) was scored, and it was 0.
- C2 typhoons were "insufficient_history" (< 8 earlier origins). C3 and C4 were "missing" or "insufficient_history".
- The served code averages only the scored indicators, so the climate domain was **0.000**. That is a statement about data availability, not low climate stress. FIRI then averaged that 0 with the other domains.

**Treatments** (served index, 17 targets; an audit, not model selection):

| Treatment | Rows with a forecast | Abstained | TP/FP/FN/TN | Accuracy | R1–R7 |
|---|---|---|---|---|---|
| Served (stored) | 17 | 0 | 11/0/1/5 | 0.941 | F P P P F P P |
| T1 domain abstention (C counts only with ≥ 3 of 4 indicators) | 14 | **3** (2022-Q3, 2022-Q4, 2023-Q1: under 4 domains, so FIRI's own rule abstains) | 11/0/1/2 | 0.929 | F P P P F P P |
| T2 consistent coverage (C uses only indicators scored at all 17 targets, i.e. C1) | 17 | 0 | 4/0/8/5 | 0.529 | all F |
| T3 equal domain weights (no outcome-fitted evidence weights) | 17 | 0 | 10/0/2/5 | 0.882 | F P P P F P P |
| T4 = T1 + equal weights | 14 | 3 | 10/0/2/2 | 0.857 | F P P P F P P |
| T5 climate domain excluded | 8 | 9 | 8/0/0/0 | 1.000 (one class) | F P F F F P P |
| **T6 (descriptive; breaks the ≥ 4-domain rule)**: C unavailable in warm-up, index over the other 3 domains | 17 | 0 | **11/2/1/3** | **0.824** | F P P P F P **F** |

**Interpretation:**

- Without the warm-up zero, **2022-Q4 and 2023-Q1 move from 0.430 / 0.454 to 0.574 / 0.606**. They become false alarms: specificity falls from 1.00 to 0.60, and R7 fails.
- Under a defensible treatment (T1), FIRI **cannot forecast those quarters at all**.
- The perfect 5/5 LOW record is therefore partly an artefact of treating unavailable data as zero.
- The later HIGH quarters depend on C2–C4. With C1 only (T2), recall drops to 4/12.
- On independent years (Y14 `domain_replication.json`), the analog climate domain has AUC **0.49** [0.37, 0.60] for 1999–2020. The 2021+ climate signal does not replicate.
- The equal-weight version (T3) still scores 0.882. The outcome-fitted weights added one correct call.

**The served FIRI and its history were not modified.**

## Investigation B: remittances

| | Result |
|---|---|
| Obtained? | **Yes, legitimately.** IMF BOP public API, Philippine personal transfers, quarterly 1999-Q1 .. 2026-Q2. It agrees with the project's 2021+ BSP figures (levels r = 0.997). BSP's own Excel was not obtainable without circumventing a block, which was not done. |
| Geography | National only (not regional or provincial) |
| Does it lead hunger? (1999–2020, 77 origins) | Weakly, with a plausible sign. E2 (remittance decline) at the issue date vs the coming hunger change: **r = +0.17 [0.03, 0.31]**. Concurrent r = −0.17 [−0.32, −0.03]. |
| Does it improve the forecast? | **No.** REMIT (H1 + E2): Brier 0.223 vs H1 0.216 (+0.007, p 0.66), balanced accuracy 0.50. SCREEN kept E2 at 22 of 77 origins and still did not beat H1. |

## Investigation C: five candidates on independent years

**Rows.** 77 targets, 2001-Q1 .. 2020-Q4, one row per quarter; prevalence 0.70 (23 LOW). The quarter is the bootstrap unit (B = 5000).

**Early origins.** 29 had too few training rows. There SCREEN, CONT and REMIT fall back to H1, and those rows equal H1.

| Model | n | Acc | Bal | Prec | Rec | Spec | F1 | AUC | Brier | TP/FP/FN/TN | Cal. slope | Δ Brier vs H1 (p; block p) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PERSIST | 77 | 0.636 | 0.566 | 0.74 | 0.74 | 0.39 | 0.741 | 0.566 | 0.364 | 40/14/14/9 | – | +0.148 (1.00) |
| CLIM | 77 | 0.636 | 0.591 | 0.76 | 0.70 | 0.48 | 0.731 | 0.494 | 0.240 | 38/12/16/11 | 0.18 | +0.024 (0.83) |
| **H1 hunger persistence** | 77 | 0.662 | 0.585 | 0.75 | 0.78 | 0.39 | 0.764 | 0.682 | **0.216** | 42/14/12/9 | 0.42 | – |
| **C1 FIRIR** corrected FIRI-style | 77 | 0.506 | 0.573 | 0.79 | 0.41 | 0.74 | 0.537 | 0.630 | 0.248 | 22/6/32/17 | 1.22 | +0.032 (0.93; 0.93) |
| **C2 SCREEN** H1 + in-fold-screened drivers | 77 | 0.662 | 0.535 | 0.72 | 0.85 | 0.22 | 0.780 | 0.618 | 0.220 | 46/18/8/5 | 0.38 | +0.004 (0.62; 0.81) |
| **C3 KAL** survey-uncertainty state space | 76 | 0.658 | **0.607** | 0.76 | 0.74 | 0.48 | 0.750 | **0.715** | **0.192** | 39/12/14/11 | **0.77** | **−0.025 (0.091; 0.25)** |
| **C4 CONT** continuous → P(> 11.3) | 77 | 0.662 | 0.522 | 0.71 | 0.87 | 0.17 | 0.783 | 0.614 | 0.236 | 47/19/7/4 | 0.28 | +0.020 (0.78; 0.86) |
| **C5 REMIT** H1 + remittances | 77 | 0.636 | 0.504 | 0.70 | 0.83 | 0.17 | 0.763 | 0.633 | 0.223 | 45/19/9/4 | 0.37 | +0.007 (0.66; 0.78) |

**Gate (frozen).** Holm p: KAL 0.455; all others 1.0.

| Candidate | G1: Brier < H1, Holm p < 0.10 | G2: balanced ≥ H1 | Passes |
|---|---|---|---|
| C1 FIRIR | no | no | **no** |
| C2 SCREEN | no | no | **no** |
| C3 KAL | no (raw p 0.091, Holm 0.455) | **yes** (0.607 vs 0.582) | **no** |
| C4 CONT | no | no | **no** |
| C5 REMIT | no | no | **no** |

**Drivers kept by in-fold screening (C2), out of 77 origins:**

| Kept | Origins |
|---|---|
| none | 38 |
| C3 production drop | 23 |
| E2 remittance decline | 22 |
| A2 headline inflation | 12 |
| C4 fisheries | 11 |

No driver was stable across folds.

**Continuous outcome** (BL hunger level, 2001–2020):

| Forecast | MAE (pts) | CRPS |
|---|---|---|
| CONT (C4) | 4.61 | 3.21 |
| RW (newest reading) | 4.87 | 3.40 |
| **Climatological mean** | **4.23** | **3.09** |

CONT beats RW on CRPS (−0.19, p 0.21), but neither beats the long-run mean. **At a 3-quarter true horizon, the BL hunger level is best predicted by its long-run average.** Only the crossing of 11.3 retains a little persistence information.

## The 17 official FIRI Lead-2 targets (2022-Q3..2026-Q3): seven rules for every candidate

**DESCRIPTIVE ONLY:** no candidate passed the gate, so nothing is selected from these rows.

| Forecast | Rows | Acc | Bal | P / R | AUC | Brier | TP/FP/FN/TN | R1 | R2 | R3 | R4 | R5 | R6 | R7 | All |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Served FIRI v2 | 17 | 0.941 | 0.958 | 1.00 / 0.92 | 0.933 | 0.189 | 11/0/1/5 | F | P | P | P | F | P | P | no |
| H1 (stored with the FIRI rows) | 17 | 0.706 | 0.617 | 0.77 / 0.83 | 0.792 | 0.161 | 10/3/2/2 | F | F | F | F | F | P | F | no |
| Y15 H1 (recomputed) | 17 | 0.706 | 0.617 | 0.77 / 0.83 | 0.825 | 0.142 | 10/3/2/2 | F | F | F | F | F | P | F | no |
| C1 FIRIR | 17 | 0.706 | 0.675 | 0.82 / 0.75 | 0.783 | 0.228 | 9/2/3/3 | F | F | F | F | F | P | F | no |
| C2 SCREEN | 17 | 0.706 | 0.733 | 0.89 / 0.67 | 0.667 | 0.217 | 8/1/4/4 | F | F | P | F | F | P | F | no |
| C3 KAL | 17 | 0.706 | 0.500 | 0.71 / 1.00 | 0.783 | 0.155 | 12/5/0/0 | F | F | F | F | F | P | F | no |
| C4 CONT | 17 | 0.588 | 0.417 | 0.67 / 0.83 | 0.683 | 0.215 | 10/5/2/0 | F | F | F | F | F | P | F | no |
| C5 REMIT | 17 | 0.706 | 0.500 | 0.71 / 1.00 | 0.783 | 0.180 | 12/5/0/0 | F | F | F | F | F | P | F | no |

**R1 fails structurally:** 17 regional quarters, below 40 rows. One outcome per quarter means 17 independent observations, 5 of them LOW, two of those exactly at 11.3.

## Prospective workflow: reviewed, not modified, nothing issued

`../y14_food_insecurity_forecast/runner/issue_forecast.py` was confirmed to:

- record the UTC write time;
- flag `validProspective` (true only if written on or before the issue date);
- record the newest SWS round used, with its publication date;
- record every forecast and its class at 0.50, and the indicators;
- record the git HEAD and plan hash;
- record the SHA-256 of all 16 input files;
- write a timestamped file that refuses to overwrite, and append to `prospective/SEALS.txt`.

**Gaps noted:**

- It does not hash the Y15 remittance file. No Y15 candidate is issued, so this does not matter yet.
- It writes, rather than refuses, when run late. The `validProspective = false` flag is the safeguard.

**No new seal was created and nothing was backdated.** The only existing Y14 file is the demonstration flagged `validProspective = false`. The first valid issuance remains **2027-01-01**.

## Conclusions

| Question | Answer |
|---|---|
| 1. Did the warm-up affect FIRI's apparent performance? | **Yes.** Unavailable climate indicators were averaged as 0.000 at the first three LOW targets. Without that zero, two of the five LOW quarters become false alarms: accuracy 0.941 → 0.824, specificity 1.00 → 0.60. Under domain abstention, FIRI cannot issue those quarters. The climate signal does not replicate on 1999–2020 (AUC 0.49). |
| 2. Remittances obtained? Improved? | **Obtained** from the IMF BOP public API, 1999–2026, national, validated against BSP (r = 0.997). There is a weak leading signal (r = +0.17), but **no forecast improvement** (Brier +0.007 vs H1). |
| 3. Best candidate vs persistence on independent data | **C3 KAL, the survey-uncertainty state-space model.** Brier 0.192 vs 0.216 (−0.025; raw p 0.091; Holm 0.455; block p 0.25). It is the best calibrated (slope 0.77 vs 0.42), with higher balanced accuracy (0.61 vs 0.58) and higher AUC (0.72 vs 0.68). It does **not** pass the gate. It was worse than RW in the Phase-2 four-area pooled test, and on the 2021–2026 rows it never forecasts LOW. |
| 4. Did any candidate pass all seven rules without leakage? | **No.** R1 cannot pass for any regional quarterly forecast until 40 quarters are observed. |
| 5. Remaining hypothesis worth pursuing | **Pre-register KAL as the single challenger to H1 for prospective sealed comparison from 2027-01-01.** It is the only approach that has beaten persistence on Brier, calibration and AUC on both Y14 (46 rows) and Y15 (77 rows), though not significantly. It uses only SWS data, so it needs no new data source. One pre-registered hypothesis, scored only on future quarters, avoids the multiplicity that has accumulated across 20+ variants on the historical rows. Adding it to `issue_forecast.py` needs a new frozen plan (not done here). Separately, a more frequent, provincial food-insecurity observation remains the only data change that could lift the ceiling. |

# LEAD2_POST_SWS_ISSUE: protocol (frozen before any scoring)

**Status.** Frozen before any result in this folder was computed. The SHA-256 is in `PROTOCOL_SHA256.txt` and the UTC time in `PROTOCOL_FROZEN_AT.txt`. Every runner checks the hash.

**Done before freezing:** only the Step 1 data audit (`runner/audit_dates.py` → `DATA_AUDIT.md`). It reads publication dates only. No forecast or outcome was scored.

## 1. Hypothesis

Issuing the Lead-2 forecast **after the newest SWS round is published**, instead of on the first day of quarter t+1, shortens the hunger-information gap from about 3 quarters to about 2. The target quarter stays the same (t+2). This could make Lead 2 reliable.

**This is a change of issue timing, not of the model.** It is never reported as the original Lead 2 passing. Lead 1 is not touched.

## 2. Issue rule (fixed from the Step 1 distribution only)

| Item | Definition |
|---|---|
| Current issue date | O(t) = first day of quarter t+1 |
| Cap | **CAP(t) = last day of quarter t + 67 days.** 67 = nearest-rank 90th percentile of the days from quarter end to publication of the last SWS round of the quarter, over the 21 quarters with **verified** dates (2021-Q2 .. 2026-Q3). |
| P(t) | Publication date of the **last** SWS round assigned to quarter t, from the same series used throughout: `rlib.rounds()`, BL. |
| **Post-SWS issue date** | **O'(t) = max( O(t), min( P(t) + 1 day, CAP(t) ) )**. If no quarter-t round exists, O'(t) = CAP(t). |

**Information.** Everything published **strictly before** O'(t). A round published on O'(t) or later is not used.

**Target:** quarter t+2. **Lead time** = days from O'(t) to the last day of quarter t+2. It is reported (median, min, max) against the current O(t) lead time (about 182 days).

## 3. Information at O'(t)

| Input | Rule |
|---|---|
| SWS (all areas) | Rounds published < O'(t) |
| CPI (provincial food and all-items YoY) for baselines | Month M is available at date D if D ≥ the first day of month M+2. This is the project's conservative rule: at O(t) it gives month 2 of quarter t, as `e41_lib.m0_of`. |
| **Model price term** | **P0_price exactly as served**, i.e. the stored walk-forward `P0_price` (features as of O(t), CPI through month 2 of quarter t). The served price pipeline (`e41_lib.m0_of`, `origin`) fixes its CPI cutoff at O(t); refreshing it would be a new model variant, which this protocol forbids. **The model therefore does *not* use the fresher CPI available at O'(t). This is a disclosed limitation that works against the model**, because the baselines below do use the fresher CPI. |
| News, climate and other price features | Inside P0_price, as served (as of O(t) < O'(t)) |

## 4. Models

No new family, feature or tuning.

| Name | Role | Definition |
|---|---|---|
| **M0** | primary | P = H4(O'(t)) × P0_price. H4 is the served hunger term (`LEAD2_OPTIMIZATION/runner/a3.h4`) recomputed at O'(t): newest BL reading from `ch1_lib.bl_known(O')`; true horizon h = (t+2) − newest quarter; σ = RMS of four-area horizon-h changes from `fi_lib.known(O', area, "primary")`; P = Φ((h_last − 11.3)/max(σ, 0.5)); NaN if fewer than 8 errors, as served. |
| **M1** | the one pre-listed variant | P = KAL(O'(t)) × P0_price. KAL is the Y15/Y16 Kalman hunger term (`common/hmodels.kalman` logic, four areas) with its issue date replaced by O'(t). |

**Parity before scoring:** H4 and KAL recomputed at O(t) must equal `a3.h4` and `hmodels.kalman` (and the stored `pi_H4`) to within 1e-6, or the run stops.

## 5. Baselines, all recomputed at the same O'(t)

| Baseline | Definition |
|---|---|
| always-LOW | Probability 0 |
| **CLIM'** | Share of HIGH among T43c labels (`ch1_lib.labels()`) of quarters q ≤ t whose BL rounds were all published < O'(t) and whose three CPI months are all available at O'(t). Province labels pooled, as served. |
| **PERSIST-SI'** | (newest BL reading published < O'(t)) > 11.3 **AND** the price condition on the newest three CPI months available at O'(t): mean food YoY > θ_food[p] or mean (food − all) > θ_gap[p], with E40 thresholds. This is `ch1_lib.persist_si` with both cutoffs moved to O'(t). |

Parity: at O(t), CLIM' and PERSIST-SI' must equal the stored `CLIM_p` and `PERSIST-SI_p`, or the run stops.

## 6. Evaluation A: official rows (T43c, 5 provinces, Lead 2)

- **Rows:** the 65 official Lead-2 rows (13 target quarters 2023-Q2 .. 2026-Q3); y = stored T43c label.
- **Rules:** R1–R7 exactly as frozen (`P0H4_LEAD12_REVIEW/runner/reproduce.rules`, equal to `ch1_lib` §7), with the `PERSIST-SI_p` and `CLIM_p` columns replaced by PERSIST-SI' and CLIM'. Threshold 0.50.
- **Reported for M0, M1 and each baseline:**
  - accuracy, balanced accuracy, precision, recall, specificity, AUC, Brier, each with a 95% quarter-cluster bootstrap CI (B = 2000, seed 2036);
  - R1–R7;
  - onsets anticipated (province HIGH after LOW);
  - metrics by third of the quarters;
  - the original-issue P0H4 on the same rows, for comparison.
- **Leakage audit, per row:**
  - newest SWS round published < O'(t);
  - newest CPI month used available at O'(t);
  - P0_price issued at O(t) ≤ O'(t).

  Any violation stops the run.

## 7. Evaluation B: independent years (regional TFI-2, BL hunger > 11.3)

- **Rows:** origins t with targets 2002-Q1 .. 2020-Q4 and an observed BL outcome (`rlib.observed`).
- **Dates:** O'(t) from the pre-2021 rule dates, label-month end + 60 days.
- **Sensitivity** (lag bound, as in Y12): every pre-2021 publication date + 30 days (label-month end + 90). O'(t) is recomputed, so it is mostly capped.
- **Components:**
  - **H1'**: persistence probability at O'(t) (RW, `rlib.forecast` logic: newest BL reading, pooled four-area σ at the true horizon);
  - **KAL'**: Kalman at O'(t);
  - **PERSIST'**: binary, newest reading > 11.3;
  - **CLIM'**: expanding share of BL quarters > 11.3 with all rounds published < O'(t);
  - always-LOW.
- **The hunger component of M0 on TFI-2 is the persistence probability itself** (H4's σ is pooled from 2021+ only, so it is undefined before 2021, and its pre-2021 analogue is H1'). **M0 therefore cannot beat persistence on this gate by construction.** This is fixed now and is a consequence of the decision rule.
- **Gate** (same as Y14/Y15), applied to M1's hunger component (KAL') against persistence (H1'):
  - Brier(KAL') < Brier(H1'), one-sided quarter bootstrap p < 0.10 (B = 5000, seed 2036);
  - balanced accuracy(KAL') ≥ balanced accuracy(H1').

  It must pass under **both** the main and the sensitivity dates. The moving-block (L = 4) p-value is reported as information.

## 8. Label-noise sensitivity (as in Y1)

For M0 and M1 on the official rows:

- flip each BL quarter within 1.0 point of 11.3, one at a time and all together, and recompute R2, R3, R4, R6 and R7;
- Monte Carlo over SWS sampling error (2000 draws): share of draws in which each classification rule passes.

## 9. Decision

| Decision | Condition |
|---|---|
| **(A)** | For M0 or M1: R1–R7 all pass on the official rows (§6) **and** the §7 gate passes for that model, under main and sensitivity dates. **A development result.** It needs sealed prospective confirmation, and is disclosed as a change of issue timing. |
| **(C)** | Otherwise |

Baseline reproduction comes first: the stored P0H4 at O(t) must give Lead 2 **6/4/11/44** and Lead 1 **11/5/6/48**, or the run stops.

**Variants run:** exactly M0 and M1, plus the baselines. Every result is reported, and nothing is changed after scoring.

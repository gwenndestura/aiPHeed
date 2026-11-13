# 10 — PASS / FAIL assessment for every acceptance criterion

**Model:** FINAL (RATE + MIND). **Protocol:** PROTOCOL_REL (sha256 `1efdf5a4…`).

**All results are retrospective.** The 72 evaluation rows had been scored before this study. The computation is leakage-free, but the researcher had seen the outcomes. "PASS" below means the retrospective evidence complies. It does **not** mean independent validation.

## Brief §1 — Ground truth
| Criterion | Status |
|---|---|
| 2013/2015/2018/2019/2021 provincial HFIAS retrieved and audited | PASS (published provincial estimates) |
| Actual household responses + sampling weights | **UNPROVEN** (no public microdata; FNRI PUF blocked from this network) |
| Harmonisation / design / coverage / uncertainty verified | PARTIAL (2013 SE approximated; 2021 SE assumed 3.0 pp; ENNS rolling subsets) |
| No manufactured quarterly labels | PASS |
| Every exclusion documented | PASS (44 areas, `GT_excluded_areas.csv`) |

## Brief §2 — Chronological validation
| Criterion | Status |
|---|---|
| Rolling-origin evaluation | PASS |
| Information at each origin reconstructed; outcome not used in its fit | PASS (computational; 0 violations in 110 fits) |
| Predictions generated before accessing the outcome | **FAIL as independent evidence.** The outcomes were already known to the researcher (retrospective) |
| Every eligible round evaluated | PASS (2018, 2019, 2021; 2015 has no earlier provincial training round) |
| Independent evaluation periods reported | PASS: **3** |
| Existing metrics reproduced; discrepancies investigated | PASS (exact; none) |

## Brief §3–4 — Reliability and lead (gates G1–G9 per lead)
| Gate | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|
| G1 accuracy ≥ 0.75 | PASS 0.861 | PASS 0.847 | PASS 0.819 | PASS 0.819 | PASS 0.792 |
| G2 beats always-LOW (CI > 0) | PASS | PASS | PASS | PASS | **FAIL** |
| G3 HIGH recall ≥ 0.75 and ≥ 0.50 every round | **FAIL** (2021 1/4) | **FAIL** | PASS | **FAIL** | **FAIL** |
| G4 precision ≥ 0.60, HIGH F1 ≥ 0.70 | PASS | PASS | PASS | PASS | PASS |
| G5 BA ≥ 0.75, macro F1 ≥ 0.75 | PASS | PASS | PASS | PASS | PASS |
| G6 calibration consistency | PASS | PASS | PASS | PASS | PASS |
| G7 Brier beats persistence and climatology | PASS | PASS | PASS | PASS | PASS |
| G8 PR-AUC ≥ persistence | PASS | PASS | PASS | PASS | PASS |
| G9 every seed ≥ 0.75, every round ≥ 0.70 | PASS | PASS | PASS | PASS | **FAIL** |
| **Lead passes** | **FAIL** | **FAIL** | PASS | **FAIL** | **FAIL** |

**Maximum reliable lead (contiguous): 0.** For comparison, the weaker earlier rules give 4 (robust rule) and 5 (thesis Algorithm 3).

## Brief §5 — Stability
| Criterion | Status |
|---|---|
| Five seeds | PASS (L1 0.847–0.861) |
| G10a survey-round sensitivity | PASS on accuracy (≥ 0.72), but **HIGH calls unstable** (2021 recall 1/4–3/4; up to 8 flips). One refit is not executable and one is a no-op; both are recorded |
| G10b unseen provinces | PASS (0.847 accuracy, 0.76 recall) |
| G10c bootstrap | PASS (cluster CI [0.778, 0.931]) |
| Threshold sensitivity | Reported; stable 0.50–0.60; not moved |
| Failed experiments preserved | PASS |

## Brief §6 — Contributors
| Group | Genuinely improves out-of-sample? |
|---|---|
| 1 Market and prices | **NOT ESTABLISHED** (ΔBrier +0.011, CI includes 0; direction plausible) |
| 2 Climate stress | **FAIL** (no effect) |
| 3 Employment | **FAIL** (no effect) |
| 4 OFW remittances | **UNTESTABLE** (no input) |
| 5 Poverty and social vulnerability | **NOT ESTABLISHED** (CI includes 0; not selected in 2021 or live fits) |
| Regional economy (not on dashboard) | PASS (+0.029 [+0.003, +0.054]) |
| Agriculture and fish (not on dashboard) | PASS (+0.011 [+0.001, +0.020]) |

## Brief §7 — External checks (context only)
| Check | Result |
|---|---|
| FIES 2023 CALABARZON vs FINAL | Consistent: lowest FIES region; FINAL all-LOW. Not a test of HIGH detection |
| Regional FIES 2023 ranking | ρ = 0.835 (15 regions); partly by construction (regional GRDP input) |
| PSA poverty 2023 vs provincial forecasts | ρ = 0.60; FINAL tracks poverty more than the outcome does |
| SWS Balance Luzon | Context: hunger roughly doubled since 2022 while FINAL's CALABARZON p stays ≈ 0. Flagged, not adjudicable |

## Brief §8 — Freeze and seal
| Criterion | Status |
|---|---|
| Gates pass → freeze | **NOT DONE: gates fail** |
| Seal 2027-Q1–2028-Q1 | **NOT DONE** (conditional on the gates) |
| Existing ENNS 2022 seals hashed and re-verified | PASS (`4ad9267f`, `71ebe142`) |
| Procedure for scoring the next FNRI round | PASS (`09_…md` §3) |
| Code and configuration under version control | **FAIL** (`app/hcw/` and `research_notes/` untracked) |

## Overall verdict
**FINAL does not meet the public-data reliability gates.**

What the evidence does support (retrospectively):
- Lead-1 accuracy 0.861, macro F1 0.847, PR-AUC 0.846.
- Brier significantly better than always-LOW, climatology, persistence and the three statistical baselines.
- Little loss on unseen provinces.

What it does not establish:
- Reliable HIGH detection when the survey gap exceeds the training range (2021: 1 of 4 HIGH found; persistence found 4 of 4).
- Stable HIGH calls when the training-round mix changes.
- Out-of-sample value for four of the five dashboard groups.
- Independent validity.

**Exactly what remains unproven, and what would prove it:**
1. Independent predictive skill. Needs the ENNS 2022 (or later) provincial HFIAS outcomes, scored once against seal `4ad9267f`.
2. HIGH detection at long survey gaps. Needs a round with more than 4 HIGH provinces and gaps of at least 24 quarters.
3. Label fidelity. Needs FNRI household microdata with weights, or published 2021 provincial SEs.
4. Contributor value for market and poverty. Needs more rounds; the current CIs include 0.
5. Reproducibility from version control. Needs a commit of `app/hcw/` and the research scripts, which requires your approval.

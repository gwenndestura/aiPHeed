# FIRI Lead 2 feasibility: can aiPHeed forecast overall food insecurity two quarters ahead?

**Frozen before scoring.** SHA-256 and UTC time in `runner/PROTOCOL_SHA256.txt` and `runner/PROTOCOL_FROZEN_AT.txt`.
The runner refuses to run if this file changes. Inputs are read only; outputs go to `out/` in this folder.

## 1. Question and constructs (not conflated)

| Construct | What it is | Lead-2 target |
|---|---|---|
| **P0H4** | P(BL hunger > 11.3% **and** the province's food-price condition), Chapter I T43c | T43c per province (unchanged; R1–R7 as frozen, sha dd9ab815) |
| **FIRI v2** | A 0–1 composite proxy index of six domains (affordability, vulnerability, climate/production, household economy, news, regional hunger), percentile-normalized against earlier origins, evidence-weighted (C3). **Not a probability.** | Issued for t + 2 by construction (`firi2_history.csv` stores only Lead-2 issues) |

The thesis objective is overall food insecurity. This protocol tests FIRI against that objective. It does **not** score
FIRI on the P0H4 target and does not report a FIRI result as a P0H4 result.

## 2. Target

Three targets were considered:

1. **The future FIRI value. Rejected.** FIRI is not observed. There is no "realised FIRI" for a quarter, only the value
   the system computes. A FIRI computed at a later origin is the system's own output, so scoring against it would be
   circular, not a validation of food-insecurity forecasting. FIRI values are also stored only at Lead 2.
2. **A provincial food-insecurity outcome. Not available.** No provincial food-insecurity observation exists for
   2021–2026 in the authorised data. Copying the regional hunger outcome to the five provinces is not independent
   ground truth and is not scored as such. T43c is a price-conditioned label, a different construct, and is reported
   only as agreement.
3. **R: observed SWS involuntary hunger, Balance Luzon, above 11.3% in the target quarter. Selected.** This is the only
   direct food-insecurity observation, and it is regional. It is the same primary outcome as FIRI2_PROTOCOL.md §3.

**Outcome series.** `backend/data/inputs/sws_rounds.csv`, using every round labelled with the target quarter, taking
the mean H. y = 1 if the mean is above 11.3. The runner also reports whether any single-round choice would change a
label.

## 3. Candidate (one, nothing fitted)

**F2** is the stored FIRI v2 (selected C3) Lead-2 value from `backend/data/thesis/firi2_history.csv`, rows with
`kind = backtest`.

- **Regional score:** the mean of the five provinces, which is the served aggregation. Quarters with fewer than five
  computable provinces are dropped and reported.
- **Class:** HIGH if the regional score is ≥ 0.50, the frozen threshold.
- **Not changed:** no refit, no recalibration, no new threshold.

**Why no new model.** The authorised R outcomes 2022-Q3..2026-Q3 were already examined (FIRI2 diagnostics,
`firi2_evaluation.json`, `FIRI_PROVINCIAL_RELIABILITY`). A model fitted to them would be tuned on known answers. The
existing FIRI v2 is already the Lead-2 forecast; this task tests it, it does not improve it.

**Disclosed before scoring:**

- `firi2_evaluation.json` reports C3 on R at Lead 2 as 17 quarters, TP 11 / FP 0 / FN 1 / TN 5.
- C3 was chosen by Lead-2 R accuracy on those same quarters.
- The R series in the window is LOW in 2022-Q3..2023-Q3 and HIGH from 2023-Q4, which is **one** class change.
- `FIRI_PROVINCIAL_RELIABILITY` scored 16 quarters because it used E114's month-based quarters, which file Oct-2022
  under Q4. This protocol uses the production series, which follows the SWS quarter labels.

Every result here is **development evidence**.

## 4. Baselines (identical rows)

| Id | Definition | Used in |
|---|---|---|
| ALWAYS-HIGH | p = 1. This is the constant majority forecast for R. | R4, the trivial-forecast comparison |
| ALWAYS-LOW | p = 0 | reported (R4 as written) |
| PERSIST | The class of the newest SWS quarter with a round published before the issue date (mean of that quarter's rounds published before the issue date); p ∈ {0, 1} | R4, McNemar |
| H1 | FIRI's own H1 indicator: P(> 11.3%) from the latest posted round. This is the probabilistic persistence forecast; it is checked to be identical for the five provinces. | R5, the persistence Brier comparator |
| CLIM | Share of quarters from 2021 with y = 1 among quarters with a round published before the issue date, using the rounds published before the issue date; 0.5 if there are none | R5 |

## 5. Reliability criteria: thresholds unchanged, applicability stated before scoring

The unit is the quarter (one regional row per quarter). The bootstrap resamples quarters (5,000 draws, seed 2036).

| Rule | As frozen for P0H4 | How it is applied to R |
|---|---|---|
| R1 | ≥ 10 quarters and ≥ 40 rows | Applied **as written**. A regional target has one row per quarter, so the row part cannot be met with 17 quarters, and R1 is expected to fail. The quarter part is reported separately as **R1-q**, labelled an adaptation, and never used to claim that the original test passed. |
| R2 | accuracy ≥ 0.75 | as written |
| R3 | balanced accuracy ≥ 0.70 | as written |
| R4 | accuracy > always-LOW and > PERSIST-SI | Applied **as written** (always-LOW, PERSIST). Also reported against ALWAYS-HIGH, because always-LOW is not the trivial forecast when the majority is HIGH (**R4-maj**, an adaptation). |
| R5 | Brier < persistence and < CLIM, one-sided cluster p < 0.10 | The FIRI index is used as the score. It is not a calibrated probability, as FIRI2_PROTOCOL §3 discloses. Compared with H1 and CLIM. |
| R6 | precision and recall ≥ 0.60 (HIGH) | as written |
| R7 | each `np.array_split` third ≥ 0.60 and leave-one-quarter-out minimum ≥ 0.70 | as written |

## 6. Is the evidence sufficient for a credible conclusion?

These conditions are pre-declared and do not change R1–R7.

- **S1:** the observed R class changes at least 3 times in the window, so the forecast is tested on more than one regime
  switch.
- **S2:** at least 5 quarters of each class.
- **S3:** the forecast beats PERSIST on McNemar exact one-sided p < 0.10, on discordant quarters.

Also reported: the Wilson 95% CI of accuracy and of LOW-class specificity, and onsets caught (LOW→HIGH in the outcome).

## 7. Decision

- **Outcome A (defensible FIRI Lead-2 forecast of R):** every rule R2–R7 is met as written, R1-q holds and S1–S3 hold.
  Even then, the result is development evidence, and adoption needs prospective confirmation and the owner's approval.
- **Outcome B (correctable defect):** only if a confirmed implementation defect changes the result.
- **Outcome C (insufficient evidence):** otherwise. The report names the missing data.

R1 as written can never pass with one regional row per quarter. A pass of R2–R7 with R1-q is therefore reported as
**"meets the adapted criteria on development evidence"**, never as "passes R1–R7".

## 8. EW4 issue-date check (separate; not used to tune)

This checks the P4 × H4 forecast sealed for the 2026-10-01 issue (`881151a5`).

1. **Perturbation audit at origin 2026-Q3.** This is the frozen LEAD2_OPTIMIZATION audit, run at the issue origin it
   never covered. It randomises every CPI, Pink Sheet and rice-CPI month after m0 (Aug 2026), and every SWS round and
   news record published on or after 2026-10-01. It extends the frozen audit by also randomising LFS months after
   2026-06, production quarters ≥ 2026-Q3, and remittance and rice-wholesale quarters ≥ 2026-Q3. The P4 and P0 price
   values and H1 must be identical.
2. **An input table.** For each input: the newest period used, its publication date and the evidence for that date
   (stored timestamp, or release calendar where no timestamp is stored).
3. **Seal timing.** When each seal was generated relative to the issue date, and whether any target outcome was public
   then.

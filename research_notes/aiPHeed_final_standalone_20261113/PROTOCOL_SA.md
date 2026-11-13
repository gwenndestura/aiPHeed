# PROTOCOL_SA: standalone acceptance of FINAL (RATE + MIND), locked 2026-11-13 before any scoring under it

## 0. Disclosure

**What I already knew before writing this protocol.** These FINAL Lead 1 values come from the 2026-11-12 reports:
- accuracy 86.1 %;
- HIGH recall 0.80 and precision 0.80;
- balanced accuracy 84.7;
- calibration slope 1.25;
- ECE 0.072 (5-bin).

**Thresholds.** They are therefore set from the brief and from candidate-independent arguments only:
- Every proposed threshold is kept.
- The one exception is Rule 6. Its proposed ECE, slope and intercept limits are untestable at n = 72; the evidence is simulated with no model output (`evidence/P0_*.json`).
- For transparency, Rule 6 is reported under **both** the proposed and the adjusted form.

## 1. Evaluation data (reused, not independent)

**The rows**
- 72 province-rounds: ENNS 2018 (22), 2019 (25), 2021 (25).
- Forecast origins one, two and three quarters before each survey's reference quarter.
- Each province-round counts once per lead.
- Leads are never pooled as independent rows; pooled intervals resample province-rounds.

**Why they are not independent.** These rows were already used to develop and compare about 38 configurations. Every metric below is therefore **retrospective on reused rows**. The protocol's decision mapping (section 4) caps the verdict accordingly.

**What is scored.**
- **Primary:** Lead 1, the one-quarter-ahead requirement.
- **Reported, not used for acceptance:** Leads 2 and 3.

**Label.** HIGH = FNRI HFIAS moderate+severe prevalence ≥ 50 % in the survey round (`y_high`).
- Survey uncertainty is carried by `q_true` = P(prevalence ≥ 50 % | estimate, SE).
- Calibration uses `y_high`; `q_true` versions are reported as sensitivity.

**Forecast.** The five-seed mean probability (seeds 168, 1, 2, 3, 4), classified at a cut-off of 0.50.

**Intervals.** 95 % percentile bootstrap: 6,000 draws, seed 7, resampling province-rounds.

## 2. The seven rules

| Rule | Acceptance (Lead 1 unless stated) |
|---|---|
| 1 Data integrity | 100 % of checks pass (see 2.1) |
| 2 Forecast validity | 100 % of checks pass (see 2.2) |
| 3 Overall performance | Balanced accuracy ≥ 0.70 **and** AUROC ≥ 0.70 (point estimates). Accuracy, precision, recall, F1, confusion matrix and all intervals are reported. |
| 4 HIGH detection | HIGH recall ≥ 0.80 (point). Reported by lead, round and province; every miss is listed. |
| 5 HIGH reliability | HIGH precision ≥ 0.60 (point). Every false positive is listed. |
| 6 Probability reliability | See 2.6 |
| 7 Stability and reproducibility | See 2.7 |

**On point estimates.** With 25 HIGH and 47 LOW rows, the 95 % intervals are about ±0.10 wide. A lower-bound requirement is reserved for independent validation (section 5).

### 2.1 Rule 1 checks
- (a) No synthetic rows: every FINAL fit was run with no generator (configuration string `syn=None`) and the training tables carry `syn = 0` only.
- (b) Each evaluation row is a unique (province, round, lead).
- (c) No exact duplicate training rows: (province, round, origin).
- (d) Repeated origins of one training outcome are documented and never counted as independent evaluation cases.
- (e) Every outcome traces to a published FNRI table (file and source column).
- (f) Missing inputs are handled by MIND (training median plus a missing flag) with statistics from training rows only. Rates of missing inputs are reported for training and test rows.
- (g) The source register is documented: source, geography, reference period, release rule.

### 2.2 Rule 2 checks
- (a) For every evaluation row, the target quarter minus the origin equals the lead, and the target quarter is the survey's reference quarter.
- (b) The anchor survey was released (reference quarter + 6 quarters, the pipeline's release rule) on or before the origin.
- (c) Every training outcome was released on or before the fold's origin.
- (d) RATE uses only the gap (target minus anchor reference quarter, known at origin) and a training-mean gap. MIND uses training medians and the row's own missingness. Verified in code.
- (e) Input as-of construction: the existing leakage tests of the pipeline pass when re-run.
- (f) Operational alignment: the live use (CALABARZON, next quarter) is checked for gaps outside the training range. **This is reported, and is a Rule 7 limitation if violated.**

### 2.6 Rule 6: probability reliability

**As proposed (reported):** ECE (10 equal-width bins) ≤ 0.05; calibration slope in [0.80, 1.20]; calibration intercept in [−0.10, +0.10].

**Why it is adjusted.** A **perfectly calibrated** forecaster with n = 72 (`P0_threshold_pass_rates_perfect_model.json`):
- meets ECE ≤ 0.05 only 0.7 % of the time (median ECE 0.11);
- has slope in [0.80, 1.20] only 47 % of the time;
- has logit intercept within ±0.10 only 29 % of the time.

The proposed limits become meaningful at about 600–1,000 forecasts (ECE ≤ 0.05 for 84 % of perfect forecasters at n = 600 and 99.5 % at n = 1,000). The proposed rule therefore cannot distinguish a calibrated from a miscalibrated model at this sample size.

**Adjusted acceptance at n < 600 (all must hold).** These are tests of consistency with perfect calibration at the 5 % level. They have low power: a PASS means "no evidence of miscalibration", not "proven calibrated".
- **6a.** ECE ≤ the 95th percentile of ECE for the candidate's own probabilities with outcomes drawn as Bernoulli(p) (5,000 simulations).
- **6b.** Calibration in the large: |mean(p) − observed HIGH rate| ≤ 0.10. This is the brief's ±0.10 read on the probability scale; a perfect forecaster at n = 72 meets it 96 % of the time.
- **6c.** Cox calibration test: the joint likelihood-ratio test of intercept = 0 and slope = 1 is not rejected at α = 0.05.
- **6d.** Brier skill score against the training HIGH rate of each fold (a forecast available at origin) > 0.

Reported but not used for acceptance: Brier score; Brier against `q_true`; logit intercept and slope with intervals; a reliability diagram.

### 2.7 Rule 7: stability, uncertainty and reproducibility

All of the following must hold:
- **7a. Reproduction.** Refitting FINAL from the cached inputs, code and seed reproduces the stored predictions (max absolute difference ≤ 1e-9) for Lead 1, seed 168, all three rounds. The sealed forecast file hash is unchanged.
- **7b. Seeds.** Worst single-seed Lead 1 balanced accuracy ≥ 0.70.
- **7c. Rounds.** For each round with at least 4 HIGH and 4 LOW rows (all three qualify), Lead 1 balanced accuracy ≥ 0.60 **and** HIGH recall ≥ 0.50. A round below either is "severe instability".
- **7d. Leave one round out.** Pooled Lead 1 Rules 3–5 are recomputed without each round. Results are reported; a flip is noted as dependence on one round.
- **7e. Inputs.** Each trigger group's inputs are set to missing in turn (as if unpublished), with one refit per round, Lead 1, seed 168. Severe if Lead 1 balanced accuracy changes by more than 0.10 for any group.
- **7f. Operational range.** No serving gap may exceed the longest gap present in training rows. If one does, it is reported as an extrapolation limitation.

**Rule 7 is a FAIL** if 7a or 7b fails, or if any severe instability (7c, 7e) remains. **An explanation does not convert a severe instability into a PASS.**

## 3. Improvement candidates (Part B, written and hashed before any candidate is scored)

Candidates are defined after the diagnosis, which uses training rows only, in `PROTOCOL_SA_PARTB.md`, hashed before scoring.
- At most two candidates.
- Each is scored once on the 72 rows and labelled retrospective.
- No threshold, feature or province-specific correction may be chosen by reading 2018, 2019 or 2021 outcomes.

## 4. Decision mapping

| Evidence | Verdict |
|---|---|
| 7 of 7 on an independent provincial round | ACCEPT |
| 7 of 7 on the reused 72 rows only | CONDITIONALLY ACCEPT (pending independent validation) |
| Any rule failed | REJECT as a reliable standalone forecaster. Research use and prospective sealing remain allowed. |

## 5. Independent validation (future)

On an unseen provincial HFIAS round, with forecasts sealed before the outcomes:
- the same seven rules, plus the lower 95 % bound of balanced accuracy ≥ 0.60;
- the proposed Rule 6 limits once at least 600 forecasts accumulate.

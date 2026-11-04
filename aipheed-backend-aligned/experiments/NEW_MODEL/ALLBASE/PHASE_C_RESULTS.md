# ALLBASE, Phase C: results of the three pre-registered candidates

**Status:** development evidence only. The 62 quarters (targets 2010-Q1..2026-Q3) were examined before, so nothing
here is independent validation. No 2027 label exists or was read.

**Run details:**
- Pre-registration `PHASE_B_PREREGISTRATION.md`, SHA-256 `5001657e…6501`, hashed before any run and checked by every
  step. Not committed: committing is not authorized.
- Runner `runner/phase_c.py` (`features` → `fit` → `blend` → `score`); outputs in `out/`; registry in `REGISTRY.csv`.

## 1. Pre-checks (all passed)

| Check | Result |
|---|---|
| C-b refit reproduces stored C-b | 904 / 904 rows, max \|Δp\| 1.1e-16 |
| LOGIT regenerated from 1998-Q3 reproduces stored rows | 138 / 138 rows, max \|Δp\| 1.1e-16 (so K2 uses the regenerated history; no fallback) |
| K3 features: two independent implementations agree | 113 / 113 origins |
| K3 features: unchanged when every SWS round published on or after O(t) is randomized | 113 / 113 origins, 5 reps (172 future rounds changed in the test, 0 past rounds) |
| K2 weights: unchanged when forecasts from origins ≥ t and labels unknown at O(t) are randomized | All origins, both leads, 5 reps |
| K2: first origin with ≥ 20 eligible pairs | 2004-Q2 (Lead 1), 2004-Q3 (Lead 2); w = 0.5 before |

**Implementation detail fixed before the blend run:** in the K2 weight rule, a tie that remains after "closest to
0.5" goes to the lower w. The design did not specify this case.

## 2. Metrics (62 quarters per lead)

| Lead 1 | Accuracy | Balanced | Precision | Recall | F1 | AUC | Brier | ECE | TP/FP/FN/TN | Failed |
|---|---|---|---|---|---|---|---|---|---|---|
| C-b | **0.790** | 0.717 | 0.812 | 0.907 | **0.857** | 0.702 | 0.187 | 0.169 | 39/9/4/10 | R7 |
| K1 | 0.710 | 0.600 | 0.745 | 0.884 | 0.809 | **0.786** | **0.172** | 0.139 | 38/13/5/6 | R2, R3, R7 |
| K2 | 0.774 | 0.690 | 0.796 | 0.907 | 0.848 | 0.704 | 0.188 | 0.144 | 39/10/4/9 | R3, R7 |
| K3 | 0.774 | 0.705 | 0.809 | 0.884 | 0.844 | 0.687 | 0.190 | 0.171 | 38/9/5/10 | R5, R7 |

| Lead 2 | Accuracy | Balanced | Precision | Recall | F1 | AUC | Brier | ECE | TP/FP/FN/TN | Failed |
|---|---|---|---|---|---|---|---|---|---|---|
| C-b | **0.790** | 0.717 | 0.812 | 0.907 | **0.857** | 0.704 | 0.184 | 0.152 | 39/9/4/10 | R7 |
| K1 | 0.774 | **0.734** | 0.837 | 0.837 | 0.837 | **0.710** | 0.185 | 0.148 | 36/7/7/12 | R7 |
| K2 | 0.790 | 0.717 | 0.812 | 0.907 | 0.857 | 0.704 | 0.184 | 0.152 | 39/9/4/10 | R7 (identical to C-b: w = 1) |
| K3 | 0.774 | 0.705 | 0.809 | 0.884 | 0.844 | 0.703 | **0.182** | **0.139** | 38/9/5/10 | R7 |

**Algorithm 3 (MRLT):**
- C-b 2; K2 2; K3 2.
- K1 0 (Lead-1 accuracy 0.710). A blend's MRLT is capped at 2, because LOGIT exists at Leads 1–2 only.

**Algorithm 4:** not testable. It needs the first four sealed 2027 quarters, which have no labels yet.

**Against C-b** (paired Brier, one-sided; reported separately from the 42-test family):

| | Lead 1 | Lead 2 |
|---|---|---|
| K1 | −0.016 (95% CI −0.053..0.020), p 0.21, 9 calls changed | +0.001, p 0.54, 7 calls changed |
| K2 | +0.001, p 0.63, 1 call changed | 0.000, 0 calls changed |
| K3 | +0.003, p 0.66, 3 calls changed | −0.002 (95% CI −0.013..0.010), p 0.40, 3 calls changed |

**What K2 learned.** In the evaluation window K2's weight on C-b is 0.8–1.0 at Lead 1 and 1.0 at Lead 2: the
historical record prefers C-b alone. The fixed 50/50 average (K1) gives the best Lead-1 AUC and Brier of any model so
far (0.786 / 0.172), but it loses 8 points of accuracy at the 0.50 cut and fails R2 and R3.

## 3. The single 42-test Holm family (3 candidates × 7 baselines × 2 leads, paired Brier)

"Better" = Holm-adjusted p < 0.05 with a lower Brier. Each entry gives the Brier difference, the raw p and the Holm p.

| Candidate, lead | Persistence | PSA-only logistic | Combined logistic | NLP-only logistic (n 20/19) | LightGBM gov-only | LightGBM NLP-only (n 20/19) | Always-HIGH | Better |
|---|---|---|---|---|---|---|---|---|
| K1 L1 | −0.167, p 0.000, Holm 0.000 ✓ | −0.036, 0.072, 0.652 | −0.021, 0.112, 0.652 | −0.204, 0.001, 0.027 ✓ | −0.061, 0.001, 0.038 ✓ | −0.158, 0.002, 0.056 | −0.135, 0.004, 0.094 | 3 / 7 |
| K1 L2 | −0.154, 0.001, 0.021 ✓ | −0.054, 0.045, 0.450 | −0.049, 0.003, 0.084 | −0.271, 0.000, 0.000 ✓ | −0.055, 0.006, 0.147 | −0.147, 0.001, 0.027 ✓ | −0.121, 0.011, 0.179 | 3 / 7 |
| K2 L1 | −0.151, 0.000, 0.008 ✓ | −0.020, 0.260, 1.000 | −0.005, 0.442, 1.000 | −0.157, 0.002, 0.064 | −0.045, 0.004, 0.094 | −0.111, 0.005, 0.120 | −0.118, 0.009, 0.156 | 1 / 7 |
| K2 L2 | −0.155, 0.000, 0.008 ✓ | −0.055, 0.040, 0.436 | −0.050, 0.079, 0.652 | −0.228, 0.003, 0.092 | −0.056, 0.002, 0.060 | −0.103, 0.020, 0.265 | −0.123, 0.008, 0.155 | 1 / 7 |
| K3 L1 | −0.148, 0.000, 0.014 ✓ | −0.018, 0.281, 1.000 | −0.003, 0.470, 1.000 | −0.143, 0.007, 0.155 | −0.042, 0.008, 0.156 | −0.097, 0.018, 0.246 | −0.116, 0.008, 0.156 | 1 / 7 |
| K3 L2 | −0.157, 0.000, 0.008 ✓ | −0.057, 0.031, 0.370 | −0.052, 0.081, 0.652 | −0.207, 0.014, 0.210 | −0.058, 0.000, 0.008 ✓ | −0.082, 0.081, 0.652 | −0.124, 0.006, 0.147 | 2 / 7 |

- **Every Brier difference is negative.** All three candidates are numerically better than every baseline at both
  leads, but most differences are not significant after the 42-test correction.
- **No candidate passes all 14 of its comparisons.** The unmet ones are always the two logistic regressions, and
  usually always-HIGH and the news-only models.
- **Power:** beating LOGIT at Lead 1 at the observed effect would need about 417 quarters for K1, 32,457 for K2 and
  125,569 for K3 at Holm's strictest step. Full per-test detail (CI, skill score, n, power) is in
  `out/phase_c_results.json`.

## 4. Gates (pre-registered, reported individually)

| Gate | K1 | K2 | K3 |
|---|---|---|---|
| G1 all 14 comparisons significant (42-test Holm) | ✗ (6 / 14) | ✗ (2 / 14) | ✗ (3 / 14) |
| G2 improves C-b (both leads p < 0.10, accuracy not lower) | ✗ | ✗ | ✗ |
| G3 R1–R7 at both leads | ✗ (R2, R3, R7) | ✗ (R3, R7) | ✗ (R5, R7) |
| G4 Algorithm 3 MRLT ≥ 2 | ✗ (0) | ✓ (2) | ✓ (2) |
| G5 R7 fixed without displacement | ✗ | ✗ | ✗ |
| **Adoption (G2 and G4)** | **No** | **No** | **No** |

**Selection on fold S (2010–2017):**
- No candidate is eligible.
- K1 has the lowest Lead-1 Brier there (0.146 vs C-b's 0.176) but is worse at Lead 2 (0.169 vs 0.164).
- K2 is worse than C-b at Lead 1.
- K3 is worse than C-b at Lead 1 (0.178 vs 0.176).
- **No candidate is chosen. C-b stays the main model.**

## 5. R7 investigation

**Reversal events** (label side differs from the newest known reading): 21 of 62 quarters at each lead, 12 (Lead 1)
and 11 (Lead 2) of them in 2015-Q2..2020-Q4.

| Lead 1 | Full accuracy | Reversal recall | Non-reversal acc. | 2010–15 | **2015–20** | 2021–26 | Reversal recall 2015–20 |
|---|---|---|---|---|---|---|---|
| Persistence | 0.661 | 0.000 | 1.000 | 0.905 | 0.429 | 0.650 | 0.00 |
| C-b | 0.790 | 0.524 | 0.927 | 0.952 | **0.571** | 0.850 | 0.50 |
| K1 | 0.710 | 0.333 | 0.902 | 0.952 | 0.476 | 0.700 | 0.25 |
| K2 | 0.774 | 0.476 | 0.927 | 0.952 | 0.571 | 0.800 | 0.50 |
| K3 | 0.774 | 0.524 | 0.902 | 0.952 | 0.571 | 0.800 | 0.50 |

**Lead 2:**
- C-b and K2: middle third 0.571, reversal recall 0.455.
- K3: 0.571.
- K1: 0.524.

**Finding.**
- **Within the frozen R7 definition and periods, no quarter removed, none of the candidates moves the 2015–2020
  third.** K3's reversal features change 3 calls per lead (origins 2017-Q3, 2020-Q2 and 2025-Q3). Two fall in that
  third, one becoming right and one wrong, so there is no net change; the third costs one quarter in 2021–2026.
- **The model already catches about half the reversals; the other half were not anticipated by anything available at
  the issue date,** including the history of crossings and alternations.
- With a noise ceiling of 0.773 in that third (Phase A), the gap is not survey noise alone. It is still not
  reachable with these inputs.

## 6. Prospective registry (prepared and verified; not active until committed)

**Scripts changed** (`SENIOR_REVIEW/runner/`):
- `prospective_lib.py`: models, K3 features, K2 rule, registry fields.
- `seal_next.py`: seals every model, plus the replay.
- `score_prospective.py`: scores every model, plus Algorithm 4 and the prospective 42-test family.

**What every issue date now seals:** C-b, REF+news, REF, K1, K2, K3, persistence, PSA-only logistic, combined
logistic, NLP-only logistic, LightGBM gov-only, LightGBM NLP-only, always-HIGH and CLIM, at Leads 1–2 (28 rows).

**Fields on every row:**
- `model_id`, `model_version` (column and setting hash plus commit), `feature_version`, `config_sha256`;
- issue date, `sealed_at` (UTC), lead, target, probability, class;
- `feature_cutoff` (newest month or quarter per source);
- `input_hashes` (dataset version);
- `generation_record`: library versions, script hashes, the Phase C runner hash, the pre-registration hash, and the
  hashes of K2's history files.

**Verification:**

| Test | Result |
|---|---|
| Dry-run seal 2026-10-01 | Replay exact for every model with a stored value (C-b, REF+news, REF, K1–K3, the three logistic regressions, always-HIGH, PERSIST, CLIM; max \|Δp\| 3e-16); table rows, z_N1R and the reversal features equal |
| Dry-run seal 2026-07-01 | Replay exact, including LightGBM gov-only and NLP-only (stored only to origin 2026-Q2) |
| Scorer on a replay of all stored development forecasts | Every model's metrics equal the Phase C values; the independent R1–R7 check agrees for every model; the prospective 42-test family reproduces the historical one exactly (diff, p, Holm p) |
| Existing dry-run harness | 11 / 11 pass |
| Real `prospective/` folder and ledger | Untouched (no seal row) |

**Still needed before the 2027-01-01 issue date:**
- The real sealer refuses while the model code is uncommitted. This now includes `NEW_MODEL/ALLBASE/runner/` and the
  pre-registration.
- So the registry becomes active only after you authorize a local commit of:
  - `ALLBASE/` (documents, runner, `out/`, `REGISTRY.csv`);
  - the three changed scripts;
  - a "Scripts revision 3" block appended to `SEAL_LEDGER.md` with the new hashes, which I have not written into the
    ledger yet.
- The data refresh before sealing is still needed, as before.
- If the commit does not happen before the 2027-01-01 sealing window closes (14 days), the expanded registry starts
  at 2027-04-01. C-b's own 2027-Q1 Lead-2 forecast is already sealed (`67baec66`).

**Current script hashes (for the revision-3 ledger block; LF line endings restored 2026-11-03):**
- `prospective_lib.py` `11ec4142…3871`
- `seal_next.py` `2c744a47…10b7`
- `score_prospective.py` `f2a3f913…039e`
- `dryrun_test.py` `5794a5bf…e4f8` (unchanged)
- `ALLBASE/runner/phase_c.py` `5be352e6…2374`

## 7. Conclusion

- **The improvement attempts K1–K3 all fail the pre-registered adoption rule. C-b stays the main model**, unchanged.
- **No all-baseline claim can be made.** The combined and PSA-only logistic regressions remain statistically
  unbeaten at both leads, as Phase A predicted.
- **The one honest route to that test is now prepared:** the sealed prospective comparison of C-b, K1–K3 and all
  seven baselines. It is reported separately from this historical family, from 20 labelled quarters per lead
  (around 2032), with Algorithm 4 on the first four 2027 quarters (point values only).
- **Thesis wording this supports:** "Three pre-registered refinements of C-b were tested (a fixed and a historically
  weighted average with logistic regression, and hunger-reversal features). None improved C-b under the pre-registered
  criteria. The 50/50 average raised Lead-1 AUC to 0.786 but lowered accuracy to 0.710. In a single Holm family
  of 42 tests, every candidate had a lower Brier score than every baseline, and each was significantly better than
  persistence at both leads. None was significantly better than the PSA-only or combined logistic regressions with 62
  quarters."

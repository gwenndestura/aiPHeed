# RELIABLE_NEWINFO: results (EXPLORATORY, the last attempt)

**Plan:** `PLAN.md`, SHA-256 `ffb69ae2…2cb3` (commit `adab6f0`). It was run exactly as written:
`runner/fetch_chirps.py`, then `runner/run_newinfo.py` with `features`, `fit`, `score` and `seal`.

**Evidence status:** development evidence; the last attempt; two candidates.

## Decision

**Neither candidate passes all of R1–R7 at both Lead 1 and Lead 2.** REF+news stays the main model under the paper's 75%
rule (Maximum Reliable Lead Time 2). **The attempts to pass R1–R7 are closed.** Nothing is sealed.

## 1. Checks

- **Plan known before the run.** The 0/1 PERSIST blend (0.5 × REF + 0.5 × PERSIST) was checked before the plan. It
  gives persistence's call in 62 of 62 quarters, accuracy 0.661, and **fails R2 and R4 by construction**. It was not a
  candidate.
- **CHIRPS rainfall** (`data/chirps_hashes.json`):
  - daily data 1981-01-01..2026-09-30 from SERVIR ClimateSERV (datatype 0), averaged over 120.6–122.5°E,
    13.6–14.9°N;
  - 549 complete months, 10 raw JSON files, each with its SHA-256; monthly CSV `399bfb43…`;
  - mean annual total 2,645 mm;
  - today's vintage.
- **Publication rule.** Month m is used at issue date O(t) only from the first day of month m+2. The 2026-10-01 issue
  uses months up to 2026-08.
- **Base years.** The z-scores are standardized on 1981–1997 only. Across the 113 origins they average +1.1 (`RF_z3`) and
  +1.3 (`RF_z6`): the recent decades are wetter than the base years, or the product has drifted. Disclosed, not
  adjusted.
- **Refit machinery.** The refit code with REF's columns reproduces the stored REF Lead-1 and Lead-2 forecasts: 226 of
  226 rows, the same configuration at every origin, max |Δp| = 1.1e-16 (floating-point rounding; the plan's limit is
  1e-12).

## 2. Per lead (62 labelled quarters, targets 2010-Q1..2026-Q3, threshold 0.50)

| | REF (reference) L1 / L2 | **C1 BLEND** (0.5 REF + 0.5 `pi_H4L`) L1 / L2 | **C2** REF + rainfall L1 / L2 |
|---|---|---|---|
| Accuracy | 0.790 / 0.790 | 0.742 / 0.758 | 0.790 / 0.790 |
| Balanced accuracy | 0.717 / 0.717 | 0.667 / 0.693 | 0.717 / 0.717 |
| Precision | 0.812 / 0.812 | 0.787 / 0.804 | 0.812 / 0.812 |
| Recall | 0.907 / 0.907 | 0.860 / 0.860 | 0.907 / 0.907 |
| F1 | 0.857 / 0.857 | 0.822 / 0.831 | 0.857 / 0.857 |
| AUC | 0.702 / 0.704 | **0.727 / 0.752** | 0.713 / 0.710 |
| Brier | 0.1875 / 0.1838 | **0.1842 / 0.1777** | 0.1862 / 0.1829 |
| TP / FP / FN / TN | 39/9/4/10 both | 37/10/6/9 · 37/9/6/10 | 39/9/4/10 both |
| Rules failed | R7 · R7 | **R2, R3, R7 · R3, R7** | **R7 · R7** |

### R1–R7 with values

| Rule | C1 L1 | C1 L2 | C2 L1 | C2 L2 |
|---|---|---|---|---|
| R1 | pass (62) | pass (62) | pass (62) | pass (62) |
| R2 accuracy ≥ 0.75 | **fail 0.742** | pass 0.758 | pass 0.790 | pass 0.790 |
| R3 balanced ≥ 0.70 | **fail 0.667** | **fail 0.693** | pass 0.717 | pass 0.717 |
| R4 > 0.306 and > 0.661 | pass | pass | pass | pass |
| R5 Brier vs persistence; vs climatology | pass: −0.155 (p 0.000); −0.037 (p 0.067) | pass: −0.161 (0.000); −0.045 (0.026) | pass: −0.153 (0.000); −0.035 (0.087) | pass: −0.156 (0.000); −0.039 (0.063) |
| R6 precision / recall ≥ 0.60 | pass 0.787 / 0.860 | pass 0.804 / 0.860 | pass 0.812 / 0.907 | pass 0.812 / 0.907 |
| R7 thirds ≥ 0.60; LOQO min ≥ 0.70 | **fail**: 0.952 / **0.429** / 0.850; LOQO 0.738 | **fail**: 0.952 / **0.476** / 0.850; LOQO 0.754 | **fail**: 0.952 / **0.571** / 0.850; LOQO 0.787 | **fail**: same as L1 |

**C2.** The rainfall columns take 2.0% of SHAP influence. They change **no** call: C2's calls equal REF's in every
quarter. Brier and AUC improve slightly, not significantly tested here.

**C1.** The blend has the best Brier and AUC of all, but it makes **more** errors in 2015–2020 (9 of 21 correct at Lead 1, 10 at Lead 2, against REF's 12). It
leans further on the latest reading, which is exactly what fails when hunger reverses every quarter.

## 3. Sensitivity only (not used for the decision): without the mobile-phone SWS quarters

**Correction to the plan text.** The plan's prose named 2020-Q2..Q4. Its rule ("from the SWS `mode` column") excludes
only **2020-Q2 and 2020-Q3**: the November 2020 round (2020-Q4) is recorded as face-to-face. The rule was applied as
written, so 60 quarters remain.

| | Rules failed L1 / L2 | Middle third, L1 / L2 |
|---|---|---|
| REF (reference, not a candidate) | none / none | 0.60 / 0.65 |
| C1 | R3, R7 / R7 | 0.50 / 0.55 |
| C2 | none / none | 0.60 / 0.65 |

**Reading the sensitivity, plainly:**
- Dropping two of the 62 quarters lets REF and C2 pass all of R1–R7. Their middle third rises from 12/21 (0.571) to
  12/20 (0.60, **exactly the cut-off**) at Lead 1.
- REF does this on its own, so it is not the rainfall's doing.
- The exclusion was fixed in the plan as sensitivity only and was chosen knowing that the failing third is one quarter
  short. It **cannot** count as a pass.
- What it shows is how close to the line R7 is: one quarter decides it.

## 4. Conclusion

| Candidate | Result |
|---|---|
| C1 (blend with `pi_H4L`) | Better probabilities (Brier 0.184 / 0.178, AUC 0.73 / 0.75), but worse calls; fails R2/R3/R7 at Lead 1 and R3/R7 at Lead 2 |
| C2 (REF + CHIRPS rainfall) | Identical calls to REF; fails R7 only at both leads |

With RELIABLE_L12 (threshold rule), these were the planned last attempts. **No version of the food-insecurity model
passes R1–R7 at Leads 1 and 2 on the full window.**
- The binding failure is R7's 2015–2020 third.
- The Step-0 diagnosis explains it: quarterly reversals within the SWS sampling error of the 11.3% line.
- Under the paper's own 75% rule, REF+news (the main model) and REF both reach a Maximum Reliable Lead Time of 2.

## 5. Files

| File | Content |
|---|---|
| `runner/fetch_chirps.py` | The download |
| `data/chirps_raw/` | 10 raw JSON responses |
| `data/chirps_monthly.csv` | Monthly totals |
| `data/chirps_hashes.json` | Hashes and source |
| `runner/run_newinfo.py` | The run |
| `out/rain_features.csv` | `RF_z3`, `RF_z6` per origin |
| `out/forecasts_c2.csv` | C2 and the REF reproduction rows |
| `out/checks.json` | Reproduction and hashes |
| `out/results.json` | All numbers above |
| `out/fit_log.txt` | The fit log |

No seal file was written.

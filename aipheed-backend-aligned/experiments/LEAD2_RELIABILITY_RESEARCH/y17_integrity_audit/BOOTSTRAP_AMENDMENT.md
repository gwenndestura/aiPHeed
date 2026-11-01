# Y16 Amendment 1: block-bootstrap sensitivity analysis and evaluation record-keeping

| Item | Value |
|---|---|
| Amends | `EXPERIMENT_PLAN.md`, SHA-256 `208b575464d21e41dd78447c39e4586fb7101bdb0b263f298b210b7701bd9699` (unchanged; not edited) |
| Frozen | Before any prospective outcome exists. The first issue is 2027-01-01; its target (2027-Q2) resolves at the earliest on 2027-10-28. No valid Y16 seal exists at freezing. |
| Hash | `BOOTSTRAP_AMENDMENT_SHA256.txt`; time in `BOOTSTRAP_AMENDMENT_FROZEN_AT.txt` |
| Motivation | Y17 audit finding F14: the registered primary bootstrap resamples quarters independently, but quarterly hunger, and therefore the paired loss differences, may be serially correlated |

## 1. What does not change

**The primary analysis is exactly as registered in `EXPERIMENT_PLAN.md` section 5:**

- the first 20 resolved paired target quarters;
- d_i = Brier_KAL,i − Brier_PERS,i;
- an i.i.d. bootstrap over quarters, B = 5000, seed 2036;
- a 95% percentile CI;
- a one-sided p.

**Superiority is claimed if and only if all three hold:**

| | Condition |
|---|---|
| (a) | the i.i.d. bootstrap p < 0.05 |
| (b) | the i.i.d. 95% CI upper bound < 0 |
| (c) | the exact sign test p < 0.10 |

**Also unchanged:**

- the seven rules, the 0.50 threshold, the target, the horizon and the models;
- the staging: fewer than 8 resolved quarters is integrity only; 8–19 is descriptive; 20 is the primary analysis.

## 2. New: prespecified sensitivity analysis (moving-block bootstrap)

| Item | Definition |
|---|---|
| Statistic | Mean of d_i over the same 20 primary quarters |
| Ordering | The d_i are ordered by target quarter. A quarter excluded from the primary set (missing outcome, no forecast, missed issue) is **not** imputed. The series is the available pairs in time order. The number of gaps is reported. |
| Block length | **L = 4** consecutive pairs (one year). Fixed now and not tuned. |
| Resampling | Non-circular moving blocks. Each replicate draws ⌈n / L⌉ block start positions uniformly from {0, …, n − L}, concatenates the blocks, and truncates to n values. |
| Replicates and seed | B = 5000, `numpy.random.default_rng(2036)`. The seed is fixed and the analysis is run once (see section 4). |
| Interval and p | 95% percentile CI; one-sided p = the share of replicate means ≥ 0 |
| Minimum sample | n ≥ 2L = 8. Below that the result is reported as "unavailable" (it cannot arise at the primary analysis, n = 20). |

**Interpretation and reporting.** The block result is reported **next to** the primary result, in the same table, labelled "sensitivity: moving-block bootstrap (Amendment 1)".

| Primary result | Block bootstrap: p < 0.05 and CI upper < 0? | How it is reported |
|---|---|---|
| Superiority | Yes | "superiority, robust to serial dependence" |
| Superiority | No | "superiority under the registered test; **not robust** to serial dependence". Both are reported; the primary verdict is not withdrawn, but must be qualified everywhere it is cited. |
| No superiority | Either | "no superiority". **The sensitivity analysis can never turn a failed primary result into a pass**, and its thresholds are never loosened. |

## 3. Registered reporting items that the original evaluator omitted

These are in `EXPERIMENT_PLAN.md` section 5 but were missing from the code (Y17 F10, F11, F12). They are **reporting and integrity items. They do not enter the superiority decision.** The outputs label them "supplementary (registered reporting item)".

| Item | Definition |
|---|---|
| **Calibration** | 5 equal-count bins of the forecast probability (mean forecast, observed frequency, n per bin). The logistic calibration slope and intercept (logit of probability as the single predictor, effectively unpenalised) are computed only when n ≥ 10 and both classes are present, otherwise "unavailable". Reported for PERS and KAL at the descriptive and primary stages. |
| **Missed issues** | Every scheduled issue date from 2027-01-01 whose 8-day window has closed (by Manila date) and that has no valid seal is listed as missed. Missed issues are excluded from both models, and their count is reported. Failed attempts (Y18 attempt log) are reported next to them. |
| **Overlay verification** | Each valid seal records the overlay rows it used. Before any metric is computed, every recorded row must still be present, unchanged, in the current overlay. Any removal or change is an integrity failure: the evaluation stops and reports it. |

## 4. Procedural safeguards (record-keeping, not analysis)

- **Primary lock.** The first evaluation run that reaches 20 resolved quarters writes `out/PRIMARY_ANALYSIS.json` with exclusive create. It contains the primary targets, both analyses (primary and sensitivity), and a hash of the inputs. Every later run recomputes the result: if it is identical it reports "primary locked (unchanged)"; if it differs it stops with an integrity error. The primary file is never rewritten.
- **Re-issues.** A second valid seal for an issue date that already has one is refused at issuance. A re-issue found later (e.g. a manually copied file) is reported, and only the first seal by write time counts, as registered.
- **Clock source.** Valid seals are written with the system clock by `issue.py`. A seal produced through the library with a caller-supplied clock is marked as such, and is refused by the real evaluation (allowed only in tests).
- **External attestation.** It is recorded as `pending`, `completed` or `unavailable`, per seal, from operator entries only (Y18 X6). It is never inferred.

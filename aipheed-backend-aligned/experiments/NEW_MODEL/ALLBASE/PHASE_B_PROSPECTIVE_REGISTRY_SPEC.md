# ALLBASE, Phase B: prospective forecast registry specification (O5)

**Purpose:** seal, every quarter, the forecasts of C-b **and its baselines** before their outcomes exist, so that Lead-1
and Lead-2 comparisons (H3, Objective 4) and Algorithm 4 can be tested on data nobody has seen.

**Implementation:** an extension of the existing prospective scripts (`SENIOR_REVIEW/runner/`, ledger
`SENIOR_REVIEW/prospective/SEAL_LEDGER.md`, Addendum CB). It is not implemented in Phase B. The change must be
authorized, implemented, dry-run tested, committed and re-hashed in the ledger **before 2027-01-01**. Otherwise the
first issue date it can cover is 2027-04-01.

## 1. Models sealed at every issue date

| Model | Status | Specification (unchanged) |
|---|---|---|
| **C-b** | Main (Addendum CB) | `prospective_lib.MODELS["C-b"]` |
| REF+news, REF | Already sealed (comparators) | `prospective_lib.MODELS` |
| **Combined logistic (LOGIT)** | **To add** | `iv2_lib.logit_lead` on `V.cols(False, False)`, one model per lead, walk-forward |
| **PSA/government-only logistic** | **To add** | `iv2_lib.logit_lead` on `V.PSA` |
| Persistence, climatology | Already sealed | `prospective_lib.baselines` |
| Always-HIGH | Implied (p = 1) | — |
| NLP-only logistic, government-only LightGBM, NLP-only LightGBM | **To add** (approved) | IMPROVE_V2 / OBJECTIVES_COMPLETION specifications |
| **K1, K2, K3** | **To add** (approved) | `PHASE_B_EXPERIMENT_DESIGN.md` §1–§3 |

**Approved.** All seven comparators, C-b and K1–K3 are sealed, so the prospective 42-test family (statistical plan
§6) can be computed.

## 2. Fields of every sealed row

| Field | Content |
|---|---|
| `model_id`, `model_version` | Name, plus SHA-256 of its column list and settings, plus the code commit |
| `feature_version` | SHA-256 of the feature-construction code and column list (for K3: the reversal-feature function) |
| `config_sha256` | SHA-256 of the model configuration (grid, weight rule, seed) |
| `issue_date`, `sealed_at` | The first day of the quarter; the UTC timestamp of sealing (within 14 days, before any target round) |
| `origin`, `lead`, `target_quarter` | As now |
| `p_high`, `class` | The probability (full precision) and HIGH/LOW at 0.50 |
| `feature_cutoff` | For each source: the newest period used (CPI month, ONI month, Pink Sheet month, production quarter, typhoon quarter, news quarter, newest SWS round and its publication date) |
| `input_hashes` | SHA-256 of every input file (as now) |
| `stale_sources` | Freshness keys accepted as stale, if any (as now) |
| `generation_record` | Script hashes (from the ledger), Python and LightGBM versions, the dry-run/replay status |
| `plan_sha256` | The prospective plan, Addendum CB, and this registry's addendum (once hashed) |

## 3. Rules

- Every prediction is sealed **before** any SWS round of its target quarter is published, and within 14 days of the
  issue date. A late forecast is missing, never back-filled (unchanged).
- The ledger lists each file's SHA-256. The scorer verifies every hash before scoring (unchanged).
- **Algorithm 4.** The first four labelled prospective quarters per lead (from 2027-Q1) are the blind holdout:
  - F1 and AUC are scored once, as point values;
  - their labels are not read before the scoring date;
  - nothing is tuned on them.
- **Power disclaimer.** Four quarters give almost no statistical power, so collection continues. The 42-test family is
  first computed at ≥ 20 prospective quarters per lead; the R1–R7 verdict at 40.

## 4. Dry-run requirements (before activation)

1. **Replay:** a replay of 2026-10-01 must reproduce the stored LOGIT and PSA-only forecasts for that origin exactly
   (as is already done for C-b, REF+news and REF).
2. **Harness:** the existing 11-test dry-run harness passes, with the new models included in the replay check.
3. **Ledger:** new script hashes are appended to the ledger. No real seal is written by a dry run.

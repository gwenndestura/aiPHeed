# C-E prospective validation plan: C-E2 and C-E6 beside C-b (fixed 2026-11-04, before any prospective seal)

**Purpose:** obtain evidence on quarters that no model has seen. C-b, its baselines and its plan
(`SENIOR_REVIEW/PROSPECTIVE_PLAN.md`) are unchanged and are sealed by `SENIOR_REVIEW/runner/seal_next.py`. C-E2 and
C-E6 are sealed **separately** by `OBJECTIVES_AUDIT/runner/seal_ce.py` into `OBJECTIVES_AUDIT/prospective_ce/`, with
their own ledger. This plan adds models; it changes nothing in the C-b protocol.

**Status of the models:**
- C-b: main model (sealed 67baec66).
- C-E2: development / demo candidate.
- C-E6: development candidate.
- None of the C-E models is adopted.

## 1. Models sealed by this plan

| Model | Definition | Pre-registration | Leads sealed |
|---|---|---|---|
| C-E2 | `ce2_model._origin`: 23 inputs, mean of the 8 `hr_lib.GRID` settings | CE2_PREREGISTRATION.md a1b469da… | 1, 2, 3 |
| C-E6 | `ce6_model._origin`: C-E2 + ST1, ST2 (PSA rice stocks) | CE6_PREREGISTRATION.md 6e07ee14… | 1, 2, 3 |

Lead 3 is sealed so that Algorithm 3 (MRLT 3 in development) can be checked prospectively. The baselines and C-b are
sealed by `seal_next.py` at Leads 1–2 only, so all comparisons use Leads 1–2.

## 2. Issue dates and window

- **Issue dates:** every quarter start from 2027-01-01. O(t) is the issue date; t is the origin quarter.
- **Window:** a seal is written between the issue date and 14 days after it. A missed window is recorded as missing and
  never back-filled.
- **Authorization:** a real seal requires the file `prospective_ce/AUTHORIZATION_<issue>.txt` containing the line
  `AUTHORIZED: seal_ce <issue>`, created by the project owner. Without it, the script refuses.
- **Code state:** the model code (`OBJECTIVES_AUDIT/runner`, the CE pre-registrations, this plan) must be committed
  before a real seal. A dirty tree refuses.
- **No target revealed:** no SWS round of any target quarter may be published by the seal date.

## 3. Inputs at O(t) (no future information)

- **Table:** the BL rows of the IMPROVE_V2 pooled table, rebuilt from the current data files (`prospective_lib.
  build_table`), plus C-b's news anomaly (`add_news_anomaly`). This is exactly as `seal_next.py`.
- **E2:** `ce_model.e2_series` from the IMF personal-transfers file. It reads quarters ≤ t − 2 only.
- **ST1, ST2:** `ce6_model.st_values`. Stock month M ≤ (issue month) − 4 only (verified release lags 31–92 days).
- **Freshness:** a source whose newest allowed period is missing at O(t) is "stale".
  - Sources: the `prospective_lib.freshness` keys, plus `remittance_quarter_t-2` and `rice_stock_month_issue-4`.
  - A real seal refuses unless each stale key is named with `--allow-stale`. Named keys are recorded in the seal;
    their inputs are NaN.
- **Training labels:** labels known at O(t) only (`V.known_labels`).

## 4. Artifact

- **File:** `prospective_ce/sealed_ce_<issue>.csv`, one row per model × lead.
- **Columns:** issue date, origin, lead, target quarter, model id, pre-registration SHA-256, model code SHA-256s,
  p_high, class (HIGH at 0.50), persistence and climatology at O(t), newest SWS quarter and its publication date, feature
  cutoffs, stale sources, input-file SHA-256s, code commit, sealed_at, dry_run flag.
- **Ledger:** the file's SHA-256 is appended to `prospective_ce/SEAL_LEDGER_CE.md`. Sealed files are never edited.

## 5. Evaluation (`runner/score_ce_prospective.py`)

- **Labels:** `prospective_lib.labels_at(scoring_date)`: the mean of non-commissioned BL rounds published before the
  scoring date, for quarters that have ended; y = H > 11.3. Only targets ≥ 2027-Q1 are scored. **A target without a
  published label is never scored.**
- **Sources:** C-b and the baselines (persistence, LOGIT, PSA-only, NLP-only, LGBM-GOV, LGBM-NLP, ALWAYS-HIGH, CLIM)
  come from the C-b protocol's ledger (`SENIOR_REVIEW/prospective/SEAL_LEDGER.md`) and its C-b seal by reference, read
  only. C-E2 and C-E6 come from `SEAL_LEDGER_CE.md`. Every file's SHA-256 must match its ledger, or nothing is scored.

**Per model and lead:**
- metrics: accuracy, balanced accuracy, precision, recall, F1, AUC, Brier, ECE;
- the frozen R1–R7 (`hr_lib.evaluate`);
- the 75% rule with a 90% Wilson interval;
- **Algorithm 4:** the first four labelled quarters, F1 and AUC as point values.

**Families (paired Brier, one-sided quarter-cluster bootstrap via `phase_c._paired`, seed 2036, B 5000):**

| Family | Tests | Correction |
|---|---|---|
| **P1** | C-E6 vs the 7 baselines × Leads 1–2 | Holm over 14 |
| **P2** | C-E6 vs C-E2 and vs C-b × Leads 1–2 | Holm over 4 |
| **P3** (descriptive) | C-E2 vs the 7 baselines × Leads 1–2 | Holm over 14 |

- **When:** each family is computed only when every model in it has ≥ 20 labelled prospective quarters at each lead.
  Before that it reports "not yet".
- **Status:** below 40 labelled quarters per lead, every verdict is "insufficient prospective evidence".

**The four questions, kept separate:**
1. **Better probabilities:** P2 Brier, p < 0.05 after Holm.
2. **Better HIGH/LOW calls:** the discordant calls vs C-E2 and vs C-b, exact McNemar (two-sided). Descriptive.
3. **Temporal stability:** R7 on the prospective quarters, only from 40 quarters.
4. **All-baseline superiority:** all 14 P1 tests significant at 0.05 after Holm.

## 6. Fixed rules

- **No change after the first seal:** no change to the models, features, lags, families or thresholds. A change
  needs a new plan with a new SHA-256, and earlier seals stay scored under this one.
- **Thresholds and target unchanged:** target 11.3% and threshold 0.50.
PLAN-SHA256: 9392917aeaabbbecf5040f13aefdea4b9ff55368c9dc9fb2e3917a85e0e4d24c

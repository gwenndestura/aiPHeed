# C-B7 pre-registration: C-B6 + a consistent-source news index, 2017–2026 (fixed 2026-11-04, before any headline is classified or scored)

**Development evidence;** the 24th historical attempt. C-B6 (main model) stays unchanged unless C-B7 passes the rule
below and you approve.

## New data and why

- **Regional unemployment (Region IV-A, quarterly): NOT available.** PSA OpenSTAT `1B/LFS` and `3K/E2` publish
  national series only (checked 2026-11-04). Regional rates exist only in PDF releases, so this arm is dropped. It is
  reported, not replaced.
- **News 2017–2026 from ONE source:** GDELT DOC 2.0 headlines (`runner/news_g_fetch.py`).
  - Query: the CALABARZON place + food query of `OLD_NEWS/FEASIBILITY.md` §2.
  - Same instrument in both eras. C-B6's `z_N1R` exists only from 2023 (the project corpus starts in 2021), so it
    cannot inform the 2017–2022 quarters.

## Index (fixed)

1. **Admission:** `app.news.classifier_v2.classify(title, geocode_to_province)` with `relevant == 1`; titles only.
   De-syndicated as `pipeline_v3.dedupe` (same normalised title within its window).
2. **Date and quarter:** GDELT `seendate` (UTC) converted to Asia/Manila. An article belongs to quarter t if its PH
   date is in t. At origin t, only articles of quarter t published before O(t) are used.
3. **Intensity:** the XLM-RoBERTa FSSI-v2 scorer (`app.ml.nlp.classifier`, `joeddav/xlm-roberta-large-xnli`, ten
   HungerGist hypotheses, max entailment), as `fssi_v2.score_admitted`.
4. **Regional level:** G(t) = mean intensity of quarter t's admitted headlines (a mean, not a count, so volume does not
   enter). NaN when fewer than 5 are admitted.
5. **Feature `z_G`:** (G(t) − mean of G over t−8..t−1) / SD, the same rule as C-b's `z_N1R`
   (`prospective_lib.add_news_anomaly`: ≥ 4 past values, SD > 0), past origins only. NaN before 2017 by construction.
6. **Leakage check:** at every origin, removing every headline published on or after O(t) leaves `z_G` unchanged.

## Model

- **Exactly C-B6** (`cb6_model._origin`: C-b's procedure, grid selected on inner folds) with `z_G` added: 24 inputs.
- **Unchanged:** target 11.3% and threshold 0.50.
- **No variant** (other query, window, minimum or feature form) will be tried after seeing the results.

## Evaluation and acceptance

- **Evaluation (as C-B6):**
  - 62 verdict quarters, Leads 1–2 (1–8 for Algorithm 3);
  - all metrics and R1–R7;
  - paired Brier vs C-B6 and vs C-b;
  - the 14-test Holm family vs the 7 baselines.
- **Acceptance (all):**
  1. H8: Brier < C-B6 at both leads, one-sided p < 0.10;
  2. R1–R7 at Leads 1–2;
  3. MRLT ≥ 2;
  4. accuracy ≥ 0.75 at both leads;
  5. the leakage check passes;
  6. your approval.

**Expectation, stated in advance:** low.
- `z_G` is NaN for the 1998–2016 training rows.
- GDELT event news already failed (OLD_NEWS).
- News is about 1% of C-B6's SHAP.

**Reported whatever the result.**
PLAN-SHA256: f616407e17434aeb64ed49d572fd88bdd8f237352a18ec80535a6cc4a4f40bab

# Thesis objective assessment

**Requirement basis**
- **Chapter I §1.5.2 objectives**, as quoted in `../Lead1_Objectives_Assessment/LEAD1_OBJECTIVES_1_4_ASSESSMENT.md`.
- **The user's directive for this run:** at least 75% accuracy, LightGBM with all 12 families, useful news, and a maximum reliable lead.

Chapter I itself states no accuracy threshold. The 75% target is assessed exactly as frozen in `FINAL_PROTOCOL.md` §6.

| Objective | What it requires | Evidence from this run | Status |
|---|---|---|---|
| **1.** Two-tier NLP pipeline (XLM-R zero-shot + BERTopic) producing food-insecurity signals | A working, dated, measurable news pipeline | <ul><li>FSSI-v3 (XLM-R) is reused.</li><li>New: event de-duplication, the anticipatory/reporting split, and gap-aligned features known at the issue date (0% missing from 2022).</li><li>Reporting news tracks concurrent hunger (disaster ρ = 0.66).</li><li>No predictive value: ablation Holm p = 1; placebo p = .30–.93; the agri-supply lead did not replicate (Addendum 2).</li><li>BERTopic is descriptive only.</li></ul> | **Partially achieved.** Built and measurable; predictive value not demonstrated. |
| **2 I–IV.** LightGBM accuracy, precision/recall, F1, AUC-ROC | Meaningful metrics on a food-insecurity outcome | <ul><li>A two-class hunger label (ELEVATED) makes every metric meaningful for the first time.</li><li>All are reported at Leads 1–4 with confusion matrices.</li><li>FIL Lead 1: accuracy 0.318, F1 0.250, AUC 0.469.</li><li>Untouched FIL-LONG Lead 1: accuracy 0.504, AUC 0.509.</li></ul> | **Metrics achieved; the model's performance is poor.** The 75% target is **not achieved**. |
| **2 V.** Walk-forward expanding window to find the furthest reliable horizon | A horizon passing a pre-set rule | <ul><li>Rolling origin with issue-date cut-offs, true horizons and a leakage audit with a negative control.</li><li>No lead passes R1–R8, on either the 2021+ or the untouched 2003–2020 data.</li><li>The Bayes ceiling (0.58–0.64 at Lead 1) shows why no lead can pass.</li></ul> | **Not achieved.** The method is complete; the answer is "no reliable lead", with its cause measured. |
| **3.** Municipal rankings from validated province-level forecasts | A provincial or local food-insecurity outcome to validate against | <ul><li>SWS is regional (4 areas). No provincial or municipal hunger outcome exists in the data.</li><li>PSA food-price squeeze is available per province, but it is economic access, not hunger.</li><li>The existing FIRI v2 rankings remain unvalidated vulnerability estimates.</li></ul> | **Not achieved** as specified (data gap) |
| **4.** Compare LightGBM with naive persistence, PSA-only, NLP-only and logistic regression | All four arms on the same rows | <ul><li>All four were scored on the same rows at every lead, plus climatology, MA2 and always-ELEVATED.</li><li>Persistence is best at Lead 1 (2021+): 0.614.</li><li>LightGBM is not superior to any of the four.</li></ul> | **Achieved** (the comparison). The proposed model is not superior. |
| **5.** Dashboard, ISO/IEC 25010, DA evaluation | — | Not in this run's scope. Nothing was deployed or changed in production. | Not assessed |

## Directive criteria (the user's final acceptance list)

| Criterion | Met? | Where |
|---|---|---|
| One primary LightGBM using all 12 families | ✓ | FIL; `data/feature_map.csv`; test `test_twelve_families_all_in_the_model` |
| A food-insecurity outcome, not price-only | ✓ | SWS hunger, continuous and ELEVATED |
| SWS and PSA in documented roles | ✓ | `TARGET_AND_DATA_VALIDATION.md` §1–3 |
| News with publication-time cut-offs and measured contribution | ✓ | `NEWS_FEATURES_AND_CONTRIBUTION.md` (contribution measured: none) |
| A credible evaluation of 75% | ✓ evaluated; ✗ not reached | `LIGHTGBM_MODEL_AND_METRICS.md` §3–5 |
| Chronological testing with leakage prevention | ✓ | Rolling origin; `out/leakage_audit.json` |
| An empirically determined maximum reliable lead | ✓ determined: none | `MAXIMUM_RELIABLE_LEAD_TIME.md` |
| Performance across quarters and sharp increases | ✓ | `GENERALIZATION_AND_SURGE_EVALUATION.md` |
| A simple methodology matching the code | ✓ | `FINAL_SIMPLE_METHODOLOGY.md` |
| An honest objective assessment | ✓ | This file |

## Unmet criteria: exact cause and next action

| Unmet criterion | Exact cause | Corrective actions done | What would change the answer |
|---|---|---|---|
| 75% accuracy | <ul><li>Whether hunger rises above its recent average depends on new shocks that no available indicator predicts. This was tested on 22 years of untouched data.</li><li>SWS area samples add ±4–6 points of noise.</li><li>The Bayes ceiling is 0.58–0.64.</li></ul> | <ul><li>Stage 2 pre-registered models: FIL-H, FIL-BL, FIL-LONG.</li><li>Addendum 1: the noise-reduced anchors in FIL-LONG-S.</li></ul> | <ul><li>An outcome with predictable variation at the scale of interest, e.g. provincial or municipal FIES/CBMS food-insecurity prevalence measured repeatedly.</li><li>Or an indicator that genuinely leads hunger shocks; none was found.</li></ul> |
| Reliable lead | Same cause | Same | Same, plus prospective scoring of the seals |
| Useful news | <ul><li>Too few independent quarters (about 17).</li><li>A regional feed against area outcomes.</li><li>Reporting news is concurrent, not leading.</li><li>The corpus-specific association did not replicate.</li></ul> | <ul><li>Gap alignment, de-duplication and the anticipatory split.</li><li>A placebo test.</li><li>Replication in two GDELT sources (Addendum 2).</li></ul> | A real-time, consistently collected news archive and more outcome quarters, from prospective SWS rounds |
| Municipal validation (Objective 3) | No local outcome | — | CBMS 2024 LGU food-security aggregates (E87 request A) |

# E113 Root-cause audit: what failed in E112, what E113 did, and what is resolved

**Sources.** All numbers come from `out/results.json`, `out/analyses.json` and `out/leakage_audit.json`, produced under `PROTOCOL_E113.md` (sha `bb255afe…`, frozen 2026-10-25T10:16Z) and `ADDENDUM_1.md` (sha `24e5326b…`, written before scoring). Everything is **development evidence**: every quarter through 2026-Q3 was already seen in E109–E112.

## 1. What failed in E112, and why (summary before any E113 code)

| E112 failure | Root cause |
|---|---|
| No model beat persistence | Learned corrections (LightGBM, depth 1) were fitted on 8–17 Balance Luzon pairs. Nothing forced them to stay near the latest reading when evidence was weak. |
| Leads 2–4 "insufficient evidence" | The design used Balance Luzon only, so 5–7 evaluable quarters. Three SWS areas were left unused. |
| Worse after 2025 and when hunger falls | No model of the 2025 respondent-base change; models carried the 2024 surge forward. |
| News measurable, no forecast gain | Six correlated year-over-year shares were fed in raw: no composites, no lag choice, no severity. Price news did not track concurrent inflation. |
| No provincial or municipal forecast | No local food-insecurity outcome exists |
| No unseen confirmation | All 2021–2026 quarters had been examined |

## 2. Hypotheses tested, and how each could fail

| # | Hypothesis | Falsified if | Result |
|---|---|---|---|
| H1 | Pooling the 4 SWS areas adds enough power to show skill | No SH candidate passes R2 at any lead | **Falsified.** Every SH candidate has Holm p = 1.0 at every lead. |
| H2 | Shrinking toward persistence avoids the E112 losses | The SH candidates are still worse than RW | **Mostly falsified.** The best SH variant is within about 4% of RW's MASE at Leads 1–4. It is below RW only at Leads 2 and 4 (SH-N: 1.39 vs 1.44; 1.67 vs 1.71), never significantly, and never at Lead 1. Mean-reversion variants are much worse at long leads (SH-MR Lead 4: MASE 3.11 vs 1.71). |
| H3 | Regime anchoring fixes the post-2025 failure | Post-break losses vs RW stay positive | **Partly falsified.** SH-MR is slightly better than RW post-break at Leads 1–2 (−0.05, −0.01 scaled), but much worse at Leads 3–5. |
| H4 | News composites add skill | News-ablation family has Holm p ≥ .10 | **Falsified.** All 18 tests have Holm p = 1.0. The shuffled-news placebo is as good as real news (permutation p = .63). |
| H5 | GDELT replicates the agri-supply signal out of sample | REP-G BL Holm p ≥ .10 | **Falsified.** Lead 1 raw p = .16, Holm .65. |
| H6 | Lagged CPI improves hunger forecasts | CPI family has Holm p ≥ .10 | **Falsified.** All 18 tests have Holm p = 1.0. The shuffled-CPI placebo is better than real CPI (p = .97). |
| H7 | Price news tracks CPI | No lag-0 or news-leading ρ > 0 with Holm p < .10 | **Supported, narrowly.** GDELT price-news direction leads the change in food inflation by two quarters (ρ = 0.70, Holm p = .016). The corpus shows the same direction (ρ = 0.47, raw p = .028, Holm .54). Concurrent levels are negative. |
| H8 | Persistence errors are larger in high-inflation quarters | Mann–Whitney shows no difference | **Not supported.** Lead 1: high 0.96 vs other 1.31 (p = .50). |
| H9 | There are enough surges to test alert skill | Fewer than 10 events, or no alerts | **Insufficient.** 9 events at Lead 1. SH models raised one correct alert in total at Leads 1–3 (SH-P, Lead 1). The best alert record is SH-MRN at Lead 4: 4 hits of 10 events, precision .80, recall .40. No alert-skill claim is supported. |

## 3. Workstreams

| Workstream | What was done | Finding | Status |
|---|---|---|---|
| **A. Small sample** | 4-area pooled panel; expanding-window rolling origin from the first eligible origin (2022-Q4); low-variance ridge shrinkage only; Lead 1 evaluated on 14 quarters / 56 rows (E112: 9) | More evaluable quarters at every lead (12 / 11 / 9 / 7 / 6 at Leads 2–6), but no skill appears. Pre-2021 SWS history was **not used**: the study-window rule is binding (flag for the adviser). No other validated quarterly outcome exists in the repository. | **Partly resolved** (more power, still too little) |
| **B. 2025 survey change** | Regime-specific anchor (post-break mean once ≥ 2 post-break readings exist); S-PRE sensitivity (pre-break targets only); per-regime losses | No bridging round exists, so the level shift cannot be estimated separately from a real rise. Anchoring helps only marginally at Leads 1–2. | **Partly resolved.** The assumption needs adviser approval. |
| **C. Beat persistence** | Six shrinkage-to-persistence variants; baselines MA2, damped trend, AR(1), ETS (local level), linear regression, PSA-only, NLP-only; DM with HLN and Newey–West; Model Confidence Set | No SH candidate beats RW. The MCS keeps nearly every model at Leads 1–5 (the data cannot separate them). The **ETS baseline** has the lowest MASE at Leads 2–3 (1.26 vs 1.44, raw p = .062; 1.41 vs 1.55, p = .13), consistent with E111's LLR. As a pre-registered baseline it is not eligible for adoption. | **Not resolved** (persistence unbeaten) |
| **D. News** | Four interpretable composites (disaster with severity weighting, supply shock, price, assistance); in-fold lag choice (0 or 1); news-only, ablation, per-area, per-regime; GDELT replication; shuffle placebo | Composites are dense (0% missing at evaluation origins). Severity weighting does not improve the typhoon validity (ρ 0.80 vs 0.81). No forecast gain at any lead, area or regime. The Lead-4 news ablation has raw p = .066 but Holm p = 1. | **Not resolvable with these data.** News is measurable, but does not help forecasts. |
| **E. CPI** | PSA OpenStat monthly food and headline CPI (Calabarzon) already in the repository; day-10 release rule; three roles | See `E113_CPI_VALIDATION.md`: price news partly validated (leading); CPI adds no forecast skill; no high-inflation error regime | **Resolved as an analysis.** National and rice CPI are not in the repository (no-new-data rule). |
| **F. Surges** | Surge = rise beyond the two readings' combined sampling noise (1.96·√(R₁+R₂)); Brier vs climatology and RW; precision and recall | 9 events at Lead 1, 9 at Lead 2. No candidate meets the alert-claim rule. | **Not resolvable** (too few events) |
| **G. Spatial** | Checked for provincial or LGU outcomes; consistency check of provincial vulnerability V1 against PSA subsistence incidence | No food-insecurity outcome below the region. V1 vs subsistence: ρ = 0.74 (2021), −0.56 (2023), n = 5, CVs 17–53%. Inconsistent. | **Not resolvable without CBMS / FNRI provincial data** |
| **H. Maximum lead** | Pre-registered R1–R4, Holm within lead, fixed-sequence across leads | No candidate reliable at any lead | **Answered: none established** |
| **I. Uncertainty** | Conformal-style 80% bands from earlier out-of-sample errors; coverage per lead | RW coverage: 0.75 (L1), 0.67 (L2), 0.73 (L3), 0.69 (L4), 0.54 (L5), 0.58 (L6). Calibrated at Lead 1 only. For Balance Luzon alone, the pooled band over-covers (0.93 at Lead 1), because BL errors are smaller than MIN/VIS errors. | **Resolved for Lead 1**; under-covers beyond Lead 3 |

## 4. Leakage audit (`out/leakage_audit.json`)

- **Future-data test.** At 5 origins, 560 forecasts were recomputed with everything published on or after the issue date replaced by extreme values (SWS +40, future news randomised, unreleased CPI +50, future rice +50). Maximum change: **0.0**. Passed.
- **Negative control.** Changing *available* data (the latest reading, quarter-t news, the latest released CPI month) changes the forecasts (`test_negative_control_available_data_changes_forecasts`), so the test has teeth.
- **Shuffle placebos.** Real news is no better than 200 shuffled versions (permutation p = .63). Real CPI and rice are worse than shuffled versions (p = .97). Neither carries a real or a spurious (leaked) signal.
- **In-fold fitting.**
  - Ridge α, news lag, damping φ, AR ρ and state-space Q are all fitted on training pairs whose targets were published before the issue date (tested).
  - Feature scales are training RMS.
  - The surge threshold uses published survey margins, not outcomes.

## 5. Remaining unresolved items and the exact data needed

1. **Unseen outcomes:** SWS rounds from 2026-Q4 onward, to score seals A and B. About 8 quarters are needed before a Lead-1 claim can reach significance.
2. **Longer history:** a pre-2021 SWS back series would add about 40 quarters per area. It is excluded by the study-window rule; the adviser must decide.
3. **Local outcomes:**
   - CBMS 2024 LGU food-security aggregates (Objective 3);
   - DOST-FNRI provincial FIES (ENNS / NNS).
4. **Bridging data:** an SWS round fielded under both respondent bases, or SWS's own adjustment factor, to separate the 2025 design shift from real change.
5. **Price data:** the national and rice/cereals CPI sub-indices, with PSA's actual release dates, to replace the Calabarzon proxy for the other areas.

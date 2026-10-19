# Objective compliance matrix after E64 (statuses: Met / Partially Met / Not Met)

**Source:** Chapter I of `THESIS 2 (11).pdf`, §1.5 (verbatim objectives are in E62 `OBJECTIVE_COMPLIANCE_MATRIX.md`).

**Rule applied:** an objective counts as Met only when the required result exists **and** was verified. Code that exists is not enough.

| Objective | What E64 added or verified | Evidence | Status |
|---|---|---|---|
| **General: develop** | e64 path end to end: news pipeline v3 → model → record → API → approved dashboard | 447 backend tests pass (18 skipped); 46 frontend tests; production build (see report §7) | **Met** |
| **General: validate** | No independent provincial food-insecurity outcome. Only development back-tests (50 rows, all seen before). The prospective 2027-Q1 seal awaits outcomes. | report §5, §9 | **Not Met** |
| **General: deploy** | e64 and E58 run locally behind a flag. **The production default is still E38. Nothing was deployed.** The deployed configuration was not verified (no URL available). | — | **Partially Met** |
| **1. Two-tier NLP pipeline → bias-corrected FSSI and latent risk patterns per province-quarter** | **Tier 1, met:** XLM-RoBERTa-large-XNLI zero-shot intensity on admitted articles (225 new scores; stored scores reproduce exactly). **Bias-corrected FSSI-v3, met:** Equation 2 on classifier-v2 admitted articles, never zero-filled, n/status/value consistent, article keys per cell. **Tier 2, weak:** BERTopic rebuilt (152 topics, 40% outliers), but its topics are mostly place names. **In use:** integrated into the served e64 path. | `r1_fssi_audit.json`, `r1_fssi_v3_panel.csv`, `data/news_v3/topic_*`, `test_e64_news_pipeline.py` | **Partially Met.** Built, integrated and traceable. Limits: titles only and retrospective; relevance validated on AI annotations only (not human-verified); BERTopic patterns weakly food-specific; FSSI-v3 is not associated with price pressure or hunger (ρ ≈ 0.07–0.10). |
| **2 I–IV. Accuracy, precision/recall, F1, AUC** | Reported for every candidate and baseline at Lead-2 on 50 rows, by province and quarter, with quarter-cluster CIs, confusion matrices and calibration | `c2_score.json`, `c2_*` tables | **Met** (development evidence) |
| **2 V. Multiple lead times → furthest reliable horizon** | E63 (separate session, its own branch): leads 1–3 evaluated, lead 4 not computable. **No lead meets the pre-registered reliability rule.** Skill falls with lead (Brier 0.13 / 0.21 / 0.25). | E63 `FINAL_REPORT.md` | **Partially Met.** The evaluation was done; the result is "no reliable horizon established". "Reliable" is defined by the study, not by Chapter I. |
| **3. Municipal and city rankings from validated province forecasts, weighted by PSA poverty and density** | 142/142 LGUs; identity checks pass; reproducible hash; formula replicated exactly; each row traceable to its province estimate and run; weight sensitivity done; no municipal outcome exists | `r3_lgu_audit.json`, `test_e64_record.py` | **Partially Met.** Rankings are complete and traceable, but "from **validated** province forecasts" is not satisfied. 4-dp rank ties (W-E64-1) need a decision. |
| **4. Comparison with persistence, PSA-only, NLP-only, LR** | E64: government-only (A), news-only (B), government + original news (C), government + improved news (D, E), persistence, majority, climatology, on the same 50 rows | `c2_model_comparison_50rows.csv` | **Partially Met.** All comparisons were done. D's advantage over every baseline is not statistically supported (quarter sign tests p ≥ 0.11). |
| **5. Public dashboard, maps, alerts; ISO/IEC 25010; FNRI face validity** | Dashboard verified locally in e64 mode (live preview); no ISO 25010 data; no FNRI provincial anchor | browser check; E62 matrix | **Partially Met** |

## Hypotheses (§1.4) after E64

| Hypothesis | Status |
|---|---|
| H1 | FSSI is now an input (FSSI-v3). It ranks below the national employment and OFW news signals and below the CPI terms (65 splits over 12 origins). Food-CPI terms dominate, so H1 is **rejected for CPI** and **not rejected for FSSI**. |
| H2 | **Not rejected:** no lead is reliable under the rule (E63). |
| H3 | **Not rejected** at the quarter level. The combined model's advantage over the single-source variants and baselines is not statistically supported on 10 quarters. |
| H4, H5 | **Pending** the DA IV-A post-survey. |

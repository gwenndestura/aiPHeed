# aiPHeed: food-insecurity dimensional framework and validation protocol

**Date:** 2026-10-20 · **Branch:** `final-aipheed-thesis-e72` · **Companion documents:**
- `FOOD_INSECURITY_DIMENSIONAL_FRAMEWORK_AND_REDESIGN.md`: E71 conceptual detail and references.
- `aipheed-backend-aligned/experiments/E73_Objective_Remediation/PROTOCOL.md`: frozen E73 rules (sha `b6930a9a…`).

This document fixes how aiPHeed's food-insecurity risk estimates are validated:
- what has been validated now (§3, §4);
- what can only be validated later, and the complete procedure for doing so (§5–§8).

Rules and thresholds were written before the corresponding results were computed. Each section says when.

---

## 1. Framework (summary)

- **Definition.** Food security means that all people, at all times, have physical and economic access to sufficient, safe and nutritious food (World Food Summit, FAO 1996).
- **Dimensions** (FAO 2006):
  - **availability** (production, fisheries, supply);
  - **access** (affordability, income, jobs, household support);
  - **utilization** (diet, nutrition, water, sanitation, health);
  - **stability** (continuity under shocks).
- **Cross-cutting factors:** vulnerability, exposure and coping capacity.
- **Contributing factors vs outcomes.** Following IPC 3.1 and WFP CARI, contributing-factor evidence (dimensions, hazards, vulnerability) is kept apart from outcome evidence (experienced hunger, FIES, consumption, nutrition). A risk index made of contributing factors is never validated by agreement with itself or with its own inputs.

**How aiPHeed applies it.** Each FIRI v2 indicator has one role (`app/ml/inference/dimensions.py`):

| Role | FIRI v2 indicators |
|---|---|
| ACCESS | A1–A3, E1, E2 |
| AVAILABILITY | C3, C4 |
| STABILITY | C1, C2 |
| UTILIZATION | none (**not observed**) |
| VULNERABILITY | V1 |
| OUTCOME evidence (regional) | H1 |
| SIGNAL | N1 |

Every served estimate is split exactly along these roles in the API (`riskOutlook.dimensions`), the explanation text and the PDF.

## 2. Dimension-to-evidence matrix

The full matrix is in the redesign document §2: source, level, coverage, delay, type, Lead-2 role, limitations and validation needed. Additions from E73:

| Evidence | Level, coverage | Type | E73 finding |
|---|---|---|---|
| **OCTA Research *Tugon ng Masa* involuntary hunger, Balance Luzon** | Regional (Luzon outside NCR); 8 verified quarters, 2023-Q4 … 2026-Q3; n ≈ 300 per area, ±6 pts | **Direct outcome**, independent of SWS and of every aiPHeed input | New independent validation outcome (§3) |
| News trigger counts (v3 corpus) | Province-quarter, 2021–2026; 695 admitted headlines, 7 Filipino | Signal | Validated only for climate (§4) |

## 3. Evidence hierarchy: what is validated now

| Level | What | Status (E73, 2026-10-20) |
|---|---|---|
| **A. Direct outcome** | SWS Balance Luzon hunger (regional) | FIRI v2 Lead-2 class 16/17 (0.94). **Not independent:** SWS is one of FIRI's inputs (H1) and its weights were fitted to SWS. |
| **A. Direct outcome, independent** | OCTA Balance Luzon hunger (8 quarters; "elevated" > 11%, the median of the first four rounds, a rule frozen before the values were read) | **FIRI v2: 4/8 (0.50, balanced 0.60).** Rank correlation of the regional FIRI level with OCTA 0.73, 95% CI [−0.20, 1.00]. FIRI without H1: 2/8 and ρ 0.06. Latest SWS reading: 6/8. Always-elevated: 3/8. **The 80% Lead-2 criterion is not supported.** |
| **A. Direct outcome, provincial** | FNRI NNS 2023 provincial FIES; CBMS LGU FIES | **Not obtained.** The E13/E26 inventories found no public provincial/LGU series. E73 searches found only regional or national values. |
| **B. Dimension validation** | News triggers against official records (E73 §1a) | Climate news vs PAGASA typhoons: ρ 0.35 [0.06, 0.60], **pass**. Market news vs PSA food CPI: ρ −0.26 (a corpus-growth time artifact; within a quarter ≈ 0), **fail**. Fish-kill vs fisheries production, employment vs LFS, remittance vs BSP: no relation, **fail**. |
| **B. Dimension validation** | E71: outcome-free FIR71 index vs SWS | ρ −0.21 [−0.68, +0.35], **not supported** |
| **C. Construct / known groups** | E71 V4 synthetic scenarios (labelled synthetic) | Distinguishes all six brief situations (unit tests). Synthetic scenarios show internal logic only, never external validity. |
| **C. Construct** | Concurrent SWS vs OCTA (two hunger surveys) | ρ 0.71 [−0.22, 0.99] over 8 quarters. The surveys broadly agree, with sampling noise (±6 pts per area). |
| **D. Prospective** | 11 sealed forecast sets (E68, E69, FIRI v2, E70 ×4, E71 ×4) for 2026-Q4 / 2027-Q1 | Hashes verified (`E73/prospective/SEAL_REGISTER.json`); no outcome published yet |
| **E. Expert / operational** | DA evaluators and food-security experts | Instrument ready (§7). Not yet conducted. |

**Conclusion.**
- The served index's ordering of regional hunger over time comes from its observed-hunger input.
- The provincial contributing factors do not track either hunger survey.
- There is no measured provincial outcome to test provincial differences against.

## 4. Objective 1 validation results (E73 WS1)

| Check | Result |
|---|---|
| Relevance and trigger: human reference | **Pending human labels.** 300 blind headlines with two annotator files, weighted precision/recall/F1, Cohen's κ, consensus reference and per-stratum agreement (incl. Filipino) are implemented and tested on synthetic labels. |
| Trigger criterion validity vs official records | Climate passes. Market, fish kill, employment and remittance fail (above). |
| FSSI bias correction | Not validated: Δρ vs uncorrected +0.08 [−0.06, +0.20]. The empirical-Bayes alternative is not better, so the served formula is unchanged. The weight ranges 0.28–3.70. |
| Volume artifact | ρ(FSSI, n) = 0.18; ρ(bias weight, n) = −0.50. The weight works as designed and does not create a strong count artifact. |
| Coverage | 20 of 115 province-quarters SUFFICIENT. Rizal has 0 articles in 17 quarters. 399 of 695 headlines are national. 7 Filipino. 23 outlets. |
| Temporal availability | Every article is counted by publication date before the issue date (`pipeline_v3.asof`). Collection is retrospective: 687/695 were first seen after their issue date. |
| Regional news value | RW + news vs RW for SWS hunger at Lead 2: MAE 6.06 vs 6.25; 4 quarters better, 4 worse; **no value.** |
| Forecast value (E70/E71 ablations) | Removing news: Δ Brier −0.002 / +0.002, **no measurable value** |

## 5. Prospective validation procedure (implemented: `E73/runner/e73_prospective.py`)

1. **Seal before the outcome exists.** Write the forecast file and its sha256, then commit. The register records the commit time as `sealed_at`.
2. **Never edit a sealed file.** `register` verifies every hash and refuses to score a mismatched seal.
3. **Collect outcomes** into `OUTCOMES.csv` (schema in §8) with each value's published date and source URL, without opening anything before its scoring date.
4. **Score** with `e73_prospective.py score OUTCOMES.csv`. A seal is scored only on outcomes published after `sealed_at`, for its own target quarter, with these rules (fixed 2026-10-20):

| Seal | Rule |
|---|---|
| T43 seals | Province HIGH = SWS > 11.3 AND (food YoY > P60 OR gap > P60) |
| FIRI v2 | Regional mean ≥ 0.5 vs SWS > 11.3 and OCTA > 11 |
| E69 | Regional ELEVATED vs SWS > 11.3 |
| E71 | Province class vs the FIR71 rule |

5. **Accumulate** quarters. A Lead-2 accuracy claim needs about 20 or more unseen quarters (a Wilson half-width of about ±0.15 at p ≈ 0.8).

## 6. Prospective quarterly household FIES survey: the outcome aiPHeed needs

**Implemented:** `E73/runner/e73_fies_survey.py` and `E73/survey/FIES_SURVEY_TEMPLATE.csv`. **Not yet conducted.**

| Element | Specification |
|---|---|
| Instrument | The eight FAO FIES items (WORRIED, HEALTHY, FEWFOOD, SKIPPED, ATELESS, RANOUT, HUNGRY, WHLDAY), 3-month recall, yes/no, don't-know/refused = missing; Filipino and English versions back-translated |
| Population | Households in each of the five provinces (Lucena reported with Quezon or separately, as decided before fieldwork) |
| Sampling | Two-stage: barangays with probability proportional to size within each province, then systematic household selection; fresh sample every quarter (or a rotating panel, fixed in advance) |
| Sample size | **904 households per province per quarter**: ±5 points at 95%, design effect 2.0, 85% response, p = 0.5 (`sample_size()`); ≈ 4,520 per quarter for the region |
| Schedule | Fieldwork in the second month of each quarter, so the outcome falls in the forecast's target quarter |
| Scoring | Operational: raw score ≥ 4 = moderate or severe, ≥ 7 = severe. **Official estimate: FAO Rasch model with equating to the FIES global standard** (RM.weights / FIES app). The raw-score version is labelled as monitoring only. |
| Estimates | Weighted provincial prevalence with a design-adjusted 95% CI (`estimate()`); replace the Kish × assumed clustering effect with the design-based variance once the design is fixed |
| Outcome class (fixed now) | **HIGH (deteriorated)** iff prevalence exceeds the province's baseline (mean of its first two rounds) by ≥ 5 points AND the 90% lower bound of the difference is > 0. The first two rounds have no class. |
| Operating characteristics (synthetic test) | Detects a real deterioration in 18/20 synthetic replicates; flags a flat province in 0/20 |
| Join to forecasts | `join_forecasts()`: sealed province forecasts vs the survey class, scored only for rounds fielded after the seal |
| Required resources and permissions | Researcher, adviser and ethics approval. DA or LGU partnership, or a PSA/FNRI data agreement. Enumerators and training. About 4,500 interviews per quarter. Informed consent. No personal identifiers in the analysis file. |

**Lower-cost alternative.** Obtain CBMS 2022/2024 FIES aggregates for the 142 LGUs (LGUs or PSA RSSO IV-A; E26 `MISSING_OBSERVATIONS_SPEC.md`). It is a cross-section that would validate the Objective 3 prioritization, not the quarterly forecast.

## 7. Expert and DA-evaluator review (implemented: `E73/runner/e73_expert_review.py`, `E73/expert_review/EXPERT_REVIEW_FORM.csv`)

**Form: 23 items in three types.**
- 12 indicator-relevance items: does each FIRI v2 indicator measure its stated dimension or role? Rated 1–4.
- 6 explanation-clarity items, rated 1–4.
- 5 province-quarter plausibility items: agree / disagree / unsure.

**Scoring:**
- I-CVI (share rating 3–4; acceptable ≥ 0.78 with 6 or more reviewers; Polit and Beck 2006);
- S-CVI/Ave;
- Fleiss' κ for plausibility.

**Reviewers:** the 50 DA Region IV-A respondents planned for Objective 5, plus at least 2 food-security specialists.

This is judgement and usefulness evidence. It is **not** predictive validation.

## 8. Outcome file schema (`OUTCOMES.csv`)

| Column | Meaning |
|---|---|
| `quarter` | Target quarter, YYYY-Qn (fieldwork quarter for surveys) |
| `kind` | `SWS_H`, `OCTA_BL` (regional, % families); `CPI_FOOD_YOY`, `CPI_ALL_YOY` (province, mean of 3 published months); `FIR71_HIGH` (province, 0/1); `FIES_HIGH` (province, 0/1 from §6) |
| `province_code` | PSGC province code; blank for regional values |
| `value` | Number as published |
| `published` | Publication date (YYYY-MM-DD) |
| `source_url` | Primary source or reputable report quoting it |

## 9. What cannot be claimed until these steps are done

1. **Validated provincial or municipal food-insecurity accuracy:** requires §6 or CBMS.
2. **Lead-2 accuracy on unseen quarters:** requires §5 over about 20 quarters.
3. **Human-validated relevance, trigger and attribution:** requires the 300-headline labels.
4. **DA/expert acceptance:** requires §7.

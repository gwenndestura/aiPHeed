# v9 Stage 1: Spec reconciliation

**Basis:** Chapter I only (`THESIS_SPEC.md`). **All numbers here are DEVELOPMENT.** Tags: VERIFIED (command + saved output), INFERRED, NOT VERIFIED.

## Reasoning record

**Question.** Does the existing backend satisfy Chapter I, and what does its label really measure?

| Competing hypothesis | Discriminating test | Result |
|---|---|---|
| H1: the system forecasts hunger | Skill on L-SWS, with and without CPI predictors | Rejected at this strength: the only high AUC (0.719) is a base-rate artefact (§c) |
| H2: the system forecasts only price pressure | Skill on L-CPI, and the loss when CPI predictors are removed | Rejected: L-CPI AUC is 0.462 at Lead 1 and 0.251 at Lead 2 |
| H3: no usable signal at these leads on these labels | Every model against always-HIGH and persistence | **Supported**: nothing beats always-HIGH on accuracy; all AUC CIs include 0.5 or lie below it |

**Pre-mortem ("2029, the sealed test failed"), checked now:**

| # | Likely cause | Status now |
|---|---|---|
| 1 | Label saturated, so almost no LOW rows | **Already true** (§e) |
| 2 | Regime shift between training and test | **Already true**: L-COMP 8.6 % HIGH before 2024, 78 % after |
| 3 | Too few independent target quarters | **Already true**: 10 at Lead 2, each one SWS value |
| 4 | News too sparse | **Already true**: 68 of 115 cells have no relevant article (v10 audit) |
| 5 | Retrospective corpus does not behave like live collection | Open: entire corpus harvested 14–19 Oct 2026 |
| 6 | CPI publication timing assumed, not observed | Open: lock C4 rule; 30 of 34 dates provisional (E122) |
| 7 | SWS respondent base changed in 2025-Q2 | Open: recorded in `sws_area_rounds.csv` |
| 8 | Provincial differences are mostly noise | Open: within-quarter share of stress variance 29 % |
| 9 | Silent feature contamination | Checked: `as_of` on SWS; shared-tree mutation incident re-run clean (below) |
| 10 | Multiplicity across E1–E136 and v2–v9 | Open: the v9 ledger counts v9 only; earlier trials are disclosed, not deflated |

**Red team.** The L-SWS AUC of 0.719 looked like success. Inspection of `stage1_predictions.csv` shows the model produced no fit at 7 of 10 quarters at Lead 2 (6 at Lead 1), so "predictions" there are the expanding training base rate, which rises over time as HIGH rows arrive, and only 2 of the 10 quarters are LOW. F-ALL and F-NOCPI give the same AUC. This is time drift against a shared quarterly label, not skill. (VERIFIED, `stage1_predictions.csv`; the reading is INFERRED.)

**Independent re-implementation.** AUC recomputed by hand-written pairwise comparison on `stage1_predictions.csv` equals scikit-learn in all 12 cells (VERIFIED, session command).

**Shared-worktree incident.** Another session ran mutation checks that temporarily planted bugs in `as_of.py`, `v6/select.py`, `v4/features.py` and `v6/lgbm.py` (about 12:07–12:10:45 on 2026-11-02). Stage 1 was re-run at 12:15 after they were restored, with a new assert on the LightGBM parameters. The output is byte-identical to the first run (`cmp`, VERIFIED). The assert does not change the pre-registered procedure. Logged here as a process deviation.

## Reconciliation table

Gap class: **F** FIXABLE-IN-BACKEND, **A** NEEDS-ADVISER, **D** NEEDS-DATA.

| Objective | Requirement | Existing component | Gap | Class | Acceptance test |
|---|---|---|---|---|---|
| O1 | XLM-R zero-shot Filipino-English extraction | `app/ml/nlp/classifier.py`, `joeddav/xlm-roberta-large-xnli` | Titles only; 0.8 % of titles carry ≥ 2 Tagalog tokens; Tagalog not among the 15 fine-tuning languages; no human labels | D | Human sample scored: P, R, F1, kappa |
| O1 | BERTopic latent patterns per province-quarter | `app/ml/nlp/topic_model.py`, `scripts/fit_topics_v3.py` | Fitted on all years (correctly marked descriptive); seed ARI 0.62–0.66; past-only vs full ARI 0.21 | F | Per-origin refit; guard test fails an all-years fit |
| O1 | Bias-corrected FSSI | `app/ml/corpus/bias_weighter.py`, `fssi_builder.py` | Formula exact and within-quarter (no future), but a single-article cell can get weight up to 2.81 | F/D | Coverage control in the model; cell status disclosed |
| O2 | Accuracy, P, R, F1, AUC on binary province risk | v2–v6 report numeric metrics | Thesis metrics not primary; no adopted label | **A**, then F | Metric table per lead with CIs and always-HIGH/LOW |
| O2 | Walk-forward furthest reliable horizon | Frozen N1–N7 (numeric) | No classification rule adopted | **A** | Pre-registered mechanical rule evaluated for Leads 1–4 |
| O3 | LGU rankings from **validated** forecasts with poverty and density weights | `app/ml/inference/disaggregator.py` (142 LGUs) | No validated forecast exists, so rankings are conditional; 0.6/0.4 split traces to a stale guide | **A**, F | Bootstrap rank intervals; labelled ORDINAL, INDICATIVE, MODELED |
| O4 | Against persistence, PSA-only, NLP-only, logistic | v6 8-baseline Holm rule (numeric, different set) | The 4 named baselines are not all implemented on a binary label | F | Paired block-bootstrap with Holm |
| O5 | Public dashboard and alerts | Frontend, `/api/v1` | Frontend out of scope (no design changes) | — | API contract tests |
| O5 | ISO/IEC 25010 with DA evaluators | None in backend | Instruments and automated measurements absent; **no responses may be fabricated** | F, then human | Questionnaire plus scoring sheet; responses from people only |
| O5 | Face validity vs NNS 2019 and 2023 CALABARZON | `enns_fetcher.py` holds only NNS 2025 from press | **2019 and 2023 CALABARZON figures not obtained** (primary PDFs carry them as images or not at all) | D | Values read from FNRI tables, then compared as an anchor only |

## Conflicts inside Chapter I (owner or adviser to resolve)

| # | Conflict | Evidence | Class |
|---|---|---|---|
| 1 | The Introduction says 44 % of households were moderately to severely food insecure **in 2023**. FNRI's own trend chart shows **44.2 % for 2019, 33.4 % for 2021 and 31.4 % for 2023**. | VERIFIED: FNRI 2024 National Nutrition Summit Part 1 (see `AGENCY_METHODS.md`). This looks like a year mix-up (INFERRED). | A |
| 2 | RQ3 and H3 name **six** baselines; Objective 4 names **four**. | Chapter I §1.3, §1.4, §1.5.2. Standing owner rule: use the four of Objective 4. | Resolved by rule; flag to adviser |
| 3 | RQ5 mentions **DEPDev** evaluators; Scope and H5 say DA only. | Standing owner rule: 50 DA respondents only. | Resolved; thesis text should change |
| 4 | Scope says news from **2020**; the owner's hard rule is **2021+**. | Memory rule, lock W1. | Resolved; thesis text should change |
| 5 | O5 says "public" dashboard; §1.6 says "secure" dashboard. | Chapter I. | A |
| 6 | H4 tests rankings against DA evaluators' assessments, but O3 has no LGU ground truth. | Chapter I. A survey can show perceived plausibility, not accuracy. | A |
| 7 | The stated "derives a validated forecast target from CPI" is not yet supported by any validation. | §1.1 against this audit. | A |

## (a) Metrics: thesis versus earlier work

**Resolved in design:** thesis binary metrics become **primary** for v9; numeric score and within-tolerance stay as a **secondary track**. Frozen results (lock T1–R2, v2, v4, v6) are always reported alongside and are not changed. **Lead:** thesis asks for the furthest reliable horizon found empirically, so Leads 1–4 are evaluated; fixed Lead 2 stays only as a frozen-protocol result.

## (b) How each province-quarter label is actually made (VERIFIED by reading code and running it)

There are **three different things** called the thesis label:

| Artefact | Actual rule | Problem |
|---|---|---|
| `label_generator._build_stress_labels` | SWS + 2 × (food YoY − provincial mean YoY); HIGH above the **whole-period median** | Not anchored to SDG 2.1.2; median forces 50/50 and uses future rows; guarded as legacy (`label_guard`); `alpha = 2` has no cited source |
| `data/thesis/panel.parquet` `label_stress` | **The CPI-only rule renamed** (`build_thesis_panel.py` renames `label_cpi` to `label_stress`): 135 of 135 rows equal the CPI rule | **The column name says composite; the content is CPI-only.** 94.5 % HIGH from 2024. Rolling base includes 2020 |
| Thesis text | Composite "anchored to the FAO SDG 2.1.2 baseline established by the DOST-FNRI ENNS" | **No code implements any FIES anchor.** `label_generator` states FIES is "NOT used in label generation" |

**Audit finding:** the thesis's composite label, as written, has never been implemented. The FIES anchor cannot be applied arithmetically, because FIES is a Rasch-scaled 12-month prevalence and SWS hunger is a 3-month single-item share (INFERRED from `AGENCY_METHODS.md`).

## (c) Label circularity (DEVELOPMENT; protocol hash `eb305b63…`, `results/stage1_*`)

**Mechanical facts (no fitting, VERIFIED `stage1_mechanical.json`):**

- **71 %** of stress variance is between quarters, which is the SWS part shared by all provinces; 29 % is within-quarter CPI deviation. The quarterly mean of stress **equals** SWS exactly.
- L-CPI is structurally tied to its own predictor: P(HIGH | previous flag = 0) = **0.00** by construction; P(HIGH | previous flag = 1) = **0.94**. **However, a real forecast cannot see that flag:** at issue the latest complete CPI quarter is D − 2, so the previous flag is known only for targets at D − 1. At Lead 1 (target D) and beyond, the mechanical tie is not directly available.
- L-SWS and L-CPI barely agree: 53 % agreement, phi **0.13**. **They measure different things**, so a composite blends two weakly related signals.
- L-COMP agrees with L-SWS 84 % and with L-CPI 58 %: the composite is mostly SWS.

**Model skill (target quarters 2024-Q1…2026-Q3, n = 50 rows, 10 quarters):**

| Lead | Label | Base rate | Always-HIGH acc | Persist acc / AUC | F-ALL acc / bal.acc / AUC [95 % CI] | F-NOCPI acc / bal.acc / AUC | AUC diff (ALL − NOCPI) [95 % CI] |
|---|---|---|---|---|---|---|---|
| 1 | Composite | 0.78 | 0.78 | 0.66 / 0.586 | 0.34 / 0.577 / 0.577 [0.338, 0.676] | 0.40 / 0.550 / 0.576 | [−0.138, 0.167] |
| 1 | SWS only | 0.80 | 0.80 | 0.60 / 0.562 | 0.60 / 0.750 / 0.719 [0.071, 0.906] | 0.60 / 0.750 / 0.719 | [0.000, 0.000] |
| 1 | CPI only | 0.86 | 0.86 | 0.76 / 0.502 | 0.84 / 0.488 / 0.462 [0.375, 0.780] | 0.86 / 0.500 / 0.312 | [0.117, 0.256] |
| 2 | Composite | 0.78 | 0.78 | 0.58 / 0.600 | 0.30 / 0.551 / 0.610 [0.406, 0.736] | 0.34 / 0.544 / 0.605 | [−0.063, 0.020] |
| 2 | SWS only | 0.80 | 0.80 | 0.50 / 0.500 | 0.24 / 0.525 / 0.719 [0.125, 1.000] | 0.24 / 0.525 / 0.719 | [0.000, 0.000] |
| 2 | CPI only | 0.86 | 0.86 | 0.76 / 0.502 | 0.86 / 0.500 / 0.251 [0.000, 0.480] | 0.86 / 0.500 / 0.198 | [−0.003, 0.239] |

**Reading under the rule fixed in advance:** the "price pressure, not hunger" condition is **not met**, because L-CPI skill does not exceed L-SWS skill. The CPI-predictor gain at Lead 1 on L-CPI ([0.117, 0.256]) only moves AUC from well below chance up to about chance. **Development reading: no usable signal on any of the three labels (decision tree 2, not tree 1).** The CIs are wide because there are only 10 effective quarters, so this also cannot prove the signal is absent.

## (d) Measured versus inherited province variation (VERIFIED)

| Component | Province-to-province | Status |
|---|---|---|
| SWS hunger | None. One Balance Luzon value (7 regions) copied to 5 provinces | **Inherited**; each quarter is one measurement, not five |
| Food CPI | Yes (PSA provincial index) | **Measured** (price, not hunger) |
| Unemployment | **None in any quarter** (national, `unemployment_quarters_with_provincial_variation = 0`) | **Inherited**, and from national, not regional |
| FSSI, triggers | Yes, but 68 of 115 cells have no relevant article | Measured, very sparse |
| Poverty incidence | Triennial, CV up to 62 % (v6) | Measured, imprecise; not quarterly |

**Consequence:** the 50 evaluation rows of L-SWS are 10 independent observations. Every CI above is bootstrapped by quarter for this reason.

## (e) HIGH-RISK rule

The rule must come from a documented source and be fixed before scoring. **This is the owner's and adviser's decision; nothing is adopted here.** Descriptive base rates only, no model used:

| Option | Rule | Documented in | HIGH before 2024 | HIGH from 2024 | Consequence |
|---|---|---|---|---|---|
| A | stress > mean SWS Balance Luzon in calendar 2023 (11.15 %), the NNS 2023 survey year | Thesis wording ("anchored to the ... baseline"); the mapping to SWS is a proposal | 51 % | **98 %** | Faithful to the thesis wording, but nearly always HIGH since 2024, so discrimination can hardly be tested |
| B | Two tracks: Balance Luzon hunger against an adviser-set constant, and provincial price pressure by the existing rolling-mean + 1 SD rule, 2 consecutive quarters | Project E12/E51; CPI rule in `label_generator` | depends on constant; CPI 77 % | depends on constant; CPI 86 % | Honest about geography, but changes the thesis's composite and needs one adviser number |
| C | Existing whole-period median | `label_generator` | 9 % | 78 % | **Fails (e)**: tuned to class balance and uses future rows. Not offered |

The CPI rule also has an 86 % base rate in the evaluation period, so it has the same weakness: a level above a rolling mean during a sustained rise stays HIGH.

## Gate 1

**PASSED:** the table is complete and every gap is classed. **Stage 5 cannot start** until the owner or adviser picks the label rule (decision authority: "adopting a label rule, threshold or tolerance").

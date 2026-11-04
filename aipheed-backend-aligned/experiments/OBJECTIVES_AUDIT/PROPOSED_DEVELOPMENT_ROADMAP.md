# Proposed development roadmap (for approval; nothing started)

Ordered by impact on the thesis per unit of work and risk. Every modelling item is pre-registered (hashed plan, fixed
rules) before any fit, isolated in its own folder, and compared with C-b. **C-b, its seals, the ledger, production,
the frontend and the API stay untouched unless a step says "approval".**

## Priority 0: decisions only you or the adviser can make (no work until answered)

1. **Commit authorization** for the verified Phase C work (ALLBASE + the three prospective scripts + the ledger hash
   block). Needed before **2027-01-15** to cover the 2027-01-01 issue; otherwise coverage starts 2027-04-01.
2. **Option C wording** (regional forecast + vulnerability-weighted province/LGU outputs) for Objectives 2 and 3.
3. **Evaluator group:** 50 DA only (H5, §1.7, §3.7) or DA + DEPDev (RQ5) (paper contradiction C3).
4. **FNRI 2019:** accept "not published at regional level" and use 2023 regional + 2021 Batangas/Cavite.

## Priority 1: Objective 5 (largest gap that is fully within our control)

| Step | Work | Needs approval | Completion test |
|---|---|---|---|
| R5.1 | Served-model alignment plan: list every frontend/API string and number that describes a model, mapped to the served C-b fields | No (document) | Complete list with file:line |
| R5.2 | Implement it: remove the hardcoded Landing tables (read them from `/api` evaluation), correct the About text, delete dead `RegionSidebar` metrics, set the C-b mode in configuration | **Yes: frontend + API + render.yaml** | Frontend tests; every displayed metric traceable to `evaluation.json` |
| R5.3 | New **ISO/IEC 25010 instrument** for 50 DA Region IV-A evaluators: functional suitability, performance efficiency, compatibility, usability, reliability, security, maintainability, portability (items only where evaluators can judge), plus the **H4 ranking task** (each evaluator ranks provinces / top LGUs) | No (document), then your review | Approved instrument; pilot with 3–5 people |
| R5.4 | Analysis plan fixed before collection: per-characteristic means/SD, Likert descriptives, Cronbach's α (≥ 0.70) per characteristic, H5 decision rule (mean ≥ 3.5 and one-sample Wilcoxon > 3), H4 Spearman/Kendall between evaluator and aiPHeed ranks | No | Hashed plan |
| R5.5 | FNRI face-validity method: 2023 CALABARZON FIES 19.1% (17.0–21.1) vs the 2023 forecasts and SWS BL levels; 2021 Batangas 29.7%, Cavite 31.7% vs province scores (ordering only); stated as a different construct | No | One table with caveats |
| R5.6 | System test checklist (functional correctness, API vs display, workflow states, alerts, PDF) separate from evaluator feedback | No | Checklist run, results recorded |

## Priority 2: Objective 3 (method validity, no new model)

| Step | Work | Completion test |
|---|---|---|
| R3.1 | Independent recomputation of all 5 province and 142 LGU values from the source tables (second implementation) | Exact match or every difference explained |
| R3.2 | Weight sensitivity: ranks under (poverty, density) = (1, 0), (0.8, 0.2), (0.6, 0.4), (0.6, −0.4 i.e. density as a protective factor), reported as Kendall τ and top-10 overlap. **The direction of the density weight is for the adviser to decide; nothing is chosen from results** | Table + recommendation |
| R3.3 | Rank uncertainty: Monte Carlo over the SAE CVs (e.g. 1,000 draws), 90% rank intervals per LGU; flag CV > 20% | Interval per LGU |
| R3.4 | Independent evidence search: DSWD Listahanan 3 / 4Ps households per LGU (if publicly available), ENNS 2021 provincial FIES | Correlation reported, or "not available" |

## Priority 3: Objective 1 (measure the pipeline; one fair value test)

| Step | Work | Completion test |
|---|---|---|
| R1.1 | Labelled validation sample: about 300 headlines stratified by relevance score, labelled by two team members (relevance, province, food-stress yes/no); κ, and precision/recall of classifier v2, the geocoder and XLM-R | κ ≥ 0.6; P/R reported |
| R1.2 | Issue-date-safe BERTopic: refit at each origin on articles published before O(t) (or fit on 2021–2022 and transform later), topic stability (ARI between refits), share of place-name topics | Topics usable as features or documented as descriptive |
| R1.3 | **One** pre-registered news-era test of *early-warning* value: does a news signal anticipate the **direction of change** in BL hunger (Δ > 0) within 2021–2026, against hunger-only? Exact binomial / permutation; underpowered and stated so | Pre-registered result, whatever its sign |
| R1.4 | Operational value: alert events (news flags) vs subsequent typhoon/price shocks (precision of flags) | Reported |

## Priority 4: Objective 2 (at most two new hypotheses, pre-registered together, one Holm family)

| ID | Hypothesis (new; not tried) | Why it could help | Expected limit |
|---|---|---|---|
| **S1** | C-b with the raw hunger state replaced by (or supplemented with) a **local-level Kalman filter** estimate of true hunger and P(true > 11.3), using SWS's known sampling variance per quarter (2.908² / rounds), fitted on readings published before O(t) | Attacks the diagnosed cause (C-b follows one noisy reading through reversals) with a principled measurement-error model, unlike NOISE_W, which only reweighted rows | The noise ceiling (0.773 in 2015–2020) bounds any gain; may still change few calls |
| **S2** | K1 (0.5 C-b + 0.5 LOGIT, the best AUC/Brier so far) with a **walk-forward decision threshold** chosen on past forecasts only (maximize balanced accuracy, ≥ 20 past pairs, else 0.5) | Keeps K1's ranking (AUC 0.786) while restoring classification accuracy | Thresholds are noisy at n = 62; may move only a few calls |

Rules as Phase B/C: fold S selection, the same gates G1–G5, adoption only on G2 + G4 plus team/adviser approval, all
failures reported. If neither passes, **C-b stays** and Objective 2 is reported with its limits.

## Priority 5: prospective evidence (runs by itself once committed)

Quarterly seals of all 14 models from 2027; Algorithm 4 on the first four 2027 quarters (point values, about 2028);
the prospective 42-test family from 20 quarters per lead (about 2032); the R1–R7 verdict at 40 (about 2037).

## What will not be done (rule-breaking or already tested)

Forcing news weight or SHAP; copying regional hunger to provinces; changing the 11.3% line, the periods or R7;
thresholds chosen on the evaluation quarters; re-running K1–K3, NOISE_W, GDELT or price-label variants without a new
hypothesis; fabricated respondents or scores.

## Risks

- **Forking paths:** S1 and S2 are the 14th and 15th historical attempts. Report the count; the prospective record is
  the confirmatory evidence.
- **Time:** the 2027-01-15 sealing window is the hard deadline; the Objective 5 survey needs a deployed, aligned
  dashboard first.
- **Data:** BSP remittances and provincial unemployment remain unavailable unless supplied.

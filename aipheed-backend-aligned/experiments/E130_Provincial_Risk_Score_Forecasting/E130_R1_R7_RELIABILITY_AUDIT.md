# E130 reliability-rule audit (R1–R7 and N1–N7)

## Which rules apply

| Task | Rules | Source |
|---|---|---|
| Primary: numerical provincial risk score | **N1–N7** (protocol §8, frozen before any evaluation) | The E130 brief's requirements, made operational |
| Secondary: risk categories derived from the score | **R1–R7** (frozen, `FINAL_THESIS_OBJECTIVES/FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` §7, as used in E128) | Applies only once the owner approves PFDR category thresholds |

**Relation to the E129 amendments.** N1–N7 take in E129's proposed amendments without weakening anything:
- A-R1p: N1 counts distinct provincial observations;
- A-R4p: persistence is each province's own;
- A-R7p: N6 is the province floor;
- A-R2c: interval coverage, N7.

The brief's 75 %-within-tolerance requirement (N2) **replaces** the A-R2c skill threshold, and it is stricter.

## Rule-by-rule status

| Rule | Requirement | Applicable to a provincial target? | Attainable with the data held? | Status, every model, Leads 1–4 |
|---|---|---|---|---|
| N1 | ≥ 10 target quarters and ≥ 40 distinct province rows | Yes | **No.** 0 quarterly provincial reference values; PFDR gives 2 survey years per province. | **Fails** |
| N2 | ≥ 75 % of out-of-sample predictions within 1.645 × reference SE | Yes | Needs a target | Not evaluable |
| N3 | MAE and RMSE below every baseline (persistence, PSA-only, NLP-only, linear) on identical rows | Yes | Needs a target | Not evaluable |
| N4 | Squared error below persistence and climatology, cluster-bootstrap p < 0.10 (clusters = target quarters) | Yes | Needs a target | Not evaluable |
| N5 | Within-tolerance share ≥ 0.60 in each third; leave-one-quarter-out minimum ≥ 0.70 | Yes | Needs ≥ 3 target quarters | Not evaluable |
| N6 | No province with MAE skill below 0 against its own persistence | Yes | Needs per-province rows | Not evaluable |
| N7 | 80 % interval coverage between 0.70 and 0.90 | Yes | Needs a target | Not evaluable |
| R1 | ≥ 10 target quarters and ≥ 40 rows | Yes | No | **Fails** |
| R2, R3, R6 | Accuracy ≥ 0.75; balanced accuracy ≥ 0.70; HIGH precision and recall ≥ 0.60 | Only with approved thresholds | No approved thresholds | Not valid |
| R4, R5, R7 | Beat the majority class and persistence; Brier test; stability | Only with approved thresholds | No approved thresholds | Not valid |

**Survey-year reading.** Read at survey-year resolution, R1 and N1 fail as well:
- one change per province; a second only when PSA publishes provincial subsistence for a survey year after 2023 (none as of 2026-10-31);
- 10 survey rounds per province would first exist with survey year 2039 (`out/gate_recheck.json`).

## Can R1–R7 / N1–N7 ever be satisfied on these sources?

| Source | When N1 could first be met | Notes |
|---|---|---|
| PSA subsistence (biennial) | Never at quarterly resolution | At survey-year resolution, 10 rounds arrive in 2039 |
| SWS Balance Luzon (regional) | Already met (20 quarters) | Not provincial (G2). E128: no model passed R2–R7 at any lead. |
| A new quarterly provincial FIES series | 10 quarters after collection starts, the N1 minimum | The planning simulation shows 10 quarters is far from enough to *pass* N2 and N4. Even an idealized model with R² = 0.75 passes with probability ≤ 0.78 at 10 quarters; 20–40 quarters are needed. |

## Lead-2 operational conditions (brief §12)

| Condition | Status |
|---|---|
| 1. Forecast at least one completed quarter beyond the dashboard quarter | Definition met: Lead 2 = the dashboard's forecast target (`E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv`) |
| 2. Numerical agreement (N2) | Not evaluable |
| 3. Classification where valid | Not valid (no approved thresholds) |
| 4. Beat every baseline (N3) | Not evaluable |
| 5. Frozen reliability rules | N1 fails |
| 6. Acceptable across the five provinces (N6) | Not evaluable |
| 7. Overfitting and leakage audits | No model to audit. The feature panel's leakage checks (E119) pass. |
| 8. Repeatable on enough unseen origins | 0 unseen provincial origins |

**Lead 2 status: failed** (not evaluable, because no quarterly provincial reference exists).

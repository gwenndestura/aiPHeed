# aiPHeed research reassessment: food-insecurity RISK estimation and forecasting (2026-11-03)

Status: **methodology proposal, no code changed.** The production model, the registry (`production: null`) and all
locked results are unchanged. Every number below is either cited from a locked study or recomputed descriptively
from data already on file. No model was fitted, selected or scored for this document.

---

## 0. What changes in the conclusion of the November 3 report

The November 3 report said: no provincial food-insecurity forecast can be validated without repeated provincial
measurements. **That statement remains true for predicting actual prevalence.** It was too strong as a statement about
*risk*, because it judged every candidate as a prevalence predictor:

* **pfi-1.0** was asked for a chronological FIES series (gate check B6).
* **hfias-1.0** was asked for a level MAE of 5 pp or less.

Three facts measured today from the data on file (`backend/data/hfias/clean/`) change the picture:

| Fact | Value | What it means for risk |
|---|---|---|
| Spread of HFIAS food insecurity across 78 provinces (FNRI 2015) | 41.6–92.3 %, SD 9.5 pp; median SE 3.5 pp | Provinces really differ. 33 of 78 are significantly different from the national value (\|z\| > 1.96). There is a cross-sectional signal to learn. |
| Persistence of a province's position relative to the national value, 2015 → ENNS 2018/19 (same instrument, n = 43) | Spearman 0.44 (p = 0.003); above/below-national agreement 0.70 | Relative risk is partly structural and partly changes. Indicators can be tested for whether they explain the part that changes. |
| Why hfias-1.0 failed | The national level moved 53.9 % (2018 round) → 64.1 % (2019 round) | The failure was the **round-level shift in prevalence**. A risk target defined *relative to the same round* removes this shift by construction. |

So **survey-anchored relative-risk estimation is methodologically possible** with HFIAS province-rounds. It does not
need any invented quarterly labels. What stays impossible is a measured provincial *quarterly timing* signal. That
part is addressed separately in §6 and is not assumed.

---

## 1. What exact problem is aiPHeed trying to solve?

* **The goal.** Give DA IV-A a timely, evidence-based estimate of *which provinces are under conditions associated
  with elevated food-insecurity risk, now and in coming quarters*.
* **The constraint.** Direct household measurements (HFIAS, FIES) are taken only every few years, cover only some
  areas, and use instruments that cannot be pooled.
* **The research question.** Can frequently updated indicators, anchored to the sparse direct measurements that do
  exist, give risk estimates that agree with those measurements better than simple alternatives? And how far ahead
  does that remain true?

## 2. Why scarce and infrequent measurement is the research problem

* **Long gaps between surveys.** CALABARZON's provinces have one HFIAS round each (2015). Laguna, Quezon and Rizal
  have a second, from ENNS 2018/2019. Regional FIES exists for 2023. National FIES exists for 2019, 2021 and 2023.
  Between surveys, decision-makers have no measured outcome at all.
* **Fast-moving conditions.** Prices, typhoons, harvests and jobs change monthly.
* **A risk model fills the gap by:**
  * learning, from places and times where food insecurity *was* measured, how the indicators relate to it;
  * applying that relationship where and when it was not measured.

  This is the same logic as WFP HungerMap nowcasting (Martini et al. 2022, *Nature Food*) and small-area estimation.
  It is legitimate only if the learned relationship is shown to hold on measurements the model did not see.

## 3. Why risk differs from prevalence

* **A prevalence model** predicts the percentage of food-insecure households. It is judged by its error in
  percentage points against a survey. With one or two rounds and a moving national level, this cannot be validated.
  This is what pfi-1.0 and hfias-1.0 attempted.
* **A risk model** predicts the probability that an area is in a *defined elevated-risk state*. Here the proposed
  state is: the province's measured food insecurity is significantly above the reference level of the same survey
  round.
  * A score of 0.75 means "an estimated 75 % chance that the province is in the elevated state". It does **not**
    mean that 75 % of households are food insecure.
  * The model is judged by discrimination (AUC, balanced accuracy), calibration (Brier score, reliability) and skill
    over baselines, on held-out measured provinces and rounds.

## 4. What the existing data legitimately support

| Evidence | Units × occasions | Role it can play | What it cannot do |
|---|---|---|---|
| FNRI 2015 HFIAS | 78 provinces × 1 (with SE) | **Training/validation outcome** for relative risk (spatial cross-validation) | Show change over time |
| FNRI ENNS 2018/2019 HFIAS | ~76 areas (provinces and HUCs) × 1; 43–52 provinces also measured in 2015 | **Out-of-round outcome**: relative risk in a later round; change in relative position | Quarterly timing. The 2019 provinces were already scored once (hfias-1.0), so this data is development evidence, not a clean test |
| PSA FIES (SDG 2.1.2) | 17 regions × 2023; national 2019/21/23; IV-A 2025 provisional | **External validation** only (different instrument), by rank or direction | Pooling with HFIAS |
| FNRI NNS CALABARZON 2019/2023 | Region × 2 | **Face-validity anchor** | Quarterly labels |
| SWS involuntary hunger | 4 areas × ~110 quarters (1998+) | **The only measured quarterly temporal outcome**, at area level (Balance Luzon contains CALABARZON) | Provincial labels. Copying it into provinces is forbidden. |
| Owner workbook (FI12) | 40 verified primary records, 10 ENNS secondary | Cross-check of the values above | Independent new rounds: it reproduces FNRI/PSA figures, and its ENNS "mod-sev" column is mislabelled |
| PSA poverty/subsistence (provincial 2015/18/21/23), provincial CPI, palay/corn, fisheries; NASA POWER and IBTrACS (computable for all provinces); POPCEN | All provinces, monthly to triennial | **Predictors** (five groups) | Labels |
| News (FI5 Google News corpus, CALABARZON 2021+; FI6-N publisher archive, mainly Rappler, 2012+) | CALABARZON only, or nationally once geocoded | **Predictor** for the news group | Labels |

**Limits stated plainly.**
* Inside CALABARZON, the 2015 provinces cannot be told apart statistically: 53.2–59.7 % insecure, Cochran Q p = 0.46.
* All five provinces sit **below** the national value in 2015, and Laguna, Quezon and Rizal also in ENNS.
* So, measured against the national level, CALABARZON provinces are mostly LOW risk. Against the regional level, the
  only consistent signal is Quezon. Real differentiation exists **nationally**. Within the region it is weak, and the
  outputs must say so rather than exaggerate it.

## 5. Using sparse direct measurements without inventing ground truth

1. **Label only where a measurement exists.** The label set contains HFIAS province-rounds only, about 120–150 rows
   once ENNS HUCs are counted. No quarterly label is created, nothing is interpolated, and SWS is not copied into
   provinces.
2. **Define the label within a round.** The proposed target is
   y = logit(p_province) − logit(p_national, same round), and HIGH when y is significantly above 0 (z ≥ 1.645 using
   the survey SE). This removes the round-level shift and the instrument-level differences.
3. **Treat survey error as label noise, not as truth.**
   * Weight rows by 1/SE².
   * Report results under label resampling (draw p ~ N(p̂, SE) 200 times).
   * Keep provinces whose difference from the national value is not significant as a separate, honest "not
     distinguishable" group.
4. **Pool instruments only within an instrument.** HFIAS trains the model. FIES, NNS and SWS are used for
   validation, each on its own scale.
5. **Then apply the learned relationship quarterly.** Each quarter, the CALABARZON risk estimate uses only the
   indicators known at the issue date. This is risk estimation from indicators, not a new measurement.

## 6. Most appropriate LightGBM methodology

A **two-layer, survey-anchored design**. Each layer is learned only from measured outcomes.

**Layer S: where (structural relative risk). The primary LightGBM.**
* **Data.** A pooled national panel of HFIAS province-rounds (2015, ENNS 2018/2019).
* **Features.** As-of province indicators from the five groups:
  * market: provincial rice/food CPI change;
  * climate and agriculture: rainfall anomaly, typhoon exposure, palay, corn and fisheries;
  * employment: provincial LFS where PSA publishes it, otherwise regional;
  * poverty and vulnerability: poverty, subsistence, density;
  * news: national archive geocoded to provinces (feasibility to be checked);
  * plus the province's last measured relative position as an anchor.
* **Model.** Shallow, strongly regularised LightGBM: depth ≤ 3, min_data_in_leaf ≥ 10, monotone constraints where
  theory is unambiguous (more poverty → not lower risk). Hyper-parameters are chosen only in inner folds.
* **Output.** P(province is significantly above the national reference). Each quarter it is recomputed from current
  indicators, so the estimate moves when conditions move.
* **Compared fairly with:**
  * persistence of the last survey position;
  * a PSA-only (poverty-only) model;
  * logistic regression on the same features;
  * no-skill (base rate).

  NLP-only is included only if the national news layer proves feasible.

**Layer T: when (temporal anomaly), regional, at SWS area level.**
* **Data and target.** Pooled across the 4 SWS areas, quarterly 1998+. The target is the FI6 definition: hunger above
  its five-year average by more than the SWS margin of error.
* **Leads.** 0 (nowcast at quarter end, never tested before), then 1, 2 and 3. News enters here as well.
* **Prior evidence.** FI5 and E110 found no skill over persistence at Leads 1–4.
* **Rule.** Layer T enters the provincial estimate only if it passes its own criteria. Even then it enters as an
  as-of *feature* of Layer S (the area-level anomaly, which hfias-1.0 tested as H1), never as a provincial label. If
  it fails, the regional hunger outlook stays separate regional context.

**Why LightGBM here.**
* It handles missing groups natively (news and LFS gaps).
* It allows monotone constraints.
* It gives exact TreeSHAP attributions.

**Its weakness:** n ≈ 130. It must therefore beat logistic regression in pre-registered cross-validation. If it does
not, the report says so rather than assuming the method's superiority.

## 7. What the target should represent

"**The province's household food insecurity (HFIAS, any level; moderate-or-severe as secondary) is significantly
higher than the national level of the same survey round.**"

* It is measured, instrument-consistent, unaffected by round-level shifts, and not built from any predictor.
* **Decision for the owner (D-1): national or regional reference.**
  * National gives real variation to learn from, but labels CALABARZON mostly LOW.
  * Regional is more relevant to DA, but within-region differences are mostly not significant.
  * Proposal: learn against the national reference. Then present CALABARZON provinces both by probability and by
    their rank within the region, with uncertainty.

## 8. Constructing, interpreting, calibrating and validating risk scores

| Step | Method |
|---|---|
| Score | Layer S probability; continuous variant (predicted relative logit with interval) compared |
| Calibration | Platt scaling fitted inside nested CV only (n too small for isotonic); reliability diagram with bootstrap CI; ECE reported with CI |
| Uncertainty | Conformal interval on the relative logit; label-resampling spread; "not distinguishable" class shown, never forced to HIGH/LOW |
| **A. Risk-model evaluation** | Spatial CV on 2015 (leave-one-region-out, 17 folds); AUC, balanced accuracy, Brier, F1, class recall; group ablation; grouped-SHAP stability across folds; dominance check (share of the largest group per prediction) |
| **B. Forecast evaluation** | (i) Out-of-round: train 2015 → score ENNS 2018/19 relative positions (development evidence, disclosed as previously viewed). (ii) Lead k = indicators frozen k quarters before the survey (hfias-1.0 framework). (iii) Layer T walk-forward on SWS areas, Leads 0–3, against persistence. |
| **C. External validation** | Aggregate province scores to regions (population-weighted) → rank against PSA FIES 2023 (17 regions; Spearman with CI); direction against IV-A FIES 2023 vs 2025; NNS CALABARZON 2019/2023 face validity. Reported as agreement, never as accuracy against a label. |
| Confirmatory test | Only genuinely unseen measurements count: a new FNRI provincial round, PSA 2026 FIES, or Layer T prospective quarters (sealed). Everything on current data is pre-registered **development** evidence. |

## 9. Maximum defensible lead time

* **Layer S (where).** Relative position persists over the 3–4 years between rounds (ρ 0.44), so a structural
  estimate stays informative for several quarters. But that comes from persistence, not from forecasting skill. A
  lead counts as valid only where the indicator model beats "last survey position" at that lead.
* **Layer T (when).**
  * Leads 1–4: prior evidence shows no skill over persistence.
  * Lead 0 has never been tested.
* **Expected answer.** A defensible horizon of Lead 0 to Lead 1 for timing, and a structural estimate (labelled as
  such) beyond that.
* The number is determined only by the pre-registered criteria, set before any scoring and listed in the
  pre-registration (step P2 below).

## 10. Methodology: what changes and what stays

| Change | Justification | Data required | Advantage | Limitation | Evaluated by |
|---|---|---|---|---|---|
| C1 Target = within-round relative risk (HFIAS) instead of prevalence level | Matches the risk objective; removes the 53.9 → 64.1 round shift | On file | Measured, non-circular, poolable within instrument | 2019 rows already scored; within-region differences small | §8 A and B |
| C2 National pooled panel instead of CALABARZON only | Signal exists nationally (33/78 significant), not within the region | On file; national features to assemble | n ≈ 130 instead of 5–8 | Assumes the relationship transfers to IV-A; tested by leave-region-out | §8 A |
| C3 Survey-error-aware labels | SE is 2.5–3.7 pp in IV-A | On file (SE, CI) | Honest uncertainty; no false HIGH/LOW | Fewer decisive labels | Label resampling |
| C4 Two layers (where / when) | Only SWS has measured timing; it must not be copied into provinces | SWS 4 areas on file | Each claim validated where it can be | Provincial timing stays unvalidated | §8 B (iii) |
| C5 Lead 0 nowcast test (Layer T) | Never tested; operationally useful before the SWS release | On file | Fills a stated gap | May also fail against persistence | Walk-forward |
| C6 Risk-appropriate gate version (new version, not retroactive) | B6 "chronological FIES" checks a prevalence model | — | Judges risk models on risk criteria | Must be frozen before scoring | Registry gate |
| C7 National news layer (Rappler archive geocoded to provinces) | News is CALABARZON-only, so it cannot be learned nationally otherwise | FI6-N archive; geocoder extension | Lets news compete in Layer S | Source concentration (95 % Rappler); coverage bias toward large provinces | Three-way ablation in the same harness |

**Stays as is:**
* as-of / release-date discipline;
* walk-forward evaluation;
* the four baselines;
* never pooling HFIAS with FIES;
* the release gate and registry;
* the LGU vulnerability weights;
* the "no new UI elements" rule.

**Stays rejected:** all locked results and rejections (pfi-1.0, hfias-1.0, FI5, FI9). They were valid tests of what
they claimed. The new candidate gets a new identifier and a new pre-registration.

## 11. Integrating the five groups meaningfully

* All five groups enter Layer S only if each one has a national, as-of series. News is conditional on C7.
* **Contribution is measured, not assigned:**
  * grouped TreeSHAP (sum of member features) per prediction;
  * group permutation importance in cross-validation;
  * leave-one-group-out ablation with paired bootstrap CIs.
* **Dominance diagnostic.** For each prediction, record the share of the largest group, and its distribution across
  folds, provinces and quarters. A group near 100 % triggers a check for leakage, redundancy or availability bias.
  The group is never rebalanced.
* **The dashboard shows a group only if** it is in the model and its contribution passes a pre-registered minimum.
  Otherwise the existing text field says "not influential for this province". This uses existing backend fields, so
  the UI is unchanged.

## 12. Claims the completed study can legitimately make (if the criteria are met)

**Can claim:**
* "Indicator-based risk scores distinguish provinces whose measured household food insecurity (HFIAS) is above the
  national level, with AUC X and balanced accuracy Y in leave-region-out validation, compared with baselines Z."
* "In a later survey round, the scores' agreement with measured relative positions was …" (development evidence).
* "Regional aggregation agrees / does not agree with PSA FIES 2023 regional rankings (ρ …)."
* "The quarterly score changes when the underlying indicators change; which groups drive it is shown by SHAP."

**Cannot claim:**
* that a score is a prevalence;
* that quarterly provincial changes were validated against measured provincial changes;
* 75 % accuracy, unless it is reached on pre-registered held-out measurements;
* that within-CALABARZON rankings are statistically distinct, unless the data show it (currently only Quezon).

---

## 13. Proposed next steps (nothing done yet)

| Step | Output |
|---|---|
| **P1. Feasibility** | Assemble national as-of features for 2015/2018/2019, and count rows per group: provincial CPI, poverty, palay/corn, fisheries, NASA POWER, IBTrACS, LFS, news. No outcome is looked at. |
| **P2. Pre-registration (frozen, hashed)** | Target C1, reference (D-1), folds, candidate models, thresholds for the A/B/C criteria, the Lead 0–3 rule, the group-minimum rule, and the new gate version (C6). |
| **P3. Run once** | Layer S, Layer T and baselines. |
| **P4. Report** | Results reported as they come out, whatever they are. |
| **P5. Gate decision** | Only a gate-approved candidate may reach the dashboard. |

**Owner decisions needed before P2:**
* **D-1.** National or regional reference.
* **D-2.** Primary outcome: "any food insecurity" or "moderate-or-severe".
* **D-3.** Whether ENNS 2018/2019, which hfias-1.0 has already scored, may serve as development evidence while the
  confirmatory test waits for an unseen round or prospective quarters.

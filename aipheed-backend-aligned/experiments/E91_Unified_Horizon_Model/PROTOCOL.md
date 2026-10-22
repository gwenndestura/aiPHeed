# E91 protocol: one unified food-insecurity risk model with an empirically determined horizon K (frozen before scoring)

**Directive.** "E90: Develop One Unified Food Insecurity Forecasting Model With an Empirically Determined K-Quarter
Horizon" (2026-10-22). It is numbered E91 because E90 already exists (rice-led onset diagnostic, sealed HUN-RICE).

**Branch.** `e91-unified-horizon-model`, from `e90-advanced-optimization` (which contains e89-model-optimization).
The production branch is not touched.

**Freezing.** This file and `runner/run_e91.py` are hashed into `PROTOCOL.sha256` and committed before `run_e91.py
score` is run.

**Already built and checked, without metrics (`run_e91.py build`).**
- Feature tables and baselines for K = 1..4: `tables/features_k{K}.csv`, `tables/baselines_k{K}.csv`.
- At K = 1..3 the baselines, labels and S-SIM are asserted identical to the E84 run.
- At K = 4 the structural price core cannot be computed. The year-on-year base quarter (quarter t) is not yet
  published at the origin O(t), so S-SIM, S-COV and the base-effect projections are empty, as E63 found.

## 1. Starting point (verified)

| Model | Lead | Accuracy | Balanced accuracy | HIGH caught | Brier | Source |
|---|---|---|---|---|---|---|
| S-SIM | 1 | 0.846 | 0.751 | 9/16 | 0.118 | E89 run 20261022T033435Z, re-verified in E90 |
| S-COV | 2 | 0.800 | 0.636 | 5/16 | 0.177 | E89 run 20261022T033435Z, re-verified in E90 |

**Why surges are missed (E84–E90):**
- Hunger is modelled as a random walk from the last posted SWS reading.
- The 2023-Q4 onset was in no input at the Lead-2 origin.
- The 2024-Q2 onset had a rice-price signal, but no earlier surge to learn from.
- Hunger is one regional reading (Balance Luzon) shared by all five provinces.
- Since 2023-Q4 the target has followed the price condition only.

## 2. Target, rows and timing (unchanged)

- **Target.** T43 (E40 label specification).
- **Rows.** At every K: 65 rows, targets 2023-Q1..2026-Q3 × 5 provinces, 16 HIGH. The origin is t = target − K.
- **Timing.** Every feature comes from `d.cut(t)`.
- **Training labels.** Only labels complete and posted before O(t) (`e83_lib.pairs`).
- **Window.** Data from 2021-Q1 onward only.

## 3. The unified model

**One model per origin, all horizons.** At each origin t, a single model is fitted on the **pooled** training pairs of
every horizon k ∈ {1, 2, 3, 4}: (X_k(t′), y(t′+k)) with labels posted before O(t). The horizon k is an input.
- The same fitted model issues the K = 1..4 forecasts made at t.
- No horizon has its own model or its own selection.

**Structural core.** S-COV gives P(hunger > 11.3) from a random walk and P(price condition) from component CPI paths
with world-rice pass-through, for any k.

| Candidate | Description |
|---|---|
| **U-STRUCT** | The structural core alone; k enters only through the simulation horizon. No fitted horizon parameters. |
| **U-CAL** | Horizon-conditioned calibration of the core: logistic regression on k, logit P_hunger, logit P_price and their interactions with k. |
| **U-LR** | U-CAL plus every driver group (below). Logistic regression, C = 0.5, standardised on training rows. |
| **U-GB** | LightGBM boosted from the core (init score = logit core probability) on k, the two core logits and every driver group. 4 leaves, depth 2, 60 trees, rate 0.05, λ = 5. |
| **U-GB-RAW** | LightGBM on k and every driver group, without the structural core: tests whether an algorithm alone, with the horizon as input, can learn the problem. |
| U-LR-RICE (diagnostic) | U-CAL plus positive rice YoY, its interaction with k, and hunger level. **Not selectable**: the rice predictor was chosen in E90 after seeing the full-period correlation. |

**Driver groups:**

| Group | Features |
|---|---|
| Prices / market | food and gap relative to thresholds, momentum, base-effect projections, rice retail/wholesale YoY and momentum, world rice, policy events |
| Climate stress | typhoon count, maximum signal, severe count, ENSO |
| Agricultural supply | palay, corn, fish and aquaculture YoY |
| Employment and remittances | unemployment level and change, underemployment, remittance YoY, FX YoY |
| Hunger history | level relative to 11.3, last change, age of the last reading |
| Poverty | PSA 2021 SAE provincial mean, as published (from 2025-01-01) |
| News | the N3 indicators; tested as an added group |

**Missing values.** Filled with the training median.

**Eligibility and fallback.** A learned candidate is fitted when the pooled training set has at least 6 label quarters
and at least 5 HIGH labels. Otherwise it issues the structural-core probability.

**K = 4.** Candidates that use the core train on the K = 1..3 pairs. At K = 4 they issue nothing, which counts as wrong
under the PASS rule. Only U-GB-RAW can issue K = 4.

## 4. Architecture selection (before K is read)

- **Choice.** The architecture is the selectable candidate with the **lowest mean Brier across K = 1..4 on the
  selection block** (targets 2023-Q1..2024-Q4, 8 quarters).
- **Confirmation block.** Targets 2025-Q1..2026-Q3 (5 quarters), reported separately.
- **Decision threshold.** Fixed at 0.5, as in the PASS rule. No threshold is tuned.
- **Disclosure.** All 13 target quarters were scored at pooled level in E83–E90, so neither block is untouched. Only
  the sealed prospective quarters are.

## 5. Horizon K (existing rules, unchanged)

**PASS(k)** is the E83 rule (`run_e83.passes`):
1. accuracy > 0.75 with unissued rows counted as wrong;
2. balanced accuracy > every baseline (B-PERSIST, B-STATE, B-MAJ, B-CLIM, B-AH, B-AL, B-PSA, B-NLP);
3. Brier lower than B-PERSIST, B-CLIM and B-AH, with a per-date sign-flip p < 0.10, one-sided, Holm-adjusted;
4. HIGH recall ≥ 0.5.

**Temporal generalization (k)** uses the pre-set Lead-1 criteria (GENERALIZATION_CRITERIA.md):
- accuracy ≥ 0.75 in both the early block (targets ≤ 2024-Q4) and the late block, criterion (b);
- correct majority in at least 60% of quarters (otherwise "not demonstrated to generalize").

**Validated K** = the largest K such that every horizon 1..K satisfies PASS **and** temporal generalization. If
horizon 1 fails, K = 0, reported as "no validated horizon". The E83 reading (every lead from 2 to K passes) is also
reported.

## 6. Reported for every K and candidate

- Accuracy, balanced accuracy, HIGH precision, recall and F1.
- Confusion matrix and the list of missed HIGH rows.
- Brier, log-loss, calibration-in-the-large and a 5-bin reliability table.
- Baselines: persistence, climatology, always-LOW, PSA-only, NLP-only, B-STATE, B-MAJ, always-HIGH.
- The existing models S-SIM and S-COV, as experimental baselines.
- Coverage and share of fitted origins.
- Quarter-by-quarter correct counts against persistence; quarter and province accuracy SD.
- The generalization criteria (a)–(e); selection-block and confirmation-block metrics.

**Driver contribution.** On the selected learned architecture (U-LR if U-STRUCT is selected), and on U-GB:
- drop one driver group at a time;
- add news;
- report the change in Brier and accuracy at every K.

## 7. Iteration rule

After this run, errors are inspected. Any further variant is **post-hoc**:
- it is reported as such;
- it may define a candidate K;
- it never defines the validated K.

The selected architecture's forecasts from origin 2026-Q3 are sealed for prospective evaluation. Existing seals are
not touched.

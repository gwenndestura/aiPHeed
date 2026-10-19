# E66: the best defensible aiPHeed methodology for Objectives 1–4

**Date:** 2026-10-19
**Branch:** `aiPHeed/best-model-methodology-review`, created from `e62-final-audit` @ fee3b8f (recorded in `out/original_head.txt`, `out/original_status.txt`; the uncommitted E46 D-1 hunks of another session in `insights.py` and `e41_lead2.py` were kept in the working tree and are **not** part of this branch's commits).
**Protocol:** `PROTOCOL.md`, frozen before any E66 arm was scored (SHA-256 `090e9061…`, checked by every runner and by a test).
**Requirement basis:** Chapter I §1.5 only. Chapter I sets no accuracy threshold, so none is applied ("reliable" is undefined there).
**Evidence status:** every metric below is **development evidence**. All 50 evaluation rows (targets 2024-Q2..2026-Q3) were examined by E56–E65 before E66. No quarter is unseen. The first independent test is the frozen 2026-Q4 / 2027-Q1 forecasts.

---

## A. Executive conclusion

**Selected methodology: a layered early-warning architecture, served as the opt-in mode `AIPHEED_LEAD2_MODEL=e66`.** Its numbers are the E58 record's; its layers are kept separate:

| Layer | What it is | Status |
|---|---|---|
| 1. Lead-2 forecast | E56-TUNED LightGBM (two quarters ahead), the Chapter I proposed model. Its price part P_price, read through the E58 two-signal warning (P_price ≥ 0.5) | Development evidence; not validated |
| 2. Regional hunger | Latest SWS Balance Luzon hunger and P(hunger > 11.3%), shown as its own number (already in the record's components) | Observed, regional only |
| 3. Climate Food-Stress Watch (CFSW, new) | Rule-based El Niño hazard watch: PAGASA El Niño Alert/Advisory in force at issue + regional hunger > 11.3%, with provincial production drop as local exposure | Transparent rule; **not validated, not a probability, not a model input** |
| 4. LGU priority | Approved 0.6 poverty + 0.4 density weighting × province score, ranked on the unrounded index | Relative prioritization, not a municipal forecast |
| 5. News/NLP | Pipeline v3 (FSSI-v3, BERTopic) for context and event monitoring | No measured forecasting gain |

**Why this and not another model.**
- **No candidate beats the E56 LightGBM by the frozen rule** (paired Brier CI below 0 and quarter sign test p < 0.05, Holm). That covers 22 arms on the same 50 rows: news ablations, climate-aware variants, a stable-configuration fix, two new L2 logistic regressions, a random-walk hunger part, transparent rules and all baselines (section F). So the Chapter I proposed model stays.
- **The price layer is what carries the skill.** On all 50 evaluation rows **T43 equals PS** (provincial food-price pressure), because regional hunger was above 11.3% in every evaluated quarter. Read as a price-pressure warning, E56's P_price scores accuracy 0.78, balanced 0.78, Brier 0.182, onsets 7/10. The full product P(HIGH) scores 0.72 / 0.684 / 0.214 / 3/10.
- **The model cannot see the approaching El Niño** (E65: ENSO has 0 price-tree splits; prices are projected flat). E66 does not hard-code HIGH. It adds the separately labelled CFSW. For 2026-Q4 and 2027-Q1 **all five provinces are under a CLIMATE WATCH**; Cavite, Laguna and Batangas also show local exposure for 2027-Q1.

**What it can reliably predict:** nothing is established as reliable on unseen data.
- On development rows it beats persistence and the majority class on Brier (quarter-cluster CI below 0; sign test not significant, 7 of 10 quarter wins).
- It does **not** beat climatology or always-LOW in the late regime: 2025-Q4..2026-Q3 had 1 HIGH in 20 rows.

**Most important limitations:**
1. There is no provincial food-insecurity outcome. SWS hunger is regional, so the evaluated target is food-price pressure.
2. There are 10 evaluation quarters and one El Niño episode.
3. Probabilities are over-confident (calibration slope 0.55).
4. Lead 2 is less accurate than lead 1, and no lead meets the reliability rule.
5. The LGU order inside a province is static vulnerability. Lucena's rank depends entirely on an unverified substitute.

---

## B. Objectives 1–4 compliance matrix

| Obj | Requirement (Chapter I, abridged) | Implementation | Evidence | Status | Remaining work |
|---|---|---|---|---|---|
| 1 | Two-tier pipeline: zero-shot XLM-RoBERTa FSSI + BERTopic patterns per province-quarter from a Filipino-English corpus | `app/news/pipeline_v3.py` (E64): E31+E60 corpus 9,667 titles, de-syndication, XLM-R FSSI-v3, BERTopic (152 topics); classifier v2 (precision 0.92 / recall 0.75 on AI-annotated titles) | Panel produced 2021–2026 (E64 `tables/r1_fssi_v3_panel.csv`). FSSI is **not** an input of the served model. News ablations show no forecasting gain (section G). Corpus is titles only and collected retrospectively. | **Partially Met** | Human check of the annotations; prospective collection; use for context only unless a prospective gain is shown |
| 2 I–IV | Accuracy, precision/recall, F1, AUC of the LightGBM | E57 rolling origin, 10 origins, 50 rows, re-scored by E66 | P(HIGH): acc 0.72 [Wilson 0.58–0.83], prec 0.625, rec 0.556, F1 0.588, AUC 0.649. P_price warning: 0.78, AUC 0.786 | **Met (development evidence only)** | Prospective scoring of the 2026-Q4 and 2027-Q1 seals |
| 2 V | Walk-forward multi-lead evaluation; furthest reliable horizon | E63 sealed leads 1–3, re-scored by E66 | Lead 1: 0.85 / Brier 0.130. Lead 2: 0.72 / 0.214. Lead 3: 0.62 / 0.251 (≈ climatology). Lead 4 not computable. No lead meets the rule. | **Not Met** (horizon not established; "reliable" undefined in Ch. I) | Adviser definition of "reliable"; more quarters |
| 3 | Municipal/city risk rankings from validated province forecasts using PSA poverty and density | Approved 0.6/0.4 method; 142 LGUs; e66 ranks on the unrounded index | 142 unique, finite, five provinces 34/23/30/41/14. The order inside a province equals the vulnerability order. Province forecasts are not validated. | **Partially Met** (relative prioritization, not validated) | DA evaluator check (H4); verify Lucena substitute |
| 4 | Compare the LightGBM against persistence, PSA-only, NLP-only and logistic regression | E55 Chapter I baselines (45 rows) + E66 50-row scoreboard + new matched LR (N1/N2) | E56 Brier is lower than every Chapter I baseline: 0.178 vs 0.235 (NLP-only LR) and 0.400 (persistence) on 45 rows. CI excludes 0 for persistence, PSA-only LR and LR-combined, not for NLP-only. No sign test significant. | **Met as a comparison; superiority Not Yet Validated** | Unseen quarters |

---

## C. Historical experiment comparison

Rows reproduced by E66 from sealed files; metrics on the same 50 rows unless marked.

| Experiment | Model / idea | Reproducible metric | Weakness | Verdict |
|---|---|---|---|---|
| E38 (production default) | Lead-2 LightGBM on the v1 label | 0.709 on 55 rows (own label); refitted on T43 0.356 (45 rows) | v1/Eq.3 label saturated (46/50 HIGH since 2023-Q4); no climate input | Kept as production default (not E66's call); not comparable on T43 |
| E55 | T43 LightGBM, 24 configs | 0.733 (45 rows) | One configuration short of E56 | Superseded by E56 |
| E56 | E56-TUNED, 72 configs, nested | 0.72 / bal 0.684 / Brier 0.214 | Configuration switching between origins; hunger part errors in 2024-Q2 | **Retained** as the proposed model |
| E58-EW | Two-signal warning, P_price ≥ 0.5 | 0.78 / 0.78 / 0.182, onsets 7/10 | Whole gain over E56 is 2024-Q2 | **Retained** as the warning reading |
| E60 A/C/D | gov-only / + improved news / + history | 0.74 / 0.74 / 0.68; Brier 0.212 / 0.215 / 0.223 | No difference from E56 | News not adopted as predictor |
| E61 | Calibration, drift and combination fixes | All ≈ E56; random-walk hunger RMSE better | Not significant | Random-walk hunger re-tested here (N3) |
| E63 | Leads 1–3 | 0.130 / 0.214 / 0.251 | No lead meets the rule | Reported in section H |
| E64 D/E/A-S | gov + news v3 / + history / stable config | Brier 0.204 / 0.211 / 0.219 | None significant | Not adopted |
| E65 B1/B2/B3/C/D1 | Climate-aware variants and a PAGASA rule | Brier 0.213–0.223; D1 0.360 | Only one El Niño episode | Not adopted as model inputs; CFSW is the replacement layer |

---

## D. Target validity

**What T43 is:** regional SWS hunger > 11.3% AND provincial food-price pressure, where price pressure means PSA food YoY or food − headline above the province's 2021–22 reference (`tables/r7_target_by_year.csv`, `out/r4_r7.json`).

| Fact | Value |
|---|---|
| T43 = PS whenever hunger > 11.3% | **70 / 70** rows |
| T43 = PS on the 50 evaluation rows | **50 / 50** (asserted in `r1`) |
| Hunger above the line | 2024, 2025 and 2026: every quarter |
| Share of T43 variance between quarters | 0.49 (one regional hunger series, common price shocks) |
| Quarters with one label for all five provinces | 12 of 21 |
| HIGH rate by year | 2021 0.13, 2022 0.00, 2023 0.15, 2024 0.40, 2025 0.45, 2026 0.07 |
| Late regime (2025-Q4..2026-Q3) | 1 HIGH in 20 rows |

**What it represents:** on everything that has been evaluated, **provincial food-price pressure under a high-hunger regime**.

**What it does not represent:**
- household food insecurity in a province (no CBMS or provincial FIES outcome exists in the data);
- affordability: the gap rule reads a faster rise in non-food prices as relief, so in 2026-Q3 hunger was 23.6% and headline inflation 4.8–7.3%, yet the label is LOW;
- climate or production stress.

**Is the thesis claim supported?** A "food-insecurity forecast" claim is **not supported** by this target. A "provincial food-price-pressure early warning under elevated regional hunger" claim is supported as development evidence.

In e66 mode, the API's event wording now says this (`CANDIDATE_EVENTS["e66"]`). Changing the served target or the headline number to P_price would be a target redefinition. It is recommended, but it **needs adviser approval** (E51), so E66 did not do it.

**No validation against FNRI or SWS is claimed.** SWS is the label's own input, and FNRI has only a regional 2023 figure.

---

## E. El Niño and the forecast drop

Source: `tables/r5_el_nino_province_q3_q4_q1.csv` (all inputs and contributions), `tables/r5_cfsw_forward.csv`, E65 `tables/r1_change_decomposition.csv`. Served values equal the record (max difference < 5e-4, which is 3-dp storage).

### E.1 Province by province

**Inputs at each issue date:**

| Target | Issued | Hunger posted | CPI through |
|---|---|---|---|
| 2026-Q3 (back-test) | 2026-04-01 | 16.7% | 2026-02 |
| 2026-Q4 | 2026-07-01 | 22.4% | 2026-05 |
| 2027-Q1 | 2026-10-01 | 17.3% | 2026-08 |

| Province | Target | P(HIGH) | P_hunger | P_price | Food YoY latest | Headline YoY | Food proj / thr | Gap proj / thr | CFSW | N2 LR P (exploratory) |
|---|---|---|---|---|---|---|---|---|---|---|
| Batangas | 2026-Q3 | 0.097 | 0.949 | 0.102 | −0.55 | 1.00 | −0.40 / 7.15 | −1.52 / 0.66 | — | 0.14 |
| Batangas | 2026-Q4 | 0.019 | 0.997 | 0.019 | 2.15 | 5.00 | 2.39 / 7.15 | −1.92 / 0.66 | WATCH + EXPOSURE | 0.26 |
| Batangas | 2027-Q1 | 0.043 | 0.962 | 0.044 | 0.25 | 4.40 | 0.75 / 7.15 | −2.51 / 0.66 | WATCH + EXPOSURE | 0.13 |
| Cavite | 2026-Q3 | 0.434 | 0.949 | 0.457 | 1.05 | 2.20 | 1.44 / 4.71 | +0.66 / 0.74 | — | 0.53 |
| Cavite | 2026-Q4 | 0.024 | 0.997 | 0.024 | 4.90 | 6.95 | 0.99 / 4.71 | −2.71 / 0.74 | WATCH + EXPOSURE | 0.27 |
| Cavite | 2027-Q1 | 0.109 | 0.962 | 0.113 | 2.50 | 4.60 | 1.03 / 4.71 | −2.53 / 0.74 | WATCH + EXPOSURE | 0.30 |
| Laguna | 2026-Q3 | 0.120 | 0.949 | 0.127 | 1.65 | 3.60 | 1.56 / 6.05 | −1.67 / 0.61 | — | 0.29 |
| Laguna | 2026-Q4 | 0.061 | 0.997 | 0.061 | 3.75 | 8.05 | 1.34 / 6.05 | −4.48 / 0.61 | WATCH + EXPOSURE | 0.14 |
| Laguna | 2027-Q1 | 0.070 | 0.962 | 0.073 | 2.90 | 6.90 | 0.86 / 6.05 | −2.42 / 0.61 | WATCH + EXPOSURE | 0.20 |
| Quezon | 2026-Q3 | 0.806 | 0.949 | 0.850 | 0.05 | 1.50 | 3.27 / 6.24 | +1.41 / −0.56 | — | 0.67 |
| Quezon | 2026-Q4 | 0.285 | 0.997 | 0.286 | 6.50 | 8.05 | 5.41 / 6.24 | −1.61 / −0.56 | WATCH + EXPOSURE | 0.70 |
| Quezon | 2027-Q1 | 0.146 | 0.962 | 0.152 | 3.60 | 6.10 | 2.08 / 6.24 | −2.58 / −0.56 | WATCH | 0.33 |
| Rizal | 2026-Q3 | 0.124 | 0.949 | 0.131 | 0.80 | 2.60 | 0.94 / 7.10 | −1.02 / 0.92 | — | 0.21 |
| Rizal | 2026-Q4 | 0.005 | 0.997 | 0.005 | 4.60 | 7.85 | 1.11 / 7.10 | −4.38 / 0.92 | WATCH | 0.08 |
| Rizal | 2027-Q1 | 0.050 | 0.962 | 0.052 | 2.95 | 6.60 | 1.67 / 7.10 | −2.55 / 0.92 | WATCH | 0.18 |

- **Observed 2026-Q3:** LOW in all five provinces (food YoY 0.7–4.5%, hunger 23.6%), so Quezon's back-test HIGH was a false alarm.
- 2026-Q4 and 2027-Q1 are not yet observed.
- The 2026-Q3 back-test has no CFSW, because PAGASA had issued only an El Niño Watch by 2026-04-01.
- N2 LR (projection only) is an exploratory comparison, not served.

### E.2 Root causes (E65 decomposition, reproduced)

- **2026-Q3 → 2026-Q4:**
  - The CPI projection fell further below the thresholds while headline inflation outran food, which makes the gap more negative and counts as relief under T43.
  - The depth-3 configuration 68, selected only at that origin, pulled Cavite, Rizal and Batangas down through its palay, corn and typhoon trees.
- **2026-Q4 → 2027-Q1:** mostly the switch back to configuration 23.
- **The level is low** because the flat-price projection (0.8–2.1% food inflation) is far below what HIGH needs (5.5–8.0%).
- **Not causes:** stale hunger (P_hunger 0.95–0.997), a serving defect, or missing climate data.

### E.3 Is the model insensitive to the climate threat?

Yes.
- ENSO enters only as a binary t−1/t−2 phase code, with 0 price-tree splits at all three origins.
- Neutralising ENSO moves the 2027-Q1 score by at most 1 point.
- At the 2026-07-01 issue the model saw "neutral / La Niña" while PAGASA El Niño Advisory No. 1 (2026-06-09) was in force.
- No rainfall or drought series exists in the 2021–2026 window: the provincial rainfall file holds pre-2021 rows, so it is refused.
- E65's climate-aware arms (B1–B3) change nothing material, and one El Niño episode cannot teach the model an effect.
- The target excludes climate stress except through food CPI.

### E.4 What E66 implemented

`backend/app/ml/inference/climate_watch.py` implements the CFSW rule, frozen in PROTOCOL §4 before it was computed.

**How it works:**
- It uses PAGASA items dated **before** the issue date. Its hazard coding matches E65's independent coding at all 20 issue dates (0 mismatches).
- Missing hunger gives INSUFFICIENT DATA. Missing production gives "exposure unknown", never "no exposure".
- It changes no probability, decision or colour.
- In e66 mode its text goes into the existing `summary.sentence` field, and its values into a new optional API field `summary.climateWatch`. **No UI element was added.**

**History (descriptive only, `tables/r5_cfsw_vs_outcomes.csv`):**
- Before 2026, only the 2024-04-01 issue had a watch (5 rows; T43 HIGH 1 of 5).
- The 2023-10-01 and 2024-01-01 issues had an El Niño Advisory, but the posted hunger was 10.3%, below the line.
- This is too little to validate anything. The CFSW is a hazard flag, not a forecast.

**Warning implication:** an elevated **climate watch** is justified for all provinces in 2026-Q4 and 2027-Q1. A validated HIGH food-insecurity probability is **not**.

---

## F. Model comparison

**Design:**
- Rows: the 10 E57 origins (issue dates 2024-01-01..2026-04-01), targets 2024-Q2..2026-Q3, 50 rows, 18 HIGH.
- Data and labels: the same issue-date cutoffs, the same labels (T43 from E58 events), one scorer (`runner/e66_lib.py`).
- Uncertainty: quarter-cluster bootstrap (2,000 draws) and quarter sign test, Holm across arms.
- Every learner refits at each origin on data published before it (E56 frame).
- The new LR arms were defined in the frozen protocol before they were scored.

### F.1 Fifty rows (`tables/r1_metrics_50rows.csv`)

| Arm | Acc | Bal | Rec HIGH | Rec LOW | FA | Miss | Brier | AUC | Cal. slope | Onsets |
|---|---|---|---|---|---|---|---|---|---|---|
| **E56-TUNED LightGBM (proposed)** | 0.72 | 0.684 | 0.556 | 0.812 | 6 | 8 | 0.214 | 0.649 | 0.55 | 3/10 |
| **E58-EW (P_price ≥ 0.5)** | **0.78** | **0.780** | 0.778 | 0.781 | 7 | 4 | **0.182** | 0.786 | 0.75 | **7/10** |
| E60-A gov-only | 0.74 | 0.700 | 0.556 | 0.844 | 5 | 8 | 0.212 | 0.656 | 0.56 | 3/10 |
| E60-C gov + improved news | 0.74 | 0.675 | 0.444 | 0.906 | 3 | 10 | 0.215 | 0.649 | 0.51 | 3/10 |
| E60-D gov + news + history | 0.68 | 0.628 | 0.444 | 0.812 | 6 | 10 | 0.223 | 0.653 | 0.45 | 3/10 |
| E64-D gov + news v3 | 0.72 | 0.684 | 0.556 | 0.812 | 6 | 8 | 0.204 | 0.660 | 0.62 | 3/10 |
| E64-E gov + news v3 + history | 0.74 | 0.700 | 0.556 | 0.844 | 5 | 8 | 0.211 | 0.682 | 0.55 | 3/10 |
| E64-A-S stable configuration | 0.68 | 0.665 | 0.611 | 0.719 | 9 | 7 | 0.219 | 0.679 | 0.59 | 3/10 |
| E65-B1 / B3 / B2 climate-aware | 0.72–0.74 | 0.68–0.70 | 0.556 | 0.81–0.84 | 5–6 | 8 | 0.213–0.214 | 0.65 | 0.54–0.56 | 3/10 |
| E65-C climate removed | 0.72 | 0.684 | 0.556 | 0.812 | 6 | 8 | 0.223 | 0.635 | 0.48 | 3/10 |
| E65-D1 PAGASA El Niño rule | 0.64 | 0.561 | 0.278 | 0.844 | 5 | 13 | 0.360 | 0.561 | — | 4/10 |
| CPI-projection rule | 0.74 | 0.748 | 0.778 | 0.719 | 9 | 4 | 0.188 | 0.788 | 0.95 | 7/10 |
| N1 L2-LR matched inputs (new) | 0.44 | 0.465 | 0.556 | 0.375 | 20 | 8 | 0.335 | 0.469 | — | 3/10 |
| N2 L2-LR projection only (new) | 0.68 | 0.665 | 0.611 | 0.719 | 9 | 7 | 0.228 | 0.639 | 0.49 | 4/10 |
| N3 E56 price × random-walk hunger (new) | 0.72 | 0.672 | 0.500 | 0.844 | 5 | 9 | 0.203 | 0.675 | 0.66 | 3/10 |
| News-only LR (E60-B / E64-B) | 0.36 / 0.38 | 0.43 / 0.44 | 0.667 | 0.19 / 0.22 | 26 / 25 | 6 | 0.445 / 0.507 | 0.48 / 0.44 | — | 5/10, 4/10 |
| Persistence | 0.56 | 0.535 | 0.444 | 0.625 | 12 | 10 | 0.440 | 0.535 | — | 0/10 |
| Majority (always LOW) | 0.64 | 0.500 | 0 | 1 | 0 | 18 | 0.360 | 0.500 | — | 0/10 |
| Climatology | 0.64 | 0.500 | 0 | 1 | 0 | 18 | 0.304 | — | — | 0/10 |
| Province climatology | 0.64 | 0.500 | 0 | 1 | 0 | 18 | 0.293 | 0.477 | — | 0/10 |

### F.2 Paired Brier against E56 (`tables/r1_paired_vs_E56.csv`)

**No arm is better by the rule.**

| Arm | Difference | 95% CI | Quarter wins | Sign p |
|---|---|---|---|---|
| E58-EW | −0.032 | [−0.102, +0.006] | 3/10 | 0.95 |
| CPI-projection rule | −0.026 | — | — | — |
| N3 random-walk hunger | −0.011 | [−0.025, +0.0001] | 8/10 | 0.055 |
| E64-D | −0.010 | — | — | — |
| N1 LR-matched | +0.121 | — | — | — |
| News-only arms | +0.23 to +0.29 | CI excludes 0 | — | — |

- N3 is the closest to passing, but it is not adopted.
- N1 is significantly **worse** (CI excludes 0).
- The news-only arms are significantly worse.

### F.3 Against the baselines (`tables/r1_paired_vs_persistence.csv`, `r1_paired_vs_climatology.csv`)

- **Persistence:** every LightGBM-family arm has a Brier difference of −0.22 to −0.26, CI below 0, with 7 of 10 quarter wins. The sign test is not significant.
- **Climatology:** the CIs touch 0 (E56: −0.090, CI upper bound +0.0006). Not better by the rule.

### F.4 Chapter I baselines, 45 rows (`tables/r1_metrics_45rows_with_chapter1_baselines.csv`)

| Baseline | Acc | Brier |
|---|---|---|
| E56 (reference) | 0.778 | 0.178 |
| I Persistence | 0.600 | 0.400 |
| II PSA-only LR | 0.378 | 0.598 |
| III NLP-only LR | 0.667 | 0.235 |
| IV LR combined | 0.333 | 0.646 |
| E38 procedure refitted on T43 | 0.356 | 0.433 |

E56 has a lower Brier than every baseline. The CI excludes 0 for I, II, IV and E38, but not for III (+0.057, CI −0.010..+0.123). No sign test is significant.

### F.5 By regime (`tables/r1_metrics_by_regime.csv`)

| Period | Rows | E56 | E58-EW | Always LOW |
|---|---|---|---|---|
| 2024-Q2..2025-Q3 | 30 (17 HIGH) | 0.60 | 0.70 | 0.43 |
| 2025-Q4..2026-Q3 | 20 (1 HIGH) | 0.90 | 0.90 | 0.95 |

In the late regime no model discriminates: HIGH recall is 0 for E56 and EW.

### F.6 By quarter and province (`tables/r1_by_quarter.csv`, `r1_by_province.csv`)

- **Worst quarter:** 2024-Q2 (E56 0.20, EW 0.80; stale hunger).
- **Weakest province:** Cavite (E56 0.40, EW 0.50, Brier 0.41 / 0.35).
- **Rizal:** never HIGH; E56 1.0.

### F.7 Price layer scored against PS (`tables/r3_price_layer_vs_PS.csv`)

- E56 P_price: 0.78 / Brier 0.182.
- gov-only: 0.80 / 0.180.
- gov + news v3: 0.78 / 0.172.
- Projection rule: 0.74 / 0.188.
- PS persistence: 0.62 / 0.380.
- Nothing beats E56 P_price by the rule. Every model beats PS persistence on the CI, but not on the sign test.

### F.8 Selection reasons

1. **Target validity:** the layered design names what each number measures.
2. **No candidate is better than the Chapter I LightGBM by the rule**, so the LightGBM stays (PROTOCOL §5).
3. **The EW reading of the same model** has the best Brier and onset detection among model arms, at no extra fitting.
4. **The simpler CPI-projection rule is close** (Brier 0.188) but not better by the rule. It is kept as the transparent benchmark.
5. **New LR arms:** N1 is clearly worse. With about 30–60 training rows and 11+ standardised inputs, L2-LR is unstable. That also explains the poor E55 LR baselines.

---

## G. News/NLP integration

**Pipeline** (E64 `DATA_TO_DASHBOARD_FLOW.md`, verified in E62/E64), stage by stage:

| Stage | Implementation |
|---|---|
| Collection | Google News RSS titles, retrospective, 2021-01..2026-10-14 |
| Deduplication | article_key, plus de-syndication in v3 |
| Language | Filipino/English titles |
| Relevance | classifier v2 (precision 0.92 / recall 0.75, AI-annotated) |
| Trigger tagging | E40 taxonomy |
| Geography | province attribution |
| Time | quarter = quarter of the PH date; 0 errors in E62 `r5` |
| Aggregation and features | N3 / E40 shares, FSSI-v3 |
| Training, inference, explanation, API, dashboard | e64 mode only (served). In e58/e66 the model's news inputs are the old E40 keyword shares, with ~0 effect at 2027-Q1. |

**Predictive value** (same 50 rows), as Brier:

| Arm | Brier |
|---|---|
| Government only (E60-A) | 0.212 |
| + original news (E56) | 0.214 |
| + improved news (E60-C) | 0.215 |
| + news v3 (E64-D) | 0.204 |
| + news + history (E60-D / E64-E) | 0.223 / 0.211 |
| News only | 0.445 / 0.507, significantly worse than E56 |

**No news arm is better by the rule.** A higher classification F1 did not translate into forecasting gain.

**Role in e66:** context, event monitoring and explanation only. News is **not forced into the model**.

**Leakage controls:** news of quarter t is used only for issues after t. The D-E62-2 fix stops post-issue articles appearing beside an issued forecast.

**Limitations:**
- Titles only.
- Retrospective collection: 2,118 of 2,132 E60 articles were first seen after their issue date, so coverage at past issue dates cannot be reproduced.
- Leads empty.

---

## H. Lead-time analysis (`tables/r4_lead_metrics.csv`, `r4_lead_paired.csv`)

| Lead | Rows (HIGH) | E56 acc | Bal | Brier | AUC | Price part only Brier | vs persistence (CI; quarter wins) | vs climatology (CI; wins) |
|---|---|---|---|---|---|---|---|---|
| 1 | 60 (21) | 0.850 | 0.819 | 0.130 | 0.901 | 0.118 | −0.187 [−0.293, −0.091]; 9/12 | −0.155 [−0.261, −0.054]; 9/12 |
| 2 | 50 (18) | 0.720 | 0.684 | 0.214 | 0.649 | 0.182 | −0.226 [−0.399, −0.056]; 7/10 | −0.090 [−0.188, +0.001]; 5/10 |
| 3 | 45 (14) | 0.622 | 0.569 | 0.251 | 0.620 | 0.244 | −0.237; 7/9 | −0.015 [−0.116, +0.086] |
| 4 | — | — | — | — | — | — | not computable: the base CPI month falls after the cutoff | — |

On common targets (45 rows) the Brier score rises monotonically: 0.113, 0.178, 0.251.

**No lead meets the rule.** Lead 1 is closest: both CIs are below 0, but with 9 of 12 quarter wins the sign test gives p = 0.073.

**Operational Lead-2 is preserved:**
- The target quarter is computed from the clock (`app/quarterly/target.py`): viewing on 2026-10-19 gives 2027-Q1; on 2027-01-15, 2027-Q2.
- The frozen 2027-Q1 record never serves a later quarter (test).

**The gap:** the operational horizon (lead 2) is one quarter beyond the best-supported horizon (lead 1). Lead-2 reliability is **not established**.

---

## I. LGU prioritization (`out/r6_lgu.json`, `tables/r6_*.csv`)

**Method (approved, unchanged):**
- vulnerability = 0.6 × poverty_norm (PSA 2021 SAE) + 0.4 × density_norm (POPCEN 2024), min-max within each province;
- index = province score × vulnerability.

**Coverage:**
- 142 unique LGUs, five provinces 34/23/30/41/14, all finite.
- 141 own SAE values.
- 1 substitute: Lucena, a highly urbanized city absent from the PSA no-HUC table.

**What the order means:**
- **Inside a province, rank = vulnerability rank** at any province score (verified). The ranking is a **static relative prioritization**, not a forecast. Only the across-province order changes with the forecast.
- The region-wide rank correlates about equally with the province score (ρ 0.68) and with vulnerability (ρ 0.70). Because the index mixes five within-province scales, compare within a province.

**Sensitivity** (within-province Spearman vs approved; mean top-5 overlap):

| Poverty weight | Spearman | Top-5 overlap |
|---|---|---|
| 0.5 | 0.96 | 4.2 |
| 0.7 | 0.97 | 4.2 |
| 1.0 (poverty only) | 0.74 | 3.2 |
| 0.0 (density only) | 0.32 | 2.0 |

The order is robust to moderate re-weighting. It is not robust to dropping either component.

**Substitute sensitivity:**
- Lucena is **1st of 41** in Quezon with the stored substitute (16.8%).
- It stays 1st at the province maximum.
- It falls to **22nd** at the province minimum.
- Its position depends on an unverified substitute value (the source workbook is not in the repository).

**Ties (D-E66-3):**
- At the 2027-Q1 scores (0.04–0.15), 4-dp rounding creates ties for 29 LGUs, and 15 region ranks change.
- In e66 mode, ranks use the unrounded index: 0 ties, the same displayed index values, PSGC order inside true ties.
- The default ranking is unchanged.

**Census age:** POPCEN 2024 and SAE 2021 are the latest authorized. Poverty may have changed since 2021, and the SAE CVs are reported per LGU.

**Supports:** "where to look first within a province", if the province score is accepted.
**Does not support:** municipal food-insecurity rates, probabilities or classifications.

---

## J. Defects and unresolved failures

Severity: H = affects a thesis claim, M = affects outputs or interpretation, L = cosmetic or precision.

| ID | Type | Sev. | Evidence | Root cause | Files | Status / fix | Next step |
|---|---|---|---|---|---|---|---|
| D-E66-1 | Target validity | H | T43 = PS on 50/50 evaluation rows and 70/70 rows with hunger > 11.3% | SWS hunger is regional and was above the line throughout 2024–26 | label definition (E40/E43) | e66 wording states it (`CANDIDATE_EVENTS["e66"]`). Target unchanged (needs adviser). | Adviser: adopt PS + separate hunger indicator, or obtain a provincial outcome (CBMS/FIES) |
| D-E66-2 | Methodology / data | H | ENSO 0 price-tree splits; flat price projection; no in-window rainfall | One El Niño episode; no forward climate input | E56 model | CFSW layer added (e66 only; numbers unchanged) | Pre-register a forward climate input before 2027-01-01; PAGASA outlook archive |
| D-E66-3 | Code | L | 29 LGUs tied by 4-dp rounding; 15 region ranks differ | Ranks computed on the display value | `lgu_poverty.rank_lgus`, `lgu_audit.build_ranking`, `forecaster_v2.lgu_table`, `e31_engine` | Fixed opt-in (`exact_ranks`, e66). Default unchanged. | Adviser/user: adopt for production |
| D-E66-4 | Data | M | Lucena 1st ↔ 22nd of 41 with the substitute value | No municipal SAE for HUCs; substitute source unverified | `data/inputs/lgu_vulnerability.csv` | Unresolved; disclosed in the API (`povertyLimitation`) | Obtain PSA HUC estimate or document the substitute source |
| D-E66-5 | Data | M | 2026-Q3 typhoon count truncated at the 2026-09-09 fetch, filled as 0 | "No storm" = 0 also used for an incomplete quarter | E56 feature table | **Unresolved** in the frozen model (0 price splits at 2027-Q1, so no effect on P_price; small hunger-ridge term). Changing it would alter a sealed forecast. | Next model build: NaN for incomplete quarters |
| D-E66-6 | Method | M | Configuration 23 → 68 → 23 caused the 2026-Q4 dip | Per-origin nested selection | E56 procedure | Stable selection (E64 A-S) not better (+0.005). Unresolved. | Report as instability; prospective check |
| D-E66-7 | Method | M | Hunger ridge over-predicts; N3 random walk −0.011 (p = 0.055) | Small regional series | E56 hunger part | Not adopted (rule not met) | Pre-register RW hunger for 2027 |
| D-E66-8 | Data | M | Remittances missing at 2026 issues (BSP ends 2025-Q4) | Manual download needed | BSP input | Unresolved; learned NaN branch | Download BSP 2026 |
| D-E66-9 | Validation gap | H | Late regime 1 HIGH in 20 rows; no discrimination; always-LOW 0.95 | Few events | — | Disclosed | Prospective scoring of the seals |
| D-E66-10 | Calibration | M | Calibration slope 0.55 (P(HIGH)), 0.75 (P_price) | Small data; product of two parts | E56 | Disclosed ("model score, not a tested probability") | Calibrate on unseen quarters only |
| D-E66-11 | Research gap | H | No lead meets the reliability rule; "reliable" undefined in Ch. I | — | — | Disclosed | Adviser definition |
| D-E66-12 | Pre-existing | L | 6 TypeScript errors in `frontend/src/data/mockData.ts` | Mock data behind the type | frontend | Unchanged (no frontend edits allowed) | Separate fix with UI approval |
| — | Pre-existing | L | scikit-learn 1.7.2 pickles loaded under 1.8.0 (warnings) | Version drift | `requirements` | Unchanged | Pin or re-export |

---

## K. Reproducibility and tests

**Commands** (from `backend/`, venv Python; each runner checks the protocol hash and the sealed SHA-256 files):

```
venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E66_Best_Methodology_Review/runner/r2_new_arms.py      # ~2 min
venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E66_Best_Methodology_Review/runner/r1_scoreboard.py    # ~3 min
venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E66_Best_Methodology_Review/runner/r4_leads_r7_target.py
venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E66_Best_Methodology_Review/runner/r5_el_nino.py
venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E66_Best_Methodology_Review/runner/r6_lgu.py
venv/Scripts/python.exe -B -m pytest -q tests
```

**Serving the selected methodology locally:** set `AIPHEED_LEAD2_MODEL=e66`. The production default (unset = E38) is unchanged.

**Inputs:**
- sealed files: E57, E58, E60, E61, E63, E64 (hashes in `out/r1_scoreboard.json`);
- E55 baseline rows; E65 `r3_rows50.csv` and the E65 trace;
- `backend/data/e58/e58_record.json`;
- E56 feature frame (`E56_LightGBM_Optimization/runner/e56_lib.py`).

**Model configuration:** E56-TUNED nested selection over 72 configurations. Configuration 23 is served at the 2027-Q1 origin (depth 1, 40 trees, drift m = 0, feature set "all"); artifacts in `backend/data/e56/model/`.

**Test results (2026-10-19):**

| Suite | Result |
|---|---|
| Backend full suite | **468 passed, 18 skipped, 0 failed** (77 s; `out/backend_full_suite.txt`), including 15 new E66 tests (`tests/integration/test_e66_methodology.py`) |
| Frontend vitest | 46 / 46 passed |
| Frontend production build (`vite build`) | passed |
| `tsc --noEmit -p tsconfig.app.json` | 6 errors, all pre-existing in `mockData.ts` |
| Frontend files changed | none |

**What the E66 tests cover:** protocol and seal integrity; scoreboard reproduction; T43 = PS; lead metrics; lead-1/lead-2 alignment; the CFSW hazard cutoff and missing-data rules; the CFSW agreeing with E65; e66 numbers equal to e58; e58 and E38 getting no watch; the production default unchanged; 142 LGUs and the province counts; finite values; exact ranks; the default ranking unchanged; the dynamic target with no stale forecast.

---

## L. Release recommendation

- **Further testing and thesis evaluation: suitable.** The branch documents what each output measures, reproduces prior results, and adds no regressions (468/0).
- **Staging: suitable only as the opt-in `e66` mode, after the user's and adviser's review.** The CFSW and the e66 wording are new claims about meaning, and they need that review.
- **Production: not recommended.**
  - There is no validated model.
  - The served target is price pressure, not food insecurity.
  - The 2026-Q4 and 2027-Q1 seals are unscored.
  - The production default (E38) is a separate decision E66 did not make.
- **Not done, by design:** no merge to `main` or the deployed branch, no change to deployment configuration, no change of default mode.

**Decisions needed (adviser/user):**
1. Adopt PS (price pressure) plus a separate regional hunger indicator as the declared target, or keep T43 with the wording above.
2. Accept the CFSW as a documented hazard watch.
3. Define "reliable" for Objective 2 V.
4. Make exact LGU ranks the default.
5. Pre-register a forward climate input before the 2027-01-01 origin.

# E65: the 2026-Q4 / 2027-Q1 risk drop under the 2026–27 El Niño

**Date:** 2026-10-19
**Branch:** `e62-final-audit`. Nothing is committed, pushed or switched.
**Protocol:** `PROTOCOL.md`, frozen before any arm was scored (SHA-256 `9dcd0d4f…`).

**Which model:** the low values come from the experimental two-quarter-ahead model E56/E58 (`AIPHEED_LEAD2_MODEL=e58`). The production default E38 is a different model:
- it forecasts one quarter ahead and has no climate input;
- it shows HIGH for 2026-Q4 in every province except Batangas (0.17);
- it shows HIGH in all five provinces for 2027-Q1 (0.80–0.95).

E65 explains the E56/E58 values.

**Evidence status:** every accuracy figure below is development evidence. All 50 evaluation rows were seen by E56–E62, and the climate variants were designed knowing that El Niño occurred.

## Answer in brief

1. **The drop is real arithmetic on real inputs, with no implementation defect** (all served values reproduce from the frozen procedure, to the record's 3-decimal storage). It came in two steps:
   - **2026-Q3 → 2026-Q4 (issued 2026-07-01):** the CPI projection fell further below the province thresholds. The food-minus-headline gap went from about −1.5 to −1.6..−4.3 points, as headline inflation outran food. Under the depth-3 configuration 68, the palay/corn/typhoon inputs also pulled three provinces down. That configuration was selected only at that origin.
   - **2026-Q4 → 2027-Q1:** mostly the switch back to configuration 23, which *raised* Cavite, Rizal and Batangas. The level stays low because the flat-price CPI projection for 2027-Q1 (0.8–2.1% food inflation, gap −2.4..−2.6) is far below what HIGH needs (5.5–8.0%, or a gap of −0.2..+1.4).
2. **The model does not take account of the approaching El Niño in any material way.**
   - Its only ENSO inputs are binary phase codes of the quarter before last, without strength.
   - They have **zero splits in the food-price trees** at all three origins.
   - They act only in the regional hunger part, which is already saturated: setting ENSO to neutral lowers the 2027-Q1 score by **at most about 1 point**.
   - At the 2026-Q4 issue date the model saw **"neutral / La Niña"**, although PAGASA's El Niño Advisory No. 1 had been out since 2026-06-09.
   - The PAGASA outlooks, strength forecasts and rainfall/drought outlooks are not inputs, and no rainfall series exists in the window.
3. **Adding or correcting climate information does not change the evidence** (pre-registered, same 50 rows):
   - ENSO intensity (B1), the PAGASA status on the issue date (B3) and both (B2) each give paired Brier differences of about ±0.001, with CIs spanning 0 and decisions changed in at most 1 row.
   - Removing climate (C) gives +0.009, also with a CI spanning 0.
   - **No arm passes the rule.**
   - The what-if 2027-Q1 values under B1–B3 stay at 0.04–0.14. With only one El Niño episode (2023–24) in the training window, the model cannot learn an El Niño effect.
4. **The target cannot register most climate-related food stress.** Whenever regional hunger is above 11.3%, T43 is exactly the food-price condition (70 of 70 rows; every row since 2024). Drought losses, a hunger rise or a headline-inflation surge do not make it HIGH unless provincial food CPI crosses its threshold.
   - In 2026-Q3, hunger was 23.6% and headline inflation 4.8–7.3%, and the label is LOW everywhere.
5. **Recommendation: the low forecast is defensible only as a forecast of the T43 price-pressure indicator and needs a warning.** It cannot be read as evidence that El Niño food risk is low. That warning is now in the dashboard text, in E56/E58 mode only.

---

## 1. Province-by-province comparison

Sources: `tables/r1_trace_by_province.csv` (all columns) and `tables/r1_change_decomposition.csv`.

**How to read the tables:**
- P = P_hunger × P_price.
- "Offset" is the structural CPI-projection log-odds; it uses the configuration's drift m = 0 (flat prices).
- "Trees" is the sum of the price-tree TreeSHAP terms plus the tree constant.
- The food and gap projections are for the target quarter.

### Inputs at the issue date (PSA CPI, SWS)

| Target (issued) | CPI used through | Food YoY (latest 2 months) | Headline YoY | Gap | Latest posted SWS hunger |
|---|---|---|---|---|---|
| 2026-Q3 (2026-04-01, back-test) | 2026-02 | −0.55 .. 1.65 | 1.0 .. 3.6 | −1.15 .. −1.95 | 16.7% (2025-Q4, posted 2026-01-14) |
| 2026-Q4 (2026-07-01) | 2026-05 | 2.15 .. 6.50 | 5.0 .. 8.05 | −1.55 .. −4.30 | 22.4% (2026-Q1, posted 2026-05-12) |
| 2027-Q1 (2026-10-01) | 2026-08 | 0.25 .. 3.60 | 4.4 .. 6.9 | −2.10 .. −4.15 | 17.3% (2026-Q2, posted 2026-08-24) |

### Components per province

| Province | Target | Config | P | P_hunger | P_price | Food proj (thr) | Gap proj (thr) | Offset | Trees |
|---|---|---|---|---|---|---|---|---|---|
| Cavite | 2026-Q3 | 23 | 0.434 | 0.949 | 0.457 | 1.44 (4.71) | +0.66 (0.74) | −0.06 | −0.11 |
| Cavite | 2026-Q4 | 68 | 0.024 | 0.997 | 0.024 | 0.99 | −2.71 | −1.81 | −1.89 |
| Cavite | 2027-Q1 | 23 | 0.109 | 0.962 | 0.113 | 1.03 | −2.53 | −1.75 | −0.31 |
| Laguna | 2026-Q3 | 23 | 0.120 | 0.949 | 0.127 | 1.56 (6.05) | −1.67 (0.61) | −1.82 | −0.11 |
| Laguna | 2026-Q4 | 68 | 0.061 | 0.997 | 0.061 | 1.34 | −4.48 | −2.38 | −0.35 |
| Laguna | 2027-Q1 | 23 | 0.070 | 0.962 | 0.073 | 0.86 | −2.42 | −2.32 | −0.22 |
| Quezon | 2026-Q3 | 23 | 0.806 | 0.949 | 0.850 | 3.27 (6.24) | +1.41 (−0.56) | +1.85 | −0.11 |
| Quezon | 2026-Q4 | 68 | 0.285 | 0.997 | 0.286 | 5.41 | −1.61 | −0.26 | −0.66 |
| Quezon | 2027-Q1 | 23 | 0.146 | 0.962 | 0.152 | 2.08 | −2.58 | −1.50 | −0.22 |
| Rizal | 2026-Q3 | 23 | 0.124 | 0.949 | 0.131 | 0.94 (7.10) | −1.02 (0.92) | −1.78 | −0.11 |
| Rizal | 2026-Q4 | 68 | 0.005 | 0.997 | 0.005 | 1.11 | −4.38 | −3.17 | −2.06 |
| Rizal | 2027-Q1 | 23 | 0.050 | 0.962 | 0.052 | 1.67 | −2.55 | −2.60 | −0.31 |
| Batangas | 2026-Q3 | 23 | 0.097 | 0.949 | 0.102 | −0.40 (7.15) | −1.52 (0.66) | −2.06 | −0.11 |
| Batangas | 2026-Q4 | 68 | 0.019 | 0.997 | 0.019 | 2.39 | −1.92 | −2.10 | −1.86 |
| Batangas | 2027-Q1 | 23 | 0.043 | 0.962 | 0.044 | 0.75 | −2.51 | −2.76 | −0.31 |

**Observed 2026-Q3 outcome:** LOW in all five provinces. Food YoY was 0.7–4.5%, headline 4.8–7.3%, hunger 23.6%. Quezon's back-test HIGH (0.81) was therefore a false alarm. 2026-Q4 and 2027-Q1 are not yet observed.

**Dashboard:** the served values (E58 mode, `/api/v1/provinces`) equal P above, to the record's stored precision: a maximum difference of 4e-4, because back-test and earlier values are stored to 3 decimals (checked in `r1`).

## 2. Exact causes of the decline

Units are log P; a change of −0.69 halves P.

### 2026-Q3 → 2026-Q4

**Total change:** −0.68 (Laguna) to −3.15 (Rizal). The hunger part contributed +0.05.

**Inputs, with the 2026-Q4 model held fixed** (exact Shapley over input blocks):

| Province | Total input effect | CPI / market | Climate inputs | Note |
|---|---|---|---|---|
| Cavite | −2.34 | −1.52 | −0.91 | |
| Rizal | −2.34 | −1.34 | −1.19 | |
| Batangas | −1.21 | −0.02 | −1.23 | |
| Quezon | −0.83 | −1.08 | +0.15 | |
| Laguna | −0.13 | −0.36 | +0.65 | news volume −0.48 |

- The "climate inputs" here are palay/corn production and typhoons under configuration 68 (palay 33 splits, corn 31, typhoon lag 12). **ENSO had 0 splits.**
- **Model / configuration change** (23 → 68): −0.21 to −0.81.

### 2026-Q4 → 2027-Q1

**Total change:** −0.67 (Quezon) to +2.24 (Rizal). The hunger part contributed −0.04.

- **Configuration switch back to 23:** +1.51 (Cavite), +1.71 (Rizal), +1.61 (Batangas), +0.34 (Quezon), +0.11 (Laguna).
- **CPI inputs:** −0.99 (Quezon), −0.75 (Batangas), +0.54 (Rizal).
- **Climate inputs:** +0.001.

### Why 2027-Q1 is low in level

- **The CPI offset is −1.5 to −2.8 log-odds.** Food YoY to August 2026 was 0.25–3.6%, against thresholds of 4.7–7.2%. The gap was −2.1 to −4.2 points, against thresholds of −0.56 to +0.92.
- **The selected drift m = 0 projects flat prices from the latest month**, so any food-price rise after August 2026 is outside the forecast by construction.
- **The trees** (unemployment, missing remittances, corn) add −0.22 to −0.31.
- **What P_price ≥ 0.5 would need** (`tables/r2_cpi_needed_for_high.csv`): projected 2027-Q1 food inflation of 5.5% (Cavite), 6.7% (Laguna), 6.9% (Quezon), 7.9% (Rizal) or 8.0% (Batangas). The alternative is a gap above about −0.2 to +1.4.

### What did **not** cause it

| Possible cause | Evidence |
|---|---|
| Stale hunger | P_hunger is 0.95–0.997 at all three origins |
| Missing climate data | none missing; one truncation, see section 3 |
| A serving defect | served values reproduce |
| Climate variables | climate block effect +0.001 at 2026-Q4 → 2027-Q1 |

The remittance inputs were missing at both 2026 issue dates (BSP data end 2025-Q4). They are handled by a learned tree branch; their effect is −0.10 at 2027-Q1. This was already disclosed (E62 W8).

## 3. Climate-feature availability and contribution audit

Sources: `tables/r2_climate_feature_audit.csv`, `r2_enso_counterfactuals.csv`, `out/r2_climate_audit.json`, `sources/SOURCES.md`.

### Inputs the model has

| Input | Source, timing | Observed or forecast | Level | Missing handling | Price-tree splits (Q3 / Q4 / Q1 origins) | Hunger ridge |
|---|---|---|---|---|---|---|
| `enso` | NOAA ONI quarter mean of t−1, coded +1/0/−1 (strength dropped); published before O(t) | observed | one Pacific index copied to every province | quarter dropped if unpublished → NaN | 0 / 0 / 0 | yes: +3.1 H points at 2027-Q1 |
| `enso_l2` | same, t−2 | observed | same | same | 0 / 0 / 0 | yes |
| `enso_x_mom` | enso × food-CPI momentum | observed | province | — | 8 / 0 / 0 | no |
| `tc_count`, `tc_count_l1` | IBTrACS storms within 300 km, t and t−1 | observed | province centroid | no storm = 0 | 0 / 12 / 0 | yes |
| `palay_yoy`, `corn_yoy` | PSA production, t−1 | observed | province | NaN | 0 / 33+31 / 0+5 | palay yes |
| `tcl1_x_palay` | interaction | observed | province | — | 0 / 8 / 0 | no |
| `news_climate` | climate-tagged news share, quarter t | observed text | province | 0 if no article | 0 / 0 / 0 | no |

Notes on the inputs above:
- `enso` at the 2027-Q1 issue was El Niño (+1) for 2026-Q2.
- `enso_l2` at the 2026-Q4 issue was La Niña (−1) for 2025-Q4.
- **The 2026-Q3 typhoon count is truncated.** The file was fetched on 2026-09-09, so the count used for the 2027-Q1 forecast misses storms after that date (PAGASA lists TY Queenie, 24–27 Sep). Because "no storm" is filled as 0, a truncated quarter looks like a calm one.
- **The corn YoY values are extreme** (−84% to +233%) on small bases.
- **`news_climate` collection was retrospective.**

### What the model saw versus PAGASA

| Issue date | Model's ENSO inputs | PAGASA status in force (issued before the date) |
|---|---|---|
| 2026-04-01 (2026-Q3) | La Niña (2025-Q4); neutral | El Niño **Watch** (03-25) |
| 2026-07-01 (2026-Q4) | **neutral** (2026-Q1); **La Niña** (2025-Q4) | El Niño **Advisory No. 1** (06-09): conditions present; >80% chance of a full El Niño until early 2027 |
| 2026-10-01 (2027-Q1) | El Niño (2026-Q2, weak class, strength not used); neutral | **Advisory No. 4** (09-07): moderate to strong, may become very strong, until H1 2027. **Climate Advisory** (09-23): "very strong" in SOND |

- **After the 2027-Q1 issue date:** Advisory No. 5 (2026-10-07), "strong to very strong", is context only.
- **The latest observed ONI season at 10-01 (JJA) was already in the STRONG class:** the parquet's partial 2026-Q3 value. The protocol's t−1 lag, which is leakage-safe, used the WEAK-class 2026-Q2 value. This is an inference from the file's timing.

### Contribution

**ENSO counterfactuals** (each origin's fitted model, other inputs as observed):

| Origin | Change | Effect |
|---|---|---|
| 2027-Q1 | ENSO set to neutral | P_hunger 0.962 → 0.895; P falls by at most 1.0 point (Quezon 0.146 → 0.136) |
| 2027-Q1 | El Niño on both lags | P_hunger 0.958; no further rise |
| 2026-Q4 | El Niño coded on both lags | P changes by < 0.1 point |

**The price part has no ENSO route at either forecast**, so ENSO cannot raise P_price.

### Not in the model at all

- ENSO intensity (in the file, unused);
- `drought_alert`: in the file and unused; derived from ONI ≥ 1.0, **not a PAGASA drought advisory**;
- rainfall: `rainfall_anomaly_pct` is null, and `province_rainfall.parquet` holds pre-2021 rows, so it is refused;
- PAGASA ENSO status and strength outlooks;
- PAGASA monthly rainfall and dry-spell outlooks by province;
- ENSO forecast plumes.

### Provincial level

ENSO and PAGASA statements are national. PAGASA advisories name provinces only occasionally, for example:
- above-normal rain in Cavite in September 2026;
- dry conditions likely in Quezon by end-October, from Advisory No. 5, after the issue date.

The August 2026 SW-monsoon and typhoon damage (NDRRMC: more than PHP 2.2 billion in agricultural damage across several regions, CALABARZON included) is **not** province-specific. No local drought impact is assumed anywhere in E65.

## 4. Controlled evaluation

Same 10 E57 origins, 50 rows (18 HIGH), T43 labels, issue-date rule and E56 search. Sources: `tables/r3_metrics_50rows.csv`, `r3_paired_vs_A.csv`, `out/r3_evaluation.json`.

Arm A reproduces the sealed E57 E56 forecasts exactly (max difference 0).

| Model | Acc | Bal acc | HIGH recall | False alarms | Missed HIGH | Brier | Onsets | Rising | Quarters ≥ 0.75 |
|---|---|---|---|---|---|---|---|---|---|
| A frozen E56 | 0.72 | 0.684 | 0.556 | 6 | 8 | 0.214 | 3/10 | 6/18 | 6 |
| B1 ENSO intensity corrected | 0.72 | 0.684 | 0.556 | 6 | 8 | 0.213 | 3/10 | 6/18 | 6 |
| B3 PAGASA status added | 0.74 | 0.700 | 0.556 | 5 | 8 | 0.214 | 3/10 | 6/18 | 7 |
| B2 = B1 + B3 | 0.74 | 0.700 | 0.556 | 5 | 8 | 0.213 | 3/10 | 6/18 | 7 |
| C climate removed | 0.72 | 0.684 | 0.556 | 6 | 8 | 0.223 | 3/10 | 6/18 | 6 |
| D1 PAGASA El Niño rule | 0.64 | 0.561 | 0.278 | 5 | 13 | 0.360 | 4/10 | 2/18 | 5 |
| D2 CPI projection only | 0.74 | 0.748 | 0.778 | 9 | 4 | 0.188 | 7/10 | 7/18 | 7 |
| Persistence | 0.56 | 0.535 | 0.444 | 12 | 10 | 0.440 | 0/10 | 5/18 | 3 |
| Majority (as-of) | 0.64 | 0.500 | 0.000 | 0 | 18 | 0.360 | 0/10 | 0/18 | 5 |

**Paired Brier versus A** (quarter-cluster 95% CI and quarter sign test):

| Arm | Difference | 95% CI | Quarter wins (of 10) | p | Rows changed |
|---|---|---|---|---|---|
| B1 | −0.0011 | [−0.0039, +0.0006] | 7 | 0.17 | 0 |
| B3 | +0.0001 | [−0.0041, +0.0041] | 6 | 0.38 | 1 |
| B2 | −0.0011 | [−0.0042, +0.0009] | 5 | 0.62 | 1 |
| C | +0.0093 | [−0.0023, +0.0228] | 3 | 0.95 | 0 |
| D2 | −0.026 | [−0.108, +0.034] | 4 | 0.83 | 9 |

- B3's and B2's single changed row is Batangas 2025-Q3 (LOW observed, A 0.544 → 0.496).
- **No arm improves on A by the pre-registered rule.** Persistence and majority are significantly worse than A.

**El Niño issue rows** (D1 = 1: targets 2024-Q2 and 2024-Q3, 10 rows, 5 HIGH; `r3_metrics_el_nino_issue_rows.csv`):

| Model | Accuracy | Brier |
|---|---|---|
| A | 0.40 | 0.354 |
| B arms | 0.40 | 0.348–0.361 |
| D1 (El Niño rule) | 0.50 | 0.50 |
| D2 (CPI projection) | 0.80 | 0.164 |

Two quarters are too few to conclude anything. A's misses in 2024-Q2 are the stale-hunger case (E58/E59).

**Exploratory forward what-ifs** (`tables/r3_forward_whatif.csv`; not sealed or served):

| Target | A | B1 | B2 | B3 | C |
|---|---|---|---|---|---|
| 2027-Q1 | 0.043–0.146 | 0.041–0.140 | 0.041–0.142 | 0.042–0.143 | 0.041–0.129 |
| 2026-Q4 | 0.005–0.285 | the same | 0.005–0.286 | 0.005–0.286 | 0.007–0.102 |

Under B1–B3, El Niño information does not raise either forecast. With one El Niño episode in the training window, the price trees never select it.

**Disclosed limits:**
- ONI is the 2026-09-09 vintage for every quarter.
- The PAGASA status for 2022-04-01..2023-01-01 is inferred continuity.
- No historical PAGASA rainfall or drought outlook series was available, so none was used. No later-published information was substituted.

## 5. Can the target represent climate-related food stress?

Source: `tables/r4_low_label_checks.csv`, `out/r4_target_check.json`; 105 labelled province-quarters, 2021-Q2..2026-Q3.

| Condition | Rows | T43 LOW |
|---|---|---|
| Regional hunger > 11.3% | 70 | 47 (67%) |
| Hunger ≥ 20% | 25 | 16 (64%) |
| El Niño in the quarter or the one before (ONI) | 30 | 22 (73%) |
| PAGASA El Niño Alert/Advisory at quarter start | 25 | 18 (72%) |
| Provincial palay or corn YoY ≤ −10% | 55 | 45 (82%) |
| Hunger > 11.3% and a production drop | 38 | 28 (74%) |
| Hunger > 11.3% and headline inflation > 4% | 31 | 24 (77%) |
| Hunger > 11.3% and food YoY ≥ 4% but under the province threshold | 10 | 10 (100%) |

- **When hunger > 11.3%, T43 equals the price condition in 70 of 70 rows.** Every 2024–2026 row is in that state. Above the line, the hunger level adds nothing (mean H: HIGH 19.8 vs LOW 18.4, p = 0.11).
- **The only El Niño in the window** (2023-Q3..2024-Q1) had food YoY of 4.5–9.9% in 2023-Q3. The rows were LOW because hunger was 10.3%, below the line. Drought, production losses or a hunger jump cannot make T43 HIGH unless provincial food CPI crosses its threshold.
- **Verified conclusion:** T43 measures price-linked food stress under high hunger. It does **not** measure climate-related food stress, production shortfalls or affordability.
- **Labels and thresholds were not changed.**

**Proposal (exploratory, separately named, not a target, not validated, not served): CRFS-X, "Climate-related food-stress watch".**
- Components:
  - hazard: a PAGASA El Niño Advisory in force on the issue date;
  - household stress: latest posted regional hunger above 11.3%;
  - local exposure: latest provincial palay or corn YoY ≤ −10%. This component is noisy; the long-term aim is PAGASA provincial dry-spell or drought listings.
- **For 2026-Q4 and 2027-Q1, all five provinces would be "CLIMATE WATCH"** (`tables/r4_crfs_x_exploratory.csv`). Four (2026-Q4) and three (2027-Q1) also have a production drop.
- It would need a provincial outcome (CBMS/FIES) and prospective scoring before any claim.

## 6. Dashboard (backend text only; no UI element, colour or legend changed; horizon unchanged)

**E56/E58 mode, 2027-Q1 issued forecast:**
- `summary.caveat`, and therefore `summary.sentence`, now ends with:
  - the PAGASA statement in force before the issue date (2026-09-23 Climate Advisory);
  - "This is not a model input";
  - the facts that ENSO enters only the hunger part and the price part projects flat prices, with no rainfall or drought data;
  - the ENSO counterfactual (at most about 1 point);
  - "A LOW score is therefore not evidence that the El Niño poses no food risk";
  - the 2026-10-07 advisory, labelled "published after the issue date".
- The Climate Stress `evidenceNote` adds:
  - the PAGASA status on the issue date;
  - "not a model input";
  - that the ENSO code acts in the hunger part (90% → 96%), which the bars do not show;
  - the 2026-09-09 typhoon-track truncation.

**E56/E58 mode, 2026-Q4 earlier forecast:** the same, with the Advisory No. 1 status known on 07-01. The model saw "neutral; La Niña".

**D-E65-1 (fixed): the `/provinces` indicator horizon for 2026-Q3 and 2026-Q4 said "issued 2026-10-01".** It now names each estimate's own issue date: 2026-04-01 back-test, 2026-07-01 earlier forecast.

**Unchanged:**
- **Production default E38:** no climate input, and the card already says "no input for this factor". Its scores are HIGH; no text was added.
- **Back-tests:** no claim is added, because E65 did not verify them.
- **Climate card "no_effect" at 2027-Q1:** the recorded price-tree climate effect is ±0.046 log-odds, which rounds to 0%. This is existing behaviour; the new note explains where the ENSO effect sits.

## 7. Files and tests changed

**New (E65, untracked):**
- `PROTOCOL.md`, `runner/PROTOCOL_SHA256.txt`, `runner/PROTOCOL_FROZEN_AT.txt`;
- `sources/SOURCES.md` and `sources/pagasa_pdfs/` (5 PAGASA advisories and their text);
- `runner/e65_lib.py`, `r1_trace.py`, `r2_climate_audit.py`, `r3_evaluate.py`, `r4_target_check.py`;
- `tables/*` and `out/*` (including the console logs);
- this report.

**Backend:**
- `backend/app/ml/inference/enso_context.py` (new): the dated PAGASA timeline and the E65-verified ENSO facts.
- `backend/app/services/dashboard.py`: E65 hunks only — the import, `indicator_for` horizon (D-E65-1), `_with_enso`, and the caveat/sentence append. The same file also has **another session's uncommitted E64 hunks**, which E65 did not touch.
- `backend/tests/integration/test_e65_el_nino_audit.py` (new, 6 tests).

**Test results:**
- Full backend suite before the last text move: 452 passed, 18 skipped, 1 failed (`test_e61…endswith(caveat)`). The failure was fixed by moving the ENSO text into the caveat.
- After the fix:
  - E61 + E62 + E65 tests: 27 passed;
  - all dashboard, explainability and E56–E65 test files: 90 passed, 11 skipped.
- The full suite was not re-run after that last edit (it takes 94 minutes).

**Frozen artifacts:** E38 and E56–E62 folders, `backend/data/e56` and `backend/data/e58` are clean against HEAD. The sealed E57/E58 hashes are verified. The production model is not switched.

## 8. Remaining limitations

1. **No provincial food-insecurity outcome** (CBMS/FIES), so climate-related food stress cannot be validated.
2. **One El Niño episode (2023–24) in the 2021–2026 window.** No model trained here can learn an El Niño price effect.
3. **No in-window provincial rainfall or drought series**, and no machine-readable archive of PAGASA outlooks.
4. **ONI vintages and IBTrACS provisional tracks are not reproducible as of past issue dates.** The 2026-Q3 typhoon count is truncated at 09-09.
5. **The PAGASA status for 2022 is inferred continuity**, and some press-release IDs are missing from the archive list.
6. **The flat-price projection (m = 0)** ignores any expected El Niño price rise by design.
7. **Configuration switching between origins (E62 W3)** caused the 2026-Q4 dip.
8. **All results are development evidence.** The first independent evidence will be the 2026-Q4 and 2027-Q1 outcomes, scored against the frozen forecasts.

## 9. Recommendation

**The low 2026-Q4 and 2027-Q1 values require a warning. They cannot be interpreted as low El Niño food risk.**
- **Verified:** they follow correctly from the observed PSA CPI. Food inflation is far below the province thresholds, and headline inflation above food inflation counts as relief under T43. The model has no material channel for the approaching El Niño.
- **Hypothesis, not tested:** an El Niño-driven food-price rise could push the observed 2027-Q1 label to HIGH, and the model would not anticipate it. The 2024 history shows rice-led price episodes the model missed (E58), but they cannot be attributed to ENSO from this data.

**Steps:**
- Keep E38 as the production default and E58 experimental.
- Keep the frozen forecasts and score them prospectively.
- Show the new warning text.
- Ask the adviser whether to pre-register, before the 2027-01-01 origin, either a forward-looking climate input (the PAGASA status or strength outlook, where an archive exists) or the separate exploratory CRFS-X watch.
- Do not raise the forecast to HIGH by hand.

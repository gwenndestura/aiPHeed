# Final aiPHeed system selection and integration audit

Prepared 2026-10-27 on branch `aiPHeed/final-architecture` (local only). The audit starts from commit `2e503ac`.

**What was and was not changed.**
- Nothing was merged, pushed or deployed.
- No served file, model, frozen artefact or seal was changed.
- The only new files are in this folder, plus a short erratum in `DASHBOARD_SELECTION_REPORT.md` (§14).
- P0H4 stayed served throughout.

**Evidence labels used below:**

| Label | Meaning |
|---|---|
| **V** | Verified in this audit, from code, data or a live API call |
| **D** | Development evidence: historical walk-forward results on quarters that earlier designs saw |
| **R** | Recommendation |
| **A** | Assumption |

## 1. Executive recommendation

**The system is coherent at the model level, but not yet at the presentation level.** The province forecasts the dashboard serves are exactly the frozen P0H4 export (V: 60/60 rows match). P0H4 is the right model to keep serving now. Several surfaces around it still describe earlier systems. Fix five of them before the next release:

1. **Downloadable report (blocking):** it shows P0H4's probabilities but calls them "FIRI v2, a proxy composite, not a probability." It also says the bars are "exact shares of the index" and leaves 2025-Q2/Q3 blank although the dashboard shows them.
2. **LGU map colours:** the province 0.50 HIGH cut-off is applied to an LGU priority index that has already been scaled down. In 2025-Q2 four provinces are HIGH but only 1 of 142 LGUs is coloured HIGH.
3. **News timing notes:** they describe FIRI's two-quarter timing ("two-quarter-ahead forecast issued 2026-07-01") beside P0H4's Lead-1 forecast issued 2026-10-01. They also say "validated by rule R1.1" for articles chosen by classifier v2.
4. **Employment bar:** Employment is the largest bar in many forecasts (Quezon 2026-Q4: 73%, "protective") while the evidence line says unemployment rose. E1 is a documented calendar-time confound (§9.2).
5. **Mislabelled history:** the quarter list hides the 2023-Q1–2024-Q1 Lead-1 backtests with a FIRI-era reason. The timeseries labels those backtests `isForecast: true`, and `/forecast` reports a stale `verificationDate`.

**News finding (new, decisive):** news helps the served model only through the two GDELT price-news columns, at Lead 1 (§6). FSSI-v3, the XLM-R index of Objective 1, has no effect on P0H4: removing it changes the Brier score by 2×10⁻⁸. The dashboard's "News signals" bar is therefore GDELT, not the article list shown beside it.

## 2. Current system (V)

| Item | Value |
|---|---|
| Branch / commit | `aiPHeed/final-architecture` @ `2e503ac` (local only). P0H4's export is also on pushed `aiPHeed/lead2-optimization` @ `a1ce8ce` |
| Working tree | Untracked and preserved: E114 GDELT files, `docs/aiPHeed_Complete_System_Guide.docx`, `node_modules/`. Nothing else uncommitted before this audit |
| Serving mode | `AIPHEED_LEAD2_MODEL=thesis`, `AIPHEED_STRICT_MODEL=1` (`.claude/launch.json`, `backend/Dockerfile`). `ch1_system.active()` is true by default (`AIPHEED_MAP_MODEL` unset = `ch1`), so thesis mode serves the Chapter I forecast instead of FIRI v2 (`dashboard._province_forecasts_cached`) |
| Served model | **P0H4** = π_H4 (latest SWS Balance Luzon reading, pooled-area σ) × π_P (one LightGBM across leads on the price condition) |
| Served artefact | `backend/data/ch1_engine/rows.csv` (95 rows, 2023-Q1..2027-Q3), `evaluation.json`. Identical to `a1ce8ce` except three added `avail_*` flag columns (V: all 38 original columns equal) |
| Seals (unchanged) | P0H4 `a498b5ef` (`LEAD2_OPTIMIZATION/out/sealed_prospective_P0H4.csv`); S3 `cdf001f2` (`DASHBOARD_SELECTION/out`); UNI-FINAL `fcc4130d`; FIRI v2 forecast rows in `backend/data/thesis/firi2_history.csv` |
| main | `0239273` serves FIRI v2 (no `ch1_system.py` on main) |
| Deployment | Render/Vercel not checked (no access in this audit; A: it runs whatever branch was last deployed, see memory 10-21) |

**Prediction path traced (V):**

```
data inputs
  → U.stack (12 families + lead + world prices, issue-date cut-offs)
  → LightGBM π_P, refitted per issue date
  → × π_H4
  → rows.csv
  → ch1_system.province_rows
  → dashboard /provinces, /forecast, /forecast/timeseries, /explainability, /report/data,
    /provinces/{id}/municipalities, /final/risk/*
  → React (queries.ts → adapters.ts → PhilippineMap / LeftPanel / ForecastHistoryModal / AboutModal)
```

**What the frontend calls (V):**
- `/config`, `/quarters`, `/provinces`, `/provinces/{id}/municipalities`, `/forecast`, `/forecast/timeseries`, `/explainability`, `/news`, `/report/data`, `/search`;
- `/final/overview`, `/final/evaluation`, `/final/risk/evaluation`, `/final/risk/rows`, `/final/archive`;
- auth and admin routes.

It does **not** call `/ranking`, `/final/news`, `/lead2/*`, `/simple/*` or `/e107`–`/e113`. Those experimental read-only routes are still publicly mounted (`app/api/router.py`).

## 3. Final component-selection matrix

| Component | Recommended now | Reason | Evidence | Remaining limitation |
|---|---|---|---|---|
| Dashboard forecasting model | **P0H4 (keep)** | Reliable at Lead 1 (59/70 = 0.843, Brier 0.132); best Lead-2 probabilities (Brier 0.194); sealed; served values verified | `DASHBOARD_SELECTION` §3; `ch1_engine/rows.csv`; §2 here | Significantly worse than the per-lead CH1-LGBM at Lead 1 (Brier +0.045, p .027). It is a hybrid, not one LightGBM. It over-predicts low-to-moderate risk (§8) |
| Experimental thesis model | **S3** (one LightGBM, `FINAL_ARCHITECTURE` candidate C) | Fits the one-model wording of SOP 2/3. Lead 1 0.857, Brier 0.112, not significantly different from P0H4 | `DASHBOARD_SELECTION` §3/§8; seal `cdf001f2` | Its explanation needs the structural price offset in Market. Weaker at Leads 2–3 |
| News display feed | **v3 pipeline, province-attributed subset (keep, fix text)**. This is already what thesis mode shows, via `dashboard._news_pool_v3` | Real, dated, de-duplicated, 98.6% name a CALABARZON place; 296 articles 2021–2026 | §5.1 | Precision about 0.61 on displayed headlines (11/18 sampled; rainfall alerts are the main false positives). Links are Google News redirects. Timing notes are wrong (§5.2) |
| `final_engine` feed (`/final/news`, 1,043 items) | **Not displayed; keep as research only** | Not called by the frontend; only 227 items province-attributed; 2025–26 only | §5.3 | My earlier report called it the "current dashboard feed". Corrected in §14 |
| Model news pipeline | **v3 classifier v2 + syndication de-duplication (keep)** | Only one news pipeline exists in the code (`backend/app/news/*` is identical on main and current) | §5 | Recall 0.22 [0.15, 0.38]; preliminary until a human annotator labels the sample |
| NLP classifier | **Classifier v2, labelled "AI-evaluated, preliminary"** | Precision 0.63 [0.51, 0.76] | `out/news_scores.json` | Weak market trigger (precision 0.5; type-correct 1/10). No human labels yet |
| XLM-R / FSSI-v3 | **Keep as computed and displayed context. Do not claim it drives forecasts.** | Implements Objective 1 | §6: **zero effect on P0H4** (ΔBrier 2×10⁻⁸); 17–40% coverage | N1 is NaN in 83% of Lead-2 stacked rows |
| BERTopic | **Keep for topic labels in descriptive news text only** | Objective 1 ("latent risk patterns") | `thesis_system.news_evidence`, `app/ml/nlp/topic_model.py`; not in P0H4 or S3 inputs (V) | Never a predictor. Must not be described as one |
| GDELT price-news columns (`G_pri_yoy`, `NG_gap_price`) | **Keep in the model; name them on the News bar** | The only news input with a measured effect | §6: Lead-1 Brier −0.011 [−0.024, −0.002], p .024 | National, machine-coded by GDELT, not by the thesis pipeline. The test is post hoc (pre-registered family test Holm .86) |
| Twelve indicator families | **All 12 stay as inputs. Report contributions as measured, not as equal shares.** | Methodology requires the 12; ablations measure each | §7 | Only A1 (market) is clearly needed. C1 and C2 have exactly 0 effect. E1 is confounded |
| Risk probability and threshold | **P0H4 probability, HIGH ≥ 0.50 (fixed before scoring)**, named "forecast probability of HIGH risk under the Chapter I proxy definition" | Threshold not tuned (`PROTOCOL_LEAD2.md` "Decision rule") | §8 | Over-predicts at 0.2–0.4 (mean 0.30 vs observed 0.14). Not a measured hunger rate |
| Forecast horizon | **Lead 1 reliable; Lead 2 shown as experimental; Leads 3–4 not shown on the map** | R1–R7 pass at Lead 1 only | `evaluation.json` `reliable_max_lead = 1` | The dashboard opens on 2027-Q1 (Lead 2, experimental) by default (§8) |
| Trigger explanations | **P0H4 8-row relative-influence bars**, after the Employment and News note fixes | Reproducible SHAP of π_P; no hidden "other"; hunger multiplier stated | §9 | Employment direction is a confound. The "News" bar is GDELT. Only the price part is explained |
| Province forecasts | **P0H4 rows as served** | 60/60 match the export | §2 | One regional hunger value is shared by all five provinces |
| LGU rankings | **Keep as a within-province priority ranking; fix the colour band** | 142 LGUs, contiguous ranks, no ties, reproducible sha | §10 | HIGH/LOW band misapplied. Lucena uses an unverified substitute and ranks 1st in Quezon. No municipal validation |
| Forecast archive | **`/final/risk/rows` (P0H4, 95 rows) + `/final/archive` (FIL-OA regional hunger, labelled)** | Issue dates, data cut-offs and observed outcomes per row | §11 | Rows carry no model-version or seal field |
| Data-quality checks | **Keep the strict start-up check + `limitedSignal`; fix the `avail_*` flags** | Strict mode refuses to start without scored news (`main.py`) | §11 | The `avail_news` flag is 1 when only GDELT exists, so FSSI absence is invisible |
| Backend integration | **Thesis + ch1 mode (keep); fix the five stale surfaces** | §12 | §12 | Experimental routes still publicly mounted |
| Frontend integration | **No design change.** Text and data fixes only, from the backend | Hard rule: no colour/palette/legend changes | §12 | `ForecastHistoryModal` can show Lead 3–4 rows; check the labels before release |

## 4. Thesis objectives and SOP traceability (Chapter I §1.3–1.7)

**Status levels:**
- I = implemented;
- C = functionally correct (tested);
- E = predictive evidence;
- R = real-world validity.

| Requirement (Chapter I) | Existing implementation | Evidence of success | Remaining gap | Recommended component |
|---|---|---|---|---|
| **SOP 1 / H1.** Variables most predictive, via SHAP. H1: FSSI and food CPI deviation not among the strongest | P0H4 SHAP of π_P (8 rows) + ablations | I, C, E: food CPI deviation (A1) is the strongest (removal: Lead-1 accuracy 0.829 → 0.700, Holm 0.00). FSSI has zero effect | **H1 rejected for food CPI deviation, not rejected for FSSI.** E1's share is a confound | P0H4 bars + ablation table (§7) |
| **SOP 2 / H2 / Obj 2-V.** Furthest reliable lead, walk-forward | Stacked walk-forward, R1–R7 rule | I, C, E (D): Lead 1 reliable; Leads 2–15 fail | No untouched outcomes; prospective seals pending (SWS 2026-Q4, about Jan 2027) | Lead 1 only |
| **Obj 2 I–IV.** Accuracy, precision/recall, F1, AUC | `DASHBOARD_SELECTION/runner/compare.py` | Lead 1 P0H4: 0.843; P 0.69; R 11/17; F1 0.67; AUC 0.87 | – | Report as is |
| **SOP 3 / H3 / Obj 4.** Combined LightGBM vs persistence, 3 logistic variants, 2 single-source LightGBMs | `FINAL_VERIFICATION` comparators | E (D): beats persistence, LR-COMB/GOV/NLP and LGBM-NLP. Does **not** beat LGBM-GOV (0.914; Brier p .027 vs P0H4) | **H3 not rejected** against the government-only LightGBM | State it as a finding |
| **SOP 4 / H4 / Obj 3.** LGU rankings from validated province forecasts with poverty and density | `municipality_summary`, 142 LGUs | I, C (ranks reproducible). R: not tested | Post-survey not run; colour band misapplied; Lucena substitute unverified | Priority ranking (§10) |
| **Obj 1.** XLM-R + BERTopic two-tier pipeline → FSSI and latent patterns | `app/news/pipeline_v3`, `topic_model.py` | I, C: runs; strict mode checks the scores. Classifier precision 0.63, recall 0.22 (preliminary) | FSSI has no forecast effect; coverage low; no human labels | Keep as context; disclose |
| **SOP 5 / H5 / Obj 5.** Dashboard, ISO/IEC 25010 evaluation by DA IV-A, NNS face validity | Dashboard served locally | I, C (864 backend tests passed on this branch, 10-27) | **ISO evaluation not run. NNS face validity not done formally.** Report mislabelled (§12) | Fix §12 items, then evaluate |
| **Scope §1.7.** SWS + PSA determine risk; LGU estimates not official; flag limited news coverage | T43c target; `LGU_BASIS`; `limitedSignal` | I, C | Forecasts **price-pressure-conditioned regional hunger risk**, not measured provincial food insecurity | Keep "proxy definition" wording |
| **Scope.** PDF report with scores, SHAP drivers, metrics, data sufficiency | `/report/data` | **Fails (V):** describes FIRI v2 | Blocking | Fix 1 (§13) |

**Does the system forecast food-insecurity risk rather than only price pressure?** Partly.
- The label needs regional hunger > 11.3% AND provincial price pressure.
- Provinces differ only through prices.
- The hunger part is the latest SWS reading, so it cannot anticipate a new surge.
- Since 2023-Q4 the label equals the price condition in 80–92% of rows (earlier audits).

## 5. News display

### 5.1 What the dashboard actually shows (V)

In thesis mode, `/api/v1/news` builds its feed from `dashboard._news_pool_v3()`. That is `pipeline_v3.admitted()` restricted to province-attributed articles: 296 of the 695 admitted, 2021-Q1 to 2026-Q4.

Check against the ten required properties:

| # | Requirement | Status |
|---|---|---|
| 1 | Genuine, traceable articles | ✓ 23 outlets: inquirer 140, GMA 135, da.gov.ph 85, MB 80… |
| 2 | Original URL and publication date stored | **Partial:** every link is a Google News RSS redirect (100%), not the publisher URL; `published_ph` present for 100% |
| 3 | Publication vs retrieval time | ✓ `published_ph` and `first_seen_at` kept; 99.9% collected retrospectively, and the feed note says so |
| 4 | No duplicates | ✓ 0 duplicate keys, 0 duplicate normalised titles |
| 5 | CALABARZON vs other regions | ✓ 98.6% of displayed titles name a CALABARZON place |
| 6 | Direct vs indirect | **✗** categories are the five triggers only. Direct reports are rare: 1/126 in the review |
| 7 | Categories separated | Partial: market, climate, fish_kill, employment, ofw_remittance. No assistance or shortage category |
| 8 | Not every disaster or price rise treated as food insecurity | Partial: rainfall alerts and weather forecasts pass as "climate" (5 of the 7 false positives in the displayed sample) |
| 9 | No fabricated summaries, locations, dates or categories | ✓ headlines only, excerpt is a fixed context note (`FE.news_context_note`), dates from the publisher |
| 10 | Unavailable or low-quality sources | ✓ window extends up to 3 quarters back with a note when fewer than 5 articles |

**Displayed-subset precision:** 11/18 = 0.61 (sampled; stratified by trigger, so indicative only).

### 5.2 Defects in the news panel (V)

- **Timing note uses the FIRI rule.** `_lead2_news_evidence` applies FIRI's "news of q−2, issued day 1 of q−1" rule.
  - For P0H4's 2026-Q4 Lead-1 forecast (issued 2026-10-01) it shows 2026-Q2 news and says "two-quarter-ahead forecast … issued 2026-07-01".
  - For the 2025-Q2 backtest it says "made as of 2025-01-01 with 2024-Q4 news", but P0H4's forecast was made 2025-04-01.
  - No leakage: the shown window is earlier than the true cut-off. The text is wrong, not the data.
- **Wrong validation label.** `feedNote` says "validated by rule R1.1" for articles admitted by classifier v2 (E60).

### 5.3 The `final_engine` feed

Served at `/api/v1/final/news`, never called by the frontend:
- 1,043 items, 2025–26 only; 227 province-attributed;
- has categories and an event/forecast "kind";
- F1 about 0.54 in the review (indicative).

**Selection:** the dashboard keeps the v3 feed; the `final_engine` feed stays research-only. A later improvement could carry its "kind" (event vs warning) into the v3 display. It must stay separate from model inputs.

## 6. Should news be a forecasting input? (new matched experiment, V)

**Script:** `runner/news_p0h4.py`.
- **Rows:** P0H4's own 70 Lead-1 and 65 Lead-2 rows, same origins and cut-offs.
- **Price part:** refitted at every issue date; the rerun reproduces the served π_P to 4.9×10⁻⁷.
- **Placebo:** news columns permuted across issue dates within province and lead (20 shuffles, seed 2040).

| Lead | Arm | Accuracy | Balanced | Precision | Recall | Onsets | Brier |
|---|---|---|---|---|---|---|---|
| 1 | **P0H4 with news (served)** | **59/70 = 0.843** | 0.776 | 0.69 | **11/17** | **4/10** | **0.1322** |
| 1 | P0H4 without news | 56/70 = 0.800 | 0.688 | 0.62 | 8/17 | 1/10 | 0.1436 |
| 1 | P0H4 without FSSI-v3 only | 59/70 = 0.843 | – | – | 11/17 | 4/10 | 0.1322 (Δ 2×10⁻⁸) |
| 1 | P0H4 without GDELT only | 56/70 = 0.800 | – | – | 8/17 | 1/10 | 0.1436 |
| 1 | Shuffled news (mean of 20) | 0.813 | – | – | 0.50 | – | 0.1395 (range 0.1318–0.1439) |
| 1 | always-LOW / PERSIST-SI / climatology | 0.757 / 0.743 / 0.757 | 0.50 / 0.67 / 0.50 | – | 0 / 9 / 0 of 17 | 0 / 2 / 0 | 0.243 / 0.257 / 0.201 |
| 2 | P0H4 with news (served) | 50/65 = 0.769 | 0.635 | 0.60 | 6/17 | 0/10 | 0.1944 |
| 2 | P0H4 without news | 51/65 = 0.785 | 0.645 | 0.67 | 6/17 | 0/10 | 0.1901 |
| 2 | Shuffled news (mean of 20) | 0.784 | – | – | 0.35 | – | 0.1914 |

**Tests:**

| Lead | With − without news, Brier [90% CI] | p | Holm (2 leads) | Placebo perm p |
|---|---|---|---|---|
| 1 | −0.0114 [−0.0235, −0.0016] | .024 | .048 | 0.05 (the minimum with 20 shuffles) |
| 2 | +0.0044 [−0.0009, +0.0097] | .18 | .18 | 0.95 |

At Lead 1 the class changes on 3 of 70 rows.

**Interpretation:**
- At Lead 1, news improves the served model, and **all of the gain comes from GDELT's national price-news volume**.
- FSSI-v3 (the thesis's XLM-R index) has no effect: LightGBM never splits on it in a way that changes a prediction.
- The test is post hoc. In the pre-registered 13-family test (LEAD2_OPTIMIZATION) the same news effect had Holm p .86. Treat it as **suggestive**.
- At Lead 2, news slightly hurts. Not significant.

**Decisions:**
- **Keep the GDELT columns as model inputs** (part of the 12-family N1 group).
- **Do not claim FSSI improves forecasts.**
- Keep FSSI and the article list as context. Re-test FSSI when coverage improves (N1 is non-missing in 0% of 2021, 35% of 2024 and 40% of 2026 rows).
- The "News signals" bar should say it reflects GDELT price-news volume, not the listed articles.

## 7. Indicator-family audit (V, D)

**Sources:** `LEAD2_OPTIMIZATION/out/family_inventory.txt`, `ablation_P0H0.json`, `BIAS_AUDIT`, §6 here.

**Ablation:** each family dropped from the P0 price model (× regional hunger); accuracy and ΔBrier (full − ablated) at Leads 1 / 2. A negative ΔBrier means the family helps.

| Family | Source, frequency, level | Coverage / availability at the issue date | Ablation L1 / L2 accuracy, ΔBrier, Holm | Concern |
|---|---|---|---|---|
| A1 food-price projection | PSA CPI, monthly, province | Months ≤ month 2 of t; 9% missing | **0.829→0.700 / 0.769→0.615; −0.058, Holm 0.00** | Target uses the same CPI: partly structural |
| A2 headline inflation | PSA CPI, monthly, province | 0% missing | 0.829→0.843; +0.001 | none |
| A3 rice wholesale | PSA, quarterly, province | t−1; 27% missing (pre-2022-Q2) | 0.829→0.800 / 0.769→0.723; −0.010 / −0.018 (Holm .07 at L2) | – |
| V1 poverty + density | PSA SAE 2021, POPCEN 2024, static | Static profile used at all origins (published 2025: mild look-ahead, disclosed) | 0.829→0.857; +0.003 | Acts as a province identifier |
| C1 PAGASA El Niño | Event, national | Strictly before O(t) | **exactly 0** | Never used |
| C2 typhoons | IBTrACS, province | 4% missing; NaN for 2026-Q3 | **exactly 0** | Never used |
| C3 palay/corn drop | PSA, quarterly | 22% missing | +0.008 (worse with it) | – |
| C4 fisheries | PSA, quarterly | 22% missing | −0.004 | – |
| E1 unemployment change | PSA LFS, national | 22% missing | −0.006 | **Calendar-time confound** (ρ +0.95 with time); direction not interpretable |
| E2 remittances | BSP, national | Available to the 2026-Q3 origin | −0.0001 | none |
| N1 news (FSSI-v3 + GDELT) | RSS + XLM-R; GDELT GKG | FSSI 83% missing; GDELT about 17% missing | −0.012 (Holm .86) / +0.005. §6: all from GDELT | FSSI zero effect |
| H1 regional hunger outlook | SWS BL, region | From 2021-Q3 | +0.006 / −0.009 | Also the π_H multiplier: hunger matters through the product, not the feature |

**Market dominance:**
- **Partly built into the target.** The label's price condition uses the same PSA CPI that A1 projects.
- **Also genuinely predictive.** Removing A1, A2 and A3 together cuts Lead-1 accuracy to 0.714 and raises Brier by 0.057 (`validation_ablations.json`).
- Both points must appear in the methodology and on the dashboard. The current `INDICATOR.caveat` says only "provinces differ only through food prices".

## 8. Probability, threshold and horizon policy (V, D)

**What the probability means.** It is P(HIGH under T43c) = P(regional hunger > 11.3%) × P(provincial price condition). It is not a measured provincial food-insecurity rate. The dashboard wording ("Food-insecurity risk (Chapter I definition): probability that the province is HIGH risk" plus the caveat) is accurate and should stay.

**Threshold.** 0.50, fixed before scoring as the approved dashboard rule (`PROTOCOL_LEAD2.md`); not tuned on the evaluation period.

**Calibration (P0H4, Lead 1):**

| Probability bin | Mean forecast | Observed HIGH rate | Rows |
|---|---|---|---|
| 0–0.2 | 0.10 | 0.00 | 24 |
| 0.2–0.4 | 0.30 | 0.14 | 22 |
| 0.4–0.5 | 0.43 | 0.38 | 8 |
| 0.5–0.6 | 0.56 | 0.64 | 11 |
| ≥ 0.6 | 0.68 | 0.80 | 5 |

- Overall mean forecast 0.316 vs observed 0.243.
- The forecast is ordered correctly but over-predicts low-to-moderate risk.
- S3 is better calibrated overall (0.241 vs 0.243).
- Disclose "approximately calibrated above 0.4; over-predicts below".

**Behaviour:**
- Leads differ: Lead 1 2026-Q4 vs Lead 2 2027-Q1 have different values and labels.
- The price LightGBM has monotone (increasing) constraints on `A1_food`, `A1_gap` and `A_mom` (`FINAL_UNIFIED_LGBM/runner/uni_lib.py` `MONO_UP`).
- Missing inputs are NaN (LightGBM default direction), never zero-filled.

**Horizon policy:**
- **Reliable:** Lead 1 only (the quarter now under way: 2026-Q4, issued 2026-10-01).
- **Experimental:** Lead 2 (2027-Q1), labelled on every province row (V).
- **Not shown on the map:** Leads 3–4 (V: 2027-Q2/Q3 return 404).

**Defect H-1.** `/quarters` sets `current = 2027-Q1`, so the dashboard opens on the experimental horizon. **R:** open on the Lead-1 quarter and keep 2027-Q1 one click away, labelled experimental. This is a backend default change and needs your approval.

## 9. Explanations

### 9.1 What the P0H4 bars are (V)

- They are SHAP (pred_contrib) of the LightGBM π_P, in log-odds, grouped into 8 rows: market, climate, fisheries, employment, remittance, poverty, news, regional-hunger indicator.
- They are rescaled to 100%, with no hidden "other" (`ch1_system.OTHER = ()`).
- The note states that the hunger multiplier and the horizon are not included, and that the bars are influence, not causes.
- They are reproducible: exported per row in `rows.csv`.

### 9.2 Credibility problems

| Problem | Evidence | Recommendation |
|---|---|---|
| **Employment confound** | E1 is national, ρ +0.95 with time, within-year AUC 0.35/0.76/0.17 (`BIAS_AUDIT`). It holds the second-largest mean \|SHAP\| (0.26). In Quezon 2026-Q4 it is 73% "protective" while the evidence line says unemployment rose 1.3 points | **Fix (text):** add a status note to the Employment bar: "follows the calendar trend in national unemployment; the direction is not interpretable". Alternative (Improve, needs an experiment): retrain without E1, or with E1 detrended |
| **News bar is GDELT** | §6 | **Fix (text):** the news bar's note names GDELT price-news volume and says the listed articles are not inputs |
| C1 / C2 always 0 | §7 | Already shown as "no effect" (V: `status: no_effect`) |
| S3 explanation incomplete | Tree SHAP omits the offset (Market about 2% vs ablation +0.083 Brier) | Build and test before S3 can be served |

### 9.3 `/ranking` (API only, not displayed)

`whyAboveNextLower` comes from the legacy E38 explainer (`dashboard._explainer()`), with features `rice_rel`, `news_n`, `D_last`, `H_margin`, `Dnow`. These belong to a different model.

**R:** in ch1 mode, compute the differences from the P0H4 SHAP rows, or omit the field. Optionally unmount the route.

## 10. LGU prioritisation (V)

| Check | Result |
|---|---|
| Coverage | 142/142 LGUs for every quarter tested (2025-Q2, 2026-Q4, 2027-Q1) |
| Method | Vulnerability = 0.6 × poverty_norm + 0.4 × density_norm (min-max within province); index = province probability × vulnerability; competition ranks on the unrounded index, ties by PSGC; `rankingRowsSha256` reported |
| Ranks | Contiguous within each province and 1–142 regionally; no ties in the quarters checked |
| Missing poverty | Lucena only. It uses an unverified province substitute (16.8%) and is **rank 1 in Quezon** in all three quarters checked. E99 (`e99-final-improvement`) found its own estimate is about 6.5%, which would move it to about rank 14 |
| **Defect L-1: colour band** | The LGU `riskLevel` applies the province 0.50 cut-off to the index (`dashboard.py` ~l.892), and the index ≤ the province probability. In 2025-Q2 four provinces are HIGH but 141/142 LGUs are LOW. The map (`PhilippineMap.tsx` l.272) colours LGUs by this level |
| Mislabelled source mode | `provinceEstimateSource.mode` is "THESIS_LEAD2_BACKTEST" / "…EARLIER_FORECAST" for P0H4 Lead-1 quarters |
| Validation | None against municipal outcomes; DA post-survey (H4) not run |

**R (Fix L-1, backend only, no colour change):** give each LGU its province's HIGH/LOW level and keep the index for ordering only. The map then shows the province class, and the rank shows priority within it.
- The tooltip and legend text stay "Risk Level".
- Alternative: show LGUs in a neutral rank style. That would be a design change, so it is not proposed.

**R (Lucena):** flag it as "poverty value substituted, rank uncertain", or exclude it from the rank until a verified value exists. Needs your decision.

**Presentation:** "Priority ranking within the province, from the province forecast weighted by poverty and density. Not a municipal forecast or an official classification."

## 11. Archive and data quality (V)

**Archive:**
- `/final/risk/rows` serves all 95 P0H4 rows with:
  - issue date;
  - newest SWS quarter and publication date;
  - newest PSA month and latest news time;
  - lead and observed outcome.
- **Gap:** no model-version or seal field. **R:** add `model = "P0H4"` and `seal = "a498b5ef"` for the 2026-10-01 rows.
- `/final/archive` is the FIL-OA regional hunger archive, labelled by model; it is a separate product.

**Strict mode.** It refuses to start without stored XLM-R scores for every admitted article (`main.py`; Dockerfile comment).

**`avail_*` flags (Defect Q-1).** They are 1.0 for every group and quarter:
- `avail_news` is 1 whenever a GDELT column exists, even with FSSI missing (83% of rows);
- `avail_climate` is 1 even when C2 is NaN (2026-Q3).

**R:** report availability per column, so the panel can say "FSSI: too few articles".

**Limited signal.** `limitedSignal` (fewer than 5 articles) is present; `articleCount` = 10 for Quezon 2027-Q1.

## 12. Backend and frontend integration findings (V)

| # | Finding | Where | Severity |
|---|---|---|---|
| I-1 | **Downloadable report describes FIRI v2 for P0H4 numbers**, calls the bars "exact shares of the index", says poverty/news/hunger "account for 0%" while listing them, blanks 2025-Q2/Q3, and cites the E63 reliability rule | `/report/data` (`app/services/report.py`, `report_data_e31.py`) | **Blocking** |
| I-2 | LGU HIGH/LOW band misapplied | `dashboard.municipality_summary` | High |
| I-3 | News timing note and "R1.1" label wrong for P0H4 | `dashboard._lead2_news_evidence`, `_e31_news` | Medium |
| I-4 | Quarter list hides 2023-Q1..2024-Q1 with a FIRI-era reason; timeseries marks those backtests `isForecast: true`; `/forecast` `verificationDate` 2026-07-01 (FIRI issue date) instead of 2026-10-01 | `dashboard` quarter list (`E41L2.candidate_quarters`), timeseries, forecast | Medium |
| I-5 | Default view is the experimental Lead-2 quarter | `/quarters` `current` | Medium (needs approval) |
| I-6 | Employment and News bar notes | `ch1_system.evidence_note` | Medium |
| I-7 | `/ranking` reasons from the legacy explainer | `dashboard.ranking` | Low (not displayed) |
| I-8 | Experimental routes (`/simple`, `/e107`–`/e113`, `/lead2`, `/fpp`, `/final/news`) publicly mounted | `api/router.py` | Low |
| I-9 | `evidenceStatus: "EXPERIMENTAL"` on Lead-1 rows contradicts "passed the reliability test" | `/provinces` | Low (not displayed) |
| I-10 | `avail_*` flags too coarse | `export_l2.py` | Low |

**Consistency checks that passed:**
- Displayed model version = forecast model (thesis + ch1). Old FIRI records are not mixed into province scores (`province_rows` returns `[]` where ch1 does not cover a quarter).
- All 142 LGUs handled.
- The news feed is not a model input (V: the dashboard pool is display only; the model reads `pipeline_v3` FSSI and GDELT through the experiment stack).

## 13. Implementation plan (nothing implemented; awaiting approval)

| # | Class | Problem | Evidence | Files | Correction | Test | Expected effect | Regression risk | Rollback |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Fix** | Report describes FIRI v2 (I-1) | §12 | `app/services/report.py`, `report_data_e31.py` | In thesis+ch1 mode, use `CH1.INDICATOR` text, SHAP wording, CH1 quarters (incl. 2025-Q2/Q3) and the R1–R7 rule | Integration test: report metadata, series and bar notes equal the `/forecast` and `/explainability` values for every quarter | The PDF matches the dashboard | Low; FIRI mode unaffected if gated on `CH1.active()` | `git revert` |
| 2 | **Fix** | LGU band (I-2) | §10 | `dashboard.municipality_summary` | `riskLevel` = province class; `riskIndex` for order | Unit test: every LGU level equals its province level; ranks unchanged | The map no longer shows HIGH provinces as all-LOW LGUs | Medium: map colours change; no palette change | revert |
| 3 | **Fix** | News timing / label text (I-3) | §5.2 | `dashboard._lead2_news_evidence`, `_e31_news` | In ch1 mode, the evidence window = quarter before P0H4's issue date (Lead 1: q−1, issued day 1 of q); label "classifier v2 (AI-evaluated)" | Test: for each served quarter, all listed articles are published before its issue date and the note names that date | Correct timing text | Low | revert |
| 4 | **Fix** | Quarter list, `isForecast`, `verificationDate` (I-4) | §12 | quarter list, timeseries, forecast | Derive from `CH1.rows()` in ch1 mode | Tests: quarters 2023-Q1..2027-Q1 available; backtests `isForecast=false`; `verificationDate` = issue date | History complete and labelled | Low | revert |
| 5 | **Fix (text)** | Employment and News bar notes (I-6) | §9.2, §6 | `ch1_system.evidence_note`, `plain_text.py`, `driverCopy.ts` text only | Confound note; "GDELT price-news volume" note | Snapshot tests on the notes | Honest explanations | Low | revert |
| 6 | **Fix** | Archive model/seal fields; `avail` per column (I-10, §11) | §11 | `export_l2.py` (new columns only; seal file untouched, its assert stays), `final.py` | Add `model`, `seal`; per-column availability | Seal byte-identical check (existing assert); API test | Traceability | Low | revert |
| 7 | **Defer/decide** | Default view on Lead 2 (I-5) | §8 | `/quarters` | Default to the Lead-1 quarter | Config test | Users land on the reliable forecast | Behaviour change | revert |
| 8 | **Decide** | Lucena substitute | §10 | `municipality_summary` | Flag or exclude | Test | Avoids a likely wrong rank 1 | Low | revert |
| 9 | **Fix (low)** | `/ranking` reasons, `evidenceStatus`, experimental routes (I-7–I-9) | §12 | `dashboard.ranking`, `router.py` | P0H4 SHAP or omit; status by lead; gate routes behind an env flag | API tests | API consistency | Low | revert |
| 10 | **Improve (experiment)** | E1 confound | §9.2 | experiment folder only | Pre-registered retrain without or with detrended E1; adopt only if Lead-1 Brier is not worse | Walk-forward + bootstrap | A cleaner explanation | Model change, so it needs a new seal | keep P0H4 |
| 11 | **Improve (experiment)** | Feed false positives (rainfall alerts) | §5.1 | display filter only | Exclude weather bulletins from the displayed feed | Before/after precision on the review sample | Cleaner feed | None to the model | revert |
| 12 | **Defer** | Human news annotation | §5 | `annotation/` (ready) | Second annotator labels 126 headlines | `score_news.py` κ | Real reliability figure | – | – |
| 13 | **Defer** | Replace P0H4 with S3 | `DASHBOARD_SELECTION` §8 | export + `ch1_system` | Only after your approval, the Market-offset attribution and prospective scoring of `a498b5ef` vs `cdf001f2` | Prospective Brier comparison, pre-fixed | One-model alignment | High | keep P0H4 |
| 14 | **Reject** | FIRI v2 / Main as the forecaster | Lead 2: 26/65 = 0.400, below always-LOW | – | Keep only as a descriptive index if wanted | – | – | – | – |
| 15 | **Reject** | Using `final_engine` categories as model inputs | Not tested; different corpus; 2025–26 only | – | – | – | – | – | – |

**Suggested order after approval:** 1 → 2 → 3 → 4 → 5 → 6. Then decide on 7 and 8. Run the full backend and frontend test suites after each fix.

## 14. Correction to `DASHBOARD_SELECTION_REPORT.md`

**What was wrong.** That report called `data/final_engine/news_events.csv` "the current branch's dashboard feed". It is served at `/api/v1/final/news`, which the frontend does not call. In thesis mode the dashboard news panel shows the v3 pipeline's province-attributed articles (`dashboard._news_pool_v3`).

**What changes as a result:**
- Verdict H in that report compared two classifiers correctly, but the "feed" is not what users see.
- The displayed feed's precision is about 0.61 on the sampled displayed headlines (§5.1).
- The statement "news improves forecasts in no candidate" is refined by §6: P0H4 gains at Lead 1 from GDELT (post hoc, suggestive). FSSI still shows no gain.

An erratum line has been added to that report.

## 15. Answers to the twelve questions

1. **Which model should power the dashboard now?** P0H4.
2. **Which model for the thesis methodology?** S3, the single LightGBM, as the method aligned with the one-model wording. Report P0H4 as the served hybrid and disclose that the per-lead government-only LightGBM is better at Lead 1 (H3 not rejected).
3. **Which news feed should be displayed?** The v3 province-attributed feed the dashboard already shows, with the timing and label text fixed and weather bulletins filtered out (after the experiment in item 11).
4. **Should news be a forecasting input now?**
   - GDELT price-news volume: yes, as it is now. It is the only news input with a measured (post hoc, suggestive) Lead-1 gain.
   - FSSI-v3: no claim of predictive value. It stays in the 12-family input set as specified and is shown as context.
5. **Which NLP components should remain?**
   - Classifier v2 relevance filter and syndication de-duplication, labelled preliminary until human annotation.
   - XLM-R intensity → FSSI-v3, as Objective 1 output and context.
   - BERTopic, for descriptive topic labels only.
6. **Which indicator families are used and supported?**
   - All 12 are inputs.
   - Supported by ablation: A1 (strongly), A3 (Lead 2, borderline) and the GDELT part of N1 (Lead 1, suggestive).
   - No effect: C1 and C2.
   - Weak or confounded: E1.
   - Static identifier: V1.
   - H1 matters through the hunger multiplier.
7. **Which explanation method?** P0H4's 8-row relative-influence bars, with the Employment-confound and GDELT notes added.
8. **Which horizon is reliable?** Lead 1 only (development evidence). Lead 2 is experimental.
9. **How should province risk and LGU prioritisation be presented?**
   - Province: "probability of HIGH risk under the Chapter I proxy definition (regional SWS hunger × provincial food-price pressure)", with the caveat.
   - LGU: "priority ranking within the province", coloured by the province's class (after Fix 2), never as a municipal forecast.
10. **What must be fixed before the next release?** Plan items 1–6, and decisions on 7 and 8.
11. **What evidence is needed before replacing the served model?**
    - Your approval;
    - S3's Market-offset attribution, built and tested;
    - prospective scoring of seals `a498b5ef` and `cdf001f2` on SWS 2026-Q4 and 2027-Q1, with the comparison rule fixed beforehand.
12. **Which changes first after approval?** Item 1 (report), then 2 (LGU band), then 3–4 (news timing and history labels).

## 16. Known limitations

- **Small sample:** 13–14 independent hunger outcomes; 2 hunger onsets.
- **No sub-regional outcome:** one regional hunger value shared by all provinces; no provincial or municipal food-insecurity outcome.
- **No independent test data:** all results are development evidence; no untouched test.
- **News review:** a single AI reviewer working from headlines; human labels pending.
- **Thesis evaluations not run:** ISO/IEC 25010 and the DA LGU post-survey.
- **Deployment state not checked:** the Render deployment was not inspected.

## 17. Reproduction

**Python:** `C:/Users/admin/aipheed/backend/venv/Scripts/python.exe`.

| Step | Command | Output |
|---|---|---|
| Live API checks | Start the `api` configuration in `.claude/launch.json` (thesis mode, port 8000), then query the endpoints in §2 | – |
| News ablation | From `FINAL_SYSTEM_SELECTION/runner`: `python news_p0h4.py nonews`, `python news_p0h4.py placebo 20`, `python news_p0h4.py report`, `python news_p0h4.py split` | `out/p0h4_nonews.csv`, `p0h4_placebo.csv`, `news_p0h4.json`, `p0h4_news_split.csv`, `news_p0h4_split.json` |
| News scores | From `backend/`: `python ../aipheed-backend-aligned/experiments/FINAL_SYSTEM_SELECTION/runner/score_news.py` | `out/news_scores.json` (reproduces precision 0.634, recall 0.220, F1 0.33, κ 0.95/0.99; adds human κ once `annotation/news_review_human.csv` exists) |
| Four-candidate metrics | `DASHBOARD_SELECTION/runner/compare.py`, `extras.py` | – |
| Family ablations | `LEAD2_OPTIMIZATION/out/ablation_P0H0.json`, `validation_ablations.json` | – |
| Human annotation package | `annotation/README_FOR_ANNOTATOR.md`, `NEWS_ANNOTATION_GUIDE.md`, `news_review_human_TEMPLATE.csv` (126 rows, reshuffled seed 2042, no pipeline labels) | – |

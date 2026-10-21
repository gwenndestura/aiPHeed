# E83 — Deep research, model reconstruction and system validation (technical report)

**Branch.** `e83-deep-research-reconstruction`, cut from `final-system-v2` (7774e30) on 2026-10-21. E76–E82 are not
merged (user decision).

**Evidence.**
- Protocol, frozen before any result: `PROTOCOL.md` (sha256 3dddb90f…, commit b560c8a).
- Deviations: `DEVIATIONS.md` (D1–D4).
- Final run: `runs/20261021T084802Z/` (`RESULTS.json`, `RESULTS_TABLES.md`, predictions and features per lead).

**How to read the labels.**
- **Verified** = checked against data or code in this run.
- **Measured** = an out-of-sample result on the 13 evaluated quarters.
- **Post-hoc** = an arm added after a result was seen (exploratory).
- **Unresolved** = still open.

---

## 1. Bottom line

1. **The mandatory goal is not met at Lead 2 or beyond.** (Measured.) No arm, pre-registered or post-hoc, reaches
   more than 75% accuracy at Lead 2 together with discrimination and a significant advantage over the baselines.
   - Best Lead-2 arm: S-SIM-THR, 0.708 on all rows (0.767 on its 60 issued rows), balanced accuracy 0.58, HIGH recall
     0.31.
   - Always-LOW scores 0.754 on the same rows.
   - The 80% target is not reached at Lead 2.
2. **Lead 1 is the longest lead with real skill.** (Measured.)
   - The pre-registered structural model S-SIM scores:
     - accuracy 0.846, balanced accuracy 0.751, HIGH recall 0.56, AUC 0.89, Brier 0.118;
     - the persistence baseline scores 0.723 / 0.627 / 0.44, Brier 0.277;
     - its Brier advantage is not significant with 13 quarters (Holm p = 0.105).
   - The post-hoc hybrid HYB-GBA-SIM meets every criterion at Lead 1 (0.877, balanced 0.834, recall 0.75,
     Holm p = 0.098). It was chosen after seeing results, so it stays exploratory until the sealed 2026-Q4 outcome is
     known.
3. **The approved target T43 has become a price-pressure label.** (Verified; `T43_VALIDITY_AUDIT.md`.)
   - Since 2023-Q4, hunger has been above 11.3% in 10 of 10 quarters, so T43 equals the provincial food-price
     condition on 100% of those rows.
   - Hunger and food inflation moved in opposite directions (r = −0.61).
   - This is the main scientific limitation, and it is not a modelling one.
4. **News does not add measurable predictive value.** (Measured.)
   - Lead text was recovered lawfully for 730 of 9,667 articles (87 of the 695 relevant ones).
   - Neither the lead-text features nor the de-duplicated event features improve the better models.
5. **The system is functional end to end.** (Verified.)
   - All 142 LGUs return a valid, labelled output.
   - The served explanations are exact decompositions of the served numbers (tested).
   - Explanations now lead with plain English and a DA action.
   - A monthly refresh job exists and never overwrites forecasts.
   - Tests: backend 542 + 12 new pass, frontend 74/74.

---

## 2. What was audited and preserved

- **Served thesis system (unchanged in method).**
  - Province risk = FIRI v2, an evidence-weighted composite of six domains.
  - The E56-TUNED LightGBM food-price-pressure forecast is one affordability indicator.
  - LGU values = the province estimate re-weighted by PSA 2021 SAE poverty (60%) and 2024 POPCEN density (40%).
  - No served artifact, threshold or record was changed. E83's selection rule keeps the served model because no
    arm passed.
- **Data layer reused.** E83 reuses the audited E41/E43 data layer: publication-timed CPI, SWS, PSA production, LFS,
  IBTrACS/ONI, BSP and rice-policy events. The protocol §3 timing table lists what is available at each origin.
  `DATA_DICTIONARY.md` documents 38 variables: source, geography, frequency, value at origin, transformation,
  expected sign, role, measured missingness and limitation.

## 3. Literature review → design (`LITERATURE_REVIEW.md`)

Published systems are the reference point:
- Balashankar et al. 2023, *Science Advances*;
- Andrée et al. 2020, World Bank;
- Westerveld et al. 2021;
- Busker et al. 2024;
- Foini et al. 2023.

They show that:
- persistence and seasonality are hard to beat;
- skill decays quickly with lead time;
- text helps only once it is turned into normalised, driver-specific event signals and tested by ablation.

These studies use thousands of unit-months. aiPHeed has 13 evaluable target quarters per lead and one hunger series.
That choice drove the design: structural models with few parameters, regularised learners, and in-origin thresholds.

## 4. News intelligence (Directive §6)

### 4.1 Lead text (`backend/app/news/lead_extractor.py`, `LEAD_TEXT_REPORT.md`)

- **Resolution.** Publisher URLs are resolved through the publisher's own sitemaps and WordPress search API, because
  Google News links are robots-disallowed.
- **Access rules:**
  - pages are fetched only where robots.txt allows this crawler and the AI-crawler tokens;
  - bot challenges are never bypassed;
  - requests are spaced 2.5 s apart per host;
  - every attempt is logged.
- **Storage.** Lead paragraphs (at most 1,200 characters) stay local and gitignored. A text-free status file is
  committed.

| Status | Articles |
|---|---|
| lead_ok | 730 (7.6%) |
| blocked (Inquirer family, BusinessMirror, UPLB — bot challenge) | 2,982 |
| robots_disallowed (GMA /news/story, Rappler for AI crawlers) | 1,812 |
| no_method (no article sitemap or search API, e.g. Philstar, MB, PNA, ABS-CBN, PIA, Manila Times with a 600 s crawl delay) | 3,687 |
| unresolved | 456 |

Recovered leads come mostly from DA, BusinessWorld, DSWD FO4A and SunStar, so they describe press releases more than
independent reporting.

### 4.2 Event features (`backend/app/news/events.py`)

- **Relevance:** classifier v2 mechanism phrases plus an off-topic filter.
- **Polarity:** adverse, improving, response or neutral. A 60-title spot check by the analyst agreed on about 85%.
  This is an AI-assisted check, not a human-validated annotation.
- **Event clusters:** semantic clusters of the same driver within 7 days, using multilingual MiniLM.
- **Normalisation and shrinkage:** rates per 100 collected articles (controls for corpus growth), shrinkage toward
  the region (κ = 5), and the quarter-to-quarter change.

### 4.3 Ablation A–F

The ablation uses the same rows, folds and metrics throughout (`RESULTS.json → news_ablation`).

**LightGBM (the better learner):**

| Lead | No news (A) | With event features (D) | Paired Brier gain from news | Sign-flip p |
|---|---|---|---|---|
| 1 | accuracy 0.867, Brier 0.076 | accuracy 0.900, Brier 0.075 | +0.001 | 0.50 |
| 2 | 0.44 | 0.28 | ≤ +0.002 for every news set | ≥ 0.41 |

**Structural stack:**

| Comparison | Lead | Brier gain | p |
|---|---|---|---|
| N2 (event features) | 2 | +0.048 | 0.062 (not significant) |
| N2 (event features) | 1 | −0.024 | — |
| N3 (E64 news) | 1 | +0.006 | 0.28 |
| N3 (E64 news) | 2 | +0.029 | 0.25 |

**Logistic regression.** News sets "improve" a learner that is itself far below chance (0.20 → 0.36 at Lead 2).
That is not evidence of value.

**Group permutation.** Within-quarter permutation of the news group *lowers* the logistic model's Brier at Lead 1
(−0.037), so news adds noise.

**Why news is weak:**
- about 6 relevant articles per province-quarter;
- headline-only for 87.5% of relevant articles;
- retrospective collection on 2026-10-14;
- the target's provincial variation is pure CPI, which the CPI features already carry.

**Verdict.** News is kept as a displayed warning signal and is not claimed as a predictive input.

## 5. Results by lead (`RESULTS_TABLES.md`; 13 target quarters 2023-Q1..2026-Q3, 65 rows, 24.6% HIGH)

**Columns (each arm is shown as accuracy / balanced accuracy / HIGH recall / Brier):**

| Column | Arm |
|---|---|
| Best baseline | the strongest baseline at that lead |
| S-SIM | pre-registered structural simulation |
| S-SIM-THR | post-hoc: S-SIM with a threshold chosen inside each origin |
| HYB-GBA-SIM | post-hoc: LightGBM where eligible, S-SIM elsewhere |
| M-GB-ALL | LightGBM on all drivers (issued rows only) |

| Lead | Best baseline | S-SIM | S-SIM-THR | HYB-GBA-SIM | M-GB-ALL (issued) |
|---|---|---|---|---|---|
| 0 (nowcast) | B-STATE 0.923 / 0.886 / 0.81 / 0.077 | 0.815 / 0.751 / 0.62 / 0.101 | 0.800 / 0.741 / 0.62 / 0.103 | – | 45 rows: 0.867 |
| 1 | B-PERSIST 0.723 / 0.627 / 0.44 / 0.277 | **0.846 / 0.751 / 0.56 / 0.118** | 0.846 / 0.814 / 0.75 / 0.129 | **0.877 / 0.834 / 0.75 / 0.101 (meets every criterion)** | 30 rows: 0.867 |
| 2 | B-AL 0.754 / 0.500 / 0 / 0.246; B-CLIM Brier 0.219 | 0.692 / 0.522 / 0.19 / 0.276 | 0.708 / 0.575 / 0.31 / 0.271 | 0.554 / 0.494 / 0.38 / 0.347 | 25 rows: 0.40 |
| 3 | B-AL 0.754 / 0.500 | 0.492 / 0.369 / 0.12 / 0.352 | 0.400 | 0.400 | 20 rows: 0.25 |

**Longest qualifying lead.**
- Pre-registered arms: none qualifies at any lead. At Lead 1, S-SIM misses only the significance criterion
  (Holm p = 0.105 at 13 quarters).
- Post-hoc arms: Lead 1, exploratory.
- The two-quarter requirement (Lead 2) is **not met**.

**Direct hunger target** (alternative, regional, 13 quarters):

| Lead | Persistence accuracy | Always-HIGH accuracy |
|---|---|---|
| 1 | 0.85 | — |
| 2 | 0.69 | 0.77 |
| 3 | 0.54 | — |

**Why Lead 2 fails.** The HIGH quarters come from shocks that were not visible three to five months before the target:
- the Aug–Sep 2023 rice spike;
- the Q4 2024 typhoon-season food-price jump;
- the hunger surges from 9–10% to 14–20% in 2023-Q4 and 2024-Q2.

After the 2025 rice-policy shift the learners, trained on the 2024 HIGH episode, keep predicting HIGH (M-GB-ALL 0.40
at Lead 2). This matches the forecastability literature and E41–E82.

## 6. Five drivers (Directive §7)

The drop-one / only-one group ablations and within-quarter permutation (`RESULTS.json → driver_ablation`) show:

| Driver | Finding |
|---|---|
| D1 Food prices and affordability | Carries the signal. Prices alone with LightGBM: 0.90 at Lead 1. Dropping prices costs the most (LightGBM: 0.867 → 0.600 at Lead 1). Largest permutation importance (+0.051 Brier for LightGBM, Lead 1). |
| D2 Climate (IBTrACS typhoons, ONI) | Alone 0.33–0.60. Dropping it changes nothing at Lead 1. Measures exposure, not observed damage. No dated PAGASA drought archive exists for 2021–26. |
| D3 Agricultural supply (PSA palay, corn, fisheries) | Alone 0.20–0.68. Unstable. |
| D4 Household economy (national LFS, BSP) | Dropping it lowers LightGBM's balanced accuracy at Lead 1 (0.909 → 0.534). National only, so it cannot separate provinces; within-quarter permutation importance is 0 by construction. |
| D5 News | No measurable value (§4). |

All five groups reach the training pipeline, survive preprocessing and are available at prediction time. Their weak
independent value is explained by:
- national resolution (D4);
- exposure rather than impact (D2);
- sparse, retrospective coverage (D5);
- a target that, since 2023-Q4, varies by province only through CPI.

## 7. Leakage and overfitting audit (Directive §8–9)

- **Timing.**
  - Every input is cut at O(t) by publication rule (E41 `Data.cut`).
  - The study window is asserted at load: no pre-2021 row.
  - Training labels must be complete and posted before O(t).
  - Thresholds are the E40 values frozen on 2021–22, and evaluation starts in 2023.
- **In-origin fitting.** Learners, thresholds and stacks are fitted only on pairs available at each origin. There is
  no tuning on evaluation rows.
- **Lead-text timing.** Lead text was retrieved on 2026-10-21 for articles published before each origin. This is a
  real-time-availability limitation, disclosed; it cannot leak outcomes.
- **Placebo** (ST-LR-N3, Lead 2):
  - training labels permuted, 50 repetitions, mean Brier gain over climatology +0.037 (95th percentile 0.058);
  - real model −0.022.
  - The stack has no genuine skill over climatology at Lead 2, consistent with its failure.
- **Overfitting.** The learners fail after the regime change. With 25–45 training pairs and one HIGH episode, any
  flexible model memorises 2024. The structural model, with no fitted outcome parameters, generalises better at
  Leads 0–1.
- **Multiplicity.** Post-hoc arms (D2, D4) reuse the same 13 quarters. Only the prospective seal can validate them.

## 8. Explanations (Directive §11)

- **Served LightGBM indicator.** Its TreeSHAP is reproduced independently from the artifacts
  (`tests/test_e83_served_shap.py`):
  - artifact hashes match the record;
  - additivity error is 1e-16;
  - each province's probability and grouped contributions match the served record within 5e-4.
- **Served province index (FIRI v2).** The index is additive, so the bars are its exact Shapley decomposition: pushes
  sum to index − 0.5 (tested).
- **New plain-language headline.** The headline is the only sentence the approved panel shows. It now gives:
  - the class and index;
  - up to three measured reasons, each tested to match the sign of its exact push;
  - a DA action, for example "keep Quezon on the DA IV-A watch list and check food prices, rice supply and assistance
    needs in its highest-ranked towns".
- **Second sentence.** It gives the factors on the other side and states that these are measured indicators, not
  proof of hunger.
- **No UI change.** Only backend text fields changed.

## 9. Local estimates (Directive §10)

- **Verified on the live API** (thesis mode, port 8001):
  - 142/142 LGUs, unique codes, correct province, a risk index and a band;
  - each LGU says it is derived from the province estimate, not a measured municipal rate.
- **Low-precision flag (new).** 25 LGUs whose PSA SAE coefficient of variation exceeds 20% are flagged
  "low-confidence" in `povertyLimitation`.
- **Lucena.** It stays flagged as a province substitute.
- **No municipal accuracy.** None is claimed, because no municipal outcome exists. CBMS 2024 is the missing source.

## 10. Updates, quarters and archives (Directive §12–13)

- **Monthly job.** `app/tasks/scheduler.py` adds `run_monthly_refresh` on the 10th, 04:00 PHT:
  - incremental lead text;
  - the idempotent E27 cycle;
  - an append-only `data/refresh_log.jsonl`.
- **Failure handling.** A failing step is recorded and does not stop the others (tested).
- **Quarterly outcomes stay quarterly.** The cycle seals before outcomes, refuses re-seals, validates inbox files
  against window and publication time, and advances the period only when a quarter is READY.
- **Scheduler state.** It stays off by default (`AIPHEED_ENABLE_SCHEDULER`), as configured by the user for Render.

## 11. Unresolved and recommended

1. **The target.** Since 2023-Q4, T43 measures price pressure, and no provincial food-insecurity outcome exists.
   Adviser decision needed; candidate data: CBMS 2024 FIES-type modules, FNRI provincial FIES.
2. **Lead 2 at > 75% is not achievable with these data.** It would need information that anticipates price and hunger
   shocks 3–5 months ahead. Nothing in the 2021–26 data, the lawfully reachable news included, does that.
3. **Prospective test.**
   - Seal 1331d498… holds 2026-Q4 (Lead 1), 2027-Q1 (Lead 2) and 2027-Q2 (Lead 3) for:
     - S-SIM, S-SIM-THR and S-SIM-SEAS(-THR);
     - ST-LR;
     - HYB-GBA-SIM.
   - Score it when PSA CPI and SWS publish those quarters.
4. **News.** More lead text needs publisher permission or licensed access (Inquirer, GMA, Philstar, MB, PNA). It must
   not come from bypassing access controls.

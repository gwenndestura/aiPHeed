# Data inventory, point-in-time control, target feasibility and FIRI v2 indicators (phases 2–4)

**Tags:** VERIFIED (command and output saved), INFERRED (read from code or documents), NOT VERIFIED.

## 1. Inventory

**Roles:**
- **target:** the forecast variable.
- **input:** a model feature.
- **context:** shown, not used by the model.
- **validation reference:** used only to check estimates.

CPI, poverty incidence and FIRI are **never** ground truth.

| Source | Geography | Frequency | Units | Observation period (held) | Release date rule used | Missing-value policy | Role |
|---|---|---|---|---|---|---|---|
| SWS involuntary hunger (`backend/data/forecasting/sws_area_rounds.csv`, copy of E110 file, sha256 `936d0c26…`, equal to source VERIFIED) | 4 SWS areas (Balance Luzon contains CALABARZON) | Quarterly rounds | % of families; margin ± pp | 2021-Q2 … 2026-Q3; 23 rounds; 2022-Q1 and 2025-Q1 have no round | Per-round publication date; usable only if published **before** the issue date | No round → NOT_OBSERVED; never interpolated | **target** (and history input) |
| SWS published margins | Same | Per round | pp | Same | With the round | Missing margin → 6 pp (protocol T1) | Target SE / tolerance |
| PSA subsistence incidence (PFDR) | Province | 2021, 2023 | % of population | 2021, 2023 | PSA release dates (E131) | — | **validation reference** (provincial, survey years) |
| PSA FIES 2023 (PUF; Tables 7–8) | Province / decile | Triennial | Pesos, shares | 2023 | Table updated 2026-08-03 | — | Validation reference / context |
| DOST-FNRI FIES | Region; Batangas and Cavite 2021 | Irregular | % of households | 2021, 2023, 2025 | Report dates | — | Validation reference |
| PSA CPI regional (all, food, rice; 2018 = 100) | 18 regions → areas | Monthly | Index | 2021-01 … 2026-09 | Quarter end + 10 days (protocol C1–C4); YoY only from 2022-01 | Incomplete quarter → excluded | Input (challengers) / context |
| PSA unemployment, BSP remittances, GDELT shares, ONI, typhoons (E119 point-in-time dataset) | National / IV-A | Quarterly | Various | 2021+ | E119 period rule (one quarter back) | NOT_YET_PUBLISHED until its period appears | Input (challengers) / context |
| PSA poverty incidence | Region / province | 2021, 2023, 2025 | % | 3 rounds | PSA release dates | — | Context / vulnerability |
| POPCEN 2024 municipal (`data/reference/popcen2024_calabarzon_municipal.csv`) | 142 LGUs | Census | Persons | 2024 | — | — | Geography reference (VERIFIED: 142 unique codes, 5 provinces) |
| FSSI v2 news index (`data/news_e31/fssi_v2_panel.csv`) | 5 provinces | Quarterly | Index | 2021-Q1 … 2026-Q4 | Article `published_ph` timestamp | `NO_USABLE_EVIDENCE` / `LIMITED_SIGNAL` / `SUFFICIENT` kept distinct | Context (not representative of Balance Luzon; E134) |
| Served P0H4 export (`data/ch1_engine/rows.csv`) | 5 provinces | Quarterly | Probability | 2023-Q1 … 2027-Q1 | Built offline | — | Served dashboard output (not a target) |

## 2. Point-in-time (as-of) control

- **`app/forecasting/as_of.py: as_of(df, issue)`** is the one selector for the forecasting core.
  - It keeps rows published strictly before 00:00 Asia/Manila on the issue day (protocol E1, P-DASH).
  - A row without a valid publication date raises `LeakageError`; it is never kept.
  - `assert_point_in_time()` guards built tables.
- **News** uses the article publication timestamp (`published_ph`, Asia/Manila). The legacy news paths already apply it (INFERRED: `app/news/fssi_v2.py`, `pipeline_v3.py`). They were not rerouted through `as_of` (AUDIT D5).
- **Validation** (`app/forecasting/validation.py`) checks columns, quarter format, publication versus fieldwork dates, fieldwork inside the quarter, value ranges (0–100 %, margin 0–20 pp), duplicates, booleans, the 2021+ window and staleness. It returns every problem, and `load_rounds()` raises `ValidationError` on any.
- **Missing-data states** (`app/forecasting/evidence.py: DataState`): OBSERVED, NOT_YET_PUBLISHED, NOT_OBSERVED, UNAVAILABLE, NOT_APPLICABLE, INVALID. They are never merged.
- **Imputation:** the forecasting core imputes nothing. Missing quarters are missing observations in the Kalman filter.
- **Tests** (`tests/unit/test_forecasting_core.py`, VERIFIED):
  - leakage tests, which **fail when a leak is injected**: `AIPHEED_LEAK_DEMO=1` makes 2 of 2 fail; normally 2 of 2 pass (`docs/aipheed/leak_injection_demo.txt`);
  - a validation test that flags each of 6 injected problems.

## 3. Target feasibility (gate)

**What the target measures.**
- SWS "involuntary hunger": the share of families reporting they experienced hunger with nothing to eat at least once in the past three months.
- It is an experienced-hunger measure of food insecurity.

**Geography, frequency and lag.**
- Four strata (Metro Manila, Balance Luzon, Visayas, Mindanao). **CALABARZON is 1 of 7 regions in Balance Luzon.**
- Quarterly, with gaps in 2022-Q1 and 2025-Q1.
- Published 3–10 weeks after fieldwork. At a quarter-start issue the newest value is usually two quarters old.

**Scale consistency.**
- **Unit:** % of families throughout.
- **2025-Q2 change:** the respondent base switched from household heads to adults (documented break, modelled), and sample sizes alternate.
- **Sampling SE:** 1.6–2.4 pp.

**Separate tracks, never combined:**

| Track | Measure | Use |
|---|---|---|
| Primary target | SWS area hunger (quarterly) | Forecast and score |
| Provincial reference | PSA subsistence incidence (survey years) | Check provincial estimates at 2021 and 2023 |
| FIES | FNRI and PSA FIES | Construct validation |
| Other | OCTA | Cross-check only |

**Decision: claims the target supports.**
- **Supported:** a numerical forecast of SWS-measured hunger for the four SWS areas, including **Balance Luzon, the area containing CALABARZON**, scored against SWS under the frozen tolerance.
- **Not supported:**
  - any quarterly provincial or LGU food-insecurity forecast or validation (no such measurement exists);
  - any claim that CALABARZON's own level equals Balance Luzon's.
- **Implemented accordingly** (`app/forecasting/geography.py`):
  - every province and all 142 LGUs carry the Balance Luzon value as `BROADER_AREA_REFERENCE`;
  - the provincial and LGU estimate fields are `null` with status `AWAITING_GROUND_TRUTH`. This is the schema slot for a future provincial measurement such as CBMS FIES.
- **Evidence-status enum** (`app/forecasting/evidence.py: EvidenceStatus`): VALIDATED / BROADER_AREA_REFERENCE / PROVINCIAL_ESTIMATE_UNVALIDATED / AWAITING_GROUND_TRUTH. It is used by inference, geography and the API.

## 4. FIRI v2 indicators A1–H1 and the five trigger groups

**Source:** `app/ml/inference/firi.py` (INFERRED from code), plus E119 / E131 records.

| Code | Meaning | Source | Formula (as coded) | Units | Geo level | Frequency | Availability lag | Missing behaviour | Group |
|---|---|---|---|---|---|---|---|---|---|
| A1 | Food-price-pressure forecast | LightGBM on PSA CPI (FIRI pipeline) | Model probability | 0–1 | Province | Quarterly | Built at issue from data before it | Dropped (domain needs ≥ 4 of 6) | 1 Market |
| A2 | Headline inflation above usual | PSA CPI | (food − gap) − province 2021–22 P60 | pp | Province | Monthly | CPI rule | Dropped | 1 Market |
| A3 | Wholesale rice price change | PSA wholesale prices | YoY % | % | Province | Monthly | ~1 month | Dropped | 1 Market |
| C1 | El Niño alert / advisory | PAGASA ENSO | 1 if in force, else 0 | Flag | National | Advisory | State before issue | Dropped | 2 Climate |
| C2 | Typhoons within 300 km | IBTrACS | Count | Count | Province buffer | Quarterly | Incomplete quarter → `incomplete` | Dropped | 2 Climate |
| C3 | Palay / corn production drop | PSA | −min(YoY) | % | Province | Quarterly | One quarter back | Dropped | 2 Climate |
| C4 | Fisheries production drop | PSA | −YoY | % | Province | Quarterly | One quarter back | Dropped | 2 Climate |
| E1 | Unemployment change | PSA LFS | YoY pp | pp | **National** | Quarterly | One quarter back | Dropped | 3 Employment / OFW |
| E2 | Remittance decline | BSP | −YoY % | % | **National** | Monthly | One quarter back | Dropped | 3 Employment / OFW |
| N1 | FSSI-v3 news index | aiPHeed NLP | Index (needs enough articles) | 0–1 | Province | Quarterly | Article timestamps | `too_few_articles` / `missing` | 4 News / NLP |
| V1 | Poverty and density | PSA SAE 2021 / POPCEN 2024 | 0.6 × poverty_norm + 0.4 × density_norm | 0–1 | Province | Static | From 2025-07-01 (Amendment 1: static profile at every origin, disclosed) | `unavailable_at_issue` | 5 Poverty / vulnerability |
| H1 | Regional hunger outlook > 11.3 % | SWS Balance Luzon | Probability | 0–1 | Balance Luzon | Quarterly | Publication date | Dropped | Hunger (not a trigger group) |

**Findings and actions.**
- **Wrong or disconnected indicators.**
  - **A1 is itself a model output** (a LightGBM probability). It sits inside an index used for evaluation, so "market" influence partly reflects a second model.
  - **E1 and E2 are national values** shown per province.
  - **H1 and A1 together make FIRI partly target-derived** when it is compared with SWS.
  - All three are documented. They are **not used** by the numerical forecasting core, and the served FIRI and P0H4 values were not changed (production restriction).
- **Groups stay identifiable and are never weighted artificially.** In the forecasting core the five groups are context only (`app/forecasting/explain.py`), because no group has a demonstrated Lead-2 contribution (E133–E136 ablations). In the served FIRI, the protocol's equal domain weights are left unchanged.
- **NLP pipeline** (INFERRED from code and manifest):
  - the intensity model is versioned with its revision (`joeddav/xlm-roberta-large-xnli@b227ee8435ce`);
  - the scorer refuses a keyword fallback (`fssi_v2.py` raises);
  - timestamps are `published_ph` (Asia/Manila);
  - deduplication is in `app/news/pipeline_v3.py` / `audit.py`;
  - geography is title-geocoded with the relevance rule R1.1;
  - evidence states are kept distinct (manifest: 67 NO_USABLE_EVIDENCE, 46 LIMITED_SIGNAL, 7 SUFFICIENT province-quarters; 140 admitted articles);
  - language handling is via the XLM-R multilingual model plus `app/ml/corpus/language_filter.py`.
  - This pipeline was not re-executed in this session (NOT VERIFIED end to end; it needs the article store and model weights).

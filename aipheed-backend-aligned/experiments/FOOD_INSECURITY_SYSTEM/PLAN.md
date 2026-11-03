# FOOD_INSECURITY_SYSTEM, Step 4: serve REF+news (backend only) — PLAN

**Written:** 2026-11-03, before any Step-4 code is changed and before any news flag, province score or LGU rank in
this plan is computed.

**Revision 2** (2026-11-03, before the build). Revision 1 (SHA-256 `49c16262…50b1`, commit `068fe1c`) was changed as
you decided:
- §2: the P0H4 food-price pressure band is back, as context only;
- §3: Lucena uses its own PSA Table 2a value;
- §6: your answers;
- §7: the Alignment table, added.

Nothing was built between the two revisions. For revision 2, the geography list of PSA Table 2a was read (it has a
row "City of Lucena"); its values were not.

**Status:** plan for approval. The team chose REF+news as the main model (OPTION_1, pending adviser confirmation).
P0H4 stays the documented alternative (`ch1` mode, unchanged).

**Hash.** The SHA-256 of this file is computed over every byte before its last line, which begins `PLAN-SHA256:`.
`runner/export_fi.py` refuses to run if the file changed after hashing.

**What this does not change:**
- the frontend, `render.yaml`, the Dockerfile;
- the FIRI v2 default (`AIPHEED_MAP_MODEL` unset) and the `ch1` mode;
- every file in `OPTION_1/`, `IMPROVE_V2/`, `IMPROVE_V2_LEADS/`, `E85_GDELT_Events/`, `E112_.../`, `PAPER_ALIGNED/`;
- `backend/seals/`, `PREREG_LEAD2.md` and its addenda.

Nothing is pushed to GitHub. Commits are local only.

**Read before writing this plan:**
- `OPTION_1/RESULTS.md`, `SEAL_LEDGER.md`;
- `FOOD_INSECURITY_SYSTEM/STEP2_SERVING.md` and the uncommitted `foodinsecurity` mode;
- `PAPER_ALIGNED/CH3_AMENDMENT.md` §2.1, §7.2, and `P0H4_BACKEND_PROPOSAL.md`;
- `IMPROVE_V2/PLAN.md` §5 (news timing);
- `E85_GDELT_Events/PROTOCOL.md` and `runner/e85_features.py`.

**What was seen before this plan:**
- The column layouts and quarter ranges of the E85 feature files (2021-Q2..2026-Q3, five provinces; k1 = k2 = k3) and
  the E112 corpus file (2021-Q1..2026-Q4).
- The PSA OpenStat table list (Tables 1, 2, 2a, 3).
- The PSA 2018/2021/2023 food-poverty (subsistence) values for families already stored in the repository.
- The REF+news probabilities for origin 2026-Q3 (0.869 at Leads 1 and 2).
- E85's published verdict (no news value).

No province news value was compared with its history, no flag was computed, and no 2023 provincial poverty value was
downloaded.

## 1. Model served (decision 4)

| Item | Definition |
|---|---|
| Model | IMPROVE_V2 arm **REF+news**, unchanged. Rows from `OPTION_1/out/forecasts_refnews.csv` (`name == "REF+news"`), SHAP from `OPTION_1/out/shap_refnews.csv`. Nothing refitted. Model label `IMPROVE_V2-REFNEWS`. |
| Leads | **1 and 2 only.** Under the paper's 75% rule (Algorithm 3), the Maximum Reliable Lead Time is 2. Lead 3 is the first failure (0.694). |
| Rows | The same span as Step 2: Lead-1 walk-forward targets 2023-Q1..2026-Q3, plus the forecasts issued 2026-10-01: 2026-Q4 (Lead 1) and 2027-Q1 (Lead 2). |
| Checks (refuse on failure) | The 2027-Q1 row must equal `OPTION_1/sealed_prospective_REFNEWS.csv` (SHA-256 `cc1ff11b…5216`, P 0.869247, HIGH). The OPTION_1 `results.json` SHA-256 is recorded in `evaluation.json`. |
| Disclosure | If Lead 1 and Lead 2 have the same probability at every origin (true for 2026-Q3), the text says so: "Leads 1 and 2 give the same probability; the lead input has no effect." |
| `evaluation.json` | Built from `OPTION_1/out/results.json`: `max_reliable_lead = 2` (Algorithm 3), `max_reliable_lead_r1_r7 = 0`, and the Objective-2 metrics and R1–R7 results for Leads 1–3. |

**Reliability text** (`horizonLabel`, `summary.sentence`, `INDICATOR.horizon`, `caveat`, reports). It replaces the REF
wording (REF's Lead 3 accuracy was 0.726):

> "Leads 1–2 pass the paper's 75% accuracy rule (accuracy 0.758 on 62 past quarters; Maximum Reliable Lead Time 2)
> but fail the stricter reliability rules R1–R7 (balanced accuracy 0.693, Brier not significantly better than
> climatology, 2015–2020 accuracy 0.57). News adds little: 2.8% of SHAP influence, and the same model without news
> scored 0.790."

## 2. Province score (decision 2)

**Poverty input.** `pov_p` is the PSA 2023 full-year poverty incidence among families, PSA OpenStat Table 1
(`DB/1F/FY/0011F3DF010.px`), for the five provinces and CALABARZON, with its coefficient of variation (CV).
- It is fetched once by `runner/fetch_psa.py`.
- It is saved to `backend/data/foodinsecurity_engine/psa_poverty_families_2023.csv`, together with the URL, the fetch
  date and the raw JSON's SHA-256.
- If the table cannot be fetched, nothing is built.

**Score.**

  score_p(q) = P_reg(q) × pov_p / max_k pov_k, where P_reg is the regional REF+news probability.

- Range: 0 to P_reg. The poorest province shows the regional probability itself.
- The provinces get different scores. Their order is fixed by poverty in every quarter, and the text says so.
- `riskScore` = score_p, rounded to 4 decimals.
- The sentence calls it "priority score (regional probability weighted by provincial poverty)", never a probability.
  It gives P_reg and pov_p next to it.

**Colour and class.**
- `riskLevel`, colour and class are the regional class (HIGH when P_reg ≥ 0.50), the same for every province.
- They are never computed from score_p, so the weighting can never lower a class.
- The map rank follows score_p.

**Context only: food poverty.** The PSA 2023 subsistence incidence among families (Table 3; the stored file
`LEAD2_RELIABILITY_RESEARCH/.../subsistence_families_2018_2023.csv`, SHA-256 recorded) appears in text only:

> "Provincial food poverty 2023: x% of families (CV y%); low precision (CV > 30%), not used for ranking."

The "low precision" clause is printed only where CV > 30%:

| Province | CV 2023 | Clause printed |
|---|---|---|
| Batangas | 33.9 | yes |
| Cavite | 53.3 | yes |
| Laguna | 35.0 | yes |
| Quezon | 38.5 | yes |
| Rizal | 24.5 | **no** |

For Rizal the text reads "(CV 24.5%), not used for ranking".

**Context only: food-price pressure band** (revision 2). This is the price part of the served P0H4 forecast
(`pi_price`). It is read from `backend/data/ch1_engine/rows.csv` (SHA-256 recorded) for the same province, target
quarter and lead, using the **official** row issued on the same date as the REF+news row (2026-10-01 for 2026-Q4 and
2027-Q1), not the M3 update.
- **Bands:** Low < 0.33 ≤ Medium < 0.67 ≤ High.
- **Purpose:** it changes from quarter to quarter and from province to province, so each province's information changes
  over time.
- **Where it appears:** the text, as "food-price pressure: Medium (P0H4 price part 0.41; context, does not change the
  score)", and the Market driver card.
- **What it never changes:** score_p, the class, the colour or the rank.
- **Missing rows:** where there is no P0H4 row, the text reads "food-price pressure: not available".

**Removed from the province design.** The province-level 0.6/0.4 vulnerability rank is no longer shown, because
decision 2 replaces it. The old texts are rewritten:
- "never multiplies" becomes "the score is weighted by poverty; the class is not";
- "ordered by food-price pressure" becomes "ordered by the poverty-weighted score; food-price pressure is context".

## 3. LGU ranking (decision 1)

**Poverty.** PSA 2021 City and Municipal SAE, read from `backend/data/reference/sae2021_calabarzon_municipal.csv`
(141 LGUs, population basis).

**Lucena** (revision 2). Lucena is a highly urbanized city (HUC) and is not in the SAE table. Its poverty value
comes from PSA OpenStat **Table 2a** (`DB/1F/FY/0041F3DF02A.px`, "Poverty Incidence Among Population … by Region,
Province and Highly Urbanized Cities"), geography "City of Lucena" (code 57), 2021, item "Poverty Incidence among
Population (%)", with its CV.
- Basis and year are the same as the SAE.
- It is cited as "PSA 2021 Full-Year Official Poverty Statistics, Table 2a (City of Lucena)", with the URL and the
  fetch date.
- **Only if** Table 2a returns no 2021 value for Lucena, the Quezon 2021 value from Table 2 (`0031F3DF020.px`) is
  used and Lucena keeps the flag "Quezon province value, not a Lucena estimate".
- Either way, the result replaces the unverified 16.8 in `data/inputs/lgu_vulnerability.csv` through a served copy.
  The input file itself is not edited.
- In Table 2a, Quezon appears as "Quezon (w/o the City of Lucena)". It is not used for the LGUs.

**Density.** PSA 2024 population divided by land area, from the existing `lgu_vulnerability.csv`.

**Index.** index = 0.6 × minmax(poverty) + 0.4 × minmax(density), with both min-max taken within the province, as
Objective 3 states. Ranks run within the province.
- No food-poverty weight.
- No price weight.

**LGU number.** `riskIndex` = score_p × index, the existing pattern with the new province score. `riskLevel` is the
regional class. `prov_p` for the colour is P_reg, not score_p.

## 4. News (decision 3)

**Regional sentence.** It uses the six E112 category shares, from `E112_.../out/news_quarterly_corpus.csv`: the file
and timing REF+news uses (quarter t usable only if `last_published < O(t)`).
- It names the category with the largest positive year-on-year share change (`*_yoy`).
- If that change is ≥ 0.05 (5 percentage points): "Regional news (project corpus, Q, n articles): {category} coverage
  rose most, +x points year on year."
- Otherwise: "no news category rose 5 points or more year on year."

**Province sentence and early-warning flag.** These use the E85 province features (`gp_share_*`, shrunk to the region
with κ = 20, and `gp_logn`) from `E85_GDELT_Events/runs/20261021T101520Z/gdelt_features_k1.csv`, read as stored.
- **Timing.** The flag uses quarter t = the origin quarter of the forecast. The build checks that E85's cut
  (O(t) − 1 day) is on or before the issue date, and refuses otherwise.
- **Families flagged:** PRICE, FOODSEC, DISASTER, AGRI, LIVELIHOOD. RESPONSE (aid coverage) is reported but never
  flags, because it follows events rather than anticipating them.
- **History window, fixed:** the 8 quarters t−8..t−1. Fewer are used when the series is shorter, with a minimum of
  6; otherwise the text reads "not enough news history" and there is no flag.
- **Threshold, fixed.** A family flags when **all three** hold:
  - x(t) − mean(H) ≥ 1.5 × sd(H), with ddof = 1, where x(t) is its share in quarter t and H is the window;
  - x(t) − mean(H) ≥ 0.05;
  - the province's own article count expm1(`gp_logn`) ≥ 20.

  With fewer than 20 articles the value is mostly the region's, so the text reads "too few province articles" and
  there is no flag.
- **Province flag** = any family flags. The sentence reads: "Province news (GDELT, Q): {family} coverage x% against a
  usual y% (8-quarter mean): early-warning flag" or "no news category above its usual level".
- **The flag never changes score_p, the class or the rank.**
- **Coverage.** E85 stops at 2026-Q3. Later origins read "no provincial news after 2026-Q3"; a new query is out of
  scope.
- **No tuning.** The flag counts per province over the served quarters are reported in `STEP4_RESULTS.md` as they come
  out. If they fire in every quarter or in none, that is reported and nothing is changed.
- **Disclosure.** E85 found no predictive news value, and news is 2.8% of REF+news SHAP. The text says the flag is
  descriptive context, not a validated predictor.

**Rule 7.**
- A province flag on an **issued** forecast is staged as an alert candidate (`PROVINCE_NEWS_EARLY_WARNING`), next to
  the existing `REGIONAL_FOOD_INSECURITY_HIGH`.
- Both are STAGED only. They become public only after a DA Region IV-A administrator confirms them.
- Nothing calls `stage_alerts` automatically. No mailer is imported, and nothing notifies DSWD or any agency.

**Rule 1.** Unchanged from Step 2: an issued forecast is withheld until it is approved in the review queue.

## 5. Implementation (decision 5: build on the uncommitted `foodinsecurity` mode)

| File | Change |
|---|---|
| `FOOD_INSECURITY_SYSTEM/runner/fetch_psa.py` (new) | Fetches Tables 1, 2 and 2a for CALABARZON; writes the CSVs and the raw-JSON hashes |
| `FOOD_INSECURITY_SYSTEM/runner/export_fi.py` | Reads REF+news instead of REF and checks the OPTION_1 seal; computes score_p, the food-poverty and price-band context (official P0H4 `pi_price`), the LGU index with Lucena, and the news sentences and flags; checks this plan's hash |
| `backend/data/foodinsecurity_engine/` | `rows.csv`, `evaluation.json`, `lgu_rows.csv` (new), the PSA CSVs |
| `backend/app/ml/inference/foodinsecurity_system.py` | Texts per §1–§4; `province_score`, the LGU lookup, the news sentences, the extra alert candidate |
| `served_risk.py`, `dashboard.py`, `final.py`, `insights.py`, `report.py`, `report_data_e31.py`, `review.py` | Only where the mode must pass score_p, the regional class or the LGU rows; still gated on `AIPHEED_MAP_MODEL=foodinsecurity`; no field renamed, removed or added |
| `backend/tests/integration/test_foodinsecurity_mode.py` | Updated, see below |

**Tests (new or updated):**
- Scores differ by province; the poorest province equals P_reg.
- Class and colour equal the regional class for every province and LGU, including a case where score_p < 0.50 and
  P_reg ≥ 0.50.
- The 2027-Q1 row equals the OPTION_1 seal.
- Only Leads 1–2 are served.
- The reliability text names the 75% rule, the R1–R7 failure, 2.8% and 0.790.
- The food-poverty clause appears only where CV > 30%, and Rizal has none.
- Lucena carries its Table 2a value and citation (or the Quezon value and the flag, if Table 2a has none); the LGU
  index uses 0.6/0.4 within the province.
- The price band follows the cut-offs and appears in the text. Changing `pi_price` changes no score, class, colour or
  rank.
- The flag rule works on synthetic inputs: the window minimum, the 20-article floor, and RESPONSE never flags.
- Issued forecasts are withheld until approved; alerts are staged and never confirmed automatically.
- The FIRI default and `ch1` mode are unchanged.

Then the full backend suite runs, with the before and after counts reported.

**Commits.** Local only:
1. revision 1;
2. this revision 2;
3. the build;
4. `STEP4_RESULTS.md`.

## 6. Decisions on the revision-1 defaults

| # | Default | Decision |
|---|---|---|
| 1 | Score = P_reg × pov_p / max pov | Accepted |
| 2 | Rizal (CV 24.5%): the CV > 30% note is printed only where true | Accepted |
| 3 | Price band and province vulnerability rank dropped | **Changed:** the price band is back as context (§2); the province vulnerability rank stays dropped |
| 4 | Lucena = Quezon, Table 2 | **Changed:** Lucena's own Table 2a value; Quezon only as the fallback (§3) |
| 5 | Flag rule (8 quarters, 1.5 sd, 5 points, 20 articles, RESPONSE excluded) | Accepted |
| 6 | E112 regional sentence from the project corpus file the model uses | Accepted |
| 7 | No provincial news after 2026-Q3 | Accepted |

## 7. Alignment with the paper (Chapter I §1.3–1.5; status after this build)

Development evidence throughout. "Paper" means `THESIS 2 (18).pdf`; "amendment" means `PAPER_ALIGNED/CH3_AMENDMENT.md`.

| Item | What the paper asks (short) | How Step 4 serves it | Status |
|---|---|---|---|
| **Food-insecurity focus** | Forecast food-insecurity risk, not prices | Target = SWS Balance Luzon involuntary hunger > 11.3%. Prices are model inputs and a context band, never the target or a condition of the class | Met |
| **Obj 1** NLP pipeline (FSSI, BERTopic) | News signals per province-quarter | REF+news uses N1R (regional FSSI-v3), GDELT price news and six E112 categories. E85 province categories give the explanation sentences and flag (§4) | Achieved, with limits: news is 2.8% of SHAP; BERTopic is not an input |
| **Obj 2 I–IV** Accuracy, precision/recall, F1, AUC | Classification metrics | Lead 1/2: accuracy 0.758, precision 0.804, recall 0.860, F1 0.831, AUC 0.688/0.674 (OPTION_1) | Achieved (measured) |
| **Obj 2 V** Walk-forward, furthest reliable lead | Algorithm 3, 75% rule | Maximum Reliable Lead Time 2; only Leads 1–2 served; R1–R7 failure stated | Achieved under the paper's rule; fails the stricter rules |
| **Obj 3** LGU rankings, poverty 60% + density 40% | From validated province forecasts | 142 LGUs: 0.6 × SAE 2021 poverty + 0.4 × density within the province; Lucena from Table 2a; colour = regional class | Achieved as a priority ranking from the regional forecast (amendment wording below) |
| **Obj 4** vs persistence, PSA-only, NLP-only, logistic regression | Four baselines | Holm table in OPTION_1 §4: beats persistence (L1/L2) and NLP-only (L1); not the PSA-only or logistic regression | Achieved (compared); mixed result |
| **Obj 5** Dashboard, early-warning alerts, ISO/IEC 25010, FNRI | Public dashboard and evaluation | Backend serves the forecast, staged alerts (Rule 7) and the FNRI face-validity line. Frontend not changed | Backend part met; evaluation waiting for respondents |
| **RQ1** Strongest predictors (SHAP) | SHAP ranking | Bars = REF+news SHAP groups: past hunger 64%, world prices 21%, CALABARZON prices 6%, news 2.8% | Answered (descriptive) |
| **RQ2** Furthest reliable lead | Lead time | 2 quarters (Algorithm 3); 0 under R1–R7 | Answered |
| **RQ3** vs six baselines | Six comparators | OPTION_1 H3 table (Holm) | Answered |
| **RQ4** LGU rankings reflect vulnerability? | Against DA evaluators | Rankings served with provenance | Waiting for evaluators |
| **RQ5** ISO/IEC 25010 by DA and DEPDev | Evaluation | No change | Waiting for evaluators |
| **H1** FSSI and food CPI deviation not among the strongest | SHAP | News 2.8% and CALABARZON food prices 6.1%, both below past hunger and world prices. Feature ranks from `shap_refnews.csv` go in STEP4_RESULTS | Not rejected (to be confirmed with the feature ranks) |
| **H2** Not reliable across multiple leads | Algorithm 3 | Leads 1 and 2 pass the 75% rule; R1–R7 fail | Rejected under the paper's rule (2 leads); not rejected under R1–R7 |
| **H3** Combined LightGBM not better than six | H3 table | Not significantly better than all six | Not rejected |
| **H4** LGU rankings not consistent with DA | Survey | — | Waiting for evaluators |
| **H5** No favourable ISO/IEC 25010 ratings | Survey | — | Waiting for evaluators |

**Remaining wording changes** (the amendment §2.1 Option A table, adjusted to this design; for the adviser, not
applied to the paper here):

| Where | Current | Proposed |
|---|---|---|
| RQ2, RQ3, H2, H3, dependent variable (pp. 10–11) | "province-level" / "of a CALABARZON province" | "regional (Balance Luzon hunger > 11.3%) food-insecurity risk, applied to every CALABARZON province", as in the amendment |
| Obj 2 I, II, IV (pp. 12–13) | "province-level classifications", "high-risk provinces" | "quarterly regional classifications; provinces ordered by a poverty-weighted priority score" |
| Obj 3, Rule 4, Algorithm 5 (pp. 13, 46, 48) | "from validated province-level forecasts" | "from the regional food-insecurity forecast, which passed Algorithm 3 at Leads 1–2. Provinces are weighted by PSA poverty incidence (families, 2023) and LGUs ranked by PSA 2021 poverty (60%) and density (40%); priority rankings, not measured rates; the class is never changed" |
| §1.7 (p. 15) | "SWS … and PSA food price data will be used to determine food insecurity risk" | "SWS hunger defines the regional classification; PSA poverty weights the provinces; PSA food prices are model inputs and a context band" |
| Amendment §2.1 Option A | "ordered by food-price pressure and vulnerability rank; nothing multiplied" | "score weighted by provincial poverty; food-price pressure and food poverty shown as context" (this design is neither Option A nor Option B; the amendment needs a short Option C) |
| Algorithm 3 / §3.4.4 (pp. 41–43, 57) | 75% rule only | "75% rule, reported with R1–R7, which this model fails" |
| §1.5.2 Obj 1 | FSSI per province-quarter as model input | "regional news signals as model inputs; provincial GDELT categories as explanation and early-warning context" |
PLAN-SHA256: 4d4e2a2c6fc931159f866a5c66ffb1492bdf4c63dcf15ae46aad367b4f490840

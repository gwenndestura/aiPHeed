# FOOD_INSECURITY_SYSTEM, Step 4: serve REF+news (backend only) — PLAN

**Written:** 2026-11-03, before any Step-4 code is changed and before any news flag, province score or LGU rank in
this plan is computed.

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

**Removed from the province design.** The P0H4 price band and the province-level 0.6/0.4 vulnerability rank are no
longer read or shown. Decision 2 replaces them, and the P0H4 rows (`ch1_engine/rows.csv`) are no longer needed. The
texts saying "never multiplies" or "ordered by food-price pressure" are rewritten to say: "the score is weighted by
poverty; the class is not".

## 3. LGU ranking (decision 1)

**Poverty.** PSA 2021 City and Municipal SAE, read from `backend/data/reference/sae2021_calabarzon_municipal.csv`
(141 LGUs, population basis).

**Lucena.** Lucena is a highly urbanized city (HUC) and is not in the SAE table.
- It gets Quezon's 2021 provincial poverty incidence among the population (PSA OpenStat Table 2,
  `0031F3DF020.px`). Table 2 is on the same basis and year as the SAE, so the two are comparable.
- This replaces the unverified 16.8 now in `data/inputs/lgu_vulnerability.csv`, through a served copy. The input file
  itself is not edited.
- Lucena is flagged in `limitation` and its poverty provenance as "Quezon province value, not a Lucena estimate".
- Table 2a lists HUCs separately but is **not** used, as decided.

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
| `FOOD_INSECURITY_SYSTEM/runner/fetch_psa.py` (new) | Fetches Tables 1 and 2 for CALABARZON; writes the CSVs and their hashes |
| `FOOD_INSECURITY_SYSTEM/runner/export_fi.py` | Reads REF+news instead of REF and checks the OPTION_1 seal; computes score_p, the food-poverty context, the LGU index with Lucena, and the news sentences and flags; checks this plan's hash; drops the P0H4 `pi_price` columns |
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
- Lucena carries the Quezon value and the flag; the LGU index uses 0.6/0.4 within the province.
- The flag rule works on synthetic inputs: the window minimum, the 20-article floor, and RESPONSE never flags.
- Issued forecasts are withheld until approved; alerts are staged and never confirmed automatically.
- The FIRI default and `ch1` mode are unchanged.

Then the full backend suite runs, with the before and after counts reported.

**Commits.** Local only, after you approve the build:
1. This plan (now);
2. the build;
3. `STEP4_RESULTS.md`.

## 6. Points where I chose a default (change any before the build)

1. **Score formula.** P_reg × pov_p / max pov. The alternative, division by the CALABARZON value, can exceed 1 and
   would need clipping.
2. **Rizal.** The food-poverty CV is 24.5%, so the "CV > 30%" note is printed only where it is true.
3. **Dropped.** The P0H4 price band and the province vulnerability rank.
4. **Lucena.** The Quezon value comes from population-basis Table 2 (2021, matching the SAE), not the families table.
5. **Flag rule.** The values in §4: 8 quarters, 1.5 sd, 5 points, 20 articles, RESPONSE excluded.
PLAN-SHA256: 49c162626f56e0ede4aac471edbc44fc5e7e57921cad1c6532e00ec112d250b1

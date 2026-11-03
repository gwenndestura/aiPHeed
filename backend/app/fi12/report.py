"""Write the twelve FI12 deliverables to docs/fi12 from data/fi12/out (numbers are read from the result files).

    python -m app.fi12.report
"""
from __future__ import annotations

import itertools
import json

import pandas as pd

from app.fi12 import DOCS, OUT
from app.fi12 import match as M
from app.fi12 import outcomes as O
from app.fi12.study import PROTOCOL, spearman
from app.paths import BACKEND_DIR

TAG = "Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file."


def _f(x, d=2):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "–"
    return f"{x:.{d}f}" if isinstance(x, float) else str(x).replace("|", " · ")


def _table(df: pd.DataFrame, cols=None) -> str:
    df = df[cols] if cols else df
    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "\n".join("| " + " | ".join(_f(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"


def _w(name: str, title: str, body: str) -> None:
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    (DOCS / name).write_text(f"# {title}\n\n**FI12** · protocol `{lock['sha256'][:12]}` locked {lock['locked_utc']} · {TAG}\n\n{body}", encoding="utf-8")


def build() -> list[str]:
    T = pd.read_csv(OUT / "outcomes.csv")
    E = json.loads((OUT / "evaluation.json").read_text())
    R = pd.read_csv(OUT / "ranking_agreement.csv")
    L = pd.read_csv(OUT / "level_accuracy.csv")
    F = pd.read_csv(OUT / "feature_association.csv")
    A = pd.read_csv(OUT / "model_scores_by_reference_year.csv")
    X = pd.read_csv(OUT / "forecast_observation_matches.csv")
    meta = json.loads((OUT / "matching_meta.json").read_text())
    meas = E["measurement"]
    fi10 = json.loads((BACKEND_DIR / "data" / "fi10" / "out" / "evaluation.json").read_text())
    files = []

    # 1 dataset audit
    inv = T.groupby(["outcome", "reference_year"]).agg(provinces=("province", lambda s: ", ".join(sorted(s))), records=("value", "size"),
                                                       verification=("verification", lambda s: ", ".join(sorted(set(s))))).reset_index()
    body = f"""## Workbook
- File: `aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx`. The upload named "(1)" is not on disk; the only copy (Downloads,
  2026-11-03 01:35) is byte-identical to `backend/data/fi_labels/raw/owner_supplied/` (SHA-256 `6655178448d5…`, also in
  `raw/MANIFEST.csv`). The original is kept unchanged; values are read from its sheet exports.
- 10 sheets: READ ME, Labeled Provincial Data (50 long-format records), FNRI 2015 Provinces, ENNS Provincial, PSA Subsistence,
  PSA Food Threshold, Regional Benchmarks, QA and Corrections, Sources, Label Dictionary. Three cell comments
  (ENNS reference years differ by province; PSA Table 1 source; thresholds are annual per-capita PHP).
- Metadata: written by openpyxl on 2026-11-02; the comments are authored "OpenAI", so the workbook was compiled with an AI
  assistant. Its values are therefore treated as transcriptions to verify, not as primary data.
- `province_code` is empty in all 50 records. PSA Quezon excludes Lucena City (HUC); whether the FNRI and ENNS Quezon
  values include Lucena is not stated (**unverified**).

## Records by outcome and reference year
{_table(inv)}
## Verification
- **40 of 50 records verified [V]:** the 10 FNRI 2015 values equal the FNRI 2015 report appendices; the 30 PSA subsistence
  values equal PSA OpenSTAT Tables 3 and 4 (checked again in FI12 code: `outcomes.build` asserts equality to 0.05 pp).
- **10 ENNS records unverified [S]:** they come from the DEPDev CALABARZON RDP results matrix. The DEPDev PDF returns HTTP 403
  to scripted download and the FNRI tables are behind a firewall from this network. Instrument (HFIAS or FIES), fieldwork
  months, sample sizes and SEs are not given.
- Regional benchmarks: FNRI 2015 (n = 4,328) [V]; 2023 NNS FIES moderate-to-severe 19.1 % (17.0–21.1) [V]; ENNS pooled
  51.5 % HFIAS and 2023 severe 1.7 % [S]; PIA 2025 22.6 % (news report) not used.

## Per-dataset assessment
| Dataset | Source / publication | Reference year | Unit | Precision | Comparable across years? |
|---|---|---|---|---|---|
| FNRI 2015 FSS | DOST-FNRI, Philippine Nutrition Facts and Figures 2015 | 2015 | % of households (HFIAS categories) | SE and 95 % CI per province; n 735–1,076 | Single wave; HFIAS, not FIES |
| ENNS provincial | DOST-FNRI ENNS, reproduced by DEPDev RDP 2023–2028 midterm matrix (published 2026-02) | Laguna 2018; Quezon, Rizal 2019; Batangas, Cavite 2021 | % of households | none published in the matrix | No: one year per province; severe values split 1.5–2.4 % (2021) vs 7.9–13.7 % (2018–19), and severe vs moderate-to-severe rank correlation is −0.1 within the same survey, which indicates a scale or instrument difference |
| PSA subsistence incidence | PSA full-year poverty statistics (OpenSTAT Tables 3/4; RSSO IV-A release) | 2018, 2021, 2023 (income year) | % of families / % of population below the food threshold | CV 17–62 % per province (median 34 %) | Yes, same methodology; but food poverty, not experienced food insecurity |
| PSA food threshold | PSA OpenSTAT Table 3a | 2018, 2021, 2023 | PHP per capita per year | — | Context only |

## Sampling reliability (FI12 [R])
{_table(pd.DataFrame([{"outcome-year": k, "Cochran Q p (provinces differ?)": v.get("q_p"), "noise-ceiling ρ (median)": v.get("noise_ceiling_rho_median"),
                         "top province reproducible": v.get("top1_reproducible_share"), "significantly above CALABARZON": ", ".join(v.get("significantly_above_region", [])) or "none"}
                        for k, v in meas.items() if "q_p" in v]))}
- The noise ceiling is the median Spearman between the published values and a re-draw with the published SEs: a perfect
  predictor of the true provincial values would score about this against the published numbers.
- **FNRI 2015: the five provinces are not statistically distinguishable** (Q p = {_f(meas['FNRI15_SEV|2015']['q_p'])}); no province differs from the
  regional 19.0 %. A ranking of 2015 provinces cannot be validated.
- **PSA 2018 and 2021: provinces differ; Quezon is significantly above CALABARZON in both.** PSA 2023: not distinguishable.
- ENNS: no SEs, so reliability cannot be assessed.
"""
    _w("01_PROVINCIAL_DATASET_AUDIT.md", "Deliverable 1. Provincial dataset audit", body)
    files.append("01_PROVINCIAL_DATASET_AUDIT.md")

    # 2 outcome matrix
    body = """| Track | Outcome | Measures | Geography / time | Supports the claim | Does not support |
|---|---|---|---|---|---|
| A. Direct provincial food insecurity | FNRI 2015 severe (HFIAS) [V]; FNRI 2015 not food secure (derived) [V] | Experienced household food insecurity | 5 provinces, 2015 only | "In 2015 about 17–21 % of households in each province were severely food insecure" | Any provincial ranking (provinces not distinguishable); any time trend |
| A. Direct provincial food insecurity | ENNS severe; ENNS moderate-to-severe [S] | Experienced household food insecurity (instrument unconfirmed) | 1 year per province (2018/2019/2021) | Descriptive provincial context, labelled secondary | A same-year comparison of provinces; a panel; model training |
| B. Provincial food poverty | PSA subsistence incidence, families and population [V] | Income below the food threshold | 5 provinces × 2018, 2021, 2023 | Food-poverty levels and their change between waves | "Food insecurity" (it is not an experience-based measure) |
| C. Regional temporal food insecurity | SWS involuntary hunger, Balance Luzon | Experienced hunger, past 3 months | Balance Luzon (7 regions), quarterly | Quarterly regional hunger outlook (FI9) | Any provincial value: never copied to provinces |
| D. Food-price and economic pressure | PSA provincial food CPI (FI10 target) | Unusual provincial food inflation | 5 provinces, monthly | A driver of food access | Food-insecurity accuracy |

**Rule kept throughout:** tracks are never combined into one label and food-price accuracy is never reported as
food-insecurity accuracy. Severe and moderate-to-severe are evaluated separately. Families and population are both
evaluated; families are primary.
"""
    _w("02_OUTCOME_DEFINITION_MATRIX.md", "Deliverable 2. Outcome definition matrix", body)
    files.append("02_OUTCOME_DEFINITION_MATRIX.md")

    # 3 matching dataset
    cov = pd.DataFrame([{"model|lead": k, "reference years matched": ", ".join(map(str, v))} for k, v in meta["coverage"].items()])
    src = pd.DataFrame([{"model": k, "file": v[0], "column / config": v[1], "what it is": v[2]} for k, v in meta["sources"].items()])
    nm = pd.DataFrame([{"model": k, "why not matchable": v} for k, v in meta["not_matchable"].items()])
    body = f"""**Rule.** For province p, reference year Y and lead L, a model's score is the mean of its out-of-sample quarterly scores
whose target quarter lies in calendar year Y and that were issued L quarters ahead. Every contributing forecast was
issued before its target quarter began (asserted in `match.py`). Survey **reference years** are used, never publication
years. ENNS values are matched province by province to their own year. "Partial" = fewer than four quarters.

**Files.** `backend/data/fi12/out/forecast_observation_matches.csv` ({E['n_matches']} outcome × model-score rows; every
outcome record appears, with no model where none exists) and `model_scores_by_reference_year.csv`.

## Models with provincial forecasts
{_table(src)}
## Coverage
{_table(cov)}
**Consequence.** Only FI10 (food-price pressure) has historical provincial forecasts for 2015, 2018, 2019 and 2021. Every
P0H4-family model (P0H4, P0H4-U, CR, CR-ANC, UNI-FINAL, CH1-LGBM, E108) starts at target quarter 2023-Q1, so the only
outcome it can be matched to is **PSA food poverty 2023 (five values)**. No P0H4-family forecast exists for any direct
food-insecurity observation; none can be reconstructed without information that was not available then.

The served P0H4 Lead-1 2023 scores in the matching file equal `backend/data/ch1_engine/rows.csv` exactly.

## Not matchable
{_table(nm)}
## Example rows (PSA 2023, served P0H4, Lead 1)
{_table(X[(X['outcome'] == 'PSA_SUB_FAM') & (X['reference_year'] == 2023) & (X['model'] == 'P0H4') & (X['lead'] == 1)][['province', 'reference_year', 'value', 'model', 'lead', 'first_issue', 'last_issue', 'score', 'coverage']])}"""
    _w("03_FORECAST_OBSERVATION_MATCHING.md", "Deliverable 3. Forecast-to-observation matching dataset", body)
    files.append("03_FORECAST_OBSERVATION_MATCHING.md")

    # 4 provincial validation
    def rk(oid, years, keys):
        g = R[(R["outcome"] == oid) & R["year"].isin(years) & R["key"].isin(keys)].copy()
        g["p (one-sided)"] = g["p_one_sided"]
        return _table(g, ["year", "key", "n", "spearman", "p (one-sided)", "top1_hit", "top2_overlap", "coverage"])
    p0 = [f"{m}|L{l}" for m in ("P0H4", "P0H4_price", "P0H4-U", "CR", "CR-ANC", "UNI-FINAL", "CH1-LGBM", "E108") for l in (1, 2)]
    f10 = [f"{m}|L{l}" for m in ("FI10_L1sel", "FI10_L2sel", "FI10_damped", "FI10_naive") for l in (1, 2)]
    body = f"""Metrics: Spearman rank correlation between the model's provincial score and the published value (n = 5 per year), exact
one-sided permutation p over the 120 possible orders (smallest possible p = 0.008), top-1 hit (same worst province),
top-2 overlap. **MAE, RMSE and bias cannot be computed for any model:** every model outputs a probability of a
price-pressure or T43c event, not a percentage of households, so its level cannot be compared with a survey percentage.
Brier, AUC and classification metrics need binary labels, which the data do not support (Deliverable 11).

## Track A: FNRI 2015 severe food insecurity (FI10 only)
{rk('FNRI15_SEV', ['2015'], f10)}
## Track A: ENNS (mixed reference years; secondary)
**Severe**
{rk('ENNS_SEV', ['mixed'], f10)}
**Moderate-to-severe**
{rk('ENNS_MODSEV', ['mixed'], f10)}
## Track B: PSA food poverty (families), served P0H4 family, 2023
{rk('PSA_SUB_FAM', ['2023'], p0)}
## Track B: PSA food poverty (families), FI10, every wave and pooled
{rk('PSA_SUB_FAM', ['2018', '2021', '2023', 'pooled'], f10)}
Population-based results (`ranking_agreement.csv`, outcome `PSA_SUB_POP`) are within 0.1 of the family results.

## Reading
- **FI10 price-pressure forecasts rank provinces in the opposite order to food poverty.** Pooled ρ is between −0.44 and
  −0.01 at Leads 1–2, with no positive year at Lead 1. The realised price excess itself has ρ = {_f(F[(F.outcome == 'PSA_SUB_FAM') & (F.feature == 'price_excess')]['mean_spearman'].iloc[0])}:
  provinces with more food-price pressure had *less* food poverty. Against FNRI 2015 and ENNS the signs are also negative.
- **Served P0H4, 2023 food poverty:** ρ = {_f(R[(R.outcome == 'PSA_SUB_FAM') & (R.key == 'P0H4|L1') & (R.year == '2023')]['spearman'].iloc[0])} at Lead 1, p = {_f(R[(R.outcome == 'PSA_SUB_FAM') & (R.key == 'P0H4|L1') & (R.year == '2023')]['p_one_sided'].iloc[0])}; Lead 2 (three quarters) ρ = {_f(R[(R.outcome == 'PSA_SUB_FAM') & (R.key == 'P0H4|L2') & (R.year == '2023')]['spearman'].iloc[0])}.
  Not significant; one year, five provinces; the 2023 provinces are themselves not distinguishable (Q p = {_f(meas['PSA_SUB_FAM|2023']['q_p'])});
  about 40 model × lead cells were scored on these five values, so a p near 0.07–0.17 is expected by chance; and its
  top score is a Laguna–Rizal tie that the tie-break gives to Laguna, so it misses the worst province (Rizal). Lead 4 is ρ = −0.76.
- **No model reaches the locked rank-skill rule** (exact p < 0.05 and above the best baseline) on any outcome.
"""
    _w("04_PROVINCIAL_VALIDATION_REPORT.md", "Deliverable 4. Provincial validation report", body)
    files.append("04_PROVINCIAL_VALIDATION_REPORT.md")

    # 5 baselines
    bl = R[R["key"].str.startswith("BASE")]
    body = f"""Baselines are formed only from values available by 1 January of the reference year (rule: a survey value is usable from
1 January of reference year + 2, which is later than every actual PSA release).

## Ranking baselines
{_table(bl[bl['outcome'].isin(['FNRI15_SEV', 'ENNS_SEV', 'ENNS_MODSEV', 'PSA_SUB_FAM'])], ['outcome', 'year', 'key', 'n', 'spearman', 'p_one_sided', 'top1_hit', 'years_positive', 'n_years'])}
## Level accuracy, PSA food poverty (temporal validation: 2018 → 2021, 2018 + 2021 → 2023)
{_table(L, ['outcome', 'test_year', 'candidate', 'n', 'mae', 'rmse', 'bias', 'spearman', 'noise_floor_mae'])}
Candidates (fixed in the protocol): {'; '.join(f'{k} = {v}' for k, v in PROTOCOL['level_candidates'].items())}.
The noise floor is the MAE a perfect predictor of the true value would still have against the published estimate.

## Reading
- **The best ranking baseline for food poverty is the 2015 FNRI severe ranking** (pooled ρ = {_f(bl[(bl.outcome == 'PSA_SUB_FAM') & (bl.key == 'BASE:fnri2015_severe') & (bl.year == 'pooled')]['spearman'].iloc[0])}, positive in 3 of 3 waves,
  p = {_f(bl[(bl.outcome == 'PSA_SUB_FAM') & (bl.key == 'BASE:fnri2015_severe') & (bl.year == 'pooled')]['p_one_sided'].iloc[0])}). Prior poverty is the only cell below p = 0.05 (2018, ρ 0.90) but reverses in 2023 (−0.72).
- **The provincial ordering of food poverty is not stable:** 2018 vs 2021 ρ = 0.32, 2021 vs 2023 ρ = −0.70. Quezon fell
  from 4.7 % to 0.5 % of families. A persistence forecast of the ranking fails in 2023.
- **No level candidate wins both waves.** Persistence is best for 2021 (MAE 0.92 pp); the regional prior-wave value is best
  for 2023 (0.80 pp); the ridge with price pressure and poverty (trained on five rows) is worst (1.94 pp). The best candidate's
  error is 2.8–3.8× the noise floor because the whole region moved (COVID-19 rise in 2021, fall in 2023).
- **No model beats these baselines.** The only models that can be compared on the same rows (FI10, pooled) are below
  every positive baseline.
"""
    _w("05_BASELINE_COMPARISON_REPORT.md", "Deliverable 5. Baseline comparison report", body)
    files.append("05_BASELINE_COMPARISON_REPORT.md")

    # 6 features
    ok = F[F["status"] == "ok"]
    nv = F[F["status"] != "ok"].groupby("feature")["status"].first().reset_index()
    fam = pd.DataFrame([
        ("A1 food-price-pressure forecast", "FI10 forecasts; P0H4 pi_price; A1_food, A1_gap", "negative on 2018/2021 food poverty; 2023 pi_price ρ 0.82 (p 0.07, one year)"),
        ("A2 headline inflation", "head_m", "strongest positive: pooled ρ 0.47 (one-sided p 0.05, Holm 1.0)"),
        ("A3 rice price", "rice_m; val_A3", "negative (pooled −0.23; 2023 −0.82)"),
        ("V1 poverty + density", "poverty_inc; val_V1", "pooled +0.12; 2023 val_V1 −0.56"),
        ("C1 El Niño", "oni / val_C1", "no provincial variation"),
        ("C2 typhoons", "tc_365d / val_C2", "no variation in PSA years; 2015 ρ 0.58; 2023 ρ 0.16"),
        ("C3 palay/corn", "palay_yoy; val_C3", "pooled +0.29; 2023 −0.67"),
        ("C4 fisheries", "val_C4", "2023 only: +0.10"),
        ("E1 unemployment", "unemp_rate / val_E1", "national: no provincial variation"),
        ("E2 remittances", "remit_yoy / val_E2", "national: no provincial variation"),
        ("N1 FSSI / news", "news_prov_z; val_N1", "pooled +0.24; val_N1 has no provincial variation"),
        ("H1 regional hunger", "val_H1", "regional: identical for all provinces"),
    ], columns=["FIRI v2 family", "column tested", "association with provincial outcomes [R]"])
    body = f"""**Design limit.** With five provinces per year and at most three waves, a feature-ablation experiment on provincial
outcomes has no statistical power: removing a feature from a model trained on five rows changes nothing that could be
distinguished from noise. FI12 therefore measures each feature's **rank association** with each outcome (within-year
Spearman, pooled over waves, exact p, Holm correction within outcome). This is descriptive and not causal.

## The 12 FIRI v2 families (`backend/app/ml/inference/firi.py`)
{_table(fam)}
**Five of the twelve families (C1, E1, E2, H1 and, in served rows, N1) have no provincial variation.** They are national
or regional series copied to every province. They can move all provinces together but cannot tell provinces apart.

## Five trigger groups (FI10 as-of features, annual means of Lead-1 issue rows)
{_table(ok[~ok['group'].str.startswith('FIRI')], ['outcome', 'group', 'feature', 'n_years', 'mean_spearman', 'p_one_sided_positive', 'p_two_sided', 'holm_two_sided'])}
## FIRI v2 values in the served P0H4 rows (2023 only)
{_table(ok[ok['group'].str.startswith('FIRI')], ['outcome', 'feature', 'mean_spearman', 'p_one_sided_positive', 'p_two_sided', 'holm_two_sided'])}
## Not testable
{_table(nv)}
## Reading
- **No feature is associated with any provincial outcome after Holm correction** (every Holm p = 1.0).
- **Market features point the wrong way for food poverty:** food inflation excess, rice prices and the price-gap terms
  are negatively associated (realised price excess −0.45). Price pressure is highest in the more urban, less poor
  provinces. The family that drives P0H4's provincial differences is therefore the family least related to measured
  provincial food poverty.
- **Leakage and bias checks:** every feature is the as-of value used by FI10 at its issue date (FI10 as-of tests); the
  served P0H4 values are the served rows. National series copied to provinces are flagged above. SHAP was not used: with
  five observations per year no explanation of a fitted model would be meaningful.
"""
    _w("06_FEATURE_CONTRIBUTION_REPORT.md", "Deliverable 6. Feature contribution report (12 FIRI v2 families, five trigger groups)", body)
    files.append("06_FEATURE_CONTRIBUTION_REPORT.md")

    # 7 lead time
    f10s = fi10["selection"]
    body = f"""| Outcome | Maximum reliable lead | Basis |
|---|---|---|
| **A. Direct provincial food insecurity** | **Not verifiable** | One verified wave (2015) in which provinces are not distinguishable; ENNS one year per province, secondary, no SEs. No model has rank skill at any lead (Deliverable 4). Validation needs at least two comparable waves with forecasts issued before them |
| **B. Provincial food poverty** | **None** | Three waves; no model or baseline ranks provinces consistently; FI10 Leads 1–4 pooled ρ ≤ 0.25, never significant; P0H4 2023 only |
| **C. Regional SWS hunger** | **Lead 1, persistence only** (FI7 rules); none under the FI9-Z HIGH-recall ≥ 0.60 requirement | FI7/FI9/FI9-Z/FI11 [F]: naive persistence accuracy 0.871, balanced accuracy 0.743; nothing learned beats it |
| **D. Food-price pressure** | **None adopted; Lead 2 provisional** | FI10 [F]: no lead passed every locked requirement (Lead 1 failed: {', '.join(f10s['1']['checks'] and [k for k, v in f10s['1']['checks'].items() if v is False])}); tuned LightGBM beats both persistence rules on Lead-2 Brier in the forensic audit recomputation, but was not the locked selection |

A future map quarter is not evidence of a forecast lead. The dashboard can draw any quarter; a lead is reliable only
where forecasts issued that far ahead have been scored against observations.
"""
    _w("07_LEAD_TIME_ASSESSMENT.md", "Deliverable 7. Lead-time assessment", body)
    files.append("07_LEAD_TIME_ASSESSMENT.md")

    # 8 overfitting leakage bias
    body = """| # | Risk | Where | Finding | Impact |
|---|---|---|---|---|
| 1 | Publication year used as reference year | matching | Not done: reference years only; ENNS by province-specific year | — |
| 2 | Future information | matching, baselines | Every forecast issued before its target quarter (asserted); baselines use values available by 1 Jan of the reference year under a conservative rule | — |
| 3 | Regional SWS copied to provinces | P0H4 family | P0H4's hunger term is one Balance Luzon value for all provinces; provinces differ only through price | P0H4 cannot express provincial food-insecurity differences except through price |
| 4 | National series copied to provinces | FIRI C1, E1, E2, H1, N1 | No provincial variation | They cannot rank provinces |
| 5 | Contemporaneous poverty as a predictor of subsistence | baselines | Avoided: poverty and subsistence come from the same FIES; only prior waves are used | Using same-year poverty would leak the outcome |
| 6 | Workbook transcription | ENNS | 10 records secondary and unverified; compiled with an AI assistant; severe vs moderate-to-severe ρ −0.1 within one survey | ENNS treated as descriptive only |
| 7 | Instrument change | FNRI 2015 (HFIAS) vs later FIES | Severe 17–21 % (2015) vs 1.5–2.4 % (ENNS 2021) and 1.7 % (2023 regional) | Not comparable across waves; never pooled |
| 8 | Province definition | Quezon | PSA excludes Lucena; FNRI/ENNS unknown | Possible mismatch, unverified |
| 9 | Multiple comparisons | P0H4 family on PSA 2023 | ~40 model × lead cells on five values | Best p ≈ 0.07 expected by chance |
| 10 | Overfitting | level model L4 | Ridge trained on five rows is the worst level candidate | Confirms that a provincial model cannot be trained on these data |
| 11 | Selection on test data | all | Candidates, metrics and decision rules locked before scoring; one smoke test on randomised values only; no re-lock | — |
| 12 | Province bias | FI10 | Quezon (highest food poverty 2018/2021) has the lowest price pressure; price models systematically under-rank it | Price-driven maps under-prioritise the poorest province |
| 13 | FI10 configuration selected on a period including 2015 | FI10 | Selection used price labels to 2015, not FNRI labels | Small; disclosed |
"""
    _w("08_OVERFITTING_LEAKAGE_BIAS_AUDIT.md", "Deliverable 8. Overfitting, leakage and bias audit", body)
    files.append("08_OVERFITTING_LEAKAGE_BIAS_AUDIT.md")

    # 9 model comparison
    def best(oid, key, yr):
        g = R[(R.outcome == oid) & (R.key == key) & (R.year == yr)]
        return _f(g["spearman"].iloc[0]) if len(g) else "–"
    rows = [
        ("Served P0H4", "B: T43c proxy (regional hunger × provincial price)", "SWS BL + PSA CPI + 12 FIRI families", "province (price) × region (hunger)", "LightGBM × closed-form hunger", "L1 reliable on T43c [F]", "n/a (probability)",
         f"T43c L1 acc 0.843, BA 0.776 [F]; PSA 2023 ρ {best('PSA_SUB_FAM', 'P0H4|L1', '2023')} (n 5)", "beats PERSIST-SI on T43c; no provincial baseline comparison possible beyond 2023", "T43c Lead 1 only", "keep; label as proxy"),
        ("P0H4-U / CR / CR-ANC / UNI-FINAL / CH1-LGBM / E108", "B", "same family", "same", "variants", "L1 [F]", "n/a",
         f"PSA 2023 ρ: P0H4-U {best('PSA_SUB_FAM', 'P0H4-U|L1', '2023')}, CR {best('PSA_SUB_FAM', 'CR|L1', '2023')}, CR-ANC {best('PSA_SUB_FAM', 'CR-ANC|L1', '2023')}, UNI {best('PSA_SUB_FAM', 'UNI-FINAL|L1', '2023')}, CH1 {best('PSA_SUB_FAM', 'CH1-LGBM|L1', '2023')}, E108 {best('PSA_SUB_FAM', 'E108|L1', '2023')}", "none", "none on provincial outcomes", "no challenger better"),
        ("FI10 (L1 selection)", "D: provincial food-price pressure", "PSA provincial CPI + 5 trigger groups", "province", "pooled LightGBM", "none adopted [F]", "n/a",
         f"price L1 BA 0.725 [F]; food poverty pooled ρ {best('PSA_SUB_FAM', 'FI10_L1sel|L1', 'pooled')}; FNRI 2015 ρ {best('FNRI15_SEV', 'FI10_L1sel|L1', '2015')}", "ties damped persistence on price; below every food-poverty baseline", "price: provisional", "keep as price pressure only"),
        ("FI9 C0", "C: regional SWS hunger", "SWS BL", "Balance Luzon", "damped persistence", "L1 provisional [F]", "conformal interval", "acc 0.823, BA 0.714 [F]", "below naive persistence", "regional only", "keep, provisional"),
        ("Naive persistence (SWS)", "C", "SWS BL", "Balance Luzon", "latest reading", "L1 (FI7 rules) [F]", "—", "acc 0.871, BA 0.743 [F]", "is the baseline", "best regional", "reference"),
        ("FI11", "C", "SWS + 5 triggers", "Balance Luzon", "ridge/LightGBM/logit/RF", "none [F]", "—", "L1 BA 0.746 [F]", "not better than naive", "none", "rejected"),
        ("FNRI 2015 severe ranking (baseline)", "B (as predictor)", "FNRI 2015", "province", "static ranking", "—", "—", f"food poverty pooled ρ {best('PSA_SUB_FAM', 'BASE:fnri2015_severe', 'pooled')}", "best ranking baseline; not significant", "—", "context"),
        ("Regional prior-wave value (baseline)", "B levels", "PSA", "CALABARZON", "constant", "—", "MAE 1.10 (2021), 0.80 (2023)", "—", "best 2023 level", "—", "context"),
    ]
    body = _table(pd.DataFrame(rows, columns=["Model", "Target", "Data source", "Geography", "Methodology", "Lead time", "MAE/RMSE", "Metrics", "Baseline improvement", "Reliability", "Decision"]))
    body += """
## Winners by target
| Target | Best | Why |
|---|---|---|
| A. Direct provincial food insecurity | **None can be identified** | No model has historical forecasts for a verified, distinguishable observation |
| B. Provincial food poverty | **No model.** Best simple reference: FNRI 2015 severe ranking (ranks) and regional prior-wave value (levels) | Neither is significant; nothing beats them |
| C. Regional SWS hunger | **Naive persistence** (FI9 C0 is the served, provisional variant) | Earlier studies [F] |
| D. Food-price pressure | **FI10 pooled LightGBM** (Lead 2 provisional) | Earlier studies [F] |
| Overall methodology | **Two separate, honestly labelled layers** (regional measured hunger outlook + provincial price-pressure and vulnerability context) | Deliverable 10 |

No model is declared a winner across incompatible outcomes.
"""
    _w("09_COMPLETE_MODEL_COMPARISON.md", "Deliverable 9. Complete model comparison", body)
    files.append("09_COMPLETE_MODEL_COMPARISON.md")

    # 10 methodology
    body = """The simplest methodology the evidence supports:

| Element | Recommendation |
|---|---|
| What is predicted | (1) **Next-quarter Balance Luzon hunger** above its normal (measured food insecurity, regional). (2) **Provincial food-price pressure** next quarter (a driver, labelled as such). Neither is presented as a provincial food-insecurity rate |
| Outcome labels | SWS hunger for (1); PSA provincial food CPI for (2). FNRI/ENNS and PSA subsistence are **external validation references**, never training labels |
| Predictors | Latest SWS reading (persistence) for (1); FI10 trigger groups for (2) |
| Five provinces | Shown through price pressure (forecast), poverty and food-poverty context (latest PSA wave with its CI), and the 2015 FNRI and ENNS values as dated, labelled references. Provinces are not ranked by a "food-insecurity forecast" |
| 12 FIRI families | Descriptive context. Five families have no provincial variation; none is associated with provincial outcomes; none is a validated provincial food-insecurity predictor |
| Prediction | FI9 damped persistence + conformal interval; FI10 pooled model per lead |
| Uncertainty | Conformal interval for SWS; probability and track record for FI10; published CIs for every survey value |
| Validation | Prospective register (FI9, FI10) plus FI12 re-run whenever a new provincial wave appears (PSA 2026 FIES; FNRI NNS) |
| Lead time | Regional hunger: one quarter (persistence). Provincial food insecurity: **none verified** |
| Limitations | No repeated, comparable provincial food-insecurity series; provinces not distinguishable in the only verified FI wave; food-poverty ordering unstable between waves; price pressure is negatively related to provincial food poverty |

**Not recommended:** a provincial food-insecurity model trained on the workbook (five rows per wave), any HIGH/LOW label
from these percentages, or using P0H4's provincial ranking as a ranking of food insecurity.

**What would make provincial forecasting testable** (public data only, no requests):
- FNRI ENNS 2018–2021 and NNS 2023 household public-use files (blocked from this network; downloadable by the owner from
  another network) → provincial FIES estimates with SEs for 2018, 2019, 2021, 2023: four comparable waves.
- PSA 2026 FIES provincial poverty and subsistence (expected 2027).
- Approximate requirement: detecting a true provincial rank correlation of 0.6 at α = 0.05 with 80 % power needs about
  16 independent province-wave pairs (Fisher z), i.e. at least four comparable waves of five provinces; 0.4 needs about
  eight waves.
"""
    _w("10_FINAL_METHODOLOGY_RECOMMENDATION.md", "Deliverable 10. Final methodology recommendation", body)
    files.append("10_FINAL_METHODOLOGY_RECOMMENDATION.md")

    # 11 objective
    hi = sum(len(v.get("significantly_above_region", [])) for k, v in meas.items() if k.startswith("PSA_SUB_FAM|"))
    body = f"""| Target | Is 75 % accuracy achievable and meaningful? | Verdict |
|---|---|---|
| A. FNRI/ENNS direct provincial | No defensible HIGH/LOW classes: in 2015 no province differs from the region; ENNS has no SEs. Accuracy over five provinces moves in 20-point steps (4/5 = 80 % is one province) | **Unsupported** |
| B. PSA food poverty | Only {hi} province-years are significantly above CALABARZON (Quezon 2018, 2021); the protocol needs ≥ 3 HIGH and ≥ 3 LOW, so no accuracy can be computed. Ranking and level metrics show no skill | **Unsupported** |
| C. SWS regional hunger | Accuracy 0.871 (naive persistence) is above 75 %, but always-LOW scores 0.823; balanced accuracy 0.743 | **Partially achieved** (by persistence, regional only) |
| D. Price pressure | FI10 accuracy 0.73–0.74 (Leads 1–2), below 75 %; and it is not food insecurity | **Not achieved; wrong construct** |

**Recommended measure instead of accuracy:** for provincial outcomes, rank agreement (Spearman with exact p) and level
error (MAE against the published CI); for regional hunger, balanced accuracy, HIGH recall and Brier score against
persistence. A high accuracy on one target is never used to claim success on another.
"""
    _w("11_OBJECTIVE_ACHIEVEMENT_ASSESSMENT.md", "Deliverable 11. Objective achievement assessment (75 %)", body)
    files.append("11_OBJECTIVE_ACHIEVEMENT_ASSESSMENT.md")

    # 12 adoption
    body = """**Decision: the current production model stays unchanged. No challenger is eligible.**

- P0H4 remains served. It is the best-validated model **for its own target (T43c, Lead 1)**. The provincial outcomes do not
  validate it as a provincial food-insecurity forecaster: it can be matched to one five-province wave of food poverty
  (2023), where its agreement is not significant, and its provincial signal (price pressure) is negatively related to
  provincial food poverty in the only multi-wave test.
- No other model performs better on any provincial outcome. FI10 is worse than every positive baseline on food poverty.
- Nothing was changed in production: P0H4 artifacts, predictions, dashboard leads, map and indicators are untouched;
  FI12 writes only `backend/data/fi12/` and `docs/fi12/`.

**Recommended wording changes (owner decision, not made):**
- The welcome tour and map legend should not say the map forecasts food insecurity "in each CALABARZON province". A
  defensible wording: "regional hunger outlook combined with each province's food-price pressure".
- Show the dated FNRI 2015, ENNS and PSA food-poverty values as provincial references with their source and year.

**Rollback:** not applicable; nothing was deployed. To remove FI12, delete `backend/app/fi12`, `backend/data/fi12`,
`docs/fi12` and `backend/tests/unit/test_fi12.py`.
"""
    _w("12_PRODUCTION_ADOPTION_DECISION.md", "Deliverable 12. Production adoption decision", body)
    files.append("12_PRODUCTION_ADOPTION_DECISION.md")

    # cross-source consistency (descriptive, after lock)
    V = T[T["outcome"].isin(["FNRI15_SEV", "ENNS_SEV", "ENNS_MODSEV", "PSA_SUB_FAM"])].copy()
    V["k"] = V["outcome"] + "|" + V["reference_year"].astype(str).where(~V["outcome"].str.startswith("ENNS"), "own year")
    P = V.pivot_table(index="province", columns="k", values="value")
    cc = pd.DataFrame([{"a": a, "b": b, "spearman": spearman(P[a], P[b])} for a, b in itertools.combinations(P.columns, 2)])
    idx = "\n".join(f"{i + 1}. [{f}]({f})" for i, f in enumerate(files))
    readme = f"""**Question.** Can aiPHeed reliably forecast food insecurity at the provincial level, judged against independently
measured provincial observations?

**Answer.** No, and the available observations cannot show that any model does.
- The only verified direct provincial food-insecurity wave (FNRI 2015) cannot separate the five provinces statistically.
- The ENNS provincial values are secondary, mix three years and show internally inconsistent rankings.
- Every P0H4-family forecast starts in 2023, so the served model can be matched to one wave of food poverty only.
- FI10 price-pressure forecasts, the only ones covering every wave, rank provinces opposite to food poverty.
- No model beats simple references, no feature survives correction, no defensible HIGH/LOW label exists, and the 75 %
  target is unsupported for provincial outcomes.
- P0H4 stays served; nothing in production changed.

## Deliverables
{idx}

## Code and outputs
- Code: `backend/app/fi12/` (`outcomes.py`, `match.py`, `study.py`, `report.py`); tests `backend/tests/unit/test_fi12.py`.
- Protocol lock: `backend/data/fi12/out/PROTOCOL_LOCK.json` (frozen before any agreement was computed).
- Outputs: `backend/data/fi12/out/` (outcomes, matches, ranking, levels, features, evaluation).
- Reproduce: `cd backend && python -m app.fi12.study run && python -m app.fi12.report`.

## Cross-source consistency of the outcomes (descriptive, computed after the lock)
{_table(cc)}
The sources do not agree on which province is worst; two measures from the same ENNS survey rank provinces with ρ −0.1.
"""
    _w("README.md", "FI12: provincial food-insecurity validation and model reassessment", readme)
    return files


if __name__ == "__main__":
    print("\n".join(build()))

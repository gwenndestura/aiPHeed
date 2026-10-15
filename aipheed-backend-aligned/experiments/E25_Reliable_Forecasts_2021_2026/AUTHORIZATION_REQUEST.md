# Authorization request: files needed from the researcher

**What E25 is waiting for.** Nothing below has been opened, fetched or filled.

- Every item is listed as "pending" in `DATA_COMPLETENESS_MATRIX.csv`.
- **How to authorize:** supply the file and its full SHA-256. E25 verifies the hash by script; it never types or abbreviates one.
- For outcomes, add an entry to `inputs/AUTHORIZED_OUTCOMES.json` (format in `runner/score_sealed.py`).
- Each file must contain **only** the authorized period. A mixed file is refused, never filtered.

## A. Needed for a complete, valid 2027-Q1 forecast (operational lead 1)

**Cutoff:** 2026-12-31 23:59:59 PHT. The cycle then runs on or after 2027-01-01.

| # | File | Why | Used by | Source / who supplies |
|---|---|---|---|---|
| A1 | **SWS September 2026 round** (Balance Luzon hunger %), as a file with only that round, **plus its publication date with evidence** | The latest regional hunger level before the cutoff, for the H part of FINAL_T1 (PCF21). It also completes the 2026-Q3 label, which the threshold and the persistence baselines need. | PCF21 (H), τ, B1, B1p | Researcher authorizes; source SWS. **Do not ask E25 to open SWS pages.** |
| A2 | **Provincial food CPI YoY, July, August and September 2026** (5 provinces), with the RSSO IV-A or national release dates | D(2026-Q3) is the latest full quarter of provincial relative food inflation before the cutoff | PCF21 (D), M3_21, all T1 labels for 2026-Q3 | Researcher authorizes; source PSA OpenSTAT 0012M4ACP23 (query those months only) |
| A3 | **Provincial food CPI YoY, October and November 2026** (5 provinces), with release dates | Dnow(2026-Q4) for M4_21 (FINAL_T2, provincial price pressure) and the NOW variants. **Not needed by FINAL_T1.** | M4_21, PCF21_NOW, D_HIER_NOW | As A2 |
| A4 | **2026 news articles (October–December 2026)** with original publication times, and 2026 government indicators for the feature models | The required Chapter I baselines B2–B6 and the proposed LightGBM need news of the reference quarter and government indicators of the quarter before. **PCF21 does not use them.** The dashboard shows supporting news only as context. | B2–B6, PROPOSED | Researcher authorizes; aiPHeed fetchers |
| A5 | Nothing (time) | The cutoff 2026-12-31 23:59:59 PHT must pass; the forecast cannot be produced earlier | — | — |

**Minimum for the FINAL_T1 forecast alone:** A1 + A2 + A5. With A3, the T2 price-pressure part. With A4, the Chapter I baselines can also be scored for that cycle.

## B. Needed to score the sealed forecasts (the only route to C9, generalization)

| # | File | Scores |
|---|---|---|
| B1 | SWS September 2026 round (same as A1) + CPI July–September 2026 (same as A2) | E24v2 seal targets **2026-Q3** (in-scope arms B1, B1p, M2; T2 B1) |
| B2 | SWS **December 2026** round with its publication date (published around January 2027) + CPI **October–December 2026** | E10 seal (2026-Q4), E24v2 seal (2026-Q4), **E25 seal `SEAL_E25_20261014T002548Z` (2026-Q4, FINAL_T1 and 13 other arms)** |
| B3 | SWS **March 2027** round + CPI **January–March 2027** | E24v2 and E25 seals for **2027-Q1** |

A generalization claim needs **≥ 8 scored forecast dates and ≥ 5 LOW (and ≥ 5 HIGH) rows** (protocol §9). With one new quarter per three months, that is about two years of authorized outcomes.

## C. Optional, to improve completeness

| # | File | Why |
|---|---|---|
| C1 | **Verified publication dates of the March and June 2026 SWS rounds** | Only an upper bound (2026-09-10, the fetch time) is known. A verified date would let origins between publication and September use them. No backtest result changes, because both bounds lie after every backtest origin. |
| C2 | **PSA 2021 municipal Small Area Estimates workbook** (with its SHA-256) | 126 of 142 LGUs carry a province-mean poverty substitute, so their within-province rank reflects density only. Ingest with `runner/lgu_rankings.py --sae <path> --sae-sha256 <hash>`. psa.gov.ph and foi.gov.ph refused automated access (HTTP 403, E24); this was never bypassed. |
| C3 | **Confirmation (A6)** that E24v2's public PSA file `cpi_index_2021_2025_ACP22.csv` (2021–2025 rows only, SHA-256 in `inputs/INPUTS_MANIFEST.json`) may be used | It feeds Dnow and the monthly evaluation. It is in window and public, but your confirmation is still pending. |
| C4 | PSA's published **2021 monthly provincial food YoY** (2021-01…2021-12 only) | Would extend the monthly evaluation from 54 to 66 months. 2021 YoY cannot be computed in window, because it needs 2020 indices. |
| C5 | Your decision on `features_fused.parquet`: it also holds 2020 rows, read with a read-time filter so no 2020 row reaches the analysis | If you rule that no file containing pre-2021 rows may be opened at all, the six required feature baselines and the proposed LightGBM **cannot be computed**. No window-only feature file exists. |

## D. What is authorized now (for reference)

| Item | Coverage |
|---|---|
| 2021–2025 inputs | E17/E18 allowlist |
| Provincial food CPI YoY | January–June 2026 |
| SWS Balance Luzon rounds | March and June 2026 |
| Everything from July 2026 on | **Protected** |
| 2026 news and 2026 government indicators | **Not authorized** |

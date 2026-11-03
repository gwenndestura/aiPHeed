# RELIABLE_NEWINFO, Step 0: unused sources that could explain 2015–2020 (EXPLORATORY)

**Written:** 2026-11-03. No model was fitted and no result computed. The stored REF Lead-1 walk-forward forecasts
(`IMPROVE_V2_LEADS/out/forecasts_leads.csv`) and the BL labels were read to describe the failure.

## 1. What fails in 2015–2020

REF fails only R7. The middle third of the verdict window (2015-Q2..2020-Q4) scores 12 of 21 correct (0.571); the rule
needs 0.60, i.e. 13 of 21.

| Third | Errors | Labels within 1 SE (2.9 pt) of 11.3% | Errors within the SWS 95% margin (±5.7 pt) | Times the line was crossed |
|---|---|---|---|---|
| 2010-Q1..2015-Q1 | 1 of 21 | 2 | 1 of 1 | 2 |
| **2015-Q2..2020-Q4** | **9 of 21** | **12** | **8 of 9** | **9** |
| 2021-Q2..2026-Q3 | 3 of 20 | 8 | 3 of 3 | 4 |

**What the errors look like.**
- In 2015–2018, Balance Luzon hunger alternates around the line almost every quarter: 10.7, 14.7, 9.7, 13.8, 11.7,
  15.0, 11.3, 8.3, 13.8, 17.7, 11.0, 7.3, 12.7, 9.7.
- The model mostly follows the last reading, so it is wrong after each reversal.
- 8 of the 9 errors are quarters whose reading lies within SWS's own 95% sampling margin of the threshold. SWS
  reports ±5.7–6 points for Balance Luzon, from 300 respondents.

**Reading.** The failure looks like survey sampling noise around a fixed line, not a missed economic signal.

**Consequence for any attempt.** R7 needs only **one** more correct quarter in that third (13 of 21). Any new input
therefore has a real chance to pass R7 by luck, and a pass would be weak evidence.

## 2. Candidate sources

| Source | In the repo? | Years available | Publication timing | Level | Usable for an honest attempt? |
|---|---|---|---|---|---|
| **BSP OFW cash remittances** (monthly) | Only 2021-Q1..2026-Q2 (`FIRI_V2_DATA_AUDIT/data/bsp_cash_remittances_quarterly.csv`, rebuilt from releases). **Not before 2021** | BSP has published since about 1990 (HISTORY_RETRAIN `DATA_INVENTORY.md`, row E2). Needs your file in `data/raw/` | About the 15th of month m+2: a 6–7-week lag (e.g. June 2026 data on 2026-08-17; March 2026 on 2026-05-15) | National | **Yes, technically**, if you supply 1998–2020. **Weak prior**: a smooth national trend cannot follow quarter-to-quarter BL swings |
| **Rainfall** | No | PAGASA station data: by formal request (CADS forms; free for academic, non-commercial use), not openly downloadable. Open alternative: **CHIRPS** monthly, 1981–present (v3.0 replaced v2.0 in Dec 2024) | CHIRPS final: about 3 weeks (after the 20th of month m+1). PAGASA: on request | 0.05° grid → provincial / regional means | **Yes, technically (CHIRPS).** **Weak prior**: overlaps inputs already in REF (ONI, typhoons, palay/corn and fisheries production) |
| **Rice import / tariff policy dates** | No | Events: the 2018 NFA rice shortage and inflation peak; RA 11203 Rice Tariffication (signed 2019-02-14, effective 2019-03-05; dates from knowledge, not checked online here) | Known on the day | National | **No.** One or two events, picked after seeing the failing period. A dummy for them fits the period rather than testing it. Most errors (2015–2018) precede RA 11203 |
| **DSWD 4Ps coverage** | No | No clean dated regional series found. Scattered DSWD IV-A figures (e.g. 329,463 households, SY 2015–16; 546,013 beneficiaries, 2018, a different unit) | Annual reports, publication dates unclear | Regional, annual | **No.** Not a dated series, annual, and roughly flat over 2015–2020 |
| (Already tried) LFS unemployment E1 | Yes, 2005+ | — | — | National | **Not new.** HISTORY_RETRAIN option (c) used it, and it feeds the PSA-only baseline |

## 3. Verdict

**Two sources are usable in the narrow sense** (dated, available back to 1998, leakage-safe): BSP remittances (needs
your file) and CHIRPS rainfall.

**Neither is a plausible explanation of the 2015–2020 errors.** Those errors are quarter-to-quarter reversals of
readings that sit within SWS's own sampling error of the line. With R7 one quarter from passing, a pass with either
input would most likely be luck.

**Recommendation: "no honest attempt left."** The 2015–2020 failure is a limit of the target, a 300-respondent survey
area measured against a fixed 11.3% line, rather than missing information.

**If you still want the one last attempt,** BSP remittances (one family, with your file) is the more defensible choice.
It is the only one of the four named sources that the paper's own driver list includes (OFW remittance, currently
"not an input").

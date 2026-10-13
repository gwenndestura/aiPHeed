# E10: Prospective Evaluation Protocol for 2026-Q4 (frozen before any forecast)

**Status:**

- Protocol frozen 2026-10-12; its SHA-256 is recorded in `05b_FREEZE_RECORD.md`.
- **No forecast has been generated.** Generation needs your explicit go-ahead (§9).
- This is **prospective research** on one quarter. It is **not** an untouched historical test. It does not change production, the served model, thresholds or the dashboard.

## 1. Target and threshold

**S1 stress for 2026-Q4, per province:**

stress(p, 2026-Q4) = SWS_Q4 + 2 × (YoY(p) − mean of the five provinces' YoY)

| Element | Definition |
|---|---|
| SWS_Q4 | Mean Balance-Luzon involuntary-hunger % of SWS national adult-population rounds with fieldwork between 2026-10-01 and 2026-12-31. Registered-voter-only surveys are excluded; the April 2025 registered-voter round was likewise not collected for the training inputs. Whether the training registry contains any registered-voter round was not checked. |
| YoY(p) | Mean of the monthly provincial food CPI year-on-year % for October, November and December 2026. Source: PSA OpenStat table **0012M4ACP23**, commodity "01.1 - FOOD", the same province codes as `openstat_fetcher.py`. Same quarterly averaging as the training data (`_to_quarterly_avg`). **First-release values are primary.** |
| Regional mean | Defined only if all five provinces have a value; otherwise S1 is not computable for the quarter |
| Event | **HIGH if stress > τ = 14.345.** This is the approved prospective reference: median S1 of the 16 labels published before 2026-07-01, frozen. **Not tuned.** |

**Horizon:** one quarter (target 2026-Q4).

**Evaluation period:** 2026-Q4 only. The outcome becomes computable only after the December 2026 CPI release and the publication of the Q4 SWS round(s), **expected in 2027**.

## 2. Issue time and information cutoff

| Item | Rule |
|---|---|
| Issue time | The timestamp of the sealed `predictions.csv` (§7) |
| Issue deadline | **2026-10-31 23:59 Asia/Manila.** This is before the earliest plausible release of October 2026 CPI, expected in early November under PSA's documented first-week practice (schedule, not a verified date). If the forecast cannot be sealed by then, **no forecast is made.** |
| Information cutoff | Only inputs with **dated evidence of availability** at or before the input snapshot time, and before the issue time |
| Accepted evidence | (a) a verified publication date in the SWS registry; (b) a dated retrieval record (`retrieved_at_utc`); (c) the git commit date of a file whose bytes contain the value |
| Not accepted | **Proxy publication dates** (national + 14 days) and schedule dates |
| Always excluded, whatever their availability | Protected values: 2026-Q3 outcome components (July–September 2026 CPI; SWS rounds with fieldwork July–September 2026) and any 2026-Q4 data |

## 3. Eligible inputs (frozen list)

| Input | Value to be used | Availability evidence |
|---|---|---|
| `sws_hunger` | March 2026 SWS round (2026-Q1) | Published 2026-05-12, **verified** (registry) |
| — | **June 2026 round: excluded.** Its publication date is undocumented and is not substituted. | — |
| `sws_change` | March 2026 minus November 2025 | November 2025 published 2026-01-14 (verified-single) |
| `sws_age` | 3 quarters, at the staleness limit (only > 3 is stale) | Disclosed |
| `cpi_rel(p, 2026-Q2)` | Mean of April–June 2026 monthly YoY per province, minus the five-province mean | `provincial_food_cpi_yoy_2026H1_raw.csv` (30 rows, status "reported"), **retrieved 2026-10-09T14:40:49Z.** The official RSSO IV-A provincial release dates are **unverified**; the retrieval record is the availability evidence. |
| `last_published_stress` (**primary**) | S1 for **2026-Q1**: March 2026 SWS + January–March 2026 YoY from the same file | Components evidenced as above (available by 2026-10-09) |
| `last_published_stress` (**sensitivity**) | S1 for 2025-Q4 | 2025 CPI in `psa_indicators.parquet`, byte-identical to git blob `03a4ec47…` committed 2026-09-10; November 2025 SWS published 2026-01-14 |
| Training data for M1 | S1 labels 2021-Q2 to 2025-Q4 (+ 2026-Q1 in the primary variant); E9 feature construction; guard-read with `quarter <= 2025-Q4` for the 2021–2025 files | As in E9 |

**Not used:**

| Input | Reason |
|---|---|
| `food_cpi` index level | No approved 2026 source; never derived from YoY |
| News, rice, fuel, FX, climate | As in E9 |
| July–December 2026 CPI | Protected |
| Any 2026-Q3 or Q4 SWS round | Protected |

## 4. Forecasts to be produced (frozen)

| Arm | Output | Definition |
|---|---|---|
| **P: S1 formula rule (primary)** | Stress; HIGH if > 14.345 | `sws_hunger` + 2 × `cpi_rel(p, 2026-Q2)` |
| B1 carry-forward | Stress | `last_published_stress` (primary: 2026-Q1; sensitivity: 2025-Q4) |
| B2 regional | Stress | `sws_hunger` |
| M1 core LightGBM (experimental) | Stress (regressor) + uncalibrated probability (classifier, HIGH if p ≥ 0.50) | E9 settings: `num_leaves=4`, 100 trees, lr 0.05, `min_child_samples=5`, seed 42, monotone +1 on SWS and last stress; inputs `last_published_stress`, `sws_hunger`, `sws_change`; events at τ = 14.345 |

**INSUFFICIENT_DATA** for an arm and province applies if:

- a required input is missing (never zero, never estimated); or
- `sws_age` > 3.

## 5. Outcome collection (separate approval, after the seal)

1. Verify all sealed hashes first. Any mismatch voids the forecast.
2. Collect the §1 components from primary PSA and SWS sources, recording URLs, retrieval timestamps and **publication dates**.
3. Store them in `q4/outcome_*.csv` and hash them before scoring.
4. **Validity check (from the E8 r2 review, R2):** compare each Q4 component's first publication date with the issue time. If any Q4 component was published **before** the seal, Q4 is reclassified **exposure-qualified** (descriptive only).

## 6. Evaluation (single prospective quarter; descriptive only)

| Measure | Applies to |
|---|---|
| Province absolute stress error; MAE; regional-level error | P, B1, B2, M1 |
| Concordant pairs out of 10 (ties ½); top-province hit | P, B1, M1 (B2 has no ranking) |
| HIGH/LOW calls at 14.345; correct calls; per-class recall if both classes occur | All arms |
| Brier | M1 probability only |

**Reported label:**

- "one prospective quarter; outcome unseen at issue; inputs availability-evidenced (official provincial release dates unverified)", **or** the downgraded label from §5.4.

**Not claimed:**

- gross failure;
- superiority or significance;
- calibration;
- a 75% accuracy result;
- food-insecurity validity.

## 7. Freeze and record-keeping procedure (at generation)

1. Record the SHA-256 of this protocol (`05b_FREEZE_RECORD.md`, done now) and of the generation code.
2. Run under the guard. Write to a new `q4/` folder:
   - `inputs_snapshot.csv`: every input value, its source file and hash, and its availability evidence;
   - `predictions.csv`: all arms;
   - `manifest.json`: hashes of the protocol, code, inputs, snapshot, predictions and environment.
3. Set the `q4/` files read-only.
4. **External witness:** on the same day, you email the manifest's SHA-256 to your adviser. This gives an independent timestamp. Claude cannot do it for you.
5. **Before outcome collection:** re-verify every hash.

## 8. Missing, delayed, revised or unavailable data

| Situation | Rule |
|---|---|
| An input in §3 fails its hash or evidence check | No forecast is made; nothing is substituted |
| A province's 2026-Q2 YoY is missing | `cpi_rel` is undefined for **all** provinces (the five-province mean needs all five). P becomes INSUFFICIENT_DATA; B1, B2 and M1 continue. |
| Q4 SWS round not conducted, or not published before the thesis is finalized | No outcome: Q4 reported as **pending**, forecast preserved. No proxy outcome. |
| A Q4 provincial CPI value is missing | S1 not computable for the quarter: not evaluable |
| CPI revised after first release | First release is primary; revised values only as a labelled sensitivity |
| Issue deadline missed | No forecast; Q4 is not used |

## 9. Still needed before generation

- **Your explicit go-ahead to generate and seal.** The request that produced this protocol ended mid-sentence at the generation restriction.
- Your agreement to use **2026-Q1 as the primary last published label.** This includes an exposed 2026 quarter as an input. The E8 default was to exclude it; the 2025-Q4 alternative is computed as a sensitivity either way.

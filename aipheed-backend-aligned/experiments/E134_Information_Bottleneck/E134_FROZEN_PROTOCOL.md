# E134 frozen protocol: resolving the predictive information bottleneck

**Freeze.** Written and hashed **before** any E134 candidate was computed. The SHA-256 is in `runner/PROTOCOL_SHA256.txt`.

**Computed before the freeze:**
- the E133 reproduction (`out/e134_baseline_record.json`: 524 rows, maximum forecast difference 0.0);
- the acquisition of the new raw data (`data/acquisition_log.json`).

No new data value had been joined to any outcome.

**Scope.** Branch `aiPHeed/corrected-data-pipeline`, start `56d1ec1`. Offline only. Production, the dashboard, FIRI v2/FIRI3 and the E131–E133 seals are unchanged. Local commits only.

**Unchanged (never changed after results):**
- target: SWS involuntary hunger, 4 areas, 2021-Q2 … 2026-Q3;
- primary tolerance 1.645 × SE;
- the 75 % requirement;
- leads per `target.py`;
- N1–N7;
- P-DASH as the primary issue policy (P-REL reported separately and never selected);
- evaluation sets S-U (primary) and S-E132;
- study window 2021+. Pre-2021 use is only analysed for feasibility (§6), never loaded.

**Data status.** Every SWS value in the window has been seen. **Results are development evidence**; confirmation is prospective (§7).

## 1. New information tested (acquired in E134, 2021+ only)

| Id | Driver | Source | Geography | Availability at issue |
|---|---|---|---|---|
| aR | **Area rainfall deficit:** −z of the quarter's total precipitation relative to the in-fold mean of the same calendar quarter (needs ≥ 2 same-quarter values), mean over the area's regional points | NASA POWER daily PRECTOTCORR at 18 regional centres | The 4 SWS areas (equal region weights, as for CPI) | Quarter end + 10 days |
| aP | **Area palay production drop:** −(YoY % change of quarterly palay production), summed over the area's regions; 2022+ only (no pre-2021 base) | PSA OpenSTAT `0012E4EVCP0` | Regions → 4 areas | Quarter end + 75 days (conservative publication rule) |

**Area drivers enter at the area level.** Each area driver z_a moves the area level c + d_a by β·z_a:
- the area mean of z enters the common level c;
- the deviation z_a − mean enters d_a.

One sign-constrained β per driver (β ≥ 0), with prior N(0, 1); standardized in-fold over all area-quarters available.

## 2. Candidates

| Id | Definition | Status |
|---|---|---|
| **E134-AREA-T** | HFM-X (E133, unchanged drivers A rice, C typhoons, E, N, V) + aR + aP | Clean test of the new area data |
| **E134-AREA-O** | As E134-AREA-T, but with C = ONI | ONI prompted by E133 D2 (post-hoc origin, disclosed) |
| **E134-ONI** | E133 HFM-X-PH2, unchanged | Re-registration of the PH2 hypothesis for prospective test |
| **E134-ENS** | Mean of HFM-X and SEAS-LLM forecasts, and of their predictive SDs | Prompted by E133 (each wins on a different set); disclosed |

**References:** PERSIST, CLIM, LLM, SEAS-LLM, HFM-NS-DES, HFM-X (reproduced exactly).

## 3. Evaluation (unchanged rules)

- **Report:** MAE, RMSE, bias, within tolerance, coverage, terciles, sharp increases, by area, by period (pre-surge / surge 2024 / post-break 2025+), Leads 1–4, both sets, both policies.
- **Reliability:** N1–N7 on S-U (N3 baselines PERSIST, CLIM, LLM, SEAS-LLM) and N2/N3 on S-E132.
- **Primary new-data test:** E134-AREA-T against HFM-X (paired cluster bootstrap on squared error, Lead 2, S-U).
- **Ablation:** aR and aP each removed, from E134-AREA-T.
- **Contribution criterion (E133):** removal worsens MAE and within, with p < 0.10.

## 4. Selection of the E134 prospective candidate (fixed)

- **Rule:** highest S-U P-DASH Lead-2 within among E134-AREA-T, E134-AREA-O, E134-ENS, HFM-X and SEAS-LLM; ties → lower MAE.
- **Validated** only if N1–N7 pass on S-U **and** N2 and N3 pass on S-E132.
- Because every value has been seen, **the selected candidate is a prospective candidate, never a confirmed result.**

## 5. Diagnostics (not candidates)

- **Target uncertainty:** share of each model's Lead-2 MSE equal to the mean sampling variance SE²; between-instrument gap (SWS vs OCTA, E132).
- **News evidence taxonomy:** FSSI v2 quarters classified as no article found / articles but none admitted / admitted evidence / missing source.
  - Correlation of Balance Luzon–relevant CALABARZON FSSI with the later Balance Luzon HFM-X residual (diagnostic only; 5 provinces of a 7-region area).
- **Event timeline:** for the 2024 surge and the 2025–26 moves, the publication dates of every driver relative to each issue.
- **Perturbation:** E134-AREA-T with each area driver's availability delayed one extra quarter.

## 6. Pre-2021 feasibility (analysis only)

- Document the sources, the periods held elsewhere (E114 branch), and the exact provisions of this protocol and of the owner's 2021+ rule that would need amendment.
- **No pre-2021 row is loaded in E134.**

## 7. Prospective protocol and seal

- **Seal:** issue 2026-11-01; targets 2026-Q4 … 2027-Q3; every E134 candidate; write-once.
- **Frozen in `E134_PROSPECTIVE_VALIDATION_PROTOCOL.md`:**
  - feature list, preprocessing and issue policy;
  - quarterly re-issue rule;
  - scoring with `score_e134.py` (primary criterion only);
  - adoption requires ≥ 10 unseen Lead-2 quarters.

# AIPHEED protocol lock (read-only)

Verbatim quotes of the frozen evaluation protocol. Each block is read from the named file at the named commit and equals the current working tree. Built by `python -I backend/scripts/build_protocol_lock.py`; checked by `backend/tests/unit/test_protocol_lock.py`. **Never edit by hand.** A change to any value requires the owner's explicit approval and a new protocol.

## T1 · Target, sampling SE and the frozen primary tolerance

`aipheed-backend-aligned/experiments/E131_Objectives_Resolution/E131_FROZEN_PROTOCOL.md` lines 20–28 @ `88b270c`

```text
## 1. Target (measured food insecurity)

| Item | Definition |
|---|---|
| y(a, q) | SWS involuntary hunger, % of families, area a ∈ {Metro Manila, Balance Luzon, Visayas, Mindanao}: the mean of the non-commissioned rounds of quarter q, 2021-Q2 … 2026-Q3 (`E110_Hunger_Generalization/data/sws_area_rounds.csv`) |
| Sampling SE of round i | n_i = 0.9604 / (MOE_i / 100)², the simple-random-sample size implied by the published 95 % margin (BL margin for Balance Luzon, the "other areas" margin otherwise; 6 if missing). SE_i = 100 √(p_i (1 − p_i) / n_i), with p_i the round's own estimate. |
| Quarter SE | SE(a, q) = √(Σ SE_i²) / k for k rounds |
| **Tolerance (primary)** | **tol(a, q) = 1.645 × SE(a, q)**, the reference's own 90 % sampling half-width (E130 §4 principle). Uses the observed p, not 0.5, and no design-effect inflation, so it is not generous. |
| Tolerance sensitivity (information only) | 0.5× and 2× tol; and the SE implied by the published margin at p = 0.5 |
```

## T2 · Primary criterion only (no secondary tolerance)

`aipheed-backend-aligned/experiments/E131_Objectives_Resolution/E131_ADDENDUM_1_DA_OPERATIONAL_TOLERANCE.md` lines 29–29 @ `c32e5bc`

```text
1. **Only the primary evaluation is kept.** The sealed forecasts are scored with `runner/score_e131.py`, which applies the protocol §1 rule (|forecast − SWS| ≤ 1.645 × SE of the SWS quarter) and nothing else. The procedure is frozen here, before 2026-Q4 SWS is published (expected around January 2027).
```

## T3 · Tolerance in code

`aipheed-backend-aligned/experiments/E130_Provincial_Risk_Score_Forecasting/runner/e130_lib.py` lines 173–180 @ `f2c8d0f`

```python
def tolerance(se_ref) -> np.ndarray:
    """Pre-registered tolerance: the reference's own two-sided 90 % sampling half-width (1.645 x SE). A prediction
    inside it cannot be told apart from the reference by the reference's own precision."""
    return Z90 * np.asarray(se_ref, dtype=float)


def within_tolerance(pred, ref, se_ref) -> np.ndarray:
    return np.abs(np.asarray(pred, float) - np.asarray(ref, float)) <= tolerance(se_ref)
```

## T4 · Tolerance multiplier in code

`aipheed-backend-aligned/experiments/E130_Provincial_Risk_Score_Forecasting/runner/e130_lib.py` lines 30–30 @ `f2c8d0f`

```python
Z90 = float(stats.norm.ppf(0.95))           # two-sided 90 % sampling half-width multiplier
```

## E1 · Leads, issue policies and eligible evaluation quarters

`aipheed-backend-aligned/experiments/E131_Objectives_Resolution/E131_FROZEN_PROTOCOL.md` lines 30–38 @ `88b270c`

```text
## 2. Leads and issue policies

| Item | Definition |
|---|---|
| Operational Lead k | Target = D + k − 1, where D is the dashboard quarter (`backend/app/quarterly/target.py`). Lead 2 = the dashboard target. |
| **P-DASH (primary)** | Issue at 00:00 on the first day of D. Information = rounds published strictly before the issue date. |
| P-REL (secondary) | Issue on the day after the last round of quarter D − 1 is published, if that falls within D; otherwise there is no issue that quarter. Information = rounds published before that day. |
| Partial quarters | Count as observed with the rounds published at the time |
| Evaluation dashboard quarters | Every D from 2021-Q3 to 2026-Q4 whose target has an observed value, with at least 8 observed training target quarters for the model |
```

## E2 · Primary evaluation set S-U (eligible rows: n_obs >= 8)

`aipheed-backend-aligned/experiments/E133_Forecasting_Breakthrough/E133_FROZEN_PROTOCOL.md` lines 63–64 @ `9683aad`

```text
- **S-U (primary set):** rows with n_obs ≥ 8 (E132 "univariate set"; Lead 2: 40 rows, 10 target quarters,
  2024-Q1 … 2026-Q3, including the 2024 surge). Every E133 candidate is defined on all of S-U.
```

## R1 · Reliability rules N1-N7, reliable lead and maximum reliable lead

`aipheed-backend-aligned/experiments/E130_Provincial_Risk_Score_Forecasting/E130_FROZEN_EXPERIMENT_PROTOCOL.md` lines 164–184 @ `b58c48e`

```text
## 8. Reliability rules

These are frozen and apply at every lead.

**Numerical task (primary).**

| # | Rule |
|---|---|
| N1 | At least 10 target quarters and 40 rows of distinct provincial observations (copies count once) |
| N2 | At least 75 % of out-of-sample predictions within tolerance (section 4) |
| N3 | MAE **and** RMSE lower than every applicable baseline (M2–M5), on identical rows |
| N4 | Squared error below persistence **and** below climatology, each with a one-sided paired cluster bootstrap p < 0.10 (clusters = target quarters) |
| N5 | Share within tolerance ≥ 0.60 in each third of the target quarters, and leave-one-quarter-out minimum ≥ 0.70 |
| N6 | No province with MAE skill below 0 against its own persistence |
| N7 | 80 % prediction-interval coverage between 0.70 and 0.90 |

**Classification task (secondary).** The frozen R1–R7 (`FINAL_THESIS_OBJECTIVES/FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` §7) apply, and only if the owner has approved category thresholds.

**Lead k is reliable** when N1–N7 pass, plus R1–R7 where classification is valid.

**Maximum reliable lead.** The furthest consecutive lead from Lead 1 that is reliable. An unreliable intermediate lead ends the run.
```

## R2 · Reliability rules in code

`aipheed-backend-aligned/experiments/E130_Provincial_Risk_Score_Forecasting/runner/e130_lib.py` lines 257–266 @ `f2c8d0f`

```python
    R = {
        "N1_data": nq >= 10 and nrows >= 40,
        "N2_within_tolerance_75": m["within_tolerance"] >= 0.75,
        "N3_beats_every_baseline_mae_rmse": all(m["mae"] < base[b]["mae"] and m["rmse"] < base[b]["rmse"] for b in baselines),
        "N4_squared_error_vs_persistence_and_climatology": p_persist < 0.10 and p_clim < 0.10,
        "N5_stability": (bool(thirds) and min(thirds) >= 0.60) and (bool(loqo) and min(loqo) >= 0.70),
        "N6_no_province_below_persistence": all(v["skill_vs_persistence"] >= 0 for v in per_prov.values()
                                                if v["skill_vs_persistence"] == v["skill_vs_persistence"]),
        "N7_interval_coverage_80": 0.70 <= cover <= 0.90 if cover == cover else False,
    }
```

## C1 · CPI cutoff rule (protocol)

`aipheed-backend-aligned/experiments/E131_Objectives_Resolution/E131_FROZEN_PROTOCOL.md` lines 67–67 @ `88b270c`

```text
| A Market | Area food-CPI YoY; area rice-CPI YoY; area relative food price (food ÷ all-items index), as level and as 4-quarter change. Built from the OpenSTAT `0012M4ACP22` regional index, monthly 2021-01 … 2026-09 [day 10 of m + 1]. YoY only from 2022-01 (no pre-2021 base). | Area = unweighted mean of its regions (stated limitation) |
```

## C2 · CPI cutoff rule (code: availability and YoY base)

`aipheed-backend-aligned/experiments/E131_Objectives_Resolution/runner/e131_x1.py` lines 158–158 @ `c32e5bc`

```python
    available (day 10 after the quarter's last month). YoY only from 2022-01 (no pre-2021 base)."""
```

## C3 · CPI YoY base rule (code)

`aipheed-backend-aligned/experiments/E131_Objectives_Resolution/runner/e131_x1.py` lines 168–168 @ `c32e5bc`

```python
    w.loc[w["date"] < "2022-01-01", ["food_yoy", "rice_yoy"]] = np.nan
```

## C4 · CPI availability date (code)

`aipheed-backend-aligned/experiments/E131_Objectives_Resolution/runner/e131_x1.py` lines 185–185 @ `c32e5bc`

```python
    out["available"] = out["quarter"].map(lambda q: L.qend(q) + timedelta(days=10))
```

## W1 · Study window

`aipheed-backend-aligned/experiments/E131_Objectives_Resolution/E131_FROZEN_PROTOCOL.md` lines 142–142 @ `88b270c`

```text
- Study window 2021+. Every file loaded must hold only 2021+ rows, except the FIES 2023 public-use file, which is in-window by construction.
```

## W2 · Prospective adoption window

`aipheed-backend-aligned/experiments/E134_Information_Bottleneck/E134_ADDENDUM_2_AMENDED_PRIMARY.md` lines 21–21 @ `2d9a2d9`

```text
- Adoption requirement: **≥ 75 % within and N1–N7 at Lead 2 on ≥ 10 unseen Lead-2 quarters**, then owner approval and a separate integration branch. Earliest decision: 2029-Q3.
```

## W3 · Dashboard target and issue rule (served code)

`backend/app/quarterly/target.py` lines 46–63 @ `772b852`

```python
    return datetime(int(quarter[:4]), 3 * int(quarter[-1]) - 2, 1, tzinfo=PH)


def forecast_target(now: datetime | str | None = None) -> dict:
    """The dashboard's forecast target and its issue rule, for the given (or current) Philippine time."""
    t = now_ph(now)
    cal = quarter_of(t)
    target = shift(cal, 1)
    origin = quarter_start(cal)
    return {
        "now_ph": t.isoformat(timespec="seconds"),
        "calendar_quarter": cal,
        "target_quarter": target,
        "origin": origin.date().isoformat(),
        "information_cutoff": f"{origin.date().isoformat()}T00:00:00+08:00 (exclusive)",
        "latest_complete_data_quarter": shift(cal, -1),
        "lead_from_latest_data_quarter": 2,
        "rule": "next calendar quarter after the one in which the dashboard is viewed (Asia/Manila); forecasts are "
```

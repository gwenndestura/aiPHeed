# Note for the adviser: the Chapter III pipeline vs a hunger-only model (possible Chapter 3 amendment)

**In short.**
- Run exactly as Chapter III describes, the forecasting model fails its own acceptance tests. This result was reproduced
  exactly.
- A simpler model, which forecasts measured hunger and is trained on a longer history, does much better on the same
  kind of walk-forward test.
- It still fails one stability rule, and its results are development evidence.
- We propose discussing it as a Chapter 3 amendment. This is not yet a replacement.

## 1. The two models side by side

| | **Chapter III pipeline (paper)** | **Hunger-only LightGBM (IMPROVE_V2)** |
|---|---|---|
| What is forecast | Eq. 3: SWS hunger + 2 × provincial food-CPI deviation, HIGH above the median (a province-level proxy) | SWS Balance Luzon involuntary hunger above 11.3% (measured hunger, **regional**: the same for all five provinces) |
| Role of food prices | Part of the label | **Inputs only** |
| Training history | 2021-Q1..2026-Q3 (19 labelled quarters) | 1998–2026 (SWS since 1998; PSA CPI back-cast to 1994) |
| Model | LightGBM, 12 features, Optuna-tuned | LightGBM (same algorithm family), stacked leads, refitted each quarter |
| Test | Algorithm 3 walk-forward; Algorithm 4 blind holdout 2025-Q4..2026-Q3 | Walk-forward, 62 quarters 2010–2026, one forecast per quarter |
| **One quarter ahead** | Mean fold accuracy **0.30** (persistence 0.70) | Accuracy **0.79** (persistence 0.66); Brier 0.188 vs 0.339 |
| **Two quarters ahead** | Holdout accuracy 0.45, weighted F1 0.53, AUC 0.61: **not accepted** | Accuracy **0.79**, precision 0.81, recall 0.91, F1 0.86, AUC 0.70; Brier 0.184 |
| Against copying the latest survey | Significantly **worse** (McNemar p = 0.0003) | Significantly **better** (Brier, Holm p = 0.001) |
| Reliability verdict | Fails Algorithm 3 (75% rule) and Algorithm 4 (F1 0.75, AUC 0.80) | Under our stricter seven-rule test it passes six rules and fails one: **stability**, with 0.95 / **0.57** / 0.85 accuracy across the three thirds of 2010–2026 |

**Note on the paper's own rule.** Algorithm 3 accepts a lead when the mean walk-forward fold accuracy is ≥ 0.75. The
hunger-only model's mean one-quarter fold accuracy is 0.79 at both leads, so **under the paper's 75% rule alone it
would pass at Leads 1 and 2**. We still treat it as not reliable, because our pre-registered rule also requires
stability across periods, and it fails that.

## 2. Why the Chapter III pipeline fails

1. **Too little history:** about 19 labelled quarters.
2. **One regime switch:** the Eq. 3 label is LOW in almost all of 2021–23 and HIGH in almost all of 2024–26. Models
   trained on the LOW years keep predicting LOW.
3. **Thin news coverage:** too thin for the news features to carry signal.

Tuning cannot fix this (Optuna was run: 100 trials).

## 3. What the amendment would change, and what it would cost

**Changes:**
- **Target:** measured SWS hunger (regional) instead of the Eq. 3 province proxy. Food prices become inputs.
- **History:** use the long SWS and PSA record, instead of 2021–2026 only.
- **Reliability:** Algorithm 3's 75% rule, **plus** a stability check across periods.

**Costs, stated plainly:**
- **Not province-level.** Objectives 2 and 3 speak of province-level classifications. A regional target gives every
  province the same forecast. LGU rankings would then be ordered by poverty and density alone.
- **Still not "reliable".** The model fails the stability rule, mainly in about 2015–2020. Without the 2020
  mobile-phone survey quarters it would pass, but that is a sensitivity check, not the rule.
- **Weak evidence.** The improvements were chosen after seeing these quarters. The only clean test is the sealed
  forecasts:
  - Lead 2 for 2027-Q1 is sealed: HIGH, P = 0.86, hash `94c62596…`;
  - more forecasts are sealed each quarter;
  - about 10 scored quarters by late 2029 give a first independent check.
- **News.** News did not improve either model. Objective 1's pipeline stands, but its forecasting value is not shown.

## 4. What we ask

1. Whether Chapter III may report the paper pipeline's failure as a finding (H1–H3 not rejected) **and** present the
   hunger-only model as an amendment, labelled exploratory.
2. Whether Objectives 2–3 may be reworded from "province-level" to the regional hunger target, or kept as written and
   reported as not achievable with available data (no provincial food-insecurity outcome exists for 2010–2026).
3. Approval of the paper wording fixes in `DECISIONS.md` (W1–W14).

**Files:**
- `E99_REPRODUCTION.md`, `OBJECTIVES_STATUS.md`, `DECISIONS.md`;
- `../IMPROVE_V2/RESULTS.md`, `../OBJECTIVES_COMPLETION/OBJ2_METRICS_AND_HORIZON.md`.

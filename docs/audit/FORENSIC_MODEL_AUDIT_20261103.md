# aiPHeed forensic model audit and methodology comparison (2026-11-03)

**Scope.** Every food-insecurity forecasting model and experiment in the repository: about 720 commits, about 40 branches, the 97 folders in `aipheed-backend-aligned/experiments/`, the served engines in `backend/data/ch1_engine/` and `backend/app/ml/inference/firi.py`, and the FI5–FI11 modules in `backend/app/fi*`.

**What this audit did not do.** Nothing was retrained, deleted or overwritten. No served file, model, seal or dashboard element was changed. P0H4 stays served. The only new files are this report and `recompute_fi10_vs_persistence.py`, a read-only recomputation from existing FI10 predictions.

**Evidence levels.** Every number in this report carries one of three tags:

| Tag | Meaning |
|---|---|
| **[R]** | Recomputed in this audit from saved predictions or evaluation files |
| **[F]** | Read from the experiment's own report or evaluation file during this audit |
| **[M]** | Taken from the project record (memory index or earlier session notes); the file was not reopened in this audit |

An [M] number should be checked against its file before it is cited in the thesis.

---

## Part I. Executive summary

1. **No learned model beats persistence on the only measured food-insecurity outcome** (SWS involuntary hunger, Balance Luzon, which is regional) for above-normal classification at any lead. This holds across E109–E113, E128, E131–E136, FI5–FI9-Z and FI11. Every one of these studies was run under its own pre-registered rules.
2. **Persistence can be beaten for the hunger *level*, but only by another simple rule.** Damped mean reversion beat persistence on 2013–2020, a period never scored before E114: Lead-2 MSE 27.0 vs 37.8, Δ −10.8 [−19.2, −3.2] [F]. It also beat E114's LightGBM (34.0).
3. **The high accuracies in the project (0.914, 0.892, 0.846, 0.843) are on the composite proxy T43c, not on measured food insecurity.**
   - T43c = Balance Luzon hunger > 11.3% AND an unusual provincial food-price rise.
   - Since 2023-Q4 the hunger term has been true in every quarter. T43c has therefore been decided by the price term alone, and provinces differ only through prices.
4. **The one place a learned model beats both persistence baselines at Lead 2 with a confidence interval excluding zero is FI10, on provincial food-price pressure.** That target is a driver of food access, not food insecurity.
   - Tuned LightGBM vs damped persistence: Brier −0.019 [−0.042, −0.0015] [R]; vs naive persistence: −0.038 [−0.070, −0.014] [R].
   - This configuration was **not** the one the locked rule selected on the development period, and it fails the locked precision, accuracy and per-province requirements.
5. **Maximum reliable lead, by target:**
   - measured hunger (A): Lead 1 with naive persistence under FI7's rules; **none** under FI9-Z's class requirement (HIGH recall ≥ 0.60);
   - proxy T43c (B): **Lead 1** (P0H4, all R1–R7 pass);
   - price pressure (C): **none adopted**, with Lead 2 the most promising.
6. **No news or NLP component changes a HIGH/LOW decision.** News improves probability scores (Brier or AUC) in some designs only: FI6-N at quarter-end issue, and FI9-X LightGBM vs LightGBM. It never beats persistence.

---

## Part II. Model inventory

Columns: target class (A–D, Part IV), lead definition, validation design, headline metrics, status.

**Abbreviations used in the table:**
- **WF**: expanding-window walk-forward;
- **acc**: accuracy;
- **BA**: balanced accuracy;
- **R / P**: HIGH recall / HIGH precision;
- **max lead**: maximum reliable lead.

### II-a. Served or production engines

| ID | Algorithm | Where | Target | Leads | Validation | Headline result | Status |
|---|---|---|---|---|---|---|---|
| **P0H4** | One unified LightGBM (12 FIRI v2 families + lead + world prices, monotone price terms) for the price condition × closed-form SWS hunger probability (σ pooled over 4 SWS areas) | `backend/data/ch1_engine/` (branch `aiPHeed/lead2-optimization` `a1ce8ce`; seal `a498b5ef`) | B (T43c) | 1–14 | WF 2023-Q1 → 2026-Q3, 70 rows at Lead 1 | **Lead 1:** acc 0.843, BA 0.776, R 0.647, P 0.688, AUC 0.867, Brier 0.132 [F]. **Lead 2:** acc 0.769, BA 0.635, R 0.353, AUC 0.625 [F] | **Served** (dashboard map). Lead 1 passes R1–R7; verdict "promising_not_yet_verified". Lead 2+ not reliable |
| **FIRI v2** | Equal or evidence-weighted index of 12 indicators (A1–H1), percentile-scored | `backend/app/ml/inference/firi.py` | D/C composite index (not a forecast of an outcome) | — | Outcome check vs OCTA 4/8 (E73), vs SWS 3/7 (E99) [M] | Index, not a classifier | Served as an index |
| **FI9 C0** | Damped persistence + conformal interval | `backend/app/fi9/` (artifact `952ce490…`, `PRODUCTION_PIN.json`) | A (regional) | 1 (issued end of quarter's 2nd month) | WF 2010–2026, 62 targets, 11 HIGH | acc 0.823 (= always-LOW), BA 0.714, R 0.545, P 0.50, Brier 0.118, AUC 0.774; conformal coverage 60/62 [F] | Served on the FI9 card, **provisional** (fails sawtooth check) |
| **FI10** | Tuned LightGBM (Lead 1); ridge + LightGBM ensemble (Lead 2) | `backend/app/fi10/` (lock `1ac043db`) | C (provincial) | 1–2 issued; 3–4 not issued | WF test 2016–2026, 215 rows, 49 HIGH | **Lead 1:** BA 0.725, R 0.714, P 0.443, Brier 0.171. **Lead 2 (ensemble):** BA 0.659, Brier 0.144 [F] | Served on the FI10 card (uncommitted), **provisional**, no lead adopted |

### II-b. Research models

| ID | Algorithm | Branch / commit | Target | Lead / validation | Headline result | Status / reason |
|---|---|---|---|---|---|---|
| Era-0 deployed RF | Random forest, food-availability (production shock −10%) label | pre-E8 main | C/production proxy | horizon 0 | "RQ2 horizon 0, persistence wins" [M] | Superseded |
| Lean rebuild | 12 features + RF | pre-E8 | C | 110 obs | Beat the deployed model [M] | Superseded |
| E9 S1 | LightGBM | `e9*` | A-proxy | — | Beats carry-forward only; 75% "meaningless" [M] | Rejected |
| E10/E11 | LightGBM | — | A-proxy | Q4 sealed `a3903086` | No gain over S1 [M] | Rejected |
| E12 | SWS scoring | — | A | — | No combined formula validated [M] | Two-layer design |
| E13–E17 | various | — | — | — | No provincial outcome; nothing beats persistence [M]; E13 integrity 865/865 hashes [F] | Rejected |
| E23 | — | — | A | — | 85% < persistence 87.5% [M] | Rejected |
| E24v2 | — | — | — | — | VOID where pre-2021 data used [M] | Void |
| E25 | — | 2021–26 | A-threshold | — | Always-HIGH has best Brier [M] | Rejected |
| E28 / E31 | News pipeline + FSSI; LGU ranking | `81b5fa8`, `c720f71` | A/D | — | News holdout P 0.85 / R 0.40 (classifier, not forecast) [M] | Components kept |
| E32 / E35 | PCFN vs PCF21 | frozen `37e0d66b` | B | — | PCFN fails; tuning no gain [M] | Rejected |
| E36–E38 | Final integration | `bf94bb3` | B | Lead 2 | 0.709 [M] | Superseded |
| E41 | Lead-2 audit | — | B | Lead 2 | ≥75% results degenerate; M1 0.632 [M] | — |
| E43/E44 | Five-trigger risk (T43) | — | B | — | Best 0.686; AUC ~0.78 needed; climate only signal [M] | Rejected |
| E46 | Rice policy | — | B | — | I7 0.800, HIGH recall 0.44 [M] | Prospective only |
| E51 / E52 | Target definition / acceptance | — | B | dev | Thesis label saturated; PS 0.760 passes A1–A5 on dev only [M] | Dev evidence |
| E53 / E55 | LightGBM + calibration | 2027-Q1 frozen | B | Lead 2 | E55-LGBM 0.733; no calibrator passes [M] | — |
| **E56-TUNED** | LightGBM, 72 configs, nested per-origin selection | `e46-lead2-policy` `88d5266` | B (T43) | Lead 2, 45 rows | acc 0.778 [0.69, 0.87], BA 0.760, Brier 0.178; Cavite 0.44; vs E55 ΔBrier −0.001 (CI includes 0) [M] | Was served as FIRI A1 source; superseded |
| E57 | E56 rolling-origin | — | B | — | 0.720, not reliable [M] | Rejected |
| E58–E61 | Rising-stress early warning (EW) | — | B | — | 7/10 onsets; not validated (E59) [M] | Experimental |
| E63 | Lead-time study | — | B | — | No lead meets the Brier rule [M] | — |
| E64 / E65 | News v3 + BERTopic; El Niño | — | B | — | No gain; ENSO ~no effect [M] | Rejected |
| E66–E68 | Best-methodology / Lead-2 / fixes | `f8c4416`, `9320db6`; seal `79aa6f2a` | B | Lead 2 | >75% Lead 2 "not legitimately met"; no fix beats A0 [M] | Rejected |
| E69 | Two-scale risk framework | — | A + C | — | Hunger unforecastable beyond latest reading [M] | Framework |
| E70–E73 | FIRI v1/v2, FIR71 | `089bdf2` | D/C index | — | 80% Lead 2 not met (0.72); FIR71 fails; OCTA outcome FIRI 4/8 [M] | FIRI v2 kept |
| E76 | Food-insecurity model | `AIPHEED_E76=1` | A | L1–2 | Persistence unbeaten [M] | Rejected |
| E79–E82 | EW-ANOM measurement redesign | local `7b57d9b` | B | — | 75% not met; not merged (owner) [M] | Not merged |
| **E83** | S-SIM (simple rule), arms incl. LightGBM | `e83-deep-research-reconstruction`; seal `1331d498` | B | L1–2, 65 rows | **Lead 1** 0.846; **best Lead 2** S-SIM-THR 0.708, BA 0.58 [F] | Lead 2 not met |
| E84–E88 | S-COMP price channel; GDELT; affordability; outcome gap; selection | seal `ad402660` | B | — | GDELT makes S-COMP worse (Lead 1 Brier 0.167 vs 0.141); best T43 Lead 2 0.738; regional-hunger persistence 0.69 vs always-HIGH 0.77 [F] | Rejected |
| E89 / E90 | Model optimization | seal `cef43f6a` | B | Lead 2 | 0.800, recall 0.31; 2024-Q2 unlearnable [M] | Fails recall |
| E91 / E92 | Unified horizon; LightGBM + news Lead 2 | seal `f20d6d52` | B | K = 0–2 | K = 0 validated; Lead 2 = always-LOW [M] | Rejected |
| **E93 LINDIR** | Linear-tree hunger-change × LightGBM price classifier | `e93-lead2-breakthrough` `a42cbd5` | B | K1 | 0.846, BA 0.814, 12/16 HIGH; fails Brier significance (Holm 0.105); K2 0.769 with 3/16 HIGH [M] | Final E94 = LINDIR, K = 0 |
| E95–E99 | Root cause; target formulation; validation; gate | prod `053a95d` | B/A | — | cumF4 regime memory; gate FAILED; SWS vs OCTA 3/7 [M] | Gate failed |
| E100–E104 | Market / access / FB2 / REL | — | B | L1–2 | FB2 0.889 / 0.941 (dev); REL-only Lead-2 Brier 0.136 **selected after seeing outcomes** [F] | Dev only |
| E105 | Hunger model protocol | — | A | — | Frozen, **never scored** [F] | Not run |
| E106 | Simple methodology | — | B | — | Superseded by E107 [F] | Superseded |
| E107 | 12-indicator LightGBM | — | B | L1–4 | Lead 1 0.750 (40 rows); Leads 2–4 0.10–0.55 vs always-LOW 0.80–0.95 [F] | Lead 1 only |
| **E108** | π_H (latest SWS) × LightGBM price probability | — | B | L1, 13 quarters | acc 0.892, BA 0.87, R 0.81, P 0.76, AUC 0.917 [F] | "Inconclusive" (record) |
| E109–E113 | Direct SWS hunger forecasting (LightGBM-12, LLR, COMB, conformal) | E111 `aiPHeed/e111-hunger-forecast-audit` | A | true horizons | LightGBM-12 Lead-1 MAE 4.04 vs latest SWS 3.72; nothing beats latest reading; adopted = persistence + conformal band [F] | Persistence adopted |
| FIL / FIL-LONG | LightGBM | `aiPHeed/final-food-insecurity-lightgbm` | A (regional change label) | L1–4 | 0.32–0.50; FIL-LONG 0.50–0.55 on 2003–2020; Bayes ceiling 0.58–0.64 [F] | 75% unattainable |
| FIL-OA | Served LightGBM engine | `74af1a4` | A-elevated | L0–4 | ELEVATED acc 0.61, 0.52, 0.50, 0.36, 0.56 [F] | Superseded |
| **CH1-LGBM** | π_H × per-lead LightGBM π_P | `aiPHeed/firi-data-audit` `f8efaf9` | B (T43c) | L0–4, 70 rows at Lead 1 | **Lead 1** 64/70 = 0.914, TP 14 FP 3 FN 3; Lead 2 0.583 (< always-LOW 0.717) [F] | Lead 1 only |
| UNI-FINAL | One LightGBM over all leads | `aiPHeed/unified-lgbm-objectives` `f717707` | B | L1–15 | Lead 1 0.829 (R1–R7 pass); Leads 2–3 0.769 / 0.750, fail BA and recall [M] | Basis of P0H4 |
| LEAD2_* | Tuning, five triggers, one-model, final signal, as-of re-evaluation | `2641060`, `703fef6`, `c4c357e`, `76faec8`, `c5906a9` | B | Lead 2 | Lead 2 not supported; P0H4-U L2 0.800 fails R6 by one row; price unpredictable 2Q ahead [M] | Rejected |
| FORECAST_RESEARCH I–II | P0H4-U (schedule B), Z0-U | seals `bd6572e1`, `b7162a63` | B | L1–3 | Issue the day after SWS publishes improves Lead 2; learned corrections fail; provincial price vs regional hunger ρ −0.38 [F] | Env-flag candidates |
| VALIDATOR_ONLY | LightGBM without CPI/SWS inputs | `aiPHeed/system-fixes` | B | — | See report [F] | Decision pending |
| E114 | Unified LightGBM on hunger change, 4 areas | `aiPHeed/e114-genuine-forecast` `de05c5d` | A (level) | L1–2; TEST 2013–2020 | Lead 2 MSE 34.0 vs persistence 37.8; damped mean reversion **27.0**; "above usual" Brier 0.254 vs persistence 0.243 [F] | Damped rule better |
| E116 / E117 | Domain contribution | `161978e`, `9170533` | A | L1–2 | Only C3 palay/corn (Lead 1, Holm 0.021) and fish (Lead 1, small) add; nothing at Lead 2 [F/M] | Findings |
| E118–E127 | Data discovery, preprocessing, FIRI3 design, cutoff audit, amendments | `f53036e` → `8feecad` | D/C index | prospective | No provincial FI target; FIRI3 issue blocked to 2027-01-01 [F] | Design only |
| E128 | Five ML models, regional SWS | `aiPHeed/corrected-data-pipeline` | A | L1–4 | Max lead none; persistence best on T1 (acc 0.846, Brier 0.154) [F] | Rejected |
| E129 / E130 | Provincial feasibility / risk score | seal `94a08cd1` | — | — | NOT READY / BLOCKED (no provincial round after 2023) [F] | Blocked |
| E131–E136 | LLM, SEAS-LLM, HFM-X, SIMPLE, X-RED | seals `92b5535f`, `cea5a2ec`, `efba3235`, `e4f844dd` | A (level within tolerance) | Lead 2 | Best within-tolerance 0.50–0.61; max lead none; SEAS-LLM prospective primary [F] | Prospective only |
| v2 / v6 / v12 / v12x / v13 / s1 / s2 | Backend redesigns | various | A | — | No reliable lead; v13 found "Lead k = k + 1 quarters" in a pipeline [M] | Research |
| FI5 | LightGBM, five domains | `b88fd64` | A (> 20-q mean) | L1–4, 62 q | acc 0.53–0.60, AUC ~0.5; persistence 0.68 [M] | Rejected |
| FI6 / FI6-N | Monotone LightGBM change regressor; news archive | `6c90dfe` | A (> 5-y avg + MOE) | Lead 1 (quarter-end issue) | LightGBM acc 0.839, R 0.27; with news Brier −0.0099, AUC 0.70 → 0.77; persistence acc 0.871 passes [M] | Persistence |
| FI7 | Release-aware timing; world prices | `6a8b114` | A | h1 | naive 0.871 / R 0.55 / Brier 0.115; damped 0.823 / Brier 0.118; old "Lead 2" Brier 0.161 → h1 0.129 [M] | Timing adopted |
| FI8 | Persistence / measurement study | `f33aa4c` | A | — | 56% of change variance is sampling error; sawtooth [M] | Finding |
| FI9 / FI9-R / FI9-N | Damped persistence C0, conformal interval | `f33aa4c` | A | h1 | See II-a [F] | Production, provisional |
| FI9-X | 86 government + news fusion candidates | `6f9f12e` (lock `e1b3d300`) | A | L1–2 | None adopted; LightGBM + news beats LightGBM (Brier −0.010) but not persistence [F] | Rejected |
| FI9-Z | Z1–Z7 incl. Z5 cost-sensitive persistence | uncommitted (lock `106a5b83`) | A | L1 | Z5 BA 0.76, R 0.64, P 0.54 vs naive +0.018 [−0.06, +0.11] [F] | No adoption |
| FI10 | Pooled LightGBM / ridge / ET / RF, LOPO | uncommitted (lock `1ac043db`) | C | L1–4 | see Part VI-C [F/R] | Provisional |
| FI10-A | Poverty × price interactions | uncommitted (lock `e85a6e94`) | A | L1 | Interactions worse (Brier +0.004 / +0.022) [F] | Rejected |
| FI11 | ridge / LightGBM / logit / RF × trigger sets S0, A–H | uncommitted (lock `8a4316b6`) | A | L1–4, 62 q | Lead 1 "A + market, LightGBM": acc 0.758, BA 0.746, R 0.727, P 0.40, Brier 0.108; vs naive Brier −0.007 [−0.037, +0.020] [F] | Nothing passes |

**Folders without a report.** Twenty-six folders contain no `.md` report, among them E38–E44, E46, E52–E58, E60–E65, E76, E78 and E91–E95. Their rows above come from the project record [M]. Their output files were not reopened in this audit.

---

## Part III. Chronological evolution of the method

| Era (approx. 2026) | Experiments | Target | Main method | What was learned |
|---|---|---|---|---|
| 0. Sep–early Oct | deployed RF, lean rebuild, methodology audit | food availability (production shock) | RF on 12 features | Pipeline defensible; persistence wins at horizon 0 |
| 1. Oct 10–15 | E8–E38 | SWS-based labels, PCF/PCFN | LightGBM, two-layer scoring, news/FSSI | No provincial outcome exists; Brier made primary (E28) |
| 2. Oct 15–19 | E40–E68 | **T43 composite** (SWS × provincial CPI tiers) | LightGBM tuning (E56), early warning, five triggers | Lead-2 accuracy near 0.7–0.78 on small samples; "75% Lead 2" not legitimately met |
| 3. Oct 19–23 | E69–E99 | T43, FIRI v1/v2 index | FIRI index, S-SIM rules, unified horizon, LINDIR | Lead 1 about 0.85 on T43; Lead 2 recall capped by hunger-onset timing; gate failed |
| 4. Oct 23–25 | E100–E113 | Direct SWS hunger | Market/access arms, LightGBM-12, conformal | Nothing beats the latest SWS reading |
| 5. Oct 25–28 | FINAL_*, CH1, UNI, LEAD2_*, FORECAST_RESEARCH | T43c | π_H × LightGBM π_P; unified LightGBM; P0H4 served | Lead 1 0.84–0.91 on T43c; Lead 2 not supported |
| 6. Oct 28–31 | E114–E127 | SWS hunger level; FIRI3 | Untouched 2013–20 test; data audit; FIRI3 | Damped mean reversion beats persistence on level; FIRI3 prospective only |
| 7. Oct 31–Nov 2 | E128–E136; v2–v13; s1/s2 | Regional SWS | Five ML models; LLM/SEAS-LLM/HFM-X | No reliable lead; the algorithm is not the bottleneck (E136) |
| 8. Nov 2–3 | FI5–FI11 | SWS above 5-y normal + MOE; provincial price pressure | Release-aware timing, damped persistence, fusion, class requirements, FI10 provincial | Timing is the largest gain; news changes no class; price pressure forecastable at Lead 2 |

**Recurring pattern.** Each time the target moved closer to measured food insecurity (Era 2 → 4 → 7 → 8), accuracy fell toward the persistence or always-LOW level. Each time it moved toward price pressure (Era 2–5, FI10), learned models looked better. **The models did not get worse; the targets changed.**

---

## Part IV. Target classification

| Class | Definition | Targets in the repository | What a high score means |
|---|---|---|---|
| **A: actual food insecurity** | A measured household food-insecurity outcome | SWS involuntary hunger, Balance Luzon. Used in E12, E23, E69, E76, E105–E113, FIL, E114–E117, E128, E131–E136, FI5–FI9-Z, FI10-A and FI11. FIES 2023 and FNRI 2015 HFIAS exist as one-off provincial cross-sections only | Forecasts measured hunger, but **regionally** (Balance Luzon covers 7 regions) |
| **B: food-insecurity proxy** | Measured outcome combined with a non-outcome condition | T43 / T43c (SWS > 11.3% AND provincial price condition): E40–E99, E100–E108, CH1, UNI, P0H4, LEAD2_*, FORECAST_RESEARCH | When the hunger term is saturated (since 2023-Q4), mostly price prediction |
| **C: price / economic pressure** | Market or economic driver | FI10 provincial food-CPI pressure; E56 price part (FIRI A1); food-availability label of Era 0 | Forecasts a driver of food access, not food insecurity |
| **D: vulnerability** | Structural exposure, no time outcome | V1 poverty + density; FI9-X province priority (0.65 poverty); LGU ranking; FIRI v2 / FIRI3 indexes | A ranking; it cannot be scored as a forecast |

**Construct warnings:**
- FIES 2023 ranks the four SWS areas almost in reverse to SWS hunger (ρ ≈ −0.8; FI9-X label integration [F]). SWS involuntary hunger and FIES moderate/severe food insecurity are therefore different constructs.
- In 2021–26, provincial food-price pressure moved *against* regional hunger: ρ −0.38 at lag 0 (FORECAST_RESEARCH_II [F]). Class C is not a proxy for class A in this window.

---

## Part V. Comparability

Results from different eras **cannot be compared directly**, for five reasons.

1. **Different targets** (A, B or C, Part IV). An accuracy of 0.914 on T43c and 0.871 on SWS-above-normal are scores on different questions.
2. **Different lead definitions.** "Lead 1" has meant four different things:
   - a quarter-start issue for the next quarter (E83–P0H4), which is 1–2 quarters after the newest SWS reading;
   - a quarter-end issue (FI6-N);
   - an issue at the end of the quarter's 2nd month, after the SWS release (FI7–FI11);
   - "2 quarters past the newest survey" (E112).
   
   v13 also found one pipeline where Lead k meant k + 1 quarters [M].
3. **Different evaluation windows and sizes:**
   - 13–14 quarters, 65–70 rows, 2023–26 (T43c);
   - 62 regional quarters, 2010–26 (FI5–FI11);
   - 215 province-quarters, 2016–26 (FI10);
   - 2013–2020 untouched (E114).
4. **Different base rates:** 24–31% HIGH on T43c; 18% on FI9; 23% on FI10. Accuracy must be read against always-LOW: 0.757 on T43c Lead 1, 0.823 on FI9 and about 0.77 on FI10.
5. **Different selection status.** Some results come from a locked rule (P0H4, FI9, FI10, FI11). Others were found after seeing outcomes (E104 REL-only; FI10 Lead-2 tuned LightGBM, which was not the dev-selected configuration).

The comparisons in Part VI are therefore made **only within one target, one row set and one issue rule**.

---

## Part VI. Methodology comparison under equivalent conditions

### VI-A. Target A: SWS hunger above normal, regional, h1 (FI7 timing), the same 62 targets 2010–26

| Method | Accuracy | Balanced accuracy | HIGH recall | HIGH precision | Brier | Evidence |
|---|---|---|---|---|---|---|
| Always-LOW | 0.823 | 0.500 | 0.00 | — | — | [F] |
| **Naive persistence** | **0.871** | 0.743 | 0.545 | **0.667** | 0.115 | [F] |
| Damped persistence (C0, production) | 0.823 | 0.714 | 0.545 | 0.50 | 0.118 | [F] |
| Z5 cost-sensitive persistence (FI9-Z) | 0.84 | **0.76** | **0.64** | 0.54 | — | [F]; vs naive BA +0.018 [−0.06, +0.11] |
| FI11 best (A + market, LightGBM) | 0.758 | 0.746 | 0.727 | 0.40 | **0.108** | [F]; vs naive Brier −0.007 [−0.037, +0.020], P 0.72 |
| FI9-X best fusion | — | — | — | — | worse than persistence | [F] |
| FI6-N LightGBM + news (quarter-end issue; *different issue rule*) | 0.855 | — | — | — | better than without news | [M]; not comparable to the rows above |

**Reading.**
- No method is significantly better than naive persistence.
- The learned models trade precision for recall (FI11 catches 8 of 11 HIGH quarters but raises 12 false alarms).
- The best Brier (0.108) is within noise of persistence.

### VI-B. Target B: T43c, quarter-start issue, 2023-Q1 → 2026-Q3, 70 rows at Lead 1

| Method | Lead 1 accuracy | BA / recall | Lead 2 accuracy | Evidence |
|---|---|---|---|---|
| Always-LOW | 0.757 | 0.5 / 0 | 0.738 | [F] |
| PERSIST-SI | 0.743 | 0.670 / — | 0.677 | [F] |
| **CH1-LGBM** (per-lead LightGBM) | **0.914** | — / 0.82 | 0.583 (60 rows) | [F] |
| P0H4 (served, unified) | 0.843 | 0.776 / 0.647 | 0.769 | [F] |
| UNI-FINAL | 0.829 | — | 0.769 | [M] |
| E93 LINDIR (65 rows) | 0.846 | 0.814 / 0.75 | 0.769 (3/16 HIGH) | [M] |
| E83 S-SIM (65 rows) | 0.846 | — | 0.708 | [F] |

**Reading.**
- At Lead 1 every π_H × π_P model beats the baselines.
- CH1-LGBM's Lead-1 sign test vs always-LOW is only p = 0.11, and its latest block (0.90) is below always-LOW (0.95) [M].
- At Lead 2 no model beats always-LOW on balanced terms. The 2023-Q4 surge reading was published 21 days *after* the issue date, which caps Lead-2 recall [M].

### VI-C. Target C: FI10 provincial food-price pressure, test 2016–26, 215 rows, 49 HIGH

| Method | Lead 1 BA | Lead 1 Brier | Lead 2 BA | Lead 2 Brier | Evidence |
|---|---|---|---|---|---|
| Naive persistence | 0.671 | 0.165 | 0.645 | 0.174 | [F] |
| Damped persistence | 0.721 | 0.159 | 0.668 | 0.155 | [F] |
| LightGBM regression (tuned) | 0.725 | 0.171 | **0.713** | **0.136** | [F] |
| LightGBM regression without news | **0.732** | 0.167 | 0.704 | 0.141 | [F] |
| LightGBM classifier (tuned) | 0.717 | **0.158** | 0.680 | 0.162 | [F] |
| Ensemble (Lead-2 locked selection) | 0.678 | 0.167 | 0.659 | 0.144 | [F] |
| LOPO LightGBM (unseen province) | 0.678 | 0.169 | 0.708 | 0.143 | [F] |
| Ridge, separate per province | 0.593 | 0.166 | 0.596 | 0.173 | [F] |

**Paired block bootstrap** (4-quarter blocks, 5,000 draws; `recompute_fi10_vs_persistence.py`) [R]:

| Lead | LightGBM (tuned) − damped persistence, Brier | LightGBM (tuned) − naive persistence, Brier |
|---|---|---|
| 1 | +0.012 [−0.007, +0.035] (LightGBM not better) | +0.006 [−0.010, +0.025] |
| 2 | **−0.019 [−0.042, −0.0015]**, P 0.98 | **−0.038 [−0.070, −0.014]**, P 1.00 |

**Reading.**
- At Lead 1, damped persistence is as good as any learned model, and better on Brier.
- At Lead 2, tuned LightGBM is better than both persistence rules. This is the only significant learned-model gain over persistence at Lead 2 in the project.
- Two caveats apply to that gain:
  - The locked dev rule selected the ensemble, not this configuration, so the gain is a post-selection observation. It needs prospective confirmation.
  - The target is class C.
- Pooling helps: separate per-province models are the worst. Generalization to an unseen province holds at Lead 2 (LOPO 0.708).

---

## Part VII. FIRI v2 indicator families (A1–H1)

Source: `backend/app/ml/inference/firi.py` (`LABELS`, `DOMAINS`) [R]. Evidence comes from the experiments named in each row.

| Code | Indicator | Class | Resolution | Evidence on food insecurity | Verdict |
|---|---|---|---|---|---|
| A1 | Lead-2 food-price-pressure forecast (LightGBM) | C | province | Price part of the T43 models; E86 compared S-COMP; E100 affordability domain *negatively* related to regional hunger at Lead 2 [F] | Valid price signal; not a hunger predictor |
| A2 | Headline inflation above usual | C | province | Part of the market group; no independent gain shown [M] | Redundant with A1 |
| A3 | Wholesale rice price change | C | province / national | E117: market conditional in 2021–26, driven by A3 [M] | Weak, window-specific |
| V1 | Poverty and population density | D | province / LGU | Static at every origin (Amendment 1, disclosed in code) [R]; poverty untestable over time (E128) [F]; poverty-weighted priority validated (FI9-X) [F] | Use for ranking only |
| C1 | PAGASA El Niño alert in force | climate | national | E65 ~no effect [M]; E128 ONI acts as a period marker [F] | No predictive value |
| C2 | Typhoons within 300 km | climate | regional | Zero-storm quarters lost by an extraction defect, fixed in E127 [F]; FI7 typhoon intensity rejected [M] | No gain shown |
| C3 | Palay/corn production drop | climate / supply | province | **E117: the only indicator that improves Lead 1**, −0.83 MSE [−1.34, −0.35], Holm 0.021 [M] | Small, real Lead-1 signal |
| C4 | Fisheries production drop | supply | province | E116: fish adds at Lead 1, small [F] | Small Lead-1 signal |
| E1 | Unemployment change | employment | **national** | E74 not a top driver [M]; FI10 ablation: removing employment lowers BA 0.725 → 0.691 (point estimate) [F] | National only; price-pressure value only |
| E2 | Remittance decline | employment | **national** | No dated regional series (E114) [F] | Not testable regionally |
| N1 | FSSI-v3 (XLM-R news index) | news | regional | No effect on P0H4: removing it leaves Brier unchanged (FINAL_SYSTEM_SELECTION) [F] | No forecast value |
| H1 | Regional hunger outlook > 11.3% | A | regional | Carries nearly all of T43c's Lead-1 signal; oracle hunger × P4 nearly passes Lead 2 (LEAD2_OPTIMIZATION) [M] | The decisive input |

**Data-timing warning.** The publication lags of A3, C3, C4, E1 and E2 are *assumed*. Shifting them by one quarter worsens the Lead-2 development Brier of the served stack from 0.177 to 0.189 (DATA_AUDIT_20261030 [F]).

---

## Part VIII. Five trigger groups

| Group | On A (measured hunger) | On C (price pressure, FI10) | Net |
|---|---|---|---|
| **Market** | Hunger history dominates (E114: removing it costs +6.3 MSE; market Holm p = 1) [F]. FI11 (LightGBM): market + poverty beats poverty alone, Brier −0.013 [−0.026, −0.001] [F] | Core of the target; LightGBM without market BA 0.714 vs 0.725 [F] | Useful mainly for prices |
| **Climate** | C3/C4 small Lead-1 gain (E116/E117); El Niño none (E65) [F/M] | Removing climate lowers BA 0.725 → 0.695 (point estimate) [F] | Small |
| **Employment / remittances** | Holm p = 1 (E114) [F]; national series only | Removing employment lowers BA 0.725 → 0.691 (point estimate) [F] | Small, prices only |
| **Poverty** | No dated time series; untestable (E128). FI10-A and FI11: poverty × price interactions *worse* (FI11 LightGBM Lead 1 +0.0085 [+0.0007, +0.021]) [F] | No change when removed (0.725 → 0.725) [F] | Structural ranking only |
| **News / NLP** | Brier or AUC gain only in some designs; never changes a class (Part IX) | LightGBM *without* news is better at Lead 1 (BA 0.732 vs 0.725) [F] | No forecast value |

**All five together.** In FI11 at Lead 1, LightGBM with all five groups is *worse* than market + poverty alone: Brier +0.019 [+0.0025, +0.043] [F]. Adding groups adds variance faster than signal.

**Multiple-comparison warning.** FI11 reports 144 paired comparisons (4 families × 9 contrasts × 4 leads). About 7 would cross a 95% interval by chance. Single significant cells, such as the Lead-4 LightGBM interaction gain (−0.026), should not be read as findings.

---

## Part IX. XLM-R, BERTopic and FSSI

| Component | What it is | Quality as a classifier | Value as a forecast input | Evidence |
|---|---|---|---|---|
| XLM-R relevance / stress classifier | Multilingual transformer that labels news | Holdout P 0.85 / R 0.40 (E31); F1 0.83 (E60) | — | [M] |
| BERTopic | Topic model (news v3) | — | No gain (E64) | [M] |
| FSSI / FSSI-v3 | Food Stress Sentiment Index from classified articles (49 articles at E28) | — | No effect on P0H4; CH1 Lead-1 calls identical without news (FINAL_THESIS_OBJECTIVES) | [F] |
| GDELT price news | Event counts | — | Made S-COMP worse at Leads 1–2 (E85) | [F] |
| FI6-N archive (62,698 articles; 107 SWS-survey restatements removed) | Domain news composites | — | Lead 1 at quarter-end issue: Brier −0.0099, AUC 0.70 → 0.77; changes no class; reproduced in FI9-N | [M] |
| FI9-X news fusion | News features + government data | — | LightGBM + news beats LightGBM (Brier −0.010) but stays worse than persistence | [F] |

**Verdict.** The NLP components work as *monitoring* tools: they classify and summarize what is being reported now. They do not improve a forecast decision. News tracks concurrent conditions (FINAL_THESIS_OBJECTIVES), so its information is already contained in the latest SWS reading and CPI release.

---

## Part X. Reliability audit

| Candidate | Target | Leakage audit | Same-row baseline test | Class metrics | Stable across periods | Locked selection | Prospective record |
|---|---|---|---|---|---|---|---|
| Naive persistence (FI7) | A | n/a (one input) | — | yes | sawtooth-sensitive (+30 d release shift: Brier 0.115 → 0.144) [M] | yes | yes (FI9 register) |
| FI9 C0 | A | passed (18/18) | worse than naive | yes | fails sawtooth check | yes | yes (first score ~May 2027) |
| FI11 Lead-1 best | A | passed | not significant | yes | 2018+ BA 0.69 (< 0.70) | yes | no |
| P0H4 | B | passed (perturbation) | beats PERSIST-SI (Brier −0.125, p 0.036) | yes | thirds 0.88 / 0.76 / 0.90 | yes | served |
| CH1-LGBM | B | passed; threshold look-ahead at the first origin | vs always-LOW sign test p = 0.11 | yes | latest block below always-LOW | yes | no |
| FI10 Lead 2 LightGBM | C | passed (as-of tests) | **beats both persistence rules** [R] | yes | LOPO 0.708 | **no** (not the dev pick) | provisional register |
| E114 damped mean reversion | A (level) | passed | beats persistence on untouched 2013–20 | MSE / Brier | one untouched test | pre-declared comparator | no |

---

## Part XI. Lead-time comparison

| Target | Lead 1 | Lead 2 | Lead 3+ |
|---|---|---|---|
| A (hunger above normal) | Persistence is best and passes FI7 rules; nothing learned beats it | Nothing beats always-LOW on balanced terms (FI11 naive BA 0.467; best logit BA 0.626, fails 2018+) | No skill |
| A (hunger level) | Mean reversion / AR ≥ LightGBM (E117) | Damped mean reversion beats persistence (E114 untouched) | — |
| B (T43c) | Reliable (P0H4, CH1, UNI) | Not reliable (recall 0.35) | Not reliable |
| C (price pressure) | Persistence ties the best model | **LightGBM beats persistence** (not locked-selected) | No skill |

**Maximum reliable lead.**
- On measured food insecurity: **Lead 1, and only for persistence**, under FI7's rules. Under FI9-Z's HIGH-recall ≥ 0.60 requirement, it is **none**.
- On the served proxy: **Lead 1**.
- **No defensible result supports Lead 2 on any food-insecurity target (A or B).**

---

## Part XII. Leakage and defect audit

| # | Finding | Where | Effect | Status |
|---|---|---|---|---|
| 1 | Threshold look-ahead: T43c thresholds use 2021–22 data not all published by the first Lead-1 issue date | CH1 / FINAL_VERIFICATION | 2023-Q1 only; Lead 1 0.914 → 0.908 without it [F] | Disclosed, not corrected |
| 2 | Rounding-sensitive label (Batangas 2025-Q2) | CH1 | 0.914 → 0.900 under the index-based label [F] | Disclosed |
| 3 | T43c reuses the regional hunger term that is also an input (H1) | E128 rejection reason | Lead-1 skill partly re-forecasts SWS persistence [F] | Structural |
| 4 | T43c hunger term saturated since 2023-Q4 | FORECAST_RESEARCH | The target reduces to price pressure; provinces differ only through prices [F] | Structural |
| 5 | Pre-2021 rows admitted by `firi3.validate_inputs` v1 | E122 | Corrected by Amendment 1 (40 CPI rows rejected) [F] | Fixed |
| 6 | Zero-storm quarters dropped by `groupby(q).size()` | E126 / E127 | 9 regional values changed [F] | Fixed (Amendment 3) |
| 7 | Sign error in one-sided p-values | E116 | Found on reading the output; fixed before reporting [F] | Fixed, disclosed |
| 8 | REL-only arm selected after seeing outcomes | E104 | Retrospective results are development-only [F] | Disclosed |
| 9 | Assumed publication lags for A3, C3, C4, E1 and E2 | Data audit 10-30 | Lead-2 dev Brier 0.177 → 0.189 if one quarter later [F] | Open |
| 10 | V1 treated as available at every origin | `firi.py` Amendment 1 | Publication-timing deviation [R] | Disclosed |
| 11 | "Untouched" pre-2021 quarters had already been scored once by E114 | v12x | Later claims of untouched pre-2021 tests are invalid [M] | Disclosed |
| 12 | 107 SWS-survey restatement articles in the news archive (outcome leak) | FI6-N | Removed before modelling [M] | Fixed |
| 13 | FI6-N "Lead 1" described as a nowcast | this project, FI9-N | It is a next-quarter forecast at quarter-end issue | Corrected |
| 14 | FI9-X Lead-2 AUC overstated | FI9-X report | Corrected to 0.33–0.66 | Fixed |
| 15 | FI10 serving rewrote `dataset.csv` | FI10 | sha restored to `68274c42…`; guard added; noted in AMENDMENT_1 | Fixed |
| 16 | FI10-A lock re-created after a crash | FI10-A | Re-locked before any result existed | Disclosed |
| 17 | SWS survey-design effect (300- vs 600-respondent rounds; sawtooth) | FI8 / FI9-R | About −5 to −6.5 pp on n = 300 rounds; breaks h1 robustness [M] | Open (needs SWS microdata) |
| 18 | Pre-2021 SWS release dates rule-based | FI8 | Conservative (27–68 days late), so no leak [M] | Accepted |
| 19 | `label_generator.py` contradiction | Methodology audit 09-04 | Era-0 label code inconsistency [M] | Superseded era |
| 20 | Dashboard tour says P0H4 forecasts "each CALABARZON province" | frontend tour | Overstates a regional + price proxy | **Open owner decision** |

**No leak was found in the served P0H4 or the FI9/FI10 pipelines.** Their as-of tests and perturbation audits pass [F].

---

## Part XIII. Eligibility-gated rankings

**Gate.** A result is eligible only if it meets all five conditions:
- G1: a leakage audit passed;
- G2: walk-forward out-of-sample evaluation;
- G3: same-row baselines reported;
- G4: class-specific metrics reported;
- G5: selection locked before scoring, or the deviation disclosed.

Ineligible results are listed but not ranked.

### A: measured food insecurity (SWS, regional), above-normal classification, Lead 1

| Rank | Method | Key evidence | Note |
|---|---|---|---|
| 1 | **Naive persistence** | acc 0.871, BA 0.743, P 0.667, Brier 0.115 | Most precise and simplest; no learned model significantly better |
| 2 | Z5 cost-sensitive persistence | BA 0.76, R 0.64 | Best HIGH detection; gain over naive not significant |
| 3 | FI11 A + market LightGBM | Brier 0.108, R 0.727, P 0.40 | Not significant vs naive; fails 2018+ robustness |
| 4 | FI9 C0 damped persistence (served) | BA 0.714, Brier 0.118 | Below naive; provisional |

### A: measured hunger level

| Rank | Method | Key evidence |
|---|---|---|
| 1 | **Damped mean reversion** (E114 comparator) | Untouched 2013–20, Lead 2 MSE 27.0 vs persistence 37.8 |
| 2 | E114 LightGBM | 34.0 (p 0.038 vs persistence) |
| 3 | Persistence | 37.8 |

### B: T43c proxy, Lead 1

| Rank | Method | Key evidence | Note |
|---|---|---|---|
| 1 | **P0H4** (served) | 0.843, all R1–R7, beats PERSIST-SI on Brier (p 0.036) | Passes its locked gate; served |
| 2 | CH1-LGBM | 0.914 | Higher accuracy, but weaker significance vs always-LOW (p 0.11) and a first-origin threshold look-ahead |
| 3 | UNI-FINAL | 0.829 | — |

Ineligible: E93 LINDIR (fails its own Brier significance rule), E108 (recorded "inconclusive"), E56 (45 rows; per-origin configuration changes).

### C: provincial food-price pressure

| Lead | Rank 1 | Note |
|---|---|---|
| 1 | Damped persistence (Brier 0.159, BA 0.721) | No learned model better |
| 2 | LightGBM regression (tuned), Brier 0.136, BA 0.713 | Beats both persistence rules [R]; G5 deviation: not the locked dev pick |

### D: vulnerability ranking

| Rank | Method | Note |
|---|---|---|
| 1 | FI9-X poverty-weighted province priority (0.65 poverty / 0.35 density) | Validated as a ranking; not a forecast |

---

## Part XIV. Final research decision

| Question | Decision the evidence justifies |
|---|---|
| **Best methodology** | **Release-aware, persistence-anchored forecasting of the measured regional outcome, with calibrated uncertainty.** That is: issue after the SWS release (FI7: Brier 0.161 → 0.129, the largest single gain in the project); use persistence as the forecast and the bar every model must beat; attach a conformal interval; report class-specific metrics. Learned models and drivers are evaluated as challengers, not assumed |
| **Best algorithm** | For measured hunger: **none of the learned algorithms**. Persistence (classification) and damped mean reversion (level) are best. For price pressure: **pooled LightGBM regression**, at Lead 2 only |
| **Best experiment** | **FI7** for the method (timing). **E114** for the strongest out-of-sample evidence (untouched 2013–20). **FI10** for the only learned Lead-2 gain over persistence |
| **Best verified result** | P0H4 Lead 1 on T43c: acc 0.843, BA 0.776, all locked criteria pass, recomputed from code (LEAD2_ONE_MODEL) [F]. On measured hunger: naive persistence acc 0.871, BA 0.743, Brier 0.115 [F] |
| **Best HIGH detection** | Measured hunger: Z5 cost-sensitive persistence (recall 0.64, precision 0.54). T43c: CH1-LGBM (14/17) |
| **Most reliable** | Naive persistence on measured hunger at Lead 1 (passes FI7 rules; caveat: sensitive to the SWS sawtooth and to release-date assumptions) |
| **Most generalizable** | FI10 pooled LightGBM at Lead 2 for price pressure (unseen-province LOPO BA 0.708); damped mean reversion for the hunger level (untouched 2013–20) |
| **Most interpretable** | Persistence / damped persistence (one parameter). FIRI v2 for showing domain shares, which are not attributions |
| **Best Lead 1** | Measured hunger: naive persistence. Proxy: P0H4 |
| **Best Lead 2** | Measured hunger: **none**. Proxy: none reliable. Price pressure: tuned LightGBM (provisional; needs prospective confirmation) |
| **Maximum reliable lead** | **Lead 1** (persistence on measured hunger under FI7 rules; P0H4 on the proxy). **No food-insecurity target supports Lead 2** |
| **Best for deployment** | **Keep the current stack and label it exactly:** P0H4 map as a *Lead-1 proxy risk class* (regional hunger × provincial prices), the FI9 card as the *regional measured-hunger outlook* (provisional), and the FI10 card as *provincial price pressure* (not food insecurity). Replacing P0H4 is not justified: no alternative passes its gate on the same target |
| **Overall winner** | **Persistence-anchored release-aware forecasting** is the methodology with the best verified evidence. P0H4 is the best *served* model, but on a proxy. **No learned model has been shown to forecast measured food insecurity better than its latest reading.** |
| **Remaining issues** | (1) No repeated provincial food-insecurity outcome exists, so provincial food insecurity cannot be forecast or validated. (2) SWS is regional (Balance Luzon), and 56% of its change variance is sampling error; the 300/600-respondent sawtooth needs SWS microdata. (3) 2021+ contains one shock episode, so Lead-2 tests have low power. (4) The T43c hunger term is saturated; the proxy now measures prices. (5) The FI10 Lead-2 gain was not locked-selected; confirm it on the prospective register. (6) Five indicator publication lags are assumed. (7) Prospective records first score around May 2027. (8) Dashboard tour wording ("each CALABARZON province") is an open owner decision. (9) FI9-Z, FI10, FI10-A and FI11 are uncommitted |

**What this decision does not say.**
- It does not say the 75% Lead-2 objective has been met. It has not, on any food-insecurity target.
- It does not say news or NLP improves the forecast. The evidence shows it improves probability scores in some designs only.
- It does not say FI10 forecasts food insecurity. It forecasts measured provincial price pressure.

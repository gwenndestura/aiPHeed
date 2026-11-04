# Fixes report (2026-11-04): probabilistic persistence and BERTopic topic quality

**Branch:** `aiPHeed/cb6-fixes`, cut from `origin/aiPHeed/cb6-main` at 2d762abd. Local only; not pushed.
**Both plans were hashed and committed (30d3a6dd) before any fit or score:**
- `PLAN_PERSIST_P.md`, SHA-256 b3e8b02d…;
- `PLAN_BERTOPIC_V2.md`, SHA-256 03667649….

No forecasting model was refitted. No served file, dashboard, frontend or seal was changed.

---

## Fix 1: probabilistic persistence baseline (Objective 4)

**Problem:** the stored persistence baseline is a 0/1 forecast (1 if the latest SWS reading is above 11.3%). Its Brier
score equals its error rate (0.339), so any model that gives probabilities beats it easily.

**Fix:** PERSIST-P carries forward the latest reading **with its uncertainty**: Φ((h_last − 11.3)/σ), with σ from
past latest-reading errors at the true horizon (`hr_lib.pi_h4l`, the candidates' own `pi_H4L` input). Run:
`runner/persist_p.py` → `out/persist_p_results.json`, `out/persist_p_forecasts.csv`.

**Checks:**
- The recomputed hard-PERSIST families reproduce the stored C-E6 and C-B6 families exactly (difference 0.0).
- PERSIST-P gives the same HIGH/LOW call as PERSIST in 59 of 62 quarters. The 3 differences are origins where the
  latest reading was exactly 11.3% (p = 0.5), as the plan anticipated.

**PERSIST-P itself (62 quarters):**

| | Lead 1 | Lead 2 |
|---|---|---|
| Accuracy | 0.677 | 0.677 |
| Brier (0/1 version) | **0.199** (0.339) | **0.190** (0.339) |
| AUC (0/1 version) | **0.716** (0.594) | **0.748** (0.594) |

**Candidates vs PERSIST-P (paired Brier, one-sided cluster bootstrap seed 2036, Holm over 14):**

| Model | Lead 1 Brier model / PERSIST-P | Holm p | Lead 2 Brier model / PERSIST-P | Holm p |
|---|---|---|---|---|
| C-b | 0.187 / 0.199 | 1.00 | 0.184 / 0.190 | 1.00 |
| C-E6 | 0.184 / 0.199 | 0.68 | 0.186 / 0.190 | 0.78 |
| C-B6 | 0.183 / 0.199 | 0.82 | 0.181 / 0.190 | 0.82 |

**Baselines proven (of 14), old vs fair persistence:**

| Model | With 0/1 PERSIST | With PERSIST-P |
|---|---|---|
| C-b | 7 | 5 |
| C-E6 | 8 | **6** |
| C-B6 | 9 | 5 |

C-B6 loses always-HIGH as well (Holm 0.066 / 0.061), because its persistence test no longer comes first in the Holm
order.

**Reading:**
- Every candidate is better than fair persistence on average (Brier skill 3–8%), but **none is proven better**.
- PERSIST-P's AUC at Lead 2 (0.748) is higher than C-B6's (0.712).
- The earlier "proven better than persistence" result came from scoring persistence without probabilities. Per the
  plan, the thesis reports PERSIST-P as the persistence comparator and the 0/1 version as a secondary line.

---

## Fix 2: BERTopic topic quality (Objective 1)

**Problem:** the served time-safe topics fail two of their three pre-registered rules: coherence (NPMI −0.47, rule
> 0) and place-name share (53%, rule < 50%).

**Fix (T2, exactly one candidate):** three changes to the served settings, with everything else unchanged:
1. Place names are masked before embedding and vectorizing: 139 gazetteer words, changing 3,516 headlines. Geography
   is the geocoder's job.
2. Filipino stop words are added (the OBJ1 plan had named them; only English was used).
3. Topics are represented by c-TF-IDF instead of KeyBERTInspired.

Run: `runner/t2_topics.py main` → `out/t2_topics.json`. Each of the 19 origins (2022-Q1..2026-Q3) is fitted only on
headlines published before its issue date.

**Results (mean over 19 origins):**

| Rule | Served T0 (refitted) | **T2** | Pass? |
|---|---|---|---|
| NPMI > 0 | −0.452 | **−0.151** | ❌ |
| Place-name share < 50% | 55.4% | **0.0%** | ✅ |
| ARI ≥ 0.30 | 0.444 | **0.456** | ✅ |
| Geography-driven share < 50% (added, stricter) | 14.7% | **4.4%** | ✅ |
| Topics (mean) | 77 | 81 | — |
| Outliers | 35.7% | 35.9% | — |

**Latest origin (2026-Q3, 9,493 headlines):** T2 NPMI is **+0.011** (T0 −0.370). Its first topics are thematic:
- "rice, p20, rice program, kilo";
- "dswd, 4ps, beneficiaries, aid";
- "farmers, agri, agriculture, da";
- "classes, suspensions";
- "tourism, resort".

T0's topics at that origin mixed places, for example "makati, tagaytay" and "pasig marikina, manila, cainta". The
early origins (873–1,423 headlines) pull the mean below zero.

**Decision:**
- **Topic quality is NOT achieved** under the pre-registered rule: mean NPMI −0.151 is not > 0.
- **Formally the decision is void**, because the T0 refit missed the plan's reproduction tolerance (0.01):
  - NPMI differed by 0.014 and place-name share by 0.024 (ARI by 0.0007);
  - the cause is probably run-to-run variation in UMAP and HDBSCAN between the two runs. This was not investigated
    further.
- **The conclusion is the same either way:** T2 fails the NPMI rule.
- Per the plan, topics stay descriptive and no further variant is tried. The descriptive ablations (A1, A2) were not
  run, because their gate needs a recorded (non-void) decision.

**What can honestly be reported in Chapter 4:**
- The topic model is now leakage-safe and **thematic rather than geographic**: place-name topics fall from 55% to 0%,
  and geography-driven topics from 15% to 4%.
- Stability is unchanged (ARI 0.46).
- Coherence improved from −0.45 to −0.15, and is positive (+0.01) at the full-corpus origin. It still fails the
  pre-registered rule.
- Topics are used for description and monitoring, not as forecast inputs.

---

## What these fixes do and do not change

| Objective | Before | After | Still needed |
|---|---|---|---|
| 1. NLP | Topics fail 2 of 3 rules | Topics fail 1 of 4 rules (coherence, mean −0.15) | Human labels of the 300 headlines (team) |
| 2. Forecasting | Partial | Unchanged; no model refitted | 2027 prospective seals |
| 3. Geospatial | Partial | Unchanged | Adviser choice of weighting |
| 4. Baselines | C-B6 9 of 14 vs a 0/1 persistence | **Fair comparison:** C-B6 5 of 14; no candidate beats persistence | Prospective quarters; this cannot be fixed on 62 quarters |
| 5. System | In progress | Unchanged | 50 DA responses |

**Bottom line:**
- The two fixes make the evaluation **fairer and the topics better**. They do not make any objective fully achieved.
- The persistence fix makes Objective 4 **harder**: on fair terms, C-b, C-E6 and C-B6 are not proven better than
  carrying forward the latest SWS reading. This agrees with every earlier SWS study in this repository.
- On these numbers, C-B6's case as "main model" weakens further. C-E6 now has the most proven comparisons (6 of 14),
  and none of the three is distinguishable from fair persistence.

---

## Fix 3 (requested): FI6-N archive news inside C-B6 (C-B6N)

**Setup:**
- **Plan:** `PLAN_CB6N.md`, SHA-256 976076dc…, committed (5adc2f9b) before any fit.
- **Data:** the FI6-N feature file, unchanged (SHA-256 abc0e59c… = the FI6-N lock).
- **Inputs:** seven z-scored news features, on top of C-B6's 23 inputs.
- **Coverage:** news exists at 51 of 113 origins, from 2014-Q1.
- **Checks:** the news leakage check passed; the copied procedure reproduced C-B6 exactly (max difference 1e-16).
- Run: `runner/cb6n_model.py` → `out/cb6n_fits.csv`, `out/cb6n_results.json`.

**Results (62 quarters):**

| Model | Lead | Accuracy | Precision | Recall | F1 | AUC | Brier | R1–R7 |
|---|---|---|---|---|---|---|---|---|
| C-B6 | 1 | **0.806** | 0.830 | 0.907 | 0.867 | **0.723** | **0.183** | all pass |
| C-B6N (+ news) | 1 | 0.726 | 0.795 | 0.814 | 0.805 | 0.711 | 0.196 | R2, R3, R5, R7 fail |
| C-B6 | 2 | **0.806** | 0.830 | 0.907 | 0.867 | **0.712** | **0.181** | all pass |
| C-B6N (+ news) | 2 | 0.710 | 0.791 | 0.791 | 0.791 | 0.684 | 0.205 | R2, R3, R5, R7 fail |

**Paired Brier, C-B6N minus C-B6:**

| | Lead 1 | Lead 2 |
|---|---|---|
| All 62 quarters | +0.013 (p 0.84), 5 calls changed | +0.024, CI +0.0002..+0.051: **significantly worse**; 6 calls changed |
| News-era quarters only | +0.018 | +0.034 |

- **Reliable lead:** 2 → 0.
- **News share of SHAP:** about 18%. The model uses the news, but it adds noise for this target.

**Decision (pre-registered):** H8 fails. Archive news **did not improve** C-B6; it made it worse at both leads. C-B6
stays the main model. Per the plan, no other news variant is tried.

**Why this differs from FI6-N:**
- FI6-N's gain was in probability quality on a different target: a rise of more than the margin of error above the
  5-year average.
- Here the target is the 11.3% level. The latest SWS reading already carries most of the information, and seven extra
  inputs on 62 quarters let the trees fit noise.

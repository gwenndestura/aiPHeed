# v6 deviations and control outcomes

Changes or surprises after the pre-registration was committed (`3f0e0e5`). None changed a selection, a verdict or the served model.

| # | When | What | Substantive? | Effect |
|---|---|---|---|---|
| 1 | Before the first evaluation | `num_threads = 1` added to the LightGBM parameters (not listed in PREREGISTRATION §2.2), to keep runs identical across machines. | No | None on the rule. It is stricter than the pre-registered `deterministic = True` alone. |
| 2 | Before the first evaluation | A fit also falls back to "no change" if the early-stopping part has fewer than 10 rows or the inner fold is empty (`lgbm.fit`). The pre-registration lists only "< 30 rows" and "best iteration 0". | No: this path was never reached (`v6_exploratory_controls.json`: all 54 no-model fits have < 30 rows) | None |
| 3 | After the validation run | **A pre-registered control did not behave as stated.** PREREGISTRATION §7 expects "LGBM gains nothing over PERSIST" on the shuffled series. Observed at Lead 2: **LGBM-D 0.40, LGBM-D-S 0.40, LL-K 0.35, PERSIST 0.275**, and the rule selected LGBM-D at 1 of 22 issues on that series. | **Yes: reported as a failed expectation, not explained away.** | See below |
| 4 | After the validation run | **Exploratory controls** were written to investigate #3 and the leave-one-area-out result (`backend/scripts/v6_controls.py`). They were not pre-registered and are labelled EXPLORATORY. | Exploratory only | They change no decision |

## What the exploratory controls show (VERIFIED, `results/v6_exploratory_controls.json`)

| Control | Lead-2 result | Reading (INFERRED) |
|---|---|---|
| **Shuffled series vs a mean forecast** | LGBM-D 0.40; expanding area mean 0.325; PERSIST 0.275 | A shuffled series is i.i.d., so mean reversion is real there, and the `dev_mean` feature can learn it. Persistence is the wrong yardstick for that control. LGBM-D is still 3 rows above the plain mean, on **one** permutation seed. This most plausibly explains the gain, but it does not prove it. |
| **Label permutation on the real series** (training changes permuted, 20 seeds) | Mean 0.355, range 0.30–0.475. Honest LGBM-D 0.30; PERSIST 0.40. | **No sign of leakage, and no sign of skill:** the honest fit is at the bottom of what random labels produce. Random labels can reach 0.475 by chance, which also shows how noisy 40 rows are. |
| **Future-shifted indicators** (each issue given the next quarter's snapshot) | LGBM-D 0.325 vs honest 0.30 (one row); MAE 6.93 vs 7.50 | Even a deliberate leak of these indicators hardly helps, so they carry little information about hunger change. |
| **No-model census** | 54 of 84 fits have no model; all have < 30 training rows. At Lead 2, a model exists at only 6 of the 10 development-test issues (2025-01-01 onward). | **LightGBM was never fitted for the 2024 surge rows.** Those 16 rows equal persistence. Its evaluation really rests on **24 rows**. |
| **Leave-one-area-out** | Held out 0.425 vs pooled 0.30. A model exists on only 16 of 40 held-out rows; the other 24 equal persistence. On those 16 rows: 0.5625 vs persistence 0.50, MAE 3.61 vs 3.78. | The higher held-out score mainly reflects more fallback to persistence, not better generalisation. The 16 rows are too few to claim a gain. |

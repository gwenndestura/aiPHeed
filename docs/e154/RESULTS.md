# E154 results: small meaningful inputs, very simple trees

**Verdict: accuracy did not rise, but the model is far less overfit. Under the rule fixed in advance it does not replace the E151 required model.** Production is unchanged. One run, nothing tuned. Fifth look at these rows, retrospective.

| Lead 1, 72 rows | E154 | LEVEL (anchor + mean error) | E151 required |
|---|---|---|---|
| Inputs | 11 | 0 | more than 60 |
| Correct | 52 (0.722) | 51 (0.708) | 52 (0.722) |
| HIGH recall | 0.80 | 0.80 | 0.76 |
| LOW recall | 0.68 | 0.66 | 0.70 |
| AUC | 0.860 | 0.858 | 0.855 |
| Brier | 0.174 | 0.177 | 0.172 |
| Error (points) | 8.32 | 8.72 | 8.05 |
| Coverage of 90 % range | 0.86 | 0.79 | 0.96 |
| Ranking within a round | **0.70** | 0.70 | 0.67 |

* **Overfitting:** held-out error is 1.5 times in-sample, against 3.4 to 4.8 for E153's tuned trees.
* **By round:** 2018 0.636 (tie with majority), 2019 0.64, **2021 0.88 (above always-LOW's 0.84, 3 of 4 HIGH found).**
* **Other leads:** L2 0.736, L3 0.708, L4 0.722. E151's 0.75 at L4 is not repeated here, which also supports it being chance.
* **Against persistence:** Brier -0.073 [-0.132, -0.024].
* **Against E151:** +0.002 [-0.010, +0.014]. Against LEVEL: -0.003 [-0.022, +0.016].
* **Shuffled inputs:** mean 0.707, 95th percentile 0.75; 31 % of 100 runs did at least as well.
* **Slope** interval [0.46, 0.89] excludes 1. Not prevalence. Confusion: TP 20, FP 15, TN 32, FN 5.

Adoption rule: accuracy at least 0.75 **no**; Brier no worse than E151 **no** (0.174 vs 0.172, within noise); above the shuffled 95th percentile **no**.

## What this shows

1. **Eleven inputs do as well as more than sixty.** The other inputs were not adding accuracy on these rows.
2. **The level correction carries most of the accuracy.** The inputs' gain over LEVEL is 1 row, with an interval spanning zero. **Provincial input value remains unproven.**
3. **Regional consumption per person is now in use,** and employment has meaning beyond a national number. **Regional labor rates are still not in**; consumption is a stand-in for income, not labor.
4. News is left out here. That is justified by its tests, but the thesis may expect it as an input, so that is the owner's and adviser's call.

## Recommendation

**Report E151's 72.2 %, and consider E154 as the model frozen for future testing,** because it has the same accuracy, far less overfitting and inputs that can each be explained. That is a choice for simplicity, and it gives no accuracy gain. It does not meet the rule above and must not be presented as if it did.

Files: `docs/e154/PROTOCOL.md`, `backend/data/e154/out/{results.json, oof.csv, lock.json}`, `backend/app/e154/`.

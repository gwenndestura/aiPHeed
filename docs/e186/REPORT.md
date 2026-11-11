# E186: E184 plus provincial local data. Report

## Decision: **the provincial local data did not improve E184.** E184 stays the candidate; nothing was staged or deployed.

E186 added two feature sets, GOV+local and FULL+local, to Stage A's menu. The local columns are provincial farmgate palay
and wholesale rice prices, terms of trade, and NASA rainfall (`docs/e186/PROTOCOL.md`, committed `4ba31ad` before any
output). The synthetic training data is exactly E184's.

## The key finding: the local feature sets were never selected
E168's inner cross-validation chose **FULL** at all three ENNS2021 leads and **GOV** at all six ENNS2018/2019 leads. In
**0 of 9** jobs did a "+local" set fit the training folds better.

- **Same model as E184.** E186's selected model is therefore the same configuration as E184's.
- **Where the differences come from.** The local columns were in the menu, so the synthetic rows were also generated
  over them. That changed the random draws, and with them the synthetic training rows. The small differences from E184
  are that noise, **not** a contribution of the provincial data.

## Results on the 72 real rows per lead

| Lead | E168 | E184 | **E186** | E186 − E184 Brier [95 % CI] | McNemar vs E184 |
|---|---|---|---|---|---|
| 1 | 75.0 % | 76.4 % | 76.4 % | −0.0005 [−0.0021, +0.0013] | 0 vs 0 |
| 2 | 77.8 % | 79.2 % | **80.6 %** | +0.0009 [−0.0012, +0.0035] | 1 vs 0, p = 1.0 |
| 3 | 75.0 % | 77.8 % | 76.4 % | +0.0011 [−0.0016, +0.0038] | 0 vs 1, p = 1.0 |

**HIGH recall** is 0.84 / 0.88 / 0.84. **Brier** is 0.1206 / 0.1194 / 0.1269.

**Lead 2's 80.6 %** is one province more than E184 (58 against 57 of 72). Lead 3 lost one. With the same selected
features, this is a change in random synthetic rows, not a better model.

## Checks
| Check | Result |
|---|---|
| Owner's deployment rule (≥ 75 %, beats persistence, all leads; leakage) | ✅ |
| Leakage | 0.0 |
| Better than E184 (Brier CI < 0 at all leads; accuracy not lower) | ❌ |
| Beats shuffled triggers (local columns shuffled too) | ❌ +0.0011 [−0.0126, +0.0193]; shuffled accuracy 86.1 % |
| Reaches 80 % | Lead 2 only (see above) |

## ENNS 2022 seal
- **File:** `backend/data/e186/out/sealed_enns2022.json`.
- **SHA-256:** `8cbf6ede331b1b7523747d8d5fe245180d5c1242a65b5445f55b39f951758ea9`.

## Reading
- **The data exists but does not help.** The provincial price and rainfall series, which do vary by province, did not
  help the model predict the change from the latest survey on the training rows.
- **The limit.** Together with E178–E185, this points to the limit of the available validation data: three survey
  rounds and 156–532 training rows. It is not the limit of the feature set.
- **What could change it.** A new survey round (ENNS 2022 or later).

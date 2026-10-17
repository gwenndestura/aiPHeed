# E47 byte-identical repeats and artifact hashes

| run | repeat | file | sha256 (16) | identical |
|---|---|---|---|---|
| 20261017T031323Z | 20261017T032022Z | features_asof.csv | 4a64409e7f239437 | yes |
| 20261017T031323Z | 20261017T032022Z | predictions.csv | 6889b4333d2bf518 | yes |
| 20261017T031323Z | 20261017T032022Z | results.json | 8112c6f72010cce3 | yes except run_utc |
| 20261017T031323Z | 20261017T032022Z | selections.json | 33eaf39212811216 | yes |
| a1_20261017T031747Z | a1_20261017T032223Z | predictions_a1.csv | 8e526001cfac90ec | yes |
| a1_20261017T031747Z | a1_20261017T032223Z | results_a1.json | cbcfa244bcd0f2fe | yes except run_utc |

## Frozen forecasts and data

```
9bc7500083bbfaad52cbcef0d66ded5d92d5c25552be36c576bb0792af5d2641 *frozen/E47_A1_PROSPECTIVE_2027Q1.json
0433ff9864b769b27d5bfa25babd16b3f8f0c76c709e28b007fcafe7ed1b16da *frozen/E47_PROSPECTIVE_2027Q1.json
ee3adafb23d9beb6cea213a983cff1999f7f8ff2e002ab322276bce9b77389a0 *data/brent_daily_fred_raw.csv
5592d53ee00eb3e1e13d5112d1f69223f561e97c9f7077d8a05d5c587647be8d *../E46_Rice_Policy/frozen/E46_I7_PROSPECTIVE_2027Q1.json
284f23f20cf05e012082be673e6cf06497bea03950ae6ba44e4389df10d98770 *../E46_Rice_Policy/frozen/E46_I8_PROSPECTIVE_2027Q1.json
171c5ea9ba2f51f032a2b8234103e9e47949d35389b3b5d18bdc8d895e802b91 *backend/data/e46/e46_record.json
```

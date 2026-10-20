# E58: calibration of E53-A1 (C2 shrinkage vs temperature vs Platt)

## Pre-registration (written 2026-10-17T03:58Z, before any E58 result was computed)

**Base.** E53-A1 exactly as served: the same raw LightGBM probabilities from the E36 nested walk-forward (lead 1,
seed 36, pool COMPACT_T5_C / COMB_T5_C x G1/G4/G3/G2), the same labels, and the same 65 development rows
(13 target quarters 2023-Q1..2026-Q3). Only the calibration step changes. The lead-2 model (E55) is rerun with
the same three arms and reported, but it does not count toward adoption.

**Fitting rule (all arms).** At each origin t, a calibrator is fitted only on the out-of-sample raw predictions
and labels of the eligible earlier dates. These are the same dates C2 uses: `eligible_prior_dates` for lead 1 and
`e37_lib.eligible_prior` for lead 2, meaning target quarters <= t-1 whose SWS rounds were posted before the
origin. A row's own outcome and later outcomes are never used. With fewer than 3 eligible dates, the raw
probability is used unchanged, as C2 already does (MIN_DATES = 3). z = logit(raw p), with p clipped to
[1e-6, 1 - 1e-6].

**Arms.**
- **C2** (served): p' = a * p + (1 - a) * base rate, with a on the 0..1 grid (step 0.05) minimising the
  earlier rows' Brier. The run stops unless it reproduces E53-A1 (accuracy 0.785, balanced accuracy 0.836,
  AUC 0.880, Brier 0.150) and the record's served probabilities.
- **T** (temperature): p' = sigmoid(z / T), with b = 0 and T > 0 minimising the earlier rows' mean log loss
  (bounded search over log T in [-4, 4]).
- **P** (Platt): p' = sigmoid(A * z + B), with A and B minimising the earlier rows' mean log loss
  + lambda * ((A - 1)^2 + B^2). **lambda = 0.01** (fixed now), starting from A = 1, B = 0.

**Reported per arm** (lead 1, 65 rows, and lead 2, 55 rows):
- accuracy, balanced accuracy, AUC, Brier, log loss, LOW caught;
- the 5-bin reliability table and the share of predictions >= 0.5;
- for 2026-Q1..Q4 (lead 1) and 2026-Q1..Q3 + 2027-Q1 (lead 2): the five province probabilities, their spread
  (max - min), and the exact ties at 2 decimals (the number of provinces whose 2-decimal value equals
  another province's).

**Adoption rule (pre-registered).** T or P is compared with C2 on the same 65 lead-1 rows. It is eligible only if
all of these hold:
- (a) Brier <= C2 Brier AND log loss <= C2 log loss;
- (b) balanced accuracy >= 0.836 - 0.01 (= 0.826) AND AUC unchanged. The parameters differ between origins, so
  the pooled AUC over 65 rows can move slightly even though each transform is monotone. "Unchanged" is
  therefore fixed now as |AUC - C2 AUC| <= 0.005, and whether it is exactly equal is reported too;
- (c) the leakage check passes: every date used to fit the calibrator at origin t has its target quarter
  <= t - 1 and posted before O(t); none is the evaluated row or later.

If both T and P pass, prefer the lower Brier. If neither passes: "Keep C2; calibration experiments closed."

If an arm is adopted it is **not served**. Its per-quarter parameters go to `experiments/e58/E58_calibration.json`,
and the report shows what the dashboard would display (index and provinces, 2026-Q1..2027-Q1) next to the
current served values. Serving needs separate approval.

## Results

Run `20261017T040002Z`. C2 reproduces E53-A1 and the served record: **True** (lead 1 max |C2 - record| 5.0e-05 over 70 served values; lead 2, 2027-Q1: 4.0e-05). Protected md5s, the e53 record and its calibration file are identical at start and end: **True**. Platt lambda = 0.01.

### Lead 1 (E53-A1, 65 rows): adoption is judged here

| Arm | Accuracy | Balanced | AUC | Brier | Log loss | LOW caught | Share >= 0.5 | min p | max p |
|---|---|---|---|---|---|---|---|---|---|
| C2 | 0.785 | 0.836 | 0.8797 | 0.1501 | 0.4820 | 11/12 | 63% | 0.031 | 0.956 |
| T | 0.785 | 0.836 | 0.8719 | 0.1548 | 0.7240 | 11/12 | 63% | 0.000 | 1.000 |
| P | 0.877 | 0.892 | 0.8703 | 0.1226 | 0.5332 | 11/12 | 72% | 0.001 | 1.000 |

Reliability (5 bins: n, mean predicted, observed HIGH share):

| Arm | 0.0-0.2 | 0.2-0.4 | 0.4-0.6 | 0.6-0.8 | 0.8-1.0 |
|---|---|---|---|---|---|
| C2 | 10: 0.058 / 0.400 | 4: 0.296 / 0.750 | 12: 0.441 / 0.667 | 7: 0.722 / 1.000 | 32: 0.895 / 0.969 |
| T | 10: 0.042 / 0.400 | 3: 0.250 / 0.667 | 14: 0.446 / 0.714 | 7: 0.706 / 1.000 | 31: 0.937 / 0.968 |
| P | 10: 0.047 / 0.400 | 1: 0.381 / 1.000 | 10: 0.442 / 0.500 | 7: 0.693 / 1.000 | 37: 0.958 / 0.973 |

Province probabilities per quarter (spread = max - min; ties = provinces sharing a 2-decimal value):

| Quarter | Arm | Cavite | Laguna | Batangas | Rizal | Quezon | index | spread | ties |
|---|---|---|---|---|---|---|---|---|---|
| 2026-Q1 | raw | 0.9996 | 0.9998 | 0.9944 | 0.9992 | 0.9961 | 0.9978 | 0.0054 | 4 |
| 2026-Q1 | C2 | 0.8925 | 0.8926 | 0.8891 | 0.8922 | 0.8902 | 0.8913 | 0.0035 | 5 |
| 2026-Q1 | T | 0.9876 | 0.9906 | 0.9465 | 0.9810 | 0.9560 | 0.9723 | 0.0441 | 2 |
| 2026-Q1 | P | 0.9995 | 0.9997 | 0.9959 | 0.9991 | 0.9969 | 0.9982 | 0.0037 | 5 |
| 2026-Q2 | raw | 0.9895 | 0.9948 | 0.0450 | 0.9368 | 0.9776 | 0.7887 | 0.9498 | 2 |
| 2026-Q2 | C2 | 0.8743 | 0.8775 | 0.3076 | 0.8427 | 0.8672 | 0.7538 | 0.5699 | 2 |
| 2026-Q2 | T | 0.8811 | 0.9102 | 0.2063 | 0.7665 | 0.8409 | 0.7210 | 0.7038 | 0 |
| 2026-Q2 | P | 0.9687 | 0.9779 | 0.4028 | 0.9244 | 0.9547 | 0.8457 | 0.5751 | 0 |
| 2026-Q3 | raw | 0.9958 | 0.9952 | 0.9732 | 0.9973 | 0.9860 | 0.9895 | 0.0241 | 3 |
| 2026-Q3 | C2 | 0.9001 | 0.8997 | 0.8854 | 0.9010 | 0.8937 | 0.8960 | 0.0157 | 5 |
| 2026-Q3 | T | 0.9300 | 0.9259 | 0.8454 | 0.9427 | 0.8821 | 0.9052 | 0.0973 | 2 |
| 2026-Q3 | P | 0.9814 | 0.9802 | 0.9526 | 0.9853 | 0.9658 | 0.9731 | 0.0327 | 2 |
| 2026-Q4 | raw | 0.9975 | 0.9914 | 0.0939 | 0.9988 | 0.9981 | 0.8160 | 0.9049 | 3 |
| 2026-Q4 | C2 | 0.9165 | 0.9122 | 0.2839 | 0.9173 | 0.9169 | 0.7893 | 0.6334 | 3 |
| 2026-Q4 | T | 0.9582 | 0.9224 | 0.2347 | 0.9707 | 0.9633 | 0.8099 | 0.7360 | 2 |
| 2026-Q4 | P | 0.9893 | 0.9784 | 0.4634 | 0.9928 | 0.9907 | 0.8829 | 0.5293 | 3 |

Fitted parameters by target quarter (null = fewer than 3 eligible dates, raw probability used):

| Target | C2 a | T | P A | P B | dates used |
|---|---|---|---|---|---|
| 2023-Q1 | – | – | – | – | 0 |
| 2023-Q2 | – | – | – | – | 0 |
| 2023-Q3 | – | – | – | – | 1 |
| 2023-Q4 | – | – | – | – | 2 |
| 2024-Q1 | 1.0 | 0.259 | 2.387 | 0.360 | 3 |
| 2024-Q2 | 1.0 | 0.975 | 1.069 | 0.537 | 4 |
| 2024-Q3 | 0.85 | 1.683 | 0.709 | 0.807 | 5 |
| 2024-Q4 | 0.75 | 1.811 | 0.689 | 1.027 | 6 |
| 2025-Q1 | 0.65 | 1.992 | 0.708 | 1.284 | 7 |
| 2025-Q4 | 0.65 | 1.802 | 0.772 | 1.499 | 9 |
| 2026-Q1 | 0.65 | 1.802 | 0.772 | 1.499 | 9 |
| 2026-Q2 | 0.6 | 2.267 | 0.504 | 1.145 | 10 |
| 2026-Q3 | 0.65 | 2.115 | 0.516 | 1.145 | 11 |
| 2026-Q4 | 0.7 | 1.918 | 0.565 | 1.134 | 12 |

Leakage check: 0 fitting dates with a target after the origin's published quarters.

### Lead 2 (E55, 55 rows): reported only

| Arm | Accuracy | Balanced | AUC | Brier | Log loss | LOW caught | Share >= 0.5 | min p | max p |
|---|---|---|---|---|---|---|---|---|---|
| C2 | 0.673 | 0.670 | 0.8112 | 0.2141 | 0.6295 | 4/6 | 64% | 0.016 | 0.997 |
| T | 0.655 | 0.660 | 0.8010 | 0.2263 | 0.6559 | 4/6 | 62% | 0.033 | 0.999 |
| P | 0.818 | 0.752 | 0.8452 | 0.1422 | 0.4263 | 4/6 | 78% | 0.079 | 0.999 |

Reliability (5 bins: n, mean predicted, observed HIGH share):

| Arm | 0.0-0.2 | 0.2-0.4 | 0.4-0.6 | 0.6-0.8 | 0.8-1.0 |
|---|---|---|---|---|---|
| C2 | 7: 0.138 / 0.571 | 11: 0.266 / 0.909 | 10: 0.550 / 0.800 | 3: 0.642 / 1.000 | 24: 0.885 / 1.000 |
| T | 8: 0.107 / 0.625 | 10: 0.268 / 0.900 | 11: 0.533 / 0.818 | 3: 0.661 / 1.000 | 23: 0.891 / 1.000 |
| P | 2: 0.095 / 0.500 | 8: 0.275 / 0.875 | 10: 0.556 / 0.600 | 7: 0.707 / 1.000 | 28: 0.909 / 1.000 |

Province probabilities per quarter (spread = max - min; ties = provinces sharing a 2-decimal value):

| Quarter | Arm | Cavite | Laguna | Batangas | Rizal | Quezon | index | spread | ties |
|---|---|---|---|---|---|---|---|---|---|
| 2026-Q1 | raw | 0.2125 | 0.9968 | 0.2266 | 0.0463 | 0.3927 | 0.3750 | 0.9505 | 0 |
| 2026-Q1 | C2 | 0.3139 | 0.9413 | 0.3252 | 0.1809 | 0.4581 | 0.4439 | 0.7604 | 0 |
| 2026-Q1 | T | 0.3030 | 0.9748 | 0.3142 | 0.1275 | 0.4312 | 0.4302 | 0.8473 | 0 |
| 2026-Q1 | P | 0.7151 | 0.9896 | 0.7237 | 0.5091 | 0.7975 | 0.7470 | 0.4806 | 2 |
| 2026-Q2 | raw | 0.5134 | 0.5134 | 0.0332 | 0.0861 | 0.4547 | 0.3201 | 0.4802 | 2 |
| 2026-Q2 | C2 | 0.5545 | 0.5545 | 0.1704 | 0.2128 | 0.5076 | 0.4000 | 0.3841 | 2 |
| 2026-Q2 | T | 0.5085 | 0.5085 | 0.1049 | 0.1822 | 0.4711 | 0.3550 | 0.4036 | 2 |
| 2026-Q2 | P | 0.8352 | 0.8352 | 0.4643 | 0.5934 | 0.8178 | 0.7092 | 0.3709 | 2 |
| 2026-Q3 | raw | 0.9920 | 0.9977 | 0.5200 | 0.9812 | 0.8764 | 0.8735 | 0.4776 | 0 |
| 2026-Q3 | C2 | 0.8589 | 0.8617 | 0.6229 | 0.8535 | 0.8011 | 0.7996 | 0.2388 | 2 |
| 2026-Q3 | T | 0.8619 | 0.9089 | 0.5076 | 0.8180 | 0.6778 | 0.7549 | 0.4013 | 0 |
| 2026-Q3 | P | 0.9742 | 0.9842 | 0.8462 | 0.9638 | 0.9219 | 0.9381 | 0.1380 | 0 |
| 2027-Q1 | raw | 0.9832 | 0.9832 | 0.6137 | 0.9832 | 0.9832 | 0.9093 | 0.3695 | 4 |
| 2027-Q1 | C2 | 0.8200 | 0.8200 | 0.7091 | 0.8200 | 0.8200 | 0.7978 | 0.1108 | 4 |
| 2027-Q1 | T | 0.7650 | 0.7650 | 0.5335 | 0.7650 | 0.7650 | 0.7187 | 0.2315 | 4 |
| 2027-Q1 | P | 0.9709 | 0.9709 | 0.8816 | 0.9709 | 0.9709 | 0.9530 | 0.0893 | 4 |

Fitted parameters by target quarter (null = fewer than 3 eligible dates, raw probability used):

| Target | C2 a | T | P A | P B | dates used |
|---|---|---|---|---|---|
| 2023-Q3 | – | – | – | – | 0 |
| 2023-Q4 | – | – | – | – | 0 |
| 2024-Q1 | – | – | – | – | 0 |
| 2024-Q2 | – | – | – | – | 1 |
| 2024-Q3 | – | – | – | – | 2 |
| 2024-Q4 | 1.0 | 0.838 | 1.059 | 0.864 | 3 |
| 2025-Q1 | 1.0 | 1.212 | 0.802 | 1.212 | 4 |
| 2025-Q4 | 0.8 | 1.573 | 0.516 | 1.596 | 7 |
| 2026-Q1 | 0.8 | 1.573 | 0.516 | 1.596 | 7 |
| 2026-Q2 | 0.8 | 1.573 | 0.516 | 1.596 | 7 |
| 2026-Q3 | 0.5 | 2.633 | 0.407 | 1.673 | 8 |
| 2027-Q1 | 0.3 | 3.447 | 0.416 | 1.815 | 10 |

Leakage check: 0 fitting dates with a target after the origin's published quarters.

### Adoption (lead 1, rule fixed before results)

| Arm | (a) Brier and log loss <= C2 | (b) balanced >= 0.826 and AUC within 0.005 | (c) leakage | AUC - C2 AUC | Eligible |
|---|---|---|---|---|---|
| T | **no** | **no** | yes | -0.0079 | **no** |
| P | **no** | **no** | yes | -0.0094 | **no** |

**Verdict: Keep C2; calibration experiments closed.**

### What the dashboard shows now vs each arm

| Quarter | Version | CALABARZON | Cavite | Laguna | Batangas | Rizal | Quezon |
|---|---|---|---|---|---|---|---|
| 2026-Q1 (lead 1) | served now | 0.8913 | 0.8925 | 0.8926 | 0.8891 | 0.8922 | 0.8902 |
| 2026-Q1 (lead 1) | C2 | 0.8913 | 0.8925 | 0.8926 | 0.8891 | 0.8922 | 0.8902 |
| 2026-Q1 (lead 1) | T | 0.9723 | 0.9876 | 0.9906 | 0.9465 | 0.9810 | 0.9560 |
| 2026-Q1 (lead 1) | P | 0.9982 | 0.9995 | 0.9997 | 0.9959 | 0.9991 | 0.9969 |
| 2026-Q2 (lead 1) | served now | 0.7539 | 0.8743 | 0.8775 | 0.3076 | 0.8427 | 0.8672 |
| 2026-Q2 (lead 1) | C2 | 0.7538 | 0.8743 | 0.8775 | 0.3076 | 0.8427 | 0.8672 |
| 2026-Q2 (lead 1) | T | 0.7210 | 0.8811 | 0.9102 | 0.2063 | 0.7665 | 0.8409 |
| 2026-Q2 (lead 1) | P | 0.8457 | 0.9687 | 0.9779 | 0.4028 | 0.9244 | 0.9547 |
| 2026-Q3 (lead 1) | served now | 0.8960 | 0.9001 | 0.8997 | 0.8854 | 0.9010 | 0.8937 |
| 2026-Q3 (lead 1) | C2 | 0.8960 | 0.9001 | 0.8997 | 0.8854 | 0.9010 | 0.8937 |
| 2026-Q3 (lead 1) | T | 0.9052 | 0.9300 | 0.9259 | 0.8454 | 0.9427 | 0.8821 |
| 2026-Q3 (lead 1) | P | 0.9731 | 0.9814 | 0.9802 | 0.9526 | 0.9853 | 0.9658 |
| 2026-Q4 (lead 1) | served now | 0.7894 | 0.9165 | 0.9122 | 0.2839 | 0.9173 | 0.9169 |
| 2026-Q4 (lead 1) | C2 | 0.7893 | 0.9165 | 0.9122 | 0.2839 | 0.9173 | 0.9169 |
| 2026-Q4 (lead 1) | T | 0.8099 | 0.9582 | 0.9224 | 0.2347 | 0.9707 | 0.9633 |
| 2026-Q4 (lead 1) | P | 0.8829 | 0.9893 | 0.9784 | 0.4634 | 0.9928 | 0.9907 |
| 2027-Q1 (lead 2) | served now | 0.7978 | 0.8200 | 0.8200 | 0.7091 | 0.8200 | 0.8200 |
| 2027-Q1 (lead 2) | C2 | 0.7978 | 0.8200 | 0.8200 | 0.7091 | 0.8200 | 0.8200 |
| 2027-Q1 (lead 2) | T | 0.7187 | 0.7650 | 0.7650 | 0.5335 | 0.7650 | 0.7650 |
| 2027-Q1 (lead 2) | P | 0.9530 | 0.9709 | 0.9709 | 0.8816 | 0.9709 | 0.9709 |

plan 2973784ae15ba8ce45500789b3f777e78c9e2ca082386cb6fe70295dd6b046ad
max reliable lead: 0

## L1 verdict 2010-Q1..2026-Q3, 62 q, HIGH share 0.694

| Model | q | Acc | Bal | Prec | Rec | F1 | AUC | Brier | TP/FP/FN/TN | Fails | vs REF diff (p) | vs PERSIST diff (p) | fallback | Platt skipped | sigma fb |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REF | 62 | 0.790 | 0.717 | 0.812 | 0.907 | 0.857 | 0.702 | 0.188 | 39/9/4/10 | R7 | +0.000 (1.000) | -0.151 (0.000) | 0 |  |  |
| I1 | 62 | 0.758 | 0.679 | 0.792 | 0.884 | 0.835 | 0.712 | 0.185 | 38/10/5/9 | R3, R7 | -0.002 (0.425) | -0.153 (0.000) | 0 |  |  |
| I2 | 62 | 0.710 | 0.541 | 0.712 | 0.977 | 0.824 | 0.678 | 0.197 | 42/17/1/2 | R2, R3, R7 | +0.010 (0.725) | -0.142 (0.003) | 0 |  | 0 |
| I3 | 62 | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.581 | 0.209 | 43/19/0/0 | R2, R3, R7 | +0.021 (0.850) | -0.130 (0.006) | 0 | 0 |  |
| ALL | 62 | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.533 | 0.213 | 43/19/0/0 | R2, R3, R5, R7 | +0.026 (0.860) | -0.126 (0.008) | 0 | 0 | 0 |
| REF+news | 62 | 0.758 | 0.693 | 0.804 | 0.860 | 0.831 | 0.688 | 0.195 | 37/9/6/10 | R3, R5, R7 | +0.008 (0.820) | -0.143 (0.000) | 0 |  |  |
| I1+news | 62 | 0.742 | 0.667 | 0.787 | 0.860 | 0.822 | 0.706 | 0.187 | 37/10/6/9 | R2, R3, R7 | -0.001 (0.474) | -0.152 (0.000) | 0 |  |  |
| I2+news | 62 | 0.726 | 0.567 | 0.724 | 0.977 | 0.832 | 0.687 | 0.195 | 42/16/1/3 | R2, R3, R7 | +0.007 (0.674) | -0.144 (0.002) | 0 |  | 0 |
| I3+news | 62 | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.573 | 0.209 | 43/19/0/0 | R2, R3, R7 | +0.022 (0.854) | -0.130 (0.006) | 0 | 0 |  |
| ALL+news | 62 | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.534 | 0.213 | 43/19/0/0 | R2, R3, R5, R7 | +0.025 (0.860) | -0.126 (0.008) | 0 | 0 | 0 |
| PERSIST | 62 | 0.661 | 0.594 | 0.750 | 0.767 | 0.759 | 0.594 | 0.339 | 33/11/10/8 | R2, R3, R4, R5, R7 | +0.151 (1.000) | +0.000 (1.000) | 0 |  |  |
| LOGIT | 62 | 0.710 | 0.629 | 0.766 | 0.837 | 0.800 | 0.759 | 0.193 | 36/11/7/8 | R2, R3, R5, R7 | +0.005 (0.560) | -0.146 (0.001) | 0 |  |  |
| PSA-only | 62 | 0.726 | 0.582 | 0.732 | 0.953 | 0.828 | 0.633 | 0.208 | 41/15/2/4 | R2, R3, R5, R7 | +0.021 (0.744) | -0.130 (0.011) | 0 |  |  |
| NLP-only | 20 | 0.450 | 0.478 | 0.625 | 0.385 | 0.476 | 0.390 | 0.353 | 5/3/8/4 | R1, R2, R3, R4, R5, R6, R7 | +0.153 (0.998) | +0.003 (0.510) | 13 |  |  |
| ALWAYS-HIGH | 62 | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | – | 0.306 | 43/19/0/0 | R2, R3, R5, R7 | +0.119 (0.991) | -0.032 (0.365) |  |  |  |
| ALWAYS-LOW | 62 | 0.306 | 0.500 | – | 0.000 | 0.000 | – | 0.694 | 0/0/43/19 | R2, R3, R4, R5, R6, R7 | +0.506 (1.000) | +0.355 (1.000) |  |  |  |

Rule values for arms:

- REF: R1 PASS 62 q, 62 rows; R2 PASS 0.7903; R3 PASS 0.7166; R4 PASS 0.7903 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1512, p 0.000', 'CLIM': 'diff -0.0331, p 0.096'}; R6 PASS P 0.812, R 0.907; R7 FAIL thirds [0.952, 0.571, 0.85] (sizes [21, 21, 20]), LOQO min 0.787; other split [0.95, 0.571, 0.857] (sizes [20, 21, 21])
- I1: R1 PASS 62 q, 62 rows; R2 PASS 0.7581; R3 FAIL 0.6787; R4 PASS 0.7581 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1535, p 0.000', 'CLIM': 'diff -0.0354, p 0.065'}; R6 PASS P 0.792, R 0.884; R7 FAIL thirds [0.952, 0.476, 0.85] (sizes [21, 21, 20]), LOQO min 0.754; other split [0.95, 0.476, 0.857] (sizes [20, 21, 21])
- I2: R1 PASS 62 q, 62 rows; R2 FAIL 0.7097; R3 FAIL 0.541; R4 PASS 0.7097 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1417, p 0.003', 'CLIM': 'diff -0.0236, p 0.087'}; R6 PASS P 0.712, R 0.977; R7 FAIL thirds [0.952, 0.524, 0.65] (sizes [21, 21, 20]), LOQO min 0.705; other split [0.95, 0.524, 0.667] (sizes [20, 21, 21])
- I3: R1 PASS 62 q, 62 rows; R2 FAIL 0.6935; R3 FAIL 0.5; R4 PASS 0.6935 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1299, p 0.006', 'CLIM': 'diff -0.0119, p 0.027'}; R6 PASS P 0.694, R 1.000; R7 FAIL thirds [0.952, 0.476, 0.65] (sizes [21, 21, 20]), LOQO min 0.689; other split [0.95, 0.476, 0.667] (sizes [20, 21, 21])
- ALL: R1 PASS 62 q, 62 rows; R2 FAIL 0.6935; R3 FAIL 0.5; R4 PASS 0.6935 vs 0.3065 / 0.6613; R5 FAIL {'PERSIST-SI': 'diff -0.1255, p 0.008', 'CLIM': 'diff -0.0074, p 0.115'}; R6 PASS P 0.694, R 1.000; R7 FAIL thirds [0.952, 0.476, 0.65] (sizes [21, 21, 20]), LOQO min 0.689; other split [0.95, 0.476, 0.667] (sizes [20, 21, 21])
- REF+news: R1 PASS 62 q, 62 rows; R2 PASS 0.7581; R3 FAIL 0.6934; R4 PASS 0.7581 vs 0.3065 / 0.6613; R5 FAIL {'PERSIST-SI': 'diff -0.1435, p 0.000', 'CLIM': 'diff -0.0254, p 0.171'}; R6 PASS P 0.804, R 0.860; R7 FAIL thirds [0.952, 0.571, 0.75] (sizes [21, 21, 20]), LOQO min 0.754; other split [0.95, 0.571, 0.762] (sizes [20, 21, 21])
- I1+news: R1 PASS 62 q, 62 rows; R2 FAIL 0.7419; R3 FAIL 0.6671; R4 PASS 0.7419 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1517, p 0.000', 'CLIM': 'diff -0.0336, p 0.079'}; R6 PASS P 0.787, R 0.860; R7 FAIL thirds [0.952, 0.476, 0.8] (sizes [21, 21, 20]), LOQO min 0.738; other split [0.95, 0.476, 0.81] (sizes [20, 21, 21])
- I2+news: R1 PASS 62 q, 62 rows; R2 FAIL 0.7258; R3 FAIL 0.5673; R4 PASS 0.7258 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1441, p 0.002', 'CLIM': 'diff -0.0260, p 0.069'}; R6 PASS P 0.724, R 0.977; R7 FAIL thirds [0.952, 0.524, 0.7] (sizes [21, 21, 20]), LOQO min 0.721; other split [0.95, 0.524, 0.714] (sizes [20, 21, 21])
- I3+news: R1 PASS 62 q, 62 rows; R2 FAIL 0.6935; R3 FAIL 0.5; R4 PASS 0.6935 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1296, p 0.006', 'CLIM': 'diff -0.0116, p 0.033'}; R6 PASS P 0.694, R 1.000; R7 FAIL thirds [0.952, 0.476, 0.65] (sizes [21, 21, 20]), LOQO min 0.689; other split [0.95, 0.476, 0.667] (sizes [20, 21, 21])
- ALL+news: R1 PASS 62 q, 62 rows; R2 FAIL 0.6935; R3 FAIL 0.5; R4 PASS 0.6935 vs 0.3065 / 0.6613; R5 FAIL {'PERSIST-SI': 'diff -0.1258, p 0.008', 'CLIM': 'diff -0.0077, p 0.113'}; R6 PASS P 0.694, R 1.000; R7 FAIL thirds [0.952, 0.476, 0.65] (sizes [21, 21, 20]), LOQO min 0.689; other split [0.95, 0.476, 0.667] (sizes [20, 21, 21])

### L1 dev_2010_2022 2010-Q1..2022-Q4, 48 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 48 | 0.729 | 0.205 | False | R2, R3, R5 |
| I1 | 48 | 0.688 | 0.207 | False | R2, R3, R5, R7 |
| I2 | 48 | 0.688 | 0.213 | False | R2, R3, R5, R7 |
| I3 | 48 | 0.667 | 0.219 | False | R2, R3, R7 |
| ALL | 48 | 0.667 | 0.224 | False | R2, R3, R5, R7 |
| REF+news | 48 | 0.729 | 0.205 | False | R2, R3, R5 |
| I1+news | 48 | 0.688 | 0.207 | False | R2, R3, R5, R7 |
| I2+news | 48 | 0.688 | 0.213 | False | R2, R3, R5, R7 |
| I3+news | 48 | 0.667 | 0.219 | False | R2, R3, R7 |
| ALL+news | 48 | 0.667 | 0.225 | False | R2, R3, R5, R7 |
| PERSIST | 48 | 0.604 | 0.396 | False | R2, R3, R4, R5, R7 |
| LOGIT | 48 | 0.688 | 0.217 | False | R2, R3, R5, R7 |
| PSA-only | 48 | 0.708 | 0.221 | False | R2, R3, R5, R7 |
| NLP-only | 6 | 0.333 | 0.393 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 48 | 0.667 | 0.333 | False | R2, R3, R5, R7 |
| ALWAYS-LOW | 48 | 0.333 | 0.667 | False | R2, R3, R4, R5, R6, R7 |

### L1 block_2023_2026 2023-Q1..2026-Q3, 14 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 14 | 1.000 | 0.126 | False | R1, R5 |
| I1 | 14 | 1.000 | 0.111 | False | R1, R5 |
| I2 | 14 | 0.786 | 0.142 | False | R1, R3, R4, R5, R7 |
| I3 | 14 | 0.786 | 0.174 | False | R1, R3, R4, R5, R7 |
| ALL | 14 | 0.786 | 0.176 | False | R1, R3, R4, R5, R7 |
| REF+news | 14 | 0.857 | 0.160 | False | R1, R4, R5 |
| I1+news | 14 | 0.929 | 0.119 | False | R1, R5 |
| I2+news | 14 | 0.857 | 0.131 | False | R1, R3, R4, R5 |
| I3+news | 14 | 0.786 | 0.175 | False | R1, R3, R4, R5, R7 |
| ALL+news | 14 | 0.786 | 0.173 | False | R1, R3, R4, R5, R7 |
| PERSIST | 14 | 0.857 | 0.143 | False | R1, R4, R5 |
| LOGIT | 14 | 0.786 | 0.111 | False | R1, R3, R4, R5, R7 |
| PSA-only | 14 | 0.786 | 0.163 | False | R1, R4, R5 |
| NLP-only | 14 | 0.500 | 0.336 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 14 | 0.786 | 0.214 | False | R1, R3, R4, R5, R7 |
| ALWAYS-LOW | 14 | 0.214 | 0.786 | False | R1, R2, R3, R4, R5, R6, R7 |

### L1 news_era 2021-Q2..2026-Q3, 20 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 20 | 0.850 | 0.200 | False | R1, R5, R7 |
| I1 | 20 | 0.850 | 0.178 | False | R1, R7 |
| I2 | 20 | 0.650 | 0.223 | False | R1, R2, R3, R4, R5, R7 |
| I3 | 20 | 0.650 | 0.225 | False | R1, R2, R3, R4, R5, R7 |
| ALL | 20 | 0.650 | 0.227 | False | R1, R2, R3, R4, R5, R7 |
| REF+news | 20 | 0.750 | 0.224 | False | R1, R5, R7 |
| I1+news | 20 | 0.800 | 0.184 | False | R1, R7 |
| I2+news | 20 | 0.700 | 0.216 | False | R1, R2, R3, R5, R7 |
| I3+news | 20 | 0.650 | 0.226 | False | R1, R2, R3, R4, R5, R7 |
| ALL+news | 20 | 0.650 | 0.226 | False | R1, R2, R3, R4, R5, R7 |
| PERSIST | 20 | 0.650 | 0.350 | False | R1, R2, R3, R4, R5, R7 |
| LOGIT | 20 | 0.750 | 0.141 | False | R1, R3, R7 |
| PSA-only | 20 | 0.750 | 0.184 | False | R1, R5, R7 |
| NLP-only | 20 | 0.450 | 0.353 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 20 | 0.650 | 0.350 | False | R1, R2, R3, R4, R5, R7 |
| ALWAYS-LOW | 20 | 0.350 | 0.650 | False | R1, R2, R3, R4, R5, R6, R7 |

### L1 S1_no_phone_2020 2010-Q1..2026-Q3, 60 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 60 | 0.800 | 0.185 | True | none |
| I1 | 60 | 0.767 | 0.185 | False | R3, R7 |
| I2 | 60 | 0.700 | 0.198 | False | R2, R3, R7 |
| I3 | 60 | 0.683 | 0.211 | False | R2, R3, R4, R7 |
| ALL | 60 | 0.683 | 0.217 | False | R2, R3, R4, R5, R7 |
| REF+news | 60 | 0.767 | 0.193 | False | R5 |
| I1+news | 60 | 0.750 | 0.186 | False | R3, R7 |
| I2+news | 60 | 0.717 | 0.196 | False | R2, R3, R7 |
| I3+news | 60 | 0.683 | 0.212 | False | R2, R3, R4, R7 |
| ALL+news | 60 | 0.683 | 0.216 | False | R2, R3, R4, R5, R7 |
| PERSIST | 60 | 0.683 | 0.317 | False | R2, R3, R4, R5, R7 |
| LOGIT | 60 | 0.733 | 0.179 | False | R2, R3, R7 |
| PSA-only | 60 | 0.717 | 0.210 | False | R2, R3, R5, R7 |
| NLP-only | 20 | 0.450 | 0.353 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 60 | 0.683 | 0.317 | False | R2, R3, R4, R5, R7 |
| ALWAYS-LOW | 60 | 0.317 | 0.683 | False | R2, R3, R4, R5, R6, R7 |

### L1 S2_no_adults_2025Q2plus 2010-Q1..2024-Q4, 56 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 56 | 0.768 | 0.194 | False | R5, R7 |
| I1 | 56 | 0.732 | 0.198 | False | R2, R3, R5, R7 |
| I2 | 56 | 0.679 | 0.210 | False | R2, R3, R5, R7 |
| I3 | 56 | 0.661 | 0.219 | False | R2, R3, R7 |
| ALL | 56 | 0.661 | 0.225 | False | R2, R3, R5, R7 |
| REF+news | 56 | 0.732 | 0.205 | False | R2, R3, R5, R7 |
| I1+news | 56 | 0.714 | 0.200 | False | R2, R3, R5, R7 |
| I2+news | 56 | 0.696 | 0.210 | False | R2, R3, R5, R7 |
| I3+news | 56 | 0.661 | 0.220 | False | R2, R3, R7 |
| ALL+news | 56 | 0.661 | 0.226 | False | R2, R3, R5, R7 |
| PERSIST | 56 | 0.625 | 0.375 | False | R2, R3, R4, R5, R7 |
| LOGIT | 56 | 0.679 | 0.209 | False | R2, R3, R5, R7 |
| PSA-only | 56 | 0.732 | 0.206 | False | R2, R3, R7 |
| NLP-only | 14 | 0.429 | 0.345 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 56 | 0.661 | 0.339 | False | R2, R3, R5, R7 |
| ALWAYS-LOW | 56 | 0.339 | 0.661 | False | R2, R3, R4, R5, R6, R7 |

### L1 S3_both 2010-Q1..2024-Q4, 54 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 54 | 0.778 | 0.192 | False | R7 |
| I1 | 54 | 0.741 | 0.198 | False | R2, R3, R7 |
| I2 | 54 | 0.667 | 0.212 | False | R2, R3, R5, R7 |
| I3 | 54 | 0.648 | 0.222 | False | R2, R3, R4, R7 |
| ALL | 54 | 0.648 | 0.230 | False | R2, R3, R4, R5, R7 |
| REF+news | 54 | 0.741 | 0.203 | False | R2, R3, R5, R7 |
| I1+news | 54 | 0.722 | 0.200 | False | R2, R3, R5, R7 |
| I2+news | 54 | 0.685 | 0.212 | False | R2, R3, R5, R7 |
| I3+news | 54 | 0.648 | 0.223 | False | R2, R3, R4, R7 |
| ALL+news | 54 | 0.648 | 0.230 | False | R2, R3, R4, R5, R7 |
| PERSIST | 54 | 0.648 | 0.352 | False | R2, R3, R4, R5, R7 |
| LOGIT | 54 | 0.704 | 0.195 | False | R2, R3, R5, R7 |
| PSA-only | 54 | 0.722 | 0.208 | False | R2, R3, R7 |
| NLP-only | 14 | 0.429 | 0.345 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 54 | 0.648 | 0.352 | False | R2, R3, R4, R5, R7 |
| ALWAYS-LOW | 54 | 0.352 | 0.648 | False | R2, R3, R4, R5, R6, R7 |

### L1 selection: {'passing': [], 'carried_forward': 'REF', 'rule': 'lowest Brier among arms passing R1-R7, else REF'}

| Comparator | q | Brier proposed | Brier comparator | diff | p | Holm p |
|---|---|---|---|---|---|---|
| PERSIST | 62 | 0.188 | 0.339 | -0.151 | 0.000 | 0.001 |
| PSA-only | 62 | 0.188 | 0.208 | -0.021 | 0.256 | 0.511 |
| NLP-only | 20 | 0.200 | 0.353 | -0.153 | 0.002 | 0.008 |
| LOGIT | 62 | 0.188 | 0.193 | -0.005 | 0.440 | 0.511 |
| ALWAYS-HIGH | 62 | 0.188 | 0.306 | -0.119 | 0.009 | 0.028 |

### L1 news ablation (with news minus without)

| Arm | full diff (p) | news-era q | news-era diff (p) |
|---|---|---|---|
| REF | +0.0077 (0.820) | 20 | +0.0239 (0.842) |
| I1 | +0.0018 (0.636) | 20 | +0.0055 (0.664) |
| I2 | -0.0024 (0.112) | 20 | -0.0074 (0.120) |
| I3 | +0.0003 (0.563) | 20 | +0.0009 (0.596) |
| ALL | -0.0002 (0.393) | 20 | -0.0008 (0.404) |

### L1 SHAP group shares (%)

| Arm | rows | H1 Hunger (SWS) | A1-A2 Food and headline prices | A3 Rice | C1 Climate (ONI) | C2 Typhoons | C3 Crops | C4 Fisheries | World prices | N1 News | Area indicator |
|---|---|---|---|---|---|---|---|---|---|---|---|
| REF (SHAP of REF) | 62 | 64.7 | 6.3 | 2.8 | 2.0 | 0.1 | 0.9 | 1.0 | 22.4 |  |  |
| I1 (SHAP of I1) | 62 | 52.1 | 5.6 | 1.5 | 4.3 | 0.0 | 0.6 | 1.9 | 32.4 |  | 1.7 |
| I2 (SHAP of I2) | 62 | 68.6 | 8.5 | 0.9 | 7.4 | 0.0 | 0.5 | 0.3 | 13.7 |  |  |
| I3 (SHAP of REF) | 62 | 64.7 | 6.3 | 2.8 | 2.0 | 0.1 | 0.9 | 1.0 | 22.4 |  |  |
| ALL (SHAP of I12) | 62 | 53.2 | 9.9 | 3.0 | 4.0 | 0.0 | 0.2 | 1.9 | 24.9 |  | 3.0 |
| REF+news (SHAP of REF+news) | 62 | 64.3 | 6.1 | 2.5 | 1.9 | 0.1 | 0.8 | 0.5 | 21.2 | 2.8 |  |
| I1+news (SHAP of I1+news) | 62 | 52.3 | 5.4 | 1.3 | 4.3 | 0.0 | 0.5 | 1.3 | 32.1 | 1.2 | 1.5 |
| I2+news (SHAP of I2+news) | 62 | 65.8 | 8.2 | 0.7 | 7.3 | 0.0 | 0.7 | 0.1 | 13.0 | 4.1 |  |
| I3+news (SHAP of REF+news) | 62 | 64.3 | 6.1 | 2.5 | 1.9 | 0.1 | 0.8 | 0.5 | 21.2 | 2.8 |  |
| ALL+news (SHAP of I12+news) | 62 | 52.2 | 9.6 | 2.9 | 3.9 | 0.0 | 0.1 | 1.2 | 24.6 | 2.6 | 2.8 |

## L2 verdict 2010-Q1..2026-Q3, 62 q, HIGH share 0.694

| Model | q | Acc | Bal | Prec | Rec | F1 | AUC | Brier | TP/FP/FN/TN | Fails | vs REF diff (p) | vs PERSIST diff (p) | fallback | Platt skipped | sigma fb |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REF | 62 | 0.790 | 0.717 | 0.812 | 0.907 | 0.857 | 0.704 | 0.184 | 39/9/4/10 | R7 | +0.000 (1.000) | -0.155 (0.000) | 0 |  |  |
| I1 | 62 | 0.742 | 0.667 | 0.787 | 0.860 | 0.822 | 0.666 | 0.198 | 37/10/6/9 | R2, R3, R5, R7 | +0.014 (0.838) | -0.140 (0.001) | 0 |  |  |
| I2 | 62 | 0.742 | 0.579 | 0.729 | 1.000 | 0.843 | 0.710 | 0.188 | 43/16/0/3 | R2, R3, R7 | +0.004 (0.611) | -0.151 (0.001) | 0 |  | 0 |
| I3 | 62 | 0.677 | 0.488 | 0.689 | 0.977 | 0.808 | 0.682 | 0.197 | 42/19/1/0 | R2, R3, R7 | +0.013 (0.843) | -0.142 (0.001) | 0 | 0 |  |
| ALL | 62 | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.606 | 0.215 | 43/19/0/0 | R2, R3, R5, R7 | +0.032 (0.912) | -0.123 (0.011) | 0 | 0 | 0 |
| REF+news | 62 | 0.758 | 0.693 | 0.804 | 0.860 | 0.831 | 0.674 | 0.199 | 37/9/6/10 | R3, R5, R7 | +0.015 (0.964) | -0.140 (0.000) | 0 |  |  |
| I1+news | 62 | 0.726 | 0.655 | 0.783 | 0.837 | 0.809 | 0.654 | 0.206 | 36/10/7/9 | R2, R3, R5, R7 | +0.022 (0.937) | -0.133 (0.001) | 0 |  |  |
| I2+news | 62 | 0.726 | 0.567 | 0.724 | 0.977 | 0.832 | 0.712 | 0.188 | 42/16/1/3 | R2, R3, R7 | +0.004 (0.616) | -0.151 (0.001) | 0 |  | 0 |
| I3+news | 62 | 0.661 | 0.491 | 0.690 | 0.930 | 0.792 | 0.656 | 0.203 | 40/18/3/1 | R2, R3, R4, R5, R7 | +0.019 (0.929) | -0.135 (0.001) | 0 | 0 |  |
| ALL+news | 62 | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | 0.599 | 0.218 | 43/19/0/0 | R2, R3, R5, R7 | +0.035 (0.930) | -0.120 (0.012) | 0 | 0 | 0 |
| PERSIST | 62 | 0.661 | 0.594 | 0.750 | 0.767 | 0.759 | 0.594 | 0.339 | 33/11/10/8 | R2, R3, R4, R5, R7 | +0.155 (1.000) | +0.000 (1.000) | 0 |  |  |
| LOGIT | 62 | 0.661 | 0.624 | 0.775 | 0.721 | 0.747 | 0.670 | 0.234 | 31/9/12/10 | R2, R3, R4, R5, R7 | +0.050 (0.921) | -0.105 (0.034) | 0 |  |  |
| PSA-only | 62 | 0.677 | 0.576 | 0.735 | 0.837 | 0.783 | 0.579 | 0.239 | 36/13/7/6 | R2, R3, R5, R7 | +0.055 (0.960) | -0.100 (0.036) | 0 |  |  |
| NLP-only | 19 | 0.421 | 0.482 | 0.600 | 0.250 | 0.353 | 0.488 | 0.434 | 3/2/9/5 | R1, R2, R3, R4, R5, R6, R7 | +0.227 (0.997) | +0.013 (0.526) | 13 |  |  |
| ALWAYS-HIGH | 62 | 0.694 | 0.500 | 0.694 | 1.000 | 0.819 | – | 0.306 | 43/19/0/0 | R2, R3, R5, R7 | +0.123 (0.992) | -0.032 (0.366) |  |  |  |
| ALWAYS-LOW | 62 | 0.306 | 0.500 | – | 0.000 | 0.000 | – | 0.694 | 0/0/43/19 | R2, R3, R4, R5, R6, R7 | +0.510 (1.000) | +0.355 (1.000) |  |  |  |

Rule values for arms:

- REF: R1 PASS 62 q, 62 rows; R2 PASS 0.7903; R3 PASS 0.7166; R4 PASS 0.7903 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1549, p 0.000', 'CLIM': 'diff -0.0385, p 0.070'}; R6 PASS P 0.812, R 0.907; R7 FAIL thirds [0.952, 0.571, 0.85] (sizes [21, 21, 20]), LOQO min 0.787; other split [0.95, 0.571, 0.857] (sizes [20, 21, 21])
- I1: R1 PASS 62 q, 62 rows; R2 FAIL 0.7419; R3 FAIL 0.6671; R4 PASS 0.7419 vs 0.3065 / 0.6613; R5 FAIL {'PERSIST-SI': 'diff -0.1404, p 0.001', 'CLIM': 'diff -0.0240, p 0.159'}; R6 PASS P 0.787, R 0.860; R7 FAIL thirds [0.952, 0.429, 0.85] (sizes [21, 21, 20]), LOQO min 0.738; other split [0.95, 0.429, 0.857] (sizes [20, 21, 21])
- I2: R1 PASS 62 q, 62 rows; R2 FAIL 0.7419; R3 FAIL 0.5789; R4 PASS 0.7419 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1509, p 0.001', 'CLIM': 'diff -0.0345, p 0.016'}; R6 PASS P 0.729, R 1.000; R7 FAIL thirds [0.952, 0.524, 0.75] (sizes [21, 21, 20]), LOQO min 0.738; other split [0.95, 0.524, 0.762] (sizes [20, 21, 21])
- I3: R1 PASS 62 q, 62 rows; R2 FAIL 0.6774; R3 FAIL 0.4884; R4 PASS 0.6774 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1418, p 0.001', 'CLIM': 'diff -0.0254, p 0.078'}; R6 PASS P 0.689, R 0.977; R7 FAIL thirds [0.952, 0.429, 0.65] (sizes [21, 21, 20]), LOQO min 0.672; other split [0.95, 0.429, 0.667] (sizes [20, 21, 21])
- ALL: R1 PASS 62 q, 62 rows; R2 FAIL 0.6935; R3 FAIL 0.5; R4 PASS 0.6935 vs 0.3065 / 0.6613; R5 FAIL {'PERSIST-SI': 'diff -0.1232, p 0.011', 'CLIM': 'diff -0.0068, p 0.323'}; R6 PASS P 0.694, R 1.000; R7 FAIL thirds [0.952, 0.476, 0.65] (sizes [21, 21, 20]), LOQO min 0.689; other split [0.95, 0.476, 0.667] (sizes [20, 21, 21])
- REF+news: R1 PASS 62 q, 62 rows; R2 PASS 0.7581; R3 FAIL 0.6934; R4 PASS 0.7581 vs 0.3065 / 0.6613; R5 FAIL {'PERSIST-SI': 'diff -0.1399, p 0.000', 'CLIM': 'diff -0.0234, p 0.208'}; R6 PASS P 0.804, R 0.860; R7 FAIL thirds [0.952, 0.571, 0.75] (sizes [21, 21, 20]), LOQO min 0.754; other split [0.95, 0.571, 0.762] (sizes [20, 21, 21])
- I1+news: R1 PASS 62 q, 62 rows; R2 FAIL 0.7258; R3 FAIL 0.6554; R4 PASS 0.7258 vs 0.3065 / 0.6613; R5 FAIL {'PERSIST-SI': 'diff -0.1325, p 0.001', 'CLIM': 'diff -0.0161, p 0.259'}; R6 PASS P 0.783, R 0.837; R7 FAIL thirds [0.952, 0.429, 0.8] (sizes [21, 21, 20]), LOQO min 0.721; other split [0.95, 0.429, 0.81] (sizes [20, 21, 21])
- I2+news: R1 PASS 62 q, 62 rows; R2 FAIL 0.7258; R3 FAIL 0.5673; R4 PASS 0.7258 vs 0.3065 / 0.6613; R5 PASS {'PERSIST-SI': 'diff -0.1507, p 0.001', 'CLIM': 'diff -0.0343, p 0.018'}; R6 PASS P 0.724, R 0.977; R7 FAIL thirds [0.952, 0.524, 0.7] (sizes [21, 21, 20]), LOQO min 0.721; other split [0.95, 0.524, 0.714] (sizes [20, 21, 21])
- I3+news: R1 PASS 62 q, 62 rows; R2 FAIL 0.6613; R3 FAIL 0.4914; R4 FAIL 0.6613 vs 0.3065 / 0.6613; R5 FAIL {'PERSIST-SI': 'diff -0.1355, p 0.001', 'CLIM': 'diff -0.0190, p 0.140'}; R6 PASS P 0.690, R 0.930; R7 FAIL thirds [0.952, 0.429, 0.6] (sizes [21, 21, 20]), LOQO min 0.656; other split [0.95, 0.429, 0.619] (sizes [20, 21, 21])
- ALL+news: R1 PASS 62 q, 62 rows; R2 FAIL 0.6935; R3 FAIL 0.5; R4 PASS 0.6935 vs 0.3065 / 0.6613; R5 FAIL {'PERSIST-SI': 'diff -0.1202, p 0.012', 'CLIM': 'diff -0.0038, p 0.393'}; R6 PASS P 0.694, R 1.000; R7 FAIL thirds [0.952, 0.476, 0.65] (sizes [21, 21, 20]), LOQO min 0.689; other split [0.95, 0.476, 0.667] (sizes [20, 21, 21])

### L2 dev_2010_2022 2010-Q1..2022-Q4, 48 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 48 | 0.750 | 0.193 | False | R3, R5 |
| I1 | 48 | 0.688 | 0.221 | False | R2, R3, R5, R7 |
| I2 | 48 | 0.729 | 0.194 | False | R2, R3, R7 |
| I3 | 48 | 0.646 | 0.207 | False | R2, R3, R4, R5, R7 |
| ALL | 48 | 0.667 | 0.229 | False | R2, R3, R5, R7 |
| REF+news | 48 | 0.750 | 0.193 | False | R3, R5 |
| I1+news | 48 | 0.688 | 0.221 | False | R2, R3, R5, R7 |
| I2+news | 48 | 0.729 | 0.194 | False | R2, R3, R7 |
| I3+news | 48 | 0.646 | 0.207 | False | R2, R3, R4, R5, R7 |
| ALL+news | 48 | 0.667 | 0.229 | False | R2, R3, R5, R7 |
| PERSIST | 48 | 0.646 | 0.354 | False | R2, R3, R4, R5, R7 |
| LOGIT | 48 | 0.646 | 0.251 | False | R2, R3, R4, R5, R7 |
| PSA-only | 48 | 0.708 | 0.232 | False | R2, R3, R5, R7 |
| NLP-only | 5 | 0.400 | 0.376 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 48 | 0.667 | 0.333 | False | R2, R3, R5, R7 |
| ALWAYS-LOW | 48 | 0.333 | 0.667 | False | R2, R3, R4, R5, R6, R7 |

### L2 block_2023_2026 2023-Q1..2026-Q3, 14 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 14 | 0.929 | 0.151 | False | R1, R5 |
| I1 | 14 | 0.929 | 0.121 | False | R1 |
| I2 | 14 | 0.786 | 0.168 | False | R1, R3, R5, R7 |
| I3 | 14 | 0.786 | 0.162 | False | R1, R3, R5, R7 |
| ALL | 14 | 0.786 | 0.168 | False | R1, R3, R5, R7 |
| REF+news | 14 | 0.786 | 0.217 | False | R1, R5 |
| I1+news | 14 | 0.857 | 0.156 | False | R1, R5 |
| I2+news | 14 | 0.714 | 0.169 | False | R1, R2, R3, R4, R5, R7 |
| I3+news | 14 | 0.714 | 0.190 | False | R1, R2, R3, R4, R5, R7 |
| ALL+news | 14 | 0.786 | 0.182 | False | R1, R3, R5, R7 |
| PERSIST | 14 | 0.714 | 0.286 | False | R1, R2, R3, R4, R5, R7 |
| LOGIT | 14 | 0.714 | 0.177 | False | R1, R2, R4, R5, R7 |
| PSA-only | 14 | 0.571 | 0.261 | False | R1, R2, R4, R5, R6, R7 |
| NLP-only | 14 | 0.429 | 0.455 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 14 | 0.786 | 0.214 | False | R1, R3, R5, R7 |
| ALWAYS-LOW | 14 | 0.214 | 0.786 | False | R1, R2, R3, R4, R5, R6, R7 |

### L2 news_era 2021-Q3..2026-Q3, 19 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 19 | 0.842 | 0.207 | False | R1, R5 |
| I1 | 19 | 0.842 | 0.180 | False | R1 |
| I2 | 19 | 0.737 | 0.217 | False | R1, R2, R3, R5, R7 |
| I3 | 19 | 0.632 | 0.224 | False | R1, R2, R3, R5, R7 |
| ALL | 19 | 0.632 | 0.238 | False | R1, R2, R3, R5, R7 |
| REF+news | 19 | 0.737 | 0.256 | False | R1, R2, R5, R7 |
| I1+news | 19 | 0.789 | 0.206 | False | R1, R5 |
| I2+news | 19 | 0.684 | 0.218 | False | R1, R2, R3, R5, R7 |
| I3+news | 19 | 0.579 | 0.244 | False | R1, R2, R3, R4, R5, R7 |
| ALL+news | 19 | 0.632 | 0.248 | False | R1, R2, R3, R5, R7 |
| PERSIST | 19 | 0.579 | 0.421 | False | R1, R2, R3, R4, R5, R7 |
| LOGIT | 19 | 0.737 | 0.177 | False | R1, R2, R5, R7 |
| PSA-only | 19 | 0.526 | 0.327 | False | R1, R2, R3, R4, R5, R6, R7 |
| NLP-only | 19 | 0.421 | 0.434 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 19 | 0.632 | 0.368 | False | R1, R2, R3, R5, R7 |
| ALWAYS-LOW | 19 | 0.368 | 0.632 | False | R1, R2, R3, R4, R5, R6, R7 |

### L2 S1_no_phone_2020 2010-Q1..2026-Q3, 60 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 60 | 0.817 | 0.174 | True | none |
| I1 | 60 | 0.767 | 0.193 | False | R3, R7 |
| I2 | 60 | 0.733 | 0.188 | False | R2, R3, R7 |
| I3 | 60 | 0.683 | 0.195 | False | R2, R3, R4, R7 |
| ALL | 60 | 0.683 | 0.219 | False | R2, R3, R4, R5, R7 |
| REF+news | 60 | 0.783 | 0.190 | True | none |
| I1+news | 60 | 0.750 | 0.201 | False | R3, R5, R7 |
| I2+news | 60 | 0.717 | 0.188 | False | R2, R3, R7 |
| I3+news | 60 | 0.667 | 0.202 | False | R2, R3, R4, R7 |
| ALL+news | 60 | 0.683 | 0.223 | False | R2, R3, R4, R5, R7 |
| PERSIST | 60 | 0.683 | 0.317 | False | R2, R3, R4, R5, R7 |
| LOGIT | 60 | 0.683 | 0.225 | False | R2, R3, R4, R5, R7 |
| PSA-only | 60 | 0.667 | 0.246 | False | R2, R3, R4, R5, R7 |
| NLP-only | 19 | 0.421 | 0.434 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 60 | 0.683 | 0.317 | False | R2, R3, R4, R5, R7 |
| ALWAYS-LOW | 60 | 0.317 | 0.683 | False | R2, R3, R4, R5, R6, R7 |

### L2 S2_no_adults_2025Q2plus 2010-Q1..2024-Q4, 56 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 56 | 0.768 | 0.190 | True | none |
| I1 | 56 | 0.714 | 0.212 | False | R2, R3, R5, R7 |
| I2 | 56 | 0.714 | 0.199 | False | R2, R3, R7 |
| I3 | 56 | 0.643 | 0.207 | False | R2, R3, R7 |
| ALL | 56 | 0.661 | 0.230 | False | R2, R3, R5, R7 |
| REF+news | 56 | 0.732 | 0.208 | False | R2, R3, R5 |
| I1+news | 56 | 0.696 | 0.220 | False | R2, R3, R5, R7 |
| I2+news | 56 | 0.696 | 0.202 | False | R2, R3, R7 |
| I3+news | 56 | 0.625 | 0.214 | False | R2, R3, R4, R5, R7 |
| ALL+news | 56 | 0.661 | 0.234 | False | R2, R3, R5, R7 |
| PERSIST | 56 | 0.625 | 0.375 | False | R2, R3, R4, R5, R7 |
| LOGIT | 56 | 0.643 | 0.252 | False | R2, R3, R5, R7 |
| PSA-only | 56 | 0.679 | 0.247 | False | R2, R3, R5, R7 |
| NLP-only | 13 | 0.385 | 0.414 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 56 | 0.661 | 0.339 | False | R2, R3, R5, R7 |
| ALWAYS-LOW | 56 | 0.339 | 0.661 | False | R2, R3, R4, R5, R6, R7 |

### L2 S3_both 2010-Q1..2024-Q4, 54 q

| Model | q | Acc | Brier | all R1-R7 | fails |
|---|---|---|---|---|---|
| REF | 54 | 0.796 | 0.179 | True | none |
| I1 | 54 | 0.741 | 0.206 | False | R2, R3, R5, R7 |
| I2 | 54 | 0.704 | 0.199 | False | R2, R3, R7 |
| I3 | 54 | 0.648 | 0.205 | False | R2, R3, R4, R7 |
| ALL | 54 | 0.648 | 0.235 | False | R2, R3, R4, R5, R7 |
| REF+news | 54 | 0.759 | 0.198 | False | R5 |
| I1+news | 54 | 0.722 | 0.215 | False | R2, R3, R5, R7 |
| I2+news | 54 | 0.685 | 0.202 | False | R2, R3, R7 |
| I3+news | 54 | 0.630 | 0.213 | False | R2, R3, R4, R5, R7 |
| ALL+news | 54 | 0.648 | 0.239 | False | R2, R3, R4, R5, R7 |
| PERSIST | 54 | 0.648 | 0.352 | False | R2, R3, R4, R5, R7 |
| LOGIT | 54 | 0.667 | 0.243 | False | R2, R3, R5, R7 |
| PSA-only | 54 | 0.667 | 0.255 | False | R2, R3, R5, R7 |
| NLP-only | 13 | 0.385 | 0.414 | False | R1, R2, R3, R4, R5, R6, R7 |
| ALWAYS-HIGH | 54 | 0.648 | 0.352 | False | R2, R3, R4, R5, R7 |
| ALWAYS-LOW | 54 | 0.352 | 0.648 | False | R2, R3, R4, R5, R6, R7 |

### L2 selection: {'passing': [], 'carried_forward': 'REF', 'rule': 'lowest Brier among arms passing R1-R7, else REF'}

| Comparator | q | Brier proposed | Brier comparator | diff | p | Holm p |
|---|---|---|---|---|---|---|
| PERSIST | 62 | 0.184 | 0.339 | -0.155 | 0.000 | 0.001 |
| PSA-only | 62 | 0.184 | 0.239 | -0.055 | 0.040 | 0.080 |
| NLP-only | 19 | 0.207 | 0.434 | -0.227 | 0.003 | 0.014 |
| LOGIT | 62 | 0.184 | 0.234 | -0.050 | 0.079 | 0.080 |
| ALWAYS-HIGH | 62 | 0.184 | 0.306 | -0.123 | 0.008 | 0.023 |

### L2 news ablation (with news minus without)

| Arm | full diff (p) | news-era q | news-era diff (p) |
|---|---|---|---|
| REF | +0.0150 (0.964) | 19 | +0.0491 (0.971) |
| I1 | +0.0079 (0.973) | 19 | +0.0258 (0.973) |
| I2 | +0.0002 (0.520) | 19 | +0.0007 (0.532) |
| I3 | +0.0063 (0.957) | 19 | +0.0207 (0.963) |
| ALL | +0.0030 (0.985) | 19 | +0.0099 (0.987) |

### L2 SHAP group shares (%)

| Arm | rows | H1 Hunger (SWS) | A1-A2 Food and headline prices | A3 Rice | C1 Climate (ONI) | C2 Typhoons | C3 Crops | C4 Fisheries | World prices | N1 News | Area indicator |
|---|---|---|---|---|---|---|---|---|---|---|---|
| REF (SHAP of REF) | 62 | 64.7 | 6.3 | 2.7 | 2.1 | 0.1 | 0.9 | 0.9 | 22.4 |  |  |
| I1 (SHAP of I1) | 62 | 52.2 | 5.2 | 1.3 | 4.1 | 0.0 | 0.6 | 2.1 | 32.8 |  | 1.7 |
| I2 (SHAP of I2) | 62 | 68.2 | 8.5 | 1.0 | 7.6 | 0.0 | 0.5 | 0.3 | 13.9 |  |  |
| I3 (SHAP of REF) | 62 | 64.7 | 6.3 | 2.7 | 2.1 | 0.1 | 0.9 | 0.9 | 22.4 |  |  |
| ALL (SHAP of I12) | 62 | 52.5 | 10.2 | 2.9 | 4.0 | 0.0 | 0.2 | 2.0 | 25.2 |  | 3.1 |
| REF+news (SHAP of REF+news) | 62 | 64.2 | 6.0 | 2.4 | 1.9 | 0.1 | 0.8 | 0.4 | 21.4 | 2.7 |  |
| I1+news (SHAP of I1+news) | 62 | 52.6 | 5.1 | 1.3 | 4.2 | 0.0 | 0.5 | 1.2 | 32.6 | 0.8 | 1.6 |
| I2+news (SHAP of I2+news) | 62 | 66.1 | 8.4 | 0.8 | 7.5 | 0.0 | 0.7 | 0.1 | 13.3 | 3.1 |  |
| I3+news (SHAP of REF+news) | 62 | 64.2 | 6.0 | 2.4 | 1.9 | 0.1 | 0.8 | 0.4 | 21.4 | 2.7 |  |
| ALL+news (SHAP of I12+news) | 62 | 52.2 | 10.0 | 2.8 | 3.8 | 0.0 | 0.2 | 1.3 | 25.0 | 1.9 | 2.9 |
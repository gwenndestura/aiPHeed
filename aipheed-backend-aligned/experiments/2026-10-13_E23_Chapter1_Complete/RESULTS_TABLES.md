# Results tables (generated from runs 20261013T152113Z and 20261013T152838Z_E23B)

## E23 — PRIMARY target (training-window median threshold)

Evaluable leads: none · maximum reliable lead: none

**Lead 1** — 8 origins (2023-Q4…2026-Q1), test HIGH 37 / LOW 3, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.825 | 0.969 | 0.838 | 0.899 | 0.703 | 0.142 | 31/1/6/2 |
| B1_naive_persistence | 0.875 | 0.971 | 0.892 | 0.930 | 0.779 | 0.125 | 33/1/4/2 |
| B2_lr_combined | 0.650 | 0.960 | 0.649 | 0.774 | 0.622 | 0.275 | 24/1/13/2 |
| B3_lr_gov_only | 0.650 | 0.960 | 0.649 | 0.774 | 0.640 | 0.286 | 24/1/13/2 |
| B4_lr_nlp_only | 0.600 | 1.000 | 0.568 | 0.724 | 0.802 | 0.231 | 21/0/16/3 |
| B5_lgbm_gov_only | 0.850 | 0.970 | 0.865 | 0.914 | 0.649 | 0.131 | 32/1/5/2 |
| B6_lgbm_nlp_only | 0.625 | 1.000 | 0.595 | 0.746 | 0.730 | 0.249 | 22/0/15/3 |
| S_lr_psa_only | 0.750 | 0.966 | 0.757 | 0.848 | 0.685 | 0.187 | 28/1/9/2 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | 0.0173 | 0.730 | 1.000 | 3/5 |
| B2_lr_combined | — | — | — | -0.1330 | 0.117 | 0.438 | 5/3 |
| B3_lr_gov_only | — | — | — | -0.1438 | 0.109 | 0.438 | 6/2 |
| B4_lr_nlp_only | — | — | — | -0.0889 | 0.062 | 0.312 | 5/3 |
| B5_lgbm_gov_only | — | — | — | 0.0112 | 0.711 | 1.000 | 3/5 |
| B6_lgbm_nlp_only | — | — | — | -0.1065 | 0.051 | 0.305 | 6/2 |
| S_lr_psa_only | — | — | — | -0.0444 | 0.176 | — | 7/1 |

**Lead 2** — 7 origins (2024-Q2…2026-Q2), test HIGH 33 / LOW 2, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.886 | 0.939 | 0.939 | 0.939 | 0.106 | 0.113 | 31/2/2/0 |
| B1_naive_persistence | 0.829 | 0.935 | 0.879 | 0.906 | 0.439 | 0.171 | 29/2/4/0 |
| B2_lr_combined | 0.714 | 0.926 | 0.758 | 0.833 | 0.364 | 0.224 | 25/2/8/0 |
| B3_lr_gov_only | 0.743 | 0.929 | 0.788 | 0.852 | 0.288 | 0.169 | 26/2/7/0 |
| B4_lr_nlp_only | 0.629 | 1.000 | 0.606 | 0.755 | 0.833 | 0.247 | 20/0/13/2 |
| B5_lgbm_gov_only | 0.800 | 0.933 | 0.848 | 0.889 | 0.121 | 0.138 | 28/2/5/0 |
| B6_lgbm_nlp_only | 0.543 | 0.947 | 0.545 | 0.692 | 0.742 | 0.278 | 18/1/15/1 |
| S_lr_psa_only | 0.714 | 0.926 | 0.758 | 0.833 | 0.273 | 0.219 | 25/2/8/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0586 | 0.117 | 0.312 | 4/3 |
| B2_lr_combined | — | — | — | -0.1109 | 0.078 | 0.312 | 5/2 |
| B3_lr_gov_only | — | — | — | -0.0565 | 0.203 | 0.312 | 4/3 |
| B4_lr_nlp_only | — | — | — | -0.1341 | 0.023 | 0.117 | 6/1 |
| B5_lgbm_gov_only | — | — | — | -0.0247 | 0.078 | 0.312 | 4/3 |
| B6_lgbm_nlp_only | — | — | — | -0.1651 | 0.008 | 0.047 | 7/0 |
| S_lr_psa_only | — | — | — | -0.1059 | 0.008 | — | 7/0 |

**Lead 3** — 5 origins (2024-Q4…2026-Q2), test HIGH 23 / LOW 2, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.800 | 0.909 | 0.870 | 0.889 | 0.500 | 0.136 | 20/2/3/0 |
| B1_naive_persistence | 0.840 | 0.913 | 0.913 | 0.913 | 0.457 | 0.160 | 21/2/2/0 |
| B2_lr_combined | 0.840 | 0.913 | 0.913 | 0.913 | 0.370 | 0.134 | 21/2/2/0 |
| B3_lr_gov_only | 0.840 | 0.913 | 0.913 | 0.913 | 0.283 | 0.141 | 21/2/2/0 |
| B4_lr_nlp_only | 0.800 | 1.000 | 0.783 | 0.878 | 0.891 | 0.208 | 18/0/5/2 |
| B5_lgbm_gov_only | 0.840 | 0.913 | 0.913 | 0.913 | 0.489 | 0.126 | 21/2/2/0 |
| B6_lgbm_nlp_only | 0.600 | 1.000 | 0.565 | 0.722 | 0.652 | 0.262 | 13/0/10/2 |
| S_lr_psa_only | 0.760 | 0.905 | 0.826 | 0.864 | 0.239 | 0.214 | 19/2/4/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0237 | 0.312 | 1.000 | 3/2 |
| B2_lr_combined | — | — | — | 0.0020 | 0.562 | 1.000 | 3/2 |
| B3_lr_gov_only | — | — | — | -0.0051 | 0.469 | 1.000 | 3/2 |
| B4_lr_nlp_only | — | — | — | -0.0715 | 0.156 | 0.781 | 4/1 |
| B5_lgbm_gov_only | — | — | — | 0.0108 | 0.562 | 1.000 | 3/2 |
| B6_lgbm_nlp_only | — | — | — | -0.1253 | 0.031 | 0.188 | 5/0 |
| S_lr_psa_only | — | — | — | -0.0777 | 0.125 | — | 4/1 |

**Lead 4** — 3 origins (2025-Q4…2026-Q2), test HIGH 13 / LOW 2, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.867 | 0.867 | 1.000 | 0.929 | 0.827 | 0.110 | 13/2/0/0 |
| B1_naive_persistence | 0.867 | 0.867 | 1.000 | 0.929 | 0.500 | 0.133 | 13/2/0/0 |
| B2_lr_combined | 0.867 | 0.867 | 1.000 | 0.929 | 0.462 | 0.136 | 13/2/0/0 |
| B3_lr_gov_only | 0.867 | 0.867 | 1.000 | 0.929 | 0.500 | 0.133 | 13/2/0/0 |
| B4_lr_nlp_only | 0.867 | 0.867 | 1.000 | 0.929 | 0.615 | 0.192 | 13/2/0/0 |
| B5_lgbm_gov_only | 0.867 | 0.867 | 1.000 | 0.929 | 0.250 | 0.131 | 13/2/0/0 |
| B6_lgbm_nlp_only | 0.600 | 1.000 | 0.538 | 0.700 | 0.962 | 0.219 | 7/0/6/2 |
| S_lr_psa_only | 0.867 | 0.867 | 1.000 | 0.929 | 0.385 | 0.137 | 13/2/0/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0237 | 0.250 | 1.000 | 2/1 |
| B2_lr_combined | — | — | — | -0.0262 | 0.250 | 1.000 | 2/1 |
| B3_lr_gov_only | — | — | — | -0.0234 | 0.250 | 1.000 | 2/1 |
| B4_lr_nlp_only | — | — | — | -0.0825 | 0.125 | 0.750 | 3/0 |
| B5_lgbm_gov_only | — | — | — | -0.0215 | 0.125 | 0.750 | 3/0 |
| B6_lgbm_nlp_only | — | — | — | -0.1098 | 0.250 | 1.000 | 2/1 |
| S_lr_psa_only | — | — | — | -0.0276 | 0.250 | — | 2/1 |

**Lead 5** — 3 origins (2025-Q4…2026-Q2), test HIGH 14 / LOW 1, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.933 | 0.933 | 1.000 | 0.966 | 0.143 | 0.099 | 14/1/0/0 |
| B1_naive_persistence | 0.933 | 0.933 | 1.000 | 0.966 | 0.500 | 0.067 | 14/1/0/0 |
| B2_lr_combined | 0.800 | 0.923 | 0.857 | 0.889 | 0.071 | 0.122 | 12/1/2/0 |
| B3_lr_gov_only | 0.933 | 0.933 | 1.000 | 0.966 | 0.071 | 0.072 | 14/1/0/0 |
| B4_lr_nlp_only | 0.867 | 0.929 | 0.929 | 0.929 | 0.929 | 0.168 | 13/1/1/0 |
| B5_lgbm_gov_only | 0.933 | 0.933 | 1.000 | 0.966 | 0.536 | 0.067 | 14/1/0/0 |
| B6_lgbm_nlp_only | 0.600 | 1.000 | 0.571 | 0.727 | 0.571 | 0.213 | 8/0/6/1 |
| S_lr_psa_only | 0.933 | 0.933 | 1.000 | 0.966 | 0.286 | 0.077 | 14/1/0/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | 0.0321 | 0.750 | 1.000 | 1/2 |
| B2_lr_combined | — | — | — | -0.0233 | 0.250 | 1.000 | 2/1 |
| B3_lr_gov_only | — | — | — | 0.0264 | 0.750 | 1.000 | 1/2 |
| B4_lr_nlp_only | — | — | — | -0.0688 | 0.125 | 0.750 | 3/0 |
| B5_lgbm_gov_only | — | — | — | 0.0317 | 0.875 | 1.000 | 1/2 |
| B6_lgbm_nlp_only | — | — | — | -0.1147 | 0.125 | 0.750 | 3/0 |
| S_lr_psa_only | — | — | — | 0.0217 | 0.750 | — | 1/2 |

**Lead 6** — 2 origins (2026-Q1…2026-Q2), test HIGH 9 / LOW 1, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.900 | 0.900 | 1.000 | 0.947 | 0.611 | 0.092 | 9/1/0/0 |
| B1_naive_persistence | 0.900 | 0.900 | 1.000 | 0.947 | 0.500 | 0.100 | 9/1/0/0 |
| B2_lr_combined | 0.800 | 0.889 | 0.889 | 0.889 | 0.556 | 0.124 | 8/1/1/0 |
| B3_lr_gov_only | 0.900 | 0.900 | 1.000 | 0.947 | 0.556 | 0.102 | 9/1/0/0 |
| B4_lr_nlp_only | 0.900 | 0.900 | 1.000 | 0.947 | 0.667 | 0.132 | 9/1/0/0 |
| B5_lgbm_gov_only | 0.900 | 0.900 | 1.000 | 0.947 | 0.667 | 0.098 | 9/1/0/0 |
| B6_lgbm_nlp_only | 0.700 | 1.000 | 0.667 | 0.800 | 0.722 | 0.189 | 6/0/3/1 |
| S_lr_psa_only | 0.900 | 0.900 | 1.000 | 0.947 | 0.556 | 0.100 | 9/1/0/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0075 | 0.500 | 1.000 | 1/1 |
| B2_lr_combined | — | — | — | -0.0316 | 0.250 | 1.000 | 2/0 |
| B3_lr_gov_only | — | — | — | -0.0090 | 0.500 | 1.000 | 1/1 |
| B4_lr_nlp_only | — | — | — | -0.0395 | 0.500 | 1.000 | 1/1 |
| B5_lgbm_gov_only | — | — | — | -0.0055 | 0.500 | 1.000 | 1/1 |
| B6_lgbm_nlp_only | — | — | — | -0.0965 | 0.250 | 1.000 | 2/0 |
| S_lr_psa_only | — | — | — | -0.0075 | 0.500 | — | 1/1 |

**Lead 7:** no origin with ≥ 8 published training quarters.

**Lead 8:** no origin with ≥ 8 published training quarters.

**Hypothesis decisions:** H1 not testable; H2 not testable; H3 not testable; H4 awaiting participant data; H5 awaiting participant data

## E23 — SENSITIVITY target (fixed 14.6; carries full-period information; never decisive)

Evaluable leads: [1] · maximum reliable lead: none

**Lead 1** — 8 origins (2023-Q4…2026-Q1), test HIGH 35 / LOW 5, evaluable: yes

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.750 | 0.931 | 0.771 | 0.844 | 0.760 | 0.214 | 27/2/8/3 |
| B1_naive_persistence | 0.725 | 0.929 | 0.743 | 0.825 | 0.671 | 0.275 | 26/2/9/3 |
| B2_lr_combined | 0.675 | 0.958 | 0.657 | 0.780 | 0.737 | 0.251 | 23/1/12/4 |
| B3_lr_gov_only | 0.650 | 0.957 | 0.629 | 0.759 | 0.754 | 0.251 | 22/1/13/4 |
| B4_lr_nlp_only | 0.250 | 1.000 | 0.143 | 0.250 | 0.640 | 0.420 | 5/0/30/5 |
| B5_lgbm_gov_only | 0.775 | 0.933 | 0.800 | 0.862 | 0.743 | 0.219 | 28/2/7/3 |
| B6_lgbm_nlp_only | 0.600 | 0.952 | 0.571 | 0.714 | 0.743 | 0.305 | 20/1/15/4 |
| S_lr_psa_only | 0.725 | 0.929 | 0.743 | 0.825 | 0.680 | 0.202 | 26/2/9/3 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | 0.089 | 0.332 | 1.000 | -0.0605 | 0.094 | 0.469 | 5/3 |
| B2_lr_combined | 0.023 | 0.348 | 1.000 | -0.0362 | 0.355 | 0.902 | 5/3 |
| B3_lr_gov_only | 0.006 | 0.473 | 1.000 | -0.0368 | 0.301 | 0.902 | 5/3 |
| B4_lr_nlp_only | 0.120 | 0.211 | 1.000 | -0.2057 | 0.023 | 0.141 | 6/2 |
| B5_lgbm_gov_only | 0.017 | 0.375 | 1.000 | -0.0045 | 0.371 | 0.902 | 3/5 |
| B6_lgbm_nlp_only | 0.017 | 0.488 | 1.000 | -0.0909 | 0.129 | 0.516 | 6/2 |
| S_lr_psa_only | 0.080 | 0.250 | — | 0.0128 | 0.605 | — | 5/3 |

Proposed AUC origin-cluster bootstrap 95% CI: 0.405–0.974

**Lead 2** — 7 origins (2024-Q2…2026-Q2), test HIGH 32 / LOW 3, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.800 | 0.931 | 0.844 | 0.885 | 0.354 | 0.198 | 27/2/5/1 |
| B1_naive_persistence | 0.771 | 0.929 | 0.812 | 0.867 | 0.573 | 0.229 | 26/2/6/1 |
| B2_lr_combined | 0.714 | 0.893 | 0.781 | 0.833 | 0.521 | 0.177 | 25/3/7/0 |
| B3_lr_gov_only | 0.686 | 0.889 | 0.750 | 0.814 | 0.438 | 0.181 | 24/3/8/0 |
| B4_lr_nlp_only | 0.286 | 1.000 | 0.219 | 0.359 | 0.562 | 0.401 | 7/0/25/3 |
| B5_lgbm_gov_only | 0.800 | 0.931 | 0.844 | 0.885 | 0.385 | 0.154 | 27/2/5/1 |
| B6_lgbm_nlp_only | 0.543 | 0.944 | 0.531 | 0.680 | 0.750 | 0.320 | 17/1/15/2 |
| S_lr_psa_only | 0.600 | 0.875 | 0.656 | 0.750 | 0.333 | 0.290 | 21/3/11/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0301 | 0.242 | 0.969 | 3/4 |
| B2_lr_combined | — | — | — | 0.0213 | 0.633 | 1.000 | 3/4 |
| B3_lr_gov_only | — | — | — | 0.0174 | 0.648 | 1.000 | 3/4 |
| B4_lr_nlp_only | — | — | — | -0.2028 | 0.008 | 0.047 | 7/0 |
| B5_lgbm_gov_only | — | — | — | 0.0443 | 0.938 | 1.000 | 2/5 |
| B6_lgbm_nlp_only | — | — | — | -0.1220 | 0.109 | 0.547 | 5/2 |
| S_lr_psa_only | — | — | — | -0.0912 | 0.102 | — | 5/2 |

**Lead 3** — 5 origins (2024-Q4…2026-Q2), test HIGH 23 / LOW 2, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.840 | 0.913 | 0.913 | 0.913 | 0.272 | 0.148 | 21/2/2/0 |
| B1_naive_persistence | 0.800 | 0.909 | 0.870 | 0.889 | 0.435 | 0.200 | 20/2/3/0 |
| B2_lr_combined | 0.840 | 0.913 | 0.913 | 0.913 | 0.239 | 0.134 | 21/2/2/0 |
| B3_lr_gov_only | 0.880 | 0.917 | 0.957 | 0.936 | 0.196 | 0.128 | 22/2/1/0 |
| B4_lr_nlp_only | 0.560 | 1.000 | 0.522 | 0.686 | 0.717 | 0.306 | 12/0/11/2 |
| B5_lgbm_gov_only | 0.840 | 0.913 | 0.913 | 0.913 | 0.315 | 0.140 | 21/2/2/0 |
| B6_lgbm_nlp_only | 0.600 | 1.000 | 0.565 | 0.722 | 0.804 | 0.282 | 13/0/10/2 |
| S_lr_psa_only | 0.760 | 0.905 | 0.826 | 0.864 | 0.130 | 0.177 | 19/2/4/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0517 | 0.125 | 0.500 | 4/1 |
| B2_lr_combined | — | — | — | 0.0139 | 0.625 | 1.000 | 3/2 |
| B3_lr_gov_only | — | — | — | 0.0205 | 0.625 | 1.000 | 3/2 |
| B4_lr_nlp_only | — | — | — | -0.1582 | 0.062 | 0.375 | 4/1 |
| B5_lgbm_gov_only | — | — | — | 0.0082 | 0.625 | 1.000 | 3/2 |
| B6_lgbm_nlp_only | — | — | — | -0.1333 | 0.062 | 0.375 | 4/1 |
| S_lr_psa_only | — | — | — | -0.0290 | 0.375 | — | 3/2 |

**Lead 4** — 3 origins (2025-Q4…2026-Q2), test HIGH 13 / LOW 2, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.867 | 0.867 | 1.000 | 0.929 | 0.423 | 0.127 | 13/2/0/0 |
| B1_naive_persistence | 0.800 | 0.857 | 0.923 | 0.889 | 0.462 | 0.200 | 12/2/1/0 |
| B2_lr_combined | 0.867 | 0.867 | 1.000 | 0.929 | 0.154 | 0.133 | 13/2/0/0 |
| B3_lr_gov_only | 0.867 | 0.867 | 1.000 | 0.929 | 0.231 | 0.133 | 13/2/0/0 |
| B4_lr_nlp_only | 0.533 | 0.800 | 0.615 | 0.696 | 0.269 | 0.266 | 8/2/5/0 |
| B5_lgbm_gov_only | 0.867 | 0.867 | 1.000 | 0.929 | 0.154 | 0.141 | 13/2/0/0 |
| B6_lgbm_nlp_only | 0.600 | 1.000 | 0.538 | 0.700 | 0.673 | 0.274 | 7/0/6/2 |
| S_lr_psa_only | 0.867 | 0.867 | 1.000 | 0.929 | 0.154 | 0.133 | 13/2/0/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0728 | 0.250 | 0.750 | 2/1 |
| B2_lr_combined | — | — | — | -0.0060 | 0.500 | 1.000 | 1/2 |
| B3_lr_gov_only | — | — | — | -0.0061 | 0.500 | 1.000 | 1/2 |
| B4_lr_nlp_only | — | — | — | -0.1388 | 0.125 | 0.750 | 3/0 |
| B5_lgbm_gov_only | — | — | — | -0.0139 | 0.125 | 0.750 | 3/0 |
| B6_lgbm_nlp_only | — | — | — | -0.1470 | 0.125 | 0.750 | 3/0 |
| S_lr_psa_only | — | — | — | -0.0061 | 0.500 | — | 1/2 |

**Lead 5** — 3 origins (2025-Q4…2026-Q2), test HIGH 13 / LOW 2, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.867 | 0.867 | 1.000 | 0.929 | 0.192 | 0.131 | 13/2/0/0 |
| B1_naive_persistence | 0.800 | 0.857 | 0.923 | 0.889 | 0.462 | 0.200 | 12/2/1/0 |
| B2_lr_combined | 0.867 | 0.867 | 1.000 | 0.929 | 0.038 | 0.134 | 13/2/0/0 |
| B3_lr_gov_only | 0.867 | 0.867 | 1.000 | 0.929 | 0.038 | 0.133 | 13/2/0/0 |
| B4_lr_nlp_only | 0.400 | 0.833 | 0.385 | 0.526 | 0.231 | 0.286 | 5/1/8/1 |
| B5_lgbm_gov_only | 0.867 | 0.867 | 1.000 | 0.929 | 0.365 | 0.127 | 13/2/0/0 |
| B6_lgbm_nlp_only | 0.600 | 1.000 | 0.538 | 0.700 | 0.692 | 0.245 | 7/0/6/2 |
| S_lr_psa_only | 0.867 | 0.867 | 1.000 | 0.929 | 0.154 | 0.133 | 13/2/0/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0686 | 0.125 | 0.750 | 3/0 |
| B2_lr_combined | — | — | — | -0.0021 | 0.500 | 1.000 | 2/1 |
| B3_lr_gov_only | — | — | — | -0.0019 | 0.500 | 1.000 | 2/1 |
| B4_lr_nlp_only | — | — | — | -0.1543 | 0.125 | 0.750 | 3/0 |
| B5_lgbm_gov_only | — | — | — | 0.0049 | 0.625 | 1.000 | 2/1 |
| B6_lgbm_nlp_only | — | — | — | -0.1138 | 0.125 | 0.750 | 3/0 |
| S_lr_psa_only | — | — | — | -0.0020 | 0.500 | — | 2/1 |

**Lead 6** — 2 origins (2026-Q1…2026-Q2), test HIGH 9 / LOW 1, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.900 | 0.900 | 1.000 | 0.947 | 0.389 | 0.111 | 9/1/0/0 |
| B1_naive_persistence | 0.800 | 0.889 | 0.889 | 0.889 | 0.444 | 0.200 | 8/1/1/0 |
| B2_lr_combined | 0.900 | 0.900 | 1.000 | 0.947 | 0.667 | 0.097 | 9/1/0/0 |
| B3_lr_gov_only | 0.900 | 0.900 | 1.000 | 0.947 | 0.667 | 0.100 | 9/1/0/0 |
| B4_lr_nlp_only | 0.600 | 0.857 | 0.667 | 0.750 | 0.444 | 0.228 | 6/1/3/0 |
| B5_lgbm_gov_only | 0.900 | 0.900 | 1.000 | 0.947 | 0.444 | 0.098 | 9/1/0/0 |
| B6_lgbm_nlp_only | 0.700 | 1.000 | 0.667 | 0.800 | 0.944 | 0.222 | 6/0/3/1 |
| S_lr_psa_only | 0.900 | 0.900 | 1.000 | 0.947 | 0.667 | 0.100 | 9/1/0/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0893 | 0.500 | 1.000 | 1/1 |
| B2_lr_combined | — | — | — | 0.0134 | 0.750 | 1.000 | 1/1 |
| B3_lr_gov_only | — | — | — | 0.0107 | 0.750 | 1.000 | 1/1 |
| B4_lr_nlp_only | — | — | — | -0.1175 | 0.500 | 1.000 | 1/1 |
| B5_lgbm_gov_only | — | — | — | 0.0126 | 0.750 | 1.000 | 1/1 |
| B6_lgbm_nlp_only | — | — | — | -0.1109 | 0.250 | 1.000 | 2/0 |
| S_lr_psa_only | — | — | — | 0.0107 | 0.750 | — | 1/1 |

**Lead 7:** no origin with ≥ 8 published training quarters.

**Lead 8:** no origin with ≥ 8 published training quarters.

**Hypothesis decisions:** H1 not rejected; H2 not testable; H3 not rejected; H4 awaiting participant data; H5 awaiting participant data

H1 detail: {"FSSI": {"rank": 4, "top5_pooled": true, "top5_share_of_origins": 0.625, "perm_delta_brier": 0.002003460935428122, "perm_ci_low": -0.005197452822043035}, "cpi_dev": {"rank": 23, "top5_pooled": false, "top5_share_of_origins": 0.0, "perm_delta_brier": -0.00029776635347241343, "perm_ci_low": -0.000784394190945796}}

SHAP top 10 (mean |SHAP|): food_cpi 1.095, commodity_leafy_veg 0.621, commodity_rootcrops 0.437, FSSI 0.183, headline_cpi 0.173, commodity_livestock 0.103, unemployment_rate 0.079, unemployment_rate_accel 0.075, rainfall_anomaly_pct_lag1 0.066, rice_price_regular 0.054

## E23 — PRIMARY target, 2026 targets excluded

Evaluable leads: none · maximum reliable lead: none

**Lead 1** — 7 origins (2023-Q4…2025-Q4), test HIGH 32 / LOW 3, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.800 | 0.963 | 0.812 | 0.881 | 0.708 | 0.155 | 26/1/6/2 |
| B1_naive_persistence | 0.857 | 0.966 | 0.875 | 0.918 | 0.771 | 0.143 | 28/1/4/2 |
| B2_lr_combined | 0.629 | 0.952 | 0.625 | 0.755 | 0.625 | 0.287 | 20/1/12/2 |
| B3_lr_gov_only | 0.657 | 0.955 | 0.656 | 0.778 | 0.635 | 0.303 | 21/1/11/2 |
| B4_lr_nlp_only | 0.600 | 1.000 | 0.562 | 0.720 | 0.802 | 0.234 | 18/0/14/3 |
| B5_lgbm_gov_only | 0.829 | 0.964 | 0.844 | 0.900 | 0.646 | 0.144 | 27/1/5/2 |
| B6_lgbm_nlp_only | 0.629 | 1.000 | 0.594 | 0.745 | 0.729 | 0.245 | 19/0/13/3 |
| S_lr_psa_only | 0.714 | 0.958 | 0.719 | 0.821 | 0.688 | 0.202 | 23/1/9/2 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | 0.0118 | 0.656 | 1.000 | 3/4 |
| B2_lr_combined | — | — | — | -0.1328 | 0.172 | 0.625 | 4/3 |
| B3_lr_gov_only | — | — | — | -0.1479 | 0.156 | 0.625 | 5/2 |
| B4_lr_nlp_only | — | — | — | -0.0792 | 0.109 | 0.609 | 4/3 |
| B5_lgbm_gov_only | — | — | — | 0.0104 | 0.664 | 1.000 | 3/4 |
| B6_lgbm_nlp_only | — | — | — | -0.0902 | 0.102 | 0.609 | 5/2 |
| S_lr_psa_only | — | — | — | -0.0470 | 0.195 | — | 6/1 |

**Lead 2** — 5 origins (2024-Q2…2025-Q4), test HIGH 24 / LOW 1, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.880 | 0.957 | 0.917 | 0.936 | 0.042 | 0.113 | 22/1/2/0 |
| B1_naive_persistence | 0.800 | 0.952 | 0.833 | 0.889 | 0.417 | 0.200 | 20/1/4/0 |
| B2_lr_combined | 0.680 | 0.944 | 0.708 | 0.810 | 0.500 | 0.245 | 17/1/7/0 |
| B3_lr_gov_only | 0.760 | 0.950 | 0.792 | 0.864 | 0.417 | 0.156 | 19/1/5/0 |
| B4_lr_nlp_only | 0.640 | 1.000 | 0.625 | 0.769 | 0.750 | 0.261 | 15/0/9/1 |
| B5_lgbm_gov_only | 0.760 | 0.950 | 0.792 | 0.864 | 0.042 | 0.150 | 19/1/5/0 |
| B6_lgbm_nlp_only | 0.600 | 1.000 | 0.583 | 0.737 | 0.958 | 0.259 | 14/0/10/1 |
| S_lr_psa_only | 0.680 | 0.944 | 0.708 | 0.810 | 0.333 | 0.245 | 17/1/7/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0870 | 0.094 | 0.281 | 4/1 |
| B2_lr_combined | — | — | — | -0.1324 | 0.156 | 0.312 | 4/1 |
| B3_lr_gov_only | — | — | — | -0.0434 | 0.375 | 0.375 | 3/2 |
| B4_lr_nlp_only | — | — | — | -0.1476 | 0.031 | 0.188 | 5/0 |
| B5_lgbm_gov_only | — | — | — | -0.0373 | 0.062 | 0.250 | 4/1 |
| B6_lgbm_nlp_only | — | — | — | -0.1457 | 0.031 | 0.188 | 5/0 |
| S_lr_psa_only | — | — | — | -0.1316 | 0.031 | — | 5/0 |

**Lead 3** — 3 origins (2024-Q4…2025-Q4), test HIGH 14 / LOW 1, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.733 | 0.917 | 0.786 | 0.846 | 0.500 | 0.160 | 11/1/3/0 |
| B1_naive_persistence | 0.800 | 0.923 | 0.857 | 0.889 | 0.429 | 0.200 | 12/1/2/0 |
| B2_lr_combined | 0.800 | 0.923 | 0.857 | 0.889 | 0.214 | 0.157 | 12/1/2/0 |
| B3_lr_gov_only | 0.800 | 0.923 | 0.857 | 0.889 | 0.000 | 0.169 | 12/1/2/0 |
| B4_lr_nlp_only | 0.733 | 1.000 | 0.714 | 0.833 | 0.786 | 0.222 | 10/0/4/1 |
| B5_lgbm_gov_only | 0.800 | 0.923 | 0.857 | 0.889 | 0.536 | 0.140 | 12/1/2/0 |
| B6_lgbm_nlp_only | 0.667 | 1.000 | 0.643 | 0.783 | 0.857 | 0.234 | 9/0/5/1 |
| S_lr_psa_only | 0.667 | 0.909 | 0.714 | 0.800 | 0.071 | 0.290 | 10/1/4/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0402 | 0.375 | 1.000 | 2/1 |
| B2_lr_combined | — | — | — | 0.0026 | 0.625 | 1.000 | 2/1 |
| B3_lr_gov_only | — | — | — | -0.0092 | 0.500 | 1.000 | 2/1 |
| B4_lr_nlp_only | — | — | — | -0.0619 | 0.375 | 1.000 | 2/1 |
| B5_lgbm_gov_only | — | — | — | 0.0201 | 0.750 | 1.000 | 1/2 |
| B6_lgbm_nlp_only | — | — | — | -0.0738 | 0.125 | 0.750 | 3/0 |
| S_lr_psa_only | — | — | — | -0.1302 | 0.125 | — | 3/0 |

**Lead 4** — 1 origins (2025-Q4…2025-Q4), test HIGH 4 / LOW 1, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 0.800 | 0.800 | 1.000 | 0.889 | 0.875 | 0.157 | 4/1/0/0 |
| B1_naive_persistence | 0.800 | 0.800 | 1.000 | 0.889 | 0.500 | 0.200 | 4/1/0/0 |
| B2_lr_combined | 0.800 | 0.800 | 1.000 | 0.889 | 0.000 | 0.208 | 4/1/0/0 |
| B3_lr_gov_only | 0.800 | 0.800 | 1.000 | 0.889 | 0.250 | 0.199 | 4/1/0/0 |
| B4_lr_nlp_only | 0.800 | 0.800 | 1.000 | 0.889 | 0.500 | 0.209 | 4/1/0/0 |
| B5_lgbm_gov_only | 0.800 | 0.800 | 1.000 | 0.889 | 0.625 | 0.190 | 4/1/0/0 |
| B6_lgbm_nlp_only | 0.800 | 1.000 | 0.750 | 0.857 | 1.000 | 0.148 | 3/0/1/1 |
| S_lr_psa_only | 0.800 | 0.800 | 1.000 | 0.889 | 0.250 | 0.212 | 4/1/0/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | -0.0429 | 0.500 | 1.000 | 1/0 |
| B2_lr_combined | — | — | — | -0.0506 | 0.500 | 1.000 | 1/0 |
| B3_lr_gov_only | — | — | — | -0.0419 | 0.500 | 1.000 | 1/0 |
| B4_lr_nlp_only | — | — | — | -0.0521 | 0.500 | 1.000 | 1/0 |
| B5_lgbm_gov_only | — | — | — | -0.0325 | 0.500 | 1.000 | 1/0 |
| B6_lgbm_nlp_only | — | — | — | 0.0093 | 1.000 | 1.000 | 0/1 |
| S_lr_psa_only | — | — | — | -0.0545 | 0.500 | — | 1/0 |

**Lead 5** — 1 origins (2025-Q4…2025-Q4), test HIGH 5 / LOW 0, evaluable: no

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| PROPOSED_lgbm_combined | 1.000 | 1.000 | 1.000 | 1.000 | — | 0.029 | 5/0/0/0 |
| B1_naive_persistence | 1.000 | 1.000 | 1.000 | 1.000 | — | 0.000 | 5/0/0/0 |
| B2_lr_combined | 0.800 | 1.000 | 0.800 | 0.889 | — | 0.091 | 4/0/1/0 |
| B3_lr_gov_only | 1.000 | 1.000 | 1.000 | 1.000 | — | 0.005 | 5/0/0/0 |
| B4_lr_nlp_only | 0.800 | 1.000 | 0.800 | 0.889 | — | 0.154 | 4/0/1/0 |
| B5_lgbm_gov_only | 1.000 | 1.000 | 1.000 | 1.000 | — | 0.000 | 5/0/0/0 |
| B6_lgbm_nlp_only | 0.600 | 1.000 | 0.600 | 0.750 | — | 0.221 | 3/0/2/0 |
| S_lr_psa_only | 1.000 | 1.000 | 1.000 | 1.000 | — | 0.018 | 5/0/0/0 |

| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |
|---|---|---|---|---|---|---|---|
| B1_naive_persistence | — | — | — | 0.0290 | 1.000 | 1.000 | 0/1 |
| B2_lr_combined | — | — | — | -0.0616 | 0.500 | 1.000 | 1/0 |
| B3_lr_gov_only | — | — | — | 0.0244 | 1.000 | 1.000 | 0/1 |
| B4_lr_nlp_only | — | — | — | -0.1254 | 0.500 | 1.000 | 1/0 |
| B5_lgbm_gov_only | — | — | — | 0.0288 | 1.000 | 1.000 | 0/1 |
| B6_lgbm_nlp_only | — | — | — | -0.1922 | 0.500 | 1.000 | 1/0 |
| S_lr_psa_only | — | — | — | 0.0113 | 1.000 | — | 0/1 |

**Lead 6:** no origin with ≥ 8 published training quarters.

**Lead 7:** no origin with ≥ 8 published training quarters.

**Lead 8:** no origin with ≥ 8 published training quarters.

**Hypothesis decisions:** H1 not testable; H2 not testable; H3 not testable; H4 awaiting participant data; H5 awaiting participant data

## E23-B improvement (selected LightGBM, accuracy primary)

### origin

| Lead | Origins | HIGH/LOW | E23-B accuracy | Always-HIGH | Strongest baseline | Its accuracy | Beats it | > 75% | E23-B AUC | E23-B Brier | sign-flip p | McNemar p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 8 | 37/3 | 0.850 | 0.925 | B1_naive_persistence | 0.875 | no | yes | 0.671 | 0.160 | 0.875 | 0.875 |
| 2 | 7 | 33/2 | 0.771 | 0.943 | B1_naive_persistence | 0.829 | no | yes | 0.212 | 0.173 | 1.000 | 1.000 |
| 3 | 5 | 23/2 | 0.760 | 0.920 | B1_naive_persistence | 0.840 | no | yes | 0.620 | 0.169 | 1.000 | 1.000 |
| 4 | 3 | 13/2 | 0.867 | 0.867 | B1_naive_persistence | 0.867 | no | yes | 0.577 | 0.170 | 1.000 | 0.750 |
| 5 | 3 | 14/1 | 0.933 | 0.933 | B1_naive_persistence | 0.933 | no | yes | 0.536 | 0.120 | 1.000 | 1.000 |
| 6 | 2 | 9/1 | 0.900 | 0.900 | B1_naive_persistence | 0.900 | no | yes | 0.222 | 0.095 | 1.000 | 1.000 |

### fixed

| Lead | Origins | HIGH/LOW | E23-B accuracy | Always-HIGH | Strongest baseline | Its accuracy | Beats it | > 75% | E23-B AUC | E23-B Brier | sign-flip p | McNemar p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 8 | 35/5 | 0.750 | 0.875 | B5_lgbm_gov_only | 0.775 | no | no | 0.754 | 0.257 | 1.000 | 1.000 |
| 2 | 7 | 32/3 | 0.714 | 0.914 | B5_lgbm_gov_only | 0.800 | no | no | 0.370 | 0.240 | 1.000 | 1.000 |
| 3 | 5 | 23/2 | 0.800 | 0.920 | B3_lr_gov_only | 0.880 | no | yes | 0.337 | 0.224 | 1.000 | 1.000 |
| 4 | 3 | 13/2 | 0.867 | 0.867 | B2_lr_combined | 0.867 | no | yes | 0.250 | 0.138 | 1.000 | 1.000 |
| 5 | 3 | 13/2 | 0.867 | 0.867 | B2_lr_combined | 0.867 | no | yes | 0.327 | 0.185 | 1.000 | 1.000 |
| 6 | 2 | 9/1 | 0.900 | 0.900 | B2_lr_combined | 0.900 | no | yes | 0.889 | 0.085 | 1.000 | 1.000 |

## Leave-one-quarter-out (NON-chronological; descriptive only)

Global-median threshold 14.993; AUC proposed 0.822, combined LR 0.722. Uses future quarters for training, so it cannot support any forecasting claim.

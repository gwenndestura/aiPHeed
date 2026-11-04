# Objective 2: forecasting model results (development evidence; C-b unchanged)

## 1. All candidates under fixed rules (62 quarters, 2010-Q1..2026-Q3)

| Model | Lead | Accuracy (95% CI) | Balanced | Precision | Recall | F1 | AUC | Brier | ECE | Failed | Adopted? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **C-b** (main) | 1 | 0.790 (0.674–0.873) | 0.717 | 0.812 | 0.907 | 0.857 | 0.702 | 0.187 | 0.169 | R7 | Reference |
| C-b | 2 | 0.790 | 0.717 | 0.812 | 0.907 | 0.857 | 0.704 | 0.184 | 0.152 | R7 | — |
| K1 (50/50 with LOGIT) | 1 / 2 | 0.710 / 0.774 | 0.600 / 0.734 | 0.745 / 0.837 | 0.884 / 0.837 | 0.809 / 0.837 | **0.786** / 0.710 | **0.172** / 0.185 | 0.139 / 0.148 | R2 R3 R7 / R7 | No |
| K2 (weighted) | 1 / 2 | 0.774 / 0.790 | — | — | — | — | 0.704 / 0.704 | 0.188 / 0.184 | — | R3 R7 / R7 | No |
| K3 (reversal features) | 1 / 2 | 0.774 / 0.774 | 0.705 | 0.809 | 0.884 | 0.844 | 0.687 / 0.703 | 0.190 / 0.182 | 0.171 / 0.139 | R5 R7 / R7 | No |
| **S1 (Kalman true hunger)** | 1 / 2 | **0.806** (0.691–0.886) / **0.806** | **0.743** | **0.830** | 0.907 | **0.867** | 0.711 / **0.715** | 0.187 / **0.181** | 0.165 / 0.166 | **none** | **No** (G2: p 0.46 / 0.22) |
| S2 (K1 + past-chosen threshold) | 1 / 2 | 0.774 / 0.710 | **0.778** / 0.732 | 0.892 / 0.879 | 0.767 / 0.674 | 0.825 / 0.763 | = K1 | = K1 | — | R7 / R2 R5 R7 | No (G2 impossible) |

**Algorithm 3 (MRLT):** C-b 2, K2 2, K3 2, S1 2, K1 0.

Sources:
- `NEW_MODEL/ALLBASE/PHASE_C_RESULTS.md`;
- `S1_RESULTS.md`, `out/s1_results.json`;
- `out/s2_results.json`.

## 2. Root causes investigated

| Question | Evidence | Finding |
|---|---|---|
| Why R7 fails (2015–2020) | Phase A noise ceiling; K3, S1 reversal analysis | The SWS noise ceiling is 0.773 there; C-b follows the last reading through reversals; reversal features (K3) do not help; the measurement-error filter (S1) recovers one quarter, enough to pass R7 at 0.619 but fragile |
| Persistence dependence | Phase A | C-b gives persistence's call in 77% of quarters; 10 of 13 Lead-1 errors are persistence's call |
| Predictor availability (`out/obj2_predictor_availability.json`) | Every C-b input except the news anomaly is available at 100% of origins 1998–2026 | **The FSSI anomaly is available at 0% of the 1998–2009 training origins and 17% of the evaluated origins (from 2023-Q2).** A tree model trained mostly on rows without news cannot give it weight. This is the structural reason for its ≈0% SHAP |
| Calibration | ECE 0.14–0.17 for all LightGBM candidates; LOGIT 0.130 | C-b is somewhat over-confident; K1 is the best calibrated |
| Uncertainty | Wilson 95% CI on accuracy 0.674–0.873 | Leads 1–2 overlap the 0.75 line; the MRLT result is not secure |
| Algorithms tried | LightGBM, GRU (HISTORY_RETRAIN), logistic, ensembles (K1/K2), state-space filter (S1), threshold (S2), sample weights (NOISE_W), level regression, Platt | None reaches AUC 0.80; the best is K1 (0.786, Lead 1 only) |
| Missing sources | BSP remittances (HTTP 403), provincial unemployment (national LFS only) | Cannot be tested without data files |

## 3. Status

- **Measured and reported:** every thesis metric at both leads, plus walk-forward MRLT (2 quarters).
- **Not met:**
  - the AUC target of 0.80;
  - R7 (except S1, by one forecast);
  - the Algorithm 4 blind test, which needs four sealed 2027 quarters (about 2028).
- **Pending your and the adviser's decision:** whether S1 should be added to the sealed prospective registry, so that
  new data, not the 62 examined quarters, decide between C-b and S1.

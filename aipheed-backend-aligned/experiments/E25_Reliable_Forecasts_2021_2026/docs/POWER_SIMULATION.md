# Simulated power (synthetic data only; no observed outcome used)

`runner/power_sim.py`, seed 20261014, 2000 replications per cell, one-sided exact sign-flip over forecast dates at alpha = 0.05 (Monte Carlo above 16 dates; monthly origins averaged in blocks of 3).

## A. Accuracy versus naive persistence (ideas 1, 3)

Per date: 5 rows; a row's label changes with probability *change rate* (persistence is wrong there); the model anticipates a change with probability *anticipated* and wrongly flips an unchanged row with probability *false flip*.

| Dates | Change rate | Anticipated | False flip | Power |
|---|---|---|---|---|
| 8 | 0.05 | 0.5 | 0.0 | 0.001 |
| 8 | 0.05 | 0.5 | 0.02 | 0.001 |
| 8 | 0.05 | 0.5 | 0.05 | 0.001 |
| 8 | 0.05 | 0.75 | 0.0 | 0.006 |
| 8 | 0.05 | 0.75 | 0.02 | 0.004 |
| 8 | 0.05 | 0.75 | 0.05 | 0.002 |
| 8 | 0.05 | 1.0 | 0.0 | 0.015 |
| 8 | 0.05 | 1.0 | 0.02 | 0.016 |
| 8 | 0.05 | 1.0 | 0.05 | 0.003 |
| 8 | 0.1 | 0.5 | 0.0 | 0.019 |
| 8 | 0.1 | 0.5 | 0.02 | 0.009 |
| 8 | 0.1 | 0.5 | 0.05 | 0.002 |
| 8 | 0.1 | 0.75 | 0.0 | 0.079 |
| 8 | 0.1 | 0.75 | 0.02 | 0.055 |
| 8 | 0.1 | 0.75 | 0.05 | 0.022 |
| 8 | 0.1 | 1.0 | 0.0 | 0.196 |
| 8 | 0.1 | 1.0 | 0.02 | 0.104 |
| 8 | 0.1 | 1.0 | 0.05 | 0.060 |
| 8 | 0.2 | 0.5 | 0.0 | 0.193 |
| 8 | 0.2 | 0.5 | 0.02 | 0.132 |
| 8 | 0.2 | 0.5 | 0.05 | 0.069 |
| 8 | 0.2 | 0.75 | 0.0 | 0.493 |
| 8 | 0.2 | 0.75 | 0.02 | 0.368 |
| 8 | 0.2 | 0.75 | 0.05 | 0.225 |
| 8 | 0.2 | 1.0 | 0.0 | 0.750 |
| 8 | 0.2 | 1.0 | 0.02 | 0.614 |
| 8 | 0.2 | 1.0 | 0.05 | 0.431 |
| 10 | 0.05 | 0.5 | 0.0 | 0.004 |
| 10 | 0.05 | 0.5 | 0.02 | 0.002 |
| 10 | 0.05 | 0.5 | 0.05 | 0.000 |
| 10 | 0.05 | 0.75 | 0.0 | 0.018 |
| 10 | 0.05 | 0.75 | 0.02 | 0.006 |
| 10 | 0.05 | 0.75 | 0.05 | 0.003 |
| 10 | 0.05 | 1.0 | 0.0 | 0.057 |
| 10 | 0.05 | 1.0 | 0.02 | 0.025 |
| 10 | 0.05 | 1.0 | 0.05 | 0.009 |
| 10 | 0.1 | 0.5 | 0.0 | 0.049 |
| 10 | 0.1 | 0.5 | 0.02 | 0.018 |
| 10 | 0.1 | 0.5 | 0.05 | 0.010 |
| 10 | 0.1 | 0.75 | 0.0 | 0.182 |
| 10 | 0.1 | 0.75 | 0.02 | 0.106 |
| 10 | 0.1 | 0.75 | 0.05 | 0.050 |
| 10 | 0.1 | 1.0 | 0.0 | 0.394 |
| 10 | 0.1 | 1.0 | 0.02 | 0.246 |
| 10 | 0.1 | 1.0 | 0.05 | 0.103 |
| 10 | 0.2 | 0.5 | 0.0 | 0.367 |
| 10 | 0.2 | 0.5 | 0.02 | 0.242 |
| 10 | 0.2 | 0.5 | 0.05 | 0.113 |
| 10 | 0.2 | 0.75 | 0.0 | 0.765 |
| 10 | 0.2 | 0.75 | 0.02 | 0.565 |
| 10 | 0.2 | 0.75 | 0.05 | 0.336 |
| 10 | 0.2 | 1.0 | 0.0 | 0.936 |
| 10 | 0.2 | 1.0 | 0.02 | 0.796 |
| 10 | 0.2 | 1.0 | 0.05 | 0.594 |

## B. Structural simulation: probabilistic H + 2D forecaster with the right structure (ideas 1, 2, 3, 5)

Latent regional hunger random walk (innovation sd sigma_eta) + SWS sampling error sd 1.5; provincial D AR(1) (sd 1, phi_D); label = 1[H_obs + 2D > median]. Power of the correctly specified probabilistic forecaster against B1 and B1p.

| Dates | Leads pooled | sigma_eta | phi_D | Brier vs B1 | Brier vs B1p | Accuracy vs B1 |
|---|---|---|---|---|---|---|
| 8 | [1] | 1.5 | 0.3 | 0.498 | 0.312 | 0.015 |
| 8 | [1] | 1.5 | 0.6 | 0.454 | 0.291 | 0.003 |
| 8 | [1] | 2.5 | 0.3 | 0.336 | 0.387 | 0.004 |
| 8 | [1] | 2.5 | 0.6 | 0.311 | 0.377 | 0.004 |
| 8 | [1] | 4.0 | 0.3 | 0.235 | 0.389 | 0.004 |
| 8 | [1] | 4.0 | 0.6 | 0.197 | 0.387 | 0.002 |
| 10 | [1, 2, 3] | 1.5 | 0.3 | 0.699 | 0.387 | 0.068 |
| 10 | [1, 2, 3] | 1.5 | 0.6 | 0.672 | 0.387 | 0.046 |
| 10 | [1, 2, 3] | 2.5 | 0.3 | 0.545 | 0.432 | 0.032 |
| 10 | [1, 2, 3] | 2.5 | 0.6 | 0.516 | 0.419 | 0.021 |
| 10 | [1, 2, 3] | 4.0 | 0.3 | 0.379 | 0.442 | 0.008 |
| 10 | [1, 2, 3] | 4.0 | 0.6 | 0.383 | 0.415 | 0.003 |

## D. Monthly-origin evaluation of the provincial price component (idea 9)

| Monthly origins | phi (monthly) | Power, Brier vs sign persistence |
|---|---|---|
| 51 | 0.7 | 1.000 |
| 51 | 0.9 | 0.988 |

## E. Leading indicator for regional hunger (idea 11)

| Round-to-round changes | True correlation | Power (slope) | Share of runs where it lowers MSE |
|---|---|---|---|
| 12 | 0.2 | 0.150 | 0.496 |
| 12 | 0.4 | 0.375 | 0.650 |
| 12 | 0.6 | 0.719 | 0.836 |
| 16 | 0.2 | 0.181 | 0.514 |
| 16 | 0.4 | 0.495 | 0.709 |
| 16 | 0.6 | 0.829 | 0.888 |

## F. Exploratory provincial target D > 0, 11 dates (ideas 5, 6)

| phi_D | Power, Brier vs persistence | Power, accuracy vs persistence |
|---|---|---|
| 0.3 | 0.953 | 0.000 |
| 0.6 | 0.862 | 0.000 |

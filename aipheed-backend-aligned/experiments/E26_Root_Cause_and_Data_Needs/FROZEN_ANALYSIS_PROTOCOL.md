# E26 Frozen Analysis Protocol: root cause, value of information, evaluability horizon, prospective ledger

**Freeze.**

- Written and hashed (`runner/PROTOCOL_SHA256.txt`) **before** any E26 analysis was run.
- The libraries are copied unchanged from E25: `e25lib.py`, `e23_lib.py`, `pcf.py` (hashes equal to E25's).

**What E26 does not do.** The approved target (S1 = H + 2D > τ, reading A), the criteria C1–C9, the E25 FINAL models and every sealed forecast are **unchanged**.

**No new seal.** E26 creates no new seal or forecast for 2026-Q3, 2026-Q4 or 2027-Q1. A web search exposed H2-2026 national/regional price information (`docs/CONTAMINATION_LOG.md`).

**Status of the analyses.** Every analysis below is a **diagnostic on development quarters** (all examined before). **None selects a model, a threshold, a feature or a target.**

## A. Outcome information budget (descriptive)

**Counts:**

- independent outcome observations per layer: regional SWS production rounds and labelled quarters; provincial food-insecurity outcomes in authorized data;
- T1 rows, LOW rows and label changes per lead;
- variance shares of the label (regional H vs 2D).

## B. Regional signal-to-noise

**Data:** round-to-round changes ΔH between consecutive production rounds (2021–2026, reading A).

**Sampling variance of a change:** p(100 − p)/n per round, for n = 300 and for n = 600. Both are reported, because the per-round Balance Luzon sample size is not verified in authorized data.

**Reported:**

- the share of the variance of ΔH attributable to sampling noise;
- the implied signal-to-noise ratio;
- the probability that the sign of an observed change equals the sign of the true change.

## C. Value of information (VOI)

**Information sets at origin O(t), T1-A, leads 1–3:**

| Set | Content |
|---|---|
| **I0** | Status quo (E25 rules) |
| **I1** | I0 + the production SWS round(s) whose fieldwork is in quarter t, as if published by O(t). This is a "timely regional reading". |
| **I3** | I1 + D(t) complete, so the label of quarter t is known at O(t): persistence uses it, and the threshold includes it |
| **IO** | Realized H of the target quarter. **Oracle; diagnostic upper bound only.** |

**Models under each set:**

- B1 persistence (last label known in the set);
- B1p (calibrated persistence);
- PCF21 and PCF21_NOW (E25 definitions, with the H inputs of the set).

**Rows:** identical (lead, origin) pairs across all sets: the intersection of origins with ≥ 8 labelled training quarters under every set, t ≤ 2026-Q1.

**Metrics:**

- accuracy, Brier, AUC, HIGH/LOW counts;
- label changes relative to the set's own last label, and how many were anticipated;
- exact one-sided sign-flip per date of each model vs (a) B1 under I0 and (b) B1 under the same set.

**Reading rule.** "Information value for anticipation" exists only if a model with the set beats **persistence with the same set**. Beating I0 persistence alone only shows that the information is fresher.

## D. Evaluability horizon (Monte Carlo; parameters from authorized 2021–2026 data only)

**Models:**

- **H:** local level (σ_η by maximum likelihood on the production rounds, sampling n = 600). Started from the filtered state at the last authorized round (2026-Q2).
- **Missing rounds:** a quarter has no production round with probability = the share of 2021-Q2…2026-Q2 quarters without one.
- **D:** D_HIER parameters (shrunk province means, pooled AR(1)) fitted on 2021-Q1…2026-Q2.

**Simulation:** 10,000 paths, quarters 2026-Q3…2031-Q4, seed 20261014.

**Label rule:** τ = median of the labels published before O(t), including the actual 2021–2026 labels. Labels are published one quarter after their quarter.

**Accrual:** lead-1 evaluation dates accrue from target 2026-Q4 (the first target of the E25 seal at lead 1).

**Reported by year end 2027…2031:**

- the distribution of scored dates and LOW rows;
- P(evaluable: ≥ 8 dates, ≥ 5 HIGH, ≥ 5 LOW);
- P(the ledger's anytime-valid test (section E) declares a correctly specified probabilistic forecaster better than persistence **and** calibrated persistence). This is an **optimistic upper bound**, because the simulated forecaster knows the true parameters.

## E. Prospective evaluation ledger (implemented in `backend_dev/app/quarterly/ledger.py`)

**Ledger structure:**

- **Append-only, hash-chained entries:** SEAL, OUTCOME, SCORE.
- **A SEAL is refused** if its target's outcome is already in the ledger, or if a seal exists for the same (arm, target, origin).
- **An OUTCOME** must reference a researcher authorization (path + SHA-256).
- **A SCORE** uses only sealed bytes and authorized outcomes.

**Statistics:**

- Per scored date j: d_j = Brier(baseline) − Brier(model), the mean over the 5 provinces, and likewise for accuracy.
- **e-process:** E_n = Π(1 + λ_j d_j), with λ_j predictable (aGRAPA plug-in from dates < j, clipped to [0, 0.5]).
- **Baselines:** persistence and calibrated persistence; each e-process must reach **2/α = 40** (α = 0.05, Bonferroni over the two).
- **Validity:** under H0 (E[d_j | past] ≤ 0) E_n is a non-negative supermartingale, so P(sup E_n ≥ 40) ≤ 0.025 per baseline at any stopping time.

**Claim rule.** A claim of "beats the strongest baseline on unseen quarters" (C9 evidence) needs all of:

- evaluability on the **unseen** scored rows (≥ 8 dates, ≥ 5 HIGH, ≥ 5 LOW);
- the e-processes for the declared metric (accuracy for C2 as approved; Brier only if the adviser approves P2) ≥ 40 against both baselines.

**Operating characteristics** (type-I error, power) are checked by simulation on synthetic data only.

## F. New-outcome adapters and local validation (implemented; no data used)

**Adapters** for the sources in `SOURCE_INVESTIGATION.md`:

| Adapter | Content |
|---|---|
| CBMS FIES | Municipal and provincial prevalence of moderate or severe household food insecurity |
| FNRI | Provincial FIES/HFIAS |
| PSA | Provincial subsistence incidence |
| SWS area or region aggregates | — |
| DSWD DROMIC / NDRRMC | Affected families by province and quarter |

**Each adapter checks:**

- the authorization hash;
- the declared coverage;
- geography codes (PSGC, CALABARZON only);
- the reference period inside 2021–2026 (no pre-2021 row; mixed files refused);
- the publication date evidence.

**Local validation:**

- rank agreement (Spearman, Kendall, top-third agreement, date or LGU cluster bootstrap) between aiPHeed's provincial/LGU scores and an authorized local outcome;
- the density-only and poverty-only orderings as references.

Tested on synthetic fixtures only.

## G. Two-layer reporting (implemented)

Every forecast record carries three outputs, kept separate:

1. **Regional risk** (one per quarter): P(H_{t+k} > τ) and the H interval. Evaluated with one observation per quarter.
2. **Provincial differential:** the 2μ_D contribution and P(D > 0), labelled "constructed relative food-price pressure indicator, not a verified food-insecurity outcome".
3. **The approved composite** P(S1 > τ).

Rankings state which layer drives them.

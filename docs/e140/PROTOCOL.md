# E140: resolving the zero-tree problem. Protocol E140-P1

* **Code:** `backend/app/e140/` (`diagnose.py`, `model.py`, `evaluate.py`).
* **Lock:** `backend/data/e140/out/PROTOCOL_LOCK.json`, holding the hashes of this file, `model.py`, `evaluate.py`
  and the thresholds.
* **Sequence:**
  1. **Diagnosis**, which is descriptive only. It ran before this protocol was written.
  2. **One controlled improvement:** the candidates below.
  3. **One locked run**, followed by the final audit.
* **Pre-lock check:** a smoke test on shuffled labels only.
* **E139 is preserved.** Its target, rows, folds, release rules, metrics, bootstrap and gate thresholds are imported
  unchanged. All results remain development evidence.

## 1. Diagnosis (`data/e140/out/diagnostics.json`, E139 rows, LORO)

| Finding | Value |
|---|---|
| Sample | 125 rows; 62 decisive; 16 regions; 47 re-surveyed provinces; 8.3 rows per feature |
| Residual variance after E139's linear prior | 0.154. Survey error is only 22 % of it (0.034), so 0.120 is not noise. |
| Is that residual related to any feature? | **No.** Every \|ρ\| ≤ 0.23, Holm p ≥ 0.17 (strongest: food CPI +0.22, cyclones −0.22). |
| Where the residual sits | 31 % between regions, 9 % between island groups, 0.3 % between survey rounds |
| Trees on top of the prior (10–300 trees) | Out-of-fold EB 0.194–0.201, against 0.192 with no trees. Worse at every count, also with min_child 5, without weights, and with Huber loss. |
| Trees alone, no prior | 0.257 (0 trees) → 0.206 (300 trees). Always above the prior. |

**Causes.**
1. The features' signal is almost entirely **linear**, and the prior already holds it. Residual learning has
   nothing left to learn from these features.
2. Constant-leaf trees approximate a linear signal poorly with 125 rows, so trees without the prior lag behind.
3. What remains is mainly **region-specific**. It cannot transfer to an unseen region, and no feature explains it.

**Ruled out as causes:**
* the loss function (Huber gives the same result);
* survey weighting (unweighted gives the same result);
* over-restrictive leaves (min_child 5 gives the same result);
* survey round (0.3 % of the residual).

## 2. The one controlled improvement

Two LightGBM-native candidates. Neither has a separate linear prior.

* **LT (linear trees).** `linear_tree=True`: piecewise-linear leaves, depth 1, ≥ 20 rows per leaf,
  linear_lambda 1. Features: all 15 E139 features + island group. Trees: {10, 30, 100}.
  * Why: it lets LightGBM carry the linear signal itself, and split where slopes differ (E138 found the relation
    differs by island group).
* **GBC (constant leaves, compact).** Features: poverty (3), history (2), island group, food CPI, cyclones (2).
  Settings: 4 leaves, depth 2, ≥ 10 rows per leaf, learning rate 0.02. Trees: {100, 300, 600}.
  * Why: trees alone kept improving up to 300 trees in the diagnosis. This candidate uses fewer, more relevant
    features.
* **LGBM-AUTO, the candidate.** Inside each training fold, it picks LT or GBC by inner grouped CV (nested). **Zero
  trees are not in either grid.**

**Island group.** A 3-level geographic covariate. It is known for any province, including in an unseen region. It
is not a unit identifier.

## 3. Comparisons (identical rows and folds)

1. PRIOR: the linear prior alone.
2. LGBM-GBC and LGBM-LT: LightGBM without the prior.
3. PRIOR+TREES30: the linear prior with 30 trees, forced.
4. E139, the selected model.
5. RR-F, the best E139 reference.

Base rates: NAT, REGPREV, PERS.

**Quarterly-indicator test.** LGBM-AUTO vs LGBM-AUTO without the six time-varying indicators (food and rice CPI
YoY, rainfall anomaly, cyclones over the last 4 quarters, agriculture YoY, fisheries YoY). It is run on ENNS rows
(LORO) and on TFWD.

**Schemes:** LORO, LOPO, ISLAND, V2, TFWD (as in E139).

**Reported:**
* trees and model kind per LORO fold;
* EB differences with 95 % cluster-bootstrap CIs;
* E139's metric set;
* leave-one-region, leave-one-island-group and leave-one-survey-round dependence of the LGBM-AUTO − PRIOR difference.

## 4. Gate and decision

* **T1:** the final model has more than 0 trees, and at least 75 % of LORO folds use trees. This is trivially true
  by construction; it is recorded for transparency.
* **T2:** LGBM-AUTO beats PRIOR in LORO. The 95 % CI upper bound of the EB difference must be < 0. **Trees must
  improve independent predictions.**
* **E139's checks at Lead 0, unchanged:** G1, G2, G3, G5, G6, G9, G4 (vs the best of PRIOR, RR-F and E139), G7, G8.
* **Decision:**
  * **A:** every check passes.
  * **B:** T1, T2, G1, G4, G5, G6, G7 and G8 pass (structural), while G2, G3 or G9 fail. Only the structural
    estimate may be integrated.
  * **C:** otherwise. Not achievable with the current data; production stays unchanged.
* **Leads.** Leads 1–4 are evaluated only if the decision is A or B. E139 showed that the quarterly inputs do not
  change the scores.

# E129 validation design (for any future provincial target)

## 1. Time: expanding-window walk-forward by issue date

- **Issue date:** O(t) = the first day of quarter t+1 (E128 convention).
- **Training at origin t** uses only target values **published before O(t)**, for **all provinces at once**. Same-quarter values of other provinces must not enter, because 74 % of food-CPI variance is shared across provinces, so another province's current value leaks the target.
- **Features** are point-in-time: the E119 rule (available strictly before the issue date), using the CPI ledger dates. Verified dates cover 32 of 180 province-months today; the rest are provisional.
- **Tuning** happens inside the training window only (inner chronological folds). There is **no random row split**.
- **Lead k = t+k.** One model per lead (direct), or one model with lead as a feature. The choice is fixed before fitting.

## 2. Geography

| Design | Use |
|---|---|
| **Pooled panel, per-province reporting** | **Primary.** Metrics pooled, plus one table per province (confusion matrix or errors). |
| Province-held-out (leave-one-province-out, still time-ordered) | **Supplementary only.** With 5 provinces it tests transfer to an unseen province, but the held-out province shares the regional time signal. A pass does not prove geographic generalization. |
| Province fixed effects / province-specific persistence | Required comparators, so a model gets no credit for province means |

## 3. Uncertainty

- **Cluster bootstrap over target quarters** (all 5 provinces resampled together), 2,000 draws.
- Report the design effect and effective n.
- **Holm correction** across baselines, and across provinces for per-province tests.

## 4. Shared-feature control

- **Tag features** as provincial, regional or national (`E129_FIVE_TRIGGER_GROUP_GEOGRAPHIC_AUDIT.csv`).
- **Ablation:** run national and regional features as one block. They cannot explain differences between provinces.
- **Target:** province deviation from the quarter mean, as a secondary target. It isolates what is province-specific.

## 5. Leakage tests (must pass before scoring)

- Perturb future target values and future feature months. Forecasts must not change.
- Perturb past values. Forecasts must change (negative control).
- Check that no same-quarter value from another province enters.

## 6. Evaluability rule (from E128)

**Not evaluable = not passed.**

**Minimum per lead**
- ≥ 10 evaluation quarters;
- ≥ 40 genuine province rows;
- both classes present (binary).

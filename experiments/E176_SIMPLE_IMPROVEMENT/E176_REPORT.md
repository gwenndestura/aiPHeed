# E176: SIMPLE performance improvement (2026-11-07)

**Outcome C: no acceptable improvement can be produced defensibly. No candidate was run; SIMPLE and E168 are unchanged.**
Baseline verified from saved artifacts: SIMPLE config hash `ad38a0f1...` recomputes exactly; E172 code unchanged since its lock.

## Baseline (Lead 2, E172 saved forecasts)
| | E168 | SIMPLE |
|---|---|---|
| Correct | 55/72 | 59/72 |
| Low bound / C1 | 0.641 / fail | 0.708 / pass |
| F1 | 0.730 | 0.772 |
| Balanced accuracy | 0.800 | 0.834 |
| ROC-AUC | 0.887 | 0.874 |
| Brier | 0.137 | 0.144 |

SIMPLE's +4: five ENNS 2018 LOW provinces move from P(HIGH) 0.505-0.523 to 0.493-0.499 (Abra, Camarines Norte, Isabela, Siquijor,
Zambales) and one HIGH province (Aklan) from 0.505 to 0.487. 66 of 72 classes are the same (`baseline_prediction_comparison.csv`).

## Why SIMPLE's Brier is worse (`calibration_analysis.csv`)
Entirely ENNS 2021: Brier 0.110 vs 0.086. In ENNS 2018 (0.160 vs 0.163) and 2019 (0.163 vs 0.165) SIMPLE is slightly better.
For the 2021 issue SIMPLE's selected configuration got almost no temperature shrink (lambda 0.97), so its probabilities sit further
from 0.5 (mean distance 0.318 vs 0.275), which costs Brier on the 2021 rows it gets wrong. Both models over-forecast on average
(calibration in the large +0.08); that is shared, not SIMPLE-specific.

## Why SIMPLE's ROC-AUC is worse (`ranking_analysis.csv`)
Within-survey ranking is as good or better: AUC 0.911 vs 0.902 (2018), 0.891 vs 0.865 (2019); worse in 2021 (0.833 vs 0.893).
Discordant HIGH-LOW pairs within a survey: 41 for both. The pooled loss comes from pairs across surveys (107 vs 92): the 2021
probabilities sit on a different scale from 2018/2019. It is a per-issue scale issue, not worse province ordering.

## Can calibration fix Brier without changing classifications?
Only a sign-preserving rescaling of the score (P = 0.5 fixed) keeps all 72 classes. That is a temperature change, and SIMPLE already
applies E168's training-only temperature rule. Choosing a different rule now would be chosen because the 2021 test rows show
over-confidence: that uses held-out outcomes. Platt or isotonic fitted on training folds move the 0.5 crossing, so they can flip the
2018 rows SIMPLE wins by margins of 0.001-0.013 and cannot guarantee 59/72. SIMPLE's own selection already compares identity with
cross-fitted linear calibration on training folds (identity was chosen at every issue).

## Can LightGBM changes improve ranking?
Every training-only lever (complexity, regularization, leaves/depth, inputs, lead use, bagging) was in the E172 menu; SIMPLE is the
low-complexity subset of it. Within-survey ranking is not SIMPLE's weakness. Any refit risks the razor-thin 2018 gains.

## Why the acceptance targets cannot be met honestly
The targets (>= 59/72, Brier <= 0.137, ROC-AUC >= 0.887) are measured on the same 72 rows that selected SIMPLE. A candidate is
acceptable only if it is chosen without those outcomes, yet the only lever that closes the Brier gap (more shrink for the 2021 issue)
is known only from them. So no candidate satisfies requirement 8 together with the targets.

## Answers
- Why Brier worse: ENNS 2021 over-confidence (lambda 0.97). Why AUC worse: cross-survey scale, not within-survey ranking.
- Calibration without class changes: only via a temperature change already in the method; a new one would be test-informed.
- LightGBM ranking improvement: no untested training-only lever remains.
- 59/72 retained and C1-C6: yes, for SIMPLE as it is (exploratory, post-hoc).
- Trade-off that remains: SIMPLE +4 classes (thin margins, 2018) vs E168 better Brier and AUC (2021).
Evidence status: exploratory; nothing here is independent validation. The fair test remains the E173 sealed comparison on new rows.

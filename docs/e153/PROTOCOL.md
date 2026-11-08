# E153 protocol: optimisation under overfitting control

Requested by the owner, who asked for higher accuracy and no overfitting. **E151 and E152 stand unchanged.** E152's protocol said no third attempt on these rows. The owner's explicit request overrides that, and this is disclosed.

## Evidence status, stated first

This is the fourth look at the same 72 rows, after E151, D5 and E152, and their errors have been studied. **Tuning inside training rows stops ordinary overfitting. It cannot stop overfitting by the analyst from repeated looks.** So this result is retrospective, and it can be read only as an upper-side estimate. Only sealed forecasts are clean.

## Fixed

Target HFIAS moderate plus severe, HIGH at 50, Lead 1, same 72 rows, same anchor. Nothing is scaled. All five groups always stay as inputs.

## Tuned only inside each round's training rows

* Inputs: five groups, or five groups + news.
* Tree settings: 48 combinations of leaves, minimum rows, L2 penalty, feature sampling and trees; depth at most 3; monotone signs kept.
* Weight on the LightGBM adjustment: 0.25, 0.5, 0.75, 1.
* Criterion: lowest soft Brier, not accuracy, because accuracy near the 50 line is unstable.
* Validation: leave out whole earlier rounds when training holds at least two, otherwise regions.
* The final forecast averages 10 seeds.

## Overfitting measures

1. In-sample against held-out error.
2. Rows changing class across single-seed fits.
3. Same settings fitted to training errors shuffled within round and lead, 40 times: what accuracy does a model with no input signal reach?

## Adoption rule, fixed now

E153 replaces the E151 required model **only if** pool accuracy is at least 0.75 **and** its Brier is below E151's with the 95 % interval below 0. Otherwise E151 stays, whatever the accuracy shows. Release gates R1 to R9 still decide production separately; R8 and R9 are not affected by this work.

## One run

The code checks hashes and refuses a second run.

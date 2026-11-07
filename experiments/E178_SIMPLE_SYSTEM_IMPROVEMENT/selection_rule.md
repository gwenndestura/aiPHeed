# E178 selection rule (written before any candidate was evaluated, 2026-11-07)
Population: the 156 untainted FNRI 2015 training rows, region-grouped folds, cross-fitted sd (E177 `probs`, mode raw).
A candidate counts as an improvement over K0 only if ALL hold:
1. out-of-fold accuracy not lower than K0;
2. out-of-fold Brier lower than K0 by more than 2 x the seed noise (SD of K0's Brier across 5 single-seed refits);
3. fewer rows changing class across seed instances than K0 (stability), for K1/K3 measured across three disjoint 5-seed ensembles
   (151-155, 156-160, 161-165) vs five single seeds for K0/K2.
A candidate meeting only 3 is a stability (technical) improvement with predictive improvement unverified.
Nothing is ever scored on the 72 evaluation rows.

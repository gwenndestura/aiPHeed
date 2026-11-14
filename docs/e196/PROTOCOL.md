# E196: training-selected lagged averaging of E194. Fixed before results. Local only.

Written 2026-11-10 at the owner's request ("fix Leads 2–3"), after E195.

## Problem
- **E195's single rule.** E195 averaged every lead with the two older forecasts. That helped Lead 1 (81.9 %) and hurt
  Leads 2–3.
- **Only older forecasts are available.** A Lead-L forecast can only use forecasts issued earlier (Leads L+1, L+2), and
  the Lead-(L−1) forecast is issued later. So whether to average must be decided per lead, without the test outcomes.

## Method
1. **Re-run E194 exactly.** For each (survey, lead) job: the top-5 Stage-A configurations, with E184's synthetic
   augmentation and 20 draws each. This time, also save each job's **real-row inner out-of-fold forecasts (mu),
   averaged over the 100 fits**.
   - The training rows contain several lead snapshots of each past survey target (`lead` = 1…8).
   - All snapshots of a province fall in the same region fold, so these OOF forecasts never saw their own outcome.
2. **Candidate rules for Lead L** (equal weights):
   - S1 = {L}, i.e. E194 unchanged;
   - S2 = {L, L+1};
   - S3 = {L, L+1, L+2}.
3. **Choosing a rule, on training rows only.**
   - Use the training targets (key, survey) that have OOF forecasts at every lead the candidates need.
   - Compare the candidates on that common set by weighted SSE of the averaged OOF mu against y_true, with E168's
     weights.
   - Choose the lowest SSE. Ties, or no training target with the needed leads, go to the smaller set. When S3's leads
     are missing, compare only S1 and S2. When S2's are missing too, use S1.
4. **E196 at Lead L** = the equal-weight mean of E194's outer probabilities over the chosen set's leads. The outer
   forecasts are those of the same (province, survey), all issued at or before Lead L's issue date.
5. **Evaluated** at Leads 1–3, plus Lead 4 for reference.

## Decision
- **E196 is preferred to E194 only if all three hold, at Leads 1–3:**
  - accuracy ≥ E194's at each lead;
  - Brier ≤ E194's at each lead;
  - accuracy higher at at least one lead.
- **Also reported:** McNemar and Brier CIs against E194 and E184, the owner rule, false alarms, the rule chosen per job,
  and the reproduction check against E194's stored probabilities.
- **Scope.** Nothing is committed, pushed or staged.

# PROTOCOL_DRM addendum 1 (written 2026-11-13 AFTER the confirmation test, BEFORE any model containing D3 is fitted)

## Confirmation result (DRM_confirmation.json; name-matching fixed for Samar and Maguindanao population; first run kept as *_v1_*)
D3_disp (hydro-met displaced persons per 1,000 since the anchor survey) is CONFIRMED: rho +0.506 (2015->2018) and +0.274 (2015->2019),
combined p 0.008, Holm p 0.048. D1, D2, D4, D5, D6 are not confirmed. The assistance hypothesis (D4/D5) is NOT supported on T2/T3.

## Consequences fixed now
- DROMIC provincial data do not exist before 2016 (2014 folder not compiled; Yolanda absent; 2015 and most 2016 reports unavailable: HTTP 410/401).
  D3 is therefore MISSING for every FNRI2015-target row and every NNS2013-anchored long-gap pair row.
- In the 2018 and 2019 folds every training row is an FNRI2015 target, so D3 cannot be learned there: any D3 model equals its non-D3 version
  in those rounds. Hence ATTR-D and HYB-D equal ATTR and HYB in 2018/2019 (both already fail rule 1 there), and A6 equals A5 in 2018/2019
  (fails 2018). These three are recorded as "fail by construction" and are not fitted.
- The only informative arm is LG-D, defined below. Because LG-D equals FINAL-LG wherever earlier out-of-sample rounds exist, rolling-origin
  SELECT cannot distinguish them (tie -> FINAL-LG). LG-D therefore cannot replace FINAL-LG on retrospective evidence; at most it can be sealed
  as a prospective challenger if its 2021 result improves without any degradation.

## LG-D
 FINAL-LG with one added candidate input `drm_disp` = D3 computed per training/test row at that row's own issue quarter (window from the
 2015-Q3 anchor survey to the start of the issue quarter; latest DROMIC report published before that date), monotone sign +1, added to every
 candidate input set; missing for FNRI2015 targets and pair rows (MIND missing flag, as FINAL handles all gaps). Seeds 168/1/2/3/4; 2021-fold
 training-round drops (seed 168); one 2018-fold and one 2019-fold seed-168 refit to confirm identity with FINAL-LG.
 Reported against the owner's 8 targets in every round and against FINAL / FINAL-LG with the PROTOCOL_TUNE decision rule (rule 4 is
 unattainable by construction, as stated above).

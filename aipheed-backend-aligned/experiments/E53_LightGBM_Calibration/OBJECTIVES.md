# Chapter 1 objective-to-test mapping (E53)

**Source:** `THESIS 2 (11).pdf`, §1.3–1.5. Builds on `E52_Objectives_Acceptance/OBJECTIVES.md`; the objectives themselves are unchanged.

**General objective:** develop, validate and deploy aiPHeed, a geospatial food insecurity forecasting system for DA Region IV-A using NLP and machine learning.

| # | Chapter 1 objective | E53 acceptance test | Where |
|---|---|---|---|
| 1 | Two-tier NLP pipeline → FSSI and topics per province-quarter | Unchanged from E52; the news group is now tested by ablation (does it add predictive information to the forecast?) | E53 arm A-news |
| 2 | Evaluate **LightGBM** with accuracy, precision, recall, F1, AUC-ROC and lead time (walk-forward; 75% at the required lead) | A **LightGBM** arm (LGB-R primary) on the PS target at Lead-2 with accuracy ≥ 0.75, balanced accuracy ≥ 0.70 and both recalls ≥ 0.60, on E52's identical rows; all listed metrics reported | E53 `runs/` |
| 2b | Reliable probabilities (part of "evaluate", needed for the alert threshold) | \|calibration-in-the-large\| ≤ 0.05 and Brier no worse than E52 (K1, K2) | E53 C1/C2 |
| 3 | Municipal and city rankings from validated province forecasts | Unchanged: 142 LGUs labelled as relative prioritisation; "validated" waits for the 2027 prospective test | API, E36 record |
| 4 | Beat naive persistence, PSA-only, NLP-only and logistic-regression baselines | Brier and balanced accuracy better than every E52 baseline on identical rows (A3, A4) | E53 `runs/` |
| 5 | Dashboard with maps and alerts; ISO/IEC 25010 evaluation; FNRI face validity | Dashboard live-verified. The survey needs the 50 DA IV-A respondents and the FNRI check needs the NNS 2019/2023 figures; both are external. | live checks |

**The five triggers (Chapter 1 §1.7)** are tested in two ways:
- Coverage: each group's inputs are present at every issue date.
- Ablation: does removing the group worsen the Brier score?

They are not forced to contribute.

**Target note:** PS is provincial food-price pressure, not food insecurity. Adopting it needs the adviser's approval (E51/E52).

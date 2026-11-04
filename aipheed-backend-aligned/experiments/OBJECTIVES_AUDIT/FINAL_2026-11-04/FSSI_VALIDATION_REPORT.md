# FSSI validation report

| Check | Result | Source |
|---|---|---|
| Built from XLM-R scores of admitted, de-duplicated headlines published before O(t) | ✅ | OBJ1 §1 |
| Bias correction (Eq. 1 coverage weights) | ✅ implemented; it cannot add coverage where none exists | OBJ1 §2–3 |
| Level FSSI drifts with corpus growth | Yes. The anomaly `z_N1R` is used instead | OBJ1 §3 |
| Availability | 12 of 113 origins; 10 labelled quarters (2023-Q3..2026-Q3) | `out/obj1_fssi_redundancy.json` |
| Relation to next-quarter hunger | ρ 0.45, p 0.19 (n = 10): not significant | same |
| Redundancy | ρ 0.78 crude oil, 0.76 rice inflation, 0.71 ONI | same |
| Early warning (pre-registered, Holm) | p ≥ 0.60 for all 6 signals | `out/obj1_earlywarning.json` |
| Contribution in C-E2 | 0.8% of SHAP; ablation Brier +0.0014 / +0.0011; 0 calls changed | `out/ce5_results.json` |

## Conclusion

The FSSI is computed correctly and without leakage. With 10 labelled quarters it has no measurable predictive value
beyond prices and climate.

**Improving it needs more news history or better province attribution (human labels), not a re-weighting.** The prompt
allows FSSI changes only when the annotations support them, and none exist yet. So the FSSI was not changed.

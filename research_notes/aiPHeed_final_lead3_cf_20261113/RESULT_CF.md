# Lead-3 F1 investigation: result (PROTOCOL_CF sha 054239a1, written before the run)

**Cause of the Lead-3 F1 failure (0.745 vs 0.755 at Lead 4):**
- Leads 3 and 4 use the same training rounds and the same chosen settings. The difference is four provinces whose probabilities sit at the 0.50 line:
  - Aklan 2018: 0.469 vs 0.566;
  - Palawan 2019: 0.494 vs 0.623;
  - Cagayan 2018: 0.493 vs 0.582;
  - Agusan del Sur 2021: 0.542 vs 0.444.
- Underneath, there is a seasonal data gap. Every Lead-3 origin is a 1 October issue, so the local farmgate-price window is May–July (lean season). As a result, 2–5 more provinces per round lack those inputs at Lead 3 only.

**Correction tested:** one-quarter carry-forward of missing local price inputs, applied to every lead, fold and seed (110 fits, 0 failures).

| Lead | FINAL mean fold acc | CF mean fold acc | FINAL F1 | CF F1 | FINAL Brier | CF Brier |
|---|---|---|---|---|---|---|
| 1 | 86.1 % | 86.1 % | 0.800 | 0.800 | 0.123 | 0.123 |
| 2 | 84.6 % | 86.3 % | 0.784 | 0.792 | 0.123 | 0.122 |
| 3 | 81.9 % | 81.9 % | **0.745** | **0.745** | 0.133 | 0.132 |
| 4 | 81.9 % | 80.4 % | 0.755 | **0.741** | 0.135 | 0.135 |
| 5 | 79.1 % | 75.9 % | 0.717 | 0.702 | 0.138 | 0.143 |
| 6 | 74.7 % | 74.6 % | 0.654 | 0.667 | 0.146 | 0.151 |

- **MRLT:** 5 under both.
- **Decision rule:** rule 1 passes; rules 2, 3 and 4 fail. Lead-5 accuracy drops 3.2 points, pooled Brier is worse (0.1310 vs 0.1304), and Lead 4 loses F1 ≥ 0.75. **CF is NOT adopted. FINAL is unchanged.**
- **Lead 3 under CF:** Palawan is now caught (0.526), but Guimaras is lost (0.534 → 0.427). F1 stays at 0.745.
- **Conclusion:** the Lead-3 F1 shortfall is threshold-edge noise of one province. It is not fixable by a legitimate data correction, and changing the threshold or model on these outcomes would be test-set tuning.

Evidence: `evidence/CF_vs_FINAL_by_lead.csv`, `CF_decision.json`, `CF_class_changes.csv` (17 class changes, all with p within 0.45–0.57).

# Addendum 1: the five trigger groups (user correction, before the ablation was scored)

**Written:** 2026-10-28. The candidates (§4) were already scored; the group ablation (§6) was not. This addendum's SHA-256 goes in `runner/ADDENDUM_1_SHA256.txt` before `ablation.py` runs.

## Correction

During the run the user stated that the five trigger groups are:

> Market/Prices, Climate, Employment, Fish production, OFW remittances

This matches the proposal and the dashboard decision of 2026-10-27. It replaces §2 of the protocol.

| Trigger group (dashboard key) | Model columns |
|---|---|
| Market / Prices (`market`) | A1_food, A1_gap, A_mom (A1), A2, A3, W_rice_yoy, W_rice_mom, W_cereal_yoy, W_crude_yoy |
| Climate (`climate`) | C1, C2, C3, W_urea_yoy |
| Employment (`employment`) | E1 |
| Fish production (`fish_kill`) | C4 |
| OFW remittances (`ofw_remittance`) | E2 |

The other required indicators stay in the model and are ablated the same way, but they are reported as **other inputs, not triggers**:
- News / NLP: N1 (XLM-R FSSI-v3), G_pri_yoy, NG_gap_price (GDELT);
- Poverty and vulnerability: V1;
- Regional hunger outlook: H1 (the hunger condition of the target).

## Effect on the frozen plan

- **§6** is run for the five trigger groups above plus the three other-input blocks. Holm correction is applied across the 5 trigger groups.
- **The no-trigger refit** keeps N1/GDELT, V1, H1 and lead, and removes all five trigger groups.
- **§7: the dashboard keeps its five existing groups.** Only the per-group evidence (data status, measured held-out contribution class, explanation) is added.
- **§3-§5 are unchanged.** The selection (FINAL = C0) is unaffected.

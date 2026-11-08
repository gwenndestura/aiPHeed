# E128 reliability decision

**Decision: no model is reliable at any lead.** No maximum reliable forecast horizon is established for regional food-insecurity (SWS Balance Luzon hunger) prediction with 2021–2026 data.

| Item | Decision |
|---|---|
| Frozen rule | R1–R7, unchanged. Not evaluable = not passed. |
| Lead 1 | Not reliable for any model or target (LightGBM T1 fails R1, R2, R4, R5, R6, R7) |
| Lead 2 | Not reliable. LightGBM T1 fails R1, R3 (no LOW rows), R4 and R5. Under T4, every model is at or below chance. |
| Leads 3, 4 | Not reliable (structural: R1, R3, R4, R5; LightGBM T1 Lead 4 at 0 % accuracy) |
| First unreliable lead | Lead 1 |
| Selected model | **None.** LightGBM is not selected. No baseline qualifies either. |
| Evidence status | Retrospective. All rows were inspected before E128. A pass would only have been provisional. |
| Strength of the negative result | **Inconclusive, not definitive.** R1 cannot be met by a single regional series in 2021–2026 (20 quarters). The data cannot show reliability or demonstrate unreliability with confidence. |

## What this does not say

- **It does not show that hunger is unforecastable in principle.** E114 found level-forecast skill over persistence on 2013–2020 using pre-2021 history, which is outside this study window.
- **It does not invalidate the provincial FIRI3 index.** FIRI3 is a composite, not a forecast (E121–E127).
- **It does not overturn the earlier Chapter I Lead-1 result on T43c.** It shows that result cannot be reproduced once copied regional labels are excluded.

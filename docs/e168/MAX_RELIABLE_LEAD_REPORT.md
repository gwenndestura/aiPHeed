# Maximum reliable lead report (E156 rule, unchanged)

Tool: `backend/app/e156/max_lead_all.py` → `data/e156/out/max_lead_all.json`.

| Model | Lead 1 accuracy (failed) | Lead 2 accuracy (failed) | **Max reliable lead** |
|---|---|---|---|
| E158 | 73.6 % (C1, C4) | 73.6 % (C1, C4) | **0** |
| E164 AUTO (withdrawn) | 79.2 % (C4) | 79.2 % (C4) | **0** |
| E165 AUTO-FINAL | 73.6 % (C1, C4) | 76.4 % (C1, C4) | **0** |
| E166 | 76.4 % (C1, C4) | 79.2 % (C4) | **0** |
| E167 | 66.7 % (C1, C4, C5) | 68.1 % (C1, C4, C5) | **0** |
| **E168 LightGBM-only** | 75.0 % (C1, C4) | 77.8 % (C4) | **0** |

**E168 at Lead 1 is 54/72 correct, two short of the 56 that C1 needs.**

Longer leads were not evaluated for E168, because Lead 1 fails and the rule is sequential. Why no lead is reliable is explained in `docs/final/WHY_NO_RELIABLE_LEAD.md`.

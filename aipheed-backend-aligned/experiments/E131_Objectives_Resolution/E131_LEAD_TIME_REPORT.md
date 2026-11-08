# E131 lead-time report

**Lead definitions** follow `backend/app/quarterly/target.py`:
- Lead 1 = the dashboard quarter (under way);
- **Lead 2 = the next quarter (the dashboard target; the minimum operational lead);**
- Leads 3–4 are the two quarters after that.

| Model | Lead 1 | Lead 2 | Lead 3 | Lead 4 | Maximum reliable lead |
|---|---|---|---|---|---|
| LLM (selected) | fails | fails: N1, N2, N5 (passes N3, N4, N6, N7) | fails | fails | **none** |
| DLLM | fails | fails | fails | fails | none |
| LGBM-ALL (proposed) | fails | fails: all 7 | fails | fails | **none** |
| LGBM-H, RIDGE-H, RIDGE-ALL, PSA-ONLY, NLP-ONLY | fail | fail | fail | fail | none |
| PERSIST, CLIM (baselines) | — | — | — | — | — |

The rule is applied under P-DASH and P-REL alike, on the shared rows and on the univariate set (`out/x1_rules.json`, `out/x1_univariate_rules.json`).

**The first unreliable lead is Lead 1 for every model,** so the maximum reliable lead is none and **Lead 2 status is failed.**

## Information horizon (E130)

| Issue rule | Distance from the newest SWS reading to the Lead-2 target |
|---|---|
| Dashboard (quarter start) | 3 quarters in 19 of 21 issues |
| Release-anchored | 2 quarters |

The release-anchored policy improves persistence at Lead 2 (univariate set: MAE 5.04 against 5.98) but not enough to pass.

## Why accuracy falls with lead (and why even Lead 1 fails)

- **Lead 1 already fails:** at the dashboard issue it sits 2 quarters past the newest reading, and the 2024 surge and 2025–26 oscillation dominate.
- **MAE grows with lead** on the univariate set: LLM 5.06 → 5.67 → 6.35 → 6.52; persistence 5.05 → 5.98 → 6.46 → 6.51.
- **The shared rows at Leads 3–4** (5–6 quarters) fall entirely after the surge. That is why their MAE looks lower; they are too few to rely on.
